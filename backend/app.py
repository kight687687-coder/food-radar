"""Food Radar Flask API, suitable for local use and Vercel Python Functions."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge

from ai_analyze import (
    AIProviderError,
    ProviderConfigurationError as AIConfigurationError,
    generate_chat_answer,
    generate_compare_advice,
    generate_daily_report,
    generate_report,
    generate_short_suggestion,
    generate_wiki_entry,
)
from classifier import classify
from config import ALLOWED_ORIGINS
from ocr import OCRProviderError, ProviderConfigurationError as OCRConfigurationError, ocr_image
from persistence import load_daily, load_history, load_wiki_cache, save_scan, save_wiki_cache
from score import score_ingredients


MAX_IMAGE_BASE64_LENGTH = 8_000_000
LOCAL_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
)

app = Flask(__name__)
app.json.ensure_ascii = False
app.config["MAX_CONTENT_LENGTH"] = 9 * 1024 * 1024
cors_origins = list(dict.fromkeys((*ALLOWED_ORIGINS, *LOCAL_ORIGINS))) if ALLOWED_ORIGINS else "*"
CORS(app, resources={r"/*": {"origins": cors_origins}}, supports_credentials=False)


def _resp(code=200, msg="success", data=None, status=None):
    payload = {"code": code, "msg": msg, "data": {} if data is None else data}
    return jsonify(payload), (status if status is not None else (code if code >= 400 else 200))


def _json_body():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ValueError("请求内容必须是 JSON 对象")
    return body


def _required_image(body, key="image"):
    image = body.get(key)
    if not isinstance(image, str) or not image.strip():
        raise ValueError(f"缺少 {key} 参数")
    value = image.strip()
    if value.startswith("data:") and "," in value:
        value = value.split(",", 1)[1]
    if len(value) > MAX_IMAGE_BASE64_LENGTH:
        raise ValueError("图片过大，请压缩后重试")
    return value


def _parse_avoid_ids(value):
    if value in (None, "", []):
        return None
    values = value.split(",") if isinstance(value, str) else value
    if not isinstance(values, (list, tuple)):
        raise ValueError("avoid_ids 格式不正确")
    try:
        return [int(item) for item in values if str(item).strip()]
    except (TypeError, ValueError) as exc:
        raise ValueError("avoid_ids 格式不正确") from exc


def _parse_ingredients(text):
    markers = ["配料表", "配料", "成分表", "成分", "原料表", "原料"]
    stops = [
        "生产日期", "保质期", "储存条件", "贮藏", "贮存", "食用方法", "产品标准",
        "生产许可证", "产地", "委托方", "受委托方", "制造商", "厂家", "服务热线",
        "客服", "二维码", "扫码", "微信公众号", "微博", "网址", "www.", "http",
    ]
    start = 0
    for marker in markers:
        index = text.find(marker)
        if index != -1:
            start = index + len(marker)
            break
    value = text[start:]
    for stop in stops:
        index = value.find(stop)
        if index != -1:
            value = value[:index]
            break
    value = re.sub(r"^[：:\s、，,；;\n\r]*", "", value)
    parts = [item.strip() for item in re.split(r"[、，,；;。\n\r]+", value) if item.strip()]
    filter_keywords = [
        "生产", "厂家", "地址", "保质期", "净含量", "营养", "每100", "执行", "标准",
        "温度", "储存", "食用方法", "产地", "服务热线", "热线", "商标", "公司", "有限",
        "许可证", "QS", "SC", "℃", "毫克", "克/", "mg/", "日期", "电话", "邮编",
        "网址", "扫码", "活动", "二维码", "联系电话", "GB",
    ]
    result = []
    for item in parts:
        if len(item) > 15 or any(keyword in item for keyword in filter_keywords):
            continue
        if re.fullmatch(r"\d+|[a-zA-Z]+|[\d.]+%?", item):
            continue
        if re.search(r"\d{3,}", item):
            continue
        result.append(item)
    if len(result) < 2 and parts:
        loose = [
            item for item in parts
            if len(item) <= 15
            and not re.fullmatch(r"\d+", item)
            and not any(keyword in item for keyword in filter_keywords)
        ]
        return (loose or parts)[:20]
    return result


def _validate_ingredients(ingredients_list):
    if len(ingredients_list) > 80:
        raise ValueError("配料表异常（条目过多），请重新拍摄配料表区域")
    if not ingredients_list:
        raise ValueError("无法识别有效配料表，请重新拍摄")
    food_chars = "糖粉油酸钠胶脂水盐肉奶乳蛋豆米麦淀素色香精料醋酱芡"
    food_count = sum(1 for item in ingredients_list if any(char in item for char in food_chars))
    if food_count / len(ingredients_list) < 0.3:
        raise ValueError("未找到有效配料表，请对准配料表拍摄")


def _get_subcategory(main_category, ingredients_list):
    text = ",".join(ingredients_list)
    rules = {
        "饮料类": [
            ("碳酸饮料", ("碳酸", "二氧化碳")),
            ("能量饮料", ("咖啡因", "牛磺酸")),
            ("茶饮料", ("茶", "茶多酚")),
            ("果汁饮料", ("果汁", "浓缩汁")),
        ],
        "乳制品类": [
            ("酸奶", ("嗜热链球菌", "乳酸菌", "保加利亚")),
            ("奶粉", ("乳粉", "奶粉")),
            ("奶酪", ("奶酪", "干酪")),
        ],
        "零食类": [
            ("薯片", ("马铃薯", "薯片")),
            ("膨化食品", ("膨化", "玉米粉")),
            ("坚果", ("坚果", "花生", "核桃", "杏仁")),
            ("海苔零食", ("海苔", "紫菜")),
        ],
        "正餐类": [
            ("速冻食品", ("速冻", "糯米")),
            ("方便面", ("方便面", "油炸面")),
            ("罐头食品", ("罐头", "午餐肉")),
        ],
        "肉制品类": [
            ("牛肉制品", ("牛肉",)),
            ("腌制肉品", ("亚硝酸",)),
            ("鸡肉制品", ("鸡肉",)),
        ],
    }
    defaults = {"饮料类": "饮料", "乳制品类": "纯牛奶", "零食类": "零食", "正餐类": "正餐", "肉制品类": "肉制品"}
    for label, keywords in rules.get(main_category, []):
        if any(keyword in text for keyword in keywords):
            return label
    return defaults.get(main_category, main_category)


def _run_analysis_pipeline(image_base64, user_type, avoid_ids=None):
    ocr_text = ocr_image(image_base64=image_base64)
    if not ocr_text.strip():
        raise ValueError("OCR未能识别到文字")
    if re.search(r"营\s*养\s*成\s*分", ocr_text) and not re.search(r"配\s*料|原\s*料|配\s*方", ocr_text):
        raise ValueError("识别到营养成分表，请翻转包装找到配料表重新拍摄")
    ingredient_patterns = [r"配\s*料", r"成\s*分[：:;.]", r"原\s*料[：:;.]", r"配\s*方[：:;.]", r"[Ii]ngredients?"]
    if not any(re.search(pattern, ocr_text) for pattern in ingredient_patterns):
        raise ValueError("未找到配料表，请翻转包装找到以'配料：'开头的文字重新拍摄")

    ingredients_list = _parse_ingredients(ocr_text)
    _validate_ingredients(ingredients_list)
    main_category, confidence = classify(",".join(ingredients_list))
    if confidence < 0.3 and len(ingredients_list) < 2:
        raise ValueError("未能识别到有效配料表，请对准配料表重新拍摄")
    food_category = _get_subcategory(main_category, ingredients_list)
    score_result = score_ingredients(ingredients_list, group_type=user_type, avoid_ids=avoid_ids)
    score_details = {
        "beneficial_bonus": score_result["beneficial_bonus"],
        "stacking_penalty": score_result["stacking_penalty"],
        "ingredients_count_penalty": score_result["ingredients_count_penalty"],
        "group_extra_penalty": score_result["group_extra_penalty"],
        "group_extra_details": score_result["group_extra_details"],
    }
    ai_report = generate_report(
        food_category,
        score_result["health_score"],
        score_result["risk_additives"],
        user_type,
        score_result["group_warnings"],
        beneficial_ingredients=score_result["beneficial_ingredients"],
        avoid_warnings=score_result["avoid_warnings"],
        score_details=score_details,
        ingredients=ingredients_list,
    )
    return {
        "ingredients": ",".join(ingredients_list),
        "food_category": food_category,
        "food_category_main": main_category,
        "health_score": score_result["health_score"],
        "risk_count": len(score_result["risk_additives"]),
        "risk_additives": score_result["risk_additives"],
        "group_warnings": score_result["group_warnings"],
        "beneficial_ingredients": score_result["beneficial_ingredients"],
        "beneficial_bonus": score_result["beneficial_bonus"],
        "avoid_warnings": score_result["avoid_warnings"],
        "stacking_penalty": score_result["stacking_penalty"],
        "ingredients_count_penalty": score_result["ingredients_count_penalty"],
        "group_extra_penalty": score_result["group_extra_penalty"],
        "group_extra_details": score_result["group_extra_details"],
        "score_details": score_details,
        "ai_report": ai_report,
    }


@app.get("/health")
def health():
    return _resp(data={"status": "ok", "time": datetime.now(timezone.utc).isoformat()})


@app.post("/analyze")
def analyze():
    try:
        body = _json_body()
        image = _required_image(body)
        result = _run_analysis_pipeline(image, body.get("user_type") or "普通人群", _parse_avoid_ids(body.get("avoid_ids")))
        scan_id = save_scan(result, body)
        if scan_id is not None:
            result["scan_id"] = scan_id
        return _resp(data=result)
    except ValueError as exc:
        return _resp(code=400, msg=str(exc))
    except OCRConfigurationError as exc:
        return _resp(code=503, msg=str(exc))
    except OCRProviderError:
        return _resp(code=502, msg="文字识别服务暂时不可用，请稍后重试")


@app.post("/compare")
def compare():
    try:
        body = _json_body()
        first = _run_analysis_pipeline(_required_image(body, "image1"), body.get("user_type") or "普通人群")
        second = _run_analysis_pipeline(_required_image(body, "image2"), body.get("user_type") or "普通人群")
        recommend = 1 if first["health_score"] >= second["health_score"] else 2
        return _resp(data={"food1": first, "food2": second, "recommend": f"推荐食品{'一' if recommend == 1 else '二'}"})
    except ValueError as exc:
        return _resp(code=400, msg=str(exc))
    except OCRConfigurationError as exc:
        return _resp(code=503, msg=str(exc))
    except OCRProviderError:
        return _resp(code=502, msg="文字识别服务暂时不可用，请稍后重试")


@app.get("/history")
def history():
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return _resp(code=400, msg="缺少 user_id 参数")
    records = load_history(user_id)
    return _resp(data={"list": records, "total": len(records)})


@app.get("/daily")
def daily():
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return _resp(code=400, msg="缺少 user_id 参数")
    data = load_daily(user_id)
    if not data:
        return _resp(data={"scan_count": 0, "avg_score": 0, "worst_food": None, "ai_summary": None, "daily_score": 0})
    worst_name = (data.get("worst_food") or {}).get("product_name") or "未知"
    data["ai_summary"] = generate_daily_report(data["scan_count"], data["avg_score"], worst_name, data.pop("foods_context", ""))
    return _resp(data=data)


@app.post("/api/ai-compare")
def ai_compare():
    try:
        body = _json_body()
        return _resp(data={"advice": generate_compare_advice(body.get("food_a", {}), body.get("food_b", {}))})
    except ValueError as exc:
        return _resp(code=400, msg=str(exc))


@app.post("/api/ai-suggestion")
def ai_suggestion():
    try:
        body = _json_body()
        suggestion = generate_short_suggestion(
            body.get("categories", []), body.get("risk_items", []), body.get("avg_score", 0),
            body.get("scan_count", 0), body.get("period_label", "今日"),
        )
        return _resp(data={"suggestion": suggestion})
    except ValueError as exc:
        return _resp(code=400, msg=str(exc))


@app.post("/api/ai-chat")
def ai_chat():
    try:
        body = _json_body()
        question = str(body.get("question") or "").strip()
        if not question:
            return _resp(code=400, msg="请输入问题")
        answer = generate_chat_answer(question, body.get("history", []), body.get("user_type") or "普通人群")
        return _resp(data={"answer": answer})
    except ValueError as exc:
        return _resp(code=400, msg=str(exc))
    except AIConfigurationError as exc:
        return _resp(code=503, msg=str(exc))
    except AIProviderError:
        return _resp(code=502, msg="AI 服务暂时不可用，请稍后重试")


@app.post("/api/wiki-query")
def wiki_query():
    try:
        body = _json_body()
        name = str(body.get("name") or "").strip()[:100]
        if not name:
            return jsonify({"error": "缺少name参数"}), 400
        cached = load_wiki_cache(name)
        if cached:
            return jsonify({"success": True, "data": cached, "source": "cache"})
        result = generate_wiki_entry(name)
        save_wiki_cache(name, result)
        return jsonify({"success": True, "data": result, "source": "deepseek"})
    except (AIConfigurationError, AIProviderError):
        return jsonify({"error": "AI 百科服务尚未配置或暂时不可用"}), 503
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.errorhandler(RequestEntityTooLarge)
def handle_large_request(_error):
    return _resp(code=413, msg="图片过大，请压缩后重试")


@app.errorhandler(Exception)
def handle_unexpected_error(error):
    if isinstance(error, HTTPException):
        return _resp(code=error.code or 500, msg=error.description)
    app.logger.exception("Unhandled API error")
    return _resp(code=500, msg="服务暂时不可用，请稍后重试")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
