import requests
import base64
import time
from config import BAIDU_OCR

OCR_URL = "https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic"
TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"

TOKEN_CACHE = {"access_token": None, "expires_at": 0}


def _get_access_token():
    now = time.time()
    if TOKEN_CACHE["access_token"] and now < TOKEN_CACHE["expires_at"] - 60:
        return TOKEN_CACHE["access_token"]

    resp = requests.post(TOKEN_URL, params={
        "grant_type": "client_credentials",
        "client_id": BAIDU_OCR["api_key"],
        "client_secret": BAIDU_OCR["secret_key"],
    })
    data = resp.json()
    TOKEN_CACHE["access_token"] = data["access_token"]
    TOKEN_CACHE["expires_at"] = now + data["expires_in"]
    return data["access_token"]


def ocr_image(image_path=None, image_base64=None, retries=2):
    """调用百度OCR识别图片，支持文件路径或base64字符串"""
    if image_base64 is None:
        with open(image_path, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode("utf-8")

    print("[OCR] base64前50字:", image_base64[:50], "总长度:", len(image_base64))

    for attempt in range(retries + 1):
        try:
            token = _get_access_token()
            resp = requests.post(f"{OCR_URL}?access_token={token}", data={
                "image": image_base64,
            }, timeout=15)
            result = resp.json()

            if "error_code" in result:
                raise Exception(f"OCR API错误: {result.get('error_msg', result)}")

            print("[OCR] 百度API返回:", result)

            words = [item["words"] for item in result.get("words_result", [])]
            return "\n".join(words)

        except Exception as e:
            if attempt < retries:
                time.sleep(1)
                continue
            raise e
