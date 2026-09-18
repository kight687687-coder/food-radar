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
        # 缓存令牌未过期时直接复用，提前60秒刷新避免临界过期
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
                # 百度接口返回错误码时抛出异常，交由重试逻辑或上层接口处理
                raise Exception(f"OCR API错误: {result.get('error_msg', result)}")

            print("[OCR] 百度API返回:", result)

            words = [item["words"] for item in result.get("words_result", [])]
            return "\n".join(words)

        except Exception as e:
            if attempt < retries:
                # 短暂等待后重试，缓解网络抖动或临时接口异常
                time.sleep(1)
                continue
            raise e
