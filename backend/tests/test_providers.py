import pytest


def test_baidu_ocr_requires_both_credentials():
    from ocr import ProviderConfigurationError, ocr_image

    with pytest.raises(ProviderConfigurationError, match="百度 OCR"):
        ocr_image(image_base64="ZmFrZQ==", retries=0)


def test_deepseek_client_is_created_lazily_and_requires_key():
    from ai_analyze import ProviderConfigurationError, get_deepseek_client

    with pytest.raises(ProviderConfigurationError, match="DeepSeek"):
        get_deepseek_client()


def test_fallback_report_has_complete_frontend_contract():
    from ai_analyze import build_fallback_report

    report = build_fallback_report(
        food_category="饮料",
        health_score=65,
        risk_additives=[{"name": "阿斯巴甜", "risk_level": "高"}],
        user_type="儿童",
        warnings=[{"msg": "注意甜味剂摄入"}],
    )

    assert set(report) == {
        "summary", "detail", "suggestion", "long_term_risk",
        "judgment", "recommendation",
    }
    assert all(isinstance(value, str) and value for value in report.values())


def test_fallback_report_contains_staged_fields_and_context():
    from ai_analyze import build_fallback_report

    report = build_fallback_report(
        food_category="能量饮料",
        health_score=58,
        risk_additives=[{"name": "咖啡因", "risk_level": "中", "deduct_score": 10}],
        user_type="儿童",
        warnings=[{"msg": "儿童需关注咖啡因"}],
        beneficial_ingredients=[{"nutrient": "维生素C", "benefit_category": "维生素类"}],
        avoid_warnings=[{"name": "咖啡因敏感", "warning_msg": "已命中忌口"}],
        score_details={"group_extra_penalty": 5},
        ingredients=["水", "咖啡因", "维生素C"],
    )

    assert set(report) == {
        "summary", "detail", "suggestion", "long_term_risk",
        "judgment", "recommendation",
    }
    assert all(isinstance(value, str) and value.strip() for value in report.values())
    assert "儿童" in report["judgment"] or "儿童" in report["detail"]


def test_generate_report_prompt_contains_benefits_avoids_and_score_details(monkeypatch):
    import ai_analyze

    captured = {}

    def fake_completion(messages, **kwargs):
        captured["content"] = messages[0]["content"]
        return '{"summary":"摘要","detail":"详情","suggestion":"建议","long_term_risk":"长期","judgment":"判断","recommendation":"替代"}'

    monkeypatch.setattr(ai_analyze, "_completion", fake_completion)
    ai_analyze.generate_report(
        "饮料", 58, [{"name": "咖啡因"}], "儿童", [{"msg": "儿童提醒"}],
        beneficial_ingredients=[{"nutrient": "维生素C"}],
        avoid_warnings=[{"name": "咖啡因敏感"}],
        score_details={"group_extra_penalty": 5},
        ingredients=["水", "咖啡因", "维生素C"],
    )

    assert "维生素C" in captured["content"]
    assert "咖啡因敏感" in captured["content"]
    assert "group_extra_penalty" in captured["content"]


def test_generate_report_falls_back_when_provider_fails(monkeypatch):
    import ai_analyze

    class BrokenCompletions:
        def create(self, **kwargs):
            raise RuntimeError("provider unavailable")

    class BrokenClient:
        class Chat:
            completions = BrokenCompletions()

        chat = Chat()

    monkeypatch.setattr(ai_analyze, "get_deepseek_client", lambda: BrokenClient())

    report = ai_analyze.generate_report("零食", 80, [], "普通人群", [])

    assert report["summary"]
    assert "80" in report["summary"] or "80" in report["detail"]
