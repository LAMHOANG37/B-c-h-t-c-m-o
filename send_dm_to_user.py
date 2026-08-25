import asyncio
import sys
import discord
from config import DISCORD_ORCHESTRATOR_TOKEN, NICHE_TOPIC, COLOR_ORCHESTRATOR

USER_ID = 669194207713427486

async def send_intro_dm():
    if not DISCORD_ORCHESTRATOR_TOKEN:
        print("❌ Thiếu DISCORD_ORCHESTRATOR_TOKEN trong .env")
        return

    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"[Orchestrator] [✅] Đã kết nối bot: {client.user.name}")
        try:
            user = await client.fetch_user(USER_ID)
            print(f"[Orchestrator] Tìm thấy người dùng: {user.name}#{user.discriminator} (ID: {user.id})")

            embed = discord.Embed(
                title=f"👑 [Orchestrator] Kính Chào Đại Ca! Em Đã Vào Vị Trí",
                description=f"Dạ em chào đại ca <@{user.id}>! Em là **{client.user.name}** — **Anh cả điều phối** của hệ thống 5 AI Agent.\n\n"
                            f"🌌 **Chuyên môn hiện tại:** Nghiên cứu thị trường YouTube Niche **{NICHE_TOPIC}**.\n"
                            f"🤖 **4 Anh em dưới quyền em:**\n"
                            f"• 📰 **News Agent:** Quét tin tức & xu hướng vũ trụ 30 ngày gần nhất.\n"
                            f"• 📊 **Market Agent:** Săn video breakout, bóc tách chỉ số kênh nhỏ view cao.\n"
                            f"• 🎨 **Thumbnail Agent:** Mổ xẻ thị giác, tạo 3 công thức CTR triệu view.\n"
                            f"• 🛡️ **Quota Monitor:** Kiểm toán hạn mức API 24/7.\n\n"
                            f"💬 **Đại ca cứ nhắn tin trực tiếp vào đây với em**, em có thể tư vấn ý tưởng video, đàm đạo chiến lược, hoặc nhận lệnh từ đại ca bất cứ lúc nào!",
                color=COLOR_ORCHESTRATOR
            )
            embed.set_footer(text=f"Hệ thống sẵn sàng | Gõ /help để xem danh sách lệnh")

            msg = await user.send(
                content=f"👋 Dạ đại ca <@{user.id}> ơi! Em **Orchestrator** chủ động nhắn riêng để chào đại ca và nhận lệnh đây ạ!",
                embed=embed
            )
            print(f"[Orchestrator] [🎉 THÀNH CÔNG] Đã gửi tin nhắn chủ động tới đại ca {user.name} (ID: {USER_ID})!")
        except discord.Forbidden:
            print(f"[Orchestrator] [⚠️ THẤT BẠI] User {USER_ID} đã tắt tính năng nhận DM từ thành viên server!")
        except Exception as e:
            print(f"[Orchestrator] [❌ LỖI] {e}")
        finally:
            await client.close()

    await client.start(DISCORD_ORCHESTRATOR_TOKEN)

if __name__ == "__main__":
    asyncio.run(send_intro_dm())
