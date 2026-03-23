from __future__ import annotations

import httpx


class LMSApiClient:
    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}"}

    async def get_items(self) -> list[dict[str, object]]:
        async with httpx.AsyncClient(base_url=self._base_url, timeout=10.0) as client:
            response = await client.get("/items/", headers=self._headers())
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, list):
                return payload
            return []
