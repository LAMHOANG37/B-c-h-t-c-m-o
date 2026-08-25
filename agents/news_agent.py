import json
import re
from typing import List, Dict, Any, Tuple
from config import MAX_REACT_TURNS, NICHE_TOPIC, NICHE_KEYWORDS_HINT
from agents.prompts import get_news_agent_prompt
from services.llm_client import llm_client, strip_think_tags
from services.search_service import SearchService
from services.quota_tracker import quota_tracker

NEWS_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": f"Tìm kiếm tin tức, sự kiện, khám phá mới trong niche '{NICHE_TOPIC}' trên web trong vòng 30 ngày qua.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": f"Từ khóa tìm kiếm (ví dụ: '{NICHE_TOPIC} new discovery 2024', '{NICHE_KEYWORDS_HINT.split(',')[0]}')"
                    }
                },
                "required": ["query"]
            }
        }
    }
]

class NewsAgent:
    def __init__(self):
        pass

    async def run(self) -> Dict[str, Any]:
        """
        Thực thi ReAct loop cho News/Trend Agent.
        Tối đa MAX_REACT_TURNS (6 lượt).
        """
        system_prompt = get_news_agent_prompt(NICHE_TOPIC, NICHE_KEYWORDS_HINT)
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Hãy bắt đầu nghiên cứu các xu hướng, sự kiện và tin tức nổi bật nhất về '{NICHE_TOPIC}' trong 30 ngày gần đây (gợi ý các từ khóa: {NICHE_KEYWORDS_HINT}). Tìm kiếm từ 4-6 tin tức có giá trị và trích xuất danh sách 3-6 hot_topics cụ thể."
            }
        ]

        tool_calls_count = 0
        collected_articles = []

        for turn in range(1, MAX_REACT_TURNS + 1):
            is_last_turn = (turn == MAX_REACT_TURNS)
            
            if is_last_turn:
                messages.append({
                    "role": "user",
                    "content": "Hãy đưa ra kết luận cuối cùng bằng văn bản ngay bây giờ và kết thúc bằng khối JSON hot_topics."
                })

            response = await llm_client.chat_completion(
                messages=messages,
                tools=NEWS_TOOLS,
                temperature=0.3
            )

            if response.get("status") == "error":
                return {
                    "status": "error",
                    "error_type": response.get("error_type", "API_ERROR"),
                    "message": response.get("message", "Lỗi API trong News Agent"),
                    "hot_topics": [],
                    "summary": "",
                    "tool_calls_count": tool_calls_count
                }

            content = strip_think_tags(response.get("content", ""))
            tool_calls = response.get("tool_calls", [])

            # Nếu không có tool call hoặc là lượt cuối, hoàn tất ReAct loop
            if not tool_calls or is_last_turn:
                hot_topics, summary_points = self._parse_output(content)
                # Fallback nếu JSON parse trống nhưng có nội dung
                if not hot_topics and content:
                    hot_topics = self._fallback_extract_topics(content)

                return {
                    "status": "success",
                    "content": content,
                    "hot_topics": hot_topics,
                    "summary_points": summary_points,
                    "articles": collected_articles,
                    "tool_calls_count": tool_calls_count
                }

            # Xử lý các tool calls từ model
            messages.append({
                "role": "assistant",
                "content": content if content else None,
                "tool_calls": response.get("raw_message").tool_calls if hasattr(response.get("raw_message"), "tool_calls") else None
            })

            for tc in tool_calls:
                tool_calls_count += 1
                fn_name = tc["function"]["name"]
                args_str = tc["function"]["arguments"]
                
                try:
                    args = json.loads(args_str) if isinstance(args_str, str) else args_str
                except Exception:
                    args = {}

                tool_result_str = ""
                if fn_name == "web_search":
                    query = args.get("query", "AI video tools trending")
                    search_res = await SearchService.search_news(query=query, max_results=4, timelimit="m")
                    collected_articles.extend(search_res)
                    tool_result_str = json.dumps(search_res, ensure_ascii=False)
                else:
                    tool_result_str = f"Error: Tool '{fn_name}' không tồn tại."

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "name": fn_name,
                    "content": tool_result_str
                })

            if len(collected_articles) >= 3:
                messages.append({
                    "role": "user",
                    "content": "Đã có đầy đủ bài viết và dữ liệu tin tức. Hãy đưa ra kết luận phân tích và trả về khối JSON hot_topics ngay bây giờ."
                })

        # Fallback kết thúc
        default_fallback_topics = [k.strip() for k in NICHE_KEYWORDS_HINT.split(",") if k.strip()][:4]
        if not default_fallback_topics:
            default_fallback_topics = [f"{NICHE_TOPIC} mới nhất", f"Khám phá {NICHE_TOPIC}"]

        return {
            "status": "success",
            "content": content if 'content' in locals() else f"Hoàn thành phân tích tin tức về {NICHE_TOPIC}.",
            "hot_topics": default_fallback_topics,
            "summary_points": [],
            "articles": collected_articles,
            "tool_calls_count": tool_calls_count
        }

    def _parse_output(self, text: str) -> Tuple[List[str], List[str]]:
        """Trích xuất hot_topics và summary_points từ khối JSON trong text."""
        try:
            match = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
            if match:
                data = json.loads(match.group(1))
                return data.get("hot_topics", []), data.get("summary_points", [])
            # Thử parse JSON trực tiếp nếu không có markdown block
            raw_match = re.search(r"(\{.*\})", text, flags=re.DOTALL)
            if raw_match:
                data = json.loads(raw_match.group(1))
                return data.get("hot_topics", []), data.get("summary_points", [])
        except Exception:
            pass
        return [], []

    def _fallback_extract_topics(self, text: str) -> List[str]:
        """Tự động tách các từ khóa dạng gạch đầu dòng nếu LLM không trả JSON đúng định dạng."""
        topics = []
        for line in text.splitlines():
            line = line.strip()
            if line.startswith(("- ", "* ", "1.", "2.", "3.", "4.", "5.")):
                topic_clean = re.sub(r"^[-*\d.]+\s*", "", line).strip()
                if len(topic_clean) > 3 and len(topic_clean) < 60:
                    topics.append(topic_clean)
        
        default_fallback_topics = [k.strip() for k in NICHE_KEYWORDS_HINT.split(",") if k.strip()][:4]
        return topics[:5] if topics else default_fallback_topics

news_agent = NewsAgent()
