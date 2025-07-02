from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from typing import List, Dict, Any
import json
import asyncio
from datetime import datetime

from ..models.conversation import ConversationRequest, ConversationResponse, ConversationUpdate, ConversationStatus
from ..models.agent import Agent
from ..services.conversation_service import conversation_service
from ..services.llm_service import llm_service
from ..config import settings

router = APIRouter()

# WebSocket 연결 관리
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        print(f"WebSocket 브로드캐스트 시작: {len(self.active_connections)}개 연결")
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
                print(f"WebSocket 메시지 전송 성공")
            except Exception as e:
                print(f"WebSocket 메시지 전송 실패: {e}")
                # 연결이 끊어진 경우 제거
                self.active_connections.remove(connection)

manager = ConnectionManager()

# 메시지 콜백 함수
def message_callback(conversation_id: str, message):
    """새 메시지가 생성될 때 WebSocket으로 브로드캐스트"""
    # 에이전트 이름 가져오기
    agent_name = "시스템" if message.speaker == "시스템" else message.speaker
    
    # 메시지 타입 결정 (스트림 여부에 따라)
    message_type = "stream_update" if getattr(message, 'is_streaming', False) else "new_message"
    
    message_data = {
        "type": message_type,
        "conversation_id": conversation_id,
        "message": {
            "agent_id": message.agent_id,
            "content": message.content,
            "timestamp": message.timestamp,
            "turn_number": message.turn_number,
            "agent_name": agent_name,
            "is_streaming": getattr(message, 'is_streaming', False)
        }
    }
    
    print(f"WebSocket 메시지 전송: {json.dumps(message_data, ensure_ascii=False)}")
    
    # 비동기로 브로드캐스트 실행
    asyncio.create_task(manager.broadcast(json.dumps(message_data, ensure_ascii=False)))

# 콜백 등록
conversation_service.add_message_callback(message_callback)


@router.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "AI Agent NPC 대화 시스템",
        "version": "1.0.0",
        "status": "running"
    }


@router.get("/agents", response_model=List[Agent])
async def get_agents():
    """모든 에이전트 조회"""
    return conversation_service.get_agents()


@router.get("/agents/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str):
    """특정 에이전트 조회"""
    agents = conversation_service.get_agents()
    for agent in agents:
        if agent.id == agent_id:
            return agent
    raise HTTPException(status_code=404, detail="에이전트를 찾을 수 없습니다.")


@router.get("/conversations")
async def get_conversations():
    """모든 대화 조회"""
    conversations = conversation_service.get_all_conversations()
    return [
        {
            "id": conv.id,
            "title": conv.title,
            "status": conv.status,
            "created_at": conv.created_at,
            "updated_at": conv.updated_at,
            "agent_ids": conv.agent_ids,
            "current_turn": conv.current_turn,
            "max_turns": conv.max_turns,
            "message_count": len(conv.messages)
        }
        for conv in conversations
    ]


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """특정 대화 조회"""
    conversation = conversation_service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다.")
    
    return {
        "id": conversation.id,
        "title": conversation.title,
        "status": conversation.status,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
        "agent_ids": conversation.agent_ids,
        "current_turn": conversation.current_turn,
        "max_turns": conversation.max_turns,
        "messages": [
            {
                "agent_id": msg.agent_id,
                "content": msg.content,
                "timestamp": msg.timestamp,
                "turn_number": msg.turn_number or 0,
                "agent_name": next((agent.name for agent in conversation_service.get_agents() if agent.id == msg.agent_id), "Unknown")
            }
            for msg in conversation.messages
        ],
        "agent_states": conversation.agent_states
    }


@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(request: ConversationRequest):
    """새로운 대화 생성"""
    try:
        # 에이전트 ID 검증
        available_agents = [agent.id for agent in conversation_service.get_agents()]
        print(f"Available agents: {available_agents}")
        print(f"Request agent_ids: {request.agent_ids}")
        
        for agent_id in request.agent_ids:
            if agent_id not in available_agents:
                raise HTTPException(
                    status_code=400, 
                    detail=f"존재하지 않는 에이전트 ID: {agent_id}"
                )
        
        conversation = await conversation_service.create_conversation(request)
        
        return ConversationResponse(
            conversation_id=conversation.id,
            status=conversation.status,
            message="대화가 성공적으로 생성되었습니다.",
            data={
                "title": conversation.title,
                "agent_ids": conversation.agent_ids,
                "max_turns": conversation.max_turns
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error in create_conversation: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"대화 생성 중 오류가 발생했습니다: {str(e)}")


@router.post("/conversations/{conversation_id}/start")
async def start_conversation(conversation_id: str):
    """대화 시작"""
    try:
        success = await conversation_service.start_conversation(conversation_id)
        if not success:
            raise HTTPException(status_code=400, detail="대화를 시작할 수 없습니다.")
        
        # WebSocket으로 대화 상태 변경 알림
        status_data = {
            "type": "conversation_updated",
            "conversation_id": conversation_id,
            "status": "active"
        }
        await manager.broadcast(json.dumps(status_data, ensure_ascii=False))
        
        return {
            "message": "대화가 시작되었습니다.",
            "conversation_id": conversation_id,
            "status": "active"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))





@router.post("/conversations/{conversation_id}/stop")
async def stop_conversation(conversation_id: str):
    """대화 중지"""
    try:
        success = await conversation_service.stop_conversation(conversation_id)
        if not success:
            raise HTTPException(status_code=400, detail="대화를 중지할 수 없습니다.")
        
        return {
            "message": "대화가 중지되었습니다.",
            "conversation_id": conversation_id,
            "status": "stopped"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/conversations/{conversation_id}")
async def update_conversation(conversation_id: str, update: ConversationUpdate):
    """대화 정보 업데이트"""
    conversation = conversation_service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다.")
    
    try:
        if update.status is not None:
            conversation.status = update.status
        if update.max_turns is not None:
            conversation.max_turns = update.max_turns
        if update.metadata is not None:
            conversation.metadata.update(update.metadata)
        
        conversation.updated_at = datetime.now()
        
        return {
            "message": "대화 정보가 업데이트되었습니다.",
            "conversation_id": conversation_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """대화 삭제"""
    try:
        # 먼저 대화 중지
        await conversation_service.stop_conversation(conversation_id)
        
        # 대화 제거 (conversation_service에서 처리)
        success = conversation_service.delete_conversation(conversation_id)
        
        return {
            "message": "대화가 삭제되었습니다.",
            "conversation_id": conversation_id
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/llm/test")
async def test_llm_connection():
    """LLM 연결 테스트"""
    try:
        result = await llm_service.test_connection()
        return {
            "status": "success",
            "message": "LLM 연결이 정상입니다.",
            "details": result
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"LLM 연결 실패: {str(e)}",
            "details": None
        }





@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 엔드포인트 - 실시간 대화 모니터링"""
    await manager.connect(websocket)
    try:
        while True:
            # 클라이언트로부터 메시지 수신 (필요시)
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # 연결 상태 메시지 전송
            await manager.send_personal_message(
                json.dumps({
                    "type": "connection_status",
                    "message": "연결됨",
                    "timestamp": datetime.now().isoformat()
                }, ensure_ascii=False),
                websocket
            )
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket 오류: {str(e)}")
        manager.disconnect(websocket)


@router.get("/config")
async def get_config():
    """현재 설정 정보 반환"""
    return {
        "llm_provider": settings.llm_provider,
        "vllm_url": settings.vllm_url,
        "vllm_model": settings.vllm_model,
        "conversation_max_turns": settings.conversation_max_turns,
        "conversation_turn_interval": settings.conversation_turn_interval,
        "conversation_unlimited": settings.conversation_unlimited,
        "enable_streaming": settings.enable_streaming
    }


@router.get("/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "llm_provider": settings.llm_provider,
        "memory_type": settings.memory_type
    } 