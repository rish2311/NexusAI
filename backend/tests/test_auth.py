from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient) -> None:
    res = await client.post(
        "/v1/auth/register",
        json={"email": "alice@example.com", "password": "securepass1"},
    )
    assert res.status_code == 201
    data = res.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient) -> None:
    payload = {"email": "bob@example.com", "password": "securepass1"}
    assert (await client.post("/v1/auth/register", json=payload)).status_code == 201
    res = await client.post("/v1/auth/register", json=payload)
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_login_success_and_bad_password(client: AsyncClient) -> None:
    await client.post(
        "/v1/auth/register",
        json={"email": "carol@example.com", "password": "securepass1"},
    )
    ok = await client.post(
        "/v1/auth/login",
        json={"email": "carol@example.com", "password": "securepass1"},
    )
    assert ok.status_code == 200

    bad = await client.post(
        "/v1/auth/login",
        json={"email": "carol@example.com", "password": "wrongpass1"},
    )
    assert bad.status_code == 401


@pytest.mark.asyncio
async def test_refresh_rotation_invalidates_old(client: AsyncClient) -> None:
    reg = await client.post(
        "/v1/auth/register",
        json={"email": "dave@example.com", "password": "securepass1"},
    )
    old_refresh = reg.json()["refresh_token"]
    rotated = await client.post("/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert rotated.status_code == 200
    new_refresh = rotated.json()["refresh_token"]
    assert new_refresh != old_refresh

    reuse = await client.post("/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert reuse.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_rejects_missing_token(client: AsyncClient) -> None:
    res = await client.get("/v1/auth/me")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_me_with_token(client: AsyncClient) -> None:
    reg = await client.post(
        "/v1/auth/register",
        json={"email": "erin@example.com", "password": "securepass1"},
    )
    token = reg.json()["access_token"]
    me = await client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "erin@example.com"


@pytest.mark.asyncio
async def test_logout(client: AsyncClient) -> None:
    reg = await client.post(
        "/v1/auth/register",
        json={"email": "frank@example.com", "password": "securepass1"},
    )
    refresh = reg.json()["refresh_token"]
    out = await client.post("/v1/auth/logout", json={"refresh_token": refresh})
    assert out.status_code == 204
    reuse = await client.post("/v1/auth/refresh", json={"refresh_token": refresh})
    assert reuse.status_code == 401
