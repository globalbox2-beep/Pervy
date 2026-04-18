import httpx
import logging
from typing import Any

logger = logging.getLogger(__name__)


class BitrixError(Exception):
    pass


class Bitrix24Client:
    def __init__(self, webhook_url: str):
        self._base_url = webhook_url
        self._client = httpx.AsyncClient(timeout=30.0)

    async def call(self, method: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self._base_url}/{method}"
        payload = params or {}
        logger.debug("Bitrix24 call: %s %s", method, payload)
        try:
            response = await self._client.post(url, json=payload)
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise BitrixError(f"HTTP error calling {method}: {e}") from e

        data = response.json()
        if "error" in data:
            raise BitrixError(f"Bitrix24 error [{data['error']}]: {data.get('error_description', '')}")

        return data.get("result")

    async def list_all(self, method: str, params: dict[str, Any] | None = None) -> list[dict]:
        """Fetches all pages for list methods."""
        results = []
        start = 0
        base_params = dict(params or {})
        while True:
            base_params["start"] = start
            data = await self.call(method, base_params)
            if not data:
                break
            if isinstance(data, list):
                results.extend(data)
                if len(data) < 50:
                    break
                start += 50
            else:
                results.append(data)
                break
        return results

    async def close(self):
        await self._client.aclose()
