#!/usr/bin/env python3
"""
AI Agent NPC 대화 시스템 - CLI 모드 실행 스크립트
"""

import sys
import os
import asyncio

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.cli.cli_app import main

if __name__ == "__main__":
    asyncio.run(main()) 