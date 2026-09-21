"""DeepSeek integration and deterministic fallbacks for core reports."""

from __future__ import annotations

import json

from openai import OpenAI

from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL


class ProviderConfigurationError(RuntimeError):
    pass


class AIProviderError(RuntimeError):
    pass


def get_deepseek_client() -> OpenAI:
    if not DEEPSEEK_API_KEY:
        raise ProviderConfigurationError(
            "DeepSeek 尚未配置，请在服务端设置 DEEPSEEK_API_KEY"
        )
    return OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL, timeout=35.0)


def _completion(messages, *, temperature=0.5, max_tokens=None):
    try:
        response = get_deepseek_client().chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return (response.choices[0].message.content or "").strip()
    except ProviderConfigurationError:
        raise
    except Exception as exc:
        raise AIProviderError("AI 服务暂时不可用，请稍后重试") from exc


def _json_content(content: str) -> dict:
    value = content.strip()
    if value.startswith("```"):
        value = value.split("\n", 1)[1] if "\n" in value else ""
    if value.endswith("```"):
        value = value[:-3].rstrip()
    try:
        result = json.loads(value)
    except json.JSONDecodeError as exc:
        raise AIProviderError("AI 返回格式异常，请稍后重试") from exc
    if not isinstance(result, dict):
        raise AIProviderError("AI 返回格式异常，请稍后重试")
    return result


def build_fallback_report(
    food_category,
    health_score,
    risk_additives,
    user_type,
    warnings,
    *,
    beneficial_ingredients=None,
    avoid_warnings=None,
    score_details=None,
    ingredients=None,
):
    risk_additives = risk_additives or []
    warnings = warnings or []
    beneficial_ingredients = beneficial_ingredients or []
    avoid_warnings = avoid_warnings or []
    score_details = score_details or {}
    ingredients = ingredients or []
    risk_names = "、".join(item.get("name", "") for item in risk_additives[:3] if item.get("name"))
    benefit_names = "、".join(
        item.get("nutrient") or item.get("name", "")
        for item in beneficial_ingredients[:3]
        if item.get("nutrient") or item.get("name")
    )
    avoid_names = "、".join(item.get("name", "") for item in avoid_warnings[:3] if item.get("name"))
    warning_text = "；".join(item.get("msg", "") for item in warnings[:2] if item.get("msg"))
    audience = user_type or "普通人群"

    if health_score >= 85:
        level = "整体配料风险较低"
    elif health_score >= 60:
        level = "整体风险处于中等水平"
    else:
        level = "检测到较多需要留意的成分"

    detail_parts = [f"该食品分类为{food_category}，基础健康评分为{health_score}分，{level}。"]
    if risk_names:
        detail_parts.append(f"主要风险成分包括：{risk_names}。")
    if warning_text:
        detail_parts.append(f"人群提醒：{warning_text}。")
    if not risk_names and not warning_text:
        detail_parts.append("当前规则库未检出明确的高风险添加剂或人群预警。")

    judgment_parts = [f"当前分析对象为{audience}。"]
    if risk_names:
        judgment_parts.append(f"需要重点判断的风险成分为{risk_names}。")
    if benefit_names:
        judgment_parts.append(f"同时识别到{benefit_names}等有益成分，但其正向作用不能抵消全部风险。")
    if avoid_names:
        judgment_parts.append(f"命中个人忌口：{avoid_names}，应优先回避。")
    if score_details.get("group_extra_penalty"):
        judgment_parts.append(f"当前人群适配额外扣分为{score_details['group_extra_penalty']}分。")

    recommendation = f"建议{audience}结合食用频率和份量判断，优先选择配料更简单、风险成分更少的同类食品。"
    if avoid_names:
        recommendation = f"建议{audience}优先避免命中的忌口成分（{avoid_names}），并选择配料更简单的替代品。"
    elif risk_names:
        recommendation = f"建议{audience}减少高频食用{risk_names}的食品，必要时选择同类低风险替代品。"

    return {
        "summary": f"{food_category}健康评分 {health_score} 分，{level}。",
        "detail": "".join(detail_parts),
        "suggestion": f"建议{audience}结合食用频率和份量判断，优先选择配料更简单、风险成分更少的同类食品。",
        "long_term_risk": "单次识别不能代替医学诊断；若长期高频食用，应关注配料叠加、总糖总盐以及个人过敏或疾病限制。",
        "judgment": "".join(judgment_parts),
        "recommendation": recommendation,
    }


def generate_report(
    food_category,
    health_score,
    risk_additives,
    user_type,
    warnings,
    *,
    beneficial_ingredients=None,
    avoid_warnings=None,
    score_details=None,
    ingredients=None,
):
    beneficial_ingredients = beneficial_ingredients or []
    avoid_warnings = avoid_warnings or []
    score_details = score_details or {}
    ingredients = ingredients or []
    prompt = f"""你是专业营养师和食品安全专家，请根据以下信息生成分析报告：

食品类别：{food_category}
健康评分：{health_score}
配料表：{json.dumps(ingredients, ensure_ascii=False)}
风险添加剂：{json.dumps(risk_additives, ensure_ascii=False)}
有益成分：{json.dumps(beneficial_ingredients, ensure_ascii=False)}
忌口命中：{json.dumps(avoid_warnings, ensure_ascii=False)}
人群类型：{user_type or '无'}
预警信息：{json.dumps(warnings, ensure_ascii=False)}
评分明细：{json.dumps(score_details, ensure_ascii=False)}

请用JSON格式返回以下六个字符串字段：summary、detail、suggestion、long_term_risk、judgment、recommendation。
judgment 用不超过3句短句，分别说明主要风险、正向信息和当前人群需要采取的判断；不要重复食品类别或评分。recommendation 给出食用频率、注意事项或同类替代方向。
只返回JSON，不要输出Markdown。"""
    try:
        result = _json_content(_completion([{"role": "user", "content": prompt}], temperature=0.7))
        required = ("summary", "detail", "suggestion", "long_term_risk", "judgment", "recommendation")
        if not all(isinstance(result.get(key), str) and result[key].strip() for key in required):
            raise AIProviderError("AI 返回格式异常，请稍后重试")
        return {key: result[key].strip() for key in required}
    except (ProviderConfigurationError, AIProviderError):
        return build_fallback_report(
            food_category,
            health_score,
            risk_additives,
            user_type,
            warnings,
            beneficial_ingredients=beneficial_ingredients,
            avoid_warnings=avoid_warnings,
            score_details=score_details,
            ingredients=ingredients,
        )


def generate_daily_report(scan_count, avg_score, worst_food, foods_context):
    prompt = f"""你是专业营养师，请根据今日扫描数据生成饮食总结：
扫描次数：{scan_count}；平均分：{avg_score}；最低分食品：{worst_food}；详情：{foods_context}。
只返回包含 summary、suggestion、risk_alert 三个字符串字段的JSON。"""
    try:
        return _json_content(_completion([{"role": "user", "content": prompt}], temperature=0.7))
    except (ProviderConfigurationError, AIProviderError):
        return {
            "summary": f"今日共扫描 {scan_count} 次，平均健康评分 {avg_score} 分。",
            "suggestion": "明天可优先选择配料更简单、蔬果和优质蛋白更充足的食物。",
            "risk_alert": f"重点留意今日评分较低的食品：{worst_food}。",
        }


def _format_food(food):
    name = food.get("food_category", "未知食品")
    score = int(food.get("health_score") or 0)
    risks = "、".join(item.get("name", "") for item in food.get("risk_additives", [])[:5] if item.get("name")) or "无"
    warnings = "、".join(item.get("msg", item.get("name", "")) for item in food.get("group_warnings", [])[:3]) or "无"
    return f"{name}（{score}分），风险添加剂：{risks}，预警：{warnings}"


def build_compare_advice(food_a, food_b):
    score_a = int(food_a.get("health_score") or 0)
    score_b = int(food_b.get("health_score") or 0)
    if score_a == score_b:
        return "两款食品评分接近，可进一步比较风险添加剂数量、配料表长度和个人需避开的成分，优先选择配料更简单的一款。"
    better, other, label = (food_a, food_b, "A") if score_a > score_b else (food_b, food_a, "B")
    gap = abs(score_a - score_b)
    risks = better.get("risk_additives", [])
    reason = "检出的风险添加剂更少" if len(risks) <= len(other.get("risk_additives", [])) else "综合评分更高"
    return f"更推荐食品{label}，健康评分高出 {gap} 分，且{reason}。仍建议结合食用频率、份量和个人过敏或疾病限制选择。"


def generate_compare_advice(food_a, food_b):
    prompt = (
        "你是专业营养师，请对比以下两款食品，给出150字以内的健康建议，"
        f"指出哪款更健康及具体原因：\n食品A：{_format_food(food_a)}\n食品B：{_format_food(food_b)}。"
    )
    try:
        return _completion([{"role": "user", "content": prompt}], temperature=0.7, max_tokens=300)[:150]
    except (ProviderConfigurationError, AIProviderError):
        return build_compare_advice(food_a, food_b)


def generate_short_suggestion(categories, risk_items, avg_score, scan_count, period_label="今日"):
    category_text = "、".join(categories[:5]) if categories else "无记录"
    risk_text = "、".join(item.get("name", "") for item in risk_items[:3] if item.get("name")) or "无"
    prompt = (
        f"{period_label}饮食扫描{scan_count}次，平均分{avg_score}分，品类包括{category_text}，"
        f"风险成分：{risk_text}。请给出100到150字的亲切饮食建议，只返回正文。"
    )
    try:
        return _completion([{"role": "user", "content": prompt}], temperature=0.7, max_tokens=300)
    except (ProviderConfigurationError, AIProviderError):
        return f"{period_label}共扫描 {scan_count} 次，平均 {avg_score} 分。建议继续减少高风险成分较多的食品，搭配新鲜蔬果、全谷物和优质蛋白。"


def generate_wiki_entry(name):
    prompt = f"""你是专业食品安全研究员，请介绍食品添加剂「{name}」。严格按JSON返回这些字段：
name, alias(数组), category, origin, mechanism, controversy, usage, common_in, adi,
intake_status, risk_level(1到3数字), risk_desc, warning, special_groups(数组)。不要输出Markdown。"""
    return _json_content(_completion([{"role": "user", "content": prompt}], temperature=0.3, max_tokens=900))


def generate_chat_answer(question, history=None, user_type="普通人群", context=None):
    safe_history = []
    for item in (history or [])[-8:]:
        role = item.get("role")
        content = (item.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            safe_history.append({"role": role, "content": content[:600]})

    system_prompt = (
        "你是食安雷达里的 AI 营养师，只回答食品安全、配料表、食品添加剂、营养选择和特殊人群饮食风险。"
        "先给一句结论，再用短段说明原因，最后给1到3条做法。不要使用Markdown，总字数260字以内。"
        "不要替代医生诊断；涉及急性过敏、疾病治疗或用药时建议咨询医生。"
    )
    messages = [{"role": "system", "content": system_prompt}, *safe_history]
    context_text = json.dumps(context or {}, ensure_ascii=False)
    messages.append({
        "role": "user",
        "content": (
            f"用户人群类型：{user_type or '普通人群'}\n"
            f"当前扫描结果（只能依据这些信息回答）：{context_text}\n"
            f"问题：{question}\n"
            "回答必须明确引用当前食品的评分、风险成分或人群信息；如果上下文没有相关信息，直接说明暂未识别到，不要编造。"
        ),
    })
    return _completion(messages, temperature=0.5, max_tokens=600)
