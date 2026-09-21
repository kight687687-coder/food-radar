def _client():
    import app as app_module

    app_module.app.config.update(TESTING=True)
    return app_module, app_module.app.test_client()


def test_health_imports_without_database_or_provider_keys():
    _, client = _client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json()["data"]["status"] == "ok"


def test_history_and_daily_have_compatible_empty_state_without_database():
    _, client = _client()

    history = client.get("/history?user_id=1")
    daily = client.get("/daily?user_id=1")

    assert history.get_json()["data"] == {"list": [], "total": 0}
    assert daily.get_json()["data"]["scan_count"] == 0
    assert daily.get_json()["data"]["daily_score"] == 0


def test_analyze_validates_missing_image():
    _, client = _client()

    response = client.post("/analyze", json={})

    assert response.status_code == 400
    assert response.get_json()["code"] == 400
    assert "image" in response.get_json()["msg"]


def test_parse_ingredients_removes_nutrition_claims_and_splits_amounts():
    app_module, _ = _client()

    text = (
        "配料表：生牛乳添加量≥92%白砂糖添加量≤7%每百克含活性乳酸菌（出厂时）\n"
        "水、乳粉、营养成分表：能量 320千焦 蛋白质 3.2克 脂肪 3.6克\n"
        "本产品含有乳制品 原信息：含乳制品 单 双 项"
    )

    assert app_module._parse_ingredients(text) == ["生牛乳", "白砂糖", "水", "乳粉"]


def test_parse_ingredients_keeps_real_single_character_ingredients():
    app_module, _ = _client()

    assert app_module._parse_ingredients("配料：水、糖、盐、维生素C、钠、能量 120 千焦") == [
        "水", "糖", "盐", "维生素C"
    ]


def test_analyze_preserves_response_contract_and_skips_optional_persistence(monkeypatch):
    app_module, client = _client()
    expected = {
        "ingredients": "水,白砂糖",
        "food_category": "饮料",
        "health_score": 90,
        "risk_count": 0,
        "risk_additives": [],
        "group_warnings": [],
        "beneficial_ingredients": [],
        "beneficial_bonus": 0,
        "avoid_warnings": [],
        "stacking_penalty": 0,
        "ingredients_count_penalty": 0,
        "ai_report": {"summary": "基础报告"},
    }
    monkeypatch.setattr(app_module, "_run_analysis_pipeline", lambda *args, **kwargs: expected.copy())
    monkeypatch.setattr(app_module, "save_scan", lambda result, body: None)

    response = client.post("/analyze", json={"image": "ZmFrZQ==", "user_id": 1})

    assert response.status_code == 200
    assert response.get_json()["data"]["health_score"] == 90
    assert "scan_id" not in response.get_json()["data"]


def test_ai_compare_has_deterministic_fallback_without_key():
    _, client = _client()

    response = client.post("/api/ai-compare", json={
        "food_a": {"food_category": "食品A", "health_score": 90, "risk_additives": []},
        "food_b": {"food_category": "食品B", "health_score": 60, "risk_additives": [{"name": "测试"}]},
    })

    assert response.status_code == 200
    assert "食品A" in response.get_json()["data"]["advice"]


def test_ai_chat_returns_safe_configuration_message_without_key():
    _, client = _client()

    response = client.post("/api/ai-chat", json={"question": "怎么看配料表？"})

    assert response.status_code == 503
    assert response.get_json()["code"] == 503
    assert "DEEPSEEK_API_KEY" in response.get_json()["msg"]


def test_wiki_route_keeps_mini_program_contract_without_database(monkeypatch):
    app_module, client = _client()
    monkeypatch.setattr(app_module, "generate_wiki_entry", lambda name: {"name": name, "risk_level": 1})

    response = client.post("/api/wiki-query", json={"name": "测试添加剂"})

    assert response.status_code == 200
    assert response.get_json() == {
        "success": True,
        "data": {"name": "测试添加剂", "risk_level": 1},
        "source": "deepseek",
    }
