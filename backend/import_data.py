import csv
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from config import SQLALCHEMY_DATABASE_URI
from models import Additive, GroupWarning, AvoidOption, BeneficialIngredient

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "csv")


def import_csv(filename, model_class):
    """通用CSV导入函数，自动过滤模型中不存在的字段"""
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        print(f"  [跳过] 文件不存在: {filename}")
        return 0

    engine = create_engine(SQLALCHEMY_DATABASE_URI)
    table = model_class.__tablename__

    # 清空旧数据
    with engine.connect() as conn:
        conn.execute(text(f"TRUNCATE TABLE {table}"))
        conn.commit()

    # 获取模型所有列名
    model_columns = {c.name for c in model_class.__table__.columns}

    # 读取CSV并插入
    rows = []
    with open(filepath, "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            # 只保留模型中存在的字段
            filtered = {k: v for k, v in row.items() if k in model_columns}
            rows.append(model_class(**filtered))

    # 批量插入
    with Session(engine) as session:
        session.add_all(rows)
        session.commit()

    print(f"  {filename} -> {table} : 导入 {len(rows)} 条")
    return len(rows)


def import_all():
    print("开始导入数据...\n")
    import_csv("additives.csv", Additive)
    import_csv("group_warnings.csv", GroupWarning)
    import_csv("avoid_options.csv", AvoidOption)
    import_csv("beneficial_ingredients.csv", BeneficialIngredient)
    print("\n导入完成！")


if __name__ == "__main__":
    import_all()
