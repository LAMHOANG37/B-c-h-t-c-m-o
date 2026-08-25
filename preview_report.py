import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Đảm bảo UTF-8 trên Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import (
    NICHE_TOPIC,
    NICHE_KEYWORDS_HINT,
    DAILY_RUN_ENABLED,
    DAILY_RUN_TIME,
    DAILY_RUN_TIMEZONE,
    RECIPIENT_DISCORD_USER_ID,
    DISCORD_ORCHESTRATOR_TOKEN,
    COLOR_ORCHESTRATOR
)
from agents.orchestrator import orchestrator
from agents.prompts import (
    get_news_agent_prompt,
    get_market_agent_prompt,
    get_thumbnail_agent_prompt,
    get_orchestrator_synthesis_prompt
)

def print_terminal_preview():
    score_data = orchestrator.calculate_niche_score()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    print("\n" + "=" * 80)
    print(" 🚀 BẢNG ĐIỀU KHIỂN & KIỂM SOÁT BÁO CÁO TỰ ĐỘNG CỦA BOT (TERMINAL PREVIEW)")
    print("=" * 80)
    print(f"📌 Chủ đề phân tích (Niche):      {NICHE_TOPIC}")
    print(f"🔑 Từ khóa gợi ý:                 {NICHE_KEYWORDS_HINT}")
    print(f"⏰ Lịch chạy tự động:             {DAILY_RUN_TIME} ({DAILY_RUN_TIMEZONE}) — Trạng thái: {'BẬT' if DAILY_RUN_ENABLED else 'TẮT'}")
    print(f"👤 Người nhận tin nhắn DM:        ID: {RECIPIENT_DISCORD_USER_ID or 'Chưa cấu hình'}")
    print("=" * 80)

    print("\n┌──────────────────────────────────────────────────────────────────────────────┐")
    print("│ 📬 NỘI DUNG TIN NHẮN RIÊNG (DM) ORCHESTRATOR BOT SẼ GỬI CHO ANH BÌNH         │")
    print("├──────────────────────────────────────────────────────────────────────────────┤")
    print(f"│ 👑 Tin nhắn text mở đầu:")
    print(f"│   '👋 Báo cáo nghiên cứu tự động hàng ngày: {NICHE_TOPIC} (Dành riêng cho <@{RECIPIENT_DISCORD_USER_ID}>)'")
    print("│")
    print(f"│ 🏆 Tiêu đề Embed:")
    print(f"│   '🏆 [Orchestrator] BÁO CÁO CHIẾN LƯỢC: NICHE {NICHE_TOPIC.upper()}'")
    print("│")
    print("│ 📊 Thang điểm & Xếp hạng:")
    print(f"│   • Xếp hạng:  {score_data['tier']}")
    print(f"│   • Điểm Cơ Hội: {score_data['score']}/100 (Điểm chính xác dựa trên 9 trọng số)")
    print("│")
    print("│ 💡 3 Key Takeaways Chiến Lược Cho Bạn:")
    print(f"│   1. Demand & Xu hướng: Nhu cầu tìm kiếm cao về các chủ đề bùng nổ ({NICHE_KEYWORDS_HINT.split(',')[0].strip()}).")
    print(f"│   2. Breakout Signal: Kênh nhỏ có thể bứt phá mạnh nếu tập trung vào góc nhìn độc lạ, giải thích trực quan.")
    print(f"│   3. CTR Mastery: Áp dụng màu tương phản cao + chủ thể cận cảnh nổi bật + text ngắn dưới 4 từ.")
    print("│")
    print("│ 📄 File đính kèm:")
    print(f"│   • report_{datetime.now().strftime('%Y-%m-%d_%H%M')}.md (Chứa báo cáo chuyên sâu 5 phần đầy đủ)")
    print("└──────────────────────────────────────────────────────────────────────────────┘\n")

    print("=" * 80)
    print(" 🤖 CÁCH CÁC BOT KHÁC SẼ NHẬP VAI VÀ PHẢN HỒI (GIỌNG ĐIỆU RIÊNG)")
    print("=" * 80)
    print(f"1. 👑 Orchestrator Bot:    Điềm tĩnh, chỉn chu ➔ Điều phối 3 agent & tổng hợp báo cáo chiến lược")
    print(f"2. 📰 News Agent:          Hào hứng, nhanh nhẹn ➔ '📰 Bắt được trend nóng hổi về {NICHE_TOPIC} rồi đại ca ơi!'")
    print(f"3. 📊 Market Agent:        Chắc chắn, số liệu ➔ '🚀 Số liệu không biết nói dối — Top Video Breakout đây!'")
    print(f"4. 🎨 Thumbnail Agent:     Sáng tạo, thẩm mỹ  ➔ '🎯 Đã giải mã 3 công thức CTR triệu view cho {NICHE_TOPIC}!'")
    print(f"5. 🛡️ Quota Monitor:       Kế toán, chuẩn xác ➔ '🛡️ Báo cáo kiểm toán hạn mức sau phiên chạy'")
    print("=" * 80 + "\n")

async def send_live_test_dm():
    if not RECIPIENT_DISCORD_USER_ID or not DISCORD_ORCHESTRATOR_TOKEN:
        print("❌ Thiếu RECIPIENT_DISCORD_USER_ID hoặc DISCORD_ORCHESTRATOR_TOKEN trong .env.")
        return

    import discord
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"\n[Test DM] [✅] Đã đăng nhập bot: {client.user.name}")
        try:
            user = await client.fetch_user(RECIPIENT_DISCORD_USER_ID)
            print(f"[Test DM] Tìm thấy người nhận: {user.name}#{user.discriminator} (ID: {user.id})")

            score_data = orchestrator.calculate_niche_score()
            embed = discord.Embed(
                title=f"🧪 [TEST] BÁO CÁO NGHIÊN CỨU MẪU: NICHE {NICHE_TOPIC.upper()}",
                description=f"*Đây là tin nhắn kiểm tra kết nối từ Orchestrator Bot:*\n\n"
                            f"**Xếp hạng:** `{score_data['tier']}`\n**Điểm Cơ Hội:** `{score_data['score']}/100`\n\n"
                            f"**3 Key Takeaways Chiến Lược:**\n"
                            f"1. **Demand & Xu hướng:** Sự bùng nổ của các chủ đề {NICHE_TOPIC}.\n"
                            f"2. **Breakout Signal:** Cơ hội lớn cho kênh nhỏ bứt phá view.\n"
                            f"3. **CTR Mastery:** Công thức Thumbnail màu tương phản cao.",
                color=COLOR_ORCHESTRATOR
            )
            embed.set_footer(text=f"Bản test kết nối | Lịch tự động sẽ chạy vào {DAILY_RUN_TIME} hàng ngày")

            await user.send(
                content=f"👋 Xin chào <@{user.id}>! Đây là bản tin nhắn thử nghiệm từ **Orchestrator Bot** trước giờ phát báo cáo tự động lúc `{DAILY_RUN_TIME}`.",
                embed=embed
            )
            print(f"[Test DM] [🎉 THÀNH CÔNG] Đã gửi tin nhắn test qua DM tới {user.name}!")
        except discord.Forbidden:
            print(f"[Test DM] [⚠️ THẤT BẠI] Người nhận (ID: {RECIPIENT_DISCORD_USER_ID}) đã tắt tính năng nhận DM từ server!")
        except Exception as e:
            print(f"[Test DM] [❌ LỖI] {e}")
        finally:
            await client.close()

    await client.start(DISCORD_ORCHESTRATOR_TOKEN)

if __name__ == "__main__":
    if "--send-test" in sys.argv:
        asyncio.run(send_live_test_dm())
    else:
        print_terminal_preview()
