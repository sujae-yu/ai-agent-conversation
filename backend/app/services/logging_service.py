import logging
import logging.handlers
import json
import os
import sys
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from app.config import settings

# 전역 로깅 서비스 인스턴스
_logging_service = None

def get_logging_service():
    """로깅 서비스 인스턴스 반환 (싱글톤)"""
    global _logging_service
    if _logging_service is None:
        _logging_service = LoggingService()
    return _logging_service

# ECS 포맷터 클래스를 모듈 레벨로 정의
class ECSFormatter(logging.Formatter):
    def __init__(self, service_name: str = "ai-agent-conversation-system", service_version: str = "1.0.0"):
        super().__init__()
        self.service_name = service_name
        self.service_version = service_version
    
    def format(self, record):
        # ECS 기본 필드
        log_entry = {
            "@timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "log": {
                "level": record.levelname.lower(),
                "logger": record.name
            },
            "message": record.getMessage(),
            "ecs": {
                "version": "1.6.0"
            },
            "service": {
                "name": self.service_name,
                "version": self.service_version
            },
            "process": {
                "name": record.processName,
                "pid": record.process
            },
            "thread": {
                "name": record.threadName,
                "id": record.thread
            }
        }
        
        # 소스 코드 위치 정보
        if record.pathname and record.lineno:
            log_entry["log"]["origin"] = {
                "file": {
                    "name": os.path.basename(record.pathname),
                    "line": record.lineno
                }
            }
        
        # 예외 정보 추가
        if record.exc_info:
            log_entry["error"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else "Exception",
                "message": str(record.exc_info[1]) if record.exc_info[1] else "",
                "stack_trace": self.formatException(record.exc_info)
            }
        
        # 추가 필드들 (ECS 호환)
        if hasattr(record, 'conversation_id'):
            log_entry["labels"] = {"conversation_id": record.conversation_id}
        if hasattr(record, 'agent_name'):
            log_entry["labels"] = log_entry.get("labels", {})
            log_entry["labels"]["agent_name"] = record.agent_name
        if hasattr(record, 'turn_number'):
            log_entry["labels"] = log_entry.get("labels", {})
            log_entry["labels"]["turn_number"] = record.turn_number
        
        # 사용자 정의 필드들
        if hasattr(record, 'details') and record.details:
            log_entry["event"] = log_entry.get("event", {})
            log_entry["event"]["details"] = record.details
        
        # 에러 타입별 분류
        if hasattr(record, 'error_type'):
            log_entry["error"] = log_entry.get("error", {})
            log_entry["error"]["type"] = record.error_type
        
        if hasattr(record, 'error_message'):
            log_entry["error"] = log_entry.get("error", {})
            log_entry["error"]["message"] = record.error_message
        
        # LLM 관련 필드
        if hasattr(record, 'model'):
            log_entry["llm"] = {
                "model": record.model,
                "messages_count": getattr(record, 'messages_count', None),
                "max_tokens": getattr(record, 'max_tokens', None),
                "temperature": getattr(record, 'temperature', None),
                "response_time": getattr(record, 'response_time', None)
            }
        
        # 대화 관련 필드
        if hasattr(record, 'topic'):
            log_entry["conversation"] = {
                "topic": record.topic,
                "agents": getattr(record, 'agents', [])
            }
        
        return json.dumps(log_entry, ensure_ascii=False)

class LoggingService:
    """ECS(Elastic Common Schema) 호환 로깅 서비스 클래스"""
    
    def __init__(self):
        self.service_name = "ai-agent-conversation-system"
        self.service_version = "1.0.0"
        self._setup_logging()
    
    def _setup_logging(self):
        """로깅 설정 초기화"""
        try:
            # 로그 디렉토리 생성
            log_dir = os.path.dirname(settings.log_file_path)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            # 루트 로거 설정
            root_logger = logging.getLogger()
            root_logger.setLevel(getattr(logging, settings.log_level.upper()))
            
            # 기존 핸들러 제거
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
            
            # 파일 핸들러 설정
            file_handler = logging.handlers.RotatingFileHandler(
                settings.log_file_path,
                maxBytes=self._parse_size(settings.log_max_file_size),
                backupCount=settings.log_backup_count,
                encoding='utf-8'
            )
            
            # 포맷터 설정
            if settings.log_format == "ecs":
                formatter = self._create_ecs_formatter()
            elif settings.log_format == "json":
                formatter = self._create_json_formatter()
            else:
                formatter = self._create_text_formatter()
            
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
            
            # 콘솔 핸들러 설정 (개발 환경용)
            if settings.debug or settings.log_to_console:
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setFormatter(formatter)
                root_logger.addHandler(console_handler)
            
            logging.info("로깅 시스템 초기화 완료", extra={
                "event": {"action": "logging_initialized"},
                "service": {"name": self.service_name, "version": self.service_version}
            })
            
        except Exception as e:
            print(f"로깅 설정 오류: {str(e)}")
            # 기본 로깅 설정
            logging.basicConfig(level=logging.INFO)
    
    def _create_ecs_formatter(self):
        """ECS(Elastic Common Schema) 포맷터 생성"""
        return ECSFormatter(self.service_name, self.service_version)
    
    def _create_json_formatter(self):
        """JSON 포맷터 생성 (기존 호환성 유지)"""
        class UnicodeSafeJSONFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno
                }
                
                # 예외 정보 추가
                if record.exc_info:
                    log_entry["exception"] = self.formatException(record.exc_info)
                
                # 추가 필드들
                if hasattr(record, 'conversation_id'):
                    log_entry["conversation_id"] = record.conversation_id
                if hasattr(record, 'agent_name'):
                    log_entry["agent_name"] = record.agent_name
                if hasattr(record, 'turn_number'):
                    log_entry["turn_number"] = record.turn_number
                
                return json.dumps(log_entry, ensure_ascii=False)
        
        return UnicodeSafeJSONFormatter()
    
    def _create_text_formatter(self):
        """텍스트 포맷터 생성"""
        return logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    def _parse_size(self, size_str: str) -> int:
        """크기 문자열을 바이트로 변환"""
        size_str = size_str.upper()
        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)
    
    def log_conversation_start(self, conversation_id: str, topic: str, agents: list):
        """대화 시작 로깅"""
        if settings.log_include_agent_conversations:
            logging.info(
                f"대화 시작 - ID: {conversation_id}, 주제: {topic}, 참여자: {[agent.name for agent in agents]}",
                extra={
                    "conversation_id": conversation_id,
                    "topic": topic,
                    "agents": [agent.name for agent in agents],
                    "event": {"action": "conversation_started"},
                    "details": {
                        "participant_count": len(agents),
                        "agent_names": [agent.name for agent in agents]
                    }
                }
            )
    
    def log_conversation_end(self, conversation_id: str, total_turns: int):
        """대화 종료 로깅"""
        if settings.log_include_agent_conversations:
            logging.info(
                f"대화 종료 - ID: {conversation_id}, 총 턴: {total_turns}",
                extra={
                    "conversation_id": conversation_id,
                    "total_turns": total_turns,
                    "event": {"action": "conversation_ended"},
                    "details": {
                        "duration_turns": total_turns
                    }
                }
            )
    
    def log_agent_message(self, conversation_id: str, agent_name: str, message: str, turn_number: int):
        """에이전트 메시지 로깅 - 전체 대화 내용 추적 감사용"""
        if settings.log_include_agent_conversations:
            logging.info(
                f"에이전트 발화 - {agent_name} (턴 {turn_number}): {message}",
                extra={
                    "conversation_id": conversation_id,
                    "agent_name": agent_name,
                    "turn_number": turn_number,
                    "message_length": len(message),
                    "event": {"action": "agent_message_sent"},
                    "details": {
                        "full_message": message,  # 전체 대화 내용
                        "message_length": len(message),
                        "audit_trail": True  # 감사 추적 표시
                    }
                }
            )
    
    def log_llm_request(self, model: str, messages_count: int, max_tokens: int, temperature: float, response_time: float):
        """LLM 요청 로깅"""
        logging.info(
            f"LLM 요청 - 모델: {model}, 메시지 수: {messages_count}, 응답 시간: {response_time:.2f}초",
            extra={
                "model": model,
                "messages_count": messages_count,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "response_time": response_time,
                "event": {"action": "llm_request_completed"},
                "details": {
                    "model_used": model,
                    "performance_metrics": {
                        "response_time_seconds": response_time,
                        "messages_processed": messages_count
                    }
                }
            }
        )
    
    def log_error(self, error_type: str, error_message: str, context: Dict[str, Any] = None):
        """에러 로깅"""
        logging.error(
            f"에러 발생 - 타입: {error_type}, 메시지: {error_message}",
            extra={
                "error_type": error_type,
                "error_message": error_message,
                "event": {"action": "error_occurred"},
                "details": context or {}
            }
        )
    
    def log_system_event(self, event_type: str, details: Dict[str, Any] = None):
        """시스템 이벤트 로깅"""
        logging.info(
            f"시스템 이벤트 - {event_type}",
            extra={
                "event": {"action": event_type},
                "details": details or {}
            }
        )
    
    def log_info(self, message: str, details: Dict[str, Any] = None):
        """정보 로깅"""
        logging.info(
            message,
            extra={
                "event": {"action": "info_logged"},
                "details": details or {}
            }
        )
    
    def log_warning(self, message: str, details: Dict[str, Any] = None):
        """경고 로깅"""
        logging.warning(
            message,
            extra={
                "event": {"action": "warning_logged"},
                "details": details or {}
            }
        )
    
    def log_debug(self, message: str, details: Dict[str, Any] = None):
        """디버그 로깅"""
        logging.debug(
            message,
            extra={
                "event": {"action": "debug_logged"},
                "details": details or {}
            }
        )
    
    def log_server_startup(self, host: str, port: int, debug: bool, llm_provider: str, memory_type: str):
        """서버 시작 로깅"""
        logging.info(
            f"서버 시작 - {host}:{port}, LLM: {llm_provider}, 메모리: {memory_type}",
            extra={
                "event": {"action": "server_started"},
                "details": {
                    "server_config": {
                        "host": host,
                        "port": port,
                        "debug": debug,
                        "llm_provider": llm_provider,
                        "memory_type": memory_type
                    }
                }
            }
        )
    
    def log_server_shutdown(self):
        """서버 종료 로깅"""
        logging.info(
            "서버 종료",
            extra={
                "event": {"action": "server_shutdown"}
            }
        )

 