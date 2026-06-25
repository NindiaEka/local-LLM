import httpx
from fastapi import HTTPException

from app.config import settings


async def ask_ollama(model: str, message: str) -> str:
    url = f"{settings.ollama_base_url}/api/chat"

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": message}],
        "stream": False,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=120.0)
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"]
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Ollama is not reachable")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Ollama did not respond in time")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Ollama returned an error: {e.response.status_code}")
    except KeyError:
        raise HTTPException(status_code=502, detail="Unexpected response structure from Ollama")
