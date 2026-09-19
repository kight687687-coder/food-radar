from score import score_ingredients


def test_high_risk_additive_reduces_score_and_is_reported():
    result = score_ingredients(["水", "阿斯巴甜"])

    assert result["health_score"] < 100
    assert any(item["name"] == "阿斯巴甜" for item in result["risk_additives"])


def test_scoring_works_without_database_configuration():
    result = score_ingredients(["水", "白砂糖", "维生素C"], group_type="普通人群")

    assert 0 <= result["health_score"] <= 100
    assert isinstance(result["beneficial_ingredients"], list)
    assert "group_extra_penalty" in result


def test_avoid_option_ids_are_stable_csv_row_ids():
    result = score_ingredients(["谷氨酸钠"], avoid_ids=[1])

    assert result["avoid_warnings"]
    assert result["avoid_warnings"][0]["name"] == "味精"
