import os
import base64
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional, Tuple
import anthropic
from anthropic import Anthropic, APIStatusError, RateLimitError, BadRequestError
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from services.quota_tracker import quota_tracker

class ClaudeService:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or ANTHROPIC_API_KEY
        self.model = model or CLAUDE_MODEL
        self.client = None
        if self.api_key:
            try:
                self.client = Anthropic(api_key=self.api_key)
            except Exception as e:
                print(f"[ClaudeService] Init error: {e}")

    def is_configured(self) -> bool:
        return bool(self.api_key and self.client)

    def test_connection(self) -> Tuple[bool, str]:
        """Kiểm tra kết nối Claude API với 1 request nhẹ."""
        if not self.client:
            return False, "Chưa cấu hình ANTHROPIC_API_KEY hoặc client chưa khởi tạo."
        try:
            resp = self.client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hello, reply 'OK'"}]
            )
            text = resp.content[0].text if resp.content else ""
            return True, f"Claude ({self.model}) kết nối thành công: {text.strip()}"
        except BadRequestError as e:
            return False, f"Claude 400 Bad Request: {e.message}"
        except RateLimitError as e:
            return False, f"Claude 429 Rate Limit: {e.message}"
        except Exception as e:
            return False, f"Claude API Error: {str(e)}"

    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048
    ) -> Dict[str, Any]:
        """
        Gọi chat completion tới Claude với định dạng tool tương thích.
        """
        if not self.client:
            return {
                "status": "error",
                "error_type": "NOT_CONFIGURED",
                "message": "Claude client chưa được cấu hình API Key."
            }

        # Chuyển đổi system message nếu có trong messages list
        system_prompt = ""
        filtered_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_prompt += msg["content"] + "\n"
            else:
                filtered_messages.append(msg)

        # Chuyển đổi tools sang schema Anthropic nếu cần
        claude_tools = None
        if tools:
            claude_tools = []
            for t in tools:
                if "function" in t:
                    fn = t["function"]
                    claude_tools.append({
                        "name": fn["name"],
                        "description": fn.get("description", ""),
                        "input_schema": fn.get("parameters", {"type": "object", "properties": {}})
                    })
                else:
                    claude_tools.append(t)

        max_retries = 3
        backoff_delays = [2, 4, 8]

        for attempt in range(max_retries + 1):
            try:
                def _sync_call():
                    kwargs = {
                        "model": self.model,
                        "messages": filtered_messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    }
                    if system_prompt:
                        kwargs["system"] = system_prompt.strip()
                    if claude_tools:
                        kwargs["tools"] = claude_tools

                    response = self.client.messages.create(**kwargs)
                    return response

                response = await asyncio.to_thread(_sync_call)

                # Tracking usage
                tokens_used = (response.usage.input_tokens + response.usage.output_tokens) if response.usage else 0
                quota_tracker.update_llm_headers({}, used_tokens=tokens_used)

                content_blocks = []
                tool_calls = []

                for block in response.content:
                    if block.type == "text":
                        content_blocks.append(block.text)
                    elif block.type == "tool_use":
                        import json
                        tool_calls.append({
                            "id": block.id,
                            "type": "function",
                            "function": {
                                "name": block.name,
                                "arguments": json.dumps(block.input) if isinstance(block.input, dict) else str(block.input)
                            }
                        })

                return {
                    "status": "success",
                    "content": "\n".join(content_blocks).strip(),
                    "tool_calls": tool_calls,
                    "raw_message": response
                }

            except RateLimitError as e:
                quota_tracker.record_rate_limit_hit()
                print(f"[ClaudeService] Rate limit (429) hit on attempt {attempt + 1}: {e}")
                if attempt < max_retries:
                    wait_time = backoff_delays[attempt]
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    return {
                        "status": "error",
                        "error_type": "RATE_LIMIT_EXHAUSTED",
                        "message": f"Claude Rate limit 429: Đã thử lại {max_retries} lần. {e.message}"
                    }

            except BadRequestError as e:
                print(f"[ClaudeService] Bad Request (400): {e.message}")
                return {
                    "status": "error",
                    "error_type": "BAD_REQUEST",
                    "message": f"Claude 400 Bad Request: {e.message}"
                }

            except Exception as e:
                print(f"[ClaudeService] API Error: {e}")
                return {
                    "status": "error",
                    "error_type": "API_ERROR",
                    "message": f"Claude API Error: {str(e)}"
                }

    async def analyze_thumbnail_image(self, image_url: str, video_title: str) -> Dict[str, Any]:
        """
        Tải ảnh thumbnail và gửi qua Claude Vision để phân tích chi tiết.
        """
        try:
            # Tải ảnh qua aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        return {
                            "status": "error",
                            "message": f"Không thể tải thumbnail từ URL (HTTP {resp.status})"
                        }
                    image_bytes = await resp.read()
                    content_type = resp.headers.get("Content-Type", "image/jpeg")

            base64_image = base64.b64encode(image_bytes).decode("utf-8")
            media_type = content_type if "image" in content_type else "image/jpeg"

            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64_image
                            }
                        },
                        {
                            "type": "text",
                            "text": f"Phân tích chuyên sâu hình ảnh Thumbnail YouTube này cho video '{video_title}'.\n"
                                    f"Đánh giá:\n"
                                    f"1. Text Overlay (Độ ngắn gọn, font, tương phản, hook từ ngữ)\n"
                                    f"2. Màu sắc & Ánh sáng (Phối màu, điểm nhấn tương phản)\n"
                                    f"3. Yếu tố con người / Cảm xúc (Biểu cảm gương mặt, ánh nhìn, sự tò mò)\n"
                                    f"4. Bố cục (Quy tắc 1/3, khoảng trống, điểm neo thị giác)\n"
                                    f"5. Điểm mạnh và công thức CTR rút ra."
                        }
                    ]
                }
            ]

            return await self.chat_completion(messages=messages, max_tokens=1000)

        except Exception as e:
            return {
                "status": "error",
                "message": f"Lỗi phân tích hình ảnh thumbnail qua Claude: {str(e)}"
            }
