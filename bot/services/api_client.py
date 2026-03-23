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

    async def get_learners(self) -> list[dict[str, object]]:
        return await self._get_json("/learners/")

    async def get_scores(self, lab: str) -> list[dict[str, object]]:
        return await self._get_json("/analytics/scores", params={"lab": lab})

    async def get_pass_rates(self, lab: str) -> list[dict[str, object]]:
        return await self._get_json("/analytics/pass-rates", params={"lab": lab})

    async def get_timeline(self, lab: str) -> list[dict[str, object]]:
        return await self._get_json("/analytics/timeline", params={"lab": lab})

    async def get_groups(self, lab: str) -> list[dict[str, object]]:
        return await self._get_json("/analytics/groups", params={"lab": lab})

    async def get_top_learners(
        self, lab: str, limit: int = 10
    ) -> list[dict[str, object]]:
        return await self._get_json(
            "/analytics/top-learners",
            params={"lab": lab, "limit": str(limit)},
        )

    async def get_completion_rate(self, lab: str) -> dict[str, object]:
        return await self._request_json("/analytics/completion-rate", params={"lab": lab})

    async def trigger_sync(self) -> dict[str, object]:
        return await self._request_json("/pipeline/sync", method="POST")

    async def _get_json(
        self, path: str, params: dict[str, str] | None = None
    ) -> list[dict[str, object]]:
        payload = await self._request_json(path, params=params)
        if isinstance(payload, list):
            return payload
        return []

    async def _request_json(
        self,
        path: str,
        params: dict[str, str] | None = None,
        method: str = "GET",
    ) -> dict[str, object] | list[dict[str, object]]:
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url, timeout=10.0
            ) as client:
                response = await client.request(
                    method,
                    path,
                    headers=self._headers(),
                    params=params,
                    json={} if method == "POST" else None,
                )
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
        if isinstance(payload, dict | list):
            return payload
        return {}
