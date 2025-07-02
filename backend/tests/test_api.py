import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_root():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.get("/")
    assert resp.status_code == 200
    assert "AI Agent NPC" in resp.json()["message"]

@pytest.mark.asyncio
async def test_get_agents():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.get("/api/agents")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

@pytest.mark.asyncio
async def test_get_conversations():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.get("/api/conversations")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

@pytest.mark.asyncio
async def test_create_and_delete_conversation():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # 에이전트 목록 조회
        agents_resp = await ac.get("/api/agents")
        agents = agents_resp.json()
        agent_id = agents[0]["id"] if agents else "agent1"
        # 대화 생성
        req = {
            "title": "테스트",
            "agent_ids": [agent_id],
            "max_turns": 10,
            "topic": "테스트 주제"
        }
        create_resp = await ac.post("/api/conversations", json=req)
        assert create_resp.status_code == 200
        conv_id = create_resp.json()["conversation_id"]
        # 대화 조회
        get_resp = await ac.get(f"/api/conversations/{conv_id}")
        assert get_resp.status_code == 200
        # 대화 삭제
        del_resp = await ac.delete(f"/api/conversations/{conv_id}")
        assert del_resp.status_code == 200
        # 삭제 후 조회 시 404
        get_resp2 = await ac.get(f"/api/conversations/{conv_id}")
        assert get_resp2.status_code == 404 