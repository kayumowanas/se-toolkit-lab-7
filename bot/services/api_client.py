from __future__ import annotations

import httpx


class BackendError(Exception):
    pass


class LMSApiClient:
    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}"}

    async def get_items(self) -> list[dict[str, object]]:
        return await self._get_json("/items/")

    async def get_pass_rates(self, lab: str) -> list[dict[str, object]]:
        return await self._get_json("/analytics/pass-rates", params={"lab": lab})

    async def _get_json(
        self, path: str, params: dict[str, str] | None = None
    ) -> list[dict[str, object]]:
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url, timeout=10.0
            ) as client:
                response = await client.get(path, headers=self._headers(), params=params)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            reason = exc.response.reason_phrase or "HTTP error"
            raise BackendError(f"HTTP {status_code} {reason}.") from exc
        except httpx.ConnectError as exc:
            raise BackendError(
                f"connection refused ({self._base_url}). Check that the services are running."
            ) from exc
        except httpx.TimeoutException as exc:
            raise BackendError(
                f"request timed out while calling {self._base_url}{path}."
            ) from exc
        except httpx.HTTPError as exc:
            raise BackendError(str(exc)) from exc

        payload = response.json()
        if isinstance(payload, list):
            return payload
        return []
