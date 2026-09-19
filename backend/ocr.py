"""Baidu OCR adapter with bounded retries and credential-safe errors."""

from __future__ import annotations

import base64
import time

import requests

from config import BAIDU_OCR


OCR_URL = "https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic"
TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
TOKEN_CACHE = {"access_token": None, "expires_at": 0.0}


class ProviderConfigurationError(RuntimeError):
    pass


class OCRProviderError(RuntimeError):
    pass


def _require_credentials() -> tuple[str, str]:
    api_key = BAIDU_OCR.get("api_key", "")
    secret_key = BAIDU_OCR.get("secret_key", "")
    if not api_key or not secret_key:
        raise ProviderConfigurationError(
            "百度 OCR 尚未配置，请在服务端设置 BAIDU_OCR_API_KEY 和 BAIDU_OCR_SECRET_KEY"
        )
    return api_key, secret_key


def _get_access_token() -> str:
    api_key, secret_key = _require_credentials()
    now = time.time()
    if TOKEN_CACHE["access_token"] and now < TOKEN_CACHE["expires_at"] - 60:
        return str(TOKEN_CACHE["access_token"])

    try:
        response = requests.post(
            TOKEN_URL,
            params={
                "grant_type": "client_credentials",
                "client_id": api_key,
                "client_secret": secret_key,
            },
            timeout=(5, 12),
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise OCRProviderError("百度 OCR 鉴权服务暂时不可用") from exc

    access_token = data.get("access_token")
    if not access_token:
        raise OCRProviderError("百度 OCR 凭据无效或鉴权失败")

    TOKEN_CACHE["access_token"] = access_token
    TOKEN_CACHE["expires_at"] = now + int(data.get("expires_in", 1800))
    return str(access_token)


def ocr_image(image_path=None, image_base64=None, retries=2):
    if image_base64 is None:
        if not image_path:
            raise ValueError("缺少待识别图片")
        with open(image_path, "rb") as handle:
            image_base64 = base64.b64encode(handle.read()).decode("utf-8")

    if not isinstance(image_base64, str) or not image_base64.strip():
        raise ValueError("图片内容为空")

    last_error = None
    for attempt in range(max(0, retries) + 1):
        try:
            token = _get_access_token()
            response = requests.post(
                f"{OCR_URL}?access_token={token}",
                data={"image": image_base64},
                timeout=(5, 25),
            )
            response.raise_for_status()
            result = response.json()
            if result.get("error_code"):
                message = result.get("error_msg") or "识别失败"
                raise OCRProviderError(f"百度 OCR 返回错误：{message}")

            words = [item.get("words", "") for item in result.get("words_result", [])]
            return "\n".join(word for word in words if word)
        except ProviderConfigurationError:
            raise
        except (requests.RequestException, ValueError, OCRProviderError) as exc:
            last_error = exc
            if attempt < max(0, retries):
                time.sleep(min(0.5 * (attempt + 1), 1.0))

    raise OCRProviderError("百度 OCR 服务暂时不可用，请稍后重试") from last_error
