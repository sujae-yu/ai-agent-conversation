from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
from .agent import AgentMessage, AgentState


class ConversationStatus(str, Enum):
    IDLE = "idle"
    ACTIVE = "active"
    STOPPED = "stopped"
    ENDED = "ended"
    ERROR = "error"


class Message(BaseModel):
    """대화 메시지 모델"""
    speaker: str
    content: str
    agent_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    turn_number: Optional[int] = None
    is_streaming: Optional[bool] = False


class Conversation(BaseModel):
    id: str
    topic: str
    agents: List["Agent"] = Field(default_factory=list)
    status: str = "active"
    created_at: datetime = Field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    messages: List[Message] = Field(default_factory=list)
    current_turn: int = 0
    max_turns: int = 10  # 0 = 무제한, 10-50 = 제한
    is_unlimited: bool = False
    
    # 기존 필드들 (호환성을 위해 유지)
    title: Optional[str] = None
    updated_at: Optional[datetime] = None
    agent_ids: Optional[List[str]] = None
    agent_states: Dict[str, AgentState] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True


class ConversationRequest(BaseModel):
    topic: str
    agent_ids: List[str]
    max_turns: int = 10  # 0 = 무제한, 10-50 = 제한
    title: Optional[str] = None


class ConversationResponse(BaseModel):
    conversation_id: str
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None


class ConversationUpdate(BaseModel):
    status: Optional[str] = None
    max_turns: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


# Agent 클래스 import를 위한 순환 참조 해결
from .agent import Agent
Conversation.model_rebuild() 