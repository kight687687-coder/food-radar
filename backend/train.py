import os
import pandas as pd
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "csv", "train_data.csv")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "data", "models")
MODEL_PATH = os.path.join(MODEL_DIR, "food_pipeline.pkl")

# 1. 读取训练数据
df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
print(f"训练数据: {len(df)} 条")
print("类别分布:")
print(df["category"].value_counts().to_string())

# 2. 训练
X = df["keywords"]
y = df["category"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"\n训练集: {len(X_train)} 条")
print(f"测试集: {len(X_test)} 条")

pipeline = Pipeline([
    ("tfidf", TfidfVectorizer(
        ngram_range=(1, 3),
        max_df=0.85,
        min_df=1,
        sublinear_tf=True,
    )),
    ("nb", MultinomialNB(alpha=0.05)),
])

pipeline.fit(X_train, y_train)

# 3. 评估
y_pred = pipeline.predict(X_test)
acc = accuracy_score(y_test, y_pred)
print(f"\n准确率: {acc:.2%}\n")
print("分类报告:")
print(classification_report(y_test, y_pred))

# 4. 保存
os.makedirs(MODEL_DIR, exist_ok=True)
joblib.dump(pipeline, MODEL_PATH)
print(f"模型已保存: {MODEL_PATH}")
