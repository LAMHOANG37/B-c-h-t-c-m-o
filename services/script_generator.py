import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from config import BASE_DIR, NICHE_TOPIC, COLOR_MARKET
from services.youtube_service import YouTubeService
from services.llm_client import llm_client, strip_think_tags
from services.chat_logger import chat_logger

SCRIPTS_DIR = BASE_DIR / "reports" / "scripts"
SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

class ScriptGenerator:
    def __init__(self):
        self.yt = YouTubeService()

    async def generate_script_from_market(
        self,
        topic: str,
        format_type: str = "Shorts 60s (Dọc 9:16)",
        custom_instructions: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Quét các video đang lên và đang hot trên YouTube theo topic,
        sau đó viết kịch bản chi tiết kèm bộ prompt AI tạo video (Midjourney/Runway/Flux).
        """
        # 1. Quét YouTube: Nhóm 1 (Hot/Triệu view) & Nhóm 2 (Đang lên/Breakout)
        search_query = f"{topic} {NICHE_TOPIC}"
        hot_videos = []
        breakout_videos = []

        if self.yt.is_configured():
            try:
                # Quét video hot nhất theo lượt xem
                hot_raw = await self.yt.search_videos(query=search_query, order="viewCount", days_back=60, max_results=5)
                hot_enriched = await self.yt.get_video_stats_and_breakout(hot_raw)
                hot_videos = [v for v in hot_enriched if v.get("view_count", 0) > 10000][:3]

                # Quét video mới nhất có tín hiệu bứt phá
                recent_raw = await self.yt.search_videos(query=search_query, order="relevance", days_back=30, max_results=8)
                recent_enriched = await self.yt.get_video_stats_and_breakout(recent_raw)
                breakout_videos = [v for v in recent_enriched if v.get("is_breakout") or v.get("view_sub_ratio", 0) >= 1.5][:3]
            except Exception as e:
                print(f"[ScriptGenerator] YouTube scan error: {e}", flush=True)

        market_context_str = ""
        if hot_videos or breakout_videos:
            market_context_str = "DỮ LIỆU CÁC KÊNH THÀNH CÔNG TRÊN THỊ TRƯỜNG:\n"
            if hot_videos:
                market_context_str += "🔥 Top Kênh Đang Hot (Triệu View):\n"
                for v in hot_videos:
                    market_context_str += f"- Tiêu đề: \"{v.get('title')}\" | Views: {v.get('view_count', 0):,} | Kênh: {v.get('channel_title')}\n"
            if breakout_videos:
                market_context_str += "🚀 Top Kênh Đang Lên (Kênh Nhỏ View Cao):\n"
                for v in breakout_videos:
                    market_context_str += f"- Tiêu đề: \"{v.get('title')}\" | Views: {v.get('view_count', 0):,} (Gấp {v.get('view_sub_ratio', 1.0)}x Subs) | Lý do: {v.get('breakout_reason', 'Góc tiếp cận mới')}\n"
        else:
            market_context_str = f"Chủ đề trọng tâm: {topic} trong Niche {NICHE_TOPIC}. Áp dụng công thức Hook 3s tò mò và storytelling giữ chân cao."

        # 2. Tạo Kịch Bản & Bộ Prompt AI qua LLM
        system_prompt = f"""
Bạn là Chuyên Gia Biên Kịch & Đạo Diễn AI Video hàng đầu thế giới trong niche {NICHE_TOPIC}.
Nhiệm vụ của bạn là dựa vào xu hướng các kênh đang hot và kênh đang lên để viết một BẢN KỊCH BẢN CHI TIẾT KÈM PROMPT AI TỪNG PHÂN CẢNH để người dùng có thể làm theo và tạo video ngay lập tức.

ĐỊNH DẠNG VIDEO YÊU CẦU: {format_type}
CHỦ ĐỀ: {topic}

CẤU TRÚC KỊCH BẢN BẮT BUỘC (Trình bày bằng Markdown chuyên nghiệp):
# 🎬 [TIÊU ĐỀ VIDEO ĐỀ XUẤT - BẮT TREND & TỶ LỆ CLICK CAO]
- **Định dạng:** {format_type}
- **Tone Giọng (Voiceover):** Bí ẩn, kịch tính, lôi cuốn, trầm ấm, chuẩn ElevenLabs.
- **Nhạc nền (BGM/SFX):** Cinematic space ambient, dramatic tension risers, deep space thuds.

---

## 📊 BÓC TÁCH CÔNG THỨC VIRAL TỪ THỊ TRƯỜNG
- Điểm mấu chốt khiến chủ đề này đang hot.
- Góc tiếp cận độc lạ áp dụng cho video này.

---

## 📝 KỊCH BẢN CHI TIẾT THEO CÔNG THỨC 4 BƯỚC THỰC CHIẾN

### 📍 PHÂN CẢNH 1: [0:00 - 0:10] | 🌟 HIỆN TƯỢNG KỲ LẠ QUANH TA (Hook Gây Tò Mò)
- 🗣️ **Lời thoại (Voiceover VN):** (Mô tả một hiện tượng đời sống quen thuộc nhưng kỳ lạ, kích thích sự tò mò ngay giây đầu)
- 🎨 **Prompt Tạo Ảnh (Midjourney v6 / Flux):** `(Prompt tiếng Anh chi tiết, phong cách 8k hyperrealistic scientific illustration, dramatic cinematic lighting --ar 16:9 hoặc 9:16)`
- 🎬 **Prompt Tạo Video (Runway Gen-3 / Pika / Kling AI):** `(Prompt chuyển động camera, slow motion, macro zoom cận cảnh hiện tượng)`
- 🔊 **Âm thanh / SFX:** (Mô tả hiệu ứng âm thanh kích thích thính giác)

### 📍 PHÂN CẢNH 2: [0:10 - 0:25] | 🧪 THỬ NGHIỆM THỰC TẾ (The Experiment / Test)
- 🗣️ **Lời thoại (Voiceover VN):** (Thực hiện một thử nghiệm / thí nghiệm trực quan dễ hình dung để tái hiện hoặc kiểm chứng hiện tượng)
- 🎨 **Prompt Tạo Ảnh (Midjourney / Flux):** `(Prompt hình ảnh thí nghiệm, mặt cắt 3D hoặc tương phản trước/sau)`
- 🎬 **Prompt Tạo Video (Runway / Pika):** ...
- 🔊 **Âm thanh / SFX:** ...

### 📍 PHÂN CẢNH 3: [0:25 - 0:50] | ⚡ GIẢI THÍCH KHOA HỌC SÂU (The Science Behind It)
- 🗣️ **Lời thoại (Voiceover VN):** (Giải thích bản chất vật lý, hóa học, sinh học bằng ngôn ngữ bình dân, dễ hiểu, dùng hình tượng so sánh)
- 🎨 **Prompt Tạo Ảnh (Midjourney / Flux):** `(Prompt minh họa cơ chế vi mô, cấu trúc tế bào / phân tử / tia điện / áp suất)`
- 🎬 **Prompt Tạo Video (Runway / Pika):** ...
- 🔊 **Âm thanh / SFX:** ...

### 📍 PHÂN CẢNH 4: [0:50 - 1:00] | 💡 BÀI HỌC & ỨNG DỤNG ĐỜI SỐNG + KÊU GỌI (CTA)
- 🗣️ **Lời thoại (Voiceover VN):** (Rút ra bài học thực tế trong cuộc sống hàng ngày hoặc ứng dụng khoa học hữu ích + câu hỏi tương tác)
- 🎨 **Prompt Tạo Ảnh (Midjourney / Flux):** ...
- 🎬 **Prompt Tạo Video (Runway / Pika):** ...
- 🔊 **Âm thanh / SFX:** ...

---

## 📚 TÀI LIỆU & NGUỒN XÁC THỰC KHOA HỌC (DÙNG ĐÍNH KÈM DESCRIPTION YOUTUBE):
- 🔗 **Nguồn 1:** [Tên bài báo / Nghiên cứu / Thí nghiệm uy tín] — `[Link URL kiểm chứng thật: Nature / Science / MIT / Khan Academy / NASA / Wikipedia]`
- 🔗 **Nguồn 2:** [Tài liệu học thuật hoặc Kênh khoa học thực chứng] — `[Link URL kiểm chứng]`

---

## 💡 3 LƯU Ý KHI SẢN XUẤT VIDEO NÀY:
1. ...
2. ...
3. ...
"""

        user_content = f"{market_context_str}\n\nHãy tạo bản kịch bản hoàn chỉnh kèm bộ prompt AI chi tiết cho chủ đề: '{topic}'."
        if custom_instructions:
            user_content += f"\nYêu cầu thêm: {custom_instructions}"

        llm_res = await llm_client.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=0.7,
            max_tokens=4096
        )

        script_markdown = strip_think_tags(llm_res.get("content", "# Kịch bản video vũ trụ"))
        
        # 3. Lưu file Markdown
        clean_topic_slug = re.sub(r'[^a-zA-Z0-9_-]', '_', topic)[:30]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"script_{clean_topic_slug}_{timestamp}.md"
        filepath = SCRIPTS_DIR / filename

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(script_markdown)

        return {
            "status": "success",
            "topic": topic,
            "format": format_type,
            "filename": filename,
            "filepath": str(filepath),
            "script_content": script_markdown,
            "hot_videos_analyzed": len(hot_videos),
            "breakout_videos_analyzed": len(breakout_videos)
        }

script_generator = ScriptGenerator()
