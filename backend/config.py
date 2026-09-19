"""Environment configuration for local Flask and Vercel serverless runs."""

from __future__ import annotations

import os
from urllib.parse import quote_plus

from dotenv import load_dotenv


if os.getenv("FOOD_RADAR_LOAD_DOTENV", "1").lower() not in {"0", "false", "no"}:
    load_dotenv()


def get_database_url() -> str | None:
    direct_url = (os.getenv("DATABASE_URL") or "").strip()
    if direct_url:
        return direct_url

    required = ["DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME"]
    if not all((os.getenv(key) or "").strip() for key in required):
        return None

    host = os.environ["DB_HOST"].strip()
    port = int(os.getenv("DB_PORT", "3306"))
    user = quote_plus(os.environ["DB_USER"].strip())
    password = quote_plus(os.environ["DB_PASSWORD"].strip())
    database = quote_plus(os.environ["DB_NAME"].strip())
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"


SQLALCHEMY_DATABASE_URI = get_database_url()

BAIDU_OCR = {
    "app_id": (os.getenv("BAIDU_OCR_APP_ID") or "").strip(),
    "api_key": (os.getenv("BAIDU_OCR_API_KEY") or "").strip(),
    "secret_key": (os.getenv("BAIDU_OCR_SECRET_KEY") or "").strip(),
}

DEEPSEEK_API_KEY = (os.getenv("DEEPSEEK_API_KEY") or "").strip()
DEEPSEEK_MODEL = (os.getenv("DEEPSEEK_MODEL") or "deepseek-chat").strip()
DEEPSEEK_BASE_URL = (os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com").strip()

ALLOWED_ORIGINS = tuple(
    origin.strip()
    for origin in (os.getenv("ALLOWED_ORIGINS") or "").split(",")
    if origin.strip()
)
