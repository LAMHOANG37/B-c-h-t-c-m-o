import io
import json
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
import discord
from config import (
    REPORTS_DIR,
    NICHE_TOPIC,
    COLOR_ORCHESTRATOR,
    COLOR_NEWS,
    COLOR_MARKET,
    COLOR_THUMBNAIL,
    COLOR_MONITOR,
    COLOR_ERROR,
    COLOR_WARNING,
)
from agents.prompts import get_orchestrator_synthesis_prompt
from agents.news_agent import news_agent
from agents.market_agent import market_agent
from agents.thumbnail_agent import thumbnail_agent
from services.llm_client import llm_client, strip_think_tags
from services.quota_tracker import quota_tracker

class Orchestrator:
    def __init__(self):
        pass

    def calculate_niche_score(
        self,
        demand: float = 85.0,
        growth: float = 80.0,
        competition: float = 70.0,
        content_depth: float = 75.0,
        monetization: float = 85.0,
        content_gap: float = 75.0,
        production_feasibility: float = 80.0,
        scalability: float = 85.0,
        risk: float = 70.0
    ) -> Dict[str, Any]:
        """
        Tính toán Niche Score theo công thức chuẩn:
        Final Score = Demand*0.20 + Growth*0.10 + Competition*0.15 + ContentDepth*0.15
                    + Monetization*0.15 + ContentGap*0.10 + ProductionFeasibility*0.05
                    + Scalability*0.05 + Risk*0.05
        """
        final_score = (
            (demand * 0.20) +
            (growth * 0.10) +
            (competition * 0.15) +
            (content_depth * 0.15) +
            (monetization * 0.15) +
            (content_gap * 0.10) +
            (production_feasibility * 0.05) +
            (scalability * 0.05) +
            (risk * 0.05)
        )
        final_score = round(final_score, 1)

        if final_score >= 85:
            tier = "Tier S (Cực Kỳ Tiềm Năng)"
        elif final_score >= 75:
            tier = "Tier A (Rất Tốt)"
        elif final_score >= 60:
            tier = "Tier B (Khả Thi)"
        elif final_score >= 45:
            tier = "Tier C (Trung Bình / Cạnh Tranh Cao)"
        else:
            tier = "Tier D (Rủi Ro Cao)"

        return {
            "score": final_score,
            "tier": tier,
            "metrics": {
                "Demand (20%)": demand,
                "Growth (10%)": growth,
                "Competition (15%)": competition,
                "Content Depth (15%)": content_depth,
                "Monetization (15%)": monetization,
                "Content Gap (10%)": content_gap,
                "Production Feasibility (5%)": production_feasibility,
                "Scalability (5%)": scalability,
                "Risk (5%)": risk
            }
        }

    async def run_pipeline(
        self,
        thread: Optional[discord.Thread] = None,
        dm_recipient: Optional[discord.User] = None,
        recipients: Optional[List[discord.User]] = None,
        custom_focus_topic: Optional[str] = None,
        custom_angle_summary: Optional[str] = None,
        news_bot: Optional[discord.Client] = None,
        market_bot: Optional[discord.Client] = None,
        thumbnail_bot: Optional[discord.Client] = None,
        monitor_bot: Optional[discord.Client] = None
    ) -> Dict[str, Any]:
        """
        Điều phối tuần tự 3 ReAct sub-agents, đánh giá dữ liệu, chấm điểm và gửi báo cáo vào Discord Thread hoặc DM.
        """
        quota_tracker.start_session()
        start_time = datetime.now()
        active_niche = custom_focus_topic or NICHE_TOPIC
        synthesis_prompt = get_orchestrator_synthesis_prompt(active_niche)

        # Danh sách người nhận DM (kết hợp cả dm_recipient và recipients)
        target_recipients: List[discord.User] = []
        if dm_recipient:
            target_recipients.append(dm_recipient)
        if recipients:
            for r in recipients:
                if r and r not in target_recipients:
                    target_recipients.append(r)

        # Helper để gửi tin nhắn qua bot tương ứng hoặc fallback về thread
        async def send_as_bot(bot_client: Optional[discord.Client], embed: discord.Embed, file: Optional[discord.File] = None):
            if not thread:
                return
            try:
                if bot_client and bot_client.is_ready():
                    channel = bot_client.get_channel(thread.id) or await bot_client.fetch_channel(thread.id)
                    if file:
                        await channel.send(embed=embed, file=file)
                    else:
                        await channel.send(embed=embed)
                    return
            except Exception as e:
                print(f"[Orchestrator] Send via sub-bot failed, fallback to thread: {e}", flush=True)
            try:
                if file:
                    await thread.send(embed=embed, file=file)
                else:
                    await thread.send(embed=embed)
            except Exception:
                pass

        # -------------------------------------------------------------
        # 1. NEWS / TREND AGENT
        # -------------------------------------------------------------
        loading_news = discord.Embed(
            title=f"🔍 [News/Trend Agent] Đang lùng sục tin tức '{active_niche}' 30 ngày qua...",
            description=f"*Em đang hóng hớt ReAct search trên toàn cõi internet để bắt các hot topics về {active_niche} cho đại ca!*",
            color=COLOR_NEWS
        )
        print("[Orchestrator] 🚀 [1/4] Khởi động News Agent...", flush=True)
        await send_as_bot(news_bot, loading_news)

        news_res = await news_agent.run()
        hot_topics = news_res.get("hot_topics", [])
        print(f"[Orchestrator] [✅] News Agent hoàn tất: {len(hot_topics)} chủ đề hot", flush=True)

        if news_res.get("status") == "error":
            news_embed = discord.Embed(
                title="⚠️ [News Agent] Tạm Dừng Quét Tin",
                description=f"Chi tiết: {news_res.get('message', 'Lỗi kết nối.')}",
                color=COLOR_ERROR
            )
            await send_as_bot(news_bot, news_embed)
        else:
            topics_preview = " • ".join([f"`{t}`" for t in hot_topics[:4]]) if hot_topics else "Chưa trích xuất được."
            news_embed = discord.Embed(
                title=f"📰 [News Agent] Xu Hướng Nổi Bật: {NICHE_TOPIC}",
                description=f"🔥 **Hot Trends:** {topics_preview}\n\n"
                            f"💡 **Điểm tin chính:** {news_res.get('content', '')[:180]}...",
                color=COLOR_NEWS
            )
            await send_as_bot(news_bot, news_embed)

        # -------------------------------------------------------------
        # 2. MARKET / COMPETITOR AGENT
        # -------------------------------------------------------------
        loading_market = discord.Embed(
            title="📊 [Market Agent] Bật Radar Săn Video Breakout...",
            description="*Đang quét YouTube Data để lọc các kênh nhỏ có view bùng nổ bất thường.*",
            color=COLOR_MARKET
        )
        print("[Orchestrator] 🚀 [2/4] Khởi động Market Agent...", flush=True)
        await send_as_bot(market_bot, loading_market)

        market_res = await market_agent.run(hot_topics=hot_topics)
        top_videos = market_res.get("top_videos", [])
        print(f"[Orchestrator] [✅] Market Agent hoàn tất: {len(top_videos)} top breakout videos", flush=True)

        if market_res.get("status") == "error":
            market_embed = discord.Embed(
                title="⚠️ [Market Agent] Không Thể Lấy Dữ Liệu Video",
                description=f"Chi tiết: {market_res.get('message')}",
                color=COLOR_ERROR
            )
            await send_as_bot(market_bot, market_embed)
        else:
            vid_fields = []
            for v in top_videos[:3]:
                vid_fields.append(f"🎬 **[{v.get('title')[:40]}...]({v.get('url')})**\n   Kênh: *{v.get('channel_title')}* | `{v.get('view_count', 0):,}` views (`{v.get('view_sub_ratio')}x` Subs)")
            
            market_embed = discord.Embed(
                title="🚀 [Market Agent] Top Video Bứt Phá Nhất",
                description="\n\n".join(vid_fields) if vid_fields else "Không có video phù hợp.",
                color=COLOR_MARKET
            )
            await send_as_bot(market_bot, market_embed)

        # -------------------------------------------------------------
        # 3. THUMBNAIL AGENT
        # -------------------------------------------------------------
        loading_thumb = discord.Embed(
            title=f"🎨 [Thumbnail Agent] Soi Bố Cục & Visual CTR...",
            description="*Đang phân tích màu sắc và cấu trúc ảnh thumbnail thành công.*",
            color=COLOR_THUMBNAIL
        )
        print("[Orchestrator] 🚀 [3/4] Khởi động Thumbnail Agent...", flush=True)
        await send_as_bot(thumbnail_bot, loading_thumb)

        thumb_res = await thumbnail_agent.run(top_videos=top_videos)
        ctr_formulas = thumb_res.get("ctr_formulas", [])
        print(f"[Orchestrator] [✅] Thumbnail Agent hoàn tất: {len(ctr_formulas)} CTR formulas", flush=True)

        if thumb_res.get("status") == "error":
            thumb_embed = discord.Embed(
                title="⚠️ [Thumbnail Agent] Lỗi Phân Tích Visual",
                description=f"Chi tiết: {thumb_res.get('message')}",
                color=COLOR_ERROR
            )
            await send_as_bot(thumbnail_bot, thumb_embed)
        else:
            formulas_text = "\n".join([f"✨ {f}" for f in ctr_formulas[:3]])
            thumb_embed = discord.Embed(
                title="🎯 [Thumbnail Agent] 3 Công Thức Visual Thu Hút",
                description=formulas_text if formulas_text else "Đã phân tích xong mẫu visual.",
                color=COLOR_THUMBNAIL
            )
            await send_as_bot(thumbnail_bot, thumb_embed)

        # -------------------------------------------------------------
        # 4. ĐÁNH GIÁ TÍNH TOÀN VẸN & TỔNG HỢP BÁO CÁO (ORCHESTRATOR)
        # -------------------------------------------------------------
        success_count = sum([
            1 if news_res.get("status") == "success" else 0,
            1 if market_res.get("status") == "success" else 0,
            1 if thumb_res.get("status") == "success" else 0,
        ])

        now_str = datetime.now().strftime("%Y-%m-%d_%H%M")
        report_filename = f"report_{now_str}.md"
        report_filepath = REPORTS_DIR / report_filename

        session_stats = quota_tracker.get_session_stats()
        rate_limit_hits = session_stats.get("rate_limit_hits", 0)
        summary_embed = None

        if success_count <= 1:
            insufficient_md = f"# BÁO CÁO THỊ TRƯỜNG: {NICHE_TOPIC}\nKhông đủ dữ liệu tin cậy."
            report_filepath.write_text(insufficient_md, encoding="utf-8")
            summary_embed = discord.Embed(
                title=f"⚠️ [Orchestrator] Báo Cáo Không Đủ Dữ Liệu: {NICHE_TOPIC}",
                description="Hệ thống tạm thời chưa thu thập đủ số liệu tin cậy.",
                color=COLOR_WARNING
            )
            if thread:
                await thread.send(embed=summary_embed)
        else:
            is_full = (success_count == 3)
            score_data = self.calculate_niche_score()

            synthesis_prompt_content = f"""
Hãy tổng hợp báo cáo chiến lược hoàn chỉnh dựa trên dữ liệu thật sau:
Chủ đề: {NICHE_TOPIC}
Hot Topics: {json.dumps(hot_topics, ensure_ascii=False)}
Top Videos: {json.dumps(top_videos[:5], ensure_ascii=False)}
CTR Formulas: {json.dumps(ctr_formulas, ensure_ascii=False)}
Điểm: {score_data['score']}/100 ({score_data['tier']})
"""
            synth_res = await llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": synthesis_prompt},
                    {"role": "user", "content": synthesis_prompt_content}
                ],
                temperature=0.2,
                max_tokens=3000
            )

            report_md_content = strip_think_tags(synth_res.get("content", ""))
            if not report_md_content:
                report_md_content = f"# BÁO CÁO CHIẾN LƯỢC NICHE {NICHE_TOPIC}\n- Điểm: {score_data['score']}/100"

            report_filepath.write_text(report_md_content, encoding="utf-8")

            top_recommended_topic = hot_topics[0] if hot_topics else active_niche

            # Giao diện Báo Cáo Tinh Gọn, Thoáng & Đẳng Cấp
            summary_embed = discord.Embed(
                title=f"🏆 BÁO CÁO CHIẾN LƯỢC: NICHE {NICHE_TOPIC.upper()}",
                description=f"📊 **Điểm Cơ Hội:** `{score_data['score']}/100` — **{score_data['tier']}**\n\n"
                            f"🔥 **3 ĐIỂM SÁNG TRỌNG TÂM:**\n"
                            f"• **Nhu cầu cao:** Khán giả đang quan tâm lớn về `{', '.join(hot_topics[:2]) if hot_topics else NICHE_TOPIC}`.\n"
                            f"• **Cơ hội bứt phá:** Kênh nhỏ dễ viral nếu khai thác góc nhìn giải thích trực quan & số liệu độc lạ.\n"
                            f"• **Tối ưu CTR:** Phối màu tương phản cao (Vàng Neon / Xanh Điện) + Text ngắn dưới 3 từ.\n\n"
                            f"💡 *Toàn bộ phân tích chuyên sâu đã được đính kèm trong file bên dưới!*",
                color=COLOR_ORCHESTRATOR
            )
            summary_embed.add_field(
                name="💡 ĐỀ XUẤT HÀNH ĐỘNG TIẾP THEO",
                value=f"Chủ đề **\"{top_recommended_topic}\"** đạt **{score_data['tier']}**, tiềm năng bứt phá view rất cao!\n"
                      f"👉 Gõ: `/kichban topic:\"{top_recommended_topic}\"` để em lên ngay kịch bản chi tiết & bộ Prompt AI nhé!",
                inline=False
            )
            summary_embed.set_footer(text=f"AI 4 AI Strategy • File: {report_filename}")

            if thread:
                with open(report_filepath, "rb") as f:
                    discord_file = discord.File(f, filename=report_filename)
                    await thread.send(embed=summary_embed, file=discord_file)

        # -------------------------------------------------------------
        # 5. GỬI BÁO CÁO QUA DM (NẾU CÓ NGƯỜI NHẬN TARGET_RECIPIENTS)
        # -------------------------------------------------------------
        if target_recipients and summary_embed:
            for recipient in target_recipients:
                print("\n" + "=" * 70, flush=True)
                print(f"📬 [OUTGOING DM] GỬI BÁO CÁO CHO {recipient.name} (ID: {recipient.id})", flush=True)
                print("=" * 70, flush=True)
                try:
                    with open(report_filepath, "rb") as f:
                        dm_file = discord.File(f, filename=report_filename)
                        await recipient.send(
                            content=f"👋 **Báo cáo nghiên cứu chiến lược YouTube: `{active_niche}`** (Dành riêng cho <@{recipient.id}>)\n"
                                    f"💡 *Đề xuất hôm nay:* Chủ đề **\"{top_recommended_topic}\"** đang có chỉ số rất tốt. Đại ca gõ `/kichban topic:\"{top_recommended_topic}\"` nếu muốn xuất kịch bản sản xuất ngay nhé!",
                            embed=summary_embed,
                            file=dm_file
                        )
                    print(f"[Orchestrator] [✅] Đã gửi DM báo cáo thành công tới {recipient.name} (ID: {recipient.id})", flush=True)
                except discord.Forbidden:
                    print(f"[Orchestrator] [⚠️] Không thể gửi DM cho {recipient.name} (ID: {recipient.id}) (Forbidden).", flush=True)
                except Exception as e:
                    print(f"[Orchestrator] [❌] Lỗi khi gửi DM cho {recipient.name}: {e}", flush=True)

        # -------------------------------------------------------------
        # 6. GIÁM SÁT QUOTA TỔNG KẾT
        # -------------------------------------------------------------
        final_stats = quota_tracker.get_session_stats()
        monitor_embed = discord.Embed(
            title="🛡️ [Quota Monitor] Báo Cáo Kiểm Toán Hạn Mức Sau Phiên Chạy",
            description=f"*Báo cáo đại ca số lượng tài nguyên API đã tiêu thụ trong lần chạy này:*\n\n"
                        f"• **YouTube Data API:** ~`{final_stats['yt_units']}` units (trong tổng 10,000 units/ngày)\n"
                        f"• **LLM API Requests:** `{final_stats['llm_requests']}` requests\n"
                        f"• **LLM Tokens:** `{final_stats['llm_tokens']:,}` tokens\n"
                        f"• **Rate Limit Hits (429):** `{final_stats['rate_limit_hits']}`",
            color=COLOR_MONITOR
        )
        await send_as_bot(monitor_bot, monitor_embed)

        return {
            "status": "success",
            "report_filepath": str(report_filepath),
            "report_filename": report_filename,
            "summary_embed": summary_embed
        }

orchestrator = Orchestrator()
