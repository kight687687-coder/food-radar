import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "YOUR_DB_HOST"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "YOUR_DB_USER"),
    "password": os.getenv("DB_PASSWORD", "YOUR_DB_PASSWORD"),
    "database": os.getenv("DB_NAME", "YOUR_DB_NAME"),
    "charset": "utf8mb4",
}

SQLALCHEMY_DATABASE_URI = (
    f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    f"?charset={DB_CONFIG['charset']}"
)

BAIDU_OCR = {
    "app_id": os.getenv("BAIDU_OCR_APP_ID", "YOUR_BAIDU_APP_ID"),
    "api_key": os.getenv("BAIDU_OCR_API_KEY", "YOUR_BAIDU_API_KEY"),
    "secret_key": os.getenv("BAIDU_OCR_SECRET_KEY", "YOUR_BAIDU_SECRET_KEY"),
}

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
