"""Deterministic food-ingredient scoring backed by repository CSV files."""

from collections import Counter

from data_store import load_reference_data


RISK_PENALTY = {"高": 20, "中": 10, "低": 5}
AVOID_PENALTY = 5
STACK_PENALTY = 8
STACK_THRESHOLD = 2

BENEFIT_BONUS = {
    "蛋白质类": 5,
    "膳食纤维类": 5,
    "维生素类": 4,
    "矿物质类": 4,
    "脂肪酸类": 4,
    "氨基酸类": 3,
    "益生菌类": 3,
    "抗氧化类": 3,
    "植物化学物类": 2,
    "代糖类": 2,
    "功能成分": 2,
}
BENEFIT_MAX_BONUS = 25

BENEFICIAL_ADDITIVE_NAMES = {
    "维生素C", "维生素E", "β-胡萝卜素", "茶多酚", "姜黄素", "植酸",
    "D-异抗坏血酸钠", "抗坏血酸钠", "牛磺酸", "卵磷脂", "赤藓糖醇",
    "木糖醇", "麦芽糖醇", "山梨糖醇", "甜菊糖苷", "罗汉果甜苷",
    "碳酸钙", "硫酸锌", "硫酸亚铁",
}

GROUP_PENALTY_RULES = {
    "儿童": [("type", "着色剂", 1.5), ("type", "甜味剂", 1.5), ("name", "咖啡因", 1.5)],
    "孕妇": [("type", "着色剂", 2.0), ("name", "咖啡因", 2.0), ("name_contains", "亚硝酸", 2.0)],
    "糖尿病": [("type", "甜味剂", 1.5)],
    "心血管": [("name_contains", "钠", 1.5)],
    "老人": [("name_contains", "钠", 1.3), ("name_contains", "明矾", 1.3)],
    "减肥": [("type", "甜味剂", 1.3)],
    "健身": [("type", "甜味剂", 1.2)],
    "普通人群": [],
    "其他": [],
}


def score_ingredients(ingredients_list, group_type=None, user_options=None, avoid_ids=None):
    data = load_reference_data()
    ingredients = [str(item).strip() for item in (ingredients_list or []) if str(item).strip()]
    combined_text = "".join(ingredients)

    matched_additives = [
        item for item in data.additives
        if item.name in ingredients or any(alias in combined_text for alias in item.aliases)
    ]
    matched_warnings = [
        warning for warning in data.group_warnings
        if (not group_type or warning.group_type == group_type)
        and warning.nutrient
        and (
            warning.nutrient in combined_text
            or any(warning.nutrient in additive.name for additive in matched_additives)
        )
    ]

    selected_ids = None if avoid_ids is None else {int(value) for value in avoid_ids}
    avoid_warnings = []
    for option in data.avoid_options:
        if selected_ids is not None and option.id not in selected_ids:
            continue
        if option.name in ingredients or any(keyword in combined_text for keyword in option.keywords):
            avoid_warnings.append({
                "name": option.name,
                "warning_msg": option.warning_msg,
                "suggestion": option.suggestion,
            })

    for option_name in user_options or []:
        if option_name in ingredients and not any(item["name"] == option_name for item in avoid_warnings):
            avoid_warnings.append({
                "name": option_name,
                "warning_msg": f"已避免成分: {option_name}",
                "suggestion": "该成分已从您的配料中检出",
            })

    beneficial_ingredients = []
    for item in data.beneficial_ingredients:
        if group_type and item.group_type != group_type:
            continue
        if item.nutrient and item.nutrient in combined_text:
            if not any(existing["nutrient"] == item.nutrient for existing in beneficial_ingredients):
                beneficial_ingredients.append({
                    "name": item.nutrient,
                    "nutrient": item.nutrient,
                    "benefit_category": item.benefit_category,
                    "benefit": item.benefit,
                    "suggestion": item.suggestion,
                })

    score, details = _calculate_score(
        matched_additives,
        matched_warnings,
        avoid_warnings,
        len(ingredients),
        group_type,
        beneficial_ingredients,
    )
    return {
        "health_score": score,
        "risk_additives": details["risk_additives"],
        "group_warnings": details["group_warnings"],
        "beneficial_ingredients": beneficial_ingredients,
        "beneficial_bonus": details["beneficial_bonus"],
        "avoid_warnings": avoid_warnings,
        "stacking_penalty": details["stacking_penalty"],
        "ingredients_count_penalty": details["ingredients_count_penalty"],
        "group_extra_penalty": details["group_extra_penalty"],
        "group_extra_details": details["group_extra_details"],
    }


def _calculate_score(matched_additives, matched_warnings, avoid_warnings, ingredients_count, group_type, beneficial_ingredients):
    beneficial_names = BENEFICIAL_ADDITIVE_NAMES | {item["nutrient"] for item in beneficial_ingredients}
    risk_items = [item for item in matched_additives if item.name not in beneficial_names]
    score = 100

    risk_additives = []
    for additive in sorted(risk_items, key=lambda item: RISK_PENALTY.get(item.risk_level, 0), reverse=True):
        deduct = RISK_PENALTY.get(additive.risk_level, 0)
        if not deduct:
            continue
        score -= deduct
        risk_additives.append({
            "name": additive.name,
            "risk_level": additive.risk_level,
            "reason": additive.reason,
            "deduct_score": deduct,
        })

    score -= len(avoid_warnings) * AVOID_PENALTY

    ingredients_count_penalty = 0
    if ingredients_count > 15:
        ingredients_count_penalty += 5
    if ingredients_count > 25:
        ingredients_count_penalty += 5
    score -= ingredients_count_penalty

    type_counter = Counter(item.type for item in risk_items if item.type)
    stacking_penalty = sum(STACK_PENALTY for count in type_counter.values() if count > STACK_THRESHOLD)
    score -= stacking_penalty

    group_extra_penalty = 0
    group_extra_details = []
    for additive in risk_items:
        base = RISK_PENALTY.get(additive.risk_level, 0)
        for match_type, match_value, multiplier in GROUP_PENALTY_RULES.get(group_type, []):
            matched = (
                (match_type == "type" and additive.type == match_value)
                or (match_type == "name" and additive.name == match_value)
                or (match_type == "name_contains" and match_value in additive.name)
            )
            if matched:
                extra = int(base * (multiplier - 1))
                if extra > 0:
                    group_extra_penalty += extra
                    group_extra_details.append({
                        "name": additive.name,
                        "risk_level": additive.risk_level,
                        "base_deduct": base,
                        "multiplier": multiplier,
                        "extra_deduct": extra,
                    })
                break
    score -= group_extra_penalty

    extra_by_name = {item["name"]: item for item in group_extra_details}
    for item in risk_additives:
        if item["name"] in extra_by_name:
            detail = extra_by_name[item["name"]]
            item["group_multiplier"] = detail["multiplier"]
            item["group_extra_deduct"] = detail["extra_deduct"]

    beneficial_bonus = min(
        BENEFIT_MAX_BONUS,
        sum(BENEFIT_BONUS.get(item["benefit_category"], 0) for item in beneficial_ingredients),
    )
    score += beneficial_bonus
    score = max(0, min(100, score))

    return score, {
        "risk_additives": risk_additives,
        "group_warnings": [
            {"type": item.warning_type, "msg": item.warning_msg, "suggestion": item.suggestion}
            for item in matched_warnings
        ],
        "beneficial_bonus": beneficial_bonus,
        "stacking_penalty": stacking_penalty,
        "ingredients_count_penalty": ingredients_count_penalty,
        "group_extra_penalty": group_extra_penalty,
        "group_extra_details": group_extra_details,
    }
