from pydantic_settings import BaseSettings
from typing import Optional

class LoggingConfig:
    """로깅 설정"""
    def __init__(self, config_data: dict):
        self.level = config_data.get("level", "INFO")
        self.file_path = config_data.get("file_path", "./logs/app.log")
        self.max_file_size = config_data.get("max_file_size", "10MB")
        self.backup_count = config_data.get("backup_count", 5)
        self.format = config_data.get("format", "json")
        self.include_agent_conversations = config_data.get("include_agent_conversations", True)

class Settings(BaseSettings):
    # 서버 설정
    host: str
    port: int
    debug: bool

    # LLM 설정
    llm_provider: str
    vllm_url: str
    vllm_model: str
    vllm_max_tokens: int
    vllm_temperature: float
    vllm_top_p: float
    vllm_frequency_penalty: float
    vllm_presence_penalty: float

    openai_api_key: Optional[str] = None
    openai_model: Optional[str] = None

    ollama_url: Optional[str] = None
    ollama_model: Optional[str] = None

    # 대화 설정
    conversation_max_turns: int
    conversation_turn_interval: float
    conversation_history_limit: int
    conversation_context_limit: int
    conversation_unlimited: bool

    # 스트림 설정
    enable_streaming: bool

    # 메모리 설정
    memory_type: str
    redis_url: Optional[str] = None
    postgres_url: Optional[str] = None

    # 로깅 설정
    log_level: str
    log_file_path: str
    log_max_file_size: str
    log_backup_count: int
    log_format: str
    log_include_agent_conversations: bool

    # 개발자 설정
    dev_mode: bool
    log_to_console: bool
    enable_debug_logging: bool

    # 로깅 설정 객체
    logging_config: Optional[LoggingConfig] = None

    cors_origins: str = "*"  # .env에서 CORS_ORIGINS로 관리, 기본값 전체 허용

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # 환경변수명과 필드명 매핑
        fields = {
            "host": {"env": "HOST"},
            "port": {"env": "PORT"},
            "debug": {"env": "DEBUG"},
            "llm_provider": {"env": "LLM_PROVIDER"},
            "vllm_url": {"env": "VLLM_URL"},
            "vllm_model": {"env": "VLLM_MODEL"},
            "vllm_max_tokens": {"env": "VLLM_MAX_TOKENS"},
            "vllm_temperature": {"env": "VLLM_TEMPERATURE"},
            "vllm_top_p": {"env": "VLLM_TOP_P"},
            "vllm_frequency_penalty": {"env": "VLLM_FREQUENCY_PENALTY"},
            "vllm_presence_penalty": {"env": "VLLM_PRESENCE_PENALTY"},
            "openai_api_key": {"env": "OPENAI_API_KEY"},
            "openai_model": {"env": "OPENAI_MODEL"},
            "ollama_url": {"env": "OLLAMA_URL"},
            "ollama_model": {"env": "OLLAMA_MODEL"},
            "conversation_max_turns": {"env": "CONVERSATION_MAX_TURNS"},
            "conversation_turn_interval": {"env": "CONVERSATION_TURN_INTERVAL"},
            "conversation_history_limit": {"env": "CONVERSATION_HISTORY_LIMIT"},
            "conversation_context_limit": {"env": "CONVERSATION_CONTEXT_LIMIT"},
            "conversation_unlimited": {"env": "CONVERSATION_UNLIMITED"},
            "enable_streaming": {"env": "ENABLE_STREAMING"},
            "memory_type": {"env": "MEMORY_TYPE"},
            "redis_url": {"env": "REDIS_URL"},
            "postgres_url": {"env": "POSTGRES_URL"},
            "log_level": {"env": "LOG_LEVEL"},
            "log_file_path": {"env": "LOG_FILE_PATH"},
            "log_max_file_size": {"env": "LOG_MAX_FILE_SIZE"},
            "log_backup_count": {"env": "LOG_BACKUP_COUNT"},
            "log_format": {"env": "LOG_FORMAT"},
            "log_include_agent_conversations": {"env": "LOG_INCLUDE_AGENT_CONVERSATIONS"},
            "dev_mode": {"env": "DEV_MODE"},
            "log_to_console": {"env": "LOG_TO_CONSOLE"},
            "enable_debug_logging": {"env": "ENABLE_DEBUG_LOGGING"},
            "cors_origins": {"env": "CORS_ORIGINS"},
        }
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._setup_logging_config()
    
    def _setup_logging_config(self):
        """로깅 설정 초기화"""
        log_config_data = {
            "level": self.log_level,
            "file_path": self.log_file_path,
            "max_file_size": self.log_max_file_size,
            "backup_count": self.log_backup_count,
            "format": self.log_format,
            "include_agent_conversations": self.log_include_agent_conversations
        }
        self.logging_config = LoggingConfig(log_config_data)
    
    def get_llm_config(self) -> dict:
        """현재 LLM 제공자에 따른 설정 반환"""
        if self.llm_provider == "vllm":
            return {
                "url": self.vllm_url,
                "model": self.vllm_model,
                "max_tokens": self.vllm_max_tokens,
                "temperature": self.vllm_temperature,
                "top_p": self.vllm_top_p,
                "frequency_penalty": self.vllm_frequency_penalty,
                "presence_penalty": self.vllm_presence_penalty
            }
        elif self.llm_provider == "openai":
            return {
                "api_key": self.openai_api_key,
                "model": self.openai_model
            }
        elif self.llm_provider == "ollama":
            return {
                "url": self.ollama_url,
                "model": self.ollama_model
            }
        else:
            raise ValueError(f"지원하지 않는 LLM 제공자: {self.llm_provider}")
    
    def get_memory_config(self) -> dict:
        """메모리 설정 반환"""
        return {
            "type": self.memory_type,
            "redis_url": self.redis_url,
            "postgres_url": self.postgres_url
        }
    
    def get_conversation_config(self) -> dict:
        """대화 설정 반환"""
        return {
            "max_turns": self.conversation_max_turns,
            "turn_interval": self.conversation_turn_interval,
            "history_limit": self.conversation_history_limit,
            "context_limit": self.conversation_context_limit,
            "unlimited": self.conversation_unlimited
        }

# 전역 설정 인스턴스
settings = Settings() 