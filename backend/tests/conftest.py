import importlib
import os
import sys
from pathlib import Path

import pytest


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


@pytest.fixture(autouse=True)
def clean_service_environment(monkeypatch):
    keys = [
        "DATABASE_URL",
        "DB_HOST",
        "DB_PORT",
        "DB_USER",
        "DB_PASSWORD",
        "DB_NAME",
        "BAIDU_OCR_APP_ID",
        "BAIDU_OCR_API_KEY",
        "BAIDU_OCR_SECRET_KEY",
        "DEEPSEEK_API_KEY",
    ]
    for key in keys:
        monkeypatch.delenv(key, raising=False)

    # The repository may contain a developer-only .env file. Tests must prove
    # the server works from explicit process environment rather than that file.
    monkeypatch.setenv("FOOD_RADAR_LOAD_DOTENV", "0")

    for module_name in ("config", "data_store", "score", "ocr", "ai_analyze", "persistence", "app"):
        sys.modules.pop(module_name, None)

    yield

    importlib.invalidate_caches()
