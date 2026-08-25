# 🤖 AI 4 AI — Multi-Agent YouTube Market Research Discord Bot System

Hệ thống Multi-Agent chạy qua **5 Discord Bot** chuyên dụng, hỗ trợ nghiên cứu thị trường YouTube với cấu hình **Chủ đề linh hoạt (Dynamic Niche)** (mặc định: **Khoa học vũ trụ**). Hệ thống tự động phát hiện xu hướng viral (30 ngày qua), phân tích đối thủ & video breakout (kênh nhỏ view cao), giải mã mẫu thumbnail CTR cao và tổng hợp thành báo cáo chiến lược có chấm điểm **Niche Scoring (0-100)**, xếp hạng **Tier (S/A/B/C/D)**, và hỗ trợ **Lịch chạy tự động gửi DM hàng ngày**.

---

## 📌 1. KIẾN TRÚC HỆ THỐNG (5 DISCORD BOTS)

```
[Lịch Tự Động Hàng Ngày / Lệnh /report Thủ Công]
                   │
       ┌───────────┴───────────┐
       ▼                       ▼
    [1. ORCHESTRATOR]     [5. GIÁM SÁT QUOTA]
    (Xanh dương - Blue)    (Xám - Slate)
    - Nhận lệnh / Lịch hẹn - /quota: xem usage
    - Tạo Discord Thread   - Cảnh báo khi <20%
    - Điều phối 3 agents   - Tóm tắt sau mỗi run
    - Gửi DM cho cộng sự
       │
       ├──► [2. NEWS / TREND AGENT] (Cam - Orange)
       │        │ ReAct Web Search theo NICHE_TOPIC (30 ngày qua)
       │        ▼ Xuất `hot_topics`
       ├──► [3. MARKET / COMPETITOR AGENT] (Xanh lá - Green)
       │        │ ReAct YouTube Data API v3 (Lọc Breakout Ratio)
       │        ▼ Xuất `top_videos`
       └──► [4. THUMBNAIL AGENT] (Tím - Purple)
                │ ReAct Vision Analysis theo chủ đề Niche
                ▼ Xuất 3 CTR Design Formulas
```

---

## 🛠️ 2. HƯỚNG DẪN CẤU HÌNH VÀ CÀI ĐẶT

### Cấu hình biến môi trường trong `.env`

```ini
# ==============================================================================
# DISCORD BOT TOKENS
# ==============================================================================
DISCORD_ORCHESTRATOR_TOKEN=MTIz...
DISCORD_NEWS_TOKEN=MTIz...
DISCORD_MARKET_TOKEN=MTIz...
DISCORD_THUMBNAIL_TOKEN=MTIz...
DISCORD_MONITOR_TOKEN=MTIz...

# Server & Channel
DISCORD_GUILD_ID=123456789012345678
DISCORD_CHANNEL_ID=123456789012345678
ALLOWED_DISCORD_USER_IDS=123456789012345678

# Người nhận báo cáo tự động hàng ngày qua DM (@Anh Bình trùm màn)
RECIPIENT_DISCORD_USER_ID=123456789012345678

# ==============================================================================
# CHỦ ĐỀ NGHIÊN CỨU (NICHE CONFIGURATION)
# ==============================================================================
NICHE_TOPIC="Khoa học vũ trụ"
NICHE_KEYWORDS_HINT="thiên văn học, khám phá không gian, NASA, SpaceX, vũ trụ học, hành tinh, lỗ đen, tên lửa"

# ==============================================================================
# LỊCH TỰ ĐỘNG CHẠY BÁO CÁO HÀNG NGÀY (DAILY AUTO-RUN)
# ==============================================================================
DAILY_RUN_ENABLED=true
DAILY_RUN_TIME=08:00
DAILY_RUN_TIMEZONE=Asia/Ho_Chi_Minh

# ==============================================================================
# API KEYS
# ==============================================================================
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_...
YOUTUBE_API_KEY=AIzaSy...
```

---

## 🚀 3. DANH SÁCH LỆNH SLASH COMMANDS

| Bot | Lệnh | Mô tả |
|---|---|---|
| **Orchestrator** | `/help` | Xem danh sách lệnh & trạng thái hệ thống |
| **Orchestrator** | `/report` | Khởi chạy toàn bộ quy trình phân tích Niche trong thread |
| **Orchestrator** | `/score_niche [topic]` | Chấm điểm cơ hội cho 1 niche (0-100 & Tier) |
| **Orchestrator** | `/start` | Chào hỏi, kiểm tra trạng thái hoạt động |
| **News Agent** | `/trend [topic]` | Quét tin tức 30 ngày qua cho từ khóa/niche |
| **News Agent** | `/hot_topics` | Trích xuất các chủ đề đang viral trong niche |
| **Market Agent** | `/market_search [query]` | Săn video breakout (kênh nhỏ view cao) |
| **Market Agent** | `/video_stats [url]` | Bóc tách chỉ số chi tiết của 1 video |
| **Thumbnail Agent**| `/thumbnail_analyze [url]` | Phân tích thị giác màu sắc, bố cục, text |
| **Thumbnail Agent**| `/thumbnail_ideas [topic]` | Gợi ý 3 concept thiết kế thumbnail CTR cao |
| **Quota Monitor** | `/quota` | Xem hạn mức YouTube & LLM còn lại |
| **Quota Monitor** | `/system_status` | Kiểm tra sức khỏe 5 bot, API keys & Niche |
| **Quota Monitor** | `/ping` | Đo độ trễ mạng |
