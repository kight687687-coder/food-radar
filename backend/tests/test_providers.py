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

    assert set(report) == {"summary", "detail", "suggestion", "long_term_risk"}
    assert all(isinstance(value, str) and value for value in report.values())


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
