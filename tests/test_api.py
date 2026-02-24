"""API endpoint tests."""
import pytest


@pytest.mark.asyncio
async def test_root(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "OmniBot"
    assert data["version"] == "0.2.0"
    assert "tools_loaded" in data


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


@pytest.mark.asyncio
async def test_list_tools(client):
    resp = await client.get("/api/v1/tools")
    assert resp.status_code == 200
    tools = resp.json()
    assert isinstance(tools, list)
    # Should have at least the built-in knowledge_search tool
    names = [t["name"] for t in tools]
    assert "knowledge_search" in names
