# 📚 MÃ NGUỒN PHẦN 1: CẤU HÌNH & DEPENDENCIES

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

## 📄 requirements.txt

**Chức năng chính**: Danh sách các thư viện Python cần thiết cho hệ thống (discord.py, aiohttp, google-genai, groq, anthropic, google-api-python-client...).

**Mã nguồn đầy đủ**:
`	ext
discord.py>=2.3.2
python-dotenv>=1.0.0
groq>=0.9.0
anthropic>=0.25.0
google-api-python-client>=2.100.0
duckduckgo_search>=6.0.0
pillow>=10.0.0
aiohttp>=3.9.0
pydantic>=2.0.0
tzdata>=2024.1
google-genai>=0.1.0

`

---

## 📄 .env.example

**Chức năng chính**: File mẫu định nghĩa các biến môi trường cấu hình (API Keys, Discord Bot Tokens, Guild ID, User IDs). Tuyệt đối không chứa key thật.

**Mã nguồn đầy đủ**:
`ini
# ==============================================================================
# DISCORD BOT TOKENS
# ==============================================================================
DISCORD_ORCHESTRATOR_TOKEN=
DISCORD_NEWS_TOKEN=
DISCORD_MARKET_TOKEN=
DISCORD_THUMBNAIL_TOKEN=
DISCORD_MONITOR_TOKEN=

# Guild ID
DISCORD_GUILD_ID=1031727865567395840
ALLOWED_DISCORD_USER_IDS=
RECIPIENT_DISCORD_USER_ID=1031727351643516989

# Niche Topic
NICHE_TOPIC="Khoa học đời sống, Vật lý & Hiện tượng tự nhiên"
NICHE_KEYWORDS_HINT="khoa học đời sống, vật lý thường thức, hiện tượng tự nhiên kỳ thú, bí ẩn cơ thể người, thí nghiệm khoa học, giải thích hiện tượng, everyday science, physics phenomena, biology curiosities, what if science"

# Auto-Run
DAILY_RUN_ENABLED=true
DAILY_RUN_TIME=19:30
DAILY_RUN_TIMEZONE=Asia/Ho_Chi_Minh

# LLM Provider
LLM_PROVIDER=groq
GROQ_API_KEY=

# Optional: Gemini / Imagen Key for Flow
GEMINI_API_KEY=

# YouTube API Key
YOUTUBE_API_KEY=

`

---

## 📄 config.py

**Chức năng chính**: Đọc và nạp các biến môi trường, thiết lập các hằng số hệ thống, cấu hình chủ đề Niche, màu sắc Embeds và đường dẫn thư mục.

**Các biến/hằng số quan trọng**:
- DISCORD_BOT_TOKEN, DISCORD_NEWS_BOT_TOKEN, DISCORD_MARKET_BOT_TOKEN, DISCORD_THUMBNAIL_BOT_TOKEN, DISCORD_MONITOR_BOT_TOKEN: Token của 5 bot Discord
- GROQ_API_KEY, GEMINI_API_KEY, ANTHROPIC_API_KEY, YOUTUBE_API_KEY: Khóa API các dịch vụ AI và YouTube
- NICHE_TOPIC, NICHE_KEYWORDS_HINT: Chủ đề Niche định hướng cho toàn bộ bot
- COLOR_ORCHESTRATOR, COLOR_NEWS, COLOR_MARKET, COLOR_THUMBNAIL, COLOR_MONITOR: Màu sắc đặc trưng của từng bot

**Mã nguồn đầy đủ**:
`python
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Tự động nạp file .env từ thư mục gốc
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Thư mục lưu báo cáo
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Discord Tokens
DISCORD_ORCHESTRATOR_TOKEN = os.getenv("DISCORD_ORCHESTRATOR_TOKEN", "").strip()
DISCORD_NEWS_TOKEN = os.getenv("DISCORD_NEWS_TOKEN", "").strip()
DISCORD_MARKET_TOKEN = os.getenv("DISCORD_MARKET_TOKEN", "").strip()
DISCORD_THUMBNAIL_TOKEN = os.getenv("DISCORD_THUMBNAIL_TOKEN", "").strip()
DISCORD_MONITOR_TOKEN = os.getenv("DISCORD_MONITOR_TOKEN", "").strip()

# Discord Guild & Channel
DISCORD_GUILD_ID_RAW = os.getenv("DISCORD_GUILD_ID", "").strip()
DISCORD_GUILD_ID = int(DISCORD_GUILD_ID_RAW) if DISCORD_GUILD_ID_RAW.isdigit() else None

DISCORD_CHANNEL_ID_RAW = os.getenv("DISCORD_CHANNEL_ID", "").strip()
DISCORD_CHANNEL_ID = int(DISCORD_CHANNEL_ID_RAW) if DISCORD_CHANNEL_ID_RAW.isdigit() else None

# Whitelist User IDs
ALLOWED_DISCORD_USER_IDS_RAW = os.getenv("ALLOWED_DISCORD_USER_IDS", "").strip()
ALLOWED_DISCORD_USER_IDS = [
    int(uid.strip())
    for uid in ALLOWED_DISCORD_USER_IDS_RAW.split(",")
    if uid.strip().isdigit()
]

# LLM Provider Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower().strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5").strip()

# Groq Specific Models
GROQ_TOOL_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()
GROQ_VISION_MODEL = "qwen/qwen3.6-27b"

# Gemini / Google AI Studio API Key (Flow vẽ ảnh)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

# YouTube Data API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "").strip()

# Embed Colors (Hex Int)
COLOR_ORCHESTRATOR = 0x2563EB  # Blue
COLOR_NEWS = 0xF97316          # Orange
COLOR_MARKET = 0x10B981        # Green
COLOR_THUMBNAIL = 0x8B5CF6     # Purple
COLOR_MONITOR = 0x64748B       # Slate / Gray
COLOR_ERROR = 0xEF4444         # Red
COLOR_WARNING = 0xF59E0B       # Amber

# Execution limits
MAX_REACT_TURNS = 6

# Niche Topic & Keywords Hint
NICHE_TOPIC = os.getenv("NICHE_TOPIC", "Khoa học đời sống, Vật lý & Hiện tượng tự nhiên").strip()
NICHE_KEYWORDS_HINT = os.getenv(
    "NICHE_KEYWORDS_HINT",
    "khoa học đời sống, vật lý thường thức, hiện tượng tự nhiên kỳ thú, bí ẩn cơ thể người, thí nghiệm khoa học, giải thích hiện tượng, everyday science, physics phenomena, biology curiosities, what if science"
).strip()

# Scheduled Daily Auto-Run
DAILY_RUN_ENABLED = os.getenv("DAILY_RUN_ENABLED", "true").lower().strip() in ["true", "1", "yes"]
DAILY_RUN_TIME = os.getenv("DAILY_RUN_TIME", "08:00").strip()
DAILY_RUN_TIMEZONE = os.getenv("DAILY_RUN_TIMEZONE", "Asia/Ho_Chi_Minh").strip()

# Direct Message Recipient
RECIPIENT_DISCORD_USER_ID_RAW = os.getenv("RECIPIENT_DISCORD_USER_ID", "").strip()
RECIPIENT_DISCORD_USER_ID = int(RECIPIENT_DISCORD_USER_ID_RAW) if RECIPIENT_DISCORD_USER_ID_RAW.isdigit() else None


`
