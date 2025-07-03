import logging
import logging.config
import sys
from typing import Dict, Any
from app.config import settings
from app.services.logging_service import ECSFormatter

def setup_logging():
    """로깅 설정 - 포맷에 따라 다르게 적용"""
    
    # 로그 포맷 확인
    log_format = getattr(settings, 'log_format', 'ecs')
    
    # 포맷터 선택
    if log_format == 'stdout':
        # 원래 터미널 출력용 포맷터
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        # ECS 포맷터 (기본값)
        formatter = ECSFormatter()
    
    # uvicorn 로거 설정
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.handlers.clear()
    
    # uvicorn access 로거 설정
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_access_logger.handlers.clear()
    
    # uvicorn error 로거 설정
    uvicorn_error_logger = logging.getLogger("uvicorn.error")
    uvicorn_error_logger.handlers.clear()
    
    # FastAPI 로거 설정
    fastapi_logger = logging.getLogger("fastapi")
    fastapi_logger.handlers.clear()
    
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # 콘솔 핸들러 생성
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # 파일 핸들러 생성 (선택적)
    if settings.log_file_path:
        file_handler = logging.FileHandler(settings.log_file_path)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
    
    # 로거들에 핸들러 추가
    loggers_to_configure = [
        uvicorn_logger,
        uvicorn_access_logger,
        uvicorn_error_logger,
        fastapi_logger,
        root_logger
    ]
    
    for logger in loggers_to_configure:
        logger.handlers.clear()
        logger.addHandler(console_handler)
        if settings.log_file_path:
            logger.addHandler(file_handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    
    # 특정 로거들의 레벨 조정
    uvicorn_access_logger.setLevel(logging.INFO)
    uvicorn_error_logger.setLevel(logging.ERROR)
    
    # 불필요한 로그 억제
    logging.getLogger("uvicorn.protocols.http.httptools_impl").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.protocols.websockets.websockets_impl").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.lifespan.on").setLevel(logging.WARNING)

def get_uvicorn_log_config() -> Dict[str, Any]:
    """uvicorn용 로깅 설정 반환"""
    # 로그 포맷 확인
    log_format = getattr(settings, 'log_format', 'ecs')
    
    # 포맷터 설정
    if log_format == 'stdout':
        formatters = {
            "stdout": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        }
        formatter_name = "stdout"
    else:
        formatters = {
            "ecs": {
                "()": "app.services.logging_service.ECSFormatter",
            }
        }
        formatter_name = "ecs"
    
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": formatters,
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": formatter_name,
                "stream": "ext://sys.stdout"
            }
        },
        "loggers": {
            "uvicorn": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False
            },
            "uvicorn.access": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False
            },
            "uvicorn.error": {
                "handlers": ["console"],
                "level": "ERROR",
                "propagate": False
            },
            "fastapi": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False
            }
        },
        "root": {
            "handlers": ["console"],
            "level": "INFO"
        }
    } 