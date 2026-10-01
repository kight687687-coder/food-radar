"""标签校准与法规兜底共享的 R1 证据复核规则。

单一事实源：scripts/auto_calibrate_labels.py（标签生成）与
risk_predictor.py（运行时法规兜底）共用同一套判定，
确保「标签口径」与「兜底覆盖行为」永远一致。

R1 证据分级（基于 forbidden 边的 reason 文本，2026-10-01 用户确认口径）：
- 明确禁用（成分/监管层面，如「多国已禁用」「部分食品中禁用」）
  → ban_high → 硬约束覆盖 high
- 禁用主语为专属亚人群/特定场景（苯丙酮尿症患者禁用；婴儿食品禁用），
  查询人群在映射范围内才保持 high（人群作用域约束，避免亚人群风险扩散）
- 限制/限量/慎用/注意表述 → caution → 不覆盖（交模型/标签）
- 仅风险描述或中性说明 → risk_only → 不覆盖（风险描述不直接升格 high）
"""

from __future__ import annotations

BAN_WORDS = ("禁用", "禁止")
CAUTION_WORDS = ("限制", "限量", "慎用", "注意", "避免", "不宜")

# 亚人群禁忌链 → 九大人群适用性映射（人工确认口径，可修订）
SUBGROUP_APPLICABILITY = {
    "苯丙酮尿症患者": "与「儿童」「孕妇」相关（苯丙氨酸饮食管理主要在儿童期；母源性苯丙酮尿症需孕期管控）",
    "哮喘者": "专属敏感人群，不映射九大人群",
    "甲状腺功能异常者": "专属疾病人群，不映射九大人群",
    "敏感人群": "泛化敏感表述，不映射九大人群",
    "婴幼儿": "与「儿童」部分重叠（婴幼儿属儿童范畴）",
    "胎儿": "与「孕妇」对应（母体暴露途径）",
}
SUBGROUP_TO_GROUPS = {
    "婴幼儿": {"儿童"},
    "胎儿": {"孕妇"},
    "苯丙酮尿症患者": {"儿童", "孕妇"},
}

VERDICT_TO_LABEL = {"ban_high": "high", "subgroup_scoped": "medium", "caution": "medium", "risk_only": "medium"}


def classify_forbidden_evidence(reason: str, group: str) -> tuple[str, str]:
    """R1 证据分级：返回 (判定, 说明)。判定 ∈ ban_high / subgroup_scoped / caution / risk_only。"""
    if "苯丙酮尿症患者禁用" in reason:
        if group in SUBGROUP_TO_GROUPS["苯丙酮尿症患者"]:
            return "ban_high", "苯丙酮尿症患者禁忌链与该人群相关（儿童期饮食管理／母源性苯丙酮尿症孕期管控），保持 high"
        return "subgroup_scoped", "禁用表述仅作用于苯丙酮尿症患者（专属亚人群）"
    if "婴儿食品禁用" in reason:
        if group == "儿童":
            return "ban_high", "婴儿食品禁用场景与儿童人群重叠（婴幼儿属儿童范畴）"
        return "subgroup_scoped", "禁用表述仅指向婴儿食品场景，与该人群无直接对应"
    if any(word in reason for word in BAN_WORDS):
        return "ban_high", "文本含明确禁用/禁止表述"
    if any(word in reason for word in CAUTION_WORDS):
        return "caution", "文本为限制/限量/慎用/注意表述，非明确禁用"
    return "risk_only", "文本无明确禁用表述（仅风险描述或中性说明）"
