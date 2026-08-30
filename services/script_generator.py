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
CHỦ ĐỀ CHÍNH XÁC: {topic}

QUY TẮC BẮT BUỘC VỀ BỐ CỤC:
1. Ở ĐẦU BẢN KỊCH BẢN, BẮT BUỘC PHẢI CÓ MỘT KHỐI "⚡ QUICK COPY — CÁC PROMPT DÙNG NGAY" TRÌNH BÀY THUẦN PROMPT ANH (1 DÒNG CHO ẢNH, 1 DÒNG CHO VIDEO) ĐỂ NGƯỜI DÙNG BẤM COPY 1 CHẠM LÀ DÙNG ĐƯỢC NGAY TRÊN ĐIỆN THOẠI/PC.
2. CẤU TRÚC KỂ CHUYỆN: Cấu trúc 4 bước (Hiện tượng -> Thử nghiệm -> Giải thích vi mô -> Bài học & CTA) là KHUNG THAM KHẢO LINH HOẠT. Bạn ĐƯỢC PHÉP ĐIỀU CHỈNH số lượng phân cảnh (từ 3 đến 5 cảnh) hoặc mạch diễn giải nếu chủ đề cụ thể (như so sánh 2 hiện tượng, giải mã bí ẩn, thí nghiệm giả định...) phù hợp với cách kể chuyện khác lôi cuốn và giữ chân người xem hiệu quả hơn.
3. BẮT BUỘC: Hook đầu video 3s cực mạnh + Có Prompt Tạo Ảnh (Midjourney/Flux) & Prompt Tạo Video (Runway/Kling) chuẩn điện ảnh cho từng cảnh + Lời thoại Voiceover VN cuốn hút + CTA tương tác cuối video + Nguồn bài báo khoa học uy tín.

BẢN MẪU ĐỊNH DẠNG MARKDOWN CHUẨN:

# ⚡ QUICK COPY — CÁC PROMPT DÙNG NGAY
```text
🎨 Ảnh Cảnh 1: [Prompt tiếng Anh thuần 1 dòng cho Midjourney/Flux]
🎬 Video Cảnh 1: [Prompt tiếng Anh thuần 1 dòng cho Runway/Kling]

🎨 Ảnh Cảnh 2: [Prompt tiếng Anh thuần 1 dòng cho Midjourney/Flux]
🎬 Video Cảnh 2: [Prompt tiếng Anh thuần 1 dòng cho Runway/Kling]

🎨 Ảnh Cảnh 3: [Prompt tiếng Anh thuần 1 dòng cho Midjourney/Flux]
🎬 Video Cảnh 3: [Prompt tiếng Anh thuần 1 dòng cho Runway/Kling]

🎨 Ảnh Cảnh 4: [Prompt tiếng Anh thuần 1 dòng cho Midjourney/Flux]
🎬 Video Cảnh 4: [Prompt tiếng Anh thuần 1 dòng cho Runway/Kling]
```

---

# 🎬 [TIÊU ĐỀ VIDEO ĐỀ XUẤT - BẮT TREND & TỶ LỆ CLICK CAO]
- **Định dạng:** {format_type}
- **Tone Giọng (Voiceover):** Bí ẩn, kịch tính, lôi cuốn, trầm ấm, chuẩn ElevenLabs.
- **Nhạc nền (BGM/SFX):** Cinematic space ambient, dramatic tension risers, deep space thuds.

---

## 📊 BÓC TÁCH CÔNG THỨC VIRAL TỪ THỊ TRƯỜNG
- Điểm mấu chốt khiến chủ đề này đang hot trên YouTube.
- Góc tiếp cận độc lạ áp dụng cho video này.

---

## 📝 KỊCH BẢN CHI TIẾT TỪNG PHÂN CẢNH

### 📍 PHÂN CẢNH 1: [0:00 - 0:10] | 🌟 HOOK MỞ ĐẦU (Gây Tò Mò Cực Độ)
- 🗣️ **Lời thoại (Voiceover VN):** (Câu nói giật tò mò, chỉ ra hiện tượng quen thuộc nhưng khó tin)
- 🎨 **Prompt Tạo Ảnh (Midjourney v6 / Flux):** `(Prompt tiếng Anh chi tiết, 8k hyperrealistic scientific illustration, dramatic cinematic lighting)`
- 🎬 **Prompt Tạo Video (Runway Gen-3 / Pika / Kling AI):** `(Prompt chuyển động camera, slow motion, macro zoom cận cảnh hiện tượng)`
- 🔊 **Âm thanh / SFX:** (Mô tả hiệu ứng âm thanh)

### 📍 PHÂN CẢNH 2: [0:10 - 0:25] | 🧪 THỬ NGHIỆM / DIỄN TIẾN TRỰC QUAN
- 🗣️ **Lời thoại (Voiceover VN):** (Tái hiện thí nghiệm / diễn biến hiện tượng trực quan)
- 🎨 **Prompt Tạo Ảnh (Midjourney / Flux):** ...
- 🎬 **Prompt Tạo Video (Runway / Pika):** ...
- 🔊 **Âm thanh / SFX:** ...

### 📍 PHÂN CẢNH 3: [0:25 - 0:50] | ⚡ GIẢI MÃ BẢN CHẤT KHOA HỌC SÂU
- 🗣️ **Lời thoại (Voiceover VN):** (Giải thích cơ chế vật lý / vi mô bằng hình tượng dễ hiểu)
- 🎨 **Prompt Tạo Ảnh (Midjourney / Flux):** ...
- 🎬 **Prompt Tạo Video (Runway / Pika):** ...
- 🔊 **Âm thanh / SFX:** ...

### 📍 PHÂN CẢNH 4: [0:50 - 1:00] | 💡 BÀI HỌC THỰC TẾ & KÊU GỌI TƯƠNG TÁC (CTA)
- 🗣️ **Lời thoại (Voiceover VN):** (Ứng dụng đời sống + Đặt câu hỏi kích thích bình luận)
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

        user_content = f"{market_context_str}\n\nHãy tạo bản kịch bản hoàn chỉnh kèm khối Quick Copy ở đầu và bộ prompt AI chi tiết cho chủ đề: '{topic}'."
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

        script_markdown = strip_think_tags(llm_res.get("content", "# Kịch bản video khoa học"))
        
        # 3. Trích xuất khối Quick Copy riêng để gửi Discord
        quick_copy_text = self.extract_quick_copy(script_markdown)

        # 4. Lưu file Markdown
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
            "quick_copy": quick_copy_text,
            "hot_videos_analyzed": len(hot_videos),
            "breakout_videos_analyzed": len(breakout_videos)
        }

    @staticmethod
    def extract_quick_copy(script_text: str) -> str:
        """
        Trích xuất phần QUICK COPY từ đầu kịch bản để gửi riêng dạng code block 1 chạm trên Discord.
        """
        match = re.search(r"#+\s*⚡\s*QUICK COPY[^\n]*\n+```(?:text)?\n([\s\S]*?)```", script_text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # Fallback: Quét các dòng prompt ảnh và video nếu không tìm thấy khối
        prompts = []
        for line in script_text.splitlines():
            line_str = line.strip()
            if "Prompt Tạo Ảnh" in line_str or "Prompt Tạo Video" in line_str or "🎨" in line_str or "🎬" in line_str:
                prompts.append(line_str)
        if prompts:
            return "\n".join(prompts[:10])
        return "Xem toàn bộ prompt chi tiết trong file kịch bản đính kèm bên dưới."

script_generator = ScriptGenerator()
