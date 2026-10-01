"""Phase 4 集成预测器测试。

fit_model=False 快速测试法规兜底/库外拒判/人群作用域逻辑（不加载模型）；
端到端全管线验证（含 TabICLv2）在 scripts/eval_tabicl.py --pipeline 独立执行。
"""

from __future__ import annotations

import pytest

import risk_predictor as rp


@pytest.fixture(scope="module")
def rule_only():
    """不加载模型的规则分支预测器（法规兜底 + 库外拒判可完整测试）。"""
    return rp.RiskPredictor(fit_model=False)


class TestRegulatoryOverride:
    """⑤ 法规兜底：csv forbidden_for 硬约束最高优先级。"""

    def test_forbidden_group_hits_high(self, rule_only):
        result = rule_only.predict("阿斯巴甜", "儿童")
        assert result["label"] == "high"
        assert result["source"] == "regulatory"
        assert result["confidence"] == 1.0
        assert "法规明确禁用" in result["reason"]

    def test_risk_only_not_overridden(self, rule_only):
        """亚硝酸钠 reason 为风险描述（无禁用表述），按确认口径不覆盖为 high。"""
        result = rule_only.predict("亚硝酸钠", "儿童")
        assert result["source"] != "regulatory"

    def test_scope_constraint_no_spillover(self, rule_only):
        """亚人群作用域约束：糖精钠禁忌人群为儿童（婴儿食品禁用映射），
        孕妇不受法规兜底覆盖，不因亚人群/相邻人群风险扩散为 high。"""
        result = rule_only.predict("糖精钠", "孕妇")
        assert result["source"] != "regulatory" or result["label"] != "high"

    def test_no_regulatory_high_for_unrelated_group(self, rule_only):
        """苯丙酮尿症患者禁忌链不扩散：普通人群无 csv 禁忌边。"""
        result = rule_only.predict("阿斯巴甜", "普通人群")
        assert result["source"] != "regulatory"

    def test_regulatory_reason_cites_evidence(self, rule_only):
        result = rule_only.predict("苋菜红", "儿童")  # 「多国已禁用」ban_high
        assert result["label"] == "high"
        assert result["source"] == "regulatory"
        assert "多国已禁用" in result["reason"]


class TestUnknownRejection:
    """④ 拒判门控：库外成分直接拒判，不强制泛化。"""

    def test_unknown_additive_rejected(self, rule_only):
        result = rule_only.predict("二甲基二硫代氨基甲酸锌XYZ", "儿童")
        assert result["label"] == "unknown"
        assert result["source"] == "rejected"
        assert "不在知识库" in result["reason"]

    def test_alias_still_resolves(self, rule_only):
        result = rule_only.predict("甜味素", "儿童")  # 阿斯巴甜别名
        assert result["source"] == "regulatory"
        assert result["label"] == "high"


class TestExplanationChains:
    """可解释性：法规兜底结果附带图谱解释链。"""

    def test_forbidden_result_has_chains(self, rule_only):
        result = rule_only.predict("阿斯巴甜", "儿童")
        assert result["explanation_chains"]  # warns 高预警链等

    def test_chains_absent_silently(self, rule_only):
        """无解释链的成分不报错（宁缺勿滥）。"""
        result = rule_only.predict("阿斯巴甜", "儿童")
        assert isinstance(result["explanation_chains"], list)


class TestSchema:
    def test_result_schema(self, rule_only):
        result = rule_only.predict("阿斯巴甜", "儿童")
        for key in ("additive", "group", "label", "source", "confidence",
                    "ood_distance", "reason", "explanation_chains"):
            assert key in result
        assert result["label"] in ("high", "medium", "low", "unknown")

    def test_batch_matches_single(self, rule_only):
        pairs = [("阿斯巴甜", "儿童"), ("糖精钠", "孕妇")]
        batched = rule_only.predict_batch(pairs)
        for pair, result in zip(pairs, batched):
            assert result == rule_only.predict(*pair)

    def test_invalid_group_no_crash(self, rule_only):
        result = rule_only.predict("阿斯巴甜", "外星人群")
        assert result["label"] == "unknown"
        assert result["source"] == "rejected"
