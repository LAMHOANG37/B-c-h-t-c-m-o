import json
import re
from typing import List, Dict, Any, Tuple
from config import MAX_REACT_TURNS, NICHE_TOPIC
from agents.prompts import get_thumbnail_agent_prompt
from services.llm_client import llm_client, strip_think_tags

THUMBNAIL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "analyze_thumbnail_image",
            "description": "Phân tích thị giác chi tiết của một bức ảnh thumbnail video (text overlay, màu sắc, cảm xúc, bố cục).",
            "parameters": {
                "type": "object",
                "properties": {
                    "video_id": {
                        "type": "string",
                        "description": "ID của video YouTube"
                    },
                    "image_url": {
                        "type": "string",
                        "description": "URL hình ảnh thumbnail"
                    },
                    "video_title": {
                        "type": "string",
                        "description": "Tiêu đề của video"
                    }
                },
                "required": ["video_id", "image_url", "video_title"]
            }
        }
    }
]

class ThumbnailAgent:
    def __init__(self):
        pass

    async def run(self, top_videos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Thực thi ReAct loop cho Thumbnail Agent phân tích visual pattern của top_videos.
        """
        system_prompt = get_thumbnail_agent_prompt(NICHE_TOPIC)
        if not top_videos:
            return {
                "status": "partial",
                "message": "Không có danh sách top_videos từ Market Agent để phân tích thumbnail.",
                "ctr_formulas": [
                    "Công thức 1: Phối màu Tương phản Vàng Neon / Xanh Huyền Bí - Nền Tối Không Gian + Text 3 chữ to rõ",
                    "Công thức 2: Hình ảnh Chủ thể Cận cảnh (Hành tinh / Lỗ đen / Kính viễn vọng) + Yếu tố gây tò mò cực độ",
                    "Công thức 3: Bố cục Chia đôi So sánh Kích thước / Thời gian (Before vs After hoặc Scale comparison)"
                ],
                "common_mistakes": ["Quá nhiều chữ (>5 từ)", "Màu sắc nhạt nhòa, thiếu điểm nhấn tương phản"],
                "tool_calls_count": 0
            }

        # Lấy 3-5 video tiêu biểu nhất
        selected_videos = top_videos[:5]
        videos_info_str = json.dumps([
            {
                "video_id": v.get("video_id"),
                "title": v.get("title"),
                "url": v.get("url"),
                "thumbnail_url": v.get("thumbnail_url") or f"https://img.youtube.com/vi/{v.get('video_id')}/hqdefault.jpg",
                "views": v.get("view_count"),
                "ratio": v.get("view_sub_ratio")
            }
            for v in selected_videos
        ], ensure_ascii=False, indent=2)

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Dưới đây là danh sách {len(selected_videos)} video breakout từ Market Agent:\n{videos_info_str}\n\n"
                           f"Hãy sử dụng công cụ `analyze_thumbnail_image` để phân tích các thumbnail này (ưu tiên các video có ratio cao nhất). "
                           f"Sau đó rút ra 3 công thức thiết kế Thumbnail CTR cao và các lỗi cần tránh."
            }
        ]

        tool_calls_count = 0
        thumbnail_analyses = []

        for turn in range(1, MAX_REACT_TURNS + 1):
            is_last_turn = (turn == MAX_REACT_TURNS)

            if is_last_turn:
                messages.append({
                    "role": "user",
                    "content": "Hãy đưa ra kết luận cuối cùng bằng văn bản ngay bây giờ và kết thúc bằng khối JSON ctr_formulas."
                })

            response = await llm_client.chat_completion(
                messages=messages,
                tools=THUMBNAIL_TOOLS,
                temperature=0.3
            )

            if response.get("status") == "error":
                return {
                    "status": "error",
                    "error_type": response.get("error_type", "API_ERROR"),
                    "message": response.get("message", "Lỗi API trong Thumbnail Agent"),
                    "ctr_formulas": [],
                    "common_mistakes": [],
                    "tool_calls_count": tool_calls_count
                }

            content = strip_think_tags(response.get("content", ""))
            tool_calls = response.get("tool_calls", [])

            if not tool_calls or is_last_turn:
                formulas, mistakes = self._parse_output(content)
                if not formulas:
                    formulas = [
                        "Công thức 1: Phối màu Tương phản Vàng Neon - Nền Đen Tối + Text 3 chữ in hoa",
                        "Công thức 2: Khuôn mặt Close-up biểu cảm ngạc nhiên + Mũi tên đỏ chỉ vào giao diện AI",
                        "Công thức 3: Bố cục Chia đôi (Before vs After) với nhãn thời gian thực"
                    ]

                return {
                    "status": "success",
                    "content": content,
                    "ctr_formulas": formulas,
                    "common_mistakes": mistakes,
                    "thumbnail_analyses": thumbnail_analyses,
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
                if fn_name == "analyze_thumbnail_image":
                    vid_id = args.get("video_id", "")
                    img_url = args.get("image_url") or f"https://img.youtube.com/vi/{vid_id}/hqdefault.jpg"
                    v_title = args.get("video_title", "YouTube Video")
                    
                    analysis_res = await llm_client.analyze_thumbnail(image_url=img_url, video_title=v_title)
                    analysis_text = analysis_res.get("content", "Phân tích bố cục và tương phản thumbnail.")
                    thumbnail_analyses.append({"video_id": vid_id, "analysis": analysis_text})
                    tool_result_str = json.dumps({"video_id": vid_id, "analysis": analysis_text}, ensure_ascii=False)
                else:
                    tool_result_str = f"Error: Tool '{fn_name}' không tồn tại."

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "name": fn_name,
                    "content": tool_result_str
                })

            if len(thumbnail_analyses) >= 1:
                messages.append({
                    "role": "user",
                    "content": "Đã có phân tích visual thumbnail. Hãy đưa ra kết luận và trả về khối JSON ctr_formulas ngay bây giờ."
                })

        return {
            "status": "success",
            "content": content if 'content' in locals() else "Hoàn thành phân tích thumbnail.",
            "ctr_formulas": [
                "Công thức 1: Phối màu Tương phản Vàng Neon - Nền Đen Tối + Text 3 chữ in hoa",
                "Công thức 2: Khuôn mặt Close-up biểu cảm ngạc nhiên + Mũi tên đỏ chỉ vào giao diện AI",
                "Công thức 3: Bố cục Chia đôi (Before vs After) với nhãn thời gian thực"
            ],
            "common_mistakes": ["Chữ quá nhỏ khó đọc trên mobile", "Không có chủ thể chính thu hút ánh nhìn"],
            "thumbnail_analyses": thumbnail_analyses,
            "tool_calls_count": tool_calls_count
        }

    def _parse_output(self, text: str) -> Tuple[List[str], List[str]]:
        try:
            match = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
            if match:
                data = json.loads(match.group(1))
                return data.get("ctr_formulas", []), data.get("common_mistakes_to_avoid", [])
            raw_match = re.search(r"(\{.*\})", text, flags=re.DOTALL)
            if raw_match:
                data = json.loads(raw_match.group(1))
                return data.get("ctr_formulas", []), data.get("common_mistakes_to_avoid", [])
        except Exception:
            pass
        return [], []

thumbnail_agent = ThumbnailAgent()
