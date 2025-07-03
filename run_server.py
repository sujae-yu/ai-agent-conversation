#!/usr/bin/env python3
"""
AI Agent NPC 대화 시스템 - 서버 모드 실행 스크립트
"""

import sys
import os
import uvicorn

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app.main import app
from backend.app.config import settings
from backend.app.services.logging_service import get_logging_service
from backend.app.logging_config import setup_logging, get_uvicorn_log_config

if __name__ == "__main__":
    # ECS 로깅 설정 적용
    setup_logging()
    
    # 로깅 서비스 초기화
    logging_service = get_logging_service()
    
    # 서버 시작 로깅
    logging_service.log_info("서버 실행 스크립트 시작", {
        "script": "run_server.py",
        "server_config": {
            "host": settings.host,
            "port": settings.port,
            "debug": settings.debug
        }
    })
    
    # 터미널 출력 (개발 환경용)
    if settings.debug or settings.log_to_console:
        print("🚀 AI Agent NPC 대화 시스템 서버를 시작합니다...")
        print(f"📡 서버 주소: http://{settings.host}:{settings.port}")
        print(f"📚 API 문서: http://{settings.host}:{settings.port}/docs")
        print(f"🤖 LLM 제공업체: {settings.llm_provider}")
        print(f"💾 메모리 타입: {settings.memory_type}")
        print("=" * 50)
    
    uvicorn.run(
        "backend.app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info",
        log_config=get_uvicorn_log_config()
    ) 