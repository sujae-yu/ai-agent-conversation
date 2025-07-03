def test_agent_system_prompt_dynamic(monkeypatch):
    from app.services.conversation_service import ConversationService
    from app.models.conversation import Conversation
    from app.models.agent import Agent
    from datetime import datetime

    # 테스트용 에이전트
    agent = Agent(
        id="test",
        name="테스트",
        personality="engineer",
        system_prompt="테스트 프롬프트 {system_area}",
        system_area="대화는 최대 {max_turns}턴까지 진행됩니다. {unlimited_message}",
        description="테스트용"
    )

    # ConversationService 인스턴스
    service = ConversationService()

    # 대화 객체 (무제한 아님)
    conversation = Conversation(
        id="conv1",
        topic="테스트",
        agent_ids=["test"],
        max_turns=10,
        current_turn=0,
        status="active",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        messages=[],
        agents=[agent],
        agent_states={}
    )

    # system_area 동적 치환
    max_turns = conversation.max_turns
    is_unlimited = max_turns <= 0
    unlimited_message = "무제한 대화가 가능합니다." if is_unlimited else ""
    system_area = agent.system_area.format(max_turns=max_turns, unlimited_message=unlimited_message)
    agent_system_prompt = agent.system_prompt.format(system_area=system_area)
    assert "10턴" in agent_system_prompt
    assert "무제한" not in agent_system_prompt

    # 대화 객체 (무제한)
    conversation.max_turns = 0
    max_turns = conversation.max_turns
    is_unlimited = max_turns <= 0
    unlimited_message = "무제한 대화가 가능합니다." if is_unlimited else ""
    system_area = agent.system_area.format(max_turns=max_turns, unlimited_message=unlimited_message)
    agent_system_prompt = agent.system_prompt.format(system_area=system_area)
    assert "무제한 대화가 가능합니다." in agent_system_prompt 