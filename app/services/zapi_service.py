import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

ZAPI_BASE_URL = (
    f"https://api.z-api.io/instances/{settings.ZAPI_INSTANCE_ID}"
    f"/token/{settings.ZAPI_TOKEN}"
)


async def get_status() -> dict:
    url = f"{ZAPI_BASE_URL}/status"
    headers = {"Client-Token": settings.ZAPI_CLIENT_TOKEN}

    async with httpx.AsyncClient(timeout=5) as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Erro ao consultar status Z-API: {e}")
            return {"connected": False, "error": str(e)}


async def send_text_message(phone: str, message: str) -> dict | None:
    url = f"{ZAPI_BASE_URL}/send-text"
    headers = {"Client-Token": settings.ZAPI_CLIENT_TOKEN}
    payload = {"phone": phone, "message": message}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Erro ao enviar mensagem via Z-API: {e}")
            return None
