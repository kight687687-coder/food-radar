"""Phase 5 表达层测试。

四类解释（模型结果 / 法规覆盖 / 拒判 / unknown 成分）+ 决策隔离铁律
（表达层不得改变 label/source/confidence/explanation_chain）+ DeepSeek
回退 + /api/v2/risk 路由契约与旧接口兼容性。

fit_model=False 快速测试法规/库外分支；模型分支用构造的 prediction dict
测组装逻辑（不加载 TabICLv2，端到端全管线见 scripts/eval_tabicl.py）。
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

import explain
import risk_predictor as rp


def assert_decision_isolated(prediction: dict, explanation: dict) -> None:
    """决策隔离铁律：解释前后决策字段逐位一致，表达层无权修改。"""
    assert explanation["risk_level"] == prediction["label"]
    assert explanation["source"] == prediction["source"]
    assert explanation["confidence"] == prediction["confidence"]
    assert explanation["explanation_chain"] == list(prediction.get("explanation_chains") or [])


@pytest.fixture(scope="module")
def rule_only():
    return rp.RiskPredictor(fit_model=False)


# ---- 测试用 prediction 构造（模型/低置信度拒判分支）----

MODEL_PREDICTION = {
    "additive": "柠檬酸", "group": "普通人群",
    "label": "low", "source": "model",
    "confidence": 0.82, "ood_distance": 1.2,
    "reason": "TabICLv2 少样本泛化预测 low（置信度 0.82）",
    "explanation_chains": ["柠檬酸 -[warns(低)]-> 普通人群"],
}

LOW_CONFIDENCE_PREDICTION = {
    "additive": "糖精钠", "group": "孕妇",
    "label": "unknown", "source": "rejected",
    "confidence": 0.57, "ood_distance": 3.1,
    "reason": "模型置信度不足（0.57 < 0.75），拒判",
    "explanation_chains": [],
}


class TestModelExplanation:
    """① 模型结果解释（source=model）。"""

    def test_schema(self):
        exp = explain.build_explanation(MODEL_PREDICTION)
        for key in ("risk_level", "source", "confidence", "explanation_chain", "reject_reason"):
            assert key in exp
        assert exp["risk_level"] == "low"
        assert exp["source"] == "model"
        assert exp["confidence"] == pytest.approx(0.82)
        assert_decision_isolated(MODEL_PREDICTION, exp)

    def test_reject_reason_none_when_not_rejected(self):
        exp = explain.build_explanation(MODEL_PREDICTION)
        assert exp["reject_reason"] is None

    def test_narrative_mentions_confidence_and_level(self):
        exp = explain.build_explanation(MODEL_PREDICTION)
        assert "低风险" in exp["narrative"]
        assert "82%" in exp["narrative"]
        assert "知识图谱" in exp["narrative"]


class TestRegulatoryExplanation:
    """② 法规覆盖解释（source=regulatory，真实跑兜底分支）。"""

    def test_regulatory_explanation(self, rule_only):
        prediction = rule_only.predict("苋菜红", "儿童")  # 「多国已禁用」ban_high
        exp = explain.build_explanation(prediction)
        assert exp["risk_level"] == "high"
        assert exp["source"] == "regulatory"
        assert exp["confidence"] == 1.0
        assert exp["reject_reason"] is None
        assert "多国已禁用" in exp["reason"]
        assert_decision_isolated(prediction, exp)

    def test_regulatory_narrative_cites_law(self, rule_only):
        prediction = rule_only.predict("苋菜红", "儿童")
        exp = explain.build_explanation(prediction)
        assert "法规" in exp["narrative"]
        assert "高风险" in exp["narrative"]

    def test_regulatory_chain_present(self, rule_only):
        prediction = rule_only.predict("阿斯巴甜", "儿童")
        exp = explain.build_explanation(prediction)
        assert exp["explanation_chain"]
        assert_decision_isolated(prediction, exp)


class TestRejectedExplanation:
    """③ 拒判解释（低置信度 / 模型未加载等）。"""

    def test_low_confidence_rejection(self):
        exp = explain.build_explanation(LOW_CONFIDENCE_PREDICTION)
        assert exp["risk_level"] == "unknown"
        assert exp["source"] == "rejected"
        assert exp["reject_reason"] == LOW_CONFIDENCE_PREDICTION["reason"]
        assert "证据不足" in exp["narrative"]
        assert_decision_isolated(LOW_CONFIDENCE_PREDICTION, exp)

    def test_unloaded_model_rejection(self, rule_only):
        """fit_model=False 下模型分支明确拒判，解释诚实给出原因。"""
        prediction = rule_only.predict("柠檬酸", "普通人群")
        exp = explain.build_explanation(prediction)
        assert exp["risk_level"] == "unknown"
        assert exp["source"] == "rejected"
        assert exp["reject_reason"]
        assert_decision_isolated(prediction, exp)

    def test_rejected_narrative_advises_verification(self):
        exp = explain.build_explanation(LOW_CONFIDENCE_PREDICTION)
        assert "拒判" in exp["narrative"]
        assert "建议" in exp["narrative"]


class TestUnknownAdditiveExplanation:
    """④ unknown 成分解释（库外成分拒判，真实跑门控分支）。"""

    def test_unknown_additive_rejected_explained(self, rule_only):
        prediction = rule_only.predict("二甲基二硫代氨基甲酸锌XYZ", "儿童")
        exp = explain.build_explanation(prediction)
        assert exp["risk_level"] == "unknown"
        assert exp["source"] == "rejected"
        assert "不在知识库" in exp["reject_reason"]
        assert_decision_isolated(prediction, exp)

    def test_unknown_additive_narrative(self, rule_only):
        prediction = rule_only.predict("二甲基二硫代氨基甲酸锌XYZ", "儿童")
        exp = explain.build_explanation(prediction)
        assert "证据不足" in exp["narrative"]
        assert "不在知识库" in exp["narrative"]

    def test_unknown_additive_no_fake_chain(self, rule_only):
        """库外成分没有图谱节点，解释链必须为空（宁缺勿滥）。"""
        prediction = rule_only.predict("二甲基二硫代氨基甲酸锌XYZ", "儿童")
        exp = explain.build_explanation(prediction)
        assert exp["explanation_chain"] == []


class TestNarrateFallback:
    """DeepSeek 不可用时的确定性模板回退（决策不受影响）。"""

    @pytest.fixture
    def predictions(self, rule_only):
        return [
            rule_only.predict("苋菜红", "儿童"),          # regulatory
            dict(MODEL_PREDICTION),                       # model
            rule_only.predict("二甲基二硫代氨基甲酸锌XYZ", "儿童"),  # unknown 成分
        ]

    def test_failure_keeps_template(self, monkeypatch, predictions):
        """DeepSeek 调用抛异常 → 静默回退模板 narrative，永不向上抛。"""
        def boom():
            raise RuntimeError("网络不可达")
        monkeypatch.setattr(explain, "_deepseek_client", boom)
        explanations = [explain.build_explanation(p) for p in predictions]
        result = explain.narrate_explanations(explanations, "儿童")
        assert result is explanations  # 原列表原顺序
        for before, after in zip(explanations, result):
            assert after["narrative"] == before["narrative"]  # 模板保留

    def test_unconfigured_key_falls_back(self, monkeypatch, predictions):
        monkeypatch.setattr("config.DEEPSEEK_API_KEY", "")
        explanations = [explain.build_explanation(p) for p in predictions]
        before = [e["narrative"] for e in explanations]
        explain.narrate_explanations(explanations, "儿童")
        assert [e["narrative"] for e in explanations] == before

    def test_success_enhances_narrative_only(self, monkeypatch, predictions):
        """DeepSeek 成功返回 → 只覆写 narrative，决策字段逐位不变。"""
        def fake_client():
            content = json.dumps([
                {"additive": p["additive"], "narrative": f"{p['additive']}的DeepSeek解读"}
                for p in predictions
            ], ensure_ascii=False)
            message = SimpleNamespace(content="```json\n" + content + "\n```")
            choice = SimpleNamespace(message=message)
            response = SimpleNamespace(choices=[choice])
            chat = SimpleNamespace(completions=SimpleNamespace(create=lambda **kw: response))
            return SimpleNamespace(chat=chat)
        monkeypatch.setattr(explain, "_deepseek_client", fake_client)

        explanations = [explain.build_explanation(p) for p in predictions]
        before = [(e["risk_level"], e["source"], e["confidence"]) for e in explanations]
        explain.narrate_explanations(explanations, "儿童")
        for exp, prediction, was in zip(explanations, predictions, before):
            assert exp["narrative"] == f"{prediction['additive']}的DeepSeek解读"
            assert (exp["risk_level"], exp["source"], exp["confidence"]) == was
            assert_decision_isolated(prediction, exp)

    def test_malformed_json_keeps_template(self, monkeypatch, predictions):
        def fake_client():
            message = SimpleNamespace(content="这不是JSON")
            choice = SimpleNamespace(message=message)
            response = SimpleNamespace(choices=[choice])
            chat = SimpleNamespace(completions=SimpleNamespace(create=lambda **kw: response))
            return SimpleNamespace(chat=chat)
        monkeypatch.setattr(explain, "_deepseek_client", fake_client)
        explanations = [explain.build_explanation(p) for p in predictions]
        before = [e["narrative"] for e in explanations]
        explain.narrate_explanations(explanations, "儿童")
        assert [e["narrative"] for e in explanations] == before

    def test_empty_input(self):
        assert explain.narrate_explanations([], "儿童") == []


class TestV2Route:
    """/api/v2/risk 路由契约 + 旧接口兼容性。"""

    @pytest.fixture(scope="class")
    def client(self):
        """class 级共享：手动 patch（monkeypatch 是 function 级，不能用于 class 级），
        fit_model=False 跳过模型加载，narrate 直通不走网络。"""
        import app as app_module
        rule_only = rp.RiskPredictor(fit_model=False)
        original_predictor = app_module.get_predictor
        original_narrate = app_module.narrate_explanations
        app_module.get_predictor = lambda: rule_only
        app_module.narrate_explanations = lambda explanations, group_type: explanations
        app_module.app.config["TESTING"] = True
        yield app_module.app.test_client()
        app_module.get_predictor = original_predictor
        app_module.narrate_explanations = original_narrate

    def test_regulatory_explanation_via_route(self, client):
        resp = client.post("/api/v2/risk", json={"ingredients": ["苋菜红"], "user_type": "儿童"})
        assert resp.status_code == 200
        payload = resp.get_json()
        assert payload["code"] == 200
        exp = payload["data"]["explanations"][0]
        assert exp["risk_level"] == "high"
        assert exp["source"] == "regulatory"
        assert exp["reject_reason"] is None
        assert payload["data"]["user_type"] == "儿童"
        assert payload["data"]["summary"]["high"] == 1

    def test_unknown_additive_via_route(self, client):
        resp = client.post(
            "/api/v2/risk",
            json={"ingredients": ["二甲基二硫代氨基甲酸锌XYZ"], "user_type": "儿童"},
        )
        assert resp.status_code == 200
        exp = resp.get_json()["data"]["explanations"][0]
        assert exp["risk_level"] == "unknown"
        assert "不在知识库" in exp["reject_reason"]

    def test_summary_counts(self, client):
        resp = client.post(
            "/api/v2/risk",
            json={"ingredients": ["苋菜红", "二甲基二硫代氨基甲酸锌XYZ"], "user_type": "儿童"},
        )
        summary = resp.get_json()["data"]["summary"]
        assert summary == {"total": 2, "high": 1, "medium": 0, "low": 0, "unknown": 1}

    def test_default_group_is_general(self, client):
        resp = client.post("/api/v2/risk", json={"ingredients": ["阿斯巴甜"]})
        assert resp.get_json()["data"]["user_type"] == "普通人群"

    def test_missing_ingredients_rejected(self, client):
        resp = client.post("/api/v2/risk", json={"user_type": "儿童"})
        assert resp.get_json()["code"] == 400

    def test_ingredients_must_be_list(self, client):
        resp = client.post("/api/v2/risk", json={"ingredients": "阿斯巴甜", "user_type": "儿童"})
        assert resp.get_json()["code"] == 400

    def test_blank_entries_filtered(self, client):
        resp = client.post("/api/v2/risk", json={"ingredients": ["  ", ""], "user_type": "儿童"})
        assert resp.get_json()["code"] == 400

    def test_legacy_routes_untouched(self, client):
        """旧接口零改动：所有旧端点仍注册在 v2 之上（向后兼容）。"""
        rules = {rule.rule for rule in client.application.url_map.iter_rules()}
        for legacy in ("/health", "/analyze", "/compare", "/history", "/daily",
                       "/api/ai-compare", "/api/ai-suggestion", "/api/ai-chat", "/api/wiki-query"):
            assert legacy in rules
        assert "/api/v2/risk" in rules
