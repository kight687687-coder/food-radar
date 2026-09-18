import os
import re
import joblib
import pandas as pd

MODEL_PATH = os.path.join(os.path.dirname(__file__), "data", "models", "food_pipeline.pkl")
CONFIDENCE_THRESHOLD = 0.55

_pipeline = None

# ---- 关键词分类规则（仅作为 ML 置信度低时的兜底） ----
_KEYWORD_RULES = [
    ("乳制品类", ["生牛乳", "全脂乳粉", "脱脂乳粉", "乳清蛋白", "乳清粉",
                  "嗜热链球菌", "保加利亚乳杆菌", "乳酸菌", "发酵乳",
                  "奶酪", "干酪"]),
    ("饮料类", ["二氧化碳", "咖啡因", "浓缩果汁", "红茶", "绿茶", "乌龙茶",
                "维生素饮料", "运动饮料", "电解质", "牛磺酸", "植物饮料",
                "橙汁", "苹果汁", "葡萄汁", "山楂汁", "芒果汁", "椰果",
                "柠檬汁"]),
    ("肉制品类", ["午餐肉", "火腿", "腊肉", "培根", "香肠",
                  "肉松", "肉干", "肉脯", "亚硝酸钠", "卡拉胶"]),
    ("零食类", ["薯片", "膨化", "马铃薯", "坚果", "核桃", "杏仁",
                "海苔", "紫菜", "果冻", "巧克力", "可可脂",
                "糖果", "口香糖", "棉花糖",
                "饼干", "曲奇", "薄脆", "威化"]),
    ("正餐类", ["面条", "挂面", "方便面", "水饺", "饺子", "馄饨",
                "汤圆", "粽子", "米饭", "米粉", "米线", "河粉", "粥",
                "速冻", "罐头", "豆豉", "腐乳"]),
    ("调味品类", ["酿造酱油", "生抽", "老抽", "食醋", "蚝油",
                  "味精", "鸡精", "料酒", "黄豆酱", "豆瓣酱",
                  "番茄酱", "沙拉酱", "火锅底料", "调味料"]),
]

def _classify_by_keywords(ingredients_text):
    for category, keywords in _KEYWORD_RULES:
        for kw in keywords:
            # 任一关键词命中即可判定为该食品大类
            if kw in ingredients_text:
                return category, 0.85
    return None, 0

def _load_pipeline():
    global _pipeline
    if _pipeline is None:
        _pipeline = joblib.load(MODEL_PATH)
    return _pipeline

def classify(ingredients_text):
    # 1. ML 模型（主分类器）
    try:
        pipeline = _load_pipeline()
        X = pd.DataFrame([{"ingredients": ingredients_text}])
        label = pipeline.predict(X)[0]
        proba = pipeline.predict_proba(X).max()
        proba = float(round(proba, 4))

        if proba >= CONFIDENCE_THRESHOLD:
            return label, proba
    except Exception:
        # 模型加载或预测异常时不中断主流程，转入规则兜底
        pass

    # 2. 关键词规则兜底（ML 置信度不足时使用）
    label, proba = _classify_by_keywords(ingredients_text)
    if label:
        return label, proba

    # 3. 宽松正则兜底
    fallback = _fallback_classify(ingredients_text)
    if fallback:
        return fallback, 0.5
    return "零食类", 0.0

def _fallback_classify(ingredients_text):
    # 乳、奶、酪等关键词通常指向乳制品，但含糖、香精、胶时更接近零食属性
    if re.search(r'乳|奶|酪', ingredients_text):
        if re.search(r'糖|甜|香精|胶', ingredients_text):
            return "零食类"
        return "乳制品类"
    if re.search(r'二氧化碳|咖啡因|果汁|茶|饮料', ingredients_text):
        return "饮料类"
    if re.search(r'火腿|香肠|培根|肉松|肉干|肉脯|亚硝酸钠', ingredients_text):
        return "肉制品类"
    if re.search(r'小麦|面粉|面条|米|饺子|馄饨', ingredients_text):
        return "正餐类"
    if re.search(r'酱油|醋|料酒|酱|味精|鸡精|花椒|辣椒', ingredients_text):
        return "调味品类"
    if re.search(r'薯|坚果|巧克力|糖果|饼干|膨化|海苔|紫菜|果冻', ingredients_text):
        return "零食类"
    return None
