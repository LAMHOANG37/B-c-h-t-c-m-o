import os
import time
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from config import GEMINI_API_KEY
from services.quota_tracker import quota_tracker

class GeminiService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "").strip()
        self.client = None
        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"[GeminiService] Init error: {e}")

    def is_configured(self) -> bool:
        return bool(self.api_key and self.client)

    def test_connection(self) -> Tuple[bool, str]:
        if not self.client:
            return False, "Chưa cấu hình GEMINI_API_KEY."
        try:
            res = self.client.models.generate_content(
                model='gemini-3.6-flash',
                contents="Hello, respond with 'OK'"
            )
            return True, f"Google Gemini (gemini-3.6-flash) kết nối thành công: {res.text[:30]}"
        except Exception as e:
            return False, f"Lỗi kết nối Gemini: {e}"

    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> Dict[str, Any]:
        if not self.client:
            return {"content": "", "finish_reason": "error"}

        # Chuyển đổi format messages thành prompt text hoặc contents
        system_instruction = ""
        user_parts = []
        
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                system_instruction += f"{content}\n"
            elif role == "assistant":
                user_parts.append(f"Assistant: {content}")
            else:
                user_parts.append(f"User: {content}")

        full_prompt = "\n".join(user_parts)

        try:
            t0 = time.perf_counter()
            from google.genai import types

            config = types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                system_instruction=system_instruction.strip() if system_instruction else None
            )

            # Chạy trong executor để không block asyncio loop
            loop = asyncio.get_running_loop()
            res = await loop.run_in_executor(
                None,
                lambda: self.client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=full_prompt,
                    config=config
                )
            )

            latency_ms = (time.perf_counter() - t0) * 1000
            quota_tracker.add_gemini_request(latency_ms=latency_ms)

            return {
                "content": res.text if res.text else "",
                "finish_reason": "stop",
                "provider": "Google Gemini 3.6 Flash",
                "latency_ms": latency_ms
            }
        except Exception as e:
            print(f"[GeminiService] Chat completion error: {e}", flush=True)
            return {"content": "", "finish_reason": "error"}
