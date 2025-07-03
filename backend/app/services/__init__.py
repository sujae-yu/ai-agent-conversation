# 서비스 모듈 초기화
# 순환 import 문제를 방지하기 위해 지연 로딩 사용

def get_conversation_service():
    """대화 서비스 인스턴스 반환"""
    from .conversation_service import ConversationService
    return ConversationService()

def get_llm_service():
    """LLM 서비스 인스턴스 반환"""
    from .llm_service import LLMService
    return LLMService()

def get_memory_service():
    """메모리 서비스 인스턴스 반환"""
    from .memory_service import MemoryService
    return MemoryService()

# 로깅 서비스는 logging_service.py에서 직접 import

__all__ = [
    'get_conversation_service',
    'get_llm_service',
    'get_memory_service'
] 