from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from config import SQLALCHEMY_DATABASE_URI
from models import Additive, GroupWarning, AvoidOption, BeneficialIngredient

RISK_PENALTY = {"高": 20, "中": 10, "低": 5}
AVOID_PENALTY = 5
STACK_PENALTY = 8
STACK_THRESHOLD = 2

# 有益成分加分
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

# 已知有益/安全的食品添加剂：虽然作为食品添加剂使用（多为抗氧化剂、甜味剂等），
# 但同时也是有益营养素，不应标记为风险成分，也不应扣分
BENEFICIAL_ADDITIVE_NAMES = {
    # 维生素类
    "维生素C", "维生素E", "β-胡萝卜素",
    # 天然抗氧化剂
    "茶多酚", "姜黄素", "植酸",
    # 维生素C衍生物
    "D-异抗坏血酸钠", "抗坏血酸钠",
    # 氨基酸/营养素类
    "牛磺酸", "卵磷脂",
    # 天然代糖
    "赤藓糖醇", "木糖醇", "麦芽糖醇", "山梨糖醇",
    "甜菊糖苷", "罗汉果甜苷",
    # 营养强化剂
    "碳酸钙", "硫酸锌", "硫酸亚铁",
}

# 人群额外惩罚系数
# (匹配方式, 匹配值, 倍率)  —  base_deduct × (multiplier - 1) 为额外扣分
# 匹配方式: "type" 按添加剂类型字段, "name" 按名称精确匹配, "name_contains" 按名称包含
GROUP_PENALTY_RULES = {
    "儿童": [
        ("type", "着色剂", 1.5),
        ("type", "甜味剂", 1.5),
        ("name", "咖啡因", 1.5),
    ],
    "孕妇": [
        ("type", "着色剂", 2.0),
        ("name", "咖啡因", 2.0),
        ("name_contains", "亚硝酸", 2.0),
    ],
    "糖尿病": [
        ("type", "甜味剂", 1.5),
    ],
    "心血管": [
        ("name_contains", "钠", 1.5),
    ],
    "老人": [
        ("name_contains", "钠", 1.3),
        ("name_contains", "明矾", 1.3),
    ],
    "减肥": [
        ("type", "甜味剂", 1.3),
    ],
    "健身": [
        ("type", "甜味剂", 1.2),
    ],
    "普通人群": [],
    "其他": [],
}


def _get_engine():
    return create_engine(SQLALCHEMY_DATABASE_URI)


def score_ingredients(ingredients_list, group_type=None, user_options=None, avoid_ids=None):
    """
    综合评分主函数
    :param ingredients_list: 配料列表，如 ["水", "白砂糖", "柠檬酸", ...]
    :param group_type: 人群类型，如 "儿童"、"孕妇"，None 表示不触发人群预警
    :param user_options: 用户自定义避免成分，如 ["味精", "人工色素"]
    :param avoid_ids: 指定要匹配的AvoidOption ID列表，None表示匹配全部
    :return: dict
    """
    engine = _get_engine()

    with Session(engine) as session:

        # ── 1. 匹配添加剂 ──
        all_additives = session.query(Additive).all()
        matched_additives = []
        for add in all_additives:
            if add.name in ingredients_list:
                matched_additives.append(add)
            elif add.alias:
                aliases = [a.strip() for a in add.alias.split(",")]
                if any(a in "".join(ingredients_list) for a in aliases):
                    matched_additives.append(add)

        # ── 2. 人群预警 ──
        matched_warnings = _match_group_warnings(session, matched_additives, ingredients_list, group_type)

        # ── 3. 自定义成分 ──
        avoid_warnings = _match_avoid_options(session, ingredients_list, user_options, avoid_ids)

        # ── 4. 有益成分 ──
        beneficial_ingredients = _match_beneficial_ingredients(session, ingredients_list, group_type)

    # ── 4. 计算评分 ──
    score, details = _calculate_score(matched_additives, matched_warnings, avoid_warnings, len(ingredients_list), group_type, beneficial_ingredients)

    return {
        "health_score": score,
        "risk_additives": details["risk_additives"],
        "group_warnings": details["group_warnings"],
        "beneficial_ingredients": beneficial_ingredients,
        "avoid_warnings": avoid_warnings,
        "stacking_penalty": details["stacking_penalty"],
        "ingredients_count_penalty": details["ingredients_count_penalty"],
        "group_extra_penalty": details["group_extra_penalty"],
        "group_extra_details": details["group_extra_details"],
    }


def _match_group_warnings(session, matched_additives, ingredients_list, group_type=None):
    """匹配人群预警：按人群类型 + 营养关键词匹配"""
    query = session.query(GroupWarning)
    if group_type:
        query = query.filter(GroupWarning.group_type == group_type)
    warnings = query.all()
    triggered = []
    combined_text = "".join(ingredients_list)
    for w in warnings:
        if w.nutrient:
            matched_names = [a.name for a in matched_additives]
            if w.nutrient in combined_text or any(w.nutrient in name for name in matched_names):
                triggered.append(w)
    return triggered


def _match_avoid_options(session, ingredients_list, user_options, avoid_ids=None):
    """匹配自定义避免成分"""
    from models import AvoidOption

    avoid_warnings = []
    query = session.query(AvoidOption)
    if avoid_ids is not None:
        query = query.filter(AvoidOption.id.in_(avoid_ids))
    options = query.all()
    for opt in options:
        matched = any(ing == opt.name or (opt.keywords and any(
            kw.strip() in "".join(ingredients_list) for kw in opt.keywords.split(",")
        )) for ing in ingredients_list)
        if matched:
            avoid_warnings.append({
                "name": opt.name,
                "warning_msg": opt.warning_msg,
                "suggestion": opt.suggestion,
            })

    # 也检查用户自定义选项
    if user_options:
        for opt_name in user_options:
            if opt_name in ingredients_list:
                avoid_warnings.append({
                    "name": opt_name,
                    "warning_msg": f"已避免成分: {opt_name}",
                    "suggestion": "该成分已从您的配料中检出",
                })

    return avoid_warnings


def _match_beneficial_ingredients(session, ingredients_list, group_type=None):
    """匹配有益成分：按人群类型 + 营养关键词匹配配料"""
    query = session.query(BeneficialIngredient)
    if group_type:
        query = query.filter(BeneficialIngredient.group_type == group_type)
    candidates = query.all()
    if not candidates:
        return []

    combined_text = "".join(ingredients_list)
    matched = []
    for c in candidates:
        if c.nutrient and c.nutrient in combined_text:
            # 去重：同一营养成分只保留一个
            if not any(m["nutrient"] == c.nutrient for m in matched):
                matched.append({
                    "nutrient": c.nutrient,
                    "benefit_category": c.benefit_category,
                    "benefit": c.benefit,
                    "suggestion": c.suggestion,
                })

    return matched


def _calculate_score(matched_additives, matched_warnings, avoid_warnings, ingredients_count=0, group_type=None, beneficial_ingredients=None):
    """计算健康评分（仅扣分体系）"""
    score = 100  # 基准分

    # 排除已知有益添加剂——它们不应被当作风险成分处理
    beneficial_names = set(BENEFICIAL_ADDITIVE_NAMES)
    if beneficial_ingredients:
        beneficial_names |= {b["nutrient"] for b in beneficial_ingredients}
    filtered_count = len(matched_additives)
    matched_additives = [a for a in matched_additives if a.name not in beneficial_names]
    filtered_count -= len(matched_additives)
    if filtered_count:
        print(f"[Score] 排除有益添加剂 {filtered_count}个", flush=True)

    # 按风险等级统计
    high = [a for a in matched_additives if a.risk_level == "高"]
    mid = [a for a in matched_additives if a.risk_level == "中"]
    low = [a for a in matched_additives if a.risk_level == "低"]

    risk_additives = []
    for a in high:
        risk_additives.append({"name": a.name, "risk_level": "高", "reason": a.reason, "deduct_score": 20})
    for a in mid:
        risk_additives.append({"name": a.name, "risk_level": "中", "reason": a.reason, "deduct_score": 10})
    for a in low:
        risk_additives.append({"name": a.name, "risk_level": "低", "reason": a.reason, "deduct_score": 5})

    # 添加剂扣分
    score -= len(high) * RISK_PENALTY["高"]
    score -= len(mid) * RISK_PENALTY["中"]
    score -= len(low) * RISK_PENALTY["低"]

    # 避免成分扣分
    score -= len(avoid_warnings) * AVOID_PENALTY

    # 配料数量惩罚（累加）
    ingredients_count_penalty = 0
    if ingredients_count > 15:
        score -= 5
        ingredients_count_penalty = 5
    if ingredients_count > 25:
        score -= 5
        ingredients_count_penalty += 5

    # 叠加惩罚：同类添加剂（type相同）超过指定数量触发
    from collections import Counter
    type_counter = Counter(a.type for a in matched_additives if a.type)
    stacking_penalty = 0
    for t, cnt in type_counter.items():
        if cnt > STACK_THRESHOLD:
            score -= STACK_PENALTY
            stacking_penalty += STACK_PENALTY

    # ── 5. 人群额外惩罚 ──
    group_extra_penalty = 0
    group_extra_details = []

    if group_type and group_type in GROUP_PENALTY_RULES:
        for additive in matched_additives:
            base = RISK_PENALTY.get(additive.risk_level, 0)
            if base == 0:
                continue
            for match_type, match_val, multiplier in GROUP_PENALTY_RULES[group_type]:
                matched = False
                if match_type == "type" and additive.type == match_val:
                    matched = True
                elif match_type == "name" and additive.name == match_val:
                    matched = True
                elif match_type == "name_contains" and match_val in additive.name:
                    matched = True
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
                    break  # 每条添加剂只触发一条规则

        # 把额外扣分信息写入 risk_additives
        extra_map = {d["name"]: {"multiplier": d["multiplier"], "extra_deduct": d["extra_deduct"]}
                     for d in group_extra_details}
        for ra in risk_additives:
            if ra["name"] in extra_map:
                ra["group_multiplier"] = extra_map[ra["name"]]["multiplier"]
                ra["group_extra_deduct"] = extra_map[ra["name"]]["extra_deduct"]

    score -= group_extra_penalty

    # 限制在 0-100 范围
    score = max(0, min(100, score))

    print(f"[Score] 高风险:{len(high)}个x20 中风险:{len(mid)}个x10 低风险:{len(low)}个x5", flush=True)
    print(f"[Score] 排除有益添加剂:{len(beneficial_names & orig_count)}个" if hasattr(score, 'orig_count') else "", flush=True)
    print(f"[Score] 避免成分:{len(avoid_warnings)}个x5 配料数:{ingredients_count} 叠加惩罚:{stacking_penalty}", flush=True)
    print(f"[Score] 人群额外惩罚:{group_extra_penalty}", flush=True)
    print(f"[Score] 最终分数:{score}", flush=True)

    group_warnings = [{"type": w.warning_type, "msg": w.warning_msg, "suggestion": w.suggestion}
                      for w in matched_warnings]

    return score, {
        "risk_additives": risk_additives,
        "group_warnings": group_warnings,
        "stacking_penalty": stacking_penalty,
        "ingredients_count_penalty": ingredients_count_penalty,
        "group_extra_penalty": group_extra_penalty,
        "group_extra_details": group_extra_details,
    }
