import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from config import BASE_DIR, NICHE_TOPIC, COLOR_MARKET
from services.youtube_service import YouTubeService
from services.llm_client import llm_client, strip_think_tags

CHANNELS_DIR = BASE_DIR / "reports" / "channels"
CHANNELS_DIR.mkdir(parents=True, exist_ok=True)

class ChannelAuditor:
    def __init__(self):
        self.yt = YouTubeService()

    async def audit_channel(self, channel_input: str) -> Dict[str, Any]:
        """
        Bóc tách toàn diện kênh YouTube:
        - SEO & Thẻ Tags (Tags list, Title formula)
        - Thumbnail DNA & Bố cục thị giác
        - 3 Bộ Prompt AI (Midjourney v6 / Flux) chuẩn xác để tạo ảnh giống phong cách kênh đó 100%.
        """
        # 1. Lấy dữ liệu thô từ YouTube API
        raw_data = await self.yt.get_channel_full_audit(channel_input)
        if "error" in raw_data or raw_data.get("status") != "success":
            return {"status": "error", "message": raw_data.get("error", "Không thể lấy dữ liệu kênh.")}

        chan_info = raw_data["channel_info"]
        top_vids = raw_data["top_videos"]
        pop_tags = raw_data["popular_tags"]

        # Chuẩn bị dữ liệu đưa vào LLM
        vids_summary = "\n".join([
            f"- Video: \"{v['title']}\" | Views: {v['view_count']:,} | Likes: {v['like_count']:,}\n"
            f"  Tags: {', '.join(v['tags'][:8]) if v['tags'] else 'Không có'}\n"
            f"  Thumbnail: {v['thumbnail_url']}"
            for v in top_vids[:5]
        ])

        system_prompt = f"""
Bạn là Chuyên Gia SEO YouTube & Giám Đốc Nghệ Thuật (Art Director) hàng đầu trong niche {NICHE_TOPIC}.
Nhiệm vụ của bạn là phân tích toàn diện kênh YouTube đối thủ và xuất ra:
1. Phân tích SEO & Thẻ Tag (Công thức đặt tiêu đề, các thẻ tag hiệu quả nhất).
2. Phân tích "DNA Thiết Kế Thumbnail" (Màu sắc, phong cách đồ họa 3D/2D, ánh sáng, góc nhìn).
3. Viết 3 BỘ PROMPT TẠO ẢNH AI (Midjourney v6 / Flux) CHUẨN XÁC để người dùng có thể tạo ra ảnh Thumbnail đẹp và đúng phong cách của kênh này 100%.

CẤU TRÚC BÁO CÁO AUDIT (Bắt buộc dùng Markdown):
# 📊 [BÁO CÁO AUDIT TOÀN DIỆN KÊNH: {chan_info['title'].upper()}]

## 1. 📈 TỔNG QUAN CHỈ SỐ KÊNH
- **Subscribers:** {chan_info['subscriber_count']:,} | **Tổng Lượt Xem:** {chan_info['view_count']:,} | **Tổng Video:** {chan_info['video_count']}
- **Đánh giá sức mạnh:** (Nhận xét ngắn gọn về độ phủ và tệp khán giả)

---

## 2. 🔍 CHIẾN LƯỢC SEO & THẺ TAGS (KEYWORDS)
- **Công thức Tiêu Đề (Title Pattern):** (Bóc tách cấu trúc giật tít của kênh)
- **Top Thẻ Tag (Tags) Trọng Tâm:** (Liệt kê các tags quan trọng để rank top tìm kiếm)
- **Kỹ thuật SEO Mô Tả & Giữ Chân:** (Cách đặt link, CTA, từ khóa trong mô tả)

---

## 3. 🎨 DNA THIẾT KẾ THUMBNAIL CỦA KÊNH
- **Bảng Màu Chủ Đạo (Color Palette):** (Ví dụ: Neon Yellow + Deep Space Navy + Electric Cyan)
- **Phong Cách Nghệ Thuật (Art Style):** (Ví dụ: 3D CGI Hyperrealistic / 2D Isometric Vector / Cinema Astrophotography)
- **Bố Cục & Điểm Nhấn Thị Giác:** (Bố cục 1/3, tương phản cao, khuôn mặt cảm xúc, text ngắn gọn 3 chữ)

---

## 4. 🖼️ BỘ 3 PROMPT AI TẠO THUMBNAIL PHONG CÁCH KÊNH NÀY (COPY DÙNG NGAY)

### 📍 PROMPT 1: Concept Khám Phá Vũ Trụ Huyền Ảo (Giống 100% Phong Cách Kênh)
- **Mô tả Concept:** (Ý tưởng hình ảnh)
- 🎨 **Midjourney v6 Prompt:** `(Prompt tiếng Anh chi tiết, phong cách kênh, ánh sáng cinematic, 8k, aspect ratio --ar 16:9 --v 6.0 --style raw)`
- ⚡ **Flux / DALL-E 3 Prompt:** `(Prompt chi tiết cho Flux)`

### 📍 PROMPT 2: Concept Đối Đầu / So Sánh Kịch Tính (Split Screen)
- **Mô tả Concept:** ...
- 🎨 **Midjourney v6 Prompt:** `... --ar 16:9 --v 6.0`
- ⚡ **Flux / DALL-E 3 Prompt:** `...`

### 📍 PROMPT 3: Concept Bí Ẩn / Cận Cảnh Gây Tò Mò (Curiosity Hook)
- **Mô tả Concept:** ...
- 🎨 **Midjourney v6 Prompt:** `... --ar 16:9 --v 6.0`
- ⚡ **Flux / DALL-E 3 Prompt:** `...`

---

## 💡 ĐỀ XUẤT ĐỂ KÊNH CỦA ĐẠI CA VƯỢT MẶT ĐỐI THỦ NÀY:
1. ...
2. ...
3. ...
"""

        user_content = f"""
THÔNG TIN KÊNH:
- Tên kênh: {chan_info['title']} ({chan_info['custom_url']})
- Bio / Mô tả: {chan_info['description'][:400]}
- Tags Kênh: {chan_info.get('channel_keywords', '')}
- Top Thẻ Tags Thường Dùng: {', '.join(pop_tags[:15])}

DANH SÁCH TOP VIDEO CỦA KÊNH:
{vids_summary}

Hãy tiến hành Audit toàn diện và xuất báo cáo kèm bộ Prompt AI tạo thumbnail phong cách kênh này.
"""

        llm_res = await llm_client.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=0.6,
            max_tokens=2500
        )

        audit_markdown = strip_think_tags(llm_res.get("content", "# Báo cáo Audit Kênh"))

        # Lưu file
        clean_title = re.sub(r'[^a-zA-Z0-9_-]', '_', chan_info['title'])[:30]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"audit_{clean_title}_{timestamp}.md"
        filepath = CHANNELS_DIR / filename

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(audit_markdown)

        return {
            "status": "success",
            "channel_title": chan_info["title"],
            "channel_url": f"https://www.youtube.com/{chan_info.get('custom_url', chan_info['channel_id'])}",
            "subscribers": chan_info["subscriber_count"],
            "total_views": chan_info["view_count"],
            "popular_tags": pop_tags[:10],
            "top_video_title": top_vids[0]["title"] if top_vids else "",
            "top_thumbnail_url": top_vids[0]["thumbnail_url"] if top_vids else chan_info["avatar_url"],
            "filename": filename,
            "filepath": str(filepath),
            "audit_markdown": audit_markdown
        }

channel_auditor = ChannelAuditor()
