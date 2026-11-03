from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, email: str) -> str:
    res = await client.post(
        "/v1/auth/register",
        json={"email": email, "password": "securepass1"},
    )
    assert res.status_code == 201
    return res.json()["access_token"]


@pytest.mark.asyncio
async def test_user_cannot_access_other_threads(client: AsyncClient) -> None:
    token_a = await _register(client, "usera@example.com")
    token_b = await _register(client, "userb@example.com")

    create = await client.post(
        "/v1/threads",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"title": "A's secret"},
    )
    assert create.status_code == 201
    thread_id = create.json()["id"]

    forbidden = await client.get(
        f"/v1/threads/{thread_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert forbidden.status_code == 404

    msgs = await client.get(
        f"/v1/threads/{thread_id}/messages",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert msgs.status_code == 404


@pytest.mark.asyncio
async def test_thread_crud(client: AsyncClient) -> None:
    token = await _register(client, "threader@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    created = await client.post("/v1/threads", headers=headers, json={"title": "Research"})
    assert created.status_code == 201
    thread_id = created.json()["id"]

    listed = await client.get("/v1/threads", headers=headers)
    assert listed.status_code == 200
    assert any(t["id"] == thread_id for t in listed.json())

    renamed = await client.patch(
        f"/v1/threads/{thread_id}",
        headers=headers,
        json={"title": "Renamed"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "Renamed"

    deleted = await client.delete(f"/v1/threads/{thread_id}", headers=headers)
    assert deleted.status_code == 204
