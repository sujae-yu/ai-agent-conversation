import asyncio
import json
import logging
from typing import List, Dict, Any, Optional, Callable
from openai import AsyncOpenAI
from app.models.conversation import Message
from app.config import settings

logger = logging.getLogger(__name__)

class LLMService:
    """LLM 서비스 클래스"""
    
    def __init__(self):
        self.provider = settings.llm_provider
        self.client = None
        self._setup_client()
    
    def _setup_client(self):
        """LLM 클라이언트 설정"""
        try:
            if self.provider == "vllm":
                self.client = AsyncOpenAI(
                    base_url=settings.vllm_url,
                    api_key="not-needed"
                )
                logger.info(f"vLLM 클라이언트 초기화됨: {settings.vllm_url}")
            elif self.provider == "openai":
                if not settings.openai_api_key:
                    raise ValueError("OpenAI API 키가 설정되지 않았습니다.")
                self.client = AsyncOpenAI(
                    api_key=settings.openai_api_key
                )
                logger.info("OpenAI 클라이언트 초기화됨")
            elif self.provider == "ollama":
                self.client = AsyncOpenAI(
                    base_url=settings.ollama_url,
                    api_key="not-needed"
                )
                logger.info(f"Ollama 클라이언트 초기화됨: {settings.ollama_url}")
            else:
                raise ValueError(f"지원하지 않는 LLM 제공자: {self.provider}")
        except Exception as e:
            logger.error(f"LLM 클라이언트 설정 오류: {str(e)}")
            raise
    
    async def generate_response(
        self,
        messages: List[Message],
        system_prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        callback: Optional[Callable] = None
    ) -> str:
        """LLM 응답 생성 (비스트림)"""
        try:
            # 메시지 포맷 변환
            formatted_messages = self._format_messages(messages, system_prompt)
            
            # 디버깅을 위한 로깅
            logger.info(f"LLM 요청 - 제공자: {self.provider}")
            logger.info(f"시스템 프롬프트: {system_prompt}")
            logger.info(f"포맷된 메시지 수: {len(formatted_messages)}")
            for i, msg in enumerate(formatted_messages):
                logger.info(f"포맷된 메시지 {i}: role={msg['role']}, content={msg['content']}")
            
            # 설정값 적용
            max_tokens = max_tokens or settings.vllm_max_tokens
            temperature = temperature or settings.vllm_temperature
            
            # LLM 요청
            response = await self.client.chat.completions.create(
                model=settings.vllm_model,
                messages=formatted_messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=settings.vllm_top_p,
                frequency_penalty=settings.vllm_frequency_penalty,
                presence_penalty=settings.vllm_presence_penalty,
                stream=False
            )
            
            content = response.choices[0].message.content
            
            # 콜백 실행
            if callback:
                if asyncio.iscoroutinefunction(callback):
                    await callback(content)
                else:
                    callback(content)
            
            return content
            
        except Exception as e:
            logger.error(f"LLM 응답 생성 오류: {str(e)}")
            raise

    async def generate_response_stream(
        self,
        messages: List[Message],
        system_prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stream_callback: Optional[Callable] = None
    ):
        """LLM 응답 생성 (스트림)"""
        try:
            # 메시지 포맷 변환
            formatted_messages = self._format_messages(messages, system_prompt)
            
            # 디버깅을 위한 로깅
            logger.info(f"LLM 스트림 요청 - 제공자: {self.provider}")
            logger.info(f"시스템 프롬프트: {system_prompt}")
            
            # 설정값 적용
            max_tokens = max_tokens or settings.vllm_max_tokens
            temperature = temperature or settings.vllm_temperature
            
            # 스트림 요청
            stream = await self.client.chat.completions.create(
                model=settings.vllm_model,
                messages=formatted_messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=settings.vllm_top_p,
                frequency_penalty=settings.vllm_frequency_penalty,
                presence_penalty=settings.vllm_presence_penalty,
                stream=True
            )
            
            full_content = ""
            
            async for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    full_content += content
                    
                    # 스트림 콜백 실행
                    if stream_callback:
                        if asyncio.iscoroutinefunction(stream_callback):
                            await stream_callback(content, full_content)
                        else:
                            stream_callback(content, full_content)
            
            return full_content
            
        except Exception as e:
            logger.error(f"LLM 스트림 응답 생성 오류: {str(e)}")
            raise
    
    def _format_messages(self, messages: List[Message], system_prompt: str) -> List[Dict[str, str]]:
        """메시지를 LLM 형식으로 변환"""
        formatted = []
        
        # vLLM의 경우 단순한 user/assistant 형식 사용
        if self.provider == "vllm":
            # 시스템 프롬프트와 대화 내용을 하나의 user 메시지로 결합
            full_content = system_prompt + "\n\n"
            
            # 대화 메시지들을 추가
            for message in messages:
                if message.speaker != "시스템":
                    full_content += f"{message.speaker}: {message.content}\n"
            
            # 단일 user 메시지로 전송
            formatted.append({
                "role": "user",
                "content": full_content.strip()
            })
        else:
            # 다른 제공자들은 표준 형식 사용
            if system_prompt:
                formatted.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            # 대화 메시지들을 추가
            for message in messages:
                if message.speaker != "시스템":
                    formatted.append({
                        "role": "user",
                        "content": f"{message.speaker}: {message.content}"
                    })
        
        return formatted
    
    async def test_connection(self) -> Dict[str, Any]:
        """LLM 연결 테스트 - 상세 정보 반환"""
        result = {
            "success": False,
            "provider": self.provider,
            "details": {},
            "error": None
        }
        
        try:
            # 제공자별 설정 정보
            if self.provider == "vllm":
                result["details"] = {
                    "url": settings.vllm_url,
                    "model": settings.vllm_model,
                    "max_tokens": settings.vllm_max_tokens,
                    "temperature": settings.vllm_temperature
                }
            elif self.provider == "openai":
                result["details"] = {
                    "model": settings.openai_model,
                    "api_key_set": bool(settings.openai_api_key)
                }
            elif self.provider == "ollama":
                result["details"] = {
                    "url": settings.ollama_url,
                    "model": settings.ollama_model
                }
            
            # 실제 연결 테스트
            test_messages = [{"role": "user", "content": "Hello"}]
            response = await self.client.chat.completions.create(
                model=self._get_test_model(),
                messages=test_messages,
                max_tokens=10
            )
            
            result["success"] = True
            result["details"]["response"] = response.choices[0].message.content
            result["details"]["usage"] = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
            
            logger.info(f"LLM 연결 테스트 성공: {self.provider}")
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"LLM 연결 테스트 실패: {self.provider} - {str(e)}")
        
        return result
    
    def _get_test_model(self) -> str:
        """테스트용 모델명 반환"""
        if self.provider == "vllm":
            return settings.vllm_model
        elif self.provider == "openai":
            return settings.openai_model
        elif self.provider == "ollama":
            return settings.ollama_model
        else:
            return "unknown"
    
    def get_provider_info(self) -> Dict[str, Any]:
        """현재 LLM 제공자 정보 반환"""
        return {
            "provider": self.provider,
            "config": settings.get_llm_config()
        }


# 전역 LLM 서비스 인스턴스
llm_service = LLMService() 