import asyncio
import json
import logging
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from app.models.conversation import Conversation, Message, ConversationRequest
from app.models.agent import Agent
from app.services.llm_service import LLMService
from app.services.memory_service import MemoryService
from app.config import settings

logger = logging.getLogger(__name__)

class ConversationService:
    """대화 서비스 클래스"""
    
    def __init__(self):
        self.llm_service = LLMService()
        self.memory_service = MemoryService()
        self.active_conversations: Dict[str, Conversation] = {}
        self.conversation_callbacks: Dict[str, List[Callable]] = {}
        self.message_callbacks: List[Callable] = []
    
    def add_message_callback(self, callback: Callable):
        """메시지 콜백 함수 등록"""
        self.message_callbacks.append(callback)
        logger.info("메시지 콜백 함수가 등록되었습니다.")
    
    async def create_conversation(
        self,
        request: ConversationRequest
    ) -> Conversation:
        """새 대화 생성"""
        try:
            # 에이전트 정보 로드
            all_agents = self.get_agents()
            agent_map = {agent.id: agent for agent in all_agents}
            
            # 요청된 에이전트들 필터링
            selected_agents = []
            for agent_id in request.agent_ids:
                if agent_id in agent_map:
                    selected_agents.append(agent_map[agent_id])
                else:
                    logger.warning(f"존재하지 않는 에이전트 ID: {agent_id}")
            
            if not selected_agents:
                raise ValueError("유효한 에이전트가 없습니다.")
            
            # 대화 ID 생성
            conversation_id = f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.active_conversations)}"
            
            # 무제한 대화 설정 확인
            max_turns = request.max_turns
            is_unlimited = max_turns <= 0
            
            # 대화 객체 생성
            conversation = Conversation(
                id=conversation_id,
                topic=request.topic,
                title=request.title,
                agent_ids=request.agent_ids,
                max_turns=max_turns,
                current_turn=0,
                status="idle",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                messages=[],
                agents=[],
                agent_states={}
            )
            
            # 활성 대화에 추가
            self.active_conversations[conversation_id] = conversation
            
            # 메모리에 저장
            await self.memory_service.save_conversation(conversation)
            
            logger.info(f"대화 생성됨: {conversation_id}, 주제: {request.topic}")
            
            return conversation
            
        except Exception as e:
            logger.error(f"대화 생성 오류: {str(e)}")
            raise
    
    async def start_conversation(
        self,
        conversation_id: str,
        callback: Optional[Callable] = None
    ) -> bool:
        """대화 시작"""
        try:
            conversation = self.active_conversations.get(conversation_id)
            if not conversation:
                raise ValueError(f"대화를 찾을 수 없습니다: {conversation_id}")
            
            # 콜백 등록
            if callback:
                if conversation_id not in self.conversation_callbacks:
                    self.conversation_callbacks[conversation_id] = []
                self.conversation_callbacks[conversation_id].append(callback)
            
            # 시스템 프롬프트 생성
            system_prompt = self._create_system_prompt(conversation)
            
            # 대화 시작 메시지 추가
            start_message = Message(
                speaker="시스템",
                content=f"대화가 시작되었습니다. 주제: {conversation.topic}",
                timestamp=datetime.now(),
                turn_number=0
            )
            conversation.messages.append(start_message)
            
            # 대화 상태 변경
            conversation.status = "active"
            
            # 첫 번째 에이전트가 발화
            all_agents = self.get_agents()
            agent_map = {agent.id: agent for agent in all_agents}
            current_agent = agent_map[conversation.agent_ids[0]]
            await self._agent_speak(conversation, current_agent, system_prompt)
            
            # 자동으로 대화 계속 진행을 별도 태스크로 실행
            asyncio.create_task(self._auto_continue_conversation(conversation_id))
            
            logger.info(f"대화 시작됨: {conversation_id}")
            return True
            
        except Exception as e:
            logger.error(f"대화 시작 오류: {str(e)}")
            return False
    
    async def _auto_continue_conversation(self, conversation_id: str):
        """자동으로 대화 계속 진행"""
        try:
            while True:
                conversation = self.active_conversations.get(conversation_id)
                if not conversation:
                    break
                
                # 대화 상태 확인 (중지, 종료 상태면 대화 중단)
                if conversation.status in ["stopped", "ended"]:
                    logger.info(f"대화 상태가 {conversation.status}이므로 자동 진행을 중단합니다: {conversation_id}")
                    break
                
                # 대화 종료 조건 확인
                if self._should_end_conversation(conversation):
                    await self.end_conversation(conversation_id)
                    break
                
                # 시스템 프롬프트 생성
                system_prompt = self._create_system_prompt(conversation)
                
                # 다음 발화할 에이전트 선택
                next_agent = self._select_next_agent(conversation)
                await self._agent_speak(conversation, next_agent, system_prompt)
                
                # 대화 간격 설정
                await asyncio.sleep(settings.conversation_turn_interval)
                
        except Exception as e:
            logger.error(f"자동 대화 진행 오류: {str(e)}")
            await self.end_conversation(conversation_id)
    
    async def continue_conversation(self, conversation_id: str) -> bool:
        """대화 계속"""
        try:
            conversation = self.active_conversations.get(conversation_id)
            if not conversation:
                raise ValueError(f"대화를 찾을 수 없습니다: {conversation_id}")
            
            # 대화 종료 조건 확인
            if self._should_end_conversation(conversation):
                await self.end_conversation(conversation_id)
                return False
            
            # 시스템 프롬프트 생성
            system_prompt = self._create_system_prompt(conversation)
            
            # 다음 발화할 에이전트 선택
            next_agent = self._select_next_agent(conversation)
            await self._agent_speak(conversation, next_agent, system_prompt)
            
            return True
            
        except Exception as e:
            logger.error(f"대화 계속 오류: {str(e)}")
            return False
    


    async def stop_conversation(self, conversation_id: str) -> bool:
        """대화 중지"""
        try:
            conversation = self.active_conversations.get(conversation_id)
            if not conversation:
                raise ValueError(f"대화를 찾을 수 없습니다: {conversation_id}")
            
            # 대화 상태 변경
            conversation.status = "stopped"
            
            # 중지 메시지 추가
            stop_message = Message(
                speaker="시스템",
                content="대화가 중지되었습니다.",
                timestamp=datetime.now(),
                turn_number=conversation.current_turn + 1
            )
            conversation.messages.append(stop_message)
            
            # 메모리에 저장
            await self.memory_service.save_conversation(conversation)
            
            logger.info(f"대화 중지됨: {conversation_id}")
            return True
            
        except Exception as e:
            logger.error(f"대화 중지 오류: {str(e)}")
            return False

    async def end_conversation(self, conversation_id: str) -> bool:
        """대화 종료"""
        try:
            conversation = self.active_conversations.get(conversation_id)
            if not conversation:
                return False
            
            # 대화 상태 변경
            conversation.status = "ended"
            conversation.ended_at = datetime.now()
            
            # 종료 메시지 추가
            end_message = Message(
                speaker="시스템",
                content="대화가 종료되었습니다.",
                timestamp=datetime.now(),
                turn_number=conversation.current_turn + 1
            )
            conversation.messages.append(end_message)
            
            # 메모리에 저장
            await self.memory_service.save_conversation(conversation)
            
            # 활성 대화에서 제거
            del self.active_conversations[conversation_id]
            
            # 콜백 정리
            if conversation_id in self.conversation_callbacks:
                del self.conversation_callbacks[conversation_id]
            
            logger.info(f"대화 종료됨: {conversation_id}")
            return True
            
        except Exception as e:
            logger.error(f"대화 종료 오류: {str(e)}")
            return False
    
    async def _agent_speak(
        self,
        conversation: Conversation,
        agent: Agent,
        system_prompt: str
    ):
        """에이전트 발화"""
        try:
            # 에이전트별 시스템 프롬프트 생성
            agent_system_prompt = f"{system_prompt}\n\n{agent.system_prompt}"
            
            # 디버깅을 위한 로깅
            logger.info(f"에이전트 {agent.name} 발화 시작")
            logger.info(f"기본 시스템 프롬프트: {system_prompt[:100]}...")
            logger.info(f"에이전트 시스템 프롬프트: {agent.system_prompt[:200]}...")
            logger.info(f"최종 시스템 프롬프트: {agent_system_prompt[:300]}...")
            
            # 대화 컨텍스트 생성
            context_messages = self._create_context_messages(conversation)
            logger.info(f"컨텍스트 메시지 수: {len(context_messages)}")
            for i, msg in enumerate(context_messages[-3:]):  # 최근 3개 메시지만 로깅
                logger.info(f"컨텍스트 메시지 {i}: {msg.speaker}: {msg.content[:50]}...")
            
            # 스트림 설정 확인
            if settings.enable_streaming:
                # 스트림 콜백 함수 정의
                async def stream_callback(chunk: str, full_content: str):
                    # 스트림 메시지 생성 (임시)
                    stream_message = Message(
                        speaker=agent.name,
                        content=full_content,
                        agent_id=agent.id,
                        timestamp=datetime.now(),
                        turn_number=conversation.current_turn + 1,
                        is_streaming=True
                    )
                    
                    # WebSocket으로 스트림 업데이트 전송
                    await self._execute_callbacks(conversation.id, stream_message, is_stream=True)
                
                # LLM 스트림 응답 생성
                response = await self.llm_service.generate_response_stream(
                    messages=context_messages,
                    system_prompt=agent_system_prompt,
                    stream_callback=stream_callback
                )
            else:
                # 비스트림 응답 생성
                response = await self.llm_service.generate_response(
                    messages=context_messages,
                    system_prompt=agent_system_prompt,
                    callback=self._log_agent_response
                )
            
            # 최종 메시지 생성 및 추가
            message = Message(
                speaker=agent.name,
                content=response,
                agent_id=agent.id,
                timestamp=datetime.now(),
                turn_number=conversation.current_turn + 1
            )
            conversation.messages.append(message)
            
            # 턴 수 증가
            conversation.current_turn += 1
            
            # 메모리에 저장
            await self.memory_service.save_conversation(conversation)
            
            # 최종 콜백 실행
            await self._execute_callbacks(conversation.id, message)
            
            logger.info(f"에이전트 발화 완료: {agent.name} - {response[:50]}...")
            
        except Exception as e:
            logger.error(f"에이전트 발화 오류: {str(e)}")
            raise
    
    def _create_system_prompt(self, conversation: Conversation) -> str:
        """시스템 프롬프트 생성"""
        # 무제한 대화 여부 확인
        is_unlimited = conversation.max_turns <= 0
        turn_info = "무제한" if is_unlimited else f"{conversation.current_turn}/{conversation.max_turns}"
        
        # 에이전트 이름 가져오기
        all_agents = self.get_agents()
        agent_map = {agent.id: agent for agent in all_agents}
        agent_names = [agent_map.get(agent_id, agent_id).name for agent_id in conversation.agent_ids]
        
        prompt = f"""당신은 AI 대화 시스템의 참여자입니다.

대화 정보:
- 주제: {conversation.topic}
- 현재 턴: {turn_info}
- 참여자: {', '.join(agent_names)}

대화 규칙:
1. 주제 "{conversation.topic}"에 집중하여 관련성 있는 대화를 이어가세요
2. 다른 참여자의 발화에 적절히 반응하되, 주제에서 벗어나지 마세요
3. 주제와 관련된 깊이 있는 논의를 하세요
4. 무제한 대화인 경우 서두르지 말고 충분히 대화를 이어가세요
5. 자신의 이름을 반복해서 언급하지 마세요
6. 응답 시작에 이름을 붙이지 마세요 (예: "몽키 D 루피:", "이마케팅:" 등)
7. 자연스럽게 대화에 참여하세요

현재 대화 상황을 파악하고 주제에 맞는 적절한 응답을 생성하세요."""

        return prompt
    
    def _create_context_messages(self, conversation: Conversation) -> List[Message]:
        """대화 컨텍스트 메시지 생성"""
        # 최근 메시지들만 사용 (컨텍스트 제한)
        context_limit = settings.conversation_context_limit
        recent_messages = conversation.messages[-context_limit:] if context_limit > 0 else conversation.messages
        
        return recent_messages
    
    def _select_next_agent(self, conversation: Conversation) -> Agent:
        """다음 발화할 에이전트 선택"""
        # 라운드 로빈 방식으로 에이전트 선택
        agent_index = conversation.current_turn % len(conversation.agent_ids)
        agent_id = conversation.agent_ids[agent_index]
        
        # 에이전트 정보 가져오기
        all_agents = self.get_agents()
        agent_map = {agent.id: agent for agent in all_agents}
        return agent_map[agent_id]
    
    def _should_end_conversation(self, conversation: Conversation) -> bool:
        """대화 종료 여부 확인"""
        # 무제한 대화가 아닌 경우 턴 수 확인
        is_unlimited = conversation.max_turns <= 0
        if not is_unlimited:
            return conversation.current_turn >= conversation.max_turns
        
        # 무제한 대화는 수동으로만 종료
        return False
    
    async def _execute_callbacks(self, conversation_id: str, message: Message, is_stream: bool = False):
        """콜백 함수 실행"""
        # 대화별 콜백 실행
        if conversation_id in self.conversation_callbacks:
            for callback in self.conversation_callbacks[conversation_id]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(message)
                    else:
                        callback(message)
                except Exception as e:
                    logger.error(f"대화 콜백 실행 오류: {str(e)}")
        
        # 전역 메시지 콜백 실행
        for callback in self.message_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(conversation_id, message)
                else:
                    callback(conversation_id, message)
            except Exception as e:
                logger.error(f"메시지 콜백 실행 오류: {str(e)}")
    
    def _log_agent_response(self, response: str):
        """에이전트 응답 로깅"""
        logger.info(f"에이전트 응답: {response[:100]}...")
    
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """대화 조회"""
        return self.active_conversations.get(conversation_id)
    
    def get_all_conversations(self) -> List[Conversation]:
        """모든 활성 대화 조회"""
        return list(self.active_conversations.values())
    
    def get_agents(self) -> List[Agent]:
        """모든 에이전트 조회"""
        try:
            # agents.json 파일에서 에이전트 정보 로드
            import json
            import os
            
            agents_file = os.path.join(os.path.dirname(__file__), '..', '..', 'agents.json')
            with open(agents_file, 'r', encoding='utf-8') as f:
                agents_data = json.load(f)
            
            agents = []
            for agent_id, agent_data in agents_data["agents"].items():
                agent = Agent(
                    id=agent_id,
                    name=agent_data['name'],
                    personality=agent_data['personality'],
                    description=agent_data['description'],
                    system_prompt=agent_data['system_prompt']
                )
                agents.append(agent)
            
            return agents
            
        except Exception as e:
            logger.error(f"에이전트 로드 오류: {str(e)}")
            return []
    
    async def delete_conversation(self, conversation_id: str) -> bool:
        """대화 삭제"""
        try:
            conversation = self.active_conversations.get(conversation_id)
            if not conversation:
                return False
            
            # 메모리에서 삭제
            await self.memory_service.delete_conversation(conversation_id)
            
            # 활성 대화에서 제거
            del self.active_conversations[conversation_id]
            
            # 콜백 정리
            if conversation_id in self.conversation_callbacks:
                del self.conversation_callbacks[conversation_id]
            
            logger.info(f"대화 삭제됨: {conversation_id}")
            return True
            
        except Exception as e:
            logger.error(f"대화 삭제 오류: {str(e)}")
            return False


# 전역 대화 서비스 인스턴스
conversation_service = ConversationService() 