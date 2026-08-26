# 🚀 TỔNG HỢP TOÀN BỘ MÃ NGUỒN DỰ ÁN AI 4 AI (FULL SOURCE CODE EXPORT)

Tài liệu này cung cấp toàn bộ mã nguồn thực tế của hệ thống **AI 4 AI - Multi-Agent YouTube Content Engine** để phục vụ việc đánh giá, kiểm thử kỹ thuật và rà soát hệ thống.

---

## 🌳 Cây Thư Mục Tổng Quan Dự Án
`	ext
DISCORD BOT/
│
├── config.py                     # Quản lý cấu hình, biến môi trường và màu sắc giao diện
├── main.py                       # Điểm khởi chạy 5 bot Discord, slash commands, roundtable, và dashboard
├── requirements.txt              # Danh sách thư viện phụ thuộc Python
├── .env.example                  # File mẫu định nghĩa các biến môi trường
│
├── agents/                       # Nhóm 5 AI Agent chuyên trách
│   ├── prompts.py                # System Prompts và quy chuẩn tư duy 7 nguyên tắc
│   ├── news_agent.py             # Agent săn tin tức & xu hướng mới
│   ├── market_agent.py           # Agent quét số liệu YouTube & video breakout
│   ├── thumbnail_agent.py        # Agent bóc tách visual & thiết kế prompt ảnh CTR
│   └── orchestrator.py           # Agent Anh Cả điều phối toàn bộ luồng pipeline
│
└── services/                     # Tầng kết nối API và xử lý dữ liệu
    ├── gemini_service.py         # Kết nối Google Gemini 3.6 Flash
    ├── groq_service.py           # Kết nối Groq API (openai/gpt-oss-120b)
    ├── claude_service.py         # Kết nối Anthropic Claude API
    ├── llm_client.py             # Client tổng điều phối & fallback tự động giữa các LLM
    ├── youtube_service.py        # Tương tác YouTube Data API v3
    ├── search_service.py         # Tìm kiếm web đa nguồn DuckDuckGo / News
    ├── image_service.py          # Sinh Prompt 8K và render ảnh 4K Flux Ultra
    ├── script_generator.py       # Biên kịch kịch bản 4 bước thực chiến & prompt video
    ├── channel_auditor.py        # Bóc tách toàn diện kênh YouTube (SEO, Tags, Visual DNA)
    ├── quota_tracker.py          # Đếm quota 24/7 (Gemini, Groq, YouTube) và đo độ trễ
    ├── chat_logger.py            # Ghi log lịch sử trò chuyện vào Database SQLite
    └── dashboard_server.py       # Web Dashboard Control Hub Real-time
`

---

## 📑 Danh Mục Các File Mã Nguồn Chi Tiết

Mã nguồn đầy đủ 100% (không rút gọn, không lược bỏ) đã được chia theo từng module chuyên biệt để thuận tiện cho việc đọc và review:

| STT | File Tài Liệu Xuất Bản | Nội Dung Chi Tiết | File Mã Nguồn Bao Gồm |
|:---:|:---|:---|:---|
| **1** | [**SOURCE_CODE_1_CONFIG.md**](file:///c:/Users/LAMDZ/Desktop/DISCORD%20BOT/SOURCE_CODE_1_CONFIG.md) | Cấu hình & Môi trường | 
equirements.txt, .env.example, config.py |
| **2** | [**SOURCE_CODE_2_AGENTS.md**](file:///c:/Users/LAMDZ/Desktop/DISCORD%20BOT/SOURCE_CODE_2_AGENTS.md) | 5 AI Agent Chuyên Trách | gents/prompts.py, gents/news_agent.py, gents/market_agent.py, gents/thumbnail_agent.py, gents/orchestrator.py |
| **3** | [**SOURCE_CODE_3_SERVICES.md**](file:///c:/Users/LAMDZ/Desktop/DISCORD%20BOT/SOURCE_CODE_3_SERVICES.md) | Tầng Dịch Vụ & Kết Nối API | services/gemini_service.py, services/groq_service.py, services/claude_service.py, services/llm_client.py, services/youtube_service.py, services/search_service.py, services/image_service.py, services/script_generator.py, services/channel_auditor.py, services/quota_tracker.py, services/chat_logger.py, services/dashboard_server.py |
| **4** | [**SOURCE_CODE_4_MAIN.md**](file:///c:/Users/LAMDZ/Desktop/DISCORD%20BOT/SOURCE_CODE_4_MAIN.md) | Điểm Khởi Chạy Trung Tâm | main.py |

---

## 🛡️ Nguyên Tắc An Toàn Dữ Liệu
- Toàn bộ các khóa API Keys và Discord Bot Tokens nhạy cảm **KHÔNG BAO GIỜ** được đưa vào mã nguồn xuất bản.
- Cấu hình môi trường chỉ sử dụng định dạng mẫu từ [.env.example](file:///c:/Users/LAMDZ/Desktop/DISCORD%20BOT/.env.example).
