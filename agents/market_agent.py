import json
import re
from typing import List, Dict, Any, Tuple
from config import MAX_REACT_TURNS, NICHE_TOPIC
from agents.prompts import get_market_agent_prompt
from services.llm_client import llm_client, strip_think_tags
from services.youtube_service import youtube_service

MARKET_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "youtube_search",
            "description": f"Tìm kiếm video YouTube trong niche '{NICHE_TOPIC}' trong vòng 30 ngày qua theo từ khóa và tiêu chí sắp xếp.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Từ khóa tìm kiếm trên YouTube"
                    },
                    "order": {
                        "type": "string",
                        "enum": ["viewCount", "relevance", "date"],
                        "description": "Thứ tự sắp xếp kết quả (mặc định 'viewCount')"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "youtube_video_stats",
            "description": "Lấy thông số chi tiết (views, likes, subscriber của kênh, tỷ lệ breakout) cho danh sách video_ids.",
            "parameters": {
                "type": "object",
                "properties": {
                    "video_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Danh sách các video ID cần lấy thống kê"
                    }
                },
                "required": ["video_ids"]
            }
        }
    }
]

class MarketAgent:
    def __init__(self):
        pass

    async def run(self, hot_topics: List[str]) -> Dict[str, Any]:
        """
        Thực thi ReAct loop cho Market/Competitor Agent dựa trên hot_topics.
        """
        system_prompt = get_market_agent_prompt(NICHE_TOPIC)
        topics_str = ", ".join(hot_topics) if hot_topics else f"{NICHE_TOPIC} khám phá mới, {NICHE_TOPIC} tài liệu"
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Dưới đây là các chủ đề nóng được phát hiện từ News Agent: [{topics_str}].\n"
                           f"Hãy sử dụng các công cụ YouTube để tìm kiếm các video và kênh bứt phá về '{NICHE_TOPIC}' (breakout: kênh nhỏ nhưng view cao). "
                           f"Thu thập và lọc ra 3-6 video chất lượng nhất và phân tích lý do thành công."
            }
        ]

        tool_calls_count = 0
        known_videos_cache: Dict[str, Dict[str, Any]] = {}
        all_enriched_videos: List[Dict[str, Any]] = []

        for turn in range(1, MAX_REACT_TURNS + 1):
            is_last_turn = (turn == MAX_REACT_TURNS)

            if is_last_turn:
                messages.append({
                    "role": "user",
                    "content": "Hãy đưa ra kết luận cuối cùng bằng văn bản ngay bây giờ và kết thúc bằng khối JSON top_videos."
                })

            response = await llm_client.chat_completion(
                messages=messages,
                tools=MARKET_TOOLS,
                temperature=0.3
            )

            if response.get("status") == "error":
                return {
                    "status": "error",
                    "error_type": response.get("error_type", "API_ERROR"),
                    "message": response.get("message", "Lỗi API trong Market Agent"),
                    "top_videos": [],
                    "market_insights": [],
                    "tool_calls_count": tool_calls_count
                }

            content = strip_think_tags(response.get("content", ""))
            tool_calls = response.get("tool_calls", [])

            if not tool_calls or is_last_turn:
                top_videos, insights = self._parse_output(content)
                if not top_videos and all_enriched_videos:
                    # Fallback lấy từ danh sách video đã crawl được
                    top_videos = self._fallback_top_videos(all_enriched_videos)

                return {
                    "status": "success",
                    "content": content,
                    "top_videos": top_videos,
                    "market_insights": insights,
                    "tool_calls_count": tool_calls_count
                }

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
                if fn_name == "youtube_search":
                    query = args.get("query", hot_topics[0] if hot_topics else "AI Video")
                    order = args.get("order", "viewCount")
                    videos = await youtube_service.search_videos(query=query, order=order, max_results=8)
                    for v in videos:
                        known_videos_cache[v["video_id"]] = v
                    tool_result_str = json.dumps([
                        {"video_id": v["video_id"], "title": v["title"], "channel": v["channel_title"]}
                        for v in videos
                    ], ensure_ascii=False)

                elif fn_name == "youtube_video_stats":
                    vid_ids = args.get("video_ids", [])
                    target_items = [known_videos_cache[vid] for vid in vid_ids if vid in known_videos_cache]
                    # Nếu chưa có trong cache, tạo item tối thiểu
                    if not target_items:
                        target_items = [{"video_id": vid, "channel_id": ""} for vid in vid_ids]
                    
                    enriched = await youtube_service.get_video_stats_and_breakout(target_items)
                    all_enriched_videos.extend(enriched)
                    tool_result_str = json.dumps([
                        {
                            "video_id": v.get("video_id"),
                            "title": v.get("title"),
                            "views": v.get("view_count"),
                            "subs": v.get("subscriber_count"),
                            "ratio": v.get("view_sub_ratio"),
                            "is_breakout": v.get("is_breakout"),
                            "breakout_tier": v.get("breakout_tier")
                        }
                        for v in enriched
                    ], ensure_ascii=False)
                else:
                    tool_result_str = f"Error: Tool '{fn_name}' không tồn tại."

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "name": fn_name,
                    "content": tool_result_str
                })

            if len(all_enriched_videos) >= 3:
                messages.append({
                    "role": "user",
                    "content": "Đã có đầy đủ số liệu YouTube. Hãy đưa ra kết luận phân tích và trả về khối JSON top_videos ngay bây giờ."
                })

        return {
            "status": "success",
            "content": content if 'content' in locals() else "Hoàn thành phân tích thị trường YouTube.",
            "top_videos": self._fallback_top_videos(all_enriched_videos),
            "market_insights": [],
            "tool_calls_count": tool_calls_count
        }

    def _parse_output(self, text: str) -> Tuple[List[Dict[str, Any]], List[str]]:
        try:
            match = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
            if match:
                data = json.loads(match.group(1))
                return data.get("top_videos", []), data.get("market_insights", [])
            raw_match = re.search(r"(\{.*\})", text, flags=re.DOTALL)
            if raw_match:
                data = json.loads(raw_match.group(1))
                return data.get("top_videos", []), data.get("market_insights", [])
        except Exception:
            pass
        return [], []

    def _fallback_top_videos(self, enriched_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        for v in enriched_list[:5]:
            results.append({
                "video_id": v.get("video_id", ""),
                "title": v.get("title", "Video Phân Tích"),
                "channel_title": v.get("channel_title", "Kênh YouTube"),
                "url": v.get("url", f"https://www.youtube.com/watch?v={v.get('video_id')}"),
                "thumbnail_url": v.get("thumbnail_url", f"https://img.youtube.com/vi/{v.get('video_id')}/hqdefault.jpg"),
                "view_count": v.get("view_count", 0),
                "subscriber_count": v.get("subscriber_count", 0),
                "view_sub_ratio": v.get("view_sub_ratio", 1.0),
                "breakout_reason": v.get("breakout_tier", "Tín hiệu tương tác cao")
            })
        return results

market_agent = MarketAgent()
