from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum


class AgentPersonality(str, Enum):
    PHILOSOPHER = "philosopher"
    SCIENTIST = "scientist"
    ARTIST = "artist"
    ENGINEER = "engineer"
    HISTORIAN = "historian"
    PSYCHOLOGIST = "psychologist"


class Agent(BaseModel):
    id: str
    name: str
    personality: AgentPersonality
    system_prompt: str
    description: str
    avatar_url: Optional[str] = None
    is_active: bool = True
    
    class Config:
        use_enum_values = True


class AgentMessage(BaseModel):
    agent_id: str
    content: str
    timestamp: float
    turn_number: int
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentState(BaseModel):
    agent_id: str
    current_topic: Optional[str] = None
    mood: str = "neutral"
    energy_level: int = Field(ge=0, le=10, default=5)
    conversation_style: str = "balanced"
    last_message_time: Optional[float] = None 