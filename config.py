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

