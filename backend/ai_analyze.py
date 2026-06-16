import json
from openai import OpenAI
from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)


def generate_report(food_category, health_score, risk_additives, user_type, warnings):
    """调用 DeepSeek 生成分析报告"""
    risk_text = json.dumps(risk_additives, ensure_ascii=False)
    warnings_text = json.dumps(warnings, ensure_ascii=False)

    prompt = f"""你是专业营养师和食品安全专家，请根据以下信息生成分析报告：

食品类别：{food_category}
健康评分：{health_score}
风险添加剂：{risk_text}
人群类型：{user_type or "无"}
预警信息：{warnings_text}

请用JSON格式返回：
{{
  "summary": "一句话总结",
  "detail": "详细分析",
  "suggestion": "建议",
  "long_term_risk": "长期食用风险"
}}
只返回JSON不要其他文字"""

    resp = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )

    content = resp.choices[0].message.content.strip()
    # 去除可能的 markdown 代码围栏
    if content.startswith("```"):
        lines = content.split("\n", 1)
        if len(lines) > 1:
            content = lines[1]
        if content.endswith("```"):
            content = content[:-3].rstrip()

    return json.loads(content)


def generate_daily_report(scan_count, avg_score, worst_food, foods_context):
    """生成每日总结报告"""
    prompt = f"""你是专业营养师，请根据以下今日扫描数据生成饮食总结：

今日扫描次数：{scan_count}
今日平均健康评分：{avg_score}
今日最差食品：{worst_food}
扫描详情：{foods_context}

请用JSON格式返回：
{{
  "summary": "今日饮食总结",
  "suggestion": "明日饮食建议",
  "risk_alert": "需要注意的问题"
}}
只返回JSON不要其他文字"""

    resp = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )

    content = resp.choices[0].message.content.strip()
    if content.startswith("```"):
        lines = content.split("\n", 1)
        if len(lines) > 1:
            content = lines[1]
        if content.endswith("```"):
            content = content[:-3].rstrip()

    return json.loads(content)


def generate_compare_advice(food_a, food_b):
    """生成食品对比建议（150字以内）"""
    def _fmt(f):
        name = f.get("food_category", "未知")
        score = f.get("health_score", 0)
        risks = f.get("risk_additives", [])
        warnings = f.get("group_warnings", [])
        risk_names = "、".join([r.get("name", "") for r in risks[:5]]) or "无"
        warn_names = "、".join([w.get("msg", w.get("name", "")) for w in warnings[:3]]) or "无"
        return f"{name}（{score}分），风险添加剂：{risk_names}，预警：{warn_names}"

    prompt = f"""你是专业营养师，请对比以下两款食品，给出150字以内的健康建议，指出哪款更健康及具体原因：

食品A：{_fmt(food_a)}
食品B：{_fmt(food_b)}

只返回建议文字，不要JSON，150字以内。"""

    resp = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=300,
    )

    return resp.choices[0].message.content.strip()[:150]


def generate_short_suggestion(categories, risk_items, avg_score, scan_count, period_label="今日"):
    """生成饮食建议（100-150字）"""
    cat_text = "、".join(categories[:5]) if categories else "无记录"
    risk_text = "、".join([r["name"] for r in risk_items[:3]]) if risk_items else "无"

    prompt = f"""{period_label}饮食扫描：{scan_count}次，平均分{avg_score}分，品类包括{cat_text}。
风险成分：{risk_text}。
请给出饮食建议（100-150字左右），面向注重健康的消费者，语气亲切，建议应包含：亮点总结、待改进方面、明日饮食方向。只返回建议文字，不要JSON。"""

    resp = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=300,
    )

    return resp.choices[0].message.content.strip()


def generate_wiki_entry(name):
    """调用 DeepSeek 生成添加剂百科条目"""
    prompt = f"""你是专业食品安全研究员，请介绍食品添加剂「{name}」。严格按以下JSON格式返回，不要输出任何其他内容，不要有markdown格式：
{{
  "name": "标准中文名",
  "alias": ["常见别称1", "常见别称2"],
  "category": "分类（防腐剂/甜味剂/色素/增稠剂/抗氧化剂/乳化剂/香精香料之一）",
  "origin": "来源与合成方式，说明天然还是人工合成，制备工艺，2-3句",
  "mechanism": "作用机制，说明在食品中具体怎么发挥作用，原理是什么，2-3句",
  "controversy": "安全争议，已知健康争议、相关研究结论、各国监管态度差异，2-3句，若无争议则如实说明",
  "usage": "主要用途",
  "common_in": "常见于哪些具体食品，列举4-6种",
  "adi": "ADI值，格式如'0-5 mg/kg体重/天'，若无限制则写'无需规定'",
  "intake_status": "普通人日常实际摄入量与ADI的关系，2句",
  "risk_level": 风险等级数字，1为低风险，2为中风险，3为高风险,
  "risk_desc": "风险等级一句话说明",
  "warning": "具体注意事项",
  "special_groups": ["需注意的特殊人群，如儿童、孕妇、过敏者等"]
}}"""

    resp = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=800,
    )

    content = resp.choices[0].message.content.strip()
    if content.startswith("```"):
        lines = content.split("\n", 1)
        if len(lines) > 1:
            content = lines[1]
        if content.endswith("```"):
            content = content[:-3].rstrip()

    return json.loads(content)


def generate_chat_answer(question, history=None, user_type="普通人群"):
    """AI 营养师问答，限定在食品安全和配料表相关场景。"""
    history = history or []
    safe_history = []
    for item in history[-8:]:
        role = item.get("role")
        content = (item.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            safe_history.append({"role": role, "content": content[:600]})

    system_prompt = (
        "你是食安雷达里的 AI 营养师，只回答食品安全、配料表、食品添加剂、营养选择、"
        "特殊人群饮食风险相关问题。你的表达要像真人营养师在微信里解释问题：通俗、自然、少术语。"
        "回答结构固定为：先用1句话给结论；再用2到4个短段说明原因和注意点；最后给1到3条具体做法。"
        "不要使用Markdown格式，不要使用星号、井号、表格、代码块，不要写“以下是具体分析”这类报告腔。"
        "不要堆很多标准名和缩写；如果必须提到国标或ADI，用一句人话解释即可。"
        "每段尽量不超过60个字，总字数控制在260字以内。"
        "不要替代医生诊断；遇到疾病治疗、用药、急性过敏反应等问题，要建议咨询医生。"
        "如果问题明显无关，请礼貌说明只能回答食品和营养安全相关内容。"
    )

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(safe_history)
    messages.append({
        "role": "user",
        "content": f"用户人群类型：{user_type or '普通人群'}\n问题：{question}",
    })

    resp = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=messages,
        temperature=0.5,
        max_tokens=600,
    )

    return resp.choices[0].message.content.strip()
