import json
import re
import sys
import io
from datetime import datetime, date

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from flask import Flask, request, jsonify
from flask_cors import CORS
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from config import SQLALCHEMY_DATABASE_URI, DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL
from models import Base, ScanHistory

app = Flask(__name__)
app.json.ensure_ascii = False
CORS(app)

engine = create_engine(SQLALCHEMY_DATABASE_URI)

def _resp(code=200, msg="success", data=None):
    return jsonify({"code": code, "msg": msg, "data": data or {}})

def _parse_ingredients(text):
    # 配料表标记列表（按优先级）
    MARKERS = ["配料表", "配料", "成分表", "成分", "原料表", "原料"]
    # 截断标记——遇到这些就停止（配料表之后的内容）
    STOP_KW = ["生产日期", "保质期", "储存条件", "贮藏", "贮存", "食用方法",
               "产品标准", "生产许可证", "产地", "委托方", "受委托方",
               "制造商", "厂家", "服务热线", "客服", "二维码", "扫码",
               "微信公众号", "微博", "网址", "www.", "http"]

    start = 0
    for marker in MARKERS:
        idx = text.find(marker)
        if idx != -1:
            start = idx + len(marker)
            break

    text = text[start:]

    for stop in STOP_KW:
        idx = text.find(stop)
        if idx != -1:
            text = text[:idx]
            break

    text = re.sub(r"^[：:\s、，,；;\n\r]*", "", text)

    parts = re.split(r"[、，,；;。\n\r]+", text)
    parts = [p.strip() for p in parts if p.strip()]

    FILTER_KW = ['生产', '厂家', '地址', '保质期', '净含量', '营养', '每100',
                 '执行', '标准', '温度', '储存', '食用方法', '产地',
                 '服务热线', '热线', '商标', '公司', '有限', '科技',
                 '生物', '授权', '使用', '许可', '证', '号', 'QS', 'SC',
                 '℃', '焦', '瓦', '毫克', '克/', 'g/', 'mg/', '%', '日期',
                 '年', '月', '提示', '请', '避免', '直射', '干燥', '阴凉',
                 '食用前', '建议', '警告', '注意', '联系', '客服',
                 '省', '市', '县', '区', '路', '街', '号楼', '传真', '邮编',
                 '网址', 'www', 'http', '扫码', '红包', '抽奖', '赢', '活动',
                 '兑换', '积分', '会员', '关注', '分享', '点赞', '投票',
                 '生产日期', '储存条件', '联系电话', '电话号码', '邮政编码',
                 '执行标准', '生产许可证', '备案号', '注册号', 'GB', 'SC', 'QS',
                 '电话', '邮编']
    result = []
    for p in parts:
        # 过长文本通常是地址、说明或宣传语，不作为单个配料处理
        if len(p) > 15:
            continue
        # 命中生产、标准、联系方式等关键词时，判定为非配料字段
        if any(kw in p for kw in FILTER_KW):
            continue
        # 纯数字或纯英文一般不是中文配料名称
        if re.match(r'^\d+$', p) or re.match(r'^[a-zA-Z]+$', p):
            continue
        if re.match(r'^[\d.]+%?$', p) or re.match(r'^[\d.]+(g|mg|ml|kcal|kJ|%)$', p):
            continue
        if re.search(r'[a-zA-Z]', p) and re.search(r'\d', p) and len(p) > 8:
            continue
        if re.search(r'\d{3,}', p):
            continue
        result.append(p)
    if len(result) < 2 and parts:
        # 至少去掉明显非配料的条目
        loose = [p for p in parts if len(p) <= 15
                 and not re.match(r'^\d+$', p)
                 and not any(kw in p for kw in FILTER_KW)]
        return loose[:20] if loose else parts[:20]
    return result

def _get_subcategory(main_category, ingredients_list):
    ing_text = ",".join(ingredients_list)

    # 饮料类根据碳酸、咖啡因、茶多酚、果汁等关键词细分
    if main_category == "饮料类":
        if "碳酸" in ing_text or "二氧化碳" in ing_text:
            return "碳酸饮料"
        if "咖啡因" in ing_text or "牛磺酸" in ing_text:
            return "能量饮料"
        if "茶" in ing_text or "茶多酚" in ing_text:
            return "茶饮料"
        if "果汁" in ing_text or "浓缩汁" in ing_text:
            return "果汁饮料"
        return "饮料"

    # 乳制品类根据菌种、乳粉、奶酪等关键词细分
    if main_category == "乳制品类":
        if "嗜热链球菌" in ing_text or "乳酸菌" in ing_text or "保加利亚" in ing_text:
            return "酸奶"
        if "乳粉" in ing_text or "奶粉" in ing_text:
            return "奶粉"
        if "奶酪" in ing_text or "干酪" in ing_text:
            return "奶酪"
        return "纯牛奶"

    if main_category == "零食类":
        if "马铃薯" in ing_text or "薯片" in ing_text:
            return "薯片"
        if "膨化" in ing_text or "玉米粉" in ing_text:
            return "膨化食品"
        if "坚果" in ing_text or "花生" in ing_text or "核桃" in ing_text or "杏仁" in ing_text:
            return "坚果"
        if "海苔" in ing_text or "紫菜" in ing_text:
            return "海苔零食"
        return "零食"

    # 正餐类根据速冻、方便面、罐头等关键词细分
    if main_category == "正餐类":
        if "速冻" in ing_text or "糯米" in ing_text:
            return "速冻食品"
        if "方便面" in ing_text or "油炸面" in ing_text:
            return "方便面"
        if "罐头" in ing_text or "午餐肉" in ing_text:
            return "罐头食品"
        return "正餐"

    if main_category == "肉制品类":
        if "牛肉" in ing_text:
            return "牛肉制品"
        if "猪肉" in ing_text and "亚硝酸" in ing_text:
            return "腌制肉品"
        if "鸡肉" in ing_text:
            return "鸡肉制品"
        return "肉制品"

    return main_category

def _validate_ingredients(ingredients_list, ocr_text):
    if len(ingredients_list) > 80:
        return False, "配料表异常（条目过多），请重新拍摄配料表区域"

    # 有效配料必须包含食品相关字符
    if ingredients_list:
        _FOOD_CHARS = ["糖", "粉", "油", "酸", "钠", "胶", "脂", "水", "盐",
                       "肉", "奶", "乳", "蛋", "豆", "米", "麦",
                       "淀", "素", "色", "香", "精", "料", "醋", "酱", "芡"]
        # 统计食品相关字出现比例，用于判断识别结果是否像真实配料
        food_count = sum(1 for ing in ingredients_list if any(c in ing for c in _FOOD_CHARS))
        food_ratio = food_count / len(ingredients_list)
        if food_ratio < 0.3:
            return False, "未找到有效配料表，请对准配料表拍摄"

    # 至少1条有效配料即通过
    if len(ingredients_list) >= 1:
        return True, ""

    # 没有识别到任何配料
    return False, "无法识别有效配料表，请重新拍摄"

def _run_analysis_pipeline(image_base64, user_type, avoid_ids=None):
    from ocr import ocr_image
    from classifier import classify
    from score import score_ingredients
    from ai_analyze import generate_report

    # 1. OCR
    ocr_text = ocr_image(image_base64=image_base64)
    if not ocr_text.strip():
        raise ValueError("OCR未能识别到文字")

    # 1.5 强制检查原文是否有配料表标识（在解析之前）
    _INGREDIENT_PATTERNS = [
        r'配\s*料',                          # 配料：/配料表（标点可选）
        r'成\s*分[：:;.]',                   # 成分：/成分:（排除"营养成分表"）
        r'原\s*料[：:;.]',                   # 原料：/原料:（排除营销用语）
        r'配\s*方[：:;.]',                   # 配方：/配方:
        r'[Ii]ngredients?',                  # Ingredients/ingredient
    ]
    # 排除——OCR 识别到"营养成分表"但没识别到"配料/原料/配方"
    if re.search(r'营\s*养\s*成\s*分', ocr_text) and not re.search(r'配\s*料|原\s*料|配\s*方', ocr_text):
        raise ValueError("识别到营养成分表，请翻转包装找到配料表重新拍摄")
    # 未命中配料相关标识时，直接中断分析，避免后续评分建立在错误文本上
    if not any(re.search(p, ocr_text) for p in _INGREDIENT_PATTERNS):
        raise ValueError("未找到配料表，请翻转包装找到以'配料：'开头的文字重新拍摄")

    # 2. 解析配料
    ingredients_list = _parse_ingredients(ocr_text)

    # 2.5 配料可信度验证
    valid, reason = _validate_ingredients(ingredients_list, ocr_text)
    if not valid:
        raise ValueError(reason)

    # 3. 分类
    print(f"[Classify] 输入配料: {','.join(ingredients_list[:10])}... 共{len(ingredients_list)}条")
    food_category_main, confidence = classify(",".join(ingredients_list))
    # 分类置信度过低且配料数量不足时，认为图片质量或识别区域不可靠
    if confidence < 0.3 and len(ingredients_list) < 2:
        raise ValueError("未能识别到有效配料表，请对准配料表重新拍摄")
    food_category = _get_subcategory(food_category_main, ingredients_list)

    # 4. 评分
    score_result = score_ingredients(
        ingredients_list,
        group_type=user_type,
        avoid_ids=avoid_ids,
    )

    # 5. AI分析
    ai_report = generate_report(
        food_category=food_category,
        health_score=score_result["health_score"],
        risk_additives=score_result["risk_additives"],
        user_type=user_type,
        warnings=score_result["group_warnings"],
    )

    return {
        "ingredients": ",".join(ingredients_list),
        "food_category": food_category,
        "food_category_main": food_category_main,
        "health_score": score_result["health_score"],
        "risk_count": len(score_result["risk_additives"]),
        "risk_additives": score_result["risk_additives"],
        "group_warnings": score_result["group_warnings"],
        "beneficial_ingredients": score_result["beneficial_ingredients"],
        "beneficial_bonus": score_result.get("beneficial_bonus", 0),
        "avoid_warnings": score_result["avoid_warnings"],
        "stacking_penalty": score_result.get("stacking_penalty", 0),
        "ingredients_count_penalty": score_result.get("ingredients_count_penalty", 0),
        "ai_report": ai_report,
    }

@app.route("/health", methods=["GET"])
def health():
    return _resp(data={"status": "ok", "time": datetime.now().isoformat()})

@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        body = request.get_json(force=True)
        image = body.get("image")
        user_type = body.get("user_type")
        avoid_ids = body.get("avoid_ids")

        if image:
            print("[Analyze] 收到图片 base64 长度:", len(image))
        else:
            return _resp(code=400, msg="缺少 image 参数")

        # 将前端传入的逗号分隔编号转换为整数列表，供评分模块匹配避开项
        if avoid_ids:
            avoid_ids = [int(i) for i in avoid_ids.split(",") if i.strip()]
        else:
            avoid_ids = None

        # 调用统一分析管线，得到识别、分类、评分和AI分析结果
        result = _run_analysis_pipeline(image, user_type, avoid_ids)

        with Session(engine) as session:
            record = ScanHistory(
                user_id=body.get("user_id"),
                product_name=result["food_category"],
                ingredients=result["ingredients"],
                food_category=result["food_category"],
                health_score=result["health_score"],
                risk_count=result["risk_count"],
                result_json=json.dumps(result, ensure_ascii=False),
            )
            session.add(record)
            print("准备插入记录:", record.user_id, record.product_name, record.health_score)
            session.commit()
            result["scan_id"] = record.id

        return _resp(data=result)

    except ValueError as e:
        return _resp(code=400, msg=str(e))
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return _resp(code=500, msg=f"分析失败: {str(e)}")

@app.route("/compare", methods=["POST"])
def compare():
    try:
        body = request.get_json(force=True)
        img1 = body.get("image1")
        img2 = body.get("image2")
        user_type = body.get("user_type")

        if not img1 or not img2:
            return _resp(code=400, msg="缺少 image1 或 image2 参数")

        r1 = _run_analysis_pipeline(img1, user_type)
        r2 = _run_analysis_pipeline(img2, user_type)

        # 健康评分较高的食品作为推荐结果
        recommend = 1 if r1["health_score"] >= r2["health_score"] else 2

        return _resp(data={
            "food1": r1,
            "food2": r2,
            "recommend": f"推荐食品{'一' if recommend == 1 else '二'}",
        })

    except ValueError as e:
        return _resp(code=400, msg=str(e))
    except Exception as e:
        return _resp(code=500, msg=f"对比失败: {str(e)}")

@app.route("/history", methods=["GET"])
def history():
    try:
        user_id = request.args.get("user_id", type=int)
        if not user_id:
            return _resp(code=400, msg="缺少 user_id 参数")

        with Session(engine) as session:
            records = (
                session.query(ScanHistory)
                .filter(ScanHistory.user_id == user_id)
                .order_by(ScanHistory.scan_time.desc())
                .limit(20)
                .all()
            )

        data = []
        for r in records:
            data.append({
                "id": r.id,
                "product_name": r.product_name,
                "food_category": r.food_category,
                "health_score": r.health_score,
                "risk_count": r.risk_count,
                "scan_time": r.scan_time.isoformat() if r.scan_time else None,
            })

        return _resp(data={"list": data, "total": len(data)})

    except Exception as e:
        return _resp(code=500, msg=str(e))

@app.route("/daily", methods=["GET"])
def daily():
    try:
        user_id = request.args.get("user_id", type=int)
        if not user_id:
            return _resp(code=400, msg="缺少 user_id 参数")

        today = date.today()
        with Session(engine) as session:
            records = (
                session.query(ScanHistory)
                .filter(
                    ScanHistory.user_id == user_id,
                    text("DATE(scan_time) = :today"),
                )
                .params(today=today)
                .order_by(ScanHistory.scan_time.desc())
                .all()
            )

        scan_count = len(records)
        if scan_count == 0:
            return _resp(data={
                "scan_count": 0,
                "avg_score": 0,
                "worst_food": None,
                "ai_summary": None,
                "daily_score": 0,
            })

        scores = [r.health_score for r in records if r.health_score is not None]
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0

        # 找出当天健康评分最低的食品，作为重点风险提醒
        worst = min(records, key=lambda r: r.health_score or 100)
        worst_food = {
            "product_name": worst.product_name,
            "health_score": worst.health_score,
            "risk_count": worst.risk_count,
            "scan_time": worst.scan_time.isoformat() if worst.scan_time else None,
        }

        foods_context = "; ".join(
            f"{r.product_name}({r.health_score}分/{r.risk_count}风险)"
            for r in records[:10]
        )

        # 将当天摘要交给AI生成更自然的饮食建议
        from ai_analyze import generate_daily_report
        ai_summary = generate_daily_report(
            scan_count, avg_score,
            worst.product_name or "未知", foods_context,
        )

        return _resp(data={
            "scan_count": scan_count,
            "avg_score": avg_score,
            "worst_food": worst_food,
            "ai_summary": ai_summary,
            "daily_score": round(avg_score, 0),
        })

    except Exception as e:
        return _resp(code=500, msg=str(e))

@app.route("/api/ai-compare", methods=["POST"])
def ai_compare():
    try:
        body = request.get_json(force=True)
        food_a = body.get("food_a", {})
        food_b = body.get("food_b", {})

        from ai_analyze import generate_compare_advice
        advice = generate_compare_advice(food_a, food_b)

        return _resp(data={"advice": advice})

    except Exception as e:
        print("[AI Compare Error]", str(e))
        return _resp(code=500, msg=str(e))

@app.route("/api/ai-suggestion", methods=["POST"])
def ai_suggestion():
    try:
        body = request.get_json(force=True)
        categories = body.get("categories", [])
        risk_items = body.get("risk_items", [])
        avg_score = body.get("avg_score", 0)
        scan_count = body.get("scan_count", 0)
        period_label = body.get("period_label", "今日")

        from ai_analyze import generate_short_suggestion
        suggestion = generate_short_suggestion(categories, risk_items, avg_score, scan_count, period_label)

        return _resp(data={"suggestion": suggestion})

    except Exception as e:
        print("[AI Suggestion Error]", str(e))
        return _resp(code=500, msg=str(e))

@app.route("/api/ai-chat", methods=["POST"])
def ai_chat():
    try:
        body = request.get_json(silent=True)
        if body is None:
            raw = request.get_data(as_text=True) or "{}"
            try:
                body = json.loads(raw)
            except Exception:
                body = {}
        question = (body.get("question") or "").strip()
        if not question:
            return _resp(code=400, msg="请输入问题")

        # 保留历史对话上下文，使AI回答更连贯
        history = body.get("history", [])
        user_type = body.get("user_type") or "普通人群"

        from ai_analyze import generate_chat_answer
        answer = generate_chat_answer(question, history=history, user_type=user_type)

        return _resp(data={"answer": answer})

    except Exception as e:
        print("[AI Chat Error]", str(e))
        return _resp(code=500, msg=str(e))

@app.route("/api/wiki-query", methods=["POST"])
def wiki_query():
    data = request.get_json()
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': '缺少name参数'}), 400

    import json as json_lib
    from sqlalchemy import text
    from models import WikiCache

    try:
        with Session(engine) as session:
            # 命中有效缓存时直接返回，减少AI接口调用成本并提升响应速度
            row = session.query(WikiCache).filter(
                WikiCache.name == name,
                text("updated_at > DATE_SUB(NOW(), INTERVAL 30 DAY)")
            ).first()

            if row:
                cached_data = json_lib.loads(row.data) if isinstance(row.data, str) else row.data
                return jsonify({'success': True, 'data': cached_data, 'source': 'cache'})

        # 提示词要求AI严格输出JSON，便于前端直接渲染百科字段
        prompt = f"""你是专业食品安全研究员，请介绍食品添加剂「{name}」。严格按以下JSON格式返回，不要输出任何其他内容，不要有markdown格式：
{{
  "name": "标准中文名",
  "alias": ["常见别称1", "常见别称2"],
  "category": "分类（防腐剂/甜味剂/色素/增稠剂/抗氧化剂/乳化剂/香精香料之一）",
  "origin": "来源与合成方式，天然还是人工合成，制备工艺，2-3句",
  "mechanism": "在食品中具体怎么发挥作用，原理是什么，2-3句",
  "controversy": "已知健康争议、相关研究结论、各国监管态度差异，2-3句，若无争议则如实说明",
  "usage": "主要用途",
  "common_in": "常见于哪些具体食品，列举4-6种",
  "adi": "ADI值，格式如'0-5 mg/kg体重/天'，若无限制则写'无需规定'",
  "intake_status": "普通人日常实际摄入量与ADI的关系，2句",
  "risk_level": 风险等级数字1低2中3高,
  "risk_desc": "风险等级一句话说明",
  "warning": "具体注意事项",
  "special_groups": ["需注意的特殊人群"]
}}"""

        from openai import OpenAI
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        raw = response.choices[0].message.content.strip()
        # 兼容AI偶尔返回代码块包裹JSON的情况
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[1]
        if raw.endswith('```'):
            raw = raw.rsplit('```', 1)[0]

        # 将AI返回文本解析为结构化对象，解析失败会进入JSON异常处理
        result = json_lib.loads(raw)

        with Session(engine) as session:
            existing = session.query(WikiCache).filter(WikiCache.name == name).first()
            if existing:
                existing.data = json_lib.dumps(result, ensure_ascii=False)
            else:
                session.add(WikiCache(
                    name=name,
                    data=json_lib.dumps(result, ensure_ascii=False),
                ))
            session.commit()

        return jsonify({'success': True, 'data': result, 'source': 'deepseek'})

    except json_lib.JSONDecodeError:
        return jsonify({'error': 'AI返回格式异常'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
