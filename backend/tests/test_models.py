from app.models.conversation import Conversation, ConversationRequest

def test_conversation_model_fields():
    conv = Conversation(
        id="testid",
        title="테스트",
        status="idle",
        agent_ids=["agent1"],
        current_turn=0,
        max_turns=10,
        messages=[],
        created_at="2024-07-01T00:00:00",
        updated_at="2024-07-01T00:00:00",
        agents=[],
        agent_states={}
    )
    assert conv.id == "testid"
    assert conv.status == "idle"

def test_conversation_request_validation():
    req = ConversationRequest(
        title="테스트",
        agent_ids=["agent1"],
        max_turns=10,
        topic="테스트 주제"
    )
    assert req.max_turns == 10 