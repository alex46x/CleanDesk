"""
tests/test_api.py — Integration tests for FastAPI endpoints.

Uses httpx AsyncClient with the in-process app (no real server needed).
"""

import asyncio
import os
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Override DB to an in-memory SQLite instance for isolation
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from backend.main import app
from backend.database.connection import init_db


@pytest_asyncio.fixture(scope="module")
async def client():
    """Start the app and yield a test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        await init_db()
        yield c


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Rules CRUD
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_create_rule(client: AsyncClient):
    payload = {
        "name": "Test Rule",
        "pattern": ".pdf",
        "match_type": "extension",
        "category": "TestDocs",
        "target_folder": "TestDocs",
        "priority": 10,
    }
    resp = await client.post("/api/rules/", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Rule"
    assert data["id"] > 0
    return data["id"]


@pytest.mark.asyncio
async def test_list_rules(client: AsyncClient):
    resp = await client.get("/api/rules/")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_update_rule(client: AsyncClient):
    # Create a rule first
    create_resp = await client.post("/api/rules/", json={
        "name": "Update Me",
        "pattern": ".txt",
        "match_type": "extension",
        "category": "Text",
        "target_folder": "Text",
        "priority": 5,
    })
    rule_id = create_resp.json()["id"]

    update_resp = await client.put(f"/api/rules/{rule_id}", json={"priority": 99})
    assert update_resp.status_code == 200
    assert update_resp.json()["priority"] == 99


@pytest.mark.asyncio
async def test_delete_rule(client: AsyncClient):
    create_resp = await client.post("/api/rules/", json={
        "name": "Delete Me",
        "pattern": ".xyz",
        "match_type": "extension",
        "category": "Junk",
        "target_folder": "Junk",
        "priority": 0,
    })
    rule_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/rules/{rule_id}")
    assert del_resp.status_code == 204

    # Verify gone
    list_resp = await client.get("/api/rules/")
    ids = [r["id"] for r in list_resp.json()]
    assert rule_id not in ids


@pytest.mark.asyncio
async def test_rule_not_found(client: AsyncClient):
    resp = await client.get("/api/rules/")
    # nonexistent rule update
    resp = await client.put("/api/rules/99999", json={"priority": 1})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_list_logs_empty(client: AsyncClient):
    resp = await client.get("/api/logs/")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_list_logs_status_filter(client: AsyncClient):
    resp = await client.get("/api/logs/?status=success")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Scan sessions
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_list_sessions_empty(client: AsyncClient):
    resp = await client.get("/api/scan/sessions")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_get_session_not_found(client: AsyncClient):
    resp = await client.get("/api/scan/sessions/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_start_scan_background(client: AsyncClient, tmp_path: Path):
    """Start a scan on a tiny temp dir; verify we get a session stub back."""
    # Create a few files
    (tmp_path / "test.pdf").write_bytes(b"pdf")
    (tmp_path / "image.jpg").write_bytes(b"img")

    resp = await client.post("/api/scan/start", json={
        "root_paths": [str(tmp_path)],
        "incremental": False,
    })
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] in ("started", "pending", "running", "done")


# ---------------------------------------------------------------------------
# Organize — validation
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_organize_missing_session(client: AsyncClient, tmp_path: Path):
    resp = await client.post("/api/organize/", json={
        "session_id": 99999,
        "destination_base": str(tmp_path),
        "dry_run": True,
    })
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scan_empty_paths_rejected(client: AsyncClient):
    resp = await client.post("/api/scan/start", json={"root_paths": []})
    assert resp.status_code == 422   # Pydantic validation error


@pytest.mark.asyncio
async def test_rule_invalid_match_type(client: AsyncClient):
    resp = await client.post("/api/rules/", json={
        "name": "Bad",
        "pattern": "*",
        "match_type": "invalid_type",   # Not in: glob|regex|extension
        "category": "X",
        "target_folder": "X",
        "priority": 0,
    })
    assert resp.status_code == 422
