from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

from .api.routes import router
from .config import settings


# FastAPI 앱 생성
app = FastAPI(
    title="AI Agent NPC 대화 시스템",
    description="vLLM 기반 AI 에이전트들의 자유로운 대화 시스템",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 설정
origins = (
    ["*"] if settings.cors_origins == "*"
    else [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
app.include_router(router, prefix="/api")

# 정적 파일 서빙 (프론트엔드용)
try:
    app.mount("/", StaticFiles(directory="../frontend/dist", html=True), name="static")
except:
    # 프론트엔드 빌드 파일이 없는 경우 무시
    pass


@app.on_event("startup")
async def startup_event():
    """서버 시작 시 실행"""
    from .services.logging_service import get_logging_service
    logging_service = get_logging_service()
    
    logging_service.log_info("서버가 시작되었습니다", {
        "host": settings.host,
        "port": settings.port,
        "debug": settings.debug
    })
    print("🚀 AI Agent NPC 대화 시스템이 시작되었습니다.")
    print(f"📡 LLM 제공업체: {settings.llm_provider}")
    print(f"💾 메모리 타입: {settings.memory_type}")
    print(f"🌐 서버 주소: http://{settings.host}:{settings.port}")
    print(f"📚 API 문서: http://{settings.host}:{settings.port}/docs")


@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료 시 실행"""
    from .services.logging_service import get_logging_service
    logging_service = get_logging_service()
    
    logging_service.log_info("서버가 종료되었습니다")
    print("🛑 AI Agent NPC 대화 시스템이 종료되었습니다.")


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {"message": "AI Agent NPC 대화 시스템 API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    ) 