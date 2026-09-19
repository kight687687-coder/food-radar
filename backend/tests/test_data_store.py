from data_store import load_reference_data


def test_load_reference_data_contains_all_reference_sets():
    data = load_reference_data(force_reload=True)

    assert data.additives
    assert data.group_warnings
    assert data.avoid_options
    assert data.beneficial_ingredients
    assert any(item.name == "阿斯巴甜" for item in data.additives)


def test_aliases_and_keywords_support_slash_separated_csv_values():
    data = load_reference_data(force_reload=True)

    aspartame = next(item for item in data.additives if item.name == "阿斯巴甜")
    msg = next(item for item in data.avoid_options if item.name == "味精")

    assert "E951" in aspartame.aliases
    assert "谷氨酸钠" in msg.keywords
    assert msg.id >= 1
