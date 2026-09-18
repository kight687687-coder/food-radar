import csv
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from config import SQLALCHEMY_DATABASE_URI
from models import Additive, GroupWarning, AvoidOption, BeneficialIngredient

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "csv")


def import_csv(filename, model_class):
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        print(f"  [跳过] 文件不存在: {filename}")
        return 0

    engine = create_engine(SQLALCHEMY_DATABASE_URI)
    table = model_class.__tablename__

    with engine.connect() as conn:
        conn.execute(text(f"TRUNCATE TABLE {table}"))
        conn.commit()

    model_columns = {c.name for c in model_class.__table__.columns}

    rows = []
    with open(filepath, "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            # 只导入模型中声明过的字段，避免CSV扩展列导致写库失败
            filtered = {k: v for k, v in row.items() if k in model_columns}
            rows.append(model_class(**filtered))

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
