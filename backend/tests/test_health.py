from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_healthz(client: AsyncClient) -> None:
    res = await client.get("/healthz")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
