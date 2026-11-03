from __future__ import annotations

import json
import uuid

import pytest
from httpx import AsyncClient


async def _auth(client: AsyncClient, email: str) -> str:
    res = await client.post(
        "/v1/auth/register",
        json={"email": email, "password": "securepass1"},
    )
    return res.json()["access_token"]


def _parse_sse(raw: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    event_name = "message"
    for line in raw.splitlines():
        if line.startswith("event:"):
            event_name = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            payload = json.loads(line.split(":", 1)[1].strip())
            events.append((event_name, payload))
            event_name = "message"
    return events


@pytest.mark.asyncio
async def test_streaming_chat_mocked(client: AsyncClient) -> None:
    token = await _auth(client, "streamer@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    thread = await client.post("/v1/threads", headers=headers, json={"title": "New chat"})
    thread_id = thread.json()["id"]

    res = await client.post(
        "/v1/chat/stream",
        headers=headers,
        json={
            "thread_id": thread_id,
            "message": "Explain LangGraph briefly",
            "idempotency_key": f"key-{uuid.uuid4()}",
        },
    )
    assert res.status_code == 200
    events = _parse_sse(res.text)
    kinds = [e[0] for e in events]
    assert "token" in kinds
    assert "done" in kinds
    done = next(e[1] for e in events if e[0] == "done")
    assert done["usage"]["tier"] == "free"
    assert done["usage"]["provider"] == "mock"

    msgs = await client.get(f"/v1/threads/{thread_id}/messages", headers=headers)
    assert msgs.status_code == 200
    items = msgs.json()["items"]
    assert len(items) >= 2
    assert items[0]["role"] == "user"
    assert items[1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_idempotent_duplicate_does_not_double_write(client: AsyncClient) -> None:
    token = await _auth(client, "idem@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    thread = await client.post("/v1/threads", headers=headers, json={"title": "New chat"})
    thread_id = thread.json()["id"]
    key = f"idem-{uuid.uuid4()}"
    body = {
        "thread_id": thread_id,
        "message": "Hello once",
        "idempotency_key": key,
    }

    first = await client.post("/v1/chat/stream", headers=headers, json=body)
    assert first.status_code == 200
    second = await client.post("/v1/chat/stream", headers=headers, json=body)
    assert second.status_code == 200

    msgs = await client.get(f"/v1/threads/{thread_id}/messages", headers=headers)
    items = msgs.json()["items"]
    # One user + one assistant (not doubled)
    assert len([m for m in items if m["role"] == "user"]) == 1
    assert len([m for m in items if m["role"] == "assistant"]) == 1


@pytest.mark.asyncio
async def test_user_cannot_stream_into_other_thread(client: AsyncClient) -> None:
    token_a = await _auth(client, "owner@example.com")
    token_b = await _auth(client, "intruder@example.com")
    thread = await client.post(
        "/v1/threads",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"title": "Private"},
    )
    thread_id = thread.json()["id"]

    res = await client.post(
        "/v1/chat/stream",
        headers={"Authorization": f"Bearer {token_b}"},
        json={
            "thread_id": thread_id,
            "message": "Hijack attempt",
            "idempotency_key": f"atk-{uuid.uuid4()}",
        },
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_chat_stop_endpoint(client: AsyncClient) -> None:
    token = await _auth(client, "stopper@example.com")
    res = await client.post(
        "/v1/chat/stop",
        headers={"Authorization": f"Bearer {token}"},
        json={"run_id": str(uuid.uuid4())},
    )
    assert res.status_code == 204
