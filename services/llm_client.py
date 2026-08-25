import os
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from config import LLM_PROVIDER
from services.groq_service import GroqService, strip_think_tags
from services.claude_service import ClaudeService
from services.gemini_service import GeminiService

class LLMClient:
    def __init__(self, provider: Optional[str] = None):
        self.provider = (provider or LLM_PROVIDER).lower().strip()
        self.groq_service = GroqService()
        self.claude_service = ClaudeService()
        self.gemini_service = GeminiService()

    def get_active_provider_name(self) -> str:
        if self.gemini_service.is_configured():
            return "Google Gemini (gemini-3.6-flash)"
        elif self.provider == "anthropic":
            return "Anthropic (Claude)"
        else:
            return "Groq (openai/gpt-oss-120b)"

    def test_connection(self) -> Tuple[bool, str]:
        """Kiểm tra provider xem có hoạt động không."""
        if self.gemini_service.is_configured():
            return self.gemini_service.test_connection()
        elif self.provider == "anthropic":
            return self.claude_service.test_connection()
        else:
            return self.groq_service.test_connection()

    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> Dict[str, Any]:
        """Gửi request chat completion ưu tiên Gemini 3.6 Flash -> Groq -> Claude."""
        # 1. Ưu tiên Google Gemini 3.6 Flash (Thông minh, hiểu tiếng Việt sâu, không bị lỗi think)
        if self.gemini_service.is_configured() and not tools:
            try:
                res = await self.gemini_service.chat_completion(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                if res.get("content") and res.get("content").strip():
                    return res
            except Exception as e:
                print(f"[LLMClient] Gemini error, fallback to Groq: {e}", flush=True)

        # 2. Fallback Groq / Claude
        if self.provider == "anthropic":
            return await self.claude_service.chat_completion(
                messages=messages,
                tools=tools,
                temperature=temperature,
                max_tokens=max_tokens
            )
        else:
            return await self.groq_service.chat_completion(
                messages=messages,
                tools=tools,
                temperature=temperature,
                max_tokens=max_tokens
            )

    async def analyze_thumbnail(self, image_url: str, video_title: str) -> Dict[str, Any]:
        """Phân tích thumbnail dựa trên provider đang kích hoạt."""
        if self.provider == "anthropic":
            return await self.claude_service.analyze_thumbnail_image(image_url, video_title)
        else:
            return await self.groq_service.analyze_thumbnail_simplified(image_url, video_title)

# Singleton client
llm_client = LLMClient()

__all__ = ["llm_client", "LLMClient", "strip_think_tags"]
