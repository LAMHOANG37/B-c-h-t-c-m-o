import os
import re
import json
import time
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from groq import Groq, RateLimitError, BadRequestError, APIError
from config import GROQ_API_KEY, GROQ_TOOL_MODEL, GROQ_VISION_MODEL
from services.quota_tracker import quota_tracker

def strip_think_tags(text: str) -> str:
    """Loại bỏ hoàn toàn các thẻ <think>...</think> sinh ra bởi reasoning model."""
    if not text:
        return ""
    # Xử lý cả thẻ đóng mở hoàn chỉnh và trường hợp thẻ chưa đóng hết
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    cleaned = re.sub(r"<think>.*", "", cleaned, flags=re.DOTALL)
    return cleaned.strip()

class GroqService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or GROQ_API_KEY
        self.client = None
        if self.api_key:
            try:
                self.client = Groq(api_key=self.api_key)
            except Exception as e:
                print(f"[GroqService] Init error: {e}")

    def is_configured(self) -> bool:
        return bool(self.api_key and self.client)

    def test_connection(self) -> Tuple[bool, str]:
        """Kiểm tra API Key và model gpt-oss-120b bằng một request nhẹ."""
        if not self.client:
            return False, "Chưa cấu hình GROQ_API_KEY hoặc client chưa khởi tạo."
        try:
            resp = self.client.chat.completions.create(
                model=GROQ_TOOL_MODEL,
                messages=[{"role": "user", "content": "Hello, respond with 'OK'"}],
                max_tokens=10
            )
            content = strip_think_tags(resp.choices[0].message.content or "")
            return True, f"Groq ({GROQ_TOOL_MODEL}) kết nối thành công: {content}"
        except BadRequestError as e:
            return False, f"Groq BadRequest (400 - Key/Credit/Model): {e.message}"
        except RateLimitError as e:
            return False, f"Groq RateLimit (429): {e.message}"
        except Exception as e:
            return False, f"Groq API Error: {str(e)}"

    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Gọi chat completion tới Groq kèm retry exponential backoff khi gặp 429.
        """
        if not self.client:
            return {
                "status": "error",
                "error_type": "NOT_CONFIGURED",
                "message": "Groq client chưa được cấu hình API Key."
            }

        selected_model = model or GROQ_TOOL_MODEL
        max_retries = 3
        backoff_delays = [2, 4, 8]

        for attempt in range(max_retries + 1):
            try:
                def _sync_call():
                    kwargs = {
                        "model": selected_model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    }
                    if tools:
                        kwargs["tools"] = tools
                        kwargs["tool_choice"] = "auto"
                    
                    # Gọi API có kèm response headers thô nếu hỗ trợ
                    raw_response = self.client.chat.completions.with_raw_response.create(**kwargs)
                    response = raw_response.parse()
                    headers = dict(raw_response.headers)
                    return response, headers

                response, headers = await asyncio.to_thread(_sync_call)

                # Cập nhật thông tin quota
                usage = getattr(response, "usage", None)
                tokens_used = usage.total_tokens if usage else 0
                quota_tracker.update_llm_headers(headers, used_tokens=tokens_used)

                msg = response.choices[0].message
                content = strip_think_tags(msg.content or "")
                tool_calls = []

                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        tool_calls.append({
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        })

                return {
                    "status": "success",
                    "content": content,
                    "tool_calls": tool_calls,
                    "raw_message": msg
                }

            except RateLimitError as e:
                quota_tracker.record_rate_limit_hit()
                print(f"[GroqService] Rate limit (429) hit on attempt {attempt + 1}: {e}")
                if attempt < max_retries:
                    wait_time = backoff_delays[attempt]
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    return {
                        "status": "error",
                        "error_type": "RATE_LIMIT_EXHAUSTED",
                        "message": f"Groq Rate limit 429: Đã thử lại {max_retries} lần nhưng không thành công. {e.message}"
                    }

            except BadRequestError as e:
                print(f"[GroqService] Bad Request (400): {e.message}")
                return {
                    "status": "error",
                    "error_type": "BAD_REQUEST",
                    "message": f"Groq 400 Bad Request: {e.message}"
                }

            except APIError as e:
                print(f"[GroqService] API Error ({getattr(e, 'status_code', 'unknown')}): {e.message}")
                return {
                    "status": "error",
                    "error_type": "API_ERROR",
                    "message": f"Groq API Error: {e.message}"
                }

            except Exception as e:
                print(f"[GroqService] Unexpected error: {e}")
                return {
                    "status": "error",
                    "error_type": "UNKNOWN",
                    "message": f"Lỗi không xác định khi gọi Groq: {str(e)}"
                }

    async def analyze_thumbnail_simplified(self, image_url: str, video_title: str) -> Dict[str, Any]:
        """
        Chế độ đơn giản hoá cho Groq với model qwen/qwen3.6-27b.
        Xác nhận thông tin URL và tạo phân tích cơ bản dựa trên tiêu đề và visual metadata.
        """
        messages = [
            {
                "role": "system",
                "content": "Bạn là chuyên gia phân tích Thumbnail YouTube. Hãy đánh giá cấu trúc thumbnail và đưa ra lời khuyên CTR."
            },
            {
                "role": "user",
                "content": f"Phân tích tiềm năng CTR của thumbnail cho video:\n- Tiêu đề: {video_title}\n- URL ảnh thumbnail: {image_url}\n\nHãy phân tích: Màu sắc dự kiến, bố cục tương phản, text overlay, và điểm thu hút người xem."
            }
        ]
        res = await self.chat_completion(
            messages=messages,
            model=GROQ_VISION_MODEL,
            temperature=0.3,
            max_tokens=600
        )
        return res
