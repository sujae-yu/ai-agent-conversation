from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from abc import ABC, abstractmethod
import asyncio
from .agent import AgentMessage, AgentState
from .conversation import Conversation


class MemoryEntry(BaseModel):
    conversation_id: str
    agent_id: str
    message: AgentMessage
    context: Dict[str, Any] = Field(default_factory=dict)
    importance_score: float = Field(ge=0.0, le=1.0, default=0.5)
    created_at: datetime


class MemoryInterface(ABC):
    """메모리 시스템 인터페이스"""
    
    @abstractmethod
    async def store_message(self, conversation_id: str, agent_id: str, message: AgentMessage, context: Dict[str, Any] = None) -> None:
        """메시지를 메모리에 저장"""
        pass
    
    @abstractmethod
    async def get_conversation_history(self, conversation_id: str, limit: int = 50) -> List[MemoryEntry]:
        """대화 히스토리 조회"""
        pass
    
    @abstractmethod
    async def get_agent_memory(self, agent_id: str, conversation_id: str, limit: int = 20) -> List[MemoryEntry]:
        """특정 에이전트의 메모리 조회"""
        pass
    
    @abstractmethod
    async def get_relevant_context(self, conversation_id: str, current_topic: str, limit: int = 10) -> List[MemoryEntry]:
        """현재 주제와 관련된 컨텍스트 조회"""
        pass
    
    @abstractmethod
    async def clear_conversation_memory(self, conversation_id: str) -> None:
        """대화 메모리 삭제"""
        pass


class InMemoryStorage(MemoryInterface):
    """인메모리 메모리 저장소"""
    
    def __init__(self):
        self.memories: Dict[str, List[MemoryEntry]] = {}
        self.lock = asyncio.Lock()
    
    async def store_message(self, conversation_id: str, agent_id: str, message: AgentMessage, context: Dict[str, Any] = None) -> None:
        async with self.lock:
            if conversation_id not in self.memories:
                self.memories[conversation_id] = []
            
            entry = MemoryEntry(
                conversation_id=conversation_id,
                agent_id=agent_id,
                message=message,
                context=context or {},
                created_at=datetime.now()
            )
            self.memories[conversation_id].append(entry)
    
    async def get_conversation_history(self, conversation_id: str, limit: int = 50) -> List[MemoryEntry]:
        async with self.lock:
            if conversation_id not in self.memories:
                return []
            return self.memories[conversation_id][-limit:]
    
    async def get_agent_memory(self, agent_id: str, conversation_id: str, limit: int = 20) -> List[MemoryEntry]:
        async with self.lock:
            if conversation_id not in self.memories:
                return []
            
            agent_memories = [
                entry for entry in self.memories[conversation_id]
                if entry.agent_id == agent_id
            ]
            return agent_memories[-limit:]
    
    async def get_relevant_context(self, conversation_id: str, current_topic: str, limit: int = 10) -> List[MemoryEntry]:
        async with self.lock:
            if conversation_id not in self.memories:
                return []
            
            # 간단한 키워드 기반 관련성 검색
            relevant_entries = []
            topic_keywords = current_topic.lower().split()
            
            for entry in self.memories[conversation_id]:
                content_lower = entry.message.content.lower()
                if any(keyword in content_lower for keyword in topic_keywords):
                    relevant_entries.append(entry)
            
            return relevant_entries[-limit:]
    
    async def clear_conversation_memory(self, conversation_id: str) -> None:
        async with self.lock:
            if conversation_id in self.memories:
                del self.memories[conversation_id] 