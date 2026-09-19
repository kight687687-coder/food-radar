"""Optional SQLAlchemy persistence that never blocks stateless operation."""

from __future__ import annotations

import json
from datetime import date
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from config import get_database_url
from models import Base, ScanHistory, WikiCache


@lru_cache(maxsize=1)
def get_engine():
    database_url = get_database_url()
    if not database_url:
        return None
    engine = create_engine(database_url, pool_pre_ping=True, pool_recycle=280)
    Base.metadata.create_all(engine)
    return engine


def save_scan(result, body) -> int | None:
    engine = get_engine()
    if engine is None:
        return None
    try:
        with Session(engine) as session:
            record = ScanHistory(
                user_id=body.get("user_id"),
                product_name=result.get("food_category"),
                ingredients=result.get("ingredients"),
                food_category=result.get("food_category"),
                health_score=result.get("health_score"),
                risk_count=result.get("risk_count", 0),
                result_json=json.dumps(result, ensure_ascii=False),
            )
            session.add(record)
            session.commit()
            return record.id
    except Exception:
        return None


def load_history(user_id, limit=20) -> list[dict]:
    engine = get_engine()
    if engine is None:
        return []
    try:
        with Session(engine) as session:
            records = (
                session.query(ScanHistory)
                .filter(ScanHistory.user_id == user_id)
                .order_by(ScanHistory.scan_time.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": record.id,
                    "product_name": record.product_name,
                    "food_category": record.food_category,
                    "health_score": record.health_score,
                    "risk_count": record.risk_count,
                    "scan_time": record.scan_time.isoformat() if record.scan_time else None,
                }
                for record in records
            ]
    except Exception:
        return []


def load_daily(user_id) -> dict | None:
    engine = get_engine()
    if engine is None:
        return None
    try:
        with Session(engine) as session:
            records = (
                session.query(ScanHistory)
                .filter(ScanHistory.user_id == user_id)
                .order_by(ScanHistory.scan_time.desc())
                .limit(100)
                .all()
            )
        today_records = [
            record for record in records
            if record.scan_time and record.scan_time.date() == date.today()
        ]
        if not today_records:
            return None
        scores = [record.health_score for record in today_records if record.health_score is not None]
        average = round(sum(scores) / len(scores), 1) if scores else 0
        worst = min(today_records, key=lambda record: record.health_score if record.health_score is not None else 101)
        return {
            "scan_count": len(today_records),
            "avg_score": average,
            "worst_food": {
                "product_name": worst.product_name,
                "health_score": worst.health_score,
                "risk_count": worst.risk_count,
                "scan_time": worst.scan_time.isoformat() if worst.scan_time else None,
            },
            "foods_context": "; ".join(
                f"{record.product_name}({record.health_score}分/{record.risk_count}风险)"
                for record in today_records[:10]
            ),
            "daily_score": round(average),
        }
    except Exception:
        return None


def load_wiki_cache(name):
    engine = get_engine()
    if engine is None:
        return None
    try:
        with Session(engine) as session:
            row = session.query(WikiCache).filter(WikiCache.name == name).first()
            if not row:
                return None
            return json.loads(row.data) if isinstance(row.data, str) else row.data
    except Exception:
        return None


def save_wiki_cache(name, data):
    engine = get_engine()
    if engine is None:
        return False
    try:
        with Session(engine) as session:
            row = session.query(WikiCache).filter(WikiCache.name == name).first()
            payload = json.dumps(data, ensure_ascii=False)
            if row:
                row.data = payload
            else:
                session.add(WikiCache(name=name, data=payload))
            session.commit()
        return True
    except Exception:
        return False
