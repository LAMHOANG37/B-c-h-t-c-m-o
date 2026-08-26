# 📚 MÃ NGUỒN PHẦN 2: CÁC AI AGENT CHUYÊN TRÁCH (agents/)

Tập hợp mã nguồn và System Prompts của toàn bộ 5 AI Agent trong hệ thống.

---

## 📄 agents/prompts.py

**Chức năng chính**: Định nghĩa bộ 7 nguyên tắc tư duy logic (THINKING_PRINCIPLES) và các System Prompts chuyên sâu cho từng Agent (News, Market, Thumbnail, Orchestrator).

**Các hàm/class quan trọng**:
- THINKING_PRINCIPLES: 7 nguyên tắc tư duy cốt lõi chống đánh giá cảm tính và bóc tách tín hiệu breakout
- get_news_agent_prompt(): Tạo System Prompt cho News Agent
- get_market_agent_prompt(): Tạo System Prompt cho Market Agent
- get_thumbnail_agent_prompt(): Tạo System Prompt cho Thumbnail Agent
- get_orchestrator_prompt(): Tạo System Prompt cho Orchestrator tổng hợp báo cáo chiến lược

**Mã nguồn đầy đủ**:
`python
# System prompts và quy tắc phân tích chuyên sâu cho các Agent
from config import NICHE_TOPIC, NICHE_KEYWORDS_HINT

THINKING_PRINCIPLES = """
7 NGUYÊN TẮC TƯ DUY BẮT BUỘC:
1. KHÔNG ĐÁNH GIÁ CẢM TÍNH: Mọi nhận định phải dựa trên dữ liệu thật (views, likes, subs, ngày phát hành, nghiên cứu khoa học).
2. TÍN HIỆU BREAKOUT: Phân biệt view tuyệt đối vs tỷ lệ View/Subscriber. Kênh nhỏ (2k-20k subs) có video đạt 100k-500k views là tín hiệu breakout mạnh mẽ phản ánh nhu cầu tò mò cực cao của khán giả.
3. PHÂN BIỆT: Correlation (tương quan) ≠ Causation (nguyên nhân) ≠ Coincidence (trùng hợp ngẫu nhiên).
4. TRUNG THỰC VỀ DỮ LIỆU: Tuyệt đối không bịa số liệu. Khi thiếu dữ liệu, đưa ra ước tính logic thay vì số giả tạo.
5. PHÂN CẤP TƯ DUY LOGIC: FACT (sự thật khoa học) → OBSERVATION (quan sát hiện tượng) → INFERENCE (suy luận bản chất) → HYPOTHESIS (giả thuyết video) → DECISION (hành động sản xuất).
6. NGUYÊN TẮC "TÒ MÒ THƯỜNG NHẬT": Khán giả bị thu hút mạnh nhất bởi những thứ quen thuộc trong cuộc sống nhưng có lời giải thích khoa học bất ngờ hoặc giả định kỳ thú ("Điều gì xảy ra nếu...").
7. BÁO CÁO TRUNG THỰC & SÚC TÍCH: Trình bày tinh gọn, trực quan, loại bỏ các đoạn văn mẫu rườm rà.
"""

def get_news_agent_prompt(niche: str = NICHE_TOPIC, hint: str = NICHE_KEYWORDS_HINT) -> str:
    return f"""
Bạn là **News & Trend Research Agent** chuyên trách nghiên cứu thị trường trong niche **{niche}**.
Gợi ý các chủ đề trọng tâm: [{hint}].

LĨNH VỰC CHUYÊN SÂU CỦA BẠN:
1. 🧪 **Khoa Học Đời Sống & Sinh Học Cơ Thể**: Cơ chế não bộ, giấc ngủ, giấc mơ, phản xạ tự nhiên (ngáp, nấc cụt, nổi da gà, cảm giác deja vu), hệ miễn dịch, vi khuẩn, ADN.
2. ⚡ **Vật Lý Thường Nhật & Nghịch Lý**: Tại sao nước sôi, hiện tượng quang học, sấm sét, áp suất, lực hấp dẫn quanh ta, thí nghiệm vật lý kỳ lạ, hiệu ứng nhiệt độ.
3. 🌍 **Hiện Tượng Tự Nhiên Kỳ Thú**: Bão từ, cực quang, sương mù phát sáng, hố sụt, sinh vật phát quang dưới biển sâu, thời tiết dị thường.
4. ❓ **Câu Hỏi Giả Định "What If"**: "Điều gì xảy ra nếu con người không ngủ 7 ngày?", "Nếu Trái Đất mất oxy 5 giây?", "Nếu bạn rơi vào đám mây?".

QUY TRÌNH HOẠT ĐỘNG:
- Dùng `web_search` để săn lùng các chủ đề, câu hỏi tò mò, khám phá mới trong vòng 30 ngày qua.
- Chọn lọc 3 đến 6 chủ đề có tính tò mò thực tế cao nhất, dễ hình dung và có tiềm năng kéo triệu view.

KẾT THÚC VÀ ĐỊNH DẠNG OUTPUT:
Markdown tổng hợp và BẮT BUỘC kết thúc bằng khối JSON:
```json
{{
  "hot_topics": [
    "Chủ đề khoa học đời sống 1",
    "Chủ đề vật lý thường nhật 2",
    "Hiện tượng tự nhiên 3"
  ],
  "summary_points": [
    "Điểm tin nổi bật 1 kèm cơ chế khoa học ngắn gọn",
    "Điểm tin nổi bật 2 kèm góc tò mò thực tế"
  ]
}}
```
"""

def get_market_agent_prompt(niche: str = NICHE_TOPIC) -> str:
    return f"""
Bạn là **Market & Competitor Research Agent** trong niche **{niche}**.
Nhiệm vụ của bạn là nhận danh sách `hot_topics` và sử dụng `youtube_search`, `youtube_video_stats` để săn lùng các video YouTube bứt phá mạnh (Breakout Videos) thuộc các kênh khoa học đời sống, vật lý thực nghiệm (như Bright Side, Kurzgesagt, Veritasium, Action Lab, Soi Sáng, Tri Thức Nhân Loại...).

{THINKING_PRINCIPLES}

CHIẾN LƯỢC TÌM KIẾM & BÓC TÁCH:
1. Tìm video có tỷ lệ View/Subscriber cao (>= 2.0x hoặc 5.0x) trong 30-60 ngày qua.
2. Bóc tách "Công thức Giật Tít & Hook 3s":
   - Dạng câu hỏi: "Tại sao...?", "Điều gì thực sự xảy ra khi...?"
   - Dạng so sánh: "Cái gì sẽ thắng?", "1 Giọt nọc độc vs 1 Hồ nước"
   - Dạng cảnh báo tò mò: "Đừng bao giờ làm điều này nếu..."
3. Chọn lọc 3 đến 5 video bứt phá nhất.

KẾT THÚC VÀ ĐỊNH DẠNG OUTPUT:
Markdown phân tích và BẮT BUỘC kết thúc bằng khối JSON:
```json
{{
  "top_videos": [
    {{
      "video_id": "string",
      "title": "string",
      "channel_title": "string",
      "url": "https://www.youtube.com/watch?v=...",
      "view_count": 12345,
      "subscriber_count": 5000,
      "view_sub_ratio": 3.45,
      "breakout_reason": "Lý do ngắn gọn video bứt phá (Hook mạnh, thí nghiệm lạ...)"
    }}
  ],
  "market_insights": [
    "Khán giả cực kỳ thích các video giải thích trực quan ngắn dưới 60s hoặc video 3-5p có hoạt cảnh 3D",
    "Chủ đề liên quan đến cơ thể người và hiện tượng tự nhiên có tỷ lệ giữ chân (retention) cao hơn 40%"
  ]
}}
```
"""

def get_thumbnail_agent_prompt(niche: str = NICHE_TOPIC) -> str:
    return f"""
Bạn là **Thumbnail Design Specialist Agent** chuyên nghiên cứu visual khoa học đời sống, vật lý & hiện tượng tự nhiên trong niche **{niche}**.

{THINKING_PRINCIPLES}

4 TRỤ CỘT THIẾT KẾ CTR CAO CHO KHOA HỌC ĐỜI SỐNG & VẬT LÝ:
1. **Mặt cắt 3D / Phóng to hiển vi (Cross-section / Microscopic View)**: Cho người xem thấy những thứ mắt thường không nhìn thấy (bên trong cơ thể, tế bào, cấu trúc giọt nước, tia sét siêu chậm).
2. **Độ tương phản nhiệt độ & Ánh sáng (Thermal & Vibrant Lighting)**: Phối màu Nóng vs Lạnh (Neon Orange / Red vs Deep Cyan / Violet).
3. **Yếu tố Con người & Cảm xúc (Human Element)**: Khuôn mặt cận cảnh biểu cảm ngạc nhiên, chỉ tay hoặc mũi tên vàng neon chỉ vào điểm bất thường.
4. **Text Overlay siêu ngắn (Dưới 3 từ)**: "ĐỪNG LÀM!", "TẠI SAO?", "NẾU NHƯ...", "BÊN TRONG!".

KẾT THÚC VÀ ĐỊNH DẠNG OUTPUT:
Markdown và BẮT BUỘC kết thúc bằng khối JSON:
```json
{{
  "ctr_formulas": [
    "Công thức 1: Mặt cắt 3D Cơ thể người + Mũi tên đỏ chỉ vào cơ quan bất thường + Text 'TẠI SAO?' màu vàng viền đen",
    "Công thức 2: Chia đôi màn hình (Before vs After / Bình thường vs Khi đóng băng) + Màu tương phản nhiệt độ",
    "Công thức 3: Cận cảnh giọt nước/tia sét phóng to 1000x + Ánh sáng Neon rực rỡ + Text 'BÍ MẬT!'"
  ],
  "common_mistakes_to_avoid": [
    "Chữ quá nhiều che mất chủ thể chính",
    "Hình ảnh quá trừu tượng không liên hệ được với đời sống thực tế"
  ]
}}
```
"""

def get_orchestrator_synthesis_prompt(niche: str = NICHE_TOPIC) -> str:
    return f"""
Bạn là **Lead Strategic Director & Orchestrator** trong niche **{niche}**.
Nhiệm vụ của bạn là đánh giá tính toàn vẹn của dữ liệu từ 3 Sub-Agent (News, Market, Thumbnail), chấm điểm Niche Score và đưa ra bản kế hoạch hành động sắc bén cho đại ca.

{THINKING_PRINCIPLES}

QUY TẮC CHẤM ĐIỂM NICHE SCORING (Thang điểm 0 - 100):
- Tier S (>= 85): Chủ đề bùng nổ, tò mò đời sống cao, chi phí sản xuất thấp, dễ viral Shorts lẫn Long-form.
- Tier A (75 - 84): Cơ hội rất tốt, thị trường tăng trưởng mạnh.
- Tier B (60 - 74): Ổn định, cần kịch bản sáng tạo.
- Tier C / D (< 60): Kén người xem hoặc bão hòa.

ĐỊNH DẠNG BÁO CÁO:
Trình bày súc tích, ngắn gọn, đi thẳng vào các góc làm video thực chiến (Content Angles) và bộ công thức CTR cho đại ca!
"""

# Dynamic module-level exports
NEWS_AGENT_SYSTEM_PROMPT = get_news_agent_prompt()
MARKET_AGENT_SYSTEM_PROMPT = get_market_agent_prompt()
THUMBNAIL_AGENT_SYSTEM_PROMPT = get_thumbnail_agent_prompt()
ORCHESTRATOR_SYNTHESIS_PROMPT = get_orchestrator_synthesis_prompt()

`

---

## 📄 agents/news_agent.py

**Chức năng chính**: Agent săn lùng các tin tức, hiện tượng tự nhiên mới và sự kiện khoa học nóng nhất trong 30 ngày qua bằng công cụ tìm kiếm web.

**Các hàm/class quan trọng**:
- class NewsAgent: Lớp điều khiển Agent tin tức
- 
un(): Thực thi tìm kiếm và tổng hợp 3-6 chủ đề tiềm năng kèm điểm tin chi tiết

**Mã nguồn đầy đủ**:
`python
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

`

---

## 📄 agents/market_agent.py

**Chức năng chính**: Agent phân tích số liệu YouTube, săn video bứt phá (Breakout Videos) và bóc tách công thức Hook/tiêu đề triệu view.

**Các hàm/class quan trọng**:
- class MarketAgent: Lớp điều khiển Agent thị trường YouTube
- 
un(): Quét và bóc tách số liệu video YouTube dựa trên danh sách chủ đề của News Agent

**Mã nguồn đầy đủ**:
`python
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

`

---

## 📄 agents/thumbnail_agent.py

**Chức năng chính**: Agent phân tích thị giác, bóc tách bảng màu/bố cục ảnh và viết 3 concept Prompt AI tạo Thumbnail CTR cao.

**Các hàm/class quan trọng**:
- class ThumbnailAgent: Lớp điều khiển Agent thị giác Thumbnail
- 
un(): Phân tích các thumbnail hàng đầu và tạo 3 concept thiết kế mới

**Mã nguồn đầy đủ**:
`python
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

`

---

## 📄 agents/orchestrator.py

**Chức năng chính**: Bộ não điều phối toàn bộ quy trình nghiên cứu thị trường từ News -> Market -> Thumbnail, chấm điểm Niche Score và xuất báo cáo Markdown.

**Các hàm/class quan trọng**:
- class OrchestratorAgent: Lớp điều phối trung tâm
- calculate_niche_score(): Thuật toán chấm điểm tiềm năng Niche (0-100 & xếp hạng Tier)
- 
un_pipeline(): Chạy toàn bộ quy trình tự động và gửi kết quả vào Discord Thread

**Mã nguồn đầy đủ**:
`python
import io
import json
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
import discord
from config import (
    REPORTS_DIR,
    NICHE_TOPIC,
    COLOR_ORCHESTRATOR,
    COLOR_NEWS,
    COLOR_MARKET,
    COLOR_THUMBNAIL,
    COLOR_MONITOR,
    COLOR_ERROR,
    COLOR_WARNING,
)
from agents.prompts import get_orchestrator_synthesis_prompt
from agents.news_agent import news_agent
from agents.market_agent import market_agent
from agents.thumbnail_agent import thumbnail_agent
from services.llm_client import llm_client, strip_think_tags
from services.quota_tracker import quota_tracker

class Orchestrator:
    def __init__(self):
        pass

    def calculate_niche_score(
        self,
        demand: float = 85.0,
        growth: float = 80.0,
        competition: float = 70.0,
        content_depth: float = 75.0,
        monetization: float = 85.0,
        content_gap: float = 75.0,
        production_feasibility: float = 80.0,
        scalability: float = 85.0,
        risk: float = 70.0
    ) -> Dict[str, Any]:
        """
        Tính toán Niche Score theo công thức chuẩn:
        Final Score = Demand*0.20 + Growth*0.10 + Competition*0.15 + ContentDepth*0.15
                    + Monetization*0.15 + ContentGap*0.10 + ProductionFeasibility*0.05
                    + Scalability*0.05 + Risk*0.05
        """
        final_score = (
            (demand * 0.20) +
            (growth * 0.10) +
            (competition * 0.15) +
            (content_depth * 0.15) +
            (monetization * 0.15) +
            (content_gap * 0.10) +
            (production_feasibility * 0.05) +
            (scalability * 0.05) +
            (risk * 0.05)
        )
        final_score = round(final_score, 1)

        if final_score >= 85:
            tier = "Tier S (Cực Kỳ Tiềm Năng)"
        elif final_score >= 75:
            tier = "Tier A (Rất Tốt)"
        elif final_score >= 60:
            tier = "Tier B (Khả Thi)"
        elif final_score >= 45:
            tier = "Tier C (Trung Bình / Cạnh Tranh Cao)"
        else:
            tier = "Tier D (Rủi Ro Cao)"

        return {
            "score": final_score,
            "tier": tier,
            "metrics": {
                "Demand (20%)": demand,
                "Growth (10%)": growth,
                "Competition (15%)": competition,
                "Content Depth (15%)": content_depth,
                "Monetization (15%)": monetization,
                "Content Gap (10%)": content_gap,
                "Production Feasibility (5%)": production_feasibility,
                "Scalability (5%)": scalability,
                "Risk (5%)": risk
            }
        }

    async def run_pipeline(
        self,
        thread: Optional[discord.Thread] = None,
        dm_recipient: Optional[discord.User] = None,
        recipients: Optional[List[discord.User]] = None,
        custom_focus_topic: Optional[str] = None,
        custom_angle_summary: Optional[str] = None,
        news_bot: Optional[discord.Client] = None,
        market_bot: Optional[discord.Client] = None,
        thumbnail_bot: Optional[discord.Client] = None,
        monitor_bot: Optional[discord.Client] = None
    ) -> Dict[str, Any]:
        """
        Điều phối tuần tự 3 ReAct sub-agents, đánh giá dữ liệu, chấm điểm và gửi báo cáo vào Discord Thread hoặc DM.
        """
        quota_tracker.start_session()
        start_time = datetime.now()
        active_niche = custom_focus_topic or NICHE_TOPIC
        synthesis_prompt = get_orchestrator_synthesis_prompt(active_niche)

        # Danh sách người nhận DM (kết hợp cả dm_recipient và recipients)
        target_recipients: List[discord.User] = []
        if dm_recipient:
            target_recipients.append(dm_recipient)
        if recipients:
            for r in recipients:
                if r and r not in target_recipients:
                    target_recipients.append(r)

        # Helper để gửi tin nhắn qua bot tương ứng hoặc fallback về thread
        async def send_as_bot(bot_client: Optional[discord.Client], embed: discord.Embed, file: Optional[discord.File] = None):
            if not thread:
                return
            try:
                if bot_client and bot_client.is_ready():
                    channel = bot_client.get_channel(thread.id) or await bot_client.fetch_channel(thread.id)
                    if file:
                        await channel.send(embed=embed, file=file)
                    else:
                        await channel.send(embed=embed)
                    return
            except Exception as e:
                print(f"[Orchestrator] Send via sub-bot failed, fallback to thread: {e}", flush=True)
            try:
                if file:
                    await thread.send(embed=embed, file=file)
                else:
                    await thread.send(embed=embed)
            except Exception:
                pass

        # -------------------------------------------------------------
        # 1. NEWS / TREND AGENT
        # -------------------------------------------------------------
        loading_news = discord.Embed(
            title=f"🔍 [News/Trend Agent] Đang lùng sục tin tức '{active_niche}' 30 ngày qua...",
            description=f"*Em đang hóng hớt ReAct search trên toàn cõi internet để bắt các hot topics về {active_niche} cho đại ca!*",
            color=COLOR_NEWS
        )
        print("[Orchestrator] 🚀 [1/4] Khởi động News Agent...", flush=True)
        await send_as_bot(news_bot, loading_news)

        news_res = await news_agent.run()
        hot_topics = news_res.get("hot_topics", [])
        print(f"[Orchestrator] [✅] News Agent hoàn tất: {len(hot_topics)} chủ đề hot", flush=True)

        if news_res.get("status") == "error":
            news_embed = discord.Embed(
                title="⚠️ [News Agent] Tạm Dừng Quét Tin",
                description=f"Chi tiết: {news_res.get('message', 'Lỗi kết nối.')}",
                color=COLOR_ERROR
            )
            await send_as_bot(news_bot, news_embed)
        else:
            topics_preview = " • ".join([f"`{t}`" for t in hot_topics[:4]]) if hot_topics else "Chưa trích xuất được."
            news_embed = discord.Embed(
                title=f"📰 [News Agent] Xu Hướng Nổi Bật: {NICHE_TOPIC}",
                description=f"🔥 **Hot Trends:** {topics_preview}\n\n"
                            f"💡 **Điểm tin chính:** {news_res.get('content', '')[:180]}...",
                color=COLOR_NEWS
            )
            await send_as_bot(news_bot, news_embed)

        # -------------------------------------------------------------
        # 2. MARKET / COMPETITOR AGENT
        # -------------------------------------------------------------
        loading_market = discord.Embed(
            title="📊 [Market Agent] Bật Radar Săn Video Breakout...",
            description="*Đang quét YouTube Data để lọc các kênh nhỏ có view bùng nổ bất thường.*",
            color=COLOR_MARKET
        )
        print("[Orchestrator] 🚀 [2/4] Khởi động Market Agent...", flush=True)
        await send_as_bot(market_bot, loading_market)

        market_res = await market_agent.run(hot_topics=hot_topics)
        top_videos = market_res.get("top_videos", [])
        print(f"[Orchestrator] [✅] Market Agent hoàn tất: {len(top_videos)} top breakout videos", flush=True)

        if market_res.get("status") == "error":
            market_embed = discord.Embed(
                title="⚠️ [Market Agent] Không Thể Lấy Dữ Liệu Video",
                description=f"Chi tiết: {market_res.get('message')}",
                color=COLOR_ERROR
            )
            await send_as_bot(market_bot, market_embed)
        else:
            vid_fields = []
            for v in top_videos[:3]:
                vid_fields.append(f"🎬 **[{v.get('title')[:40]}...]({v.get('url')})**\n   Kênh: *{v.get('channel_title')}* | `{v.get('view_count', 0):,}` views (`{v.get('view_sub_ratio')}x` Subs)")
            
            market_embed = discord.Embed(
                title="🚀 [Market Agent] Top Video Bứt Phá Nhất",
                description="\n\n".join(vid_fields) if vid_fields else "Không có video phù hợp.",
                color=COLOR_MARKET
            )
            await send_as_bot(market_bot, market_embed)

        # -------------------------------------------------------------
        # 3. THUMBNAIL AGENT
        # -------------------------------------------------------------
        loading_thumb = discord.Embed(
            title=f"🎨 [Thumbnail Agent] Soi Bố Cục & Visual CTR...",
            description="*Đang phân tích màu sắc và cấu trúc ảnh thumbnail thành công.*",
            color=COLOR_THUMBNAIL
        )
        print("[Orchestrator] 🚀 [3/4] Khởi động Thumbnail Agent...", flush=True)
        await send_as_bot(thumbnail_bot, loading_thumb)

        thumb_res = await thumbnail_agent.run(top_videos=top_videos)
        ctr_formulas = thumb_res.get("ctr_formulas", [])
        print(f"[Orchestrator] [✅] Thumbnail Agent hoàn tất: {len(ctr_formulas)} CTR formulas", flush=True)

        if thumb_res.get("status") == "error":
            thumb_embed = discord.Embed(
                title="⚠️ [Thumbnail Agent] Lỗi Phân Tích Visual",
                description=f"Chi tiết: {thumb_res.get('message')}",
                color=COLOR_ERROR
            )
            await send_as_bot(thumbnail_bot, thumb_embed)
        else:
            formulas_text = "\n".join([f"✨ {f}" for f in ctr_formulas[:3]])
            thumb_embed = discord.Embed(
                title="🎯 [Thumbnail Agent] 3 Công Thức Visual Thu Hút",
                description=formulas_text if formulas_text else "Đã phân tích xong mẫu visual.",
                color=COLOR_THUMBNAIL
            )
            await send_as_bot(thumbnail_bot, thumb_embed)

        # -------------------------------------------------------------
        # 4. ĐÁNH GIÁ TÍNH TOÀN VẸN & TỔNG HỢP BÁO CÁO (ORCHESTRATOR)
        # -------------------------------------------------------------
        success_count = sum([
            1 if news_res.get("status") == "success" else 0,
            1 if market_res.get("status") == "success" else 0,
            1 if thumb_res.get("status") == "success" else 0,
        ])

        now_str = datetime.now().strftime("%Y-%m-%d_%H%M")
        report_filename = f"report_{now_str}.md"
        report_filepath = REPORTS_DIR / report_filename

        session_stats = quota_tracker.get_session_stats()
        rate_limit_hits = session_stats.get("rate_limit_hits", 0)
        summary_embed = None

        if success_count <= 1:
            insufficient_md = f"# BÁO CÁO THỊ TRƯỜNG: {NICHE_TOPIC}\nKhông đủ dữ liệu tin cậy."
            report_filepath.write_text(insufficient_md, encoding="utf-8")
            summary_embed = discord.Embed(
                title=f"⚠️ [Orchestrator] Báo Cáo Không Đủ Dữ Liệu: {NICHE_TOPIC}",
                description="Hệ thống tạm thời chưa thu thập đủ số liệu tin cậy.",
                color=COLOR_WARNING
            )
            if thread:
                await thread.send(embed=summary_embed)
        else:
            is_full = (success_count == 3)
            score_data = self.calculate_niche_score()

            synthesis_prompt_content = f"""
Hãy tổng hợp báo cáo chiến lược hoàn chỉnh dựa trên dữ liệu thật sau:
Chủ đề: {NICHE_TOPIC}
Hot Topics: {json.dumps(hot_topics, ensure_ascii=False)}
Top Videos: {json.dumps(top_videos[:5], ensure_ascii=False)}
CTR Formulas: {json.dumps(ctr_formulas, ensure_ascii=False)}
Điểm: {score_data['score']}/100 ({score_data['tier']})
"""
            synth_res = await llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": synthesis_prompt},
                    {"role": "user", "content": synthesis_prompt_content}
                ],
                temperature=0.2,
                max_tokens=3000
            )

            report_md_content = strip_think_tags(synth_res.get("content", ""))
            if not report_md_content:
                report_md_content = f"# BÁO CÁO CHIẾN LƯỢC NICHE {NICHE_TOPIC}\n- Điểm: {score_data['score']}/100"

            report_filepath.write_text(report_md_content, encoding="utf-8")

            # Giao diện Báo Cáo Tinh Gọn, Thoáng & Đẳng Cấp
            summary_embed = discord.Embed(
                title=f"🏆 BÁO CÁO CHIẾN LƯỢC: NICHE {NICHE_TOPIC.upper()}",
                description=f"📊 **Điểm Cơ Hội:** `{score_data['score']}/100` — **{score_data['tier']}**\n\n"
                            f"🔥 **3 ĐIỂM SÁNG TRỌNG TÂM:**\n"
                            f"• **Nhu cầu cao:** Khán giả đang quan tâm lớn về `{', '.join(hot_topics[:2]) if hot_topics else NICHE_TOPIC}`.\n"
                            f"• **Cơ hội bứt phá:** Kênh nhỏ dễ viral nếu khai thác góc nhìn giải thích trực quan & số liệu độc lạ.\n"
                            f"• **Tối ưu CTR:** Phối màu tương phản cao (Vàng Neon / Xanh Điện) + Text ngắn dưới 3 từ.\n\n"
                            f"💡 *Toàn bộ phân tích chuyên sâu đã được đính kèm trong file bên dưới!*",
                color=COLOR_ORCHESTRATOR
            )
            summary_embed.set_footer(text=f"AI 4 AI Strategy • File: {report_filename}")

            if thread:
                with open(report_filepath, "rb") as f:
                    discord_file = discord.File(f, filename=report_filename)
                    await thread.send(embed=summary_embed, file=discord_file)

        # -------------------------------------------------------------
        # 5. GỬI BÁO CÁO QUA DM (NẾU CÓ NGƯỜI NHẬN TARGET_RECIPIENTS)
        # -------------------------------------------------------------
        if target_recipients and summary_embed:
            for recipient in target_recipients:
                print("\n" + "=" * 70, flush=True)
                print(f"📬 [OUTGOING DM] GỬI BÁO CÁO CHO {recipient.name} (ID: {recipient.id})", flush=True)
                print("=" * 70, flush=True)
                try:
                    with open(report_filepath, "rb") as f:
                        dm_file = discord.File(f, filename=report_filename)
                        await recipient.send(
                            content=f"👋 **Báo cáo nghiên cứu chiến lược YouTube: `{active_niche}`** (Dành riêng cho <@{recipient.id}>)",
                            embed=summary_embed,
                            file=dm_file
                        )
                    print(f"[Orchestrator] [✅] Đã gửi DM báo cáo thành công tới {recipient.name} (ID: {recipient.id})", flush=True)
                except discord.Forbidden:
                    print(f"[Orchestrator] [⚠️] Không thể gửi DM cho {recipient.name} (ID: {recipient.id}) (Forbidden).", flush=True)
                except Exception as e:
                    print(f"[Orchestrator] [❌] Lỗi khi gửi DM cho {recipient.name}: {e}", flush=True)

        # -------------------------------------------------------------
        # 6. GIÁM SÁT QUOTA TỔNG KẾT
        # -------------------------------------------------------------
        final_stats = quota_tracker.get_session_stats()
        monitor_embed = discord.Embed(
            title="🛡️ [Quota Monitor] Báo Cáo Kiểm Toán Hạn Mức Sau Phiên Chạy",
            description=f"*Báo cáo đại ca số lượng tài nguyên API đã tiêu thụ trong lần chạy này:*\n\n"
                        f"• **YouTube Data API:** ~`{final_stats['yt_units']}` units (trong tổng 10,000 units/ngày)\n"
                        f"• **LLM API Requests:** `{final_stats['llm_requests']}` requests\n"
                        f"• **LLM Tokens:** `{final_stats['llm_tokens']:,}` tokens\n"
                        f"• **Rate Limit Hits (429):** `{final_stats['rate_limit_hits']}`",
            color=COLOR_MONITOR
        )
        await send_as_bot(monitor_bot, monitor_embed)

        return {
            "status": "success",
            "report_filepath": str(report_filepath),
            "report_filename": report_filename,
            "summary_embed": summary_embed
        }

orchestrator = Orchestrator()

`
