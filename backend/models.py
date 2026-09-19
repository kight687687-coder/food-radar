from sqlalchemy import Column, Integer, BigInteger, String, Text, Float, DateTime
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class Additive(Base):
    __tablename__ = "additives"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="添加剂名称")
    alias = Column(String(200), comment="别名")
    type = Column(String(50), comment="类别")
    risk_level = Column(String(10), comment="风险等级")
    forbidden_group = Column(String(100), comment="禁忌人群")
    reason = Column(Text, comment="风险原因")
    standard = Column(String(100), comment="标准限量")

class GroupWarning(Base):
    __tablename__ = "group_warnings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_type = Column(String(50), nullable=False, comment="人群类型")
    warning_type = Column(String(50), nullable=False, comment="预警类型")
    nutrient = Column(String(100), comment="关联营养成分")
    threshold = Column(Float, comment="阈值")
    level = Column(String(10), comment="预警等级")
    warning_msg = Column(Text, comment="预警信息")
    suggestion = Column(Text, comment="建议")

class BeneficialIngredient(Base):
    __tablename__ = "beneficial_ingredients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_type = Column(String(50), nullable=False, comment="人群类型")
    nutrient = Column(String(100), comment="营养成分关键词")
    benefit_category = Column(String(50), comment="有益类别")
    benefit = Column(Text, comment="益处描述")
    suggestion = Column(Text, comment="摄入建议")

class AvoidOption(Base):
    __tablename__ = "avoid_options"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="选项名称")
    keywords = Column(String(500), comment="关键词")
    warning_msg = Column(Text, comment="预警信息")
    suggestion = Column(Text, comment="建议")

class ScanHistory(Base):
    __tablename__ = "scan_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, comment="用户ID")
    product_name = Column(String(200), comment="产品名称")
    ingredients = Column(Text, comment="配料表")
    food_category = Column(String(50), comment="食品分类")
    health_score = Column(Integer, comment="健康评分")
    risk_count = Column(Integer, comment="风险项数量")
    result_json = Column(Text, comment="完整结果JSON")
    scan_time = Column(DateTime, default=datetime.now, comment="扫描时间")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    openid = Column(String(100), unique=True, comment="微信openid")
    user_type = Column(String(20), default="normal", comment="用户类型")
    avoid_options = Column(Text, comment="自定义规避选项")
    nickname = Column(String(100), comment="昵称")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

class WikiCache(Base):
    __tablename__ = "wiki_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, comment="添加剂名称")
    data = Column(Text, nullable=False, comment="JSON数据")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
