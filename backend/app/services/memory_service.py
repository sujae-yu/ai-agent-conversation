import asyncio
import json
import logging
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, String, Text, DateTime, Float, JSON
from datetime import datetime
import os

from ..config import settings
from ..models.memory import MemoryInterface, MemoryEntry, InMemoryStorage
from ..models.agent import AgentMessage
from ..models.conversation import Conversation


Base = declarative_base()

logger = logging.getLogger(__name__)


class MemoryEntryModel(Base):
    """PostgreSQL 메모리 엔트리 모델"""
    __tablename__ = "memory_entries"
    
    id = Column(String, primary_key=True)
    conversation_id = Column(String, nullable=False, index=True)
    agent_id = Column(String, nullable=False, index=True)
    message_content = Column(Text, nullable=False)
    message_timestamp = Column(Float, nullable=False)
    message_turn_number = Column(String, nullable=False)
    message_metadata = Column(JSON, nullable=True)
    context = Column(JSON, nullable=True)
    importance_score = Column(Float, default=0.5)
    created_at = Column(DateTime, default=datetime.utcnow)


class RedisStorage(MemoryInterface):
    """Redis 메모리 저장소"""
    
    def __init__(self):
        self.redis_client = redis.from_url(settings.redis_url)
    
    async def store_message(self, conversation_id: str, agent_id: str, message: AgentMessage, context: Dict[str, Any] = None) -> None:
        try:
            entry_data = {
                "conversation_id": conversation_id,
                "agent_id": agent_id,
                "message_content": message.content,
                "message_timestamp": message.timestamp,
                "message_turn_number": message.turn_number,
                "message_metadata": message.metadata,
                "context": context or {},
                "importance_score": 0.5,
                "created_at": datetime.now().isoformat()
            }
            
            # Redis에 저장
            key = f"memory:{conversation_id}:{message.timestamp}"
            await self.redis_client.hset(key, mapping=entry_data)
            await self.redis_client.expire(key, 86400)  # 24시간 만료
            
            # 대화별 인덱스 추가
            await self.redis_client.lpush(f"conversation:{conversation_id}", key)
            
        except Exception as e:
            raise Exception(f"Redis 저장 오류: {str(e)}")
    
    async def get_conversation_history(self, conversation_id: str, limit: int = 50) -> List[MemoryEntry]:
        try:
            keys = await self.redis_client.lrange(f"conversation:{conversation_id}", 0, limit - 1)
            entries = []
            
            for key in keys:
                data = await self.redis_client.hgetall(key)
                if data:
                    message = AgentMessage(
                        agent_id=data[b"agent_id"].decode(),
                        content=data[b"message_content"].decode(),
                        timestamp=float(data[b"message_timestamp"]),
                        turn_number=int(data[b"message_turn_number"]),
                        metadata=json.loads(data[b"message_metadata"]) if data[b"message_metadata"] else {}
                    )
                    
                    entry = MemoryEntry(
                        conversation_id=data[b"conversation_id"].decode(),
                        agent_id=data[b"agent_id"].decode(),
                        message=message,
                        context=json.loads(data[b"context"]) if data[b"context"] else {},
                        importance_score=float(data[b"importance_score"]),
                        created_at=datetime.fromisoformat(data[b"created_at"].decode())
                    )
                    entries.append(entry)
            
            return entries
            
        except Exception as e:
            raise Exception(f"Redis 조회 오류: {str(e)}")
    
    async def get_agent_memory(self, agent_id: str, conversation_id: str, limit: int = 20) -> List[MemoryEntry]:
        try:
            keys = await self.redis_client.lrange(f"conversation:{conversation_id}", 0, -1)
            entries = []
            
            for key in keys:
                data = await self.redis_client.hgetall(key)
                if data and data[b"agent_id"].decode() == agent_id:
                    message = AgentMessage(
                        agent_id=data[b"agent_id"].decode(),
                        content=data[b"message_content"].decode(),
                        timestamp=float(data[b"message_timestamp"]),
                        turn_number=int(data[b"message_turn_number"]),
                        metadata=json.loads(data[b"message_metadata"]) if data[b"message_metadata"] else {}
                    )
                    
                    entry = MemoryEntry(
                        conversation_id=data[b"conversation_id"].decode(),
                        agent_id=data[b"agent_id"].decode(),
                        message=message,
                        context=json.loads(data[b"context"]) if data[b"context"] else {},
                        importance_score=float(data[b"importance_score"]),
                        created_at=datetime.fromisoformat(data[b"created_at"].decode())
                    )
                    entries.append(entry)
                    
                    if len(entries) >= limit:
                        break
            
            return entries
            
        except Exception as e:
            raise Exception(f"Redis 에이전트 메모리 조회 오류: {str(e)}")
    
    async def get_relevant_context(self, conversation_id: str, current_topic: str, limit: int = 10) -> List[MemoryEntry]:
        # Redis에서는 간단한 키워드 검색 구현
        try:
            all_entries = await self.get_conversation_history(conversation_id, 100)
            topic_keywords = current_topic.lower().split()
            relevant_entries = []
            
            for entry in all_entries:
                content_lower = entry.message.content.lower()
                if any(keyword in content_lower for keyword in topic_keywords):
                    relevant_entries.append(entry)
                    if len(relevant_entries) >= limit:
                        break
            
            return relevant_entries
            
        except Exception as e:
            raise Exception(f"Redis 컨텍스트 조회 오류: {str(e)}")
    
    async def clear_conversation_memory(self, conversation_id: str) -> None:
        try:
            keys = await self.redis_client.lrange(f"conversation:{conversation_id}", 0, -1)
            if keys:
                await self.redis_client.delete(*keys)
            await self.redis_client.delete(f"conversation:{conversation_id}")
            
        except Exception as e:
            raise Exception(f"Redis 메모리 삭제 오류: {str(e)}")


class PostgreSQLStorage(MemoryInterface):
    """PostgreSQL 메모리 저장소"""
    
    def __init__(self):
        self.engine = create_async_engine(settings.postgresql_url)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
    
    async def store_message(self, conversation_id: str, agent_id: str, message: AgentMessage, context: Dict[str, Any] = None) -> None:
        try:
            async with self.async_session() as session:
                entry = MemoryEntryModel(
                    id=f"{conversation_id}_{message.timestamp}_{agent_id}",
                    conversation_id=conversation_id,
                    agent_id=agent_id,
                    message_content=message.content,
                    message_timestamp=message.timestamp,
                    message_turn_number=str(message.turn_number),
                    message_metadata=message.metadata,
                    context=context or {},
                    importance_score=0.5,
                    created_at=datetime.now()
                )
                session.add(entry)
                await session.commit()
                
        except Exception as e:
            raise Exception(f"PostgreSQL 저장 오류: {str(e)}")
    
    async def get_conversation_history(self, conversation_id: str, limit: int = 50) -> List[MemoryEntry]:
        try:
            async with self.async_session() as session:
                from sqlalchemy import select
                
                stmt = select(MemoryEntryModel).where(
                    MemoryEntryModel.conversation_id == conversation_id
                ).order_by(MemoryEntryModel.created_at.desc()).limit(limit)
                
                result = await session.execute(stmt)
                entries = []
                
                for row in result.scalars():
                    message = AgentMessage(
                        agent_id=row.agent_id,
                        content=row.message_content,
                        timestamp=row.message_timestamp,
                        turn_number=int(row.message_turn_number),
                        metadata=row.message_metadata or {}
                    )
                    
                    entry = MemoryEntry(
                        conversation_id=row.conversation_id,
                        agent_id=row.agent_id,
                        message=message,
                        context=row.context or {},
                        importance_score=row.importance_score,
                        created_at=row.created_at
                    )
                    entries.append(entry)
                
                return entries[::-1]  # 시간순 정렬
                
        except Exception as e:
            raise Exception(f"PostgreSQL 조회 오류: {str(e)}")
    
    async def get_agent_memory(self, agent_id: str, conversation_id: str, limit: int = 20) -> List[MemoryEntry]:
        try:
            async with self.async_session() as session:
                from sqlalchemy import select
                
                stmt = select(MemoryEntryModel).where(
                    MemoryEntryModel.conversation_id == conversation_id,
                    MemoryEntryModel.agent_id == agent_id
                ).order_by(MemoryEntryModel.created_at.desc()).limit(limit)
                
                result = await session.execute(stmt)
                entries = []
                
                for row in result.scalars():
                    message = AgentMessage(
                        agent_id=row.agent_id,
                        content=row.message_content,
                        timestamp=row.message_timestamp,
                        turn_number=int(row.message_turn_number),
                        metadata=row.message_metadata or {}
                    )
                    
                    entry = MemoryEntry(
                        conversation_id=row.conversation_id,
                        agent_id=row.agent_id,
                        message=message,
                        context=row.context or {},
                        importance_score=row.importance_score,
                        created_at=row.created_at
                    )
                    entries.append(entry)
                
                return entries[::-1]
                
        except Exception as e:
            raise Exception(f"PostgreSQL 에이전트 메모리 조회 오류: {str(e)}")
    
    async def get_relevant_context(self, conversation_id: str, current_topic: str, limit: int = 10) -> List[MemoryEntry]:
        try:
            async with self.async_session() as session:
                from sqlalchemy import select, or_
                
                # 간단한 키워드 검색
                topic_keywords = current_topic.lower().split()
                conditions = []
                for keyword in topic_keywords:
                    conditions.append(MemoryEntryModel.message_content.ilike(f"%{keyword}%"))
                
                stmt = select(MemoryEntryModel).where(
                    MemoryEntryModel.conversation_id == conversation_id,
                    or_(*conditions)
                ).order_by(MemoryEntryModel.created_at.desc()).limit(limit)
                
                result = await session.execute(stmt)
                entries = []
                
                for row in result.scalars():
                    message = AgentMessage(
                        agent_id=row.agent_id,
                        content=row.message_content,
                        timestamp=row.message_timestamp,
                        turn_number=int(row.message_turn_number),
                        metadata=row.message_metadata or {}
                    )
                    
                    entry = MemoryEntry(
                        conversation_id=row.conversation_id,
                        agent_id=row.agent_id,
                        message=message,
                        context=row.context or {},
                        importance_score=row.importance_score,
                        created_at=row.created_at
                    )
                    entries.append(entry)
                
                return entries[::-1]
                
        except Exception as e:
            raise Exception(f"PostgreSQL 컨텍스트 조회 오류: {str(e)}")
    
    async def clear_conversation_memory(self, conversation_id: str) -> None:
        try:
            async with self.async_session() as session:
                from sqlalchemy import delete
                
                stmt = delete(MemoryEntryModel).where(
                    MemoryEntryModel.conversation_id == conversation_id
                )
                await session.execute(stmt)
                await session.commit()
                
        except Exception as e:
            raise Exception(f"PostgreSQL 메모리 삭제 오류: {str(e)}")


class MemoryServiceFactory:
    """메모리 서비스 팩토리"""
    
    @staticmethod
    def create_service() -> MemoryInterface:
        memory_type = settings.memory_type
        
        if memory_type == "inmemory":
            return InMemoryStorage()
        elif memory_type == "redis":
            return RedisStorage()
        elif memory_type == "postgresql":
            return PostgreSQLStorage()
        else:
            raise ValueError(f"지원하지 않는 메모리 타입: {memory_type}")


# 전역 메모리 서비스 인스턴스
memory_service = MemoryServiceFactory.create_service()


class MemoryService:
    """메모리 서비스 클래스"""
    
    def __init__(self):
        self.memory_type = settings.memory_type
        self._setup_memory()
    
    def _setup_memory(self):
        """메모리 설정"""
        if self.memory_type == "redis":
            self._setup_redis()
        elif self.memory_type == "postgresql":
            self._setup_postgresql()
        else:
            # 기본값은 인메모리
            self.memory_type = "inmemory"
            self._setup_inmemory()
    
    def _setup_inmemory(self):
        """인메모리 설정"""
        self.conversations: Dict[str, Conversation] = {}
        logger.info("인메모리 저장소 초기화됨")
    
    def _setup_redis(self):
        """Redis 설정"""
        try:
            import redis
            self.redis_client = redis.from_url(settings.redis_url)
            logger.info("Redis 저장소 초기화됨")
        except ImportError:
            logger.error("Redis 패키지가 설치되지 않았습니다. 인메모리로 대체합니다.")
            self.memory_type = "inmemory"
            self._setup_inmemory()
        except Exception as e:
            logger.error(f"Redis 연결 오류: {str(e)}. 인메모리로 대체합니다.")
            self.memory_type = "inmemory"
            self._setup_inmemory()
    
    def _setup_postgresql(self):
        """PostgreSQL 설정"""
        try:
            import asyncpg
            self.postgres_url = settings.postgres_url
            logger.info("PostgreSQL 저장소 초기화됨")
        except ImportError:
            logger.error("asyncpg 패키지가 설치되지 않았습니다. 인메모리로 대체합니다.")
            self.memory_type = "inmemory"
            self._setup_inmemory()
        except Exception as e:
            logger.error(f"PostgreSQL 설정 오류: {str(e)}. 인메모리로 대체합니다.")
            self.memory_type = "inmemory"
            self._setup_inmemory()
    
    async def save_conversation(self, conversation: Conversation) -> bool:
        """대화 저장"""
        try:
            if self.memory_type == "redis":
                return await self._save_to_redis(conversation)
            elif self.memory_type == "postgresql":
                return await self._save_to_postgresql(conversation)
            else:
                return await self._save_to_inmemory(conversation)
        except Exception as e:
            logger.error(f"대화 저장 오류: {str(e)}")
            return False
    
    async def load_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """대화 로드"""
        try:
            if self.memory_type == "redis":
                return await self._load_from_redis(conversation_id)
            elif self.memory_type == "postgresql":
                return await self._load_from_postgresql(conversation_id)
            else:
                return await self._load_from_inmemory(conversation_id)
        except Exception as e:
            logger.error(f"대화 로드 오류: {str(e)}")
            return None
    
    async def delete_conversation(self, conversation_id: str) -> bool:
        """대화 삭제"""
        try:
            if self.memory_type == "redis":
                return await self._delete_from_redis(conversation_id)
            elif self.memory_type == "postgresql":
                return await self._delete_from_postgresql(conversation_id)
            else:
                return await self._delete_from_inmemory(conversation_id)
        except Exception as e:
            logger.error(f"대화 삭제 오류: {str(e)}")
            return False
    
    async def list_conversations(self) -> List[Conversation]:
        """대화 목록 조회"""
        try:
            if self.memory_type == "redis":
                return await self._list_from_redis()
            elif self.memory_type == "postgresql":
                return await self._list_from_postgresql()
            else:
                return await self._list_from_inmemory()
        except Exception as e:
            logger.error(f"대화 목록 조회 오류: {str(e)}")
            return []
    
    # 인메모리 메서드들
    async def _save_to_inmemory(self, conversation: Conversation) -> bool:
        """인메모리에 저장"""
        self.conversations[conversation.id] = conversation
        return True
    
    async def _load_from_inmemory(self, conversation_id: str) -> Optional[Conversation]:
        """인메모리에서 로드"""
        return self.conversations.get(conversation_id)
    
    async def _delete_from_inmemory(self, conversation_id: str) -> bool:
        """인메모리에서 삭제 + 파일에서도 삭제 (conversations.json이 있을 경우)"""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            # 파일에도 반영
            file_path = os.path.join(os.path.dirname(__file__), '../../../conversations.json')
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump({k: v.model_dump() for k, v in self.conversations.items()}, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    logger.error(f"파일 삭제 반영 오류: {str(e)}")
            return True
        return False
    
    async def _list_from_inmemory(self) -> List[Conversation]:
        """인메모리에서 목록 조회"""
        return list(self.conversations.values())
    
    # Redis 메서드들
    async def _save_to_redis(self, conversation: Conversation) -> bool:
        """Redis에 저장"""
        try:
            conversation_data = self._serialize_conversation(conversation)
            self.redis_client.set(f"conversation:{conversation.id}", conversation_data)
            return True
        except Exception as e:
            logger.error(f"Redis 저장 오류: {str(e)}")
            return False
    
    async def _load_from_redis(self, conversation_id: str) -> Optional[Conversation]:
        """Redis에서 로드"""
        try:
            conversation_data = self.redis_client.get(f"conversation:{conversation_id}")
            if conversation_data:
                return self._deserialize_conversation(conversation_data)
            return None
        except Exception as e:
            logger.error(f"Redis 로드 오류: {str(e)}")
            return None
    
    async def _delete_from_redis(self, conversation_id: str) -> bool:
        """Redis에서 삭제 (대화 및 메시지 키 모두 삭제)"""
        try:
            # 대화 메시지 키들 삭제
            keys = await self.redis_client.lrange(f"conversation:{conversation_id}", 0, -1)
            if keys:
                await self.redis_client.delete(*keys)
            await self.redis_client.delete(f"conversation:{conversation_id}")
            # 대화 자체 삭제
            result = await self.redis_client.delete(f"conversation:{conversation_id}")
            return result > 0
        except Exception as e:
            logger.error(f"Redis 삭제 오류: {str(e)}")
            return False
    
    async def _list_from_redis(self) -> List[Conversation]:
        """Redis에서 목록 조회"""
        try:
            conversations = []
            keys = self.redis_client.keys("conversation:*")
            for key in keys:
                conversation_data = self.redis_client.get(key)
                if conversation_data:
                    conversation = self._deserialize_conversation(conversation_data)
                    if conversation:
                        conversations.append(conversation)
            return conversations
        except Exception as e:
            logger.error(f"Redis 목록 조회 오류: {str(e)}")
            return []
    
    # PostgreSQL 메서드들
    async def _save_to_postgresql(self, conversation: Conversation) -> bool:
        """PostgreSQL에 저장"""
        try:
            import asyncpg
            conn = await asyncpg.connect(self.postgres_url)
            
            conversation_data = self._serialize_conversation(conversation)
            
            await conn.execute("""
                INSERT INTO conversations (id, data, created_at, updated_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (id) DO UPDATE SET
                data = $2, updated_at = $4
            """, conversation.id, conversation_data, conversation.created_at, datetime.now())
            
            await conn.close()
            return True
        except Exception as e:
            logger.error(f"PostgreSQL 저장 오류: {str(e)}")
            return False
    
    async def _load_from_postgresql(self, conversation_id: str) -> Optional[Conversation]:
        """PostgreSQL에서 로드"""
        try:
            import asyncpg
            conn = await asyncpg.connect(self.postgres_url)
            
            row = await conn.fetchrow(
                "SELECT data FROM conversations WHERE id = $1",
                conversation_id
            )
            
            await conn.close()
            
            if row:
                return self._deserialize_conversation(row['data'])
            return None
        except Exception as e:
            logger.error(f"PostgreSQL 로드 오류: {str(e)}")
            return None
    
    async def _delete_from_postgresql(self, conversation_id: str) -> bool:
        """PostgreSQL에서 삭제 (대화 및 메시지 모두 삭제)"""
        try:
            import asyncpg
            conn = await asyncpg.connect(self.postgres_url)
            # 메시지 테이블(예: memory_entries)도 함께 삭제
            await conn.execute(
                "DELETE FROM memory_entries WHERE conversation_id = $1",
                conversation_id
            )
            # 대화 삭제
            result = await conn.execute(
                "DELETE FROM conversations WHERE id = $1",
                conversation_id
            )
            await conn.close()
            return "DELETE 1" in result
        except Exception as e:
            logger.error(f"PostgreSQL 삭제 오류: {str(e)}")
            return False
    
    async def _list_from_postgresql(self) -> List[Conversation]:
        """PostgreSQL에서 목록 조회"""
        try:
            import asyncpg
            conn = await asyncpg.connect(self.postgres_url)
            
            rows = await conn.fetch("SELECT data FROM conversations ORDER BY created_at DESC")
            
            await conn.close()
            
            conversations = []
            for row in rows:
                conversation = self._deserialize_conversation(row['data'])
                if conversation:
                    conversations.append(conversation)
            
            return conversations
        except Exception as e:
            logger.error(f"PostgreSQL 목록 조회 오류: {str(e)}")
            return []
    
    def _serialize_conversation(self, conversation: Conversation) -> str:
        """대화 객체 직렬화"""
        try:
            # Pydantic 모델을 dict로 변환
            conversation_dict = conversation.model_dump()
            return json.dumps(conversation_dict, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error(f"대화 직렬화 오류: {str(e)}")
            return "{}"
    
    def _deserialize_conversation(self, conversation_data: str) -> Optional[Conversation]:
        """대화 객체 역직렬화"""
        try:
            conversation_dict = json.loads(conversation_data)
            return Conversation(**conversation_dict)
        except Exception as e:
            logger.error(f"대화 역직렬화 오류: {str(e)}")
            return None 