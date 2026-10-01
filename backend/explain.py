"""Phase 5 表达层：把 RiskPredictor 决策结果转为可解释结构化输出 + DeepSeek 个性化解读。

铁律（与 Phase 5 确认口径一致）：
- 表达层不改变风险决策结果——risk_level / source / confidence 原样透传，
  单元测试断言「解释前后决策字段逐位一致」；
- 只负责解释：explanation_chain 来自图谱多跳链路（可解释性），
  narrative 由 DeepSeek 生成个性化人话解读，服务不可用时回退确定性模板，
  永不因表达层故障影响风险结论输出。

输出字段（确认口径）：
- risk_level: high / medium / low / unknown（拒判）
- source: regulatory（法规兜底）/ model（TabICLv2 泛化）/ rejected（拒判）
- confidence: 法规兜底为 1.0；模型为 softmax 最大概率；拒判为 0
- explanation_chain: 图谱解释链摘要列表（可能为空——宁缺勿滥）
- reject_reason: 拒判原因；非拒判为 None
"""

from __future__ import annotations

import json

from ai_analyze import ProviderConfigurationError

RISK_LEVEL_LABELS_ZH = {"high": "高风险", "medium": "中风险", "low": "低风险", "unknown": "未知（拒判）"}
SOURCE_LABELS_ZH = {
    "regulatory": "法规约束",
    "model": "知识图谱证据泛化",
    "rejected": "拒判（证据不足）",
}


def _chain_hint(explanation_chain: list[str]) -> str:
    """链路提示语（最多取两条，避免叙述冗长）。"""
    if not explanation_chain:
        return ""
    joined = "；".join(explanation_chain[:2])
    return f"图谱证据链：{joined}。"


def template_narrative(prediction: dict) -> str:
    """确定性模板叙述（DeepSeek 不可用时的回退，永远可用）。"""
    additive = prediction.get("additive") or "该成分"
    group = prediction.get("group") or "当前人群"
    label = prediction.get("label", "unknown")
    source = prediction.get("source", "rejected")
    reason = prediction.get("reason", "")
    level_zh = RISK_LEVEL_LABELS_ZH.get(label, label)
    chain_hint = _chain_hint(prediction.get("explanation_chains") or [])

    if source == "regulatory":
        return (
            f"依据法规约束，{additive} 对「{group}」属于明确禁忌场景，判定为{level_zh}。"
            f"{reason}{chain_hint}建议避免食用含该成分的食品。"
        )
    if source == "model":
        confidence = prediction.get("confidence", 0.0)
        return (
            f"综合知识图谱中的法规、证据强度与人群关联特征，"
            f"{additive} 对「{group}」的风险评估为{level_zh}（模型置信度 {confidence:.0%}）。"
            f"{chain_hint}该结论由表格基础模型基于专家标注知识少样本泛化得出。"
        )
    # rejected（低置信度 / OOD / 库外成分 / 无效人群）
    return (
        f"目前证据不足，无法对 {additive}（{group}）给出可靠的风险判断，已安全拒判。"
        f"原因：{reason}。建议进一步核验成分信息后再做决定。"
    )


def build_explanation(prediction: dict) -> dict:
    """决策结果 → 结构化解释（确定性、无网络依赖）。

    决策字段（label/source/confidence/explanation_chains/reason）逐位透传，
    表达层无权修改——测试断言此不变量。
    """
    return {
        "additive": prediction.get("additive"),
        "group": prediction.get("group"),
        "risk_level": prediction.get("label", "unknown"),
        "source": prediction.get("source", "rejected"),
        "confidence": prediction.get("confidence", 0.0),
        "explanation_chain": list(prediction.get("explanation_chains") or []),
        "reject_reason": prediction.get("reason") if prediction.get("source") == "rejected" else None,
        "reason": prediction.get("reason", ""),
        "narrative": template_narrative(prediction),
    }


def _deepseek_client():
    """独立 DeepSeek 客户端：trust_env=False 绕过系统失效代理（127.0.0.1:7892 坑）。"""
    import httpx
    from openai import OpenAI

    from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL  # noqa: F401

    if not DEEPSEEK_API_KEY:
        raise ProviderConfigurationError("DeepSeek 尚未配置（DEEPSEEK_API_KEY）")
    return OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        http_client=httpx.Client(trust_env=False, timeout=35.0),
    )


def narrate_explanations(explanations: list[dict], group_type: str) -> list[dict]:
    """DeepSeek 批量生成个性化解读；失败回退各自的模板 narrative（决策不受影响）。

    返回顺序与输入一致，仅覆写 narrative 字段。
    """
    if not explanations:
        return []
    from config import DEEPSEEK_MODEL

    facts = [
        {
            "additive": item["additive"],
            "risk_level": item["risk_level"],
            "source": item["source"],
            "confidence": round(item["confidence"], 2),
            "explanation_chain": item["explanation_chain"],
            "reject_reason": item["reject_reason"],
        }
        for item in explanations
    ]
    prompt = (
        "你是食品安全科普助手。以下 JSON 是「成分×人群」风险判定结果"
        f"（人群：{group_type}），风险等级由知识图谱与法规规则判定，"
        "你只负责解释，不得修改任何判定字段。\n"
        "请为每一条生成一段 60 字以内、通俗友好的中文解读（narrative 字段），"
        "高风险要说明规避建议，拒判要说明证据不足并建议人工核验。\n"
        f"以 JSON 数组输出，每项形如 {{\"additive\": \"...\", \"narrative\": \"...\"}}。\n"
        f"判定结果：{json.dumps(facts, ensure_ascii=False)}"
    )
    try:
        response = _deepseek_client().chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=6000,  # deepseek-v4-flash 是推理模型，Phase 1 经验：max_tokens 过小会因思维链占满而空输出
        )
        content = (response.choices[0].message.content or "").strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else ""
        if content.endswith("```"):
            content = content[:-3].rstrip()
        mapping = {item["additive"]: item["narrative"] for item in json.loads(content)}
        for item in explanations:
            enhanced = mapping.get(item["additive"])
            if enhanced:
                item["narrative"] = enhanced
    except Exception:
        # 表达层增强失败 → 保留模板 narrative，风险结论不受影响（永不向上抛）
        pass
    return explanations
