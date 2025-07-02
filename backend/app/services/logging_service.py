import logging
import logging.handlers
import json
import os
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

class LoggingService:
    """로깅 서비스 클래스"""
    
    def __init__(self):
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
            if settings.log_format == "json":
                formatter = self._create_json_formatter()
            else:
                formatter = self._create_text_formatter()
            
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
            
            # 콘솔 핸들러 설정 (개발 환경용)
            if settings.debug:
                console_handler = logging.StreamHandler()
                console_handler.setFormatter(formatter)
                root_logger.addHandler(console_handler)
            
            logging.info("로깅 시스템 초기화 완료")
            
        except Exception as e:
            print(f"로깅 설정 오류: {str(e)}")
            # 기본 로깅 설정
            logging.basicConfig(level=logging.INFO)
    
    def _create_json_formatter(self):
        """JSON 포맷터 생성"""
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
                    "agents": [agent.name for agent in agents]
                }
            )
    
    def log_conversation_end(self, conversation_id: str, total_turns: int):
        """대화 종료 로깅"""
        if settings.log_include_agent_conversations:
            logging.info(
                f"대화 종료 - ID: {conversation_id}, 총 턴: {total_turns}",
                extra={
                    "conversation_id": conversation_id,
                    "total_turns": total_turns
                }
            )
    
    def log_agent_message(self, conversation_id: str, agent_name: str, message: str, turn_number: int):
        """에이전트 메시지 로깅"""
        if settings.log_include_agent_conversations:
            logging.info(
                f"에이전트 발화 - {agent_name}: {message[:100]}...",
                extra={
                    "conversation_id": conversation_id,
                    "agent_name": agent_name,
                    "turn_number": turn_number,
                    "message_length": len(message)
                }
            )
    
    def log_llm_request(self, model: str, messages_count: int, max_tokens: int, temperature: float, response_time: float):
        """LLM 요청 로깅"""
        logging.info(
            f"LLM 요청 - 모델: {model}, 메시지 수: {messages_count}, 응답시간: {response_time:.2f}초",
            extra={
                "model": model,
                "messages_count": messages_count,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "response_time": response_time
            }
        )
    
    def log_error(self, error_type: str, error_message: str, context: Dict[str, Any] = None):
        """에러 로깅"""
        logging.error(
            f"에러 발생 - 타입: {error_type}, 메시지: {error_message}",
            extra={
                "error_type": error_type,
                "error_message": error_message,
                "context": context or {}
            }
        )
    
    def log_system_event(self, event_type: str, details: Dict[str, Any] = None):
        """시스템 이벤트 로깅"""
        logging.info(
            f"시스템 이벤트 - {event_type}",
            extra={
                "event_type": event_type,
                "details": details or {}
            }
        )
    
    def log_info(self, message: str, details: Dict[str, Any] = None):
        """일반 정보 로깅"""
        logging.info(
            message,
            extra={
                "details": details or {}
            }
        )
    
    def log_warning(self, message: str, details: Dict[str, Any] = None):
        """경고 로깅"""
        logging.warning(
            message,
            extra={
                "details": details or {}
            }
        )
    
    def log_debug(self, message: str, details: Dict[str, Any] = None):
        """디버그 로깅"""
        logging.debug(
            message,
            extra={
                "details": details or {}
            }
        )

 