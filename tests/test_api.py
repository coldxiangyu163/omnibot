import pytest


@pytest.mark.asyncio
async def test_root(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "OmniBot"


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_knowledge_stats(client):
    resp = await client.get("/api/v1/knowledge/stats")
    assert resp.status_code == 200
    assert "total_chunks" in resp.json()
