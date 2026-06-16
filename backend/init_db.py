import sys
from sqlalchemy import create_engine, text
from config import SQLALCHEMY_DATABASE_URI
from models import Base


def init_db():
    """连接MySQL并创建所有表"""
    try:
        engine = create_engine(SQLALCHEMY_DATABASE_URI)
        # 测试连接
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("数据库连接成功")
        # 创建所有表
        Base.metadata.create_all(engine)
        print("所有表创建成功")
        print("已创建表:", list(Base.metadata.tables.keys()))
    except Exception as e:
        print("数据库连接失败")
        print("错误信息:", e)


if __name__ == "__main__":
    init_db()
