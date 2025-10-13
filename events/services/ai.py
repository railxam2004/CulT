import json
import requests
from django.conf import settings

class YandexGPTError(Exception):
    pass

def generate_event_description(prompt: str, *, system_hint: str = "", temperature: float = 0.6, max_tokens: int = 800) -> str:
    """
    Вызывает YandexGPT /completion и возвращает сгенерированный текст.
    Бросает YandexGPTError при ошибке.
    """
    api_key = settings.YANDEX_GPT_API_KEY
    folder_id = settings.YANDEX_GPT_FOLDER_ID
    if not api_key or not folder_id:
        raise YandexGPTError("YandexGPT credentials are not configured")

    headers = {
        "Authorization": f"Api-Key {api_key}",
        "Content-Type": "application/json",
    }

    system_text = system_hint or (
        "Ты помощник по маркетингу культурных событий. "
        "Пиши на русском, живо и понятно. Не выдумывай конкретные цены/время, если их нет. "
        "Тон дружелюбный. Дай 1–2 абзаца (100–150 слов), можно список из 3–5 пунктов."
    )

    payload = {
        "modelUri": f"gpt://{folder_id}/yandexgpt/latest",
        "completionOptions": {
            "stream": False,
            "temperature": temperature,
            "maxTokens": max_tokens
        },
        "messages": [
            {"role": "system", "text": system_text},
            {"role": "user", "text": prompt},
        ]
    }

    try:
        resp = requests.post(
            "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
            headers=headers,
            json=payload,
            timeout=settings.YANDEX_GPT_TIMEOUT
        )
    except requests.RequestException as e:
        raise YandexGPTError(f"Network error: {e}") from e

    if resp.status_code != 200:
        # попробуем вытащить текст ошибки
        try:
            err = resp.json()
        except Exception:
            err = resp.text
        raise YandexGPTError(f"API error {resp.status_code}: {err}")

    try:
        data = resp.json()
        return data["result"]["alternatives"][0]["message"]["text"]
    except Exception as e:
        raise YandexGPTError(f"Bad response format: {e}")
