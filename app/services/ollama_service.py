import httpx
from fastapi import HTTPException

from app.config import settings

_TIMEOUT = 120.0


async def _post_ollama(payload: dict) -> dict:
    url = f"{settings.ollama_base_url}/api/chat"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=_TIMEOUT)
            response.raise_for_status()
            return response.json()
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Ollama is not reachable")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Ollama did not respond in time")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Ollama returned an error: {e.response.status_code}")


async def ask_ollama(model: str, message: str) -> str:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": message}],
        "stream": False,
    }
    try:
        data = await _post_ollama(payload)
        return data["message"]["content"]
    except KeyError:
        raise HTTPException(status_code=502, detail="Unexpected response structure from Ollama")


async def ask_ollama_raw(model: str, messages: list[dict]) -> dict:
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    return await _post_ollama(payload)
