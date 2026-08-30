import asyncio
import sys
from datetime import datetime, timezone, timedelta
from typing import Optional

# Đảm bảo Windows console hỗ trợ UTF-8 output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import discord
from discord import app_commands
from discord.ext import commands, tasks

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

from config import (
    BASE_DIR,
    DISCORD_ORCHESTRATOR_TOKEN,
    DISCORD_NEWS_TOKEN,
    DISCORD_MARKET_TOKEN,
    DISCORD_THUMBNAIL_TOKEN,
    DISCORD_MONITOR_TOKEN,
    DISCORD_GUILD_ID,
    DISCORD_CHANNEL_ID,
    ALLOWED_DISCORD_USER_IDS,
    RECIPIENT_DISCORD_USER_ID,
    NICHE_TOPIC,
    NICHE_KEYWORDS_HINT,
    DAILY_RUN_ENABLED,
    DAILY_RUN_TIME,
    DAILY_RUN_TIMEZONE,
    LLM_PROVIDER,
    COLOR_ORCHESTRATOR,
    COLOR_NEWS,
    COLOR_MARKET,
    COLOR_THUMBNAIL,
    COLOR_MONITOR,
    COLOR_ERROR,
    COLOR_WARNING
)
from services.llm_client import llm_client, strip_think_tags
from services.youtube_service import youtube_service
from services.quota_tracker import quota_tracker
from services.chat_logger import chat_logger
from services.dashboard_server import start_dashboard_server
from services.script_generator import script_generator
from services.channel_auditor import channel_auditor
from agents.orchestrator import orchestrator

# Khóa đồng bộ pipeline ngăn chạy chồng chéo
pipeline_lock = asyncio.Lock()

# Lưu ngày cuối cùng chạy lịch tự động (để không chạy trùng 2 lần trong 1 ngày)
last_scheduled_date: Optional[str] = None

# Trạng thái kiểm tra hệ thống khởi động
SYSTEM_HEALTH = {
    "llm_ok": False,
    "llm_msg": "",
    "youtube_ok": False,
    "youtube_msg": "",
    "bots_ready": False
}

# -------------------------------------------------------------
# KHỞI TẠO 5 DISCORD BOT INSTANCES (commands.Bot)
# -------------------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

orch_bot = commands.Bot(command_prefix="!orch ", intents=intents)
news_bot = commands.Bot(command_prefix="!news ", intents=intents)
market_bot = commands.Bot(command_prefix="!market ", intents=intents)
thumbnail_bot = commands.Bot(command_prefix="!thumb ", intents=intents)
monitor_bot = commands.Bot(command_prefix="!mon ", intents=intents)

async def sync_bot_tree(bot: commands.Bot, name: str):
    """Đồng bộ Slash Command cho bot với Guild hoặc Global."""
    try:
        if DISCORD_GUILD_ID:
            guild_obj = discord.Object(id=DISCORD_GUILD_ID)
            bot.tree.copy_global_to(guild=guild_obj)
            synced = await bot.tree.sync(guild=guild_obj)
            print(f"[{name}] Đã đồng bộ {len(synced)} slash commands vào Guild {DISCORD_GUILD_ID}", flush=True)
        else:
            synced = await bot.tree.sync()
            print(f"[{name}] Đã đồng bộ {len(synced)} global slash commands", flush=True)
    except Exception as e:
        print(f"[{name}] Lỗi đồng bộ slash command: {e}", flush=True)

# -------------------------------------------------------------
# STARTUP VALIDATION CHECK
# -------------------------------------------------------------
def run_startup_checks():
    print("\n" + "=" * 45, flush=True)
    print(f"   AI 4 AI - Startup Check (Niche: {NICHE_TOPIC})", flush=True)
    print("=" * 45, flush=True)

    llm_ok, llm_msg = llm_client.test_connection()
    SYSTEM_HEALTH["llm_ok"] = llm_ok
    SYSTEM_HEALTH["llm_msg"] = llm_msg
    status_icon_llm = "✅" if llm_ok else "❌"
    print(f"[{status_icon_llm}] LLM Provider ({LLM_PROVIDER}): {llm_msg}", flush=True)

    yt_ok, yt_msg = youtube_service.test_connection()
    SYSTEM_HEALTH["youtube_ok"] = yt_ok
    SYSTEM_HEALTH["youtube_msg"] = yt_msg
    status_icon_yt = "✅" if yt_ok else "❌"
    print(f"[{status_icon_yt}] YouTube API Key: {yt_msg}", flush=True)

    print(f"[⚙️] Daily Schedule: {'BẬT' if DAILY_RUN_ENABLED else 'TẮT'} lúc {DAILY_RUN_TIME} ({DAILY_RUN_TIMEZONE})", flush=True)
    if RECIPIENT_DISCORD_USER_ID:
        print(f"[👤] DM Recipient ID: {RECIPIENT_DISCORD_USER_ID}", flush=True)
    else:
        print("[ℹ️] DM Recipient: Chưa cấu hình RECIPIENT_DISCORD_USER_ID trong .env", flush=True)
    print("=" * 45 + "\n", flush=True)

# -------------------------------------------------------------
# SCHEDULED DAILY AUTO-RUN TASK
# -------------------------------------------------------------
def get_current_local_time() -> datetime:
    """Lấy thời gian hiện tại theo múi giờ DAILY_RUN_TIMEZONE."""
    if ZoneInfo:
        try:
            tz = ZoneInfo(DAILY_RUN_TIMEZONE)
            return datetime.now(tz)
        except Exception:
            pass
    # Fallback cho Asia/Ho_Chi_Minh (UTC+7)
    return datetime.now(timezone(timedelta(hours=7)))

DAILY_PM_TRACKER_FILE = BASE_DIR / "data" / ".last_daily_pm"

def get_last_daily_pm_date() -> str:
    if DAILY_PM_TRACKER_FILE.exists():
        try:
            return DAILY_PM_TRACKER_FILE.read_text(encoding="utf-8").strip()
        except Exception:
            return ""
    return ""

def set_last_daily_pm_date(date_str: str):
    try:
        DAILY_PM_TRACKER_FILE.parent.mkdir(parents=True, exist_ok=True)
        DAILY_PM_TRACKER_FILE.write_text(date_str, encoding="utf-8")
    except Exception:
        pass

@tasks.loop(seconds=30)
async def scheduled_daily_run():
    if not DAILY_RUN_ENABLED:
        return

    now = get_current_local_time()
    today_str = now.strftime("%Y-%m-%d")
    current_hm = now.strftime("%H:%M")
    last_pm_date = get_last_daily_pm_date()

    # Đúng 19:30 (hoặc khi bật bot sau 19:30 mà hôm nay chưa gửi), Bot Lớn CHỈ chủ động PM hỏi thăm ý tưởng
    if (current_hm >= DAILY_RUN_TIME) and (last_pm_date != today_str):
        set_last_daily_pm_date(today_str)
        print(f"\n[Scheduled Daily PM] ⏰ Đến giờ làm việc ({current_hm}), Bot Lớn chủ động PM hỏi thăm ý tưởng cho đại ca...", flush=True)
        await send_startup_proactive_pm(force=True)

# ID của Đại Ca để bot chủ động chào hỏi qua DM
OWNER_DISCORD_USER_ID = 669194207713427486

# Bộ nhớ ngữ cảnh hội thoại tin nhắn riêng (lưu tối đa 12 tin nhắn gần nhất mỗi người)
DM_CONVERSATION_HISTORY: dict[int, list[dict[str, str]]] = {}

has_sent_startup_pm = False

async def send_startup_proactive_pm(force: bool = False):
    """
    Bot Lớn chủ động nhắn tin riêng (PM) cho Đại Ca và Cộng sự khi khởi động hoặc đúng 19:30:
    - Chào hỏi tự nhiên, cập nhật trạng thái làm việc của team 5 bot.
    - Đặt câu hỏi mở thăm dò ý tưởng làm video hôm nay.
    - Tuyệt đối chỉ gửi 1 lần duy nhất mỗi ngày (không spam khi restart bot).
    """
    global has_sent_startup_pm
    now_vn = datetime.now(timezone(timedelta(hours=7)))
    today_str = now_vn.strftime("%Y-%m-%d")
    
    if not force:
        if get_last_daily_pm_date() == today_str or has_sent_startup_pm:
            return

    has_sent_startup_pm = True
    set_last_daily_pm_date(today_str)

    await asyncio.sleep(3)  # Đợi các client ổn định

    target_ids = []
    if OWNER_DISCORD_USER_ID:
        target_ids.append(OWNER_DISCORD_USER_ID)
    LAST_STARTUP_PM_TIMESTAMPS = getattr(send_startup_proactive_pm, "_last_sent", {})
    send_startup_proactive_pm._last_sent = LAST_STARTUP_PM_TIMESTAMPS

    bot_name = orch_bot.user.name if orch_bot.user else "Orchestrator"

    for uid in target_ids:
        try:
            # Kiểm tra Cooldown: Nếu đã gửi tin nhắn chào cho user này trong vòng 4 tiếng thì bỏ qua (tránh spam khi restart bot)
            now_dt = datetime.now()
            last_sent_dt = LAST_STARTUP_PM_TIMESTAMPS.get(uid)
            if last_sent_dt and (now_dt - last_sent_dt).total_seconds() < 14400:
                print(f"[Orchestrator] ℹ️ Đã gửi tin nhắn chào cho {uid} cách đây {int((now_dt - last_sent_dt).total_seconds() / 60)} phút. Bỏ qua để không làm phiền.", flush=True)
                continue

            user = orch_bot.get_user(uid) or await orch_bot.fetch_user(uid)
            if not user:
                continue

            now_vn = datetime.now(timezone(timedelta(hours=7)))
            time_vn_str = now_vn.strftime("%H:%M")

            greeting_prompt = f"""
Bạn là {bot_name} — Anh cả điều phối của hệ thống 5 AI Agent nghiên cứu YouTube Niche {NICHE_TOPIC}.
Bạn đang chủ động nhắn tin riêng (PM) cho {user.name} vào buổi tối ({time_vn_str} giờ Việt Nam).

QUY TẮC BẮT BUỘC:
1. Xưng "em", gọi "đại ca" hoặc "anh {user.name}".
2. Nói chuyện cực kỳ tự nhiên, dí dỏm, gãy gọn như anh em ngồi cà phê (2 - 3 câu ngắn gọn, súc tích).
3. Báo nhanh là 5 anh em đã vào ca làm việc sẵn sàng.
4. Đặt 1 câu hỏi mở ngắn gọn xem tối nay đại ca đang ấp ủ chủ đề video nào để team triển khai.
5. BẮT BUỘC KẾT THÚC BẰNG CÂU HOÀN CHỈNH, TUYỆT ĐỐI KHÔNG BỎ DỞ DÒNG CHỮ GIỮA CHỪNG.
"""
            llm_res = await llm_client.chat_completion(
                messages=[{"role": "user", "content": greeting_prompt}],
                temperature=0.7,
                max_tokens=800
            )
            greeting_text = strip_think_tags(llm_res.get("content", f"Dạ em chào đại ca {user.name}! Em và 4 anh em bot đã vào ca làm việc tối nay. Đại ca đang tính triển khai chủ đề video gì để team em cùng hội bàn nhé!"))

            # Gửi tin nhắn DM
            await user.send(greeting_text)
            LAST_STARTUP_PM_TIMESTAMPS[uid] = now_dt
            print(f"[Orchestrator] 💬 [ĐÃ GỬI PM CHỦ ĐỘNG] Tới {user.name} (ID: {uid}):\n{greeting_text}\n", flush=True)

            # Lưu vào memory và SQLite
            conv_key = user.id
            if conv_key not in DM_CONVERSATION_HISTORY:
                DM_CONVERSATION_HISTORY[conv_key] = []
            DM_CONVERSATION_HISTORY[conv_key].append({"role": "assistant", "content": greeting_text})

            chat_logger.log_chat(
                context_type="DM",
                channel_name="Direct Message (DM)",
                user_id=str(uid),
                user_name=user.name,
                bot_name=bot_name,
                bot_role="Orchestrator",
                user_message="[Bot Chủ Động Bật Tin Nhắn PM]",
                bot_response=greeting_text
            )

        except discord.Forbidden:
            print(f"[Orchestrator] ⚠️ Không thể gửi DM cho User ID {uid} (Người nhận đã tắt DM từ server).", flush=True)
        except Exception as e:
            print(f"[Orchestrator] ❌ Lỗi khi gửi PM chủ động tới {uid}: {e}", flush=True)

@orch_bot.event
async def on_ready():
    print(f"[Orchestrator Bot] [✅] Đăng nhập: {orch_bot.user.name} (ID: {orch_bot.user.id})", flush=True)
    await sync_bot_tree(orch_bot, "Orchestrator Bot")
    if not scheduled_daily_run.is_running():
        scheduled_daily_run.start()
        print(f"[Scheduled Task] Đã kích hoạt vòng lặp kiểm tra lịch chạy tự động.", flush=True)
    
    # Kích hoạt gửi PM chủ động hỏi thăm khi bot bật lên
    asyncio.create_task(send_startup_proactive_pm())

async def send_split_message(channel, text: str):
    """Gửi tin nhắn dài tự động chia nhỏ theo đoạn văn < 1900 ký tự để không bao giờ bị lỗi giới hạn 2000 ký tự của Discord."""
    if not text:
        return
    text = text.strip()
    if len(text) <= 1900:
        await channel.send(text)
        return

    paragraphs = text.split("\n\n")
    current_chunk = ""
    for p in paragraphs:
        if len(current_chunk) + len(p) + 2 > 1900:
            if current_chunk:
                await channel.send(current_chunk.strip())
                current_chunk = ""
                await asyncio.sleep(0.6)
        if len(p) > 1900:
            lines = p.split("\n")
            for line in lines:
                if len(current_chunk) + len(line) + 1 > 1900:
                    await channel.send(current_chunk.strip())
                    current_chunk = ""
                    await asyncio.sleep(0.6)
                current_chunk += line + "\n"
        else:
            current_chunk += p + "\n\n"

    if current_chunk.strip():
        await channel.send(current_chunk.strip())

async def run_multi_agent_roundtable(initiator_user: discord.User, channel, target_topic: Optional[str] = None):
    """
    Kích hoạt phiên HỘI BÀN ĐA BOT CHUYÊN NGHIỆP:
    - Bám sát 100% chủ đề yêu cầu (không lệch chủ đề).
    - Giọng điệu tự nhiên, thực chiến, không văn mẫu robot.
    - Hiển thị typing và chia nhỏ tin nhắn dài.
    - Tự động xuất kịch bản 4 bước & render ảnh 4K ngay sau khi duyệt.
    """
    bot_name = orch_bot.user.name if orch_bot.user else "Orchestrator"
    topic = target_topic.strip() if (target_topic and target_topic.strip()) else f"{NICHE_TOPIC}: Bí ẩn khoa học kỳ thú"
    is_dm = isinstance(channel, discord.DMChannel) or (channel.guild is None)
    channel_display_name = "Direct Message (DM)" if is_dm else f"#{getattr(channel, 'name', 'chung')}"

    print(f"\n[Multi-Agent Roundtable] 🚀 Kích hoạt phiên hội bàn 5 bot về chủ đề: '{topic}'", flush=True)

    # -------------------------------------------------------------
    # BƯỚC 1: ORCHESTRATOR GIAO VIỆC & ĐỊNH HƯỚNG CHỦ ĐỀ
    # -------------------------------------------------------------
    target_ch_orch = orch_bot.get_channel(channel.id) or await orch_bot.fetch_channel(channel.id) if orch_bot.is_ready() else channel
    async with target_ch_orch.typing():
        orch_prompt = f"""
Bạn là {bot_name} — Anh Cả điều phối của cả team.
Đại ca {initiator_user.name} giao trọng trách làm video về chủ đề: "{topic}".

QUY TẮC PHÁT BIỂU:
1. Xưng "anh Cả", gọi 3 bot con là "các em".
2. Giao việc dứt khoát, súc tích:
   - Lệnh cho News Agent tìm góc tiếp cận tò mò nhất của "{topic}".
   - Lệnh cho Market Agent bóc tách công thức triệu view & Hook 3s.
   - Lệnh cho Thumbnail Agent lên concept visual giật CTR cao.
3. Yêu cầu 3 anh em tự trao đổi nhanh, bám sát 100% chủ đề "{topic}", không nói chuyện ngoài lề.
4. Trình bày ngắn gọn trong 2 đoạn, cách nhau 1 dòng trống. Giọng điệu anh em thực chiến.
"""
        orch_res = await llm_client.chat_completion(
            messages=[{"role": "user", "content": orch_prompt}],
            temperature=0.7,
            max_tokens=800
        )
        orch_text = strip_think_tags(orch_res.get("content", f"Nhận lệnh đại ca {initiator_user.name}! Anh Cả kích hoạt phiên hội bàn về '{topic}' cho 3 anh em ngay đây!"))
        await send_split_message(target_ch_orch, f"👑 **[{bot_name} - Giao Việc]**:\n\n{orch_text}")

    chat_logger.log_chat(
        context_type="Channel" if not is_dm else "DM",
        channel_name=channel_display_name,
        user_id=str(initiator_user.id),
        user_name=initiator_user.name,
        bot_name=bot_name,
        bot_role="Orchestrator",
        user_message=f"Hội bàn: {topic}",
        bot_response=orch_text
    )
    await asyncio.sleep(2)

    news_name = news_bot.user.name if news_bot.user else "News Agent"
    market_name = market_bot.user.name if market_bot.user else "Market Agent"
    thumb_name = thumbnail_bot.user.name if thumbnail_bot.user else "Thumbnail Agent"

    # -------------------------------------------------------------
    # BƯỚC 2: NEWS AGENT TÌM GÓC TÒ MÒ CỦA CHỦ ĐỀ
    # -------------------------------------------------------------
    target_ch_news = news_bot.get_channel(channel.id) or await news_bot.fetch_channel(channel.id) if news_bot.is_ready() else channel
    async with target_ch_news.typing():
        news_prompt = f"""
Bạn là {news_name} (Bot Tin Tức & Xu Hướng).
Chủ đề đang họp: "{topic}".

QUY TẮC PHÁT BIỂU:
1. BẮT BUỘC BÁM SÁT 100% CHỦ ĐỀ "{topic}". Tuyệt đối không nhảy sang chủ đề khác!
2. Chỉ ra 1 góc nhìn nghịch lý hoặc câu hỏi "Tại sao" gây tò mò nhất của "{topic}" mà người xem dễ lầm tưởng.
3. Tag hỏi anh {market_name}: "Góc này bên YouTube số liệu và độ tò mò thế nào anh?"
4. Nói chuyện tự nhiên, nhiệt tình, xưng "em", gọi Market Agent là "anh {market_name}".
5. Trình bày tối đa 2 đoạn ngắn (dưới 80 từ), cách dòng rõ ràng, kết thúc câu hoàn chỉnh.
"""
        news_res = await llm_client.chat_completion(
            messages=[{"role": "user", "content": news_prompt}],
            temperature=0.7,
            max_tokens=800
        )
        news_text = strip_think_tags(news_res.get("content", f"Em thấy góc nhìn nghịch lý của '{topic}' đang rất hot!"))
        await send_split_message(target_ch_news, f"📰🔥 **[{news_name}]**:\n\n{news_text}")

    chat_logger.log_chat(
        context_type="Channel" if not is_dm else "DM",
        channel_name=channel_display_name,
        user_id=str(initiator_user.id),
        user_name=initiator_user.name,
        bot_name=news_name,
        bot_role="News Agent",
        user_message="Đề xuất góc nhìn",
        bot_response=news_text
    )
    await asyncio.sleep(2.5)

    # -------------------------------------------------------------
    # BƯỚC 3: MARKET AGENT BÓC TÁCH HOOK 3S & CÔNG THỨC GIỮ CHÂN
    # -------------------------------------------------------------
    target_ch_market = market_bot.get_channel(channel.id) or await market_bot.fetch_channel(channel.id) if market_bot.is_ready() else channel
    async with target_ch_market.typing():
        market_prompt = f"""
Bạn là {market_name} (Bot Phân Tích Số Liệu & Chiến Lược Video).
Chủ đề chính: "{topic}".
Ý kiến của News Agent: "{news_text}".

QUY TẮC PHÁT BIỂU:
1. BẮT BUỘC BÁM SÁT 100% CHỦ ĐỀ "{topic}".
2. Đưa ra 1 câu Hook 3s mở đầu giật gân, đánh trúng tâm lý người xem về "{topic}".
3. Nêu cấu trúc 4 bước giữ chân: Hiện tượng -> Thử nghiệm -> Bản chất vi mô -> Ứng dụng thực tế.
4. Tag hỏi anh {thumb_name}: "Góc này visual 3D hoặc tương phản màu sắc làm thế nào để kéo CTR cao anh?"
5. Xưng "em", gọi Thumbnail Agent là "anh {thumb_name}". Nói chuyện gãy gọn, ngắn gọn dưới 80 từ, câu cú hoàn chỉnh.
"""
        market_res = await llm_client.chat_completion(
            messages=[{"role": "user", "content": market_prompt}],
            temperature=0.7,
            max_tokens=800
        )
        market_text = strip_think_tags(market_res.get("content", f"Chủ đề '{topic}' có tỷ lệ giữ chân rất cao nếu mở đầu bằng cú Hook nghịch lý!"))
        await send_split_message(target_ch_market, f"📊🚀 **[{market_name}]**:\n\n{market_text}")

    chat_logger.log_chat(
        context_type="Channel" if not is_dm else "DM",
        channel_name=channel_display_name,
        user_id=str(initiator_user.id),
        user_name=initiator_user.name,
        bot_name=market_name,
        bot_role="Market Agent",
        user_message="Phân tích Hook & Số liệu",
        bot_response=market_text
    )
    await asyncio.sleep(2.5)

    # -------------------------------------------------------------
    # BƯỚC 4: THUMBNAIL AGENT CHỐT CONCEPT HÌNH ẢNH CTR CAO
    # -------------------------------------------------------------
    target_ch_thumb = thumbnail_bot.get_channel(channel.id) or await thumbnail_bot.fetch_channel(channel.id) if thumbnail_bot.is_ready() else channel
    async with target_ch_thumb.typing():
        thumb_prompt = f"""
Bạn là {thumb_name} (Bot Thiết Kế Visual & Thumbnail Flow Studio).
Chủ đề chính: "{topic}".
Đề xuất kịch bản của Market Agent: "{market_text}".

QUY TẮC PHÁT BIỂU:
1. BẮT BUỘC BÁM SÁT 100% CHỦ ĐỀ "{topic}".
2. Đưa ra 1 concept Thumbnail đinh: Bố cục tương phản mạnh (ví dụ: Mặt cắt 3D, phóng đại kính hiển vi, màu sắc năng lượng Xanh - Cam), Text giật tò mò dưới 4 từ.
3. Tuyên bố: "3 anh em (News, Market, Thumbnail) đã HOÀN TOÀN ĐỒNG THUẬN PHƯƠNG ÁN!" và tag kính mời anh Cả @{bot_name} duyệt lệnh để triển khai!
4. Giọng điệu nghệ thuật, thực chiến, ngắn gọn dưới 80 từ, câu cú trọn vẹn.
"""
        thumb_res = await llm_client.chat_completion(
            messages=[{"role": "user", "content": thumb_prompt}],
            temperature=0.7,
            max_tokens=800
        )
        thumb_text = strip_think_tags(thumb_res.get("content", f"Em đã chốt concept Visual 3D siêu thực cho '{topic}'. 3 anh em đã hoàn toàn thống nhất!"))
        await send_split_message(target_ch_thumb, f"🎨✨ **[{thumb_name}]**:\n\n{thumb_text}")

    chat_logger.log_chat(
        context_type="Channel" if not is_dm else "DM",
        channel_name=channel_display_name,
        user_id=str(initiator_user.id),
        user_name=initiator_user.name,
        bot_name=thumb_name,
        bot_role="Thumbnail Agent",
        user_message="Chốt Concept Thumbnail",
        bot_response=thumb_text
    )
    await asyncio.sleep(3)

    # -------------------------------------------------------------
    # BƯỚC 5: ORCHESTRATOR PHÊ DUYỆT & TỔNG KẾT KẾ HOẠCH
    # -------------------------------------------------------------
    async with target_ch_orch.typing():
        final_prompt = f"""
Bạn là {bot_name} — Anh Cả điều phối.
Team vừa thống nhất phương án tác chiến cho chủ đề: "{topic}".
- Ý kiến News: {news_text}
- Ý kiến Market: {market_text}
- Ý kiến Thumbnail: {thumb_text}

NHIỆM VỤ:
1. Tuyên bố duyệt phương án đồng thuận của 3 anh em.
2. Trình bày BẢN KẾ HOẠCH TÁC CHIẾN 1 TRANG cho đại ca {initiator_user.name}:
   - 🎯 **Tiêu đề Video đề xuất:** (Clickable & Gây tò mò)
   - ⚡ **Hook 3s mở đầu:** (Câu nói giữ chân người xem)
   - 🎬 **Cốt truyện 4 Bước Vàng:** (Hiện tượng -> Thí nghiệm -> Bản chất vi mô -> Bài học & CTA)
   - 🖼️ **Concept Thumbnail:** (Mô tả thị giác 3D đinh)
3. Tuyên bố phát lệnh cho Market Agent xuất kịch bản và Thumbnail Agent vẽ ảnh ngay lập tức!
Giọng điệu: Quyết đoán, chuyên nghiệp, thông minh, xưng "em", gọi {initiator_user.name} là "đại ca".
Trình bày thoáng đãng, dùng đầu mục rõ ràng, cách 1 dòng trống giữa các phần.
"""
        final_res = await llm_client.chat_completion(
            messages=[{"role": "user", "content": final_prompt}],
            temperature=0.6,
            max_tokens=850
        )
        final_text = strip_think_tags(final_res.get("content", "Bản kế hoạch hành động đã được phê duyệt."))
        await send_split_message(target_ch_orch, f"👑 **[{bot_name} - Phê Duyệt Kế Hoạch]**:\n\n{final_text}")

    chat_logger.log_chat(
        context_type="Channel" if not is_dm else "DM",
        channel_name=channel_display_name,
        user_id=str(initiator_user.id),
        user_name=initiator_user.name,
        bot_name=bot_name,
        bot_role="Orchestrator",
        user_message=f"Phê duyệt kế hoạch: {topic}",
        bot_response=final_text
    )
    print(f"[Multi-Agent Roundtable] [✅ HOÀN TẤT] Đã chốt kế hoạch thành công! Đang tự động kích hoạt sản xuất kịch bản & vẽ ảnh 4K...\n", flush=True)

    # -------------------------------------------------------------
    # BƯỚC 6: TỰ ĐỘNG TRIỂN KHAI THỰC TẾ (VIẾT KỊCH BẢN + VẼ ẢNH 4K)
    # -------------------------------------------------------------
    await asyncio.sleep(1)
    await send_split_message(target_ch_orch, f"🚀 **[{bot_name} - Triển Khai Tác Chiến]**: Đã phê duyệt xong! Em lệnh cho **Market Agent** xuất bản kịch bản 4 bước và **Thumbnail Agent** vẽ ảnh minh họa 4K cho đại ca ngay bây giờ! ⚡")
    
    # 1. Tự động xuất kịch bản 4 bước đúng 100% theo chủ đề
    await execute_script_generation(
        initiator_user=initiator_user,
        channel=channel,
        topic=topic,
        format_type="Shorts 60s (Dọc 9:16)"
    )

    # 2. Tự động vẽ ảnh Thumbnail 4K đúng 100% theo chủ đề
    await execute_image_generation(
        initiator_user=initiator_user,
        channel=channel,
        prompt_or_idea=f"{topic}: 3D volumetric microscopic visualization, dramatic atmospheric lighting, photorealistic scientific illustration",
        style="3D Cinematic Masterpiece",
        aspect_ratio="16:9"
    )

async def execute_script_generation(initiator_user: discord.User, channel, topic: str, format_type: str = "Shorts 60s (Dọc 9:16)"):
    """
    Thực thi tạo kịch bản chi tiết kèm prompt video AI dựa trên phân tích kênh hot & kênh đang lên.
    """
    import re
    is_dm = isinstance(channel, discord.DMChannel) or (channel.guild is None)
    clean_topic = topic
    triggers_to_remove = [
        "vậy thì làm về chủ đề", "làm về chủ đề", "hãy tạo prompt dựng kịch bản", "dựng kịch bản", "làm video", "hình ảnh cho tôi",
        "viết kịch bản", "viet kich ban", "lên kịch bản", "len kich ban", "kịch bản prompt", "kich ban prompt",
        "tạo kịch bản", "tao kich ban", "prompt làm theo", "prompt video", "làm theo kênh", "lam theo kenh",
        "tạo prompt", "tao prompt", "làm video", "lam video", "cho tôi", "hãy tạo", "làm về", "chủ đề", "kịch bản", "kich ban"
    ]
    for trigger in triggers_to_remove:
        clean_topic = re.sub(re.escape(trigger), "", clean_topic, flags=re.IGNORECASE).strip()
    clean_topic = re.sub(r"^[,.:;?! -]+", "", clean_topic).strip()
    clean_topic = re.sub(r"[,.:;?! -]+$", "", clean_topic).strip()

    if not clean_topic:
        clean_topic = f"{NICHE_TOPIC}: Hiện tượng khoa học bí ẩn"

    loading_msg = await channel.send(f"📊🎬 **[Market Agent & Biên Kịch AI]**: Đang quét thị trường & viết kịch bản 4 bước kèm Prompt AI cho chủ đề: **'{clean_topic}'**... ⏳")

    try:
        async with channel.typing():
            res = await script_generator.generate_script_from_market(
                topic=clean_topic,
                format_type=format_type
            )
            
            # 1. Gửi khối Quick Copy trong Embed / Code block riêng biệt để 1 chạm copy ngay trên điện thoại & PC
            quick_copy_text = res.get("quick_copy") or script_generator.extract_quick_copy(res["script_content"])
            quick_copy_embed = discord.Embed(
                title=f"⚡ QUICK COPY — PROMPT DÙNG NGAY ({clean_topic[:35]})",
                description=f"```text\n{quick_copy_text}\n```",
                color=0x00FFCC
            )
            quick_copy_embed.set_footer(text="💡 Chạm 1 lần vào khung trên để copy toàn bộ prompt ảnh & video!")
            await channel.send(embed=quick_copy_embed)

            # 2. Gửi file kịch bản Markdown chi tiết đầy đủ
            script_file = discord.File(res["filepath"], filename=res["filename"])
            embed = discord.Embed(
                title=f"🎬 KỊCH BẢN CHI TIẾT & PROMPT AI: {clean_topic[:45]}",
                description=f"📐 **Định dạng:** `{res['format']}`\n"
                            f"📊 **Dữ liệu phân tích:** `{res['hot_videos_analyzed']}` video top views & `{res['breakout_videos_analyzed']}` video bứt phá\n\n"
                            f"🎯 **Cấu trúc Kịch Bản:**\n"
                            f"• 🌟 **Mở đầu (Hook 3s):** Hiện tượng bất ngờ gây tò mò cực độ\n"
                            f"• 🧪 **Thử nghiệm / Diễn tiến:** Tái hiện trực quan dễ hình dung\n"
                            f"• ⚡ **Giải thích khoa học sâu:** Cơ chế vi mô + Dẫn nguồn nghiên cứu uy tín\n"
                            f"• 💡 **Ứng dụng & CTA:** Bài học đời sống + Câu hỏi kích thích bình luận\n\n"
                            f"💡 *File Kịch bản chi tiết + Lời thoại Voiceover + Prompt Runway/Midjourney từng cảnh đã đính kèm bên dưới!*",
                color=COLOR_MARKET
            )
            embed.set_footer(text=f"Yêu cầu bởi {initiator_user.name} • File: {res['filename']}")
            await channel.send(embed=embed, file=script_file)
            try:
                await loading_msg.delete()
            except Exception:
                pass

            # Ghi log vào Database cho Web Dashboard
            channel_display_name = "Direct Message (DM)" if is_dm else f"#{getattr(channel, 'name', 'server-channel')}"
            chat_logger.log_chat(
                context_type="DM" if is_dm else "Channel",
                channel_name=channel_display_name,
                user_id=str(initiator_user.id),
                user_name=initiator_user.name,
                bot_name="Market Agent",
                bot_role="Biên Kịch AI",
                user_message=f"Tạo kịch bản: {topic}",
                bot_response=f"🎬 Đã xuất kịch bản & khối Quick Copy ({res['format']}): {res['filename']}"
            )

            # Nếu yêu cầu có nhắc tới "hình ảnh" hoặc "vẽ ảnh", tự động xuất luôn 1 ảnh minh họa 4K
            if any(w in topic.lower() for w in ["hình ảnh", "hinh anh", "vẽ ảnh", "ve anh", "ảnh", "anh"]):
                await execute_image_generation(
                    initiator_user=initiator_user,
                    channel=channel,
                    prompt_or_idea=clean_topic,
                    style="3D Cinematic Masterpiece",
                    aspect_ratio="16:9" if "16:9" in format_type else "9:16"
                )
    except Exception as e:
        await channel.send(f"⚠️ Có lỗi trong quá trình tạo kịch bản: {e}")

async def execute_channel_audit(initiator_user: discord.User, channel, channel_input: str):
    """
    Thực thi bóc tách toàn diện kênh YouTube: SEO, thẻ tag, và bộ prompt tạo ảnh AI theo phong cách kênh.
    """
    import re
    is_dm = isinstance(channel, discord.DMChannel) or (channel.guild is None)
    
    # Tìm link hoặc handle trong input
    url_match = re.search(r"https?://(?:www\.)?youtube\.com/(?:@[A-Za-z0-9_.-]+|channel/UC[0-9A-Za-z_-]{22}|c/[A-Za-z0-9_.-]+|user/[A-Za-z0-9_.-]+)", channel_input)
    handle_match = re.search(r"@[A-Za-z0-9_.-]+", channel_input)
    target_channel = url_match.group(0) if url_match else (handle_match.group(0) if handle_match else channel_input.strip())

    loading_msg = await channel.send(f"🔍🎨 **[Market & Thumbnail Agent]**: Đang bóc tách toàn diện kênh `{target_channel}` (SEO, Thẻ Tags, DNA Thumbnail & Viết Prompt AI)... ⏳")

    try:
        async with channel.typing():
            res = await channel_auditor.audit_channel(target_channel)
            if res.get("status") != "success":
                await channel.send(f"⚠️ {res.get('message', 'Không thể bóc tách kênh.')}")
                return

            audit_file = discord.File(res["filepath"], filename=res["filename"])
            embed = discord.Embed(
                title=f"📊 AUDIT KÊNH: {res['channel_title']}",
                description=f"🔗 **Kênh:** [{res['channel_title']}]({res['channel_url']})\n"
                            f"👥 **Subscribers:** `{res['subscribers']:,}` | 👀 **Lượt xem:** `{res['total_views']:,}`\n\n"
                            f"🏷️ **Top Thẻ Tags SEO:**\n`{'`, `'.join(res['popular_tags'][:6])}`\n\n"
                            f"🎨 **DNA Thiết Kế & 3 Prompt AI:**\n"
                            f"• Đã bóc tách bảng màu, bố cục và hiệu ứng ánh sáng\n"
                            f"• Đã tạo 3 bộ Prompt Midjourney v6 / Flux sao chép phong cách\n\n"
                            f"💡 *Bản báo cáo SEO & Bộ Prompt AI chi tiết đã được đính kèm bên dưới!*",
                color=COLOR_THUMBNAIL
            )
            if res.get("top_thumbnail_url"):
                embed.set_thumbnail(url=res["top_thumbnail_url"])
            embed.set_footer(text=f"Yêu cầu bởi {initiator_user.name} • File: {res['filename']}")
            await channel.send(embed=embed, file=audit_file)
            try:
                await loading_msg.delete()
            except Exception:
                pass

            channel_display_name = "Direct Message (DM)" if is_dm else f"#{getattr(channel, 'name', 'server-channel')}"
            chat_logger.log_chat(
                context_type="DM" if is_dm else "Channel",
                channel_name=channel_display_name,
                user_id=str(initiator_user.id),
                user_name=initiator_user.name,
                bot_name="Thumbnail Agent",
                bot_role="Audit Kênh",
                user_message=f"Audit kênh: {channel_input}",
                bot_response=f"📊 Đã bóc tách SEO & xuất 3 Prompt AI: {res['filename']}"
            )
    except Exception as e:
        await channel.send(f"⚠️ Có lỗi trong quá trình Audit kênh: {e}")

async def execute_image_generation(initiator_user: discord.User, channel, prompt_or_idea: str, style: str = "3D Cinematic Masterpiece", aspect_ratio: str = "16:9"):
    """
    Thực thi Flow AI: Tự động phân tích ý tưởng, viết Prompt tối ưu và tự vẽ ảnh 4K gửi vào Discord.
    """
    from services.image_service import image_service
    is_dm = isinstance(channel, discord.DMChannel) or (channel.guild is None)
    width, height = (1280, 720) if aspect_ratio == "16:9" else (720, 1280)
    
    clean_idea = prompt_or_idea.replace("vẽ ảnh", "").replace("tạo ảnh", "").replace("ve anh", "").replace("tao anh", "").replace("vẽ thumbnail", "").replace("ve thumbnail", "").strip()
    if not clean_idea:
        clean_idea = f"Hiện tượng khoa học kỳ thú trong {NICHE_TOPIC}"

    loading_msg = await channel.send(f"🎨✨ **[Thumbnail Agent Flow]**: Đang tối ưu Prompt bám sát chủ đề & tự vẽ ảnh 4K cho `{clean_idea[:60]}`... ⏳")
    
    try:
        async with channel.typing():
            res = await image_service.generate_image(
                prompt_or_idea=clean_idea,
                topic=clean_idea,
                scientific_details=f"specific scientific visual characteristics, microscopic physics or natural dynamics of {clean_idea}",
                style=style,
                width=width,
                height=height,
                enhance_prompt=True
            )
            if res.get("status") != "success":
                await channel.send(f"⚠️ {res.get('message', 'Không thể vẽ ảnh.')}")
                return
            
            img_file = discord.File(res["filepath"], filename=res["filename"])
            embed = discord.Embed(
                title=f"🎨 ẢNH THUMBNAIL / MINH HỌA: {res['title'][:50]}",
                description=f"🤖 **Flow Engine:** `{res['provider']}` | 📐 **Tỷ lệ:** `{aspect_ratio}`\n\n"
                            f"📝 **Prompt AI Đã Tối Ưu (Đã Self-Check Khớp Chủ Đề):**\n```{res['prompt']}```\n"
                            f"💡 *Đại ca có thể copy prompt trên để tái sử dụng trên Midjourney v6 hoặc Flux bất cứ lúc nào!*",
                color=COLOR_THUMBNAIL
            )
            embed.set_image(url=f"attachment://{res['filename']}")
            embed.set_footer(text=f"Yêu cầu bởi {initiator_user.name} • Engine: {res['provider']}")
            await channel.send(embed=embed, file=img_file)
            try:
                await loading_msg.delete()
            except Exception:
                pass

            channel_display_name = "Direct Message (DM)" if is_dm else f"#{getattr(channel, 'name', 'server-channel')}"
            chat_logger.log_chat(
                context_type="DM" if is_dm else "Channel",
                channel_name=channel_display_name,
                user_id=str(initiator_user.id),
                user_name=initiator_user.name,
                bot_name="Thumbnail Agent",
                bot_role="Flow Visual Studio",
                user_message=f"Vẽ ảnh: {prompt_or_idea}",
                bot_response=f"🎨 Đã vẽ & render ảnh 4K ({aspect_ratio}): {res['filename']}"
            )
    except Exception as e:
        await channel.send(f"⚠️ Có lỗi trong quá trình vẽ ảnh: {e}")

@orch_bot.event
async def on_message(message: discord.Message):
    # Bỏ qua tin nhắn từ chính bot hoặc các bot khác
    if message.author.bot:
        return

    is_dm = isinstance(message.channel, discord.DMChannel) or (message.guild is None)
    bot_user = orch_bot.user
    is_mentioned = bot_user and (bot_user in message.mentions)
    
    # Kiểm tra xem có phải reply vào tin nhắn của Orchestrator bot không
    is_reply_to_bot = False
    if message.reference and message.reference.resolved and isinstance(message.reference.resolved, discord.Message):
        if bot_user and message.reference.resolved.author.id == bot_user.id:
            is_reply_to_bot = True

    # Bot sẽ phản hồi nếu: (1) Nhắn tin riêng (DM), HOẶC (2) Được @tag trong bất kỳ kênh nào, HOẶC (3) Được reply trong kênh
    if is_dm or is_mentioned or is_reply_to_bot:
        user_id = message.author.id
        bot_name = orch_bot.user.name if orch_bot.user else "Orchestrator"
        
        # Làm sạch nội dung tin nhắn (xóa mention bot nếu có)
        user_text = message.clean_content.replace(f"@{bot_name}", "").replace(f"@{orch_bot.user.name}", "").strip() if bot_user else message.content.strip()
        if not user_text:
            user_text = "Chào em!"

        context_label = "DM" if is_dm else f"Kênh #{getattr(message.channel, 'name', 'server-channel')}"
        print(f"\n[Orchestrator {context_label}] 💬 @{message.author.name} (ID: {user_id}): '{user_text}'", flush=True)

        # Quản lý bộ nhớ ngữ cảnh hội thoại
        conv_key = user_id if is_dm else message.channel.id
        if conv_key not in DM_CONVERSATION_HISTORY:
            DM_CONVERSATION_HISTORY[conv_key] = []

        DM_CONVERSATION_HISTORY[conv_key].append({"role": "user", "content": f"{message.author.name}: {user_text}"})
        if len(DM_CONVERSATION_HISTORY[conv_key]) > 10:
            DM_CONVERSATION_HISTORY[conv_key] = DM_CONVERSATION_HISTORY[conv_key][-10:]

        # Kiểm tra nếu dán link kênh YouTube hoặc yêu cầu audit kênh / tạo ảnh giống kênh
        channel_triggers = [
            "youtube.com/@", "youtube.com/channel/", "youtube.com/c/",
            "phân tích kênh", "phan tich kenh", "audit kênh", "audit kenh",
            "soi kênh", "soi kenh", "prompt ảnh kênh", "prompt anh kenh",
            "tạo ảnh giống kênh", "tao anh giong kenh", "phong cách kênh", "phong cach kenh"
        ]
        if any(p in user_text.lower() for p in channel_triggers):
            await execute_channel_audit(message.author, message.channel, channel_input=user_text)
            return

        # Kiểm tra nếu yêu cầu vẽ ảnh / tạo ảnh thumbnail qua Flow
        image_triggers = [
            "vẽ ảnh", "ve anh", "tạo ảnh", "tao anh", "vẽ thumbnail", "ve thumbnail",
            "tạo thumbnail", "tao thumbnail", "vẽ hình", "ve hinh", "generate image",
            "draw image", "tự vẽ", "tu ve"
        ]
        if any(p in user_text.lower() for p in image_triggers):
            fmt_ratio = "9:16" if ("9:16" in user_text or "dọc" in user_text.lower() or "shorts" in user_text.lower()) else "16:9"
            await execute_image_generation(message.author, message.channel, prompt_or_idea=user_text, aspect_ratio=fmt_ratio)
            return

        # Kiểm tra nếu yêu cầu viết kịch bản kèm prompt video AI
        script_phrases = [
            "kịch bản", "kich ban", "dựng kịch bản", "dung kich ban",
            "viết kịch bản", "viet kich ban", "lên kịch bản", "len kich ban",
            "kịch bản prompt", "kich ban prompt", "tạo kịch bản", "tao kich ban",
            "prompt làm theo", "prompt video", "làm theo kênh", "lam theo kenh",
            "tạo prompt", "tao prompt", "làm video", "lam video", "prompt dựng", "prompt dung"
        ]
        if any(p in user_text.lower() for p in script_phrases):
            fmt = "Video Dài (Ngang 16:9)" if ("dài" in user_text.lower() or "16:9" in user_text.lower() or "ngang" in user_text.lower()) else "Shorts 60s (Dọc 9:16)"
            await execute_script_generation(message.author, message.channel, topic=user_text, format_type=fmt)
            return

        # Kiểm tra nếu có yêu cầu chốt kế hoạch / hội bàn / phân quyền / trao đổi giữa các bot
        trigger_phrases = [
            "phân quyền", "phan quyen", "trao đổi", "trao doi", "hội bàn", "hoi ban",
            "thảo luận", "thao luan", "chốt kế hoạch", "chot ke hoach", "chốt ý tưởng",
            "chot y tuong", "cùng làm việc", "cung lam viec", "tự trao đổi", "tu trao doi",
            "họp team", "hop team", "bàn kế hoạch", "ban ke hoach", "cùng làm", "cung lam",
            "các bot làm việc", "5 bot", "hội ý", "hoi y", "thống nhất ý kiến", "thong nhat y kien",
            "phân việc", "phan viec", "giao việc", "giao viec", "bắt đầu phân tích"
        ]
        if any(p in user_text.lower() for p in trigger_phrases):
            await run_multi_agent_roundtable(message.author, message.channel, target_topic=user_text)
            return

        async with message.channel.typing():
            now_vn = datetime.now(timezone(timedelta(hours=7)))
            time_vn_str = now_vn.strftime("%H:%M:%S ngày %d/%m/%Y")
            buoi_str = "ban đêm / tối" if (now_vn.hour >= 18 or now_vn.hour < 6) else ("buổi sáng" if now_vn.hour < 12 else "buổi chiều")
            channel_hint = "tin nhắn riêng" if is_dm else f"kênh chung #{getattr(message.channel, 'name', 'chung')}"
            system_prompt = f"""
Bạn là {bot_name} — Anh cả điều phối của hệ thống 5 AI Agent nghiên cứu YouTube Niche {NICHE_TOPIC}.
Bạn đang trò chuyện như một người em / cộng sự YouTube thực chiến với {message.author.name} tại {channel_hint}.
[THỜI GIAN HIỆN TẠI]: Bây giờ là {time_vn_str} ({buoi_str} tại Việt Nam).

QUY TẮC BẮT BUỘC (TUYỆT ĐỐI TUÂN THỦ):
1. **CỰC KỲ TỰ NHIÊN, NÓI CHUYỆN NHƯ NGƯỜI THẬT:**
   - Xưng "em", gọi người nói chuyện là "đại ca" hoặc "anh {message.author.name}".
   - Nói chuyện như anh em ngồi cà phê bàn ý tưởng: dí dỏm, thực chiến, không văn mẫu robot.
2. **TRÌNH BÀY THOÁNG ĐÃNG, DỄ ĐỌC TRÊN DISCORD (RẤT QUAN TRỌNG):**
   - **Bắt buộc cách 1 dòng trống (`\n\n`)** giữa các ý để người đọc không bị mỏi mắt.
   - Sử dụng đầu mục rõ ràng: `🔹 **1. [Tên ý]:** [Mô tả ngắn gọn trong 1 - 2 câu]`.
   - KHÔNG dùng ký tự công thức rối mắt như `\(...\)` hay lồng ghép quá nhiều dấu `**`, `*`.
   - Tổng độ dài: Tối đa 3 - 4 ý ngắn gọn, súc tích (dưới 150 từ).
3. **DẪN CHỨNG & LINK NGUỒN XÁC THỰC:**
   - Khi giải thích hiện tượng khoa học, hãy chèn link nguồn uy tín (Nature, Science, Khan Academy, MIT, Wikipedia...) để người xem bấm vào kiểm chứng.
4. **KẾT BÀI GỢI MỞ SẮC BÉN:**
   - Luôn chốt bằng 1 câu hỏi gợi mở trong quote block `> ` để đại ca dễ chọn hướng tiếp theo.
"""
            messages_payload = [{"role": "system", "content": system_prompt}] + DM_CONVERSATION_HISTORY[conv_key]

            llm_res = await llm_client.chat_completion(
                messages=messages_payload,
                temperature=0.7,
                max_tokens=600
            )
            reply_text = strip_think_tags(llm_res.get("content", "Dạ em nghe đây! Đại ca tính triển khai góc nào thế ạ?"))
            if not reply_text:
                reply_text = "Dạ em đây ạ! Đại ca đang muốn đào sâu về góc nhìn nào, nói em cùng thảo luận nhé!"

            # Lưu câu trả lời của bot vào lịch sử memory
            DM_CONVERSATION_HISTORY[conv_key].append({"role": "assistant", "content": reply_text})

            # Ghi vào Database SQLite để hiển thị lên Web Dashboard
            channel_display_name = "Direct Message (DM)" if is_dm else f"#{getattr(message.channel, 'name', 'server-channel')}"
            chat_logger.log_chat(
                context_type="DM" if is_dm else "Channel",
                channel_name=channel_display_name,
                user_id=str(user_id),
                user_name=message.author.name,
                bot_name=bot_name,
                bot_role="Orchestrator",
                user_message=user_text,
                bot_response=reply_text
            )

            await message.reply(reply_text)
            print(f"[Orchestrator {context_label}] 📤 Phản hồi: {reply_text}\n", flush=True)

    await orch_bot.process_commands(message)

@orch_bot.tree.command(name="kichban", description="[Orchestrator] Quét kênh hot/đang lên và viết kịch bản chi tiết kèm prompt video AI")
@app_commands.describe(
    topic="Chủ đề hoặc từ khóa video muốn làm (ví dụ: 'Bí ẩn hố đen', 'James Webb')",
    dinh_dang="Định dạng video: 'Shorts 60s (Dọc 9:16)' hoặc 'Video Dài (Ngang 16:9)'"
)
async def orch_kichban_cmd(interaction: discord.Interaction, topic: Optional[str] = None, dinh_dang: Optional[str] = "Shorts 60s (Dọc 9:16)"):
    chosen_topic = topic or f"{NICHE_TOPIC}: Bí ẩn khám phá mới"
    await interaction.response.send_message(f"👑🎬 **[Orchestrator]**: Đã tiếp nhận yêu cầu viết kịch bản & prompt AI cho chủ đề: **'{chosen_topic}'** ({dinh_dang})! 🚀")
    await execute_script_generation(interaction.user, interaction.channel, topic=chosen_topic, format_type=dinh_dang)

@orch_bot.tree.command(name="audit_channel", description="[Orchestrator] Bóc tách toàn diện kênh YouTube (SEO, thẻ tag, và prompt tạo ảnh AI)")
@app_commands.describe(channel_url_or_handle="Link kênh YouTube hoặc @handle (ví dụ: https://www.youtube.com/@Kurzgesagt hoặc @Kurzgesagt)")
async def orch_audit_cmd(interaction: discord.Interaction, channel_url_or_handle: str):
    await interaction.response.send_message(f"👑🔍 **[Orchestrator]**: Bắt đầu phiên AUDIT TOÀN DIỆN kênh `{channel_url_or_handle}`! 🚀")
    await execute_channel_audit(interaction.user, interaction.channel, channel_input=channel_url_or_handle)

@orch_bot.tree.command(name="hoiban", description="[Orchestrator] Kích hoạt phiên hội bàn 5 bot tự động trao đổi và thống nhất ý kiến")
@app_commands.describe(topic=f"Đề tài hoặc từ khóa bạn muốn 5 bot cùng mổ xẻ (ví dụ: 'Hố đen siêu khối lượng', '{NICHE_TOPIC}')")
async def hoiban_cmd(interaction: discord.Interaction, topic: Optional[str] = None):
    await interaction.response.send_message(f"👑 **[Orchestrator]**: Kích hoạt phiên HỘI BÀN 5 BOT về chủ đề: `{topic or NICHE_TOPIC}` ngay lập tức! 🚀")
    await run_multi_agent_roundtable(interaction.user, interaction.channel, target_topic=topic)

@orch_bot.tree.command(name="chot_ke_hoach", description="[Orchestrator] Kích hoạt phiên hội bàn 5 bot tự động trao đổi và thống nhất ý kiến")
async def chot_ke_hoach_cmd(interaction: discord.Interaction):
    await interaction.response.send_message("👑 **[Orchestrator]**: Kích hoạt phiên HỘI BÀN 5 BOT và phân quyền tác chiến ngay lập tức! 🚀")
    await run_multi_agent_roundtable(interaction.user, interaction.channel)

@orch_bot.tree.command(name="start", description="[Orchestrator] Chào hỏi nhanh, kiểm tra bot hoạt động")
async def orch_start_cmd(interaction: discord.Interaction):
    bot_name = orch_bot.user.name if orch_bot.user else "Orchestrator"
    user_mention = f"<@{interaction.user.id}>"
    await interaction.response.send_message(
        f"👑 **[{bot_name}]**: Chào đại ca {user_mention}! Em là **Orchestrator** (Anh cả điều phối), hệ thống nghiên cứu niche **{NICHE_TOPIC}** đã sẵn sàng nhận lệnh `/report` để chỉ huy 4 anh em vào việc."
    )

@orch_bot.tree.command(name="help", description="[Orchestrator] Xem danh sách toàn bộ lệnh của hệ thống")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(
        title=f"📋 DANH SÁCH LỆNH HỆ THỐNG — NICHE: {NICHE_TOPIC.upper()}",
        description=f"Hệ thống nghiên cứu thị trường YouTube Niche **{NICHE_TOPIC}** gồm 5 Bot chuyên biệt:",
        color=COLOR_ORCHESTRATOR
    )
    embed.add_field(
        name="🚀 Lệnh Chính",
        value="• `/ve_anh [chu_de]` — Tự viết Prompt AI & vẽ ảnh minh họa/thumbnail 4K\n"
              "• `/kichban [topic] [dinh_dang]` — Quét kênh hot/đang lên & viết kịch bản kèm Prompt AI\n"
              "• `/audit_channel [link/@handle]` — Bóc tách SEO, Thẻ Tag & Prompt AI ảnh kênh\n"
              "• `/report` — Chạy phân tích cơ hội nội dung YouTube đầy đủ (cần quyền)\n"
              "• `/hoiban [topic]` — Kích hoạt phiên hội bàn 5 bot tự động trao đổi\n"
              "• `/quota` — Xem tình trạng quota YouTube API & Groq/LLM API\n"
              "• `/help` — Xem danh sách lệnh này",
        inline=False
    )
    embed.add_field(
        name="🛠️ Lệnh Bổ Trợ Theo Bot",
        value=f"• `/score_niche [topic]` *(Orchestrator)* — Chấm điểm nhanh 1 niche (0-100 & Tier)\n"
              f"• `/trend [topic]` *(News Bot)* — Quét tin tức {NICHE_TOPIC} 30 ngày qua\n"
              f"• `/hot_topics` *(News Bot)* — Danh sách chủ đề {NICHE_TOPIC} đang viral\n"
              f"• `/market_search [query]` *(Market Bot)* — Tìm video breakout (kênh nhỏ view cao)\n"
              f"• `/video_stats [url]` *(Market Bot)* — Bóc tách chỉ số chi tiết 1 video\n"
              f"• `/thumbnail_analyze [url]` *(Thumbnail Bot)* — Phân tích thị giác màu sắc/bố cục\n"
              f"• `/thumbnail_ideas [topic]` *(Thumbnail Bot)* — Gợi ý 3 concept CTR cao\n"
              f"• `/system_status` *(Monitor Bot)* — Kiểm tra kết nối 5 bot & API keys\n"
              f"• `/ping` *(Monitor Bot)* — Đo độ trễ mạng của hệ thống bot",
        inline=False
    )
    schedule_status = f"Bật lúc `{DAILY_RUN_TIME}` hàng ngày" if DAILY_RUN_ENABLED else "Tắt"
    embed.add_field(
        name="⚙️ Cấu Hình Hiện Tại",
        value=f"• **Chủ đề (Niche):** `{NICHE_TOPIC}`\n"
              f"• **Lịch tự động:** {schedule_status}\n"
              f"• **Người nhận DM:** <@{RECIPIENT_DISCORD_USER_ID}>" if RECIPIENT_DISCORD_USER_ID else f"• **Lịch tự động:** {schedule_status}",
        inline=False
    )
    embed.set_footer(text=f"Yêu cầu bởi {interaction.user.name} | 5 Bots Online")
    await interaction.response.send_message(embed=embed)

@orch_bot.tree.command(name="ve_anh", description="[Orchestrator] Tự viết Prompt AI & vẽ ảnh minh họa/thumbnail chuẩn 4K")
@app_commands.describe(
    chu_de="Chủ đề hoặc ý tưởng ảnh (ví dụ: Mặt cắt não bộ phát sáng khi ngủ)",
    phong_cach="Phong cách ảnh mong muốn",
    ty_le="Tỷ lệ khung hình"
)
@app_commands.choices(
    phong_cach=[
        app_commands.Choice(name="3D Cinematic Masterpiece", value="3D Cinematic Masterpiece"),
        app_commands.Choice(name="Mặt Cắt Siêu Thực (Cross-section)", value="Cross-section Sci-fi"),
        app_commands.Choice(name="Tương Phản Nhiệt (Thermal Contrast)", value="Thermal Contrast"),
        app_commands.Choice(name="Kính Hiển Vi Phóng Đại (Microscopic 1000x)", value="Microscopic 1000x")
    ],
    ty_le=[
        app_commands.Choice(name="16:9 (Ngang - Video Dài & Thumbnail)", value="16:9"),
        app_commands.Choice(name="9:16 (Dọc - Shorts / TikTok / Reels)", value="9:16")
    ]
)
async def orch_ve_anh_cmd(interaction: discord.Interaction, chu_de: str, phong_cach: Optional[app_commands.Choice[str]] = None, ty_le: Optional[app_commands.Choice[str]] = None):
    style_val = phong_cach.value if phong_cach else "3D Cinematic Masterpiece"
    ratio_val = ty_le.value if ty_le else "16:9"
    await interaction.response.send_message(f"🎨 **[Flow AI]**: Đang tối ưu Prompt & bắt đầu vẽ ảnh `{chu_de}`... 🚀")
    await execute_image_generation(interaction.user, interaction.channel, prompt_or_idea=chu_de, style=style_val, aspect_ratio=ratio_val)

@orch_bot.tree.command(name="report", description="[Orchestrator] Khởi chạy toàn bộ quy trình phân tích thị trường & cơ hội nội dung")
async def report_command(interaction: discord.Interaction):
    user_id = interaction.user.id
    if ALLOWED_DISCORD_USER_IDS and user_id not in ALLOWED_DISCORD_USER_IDS:
        await interaction.response.send_message("⛔ Bạn không có quyền dùng lệnh này.", ephemeral=True)
        return

    if not SYSTEM_HEALTH["llm_ok"] or not SYSTEM_HEALTH["youtube_ok"]:
        warning_text = "⚠️ **Hệ thống chưa sẵn sàng do lỗi kết nối API khi khởi động:**\n"
        if not SYSTEM_HEALTH["llm_ok"]:
            warning_text += f"- LLM ({LLM_PROVIDER}): {SYSTEM_HEALTH['llm_msg']}\n"
        if not SYSTEM_HEALTH["youtube_ok"]:
            warning_text += f"- YouTube API: {SYSTEM_HEALTH['youtube_msg']}\n"
        await interaction.response.send_message(warning_text, ephemeral=True)
        return

    if pipeline_lock.locked():
        await interaction.response.send_message("⏳ Đang có một phiên phân tích thị trường đang chạy, yêu cầu của bạn đã được xếp hàng. Vui lòng đợi trong giây lát...", ephemeral=True)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    thread_name = f"Report [{NICHE_TOPIC}] - {now_str}"
    channel = interaction.channel

    if not isinstance(channel, (discord.TextChannel, discord.ForumChannel)):
        await interaction.response.send_message("Lệnh này chỉ có thể chạy trong Text Channel.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=False)
    initial_msg = await interaction.followup.send(
        embed=discord.Embed(
            title=f"🚀 Đang khởi tạo phiên nghiên cứu thị trường: {NICHE_TOPIC}...",
            description=f"Yêu cầu bởi <@{user_id}>. Đang tạo thread phân tích riêng.",
            color=COLOR_ORCHESTRATOR
        )
    )

    try:
        thread = await channel.create_thread(name=thread_name, message=initial_msg, auto_archive_duration=1440)
    except Exception:
        thread = await channel.create_thread(name=thread_name, type=discord.ChannelType.public_thread, auto_archive_duration=1440)

    start_embed = discord.Embed(
        title=f"🎬 Bắt Đầu Nghiên Cứu Thị Trường: Niche {NICHE_TOPIC}",
        description=f"• **Thời gian:** `{now_str}`\n"
                    f"• **Chủ đề Niche:** `{NICHE_TOPIC}`\n"
                    f"• **Người kích hoạt:** <@{user_id}>\n"
                    f"• **Quy trình:** News Agent ➔ Market Agent ➔ Thumbnail Agent ➔ Báo Cáo Chiến Lược",
        color=COLOR_ORCHESTRATOR
    )
    await thread.send(embed=start_embed)

    async def execute_locked():
        async with pipeline_lock:
            await orchestrator.run_pipeline(
                thread=thread,
                dm_recipient=None,
                news_bot=news_bot,
                market_bot=market_bot,
                thumbnail_bot=thumbnail_bot,
                monitor_bot=monitor_bot
            )

    asyncio.create_task(execute_locked())

@orch_bot.tree.command(name="score_niche", description="[Orchestrator] Chấm điểm nhanh tiềm năng cơ hội cho một niche (0-100)")
@app_commands.describe(topic="Chủ đề / Niche cần chấm điểm (ví dụ: 'Khoa học vũ trụ', 'Hố đen kỳ bí')")
async def score_niche_cmd(interaction: discord.Interaction, topic: Optional[str] = None):
    await interaction.response.defer()
    target_topic = topic or NICHE_TOPIC
    score_data = orchestrator.calculate_niche_score()
    embed = discord.Embed(
        title=f"🎯 Đánh Giá Niche Scoring: {target_topic}",
        description=f"**Xếp hạng:** `{score_data['tier']}`\n**Điểm Cơ Hội:** `{score_data['score']}/100`\n\n"
                    f"**Chi tiết trọng số:**\n" +
                    "\n".join([f"• {k}: `{v}`/100" for k, v in score_data['metrics'].items()]),
        color=COLOR_ORCHESTRATOR
    )
    await interaction.followup.send(embed=embed)

async def handle_subagent_chat(bot: commands.Bot, message: discord.Message, agent_name: str, agent_role: str, agent_tone: str):
    """Xử lý trò chuyện khi bất kỳ thành viên nào tag hoặc reply vào 1 trong các bot con."""
    if message.author.bot:
        return

    bot_user = bot.user
    is_mentioned = bot_user and (bot_user in message.mentions)
    is_reply = False
    if message.reference and message.reference.resolved and isinstance(message.reference.resolved, discord.Message):
        if bot_user and message.reference.resolved.author.id == bot_user.id:
            is_reply = True

    is_dm = isinstance(message.channel, discord.DMChannel) or (message.guild is None)

    if is_dm or is_mentioned or is_reply:
        user_id = message.author.id
        user_text = message.clean_content.replace(f"@{bot.user.name}", "").strip() if bot_user else message.content.strip()
        if not user_text:
            user_text = "Chào em!"

        context_label = "DM" if is_dm else f"Kênh #{getattr(message.channel, 'name', 'server-channel')}"
        print(f"\n[{agent_name} {context_label}] 💬 @{message.author.name}: '{user_text}'", flush=True)

        async with message.channel.typing():
            system_prompt = f"""
Bạn là **{bot.user.name}** — chuyên gia **{agent_name}** trong hệ thống 5 AI Agent YouTube Niche **{NICHE_TOPIC}**.
VAI TRÒ: {agent_role}
TÍNH CÁCH: {agent_tone}

QUY TẮC BẮT BUỘC:
1. **SIÊU TỰ NHIÊN, CỰC GỌN GÀNG (TỐI ĐA 2 ĐOẠN NGẮN / DƯỚI 120 TỪ):**
   - Trả lời thẳng vào câu hỏi, không giải thích lan man, không dùng giọng văn mẫu robot.
   - Xưng "em", gọi người nói chuyện là "đại ca" hoặc "anh {message.author.name}".
2. **TRÌNH BÀY THOÁNG ĐÃNG:**
   - Cách 1 dòng trống (`\n\n`) giữa các ý. Dùng đầu mục rõ ràng `🔹 **[Ý chính]:** [Nội dung ngắn gọn]`.
   - Tránh các ký tự toán học khó đọc.
3. **DẪN CHỨNG & NGUỒN XÁC THỰC:**
   - Nếu giải thích về hiện tượng khoa học, số liệu hoặc cơ chế thực nghiệm, hãy đính kèm 1 link nguồn uy tín (Nature, Science, Khan Academy, MIT, Wikipedia...) để chứng minh.
4. **KẾT BÀI ĐÚNG TRỌNG TÂM:**
   - Đưa ra đúng 1 câu hỏi gợi mở trong quote block `> ` để đại ca quyết định tiếp.
"""
            llm_res = await llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"{message.author.name}: {user_text}"}
                ],
                temperature=0.7,
                max_tokens=400
            )
            reply_text = strip_think_tags(llm_res.get("content", f"Dạ em {agent_name} nghe đây ạ!"))

            # Ghi vào Database SQLite để hiển thị lên Web Dashboard
            channel_display_name = "Direct Message (DM)" if is_dm else f"#{getattr(message.channel, 'name', 'server-channel')}"
            chat_logger.log_chat(
                context_type="DM" if is_dm else "Channel",
                channel_name=channel_display_name,
                user_id=str(user_id),
                user_name=message.author.name,
                bot_name=bot.user.name,
                bot_role=agent_name,
                user_message=user_text,
                bot_response=reply_text
            )

            await message.reply(reply_text)
            print(f"[{agent_name} {context_label}] 📤 Phản hồi: {reply_text[:120]}...\n", flush=True)

    await bot.process_commands(message)

# =============================================================
# 2. NEWS / TREND AGENT (Bot Tin Tức - Giọng Nhanh Nhẹn, Hào Hứng)
# =============================================================
@news_bot.event
async def on_ready():
    print(f"[News Bot] [✅] Đăng nhập: {news_bot.user.name} (ID: {news_bot.user.id})", flush=True)
    await sync_bot_tree(news_bot, "News Bot")

@news_bot.event
async def on_message(message: discord.Message):
    await handle_subagent_chat(
        bot=news_bot,
        message=message,
        agent_name="News Agent",
        agent_role="Săn lùng tin tức nóng hổi, các sự kiện phóng tên lửa SpaceX, phát hiện thiên văn mới từ kính James Webb/NASA.",
        agent_tone="Nhanh nhẹn, hào hứng, nhiệt huyết, cập nhật tin tức cực nhanh, luôn dùng các icon lửa cháy 📰🔥."
    )

@news_bot.tree.command(name="start", description="[News Agent] Chào hỏi nhanh, kiểm tra bot hoạt động")
async def news_start_cmd(interaction: discord.Interaction):
    bot_name = news_bot.user.name if news_bot.user else "News Agent"
    user_mention = f"<@{interaction.user.id}>"
    await interaction.response.send_message(
        f"📰🔥 **[{bot_name}]**: Hú le đại ca {user_mention}! Em **News Agent** đây, đang hóng hớt tin tức **{NICHE_TOPIC}** nóng hổi 24/7, cần quét trend gì đại ca cứ dùng `/trend` hoặc `/hot_topics` nhé!"
    )

@news_bot.tree.command(name="trend", description="[News Agent] Quét tin tức và xu hướng khoa học mới nổi 30 ngày qua")
@app_commands.describe(topic=f"Từ khóa cần quét tin tức (mặc định: '{NICHE_TOPIC}')")
async def trend_command(interaction: discord.Interaction, topic: Optional[str] = None):
    await interaction.response.defer()
    search_query = topic or f"{NICHE_TOPIC} new discovery 2024"
    from services.search_service import SearchService
    results = await SearchService.search_news(query=search_query, max_results=5, timelimit="m")
    
    embed = discord.Embed(
        title=f"🔥 [News Agent] Xu Hướng & Tin Tức Mới: {search_query}",
        description="Quét dữ liệu tin tức web trong phạm vi 30 ngày gần đây:",
        color=COLOR_NEWS
    )
    if results:
        for item in results[:5]:
            embed.add_field(
                name=item.get("title", "Tin tức")[:100],
                value=f"{item.get('snippet', '')[:180]}...\n[Đọc thêm nguồn]({item.get('url')})",
                inline=False
            )
    else:
        embed.description = f"Không tìm thấy bài viết tin tức mới nào cho từ khóa `{search_query}`."

    embed.set_footer(text=f"Tin tức cập nhật lúc {datetime.now().strftime('%H:%M:%S')}")
    await interaction.followup.send(embed=embed)

@news_bot.tree.command(name="hot_topics", description="[News Agent] Quét và trích xuất danh sách chủ đề khoa học đang viral")
async def hot_topics_command(interaction: discord.Interaction):
    await interaction.response.defer()
    res = await news_agent.run()
    topics = res.get("hot_topics", [])
    embed = discord.Embed(
        title=f"⚡ [News Agent] Danh Sách Hot Topics Về '{NICHE_TOPIC}'",
        description="\n".join([f"🔥 **{i+1}. {t}**" for i, t in enumerate(topics)]) if topics else "Không trích xuất được hot topics.",
        color=COLOR_NEWS
    )
    embed.add_field(name="Tóm tắt nhận định", value=res.get("content", "")[:350] or "Đã tổng hợp tin tức.")
    await interaction.followup.send(embed=embed)

# =============================================================
# 3. MARKET / COMPETITOR AGENT (Bot Đối Thủ - Giọng Phân Tích, Số Liệu)
# =============================================================
@market_bot.event
async def on_ready():
    print(f"[Market Bot] [✅] Đăng nhập: {market_bot.user.name} (ID: {market_bot.user.id})", flush=True)
    await sync_bot_tree(market_bot, "Market Bot")

@market_bot.event
async def on_message(message: discord.Message):
    await handle_subagent_chat(
        bot=market_bot,
        message=message,
        agent_name="Market Agent",
        agent_role="Săn video breakout, bóc tách chỉ số view/sub ratio, phân tích đối thủ YouTube, tìm kiếm khoảng trống nội dung.",
        agent_tone="Sắc bén, số liệu thực chiến, phân tích chuyên nghiệp, nhắm vào các kênh nhỏ đạt view khủng, dùng icon 📊🚀."
    )

@market_bot.tree.command(name="start", description="[Market Agent] Chào hỏi nhanh, kiểm tra bot hoạt động")
async def market_start_cmd(interaction: discord.Interaction):
    bot_name = market_bot.user.name if market_bot.user else "Market Agent"
    user_mention = f"<@{interaction.user.id}>"
    await interaction.response.send_message(
        f"📊🚀 **[{bot_name}]**: Kính chào đại ca {user_mention}. Em là **Market Agent**, radar bóc tách số liệu YouTube và săn video breakout kênh nhỏ view cao cho niche **{NICHE_TOPIC}** đã sẵn sàng!"
    )

@market_bot.tree.command(name="kichban", description="[Market Agent] Quét kênh hot/đang lên và viết kịch bản chi tiết kèm prompt video AI")
@app_commands.describe(
    topic="Chủ đề hoặc từ khóa video muốn làm (ví dụ: 'Bí ẩn hố đen', 'James Webb')",
    dinh_dang="Định dạng video: 'Shorts 60s (Dọc 9:16)' hoặc 'Video Dài (Ngang 16:9)'"
)
async def market_kichban_cmd(interaction: discord.Interaction, topic: Optional[str] = None, dinh_dang: Optional[str] = "Shorts 60s (Dọc 9:16)"):
    chosen_topic = topic or f"{NICHE_TOPIC}: Khám phá bứt phá mới"
    await interaction.response.send_message(f"📊🎬 **[Market Agent]**: Bật radar quét thị trường và viết kịch bản & prompt AI cho chủ đề: **'{chosen_topic}'** ({dinh_dang})! 🚀")
    await execute_script_generation(interaction.user, interaction.channel, topic=chosen_topic, format_type=dinh_dang)

@market_bot.tree.command(name="audit_channel", description="[Market Agent] Bóc tách toàn diện kênh YouTube (SEO, thẻ tag, và prompt tạo ảnh AI)")
@app_commands.describe(channel_url_or_handle="Link kênh YouTube hoặc @handle (ví dụ: https://www.youtube.com/@Kurzgesagt hoặc @Kurzgesagt)")
async def market_audit_cmd(interaction: discord.Interaction, channel_url_or_handle: str):
    await interaction.response.send_message(f"📊🔍 **[Market Agent]**: Đang bóc tách SEO, Thẻ Tags và DNA Kênh `{channel_url_or_handle}`... 🚀")
    await execute_channel_audit(interaction.user, interaction.channel, channel_input=channel_url_or_handle)

@market_bot.tree.command(name="market_search", description="[Market Agent] Tìm kiếm video YouTube có tín hiệu breakout (view/sub cao)")
@app_commands.describe(query=f"Từ khóa tìm kiếm trên YouTube (ví dụ: '{NICHE_TOPIC} giải thích', '{NICHE_KEYWORDS_HINT.split(',')[0]}')")
async def market_search_cmd(interaction: discord.Interaction, query: Optional[str] = None):
    await interaction.response.defer()
    search_query = query or f"{NICHE_TOPIC} bí ẩn"
    videos = await youtube_service.search_videos(query=search_query, order="viewCount", max_results=6)
    if not videos:
        await interaction.followup.send(f"Không tìm thấy video nào cho từ khóa `{search_query}` hoặc lỗi YouTube API.")
        return

    enriched = await youtube_service.get_video_stats_and_breakout(videos)
    embed = discord.Embed(
        title=f"📊 [Market Agent] Kết Quả YouTube Breakout: {search_query}",
        description="Danh sách video được xếp hạng theo tỷ lệ View / Subscriber:",
        color=COLOR_MARKET
    )
    for v in enriched[:5]:
        embed.add_field(
            name=f"🎬 {v.get('title')[:70]}",
            value=f"• Kênh: **{v.get('channel_title')}** (Subs: `{v.get('subscriber_count', 0):,}`)\n"
                  f"• Views: `{v.get('view_count', 0):,}` | Ratio: `{v.get('view_sub_ratio')}x`\n"
                  f"• Tín hiệu: **{v.get('breakout_tier')}** ➔ [Xem Video]({v.get('url')})",
            inline=False
        )
    await interaction.followup.send(embed=embed)

@market_bot.tree.command(name="video_stats", description="[Market Agent] Xem phân tích chỉ số chi tiết của 1 video YouTube qua ID/URL")
@app_commands.describe(video_url_or_id="URL hoặc Video ID (ví dụ: https://www.youtube.com/watch?v=dQw4w9WgXcQ)")
async def video_stats_cmd(interaction: discord.Interaction, video_url_or_id: str):
    await interaction.response.defer()
    import re
    vid_match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", video_url_or_id)
    vid_id = vid_match.group(1) if vid_match else video_url_or_id.strip()

    items = [{"video_id": vid_id, "channel_id": ""}]
    enriched = await youtube_service.get_video_stats_and_breakout(items)
    if not enriched or enriched[0].get("view_count", 0) == 0:
        await interaction.followup.send(f"Không thể lấy thông số cho video ID: `{vid_id}`.")
        return

    v = enriched[0]
    embed = discord.Embed(
        title=f"📈 [Market Agent] Phân Tích Chỉ Số Video",
        description=f"**[{v.get('title', 'Video')}]({v.get('url')})**",
        color=COLOR_MARKET
    )
    embed.add_field(name="Kênh YouTube", value=v.get("channel_title", "N/A"), inline=True)
    embed.add_field(name="Subscribers", value=f"`{v.get('subscriber_count', 0):,}`", inline=True)
    embed.add_field(name="Lượt Xem", value=f"`{v.get('view_count', 0):,}`", inline=True)
    embed.add_field(name="Lượt Like", value=f"`{v.get('like_count', 0):,}`", inline=True)
    embed.add_field(name="Breakout Ratio", value=f"`{v.get('view_sub_ratio')}x`", inline=True)
    embed.add_field(name="Đánh Giá Tín Hiệu", value=f"**{v.get('breakout_tier')}**", inline=True)
    
    if v.get("thumbnail_url"):
        embed.set_thumbnail(url=v.get("thumbnail_url"))
    await interaction.followup.send(embed=embed)

# =============================================================
# 4. THUMBNAIL AGENT (Bot Thumbnail - Giọng Sáng Tạo, Nghệ Sĩ, Thẩm Mỹ)
# =============================================================
@thumbnail_bot.event
async def on_ready():
    print(f"[Thumbnail Bot] [✅] Đăng nhập: {thumbnail_bot.user.name} (ID: {thumbnail_bot.user.id})", flush=True)
    await sync_bot_tree(thumbnail_bot, "Thumbnail Bot")

@thumbnail_bot.event
async def on_message(message: discord.Message):
    await handle_subagent_chat(
        bot=thumbnail_bot,
        message=message,
        agent_name="Thumbnail Agent",
        agent_role="Mổ xẻ thị giác, phân tích độ tương phản, bố cục 1/3, font chữ, tâm lý màu sắc, tạo 3 concept CTR kéo triệu view.",
        agent_tone="Sáng tạo, mắt nhìn nghệ thuật, gu thẩm mỹ cao, am hiểu visual tâm lý người xem, dùng icon 🎨✨."
    )

@thumbnail_bot.tree.command(name="start", description="[Thumbnail Agent] Chào hỏi nhanh, kiểm tra bot hoạt động")
async def thumb_start_cmd(interaction: discord.Interaction):
    bot_name = thumbnail_bot.user.name if thumbnail_bot.user else "Thumbnail Agent"
    user_mention = f"<@{interaction.user.id}>"
    await interaction.response.send_message(
        f"🎨✨ **[{bot_name}]**: Dạ em chào đại ca {user_mention}! **Thumbnail Specialist** đã có mặt, sẵn sàng soi màu sắc, độ tương phản và giải mã công thức CTR kéo triệu view cho niche **{NICHE_TOPIC}**!"
    )

@thumbnail_bot.tree.command(name="thumbnail_analyze", description="[Thumbnail Agent] Phân tích thị giác chi tiết một Thumbnail qua Image URL hoặc Video URL")
@app_commands.describe(url="URL ảnh thumbnail hoặc URL video YouTube")
async def thumb_analyze_cmd(interaction: discord.Interaction, url: str):
    await interaction.response.defer()
    import re
    img_url = url
    vid_match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", url)
    if vid_match:
        img_url = f"https://img.youtube.com/vi/{vid_match.group(1)}/maxresdefault.jpg"

    res = await llm_client.analyze_thumbnail(image_url=img_url, video_title="Video Analysis Request")
    embed = discord.Embed(
        title=f"🎨 [Thumbnail Agent] Phân Tích Thiết Kế & Điểm Nhấn CTR ({NICHE_TOPIC})",
        description=res.get("content", "Đã phân tích cấu trúc thumbnail.")[:1000],
        color=COLOR_THUMBNAIL
    )
    embed.set_image(url=img_url)
    await interaction.followup.send(embed=embed)

@thumbnail_bot.tree.command(name="thumbnail_ideas", description="[Thumbnail Agent] Gợi ý 3 concept thiết kế thumbnail CTR cao cho video")
@app_commands.describe(topic=f"Chủ đề hoặc tựa đề video bạn định làm (mặc định: '{NICHE_TOPIC}')")
async def thumb_ideas_cmd(interaction: discord.Interaction, topic: Optional[str] = None):
    await interaction.response.defer()
    target_topic = topic or f"{NICHE_TOPIC}: Sự thật kinh ngạc về Vũ Trụ"
    prompt = f"Gợi ý 3 concept thiết kế Thumbnail YouTube tỷ lệ nhấp chuột (CTR) cực cao cho chủ đề: '{target_topic}' trong niche '{NICHE_TOPIC}'. Bao gồm: Text ngắn gọn (dưới 4 từ), phối màu tương phản, bố cục hình ảnh chủ thể và điểm hút ánh nhìn."
    res = await llm_client.chat_completion(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=800
    )
    embed = discord.Embed(
        title=f"💡 [Thumbnail Agent] 3 Ý Tưởng Thumbnail: {target_topic}",
        description=strip_think_tags(res.get("content", "Không có nội dung.")),
        color=COLOR_THUMBNAIL
    )
    await interaction.followup.send(embed=embed)

@thumbnail_bot.tree.command(name="audit_channel", description="[Thumbnail Agent] Bóc tách phong cách Thumbnail & viết 3 Prompt AI sao chép kênh đối thủ")
@app_commands.describe(channel_url_or_handle="Link kênh YouTube hoặc @handle (ví dụ: https://www.youtube.com/@Kurzgesagt hoặc @Kurzgesagt)")
async def thumb_audit_cmd(interaction: discord.Interaction, channel_url_or_handle: str):
    await interaction.response.send_message(f"🎨🔍 **[Thumbnail Agent]**: Đang bóc tách DNA Thumbnail & viết bộ Prompt AI cho kênh `{channel_url_or_handle}`... 🚀")
    await execute_channel_audit(interaction.user, interaction.channel, channel_input=channel_url_or_handle)

@thumbnail_bot.tree.command(name="ve_anh", description="[Thumbnail Agent] Tự viết Prompt AI & vẽ ảnh minh họa/thumbnail chuẩn 4K")
@app_commands.describe(
    chu_de="Chủ đề hoặc ý tưởng ảnh (ví dụ: Cận cảnh giọt nước đóng băng phát sáng)",
    phong_cach="Phong cách ảnh mong muốn",
    ty_le="Tỷ lệ khung hình"
)
@app_commands.choices(
    phong_cach=[
        app_commands.Choice(name="3D Cinematic Masterpiece", value="3D Cinematic Masterpiece"),
        app_commands.Choice(name="Mặt Cắt Siêu Thực (Cross-section)", value="Cross-section Sci-fi"),
        app_commands.Choice(name="Tương Phản Nhiệt (Thermal Contrast)", value="Thermal Contrast"),
        app_commands.Choice(name="Kính Hiển Vi Phóng Đại (Microscopic 1000x)", value="Microscopic 1000x")
    ],
    ty_le=[
        app_commands.Choice(name="16:9 (Ngang - Video Dài & Thumbnail)", value="16:9"),
        app_commands.Choice(name="9:16 (Dọc - Shorts / TikTok / Reels)", value="9:16")
    ]
)
async def thumb_ve_anh_cmd(interaction: discord.Interaction, chu_de: str, phong_cach: Optional[app_commands.Choice[str]] = None, ty_le: Optional[app_commands.Choice[str]] = None):
    style_val = phong_cach.value if phong_cach else "3D Cinematic Masterpiece"
    ratio_val = ty_le.value if ty_le else "16:9"
    await interaction.response.send_message(f"🎨 **[Thumbnail Agent Flow]**: Đang tối ưu Prompt & bắt đầu vẽ ảnh `{chu_de}`... 🚀")
    await execute_image_generation(interaction.user, interaction.channel, prompt_or_idea=chu_de, style=style_val, aspect_ratio=ratio_val)

# =============================================================
# 5. MONITOR BOT (Bot Giám Sát - Giọng Kế Toán, Chuẩn Xác)
# =============================================================
@tasks.loop(minutes=2)
async def quota_auto_alert_task():
    """Tự động kiểm tra định kỳ và phát cảnh báo nếu Quota xuống dưới 20%."""
    summary = quota_tracker.get_quota_summary(provider=LLM_PROVIDER)
    is_low_yt = summary["yt_pct_remaining"] <= 20.0
    is_low_llm = summary["llm_remaining_requests"] is not None and summary["llm_remaining_requests"] <= 20

    if (is_low_yt or is_low_llm) and not quota_tracker.yt_warned_today:
        quota_tracker.yt_warned_today = True
        print(f"\n[Quota Monitor] 🚨 PHÁT HIỆN HẠN MỨC API XUỐNG DƯỚI 20%! Đang phát cảnh báo...", flush=True)

        warn_embed = discord.Embed(
            title="🚨 [Quota Monitor] CẢNH BÁO: HẠN MỨC API ĐÃ DƯỚI 20%!",
            description="**Hệ thống ghi nhận hạn mức API sắp cạn kiệt.** Vui lòng hạn chế các lệnh phân tích lớn để tránh bị gián đoạn.",
            color=COLOR_ERROR
        )
        warn_embed.add_field(
            name="📹 YouTube Data API v3",
            value=f"• Còn lại: `{summary['yt_remaining']:,}` / `{summary['yt_limit']:,}` units (**{summary['yt_pct_remaining']:.1f}%**)\n"
                  f"• ⏰ **Thời gian Reset:** `{summary['yt_reset_time_vn']}`\n"
                  f"• ⏳ **Đếm ngược:** Còn `{summary['yt_countdown']}`",
            inline=False
        )
        if summary['llm_remaining_requests'] is not None:
            warn_embed.add_field(
                name="🧠 LLM Provider",
                value=f"• Requests còn lại: `{summary['llm_remaining_requests']}` requests\n"
                      f"• Reset sau: `{summary['llm_reset_time'] or 'Theo phút'}`",
                inline=False
            )
        warn_embed.set_footer(text=f"Kiểm toán tự động lúc {datetime.now().strftime('%H:%M:%S')}")

        # Gửi cảnh báo vào Channel chung
        if DISCORD_CHANNEL_ID:
            try:
                ch = monitor_bot.get_channel(DISCORD_CHANNEL_ID) or await monitor_bot.fetch_channel(DISCORD_CHANNEL_ID)
                if ch:
                    await ch.send(embed=warn_embed)
            except Exception as e:
                print(f"[Quota Monitor] Không thể gửi cảnh báo vào channel: {e}", flush=True)

        # Gửi cảnh báo trực tiếp qua DM cho Đại Ca
        if OWNER_DISCORD_USER_ID:
            try:
                owner = monitor_bot.get_user(OWNER_DISCORD_USER_ID) or await monitor_bot.fetch_user(OWNER_DISCORD_USER_ID)
                if owner:
                    await owner.send(
                        content=f"🚨 **Báo cáo khẩn cấp:** Hạn mức Quota YouTube API của hệ thống đã xuống dưới 20%!",
                        embed=warn_embed
                    )
            except Exception as e:
                print(f"[Quota Monitor] Không thể gửi DM cảnh báo cho Đại Ca: {e}", flush=True)

@monitor_bot.event
async def on_ready():
    print(f"[Monitor Bot] [✅] Đăng nhập: {monitor_bot.user.name} (ID: {monitor_bot.user.id})", flush=True)
    await sync_bot_tree(monitor_bot, "Monitor Bot")
    if not quota_auto_alert_task.is_running():
        quota_auto_alert_task.start()
        print(f"[Quota Monitor] Đã kích hoạt vòng lặp giám sát hạn mức tự động (< 20%).", flush=True)

@monitor_bot.event
async def on_message(message: discord.Message):
    await handle_subagent_chat(
        bot=monitor_bot,
        message=message,
        agent_name="Quota Monitor",
        agent_role="Kiểm toán hạn mức API 24/7, theo dõi chi phí tokens, đếm ngược thời gian reset YouTube/LLM, bảo vệ an toàn hệ thống.",
        agent_tone="Kế toán chuẩn xác, cẩn thận, chi tiết, nhắc nhở bảo vệ hạn mức, dùng icon 🛡️📈."
    )

@monitor_bot.tree.command(name="start", description="[Monitor Bot] Chào hỏi nhanh, kiểm tra bot hoạt động")
async def monitor_start_cmd(interaction: discord.Interaction):
    bot_name = monitor_bot.user.name if monitor_bot.user else "Quota Monitor"
    user_mention = f"<@{interaction.user.id}>"
    await interaction.response.send_message(
        f"🛡️📈 **[{bot_name}]**: Báo cáo đại ca {user_mention}: **Quota Monitor** đang túc trực 24/7, kiểm soát từng unit API và theo dõi an toàn toàn bộ hệ thống!"
    )

@monitor_bot.tree.command(name="quota", description="[Monitor Bot] Xem hạn mức API và thời gian Reset tiếp theo")
async def quota_command(interaction: discord.Interaction):
    summary = quota_tracker.get_quota_summary(provider=LLM_PROVIDER)
    embed = discord.Embed(
        title="📊 [Quota Monitor] Tình Trạng Hạn Mức API & Thời Gian Reset",
        description="Theo dõi chi tiết số lượng request, hạn mức khả dụng và thời gian reset trong ngày:",
        color=COLOR_MONITOR
    )
    
    # YouTube API
    yt_status_icon = "🟢 An Toàn" if summary['yt_pct_remaining'] > 20 else "🔴 Cảnh Báo"
    yt_text = (
        f"• **Trạng thái:** {yt_status_icon}\n"
        f"• **Đã dùng:** `{summary['yt_used']:,}` / `{summary['yt_limit']:,}` units\n"
        f"• **Còn lại:** `{summary['yt_remaining']:,}` units (**{summary['yt_pct_remaining']:.1f}%**)\n"
        f"• ⏰ **Thời gian Reset tiếp theo:** `{summary['yt_reset_time_vn']}`\n"
        f"• ⏳ **Đếm ngược:** Còn **`{summary['yt_countdown']}`**"
    )
    embed.add_field(name="📹 YouTube Data API v3", value=yt_text, inline=False)
    
    # LLM API (Groq)
    llm_status_icon = "🟢 An Toàn" if summary['llm_requests_pct'] > 20 else "🔴 Cảnh Báo"
    llm_text = (
        f"• **Provider:** `{summary['llm_provider'].upper()} (openai/gpt-oss-120b)`\n"
        f"• **Trạng thái:** {llm_status_icon}\n"
        f"• **Requests (RPM):** `{summary['llm_remaining_requests']}` / `{summary['llm_limit_requests']}` RPM (**{summary['llm_requests_pct']}%**)\n"
        f"• **Tokens (TPM):** `{summary['llm_remaining_tokens']:,}` / `{summary['llm_limit_tokens']:,}` TPM (**{summary['llm_tokens_pct']}%**)\n"
        f"• **Tổng tokens đã dùng hôm nay:** `{summary['llm_total_tokens']:,}` tokens\n"
        f"• **Tổng calls:** `{summary['llm_total_requests']}` calls\n"
        f"• ⏰ **Reset tốc độ:** `{summary['llm_reset_requests']}`"
    )
    embed.add_field(name="🧠 Groq AI API (Rate Limits)", value=llm_text, inline=False)

    # Google Gemini & Flow Studio
    if summary.get('gemini_active'):
        gemini_text = (
            f"• **Model:** `Google Gemini 3.6 Flash & Flow Studio`\n"
            f"• **Trạng thái:** 🟢 Đang Kết Nối\n"
            f"• **Hạn mức ngày (RPD):** `{summary['gemini_remaining']:,}` / `{summary['gemini_daily_limit']:,}` RPD (**{summary['gemini_pct_remaining']}%**)\n"
            f"• **Tốc độ xử lý (Latency):** `{summary['gemini_last_latency_ms']} ms` (TB: `{summary['gemini_avg_latency_ms']} ms`)\n"
            f"• **Ảnh Flow đã xuất:** `{summary['gemini_flow_images_generated']}` ảnh 4K\n"
            f"• **Tổng Gemini Calls:** `{summary['gemini_total_requests']}` calls\n"
            f"• 🕒 **Dùng gần nhất:** `{summary['gemini_last_used']}`"
        )
        embed.add_field(name="🧬 Google Gemini & Flow Engine", value=gemini_text, inline=False)
    
    embed.set_footer(text=f"Kiểm toán lúc {datetime.now().strftime('%H:%M:%S')} | Web Dashboard: http://localhost:8080")
    await interaction.response.send_message(embed=embed)

@monitor_bot.tree.command(name="quota_alert_test", description="[Monitor Bot] Kiểm tra mẫu thông báo cảnh báo khi Quota xuống dưới 20%")
async def quota_alert_test_cmd(interaction: discord.Interaction):
    summary = quota_tracker.get_quota_summary(provider=LLM_PROVIDER)
    test_embed = discord.Embed(
        title="🚨 [TEST] CẢNH BÁO HẠN MỨC API DƯỚI 20%",
        description="*(Đây là tin nhắn mô phỏng cảnh báo tự động khi Quota YouTube hoặc LLM xuống dưới 20%)*",
        color=COLOR_ERROR
    )
    test_embed.add_field(
        name="📹 YouTube Data API v3",
        value=f"• Còn lại: `{summary['yt_remaining']:,}` / `{summary['yt_limit']:,}` units (**{summary['yt_pct_remaining']:.1f}%**)\n"
              f"• ⏰ **Thời gian Reset tiếp theo:** `{summary['yt_reset_time_vn']}`\n"
              f"• ⏳ **Đếm ngược:** Còn **`{summary['yt_countdown']}`**",
        inline=False
    )
    test_embed.set_footer(text="Mô phỏng cảnh báo Quota | Tự động kích hoạt khi < 20%")
    await interaction.response.send_message(embed=test_embed)

@monitor_bot.tree.command(name="system_status", description="[Monitor Bot] Kiểm tra sức khỏe kết nối của 5 bot và các API keys")
async def system_status_cmd(interaction: discord.Interaction):
    llm_ok, llm_msg = llm_client.test_connection()
    yt_ok, yt_msg = youtube_service.test_connection()
    
    embed = discord.Embed(
        title="🛡️ [Monitor Bot] Báo Cáo Sức Khỏe Toàn Bộ Hệ Thống",
        description="Kiểm tra trạng thái sẵn sàng của 5 Discord Bot và các API liên kết:",
        color=COLOR_MONITOR
    )
    embed.add_field(
        name="🧠 LLM Provider",
        value=f"{'✅ Hoạt động' if llm_ok else '❌ Lỗi'}: {llm_msg}",
        inline=False
    )
    embed.add_field(
        name="📹 YouTube Data API",
        value=f"{'✅ Hoạt động' if yt_ok else '❌ Lỗi'}: {yt_msg}",
        inline=False
    )
    embed.add_field(
        name="🤖 5 Discord Bots",
        value=f"• 1. Orchestrator: `{'Online' if orch_bot.is_ready() else 'Offline'}`\n"
              f"• 2. News Agent: `{'Online' if news_bot.is_ready() else 'Offline'}`\n"
              f"• 3. Market Agent: `{'Online' if market_bot.is_ready() else 'Offline'}`\n"
              f"• 4. Thumbnail Agent: `{'Online' if thumbnail_bot.is_ready() else 'Offline'}`\n"
              f"• 5. Quota Monitor: `{'Online' if monitor_bot.is_ready() else 'Offline'}`",
        inline=False
    )
    embed.add_field(
        name=f"🌌 Niche Hiện Tại",
        value=f"• **Chủ đề:** `{NICHE_TOPIC}`\n"
              f"• **Keywords:** `{NICHE_KEYWORDS_HINT}`\n"
              f"• **Lịch tự động:** `{DAILY_RUN_TIME}` ({'Bật' if DAILY_RUN_ENABLED else 'Tắt'})\n"
              f"• **DM Recipient:** `{RECIPIENT_DISCORD_USER_ID or 'Chưa cấu hình'}`",
        inline=False
    )
    await interaction.response.send_message(embed=embed)

@monitor_bot.tree.command(name="ping", description="[Monitor Bot] Kiểm tra độ trễ (latency) của các bot")
async def ping_cmd(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🏓 Pong! Độ Trễ Của Hệ Thống Bot",
        description=f"• **Orchestrator Bot:** `{round(orch_bot.latency * 1000)}ms`\n"
                    f"• **News Bot:** `{round(news_bot.latency * 1000)}ms`\n"
                    f"• **Market Bot:** `{round(market_bot.latency * 1000)}ms`\n"
                    f"• **Thumbnail Bot:** `{round(thumbnail_bot.latency * 1000)}ms`\n"
                    f"• **Monitor Bot:** `{round(monitor_bot.latency * 1000)}ms`",
        color=COLOR_MONITOR
    )
    await interaction.response.send_message(embed=embed)

# -------------------------------------------------------------
# MAIN ASYNC ENTRYPOINT
# -------------------------------------------------------------
async def main():
    run_startup_checks()
    tasks_list = []

    print("[Bots Status] Đang kết nối các bot Discord...", flush=True)
    if DISCORD_ORCHESTRATOR_TOKEN:
        tasks_list.append(orch_bot.start(DISCORD_ORCHESTRATOR_TOKEN))
    if DISCORD_NEWS_TOKEN:
        tasks_list.append(news_bot.start(DISCORD_NEWS_TOKEN))
    if DISCORD_MARKET_TOKEN:
        tasks_list.append(market_bot.start(DISCORD_MARKET_TOKEN))
    if DISCORD_THUMBNAIL_TOKEN:
        tasks_list.append(thumbnail_bot.start(DISCORD_THUMBNAIL_TOKEN))
    if DISCORD_MONITOR_TOKEN:
        tasks_list.append(monitor_bot.start(DISCORD_MONITOR_TOKEN))

    # Khởi chạy Web Dashboard Server (http://localhost:5000)
    try:
        await start_dashboard_server(host="0.0.0.0", port=5000)
    except Exception as d_err:
        print(f"[Dashboard Server] Không thể khởi động Web Dashboard: {d_err}", flush=True)

    try:
        await asyncio.gather(*tasks_list)
    except KeyboardInterrupt:
        print("\nĐang tắt hệ thống bot...", flush=True)
    except Exception as e:
        print(f"Lỗi khi chạy bot: {e}", flush=True)

if __name__ == "__main__":
    if "--check-only" in sys.argv:
        run_startup_checks()
    else:
        asyncio.run(main())
