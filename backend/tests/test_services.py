import pytest
from app.services.conversation_service import conversation_service
from app.models.conversation import ConversationRequest

@pytest.mark.asyncio
async def test_create_and_delete_conversation():
    req = ConversationRequest(
        title="테스트",
        agent_ids=["agent1"],
        max_turns=10,
        topic="테스트 주제"
    )
    conv = await conversation_service.create_conversation(req)
    assert conv.id
    assert conv.title == "테스트"
    # 삭제
    result = await conversation_service.delete_conversation(conv.id)
    assert result is True

@pytest.mark.asyncio
async def test_delete_nonexistent_conversation():
    result = await conversation_service.delete_conversation("nonexistent_id")
    assert result is False 