import os
import json
import asyncio
from datetime import datetime
from aiohttp import web
from config import NICHE_TOPIC, DAILY_RUN_TIME, DAILY_RUN_TIMEZONE, LLM_PROVIDER, BASE_DIR
from services.quota_tracker import quota_tracker
from services.chat_logger import chat_logger
from services.growth_experiments import growth_experiments

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 4 AI - Production Studio & Quota Hub</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #06080e;
            --bg-card: rgba(13, 18, 30, 0.85);
            --bg-card-hover: rgba(20, 28, 46, 0.95);
            --border-color: rgba(255, 255, 255, 0.08);
            --border-glow: rgba(139, 92, 246, 0.4);
            --accent-purple: #8b5cf6;
            --accent-blue: #3b82f6;
            --accent-cyan: #06b6d4;
            --accent-green: #10b981;
            --accent-amber: #f59e0b;
            --accent-rose: #f43f5e;
            --accent-groq: #f97316;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --text-dim: #64748b;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            background-color: var(--bg-primary);
            background-image: 
                radial-gradient(at 0% 0%, rgba(139, 92, 246, 0.15) 0px, transparent 45%),
                radial-gradient(at 100% 0%, rgba(249, 115, 22, 0.12) 0px, transparent 45%),
                radial-gradient(at 50% 100%, rgba(59, 130, 246, 0.10) 0px, transparent 50%);
            background-attachment: fixed;
            color: var(--text-main);
            font-family: 'Plus Jakarta Sans', sans-serif;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }

        header {
            background: rgba(6, 8, 14, 0.9);
            backdrop-filter: blur(16px);
            border-bottom: 1px solid var(--border-color);
            position: sticky;
            top: 0;
            z-index: 50;
            padding: 0.85rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 0.875rem;
        }

        .brand-logo {
            width: 42px;
            height: 42px;
            border-radius: 12px;
            background: linear-gradient(135deg, var(--accent-purple), var(--accent-groq));
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.35rem;
            box-shadow: 0 0 25px rgba(249, 115, 22, 0.35);
        }

        .brand-title {
            font-size: 1.2rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            background: linear-gradient(to right, #ffffff, #cbd5e1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .brand-subtitle {
            font-size: 0.78rem;
            color: var(--text-muted);
            font-weight: 500;
        }

        .header-badges {
            display: flex;
            gap: 0.6rem;
            align-items: center;
        }

        .badge {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border-color);
            padding: 0.35rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.4rem;
            color: var(--text-muted);
        }

        .badge-dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background-color: var(--accent-green);
            box-shadow: 0 0 8px var(--accent-green);
        }

        /* Studio Navigation Tabs */
        .studio-nav {
            background: rgba(13, 18, 30, 0.7);
            border-bottom: 1px solid var(--border-color);
            padding: 0.5rem 2rem;
            display: flex;
            gap: 0.5rem;
            overflow-x: auto;
        }

        .nav-tab {
            background: transparent;
            border: none;
            color: var(--text-muted);
            padding: 0.6rem 1.1rem;
            border-radius: 10px;
            font-size: 0.85rem;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            transition: all 0.2s ease;
        }

        .nav-tab:hover {
            background: rgba(255, 255, 255, 0.05);
            color: var(--text-main);
        }

        .nav-tab.active {
            background: linear-gradient(135deg, rgba(139, 92, 246, 0.25), rgba(59, 130, 246, 0.25));
            color: #ffffff;
            border: 1px solid rgba(139, 92, 246, 0.5);
            box-shadow: 0 0 15px rgba(139, 92, 246, 0.2);
        }

        main {
            flex: 1;
            padding: 1.75rem 2rem;
            max-width: 1600px;
            margin: 0 auto;
            width: 100%;
        }

        .tab-content { display: none; }
        .tab-content.active { display: block; }

        /* Grid Layouts */
        .grid-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 1.25rem;
            margin-bottom: 1.75rem;
        }

        .card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1.35rem;
            backdrop-filter: blur(12px);
            transition: transform 0.2s, border-color 0.2s, box-shadow 0.2s;
        }

        .card:hover {
            transform: translateY(-2px);
            border-color: var(--border-glow);
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        }

        .card-title {
            font-size: 0.78rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-dim);
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .card-value {
            font-size: 1.8rem;
            font-weight: 800;
            font-family: 'JetBrains Mono', monospace;
            color: #ffffff;
            display: flex;
            align-items: baseline;
            gap: 0.35rem;
        }

        .card-desc {
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-top: 0.5rem;
        }

        /* Progress Bar */
        .progress-container {
            width: 100%;
            height: 6px;
            background: rgba(255, 255, 255, 0.07);
            border-radius: 9999px;
            margin-top: 0.75rem;
            overflow: hidden;
        }

        .progress-fill {
            height: 100%;
            border-radius: 9999px;
            background: linear-gradient(90deg, var(--accent-cyan), var(--accent-blue));
            transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1);
        }

        /* Studio Video Grid */
        .video-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 1.5rem;
        }

        .video-card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }

        .video-wrapper {
            position: relative;
            background: #000;
            width: 100%;
            aspect-ratio: 9/16;
            max-height: 480px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .video-wrapper video {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }

        .video-info {
            padding: 1rem;
            flex: 1;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }

        .video-title {
            font-weight: 700;
            font-size: 0.95rem;
            margin-bottom: 0.35rem;
            color: #ffffff;
        }

        .video-meta {
            font-size: 0.75rem;
            color: var(--text-muted);
            display: flex;
            gap: 0.75rem;
        }

        /* A/B Test Arm Cards */
        .ab-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
            margin-top: 1rem;
        }

        .arm-card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1.5rem;
        }

        .arm-badge {
            display: inline-block;
            padding: 0.25rem 0.65rem;
            border-radius: 8px;
            font-weight: 700;
            font-size: 0.75rem;
            margin-bottom: 0.85rem;
        }

        .arm-a { background: rgba(59, 130, 246, 0.2); color: var(--accent-blue); border: 1px solid var(--accent-blue); }
        .arm-b { background: rgba(244, 63, 94, 0.2); color: var(--accent-rose); border: 1px solid var(--accent-rose); }

        /* Prompt Box */
        .prompt-box {
            background: rgba(0, 0, 0, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 10px;
            padding: 0.85rem;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.8rem;
            color: #cbd5e1;
            margin-top: 0.75rem;
            word-break: break-word;
            position: relative;
        }

        .btn-copy {
            position: absolute;
            top: 6px;
            right: 6px;
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.15);
            color: #fff;
            padding: 0.25rem 0.5rem;
            border-radius: 6px;
            font-size: 0.7rem;
            cursor: pointer;
        }

        .btn-copy:hover { background: var(--accent-purple); }

        /* Gallery Grid */
        .gallery-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 1.25rem;
        }

        .gallery-item {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            overflow: hidden;
            transition: transform 0.2s;
        }

        .gallery-item:hover { transform: scale(1.02); }
        .gallery-item img { width: 100%; height: auto; display: block; }
        .gallery-caption { padding: 0.75rem; font-size: 0.8rem; color: var(--text-muted); }

        /* Live Chat Table */
        .chat-feed {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1.25rem;
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
            max-height: 650px;
            overflow-y: auto;
        }

        .chat-msg {
            background: rgba(0, 0, 0, 0.25);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 0.85rem 1.1rem;
        }

        .msg-header {
            display: flex;
            justify-content: space-between;
            font-size: 0.75rem;
            color: var(--text-dim);
            margin-bottom: 0.35rem;
        }

        .bot-tag {
            font-weight: 700;
            color: var(--accent-purple);
        }

        .msg-text {
            font-size: 0.88rem;
            line-height: 1.5;
            color: #e2e8f0;
            white-space: pre-wrap;
        }

        /* Action Buttons */
        .btn-action {
            background: linear-gradient(135deg, var(--accent-purple), var(--accent-blue));
            border: none;
            color: #fff;
            padding: 0.6rem 1.25rem;
            border-radius: 10px;
            font-weight: 700;
            font-size: 0.85rem;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            transition: all 0.2s;
        }

        .btn-action:hover {
            box-shadow: 0 0 20px rgba(139, 92, 246, 0.4);
            transform: translateY(-1px);
        }

        input[type="text"] {
            background: rgba(0, 0, 0, 0.4);
            border: 1px solid var(--border-color);
            color: #fff;
            padding: 0.6rem 1rem;
            border-radius: 10px;
            font-size: 0.85rem;
            outline: none;
            width: 100%;
        }

        input[type="text"]:focus {
            border-color: var(--accent-purple);
        }

        @media (max-width: 900px) {
            .ab-container { grid-template-columns: 1fr; }
            header { flex-direction: column; gap: 0.85rem; }
        }
    </style>
</head>
<body>
    <header>
        <div class="brand">
            <div class="brand-logo">⚡</div>
            <div>
                <div class="brand-title">AI 4 AI • PRODUCTION STUDIO</div>
                <div class="brand-subtitle">Niche: __NICHE_TOPIC__</div>
            </div>
        </div>
        <div class="header-badges">
            <div class="badge"><span class="badge-dot"></span> 5 Bot Live</div>
            <div class="badge">⚙️ Lịch: __DAILY_RUN_TIME__</div>
            <div class="badge" style="color: var(--accent-groq);">⚡ Gemini 3.6 Flash Engine</div>
        </div>
    </header>

    <!-- Studio Nav Tabs -->
    <nav class="studio-nav">
        <button class="nav-tab active" onclick="switchTab('overview')">📊 Tổng Quan & Quota</button>
        <button class="nav-tab" onclick="switchTab('videos')">🎬 Video Shorts Player</button>
        <button class="nav-tab" onclick="switchTab('ab-testing')">⚖️ A/B Testing Studio</button>
        <button class="nav-tab" onclick="switchTab('scripts')">📝 Kịch Bản & Quick Copy</button>
        <button class="nav-tab" onclick="switchTab('gallery')">🎨 Visual 4K Gallery</button>
        <button class="nav-tab" onclick="switchTab('chats')">💬 Live Discord Feed</button>
    </nav>

    <main>
        <!-- TAB 1: OVERVIEW -->
        <div id="tab-overview" class="tab-content active">
            <div class="grid-cards">
                <div class="card">
                    <div class="card-title"><span>Google Gemini Quota (RPD)</span> <span>⚡</span></div>
                    <div class="card-value" id="gemini-requests">-- <span style="font-size: 1rem; color: var(--text-dim)">/ 1500</span></div>
                    <div class="progress-container"><div class="progress-fill" id="gemini-progress" style="width: 0%"></div></div>
                    <div class="card-desc" id="gemini-desc">Còn lại -- lượt gọi miễn phí hôm nay</div>
                </div>

                <div class="card">
                    <div class="card-title"><span>YouTube Data API (Units)</span> <span>📺</span></div>
                    <div class="card-value" id="yt-units">-- <span style="font-size: 1rem; color: var(--text-dim)">/ 10000</span></div>
                    <div class="progress-container"><div class="progress-fill" id="yt-progress" style="width: 0%; background: linear-gradient(90deg, var(--accent-rose), var(--accent-amber));"></div></div>
                    <div class="card-desc" id="yt-desc">Đã tiêu hao -- units</div>
                </div>

                <div class="card">
                    <div class="card-title"><span>Độ Trễ Phản Hồi TB</span> <span>⏱️</span></div>
                    <div class="card-value" id="avg-latency" style="color: var(--accent-green)">-- ms</div>
                    <div class="card-desc">Tốc độ xử lý siêu tốc qua Flash LPU</div>
                </div>

                <div class="card">
                    <div class="card-title"><span>Tổng Tương Tác Bot</span> <span>🤖</span></div>
                    <div class="card-value" id="total-chats" style="color: var(--accent-purple)">--</div>
                    <div class="card-desc">Tin nhắn và phân tích đã thực hiện</div>
                </div>
            </div>

            <!-- Quick Action Studio -->
            <div class="card" style="margin-top: 1rem;">
                <h3 style="font-size: 1rem; margin-bottom: 1rem; color: #fff;">🚀 Studio Quick Actions (Lệnh Thực Thi Nhanh)</h3>
                <div style="display: flex; gap: 0.75rem; flex-wrap: wrap;">
                    <div style="flex: 1; min-width: 250px;">
                        <input type="text" id="quick-topic" placeholder="Nhập chủ đề (vd: Vì sao bầu trời có màu xanh)...">
                    </div>
                    <button class="btn-action" onclick="runABTest()"><span style="font-size: 1.1rem;">⚖️</span> Chạy A/B Testing Studio</button>
                    <button class="btn-action" style="background: linear-gradient(135deg, var(--accent-groq), var(--accent-rose));" onclick="switchTab('videos')">🎬 Xem Kho Video Shorts</button>
                </div>
            </div>
        </div>

        <!-- TAB 2: VIDEOS -->
        <div id="tab-videos" class="tab-content">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.25rem;">
                <h2 style="font-size: 1.25rem; font-weight: 800;">🎬 Kho Video Shorts Đã Dựng Hoàn Chỉnh (9:16)</h2>
                <button class="btn-action" onclick="fetchVideos()">🔄 Làm Mới Video</button>
            </div>
            <div class="video-grid" id="video-list">
                <div style="color: var(--text-muted); font-size: 0.9rem;">Đang tải danh sách video...</div>
            </div>
        </div>

        <!-- TAB 3: A/B TESTING -->
        <div id="tab-ab-testing" class="tab-content">
            <h2 style="font-size: 1.25rem; font-weight: 800; margin-bottom: 0.5rem;">⚖️ Phòng Thí Nghiệm Tăng Trưởng (A/B Testing Studio)</h2>
            <p style="color: var(--text-muted); font-size: 0.85rem; margin-bottom: 1.25rem;">So sánh 2 chiến lược đóng gói đối kháng: <strong>Arm A (Tò Mò Nghịch Lý)</strong> vs <strong>Arm B (Kịch Tính Cảnh Báo)</strong>.</p>
            
            <div id="ab-result" style="display: none;">
                <div class="ab-container">
                    <div class="arm-card">
                        <span class="arm-badge arm-a">STRATEGY ARM A • CURIOSITY</span>
                        <h3 id="arm-a-title" style="font-size: 1.1rem; color: #fff; margin-bottom: 0.5rem;">--</h3>
                        <p style="color: var(--accent-blue); font-size: 0.85rem; font-weight: 600;" id="arm-a-hook">Hook: --</p>
                        <div class="prompt-box">
                            <button class="btn-copy" onclick="copyText('arm-a-prompt')">Copy</button>
                            <div id="arm-a-prompt">--</div>
                        </div>
                    </div>

                    <div class="arm-card">
                        <span class="arm-badge arm-b">STRATEGY ARM B • DRAMA & WARNING</span>
                        <h3 id="arm-b-title" style="font-size: 1.1rem; color: #fff; margin-bottom: 0.5rem;">--</h3>
                        <p style="color: var(--accent-rose); font-size: 0.85rem; font-weight: 600;" id="arm-b-hook">Hook: --</p>
                        <div class="prompt-box">
                            <button class="btn-copy" onclick="copyText('arm-b-prompt')">Copy</button>
                            <div id="arm-b-prompt">--</div>
                        </div>
                    </div>
                </div>
                <div class="card" style="margin-top: 1.25rem; border-color: rgba(16, 185, 129, 0.4);">
                    <h4 style="color: var(--accent-green); margin-bottom: 0.25rem;">💡 Đánh Giá Khuyến Nghị Chuyên Gia:</h4>
                    <p id="ab-rec" style="font-size: 0.9rem; color: #cbd5e1;">--</p>
                </div>
            </div>
            <div id="ab-placeholder" style="text-align: center; padding: 3rem 1rem; color: var(--text-muted);">
                Nhập chủ đề ở thanh tìm kiếm và bấm "Chạy A/B Testing Studio" để xem kết quả so sánh đối kháng!
            </div>
        </div>

        <!-- TAB 4: SCRIPTS -->
        <div id="tab-scripts" class="tab-content">
            <h2 style="font-size: 1.25rem; font-weight: 800; margin-bottom: 1.25rem;">📝 Kho Kịch Bản & Khối Quick Copy</h2>
            <div id="script-list" style="display: flex; flex-direction: column; gap: 1rem;">
                <!-- Scripts loaded dynamically -->
            </div>
        </div>

        <!-- TAB 5: GALLERY -->
        <div id="tab-gallery" class="tab-content">
            <h2 style="font-size: 1.25rem; font-weight: 800; margin-bottom: 1.25rem;">🎨 Thư Viện Hình Ảnh 4K & Thumbnail Studio</h2>
            <div class="gallery-grid" id="gallery-list">
                <!-- Images loaded dynamically -->
            </div>
        </div>

        <!-- TAB 6: LIVE CHAT FEED -->
        <div id="tab-chats" class="tab-content">
            <h2 style="font-size: 1.25rem; font-weight: 800; margin-bottom: 1.25rem;">💬 Luồng Nhật Ký Discord Real-Time</h2>
            <div class="chat-feed" id="chat-list">
                <!-- Chats loaded dynamically -->
            </div>
        </div>
    </main>

    <script>
        function switchTab(tabId) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.nav-tab').forEach(el => el.classList.remove('active'));
            
            const target = document.getElementById('tab-' + tabId);
            if (target) target.classList.add('active');
            
            event.target.classList.add('active');
            if (tabId === 'videos') fetchVideos();
            if (tabId === 'scripts') fetchScripts();
            if (tabId === 'gallery') fetchGallery();
            if (tabId === 'chats') fetchChats();
        }

        function copyText(id) {
            const text = document.getElementById(id).innerText;
            navigator.clipboard.writeText(text);
            alert('Đã copy Prompt vào Clipboard thành công!');
        }

        async function fetchStats() {
            try {
                const res = await fetch('/api/stats');
                const data = await res.json();
                const q = data.quota || {};
                const c = data.chat_stats || {};

                // Gemini
                const gUsed = q.gemini_requests_today || 0;
                const gLimit = q.gemini_daily_limit || 1500;
                const gPercent = Math.min(100, Math.round((gUsed / gLimit) * 100));
                document.getElementById('gemini-requests').innerHTML = `${gUsed} <span style="font-size: 1rem; color: var(--text-dim)">/ ${gLimit}</span>`;
                document.getElementById('gemini-progress').style.width = gPercent + '%';
                document.getElementById('gemini-desc').innerText = `Còn lại ${gLimit - gUsed} lượt gọi miễn phí hôm nay`;

                // YouTube
                const yUsed = q.yt_units_today || 0;
                const yLimit = q.yt_daily_limit || 10000;
                const yPercent = Math.min(100, Math.round((yUsed / yLimit) * 100));
                document.getElementById('yt-units').innerHTML = `${yUsed} <span style="font-size: 1rem; color: var(--text-dim)">/ ${yLimit}</span>`;
                document.getElementById('yt-progress').style.width = yPercent + '%';
                document.getElementById('yt-desc').innerText = `Đã tiêu hao ${yUsed} / ${yLimit} units`;

                // Latency & Chats
                document.getElementById('avg-latency').innerText = `${q.gemini_avg_latency_ms || 320} ms`;
                document.getElementById('total-chats').innerText = c.total_messages || 0;
            } catch (e) {
                console.error('Lỗi tải stats:', e);
            }
        }

        async function fetchVideos() {
            try {
                const res = await fetch('/api/videos');
                const videos = await res.json();
                const list = document.getElementById('video-list');
                if (!videos || videos.length === 0) {
                    list.innerHTML = '<div style="color: var(--text-muted); padding: 2rem 0;">Chưa có video Shorts nào được xuất. Hãy gõ lệnh <code>/render_video</code> trên Discord để tạo video đầu tiên!</div>';
                    return;
                }
                list.innerHTML = videos.map(v => `
                    <div class="video-card">
                        <div class="video-wrapper">
                            <video src="/api/videos/${encodeURIComponent(v.filename)}" controls playsinline preload="metadata"></video>
                        </div>
                        <div class="video-info">
                            <div class="video-title">${v.filename}</div>
                            <div class="video-meta">
                                <span>📦 ${v.size_mb} MB</span>
                                <span>🕒 ${v.modified_time}</span>
                            </div>
                            <a href="/api/videos/${encodeURIComponent(v.filename)}" download class="btn-action" style="margin-top: 0.75rem; text-decoration: none; justify-content: center; font-size: 0.78rem;">⬇️ Tải Video MP4</a>
                        </div>
                    </div>
                `).join('');
            } catch (e) {
                console.error('Lỗi tải videos:', e);
            }
        }

        async function fetchScripts() {
            try {
                const res = await fetch('/api/reports');
                const reports = await res.json();
                const list = document.getElementById('script-list');
                const scriptReports = reports.filter(r => r.filename.includes('script_') || r.filename.endsWith('.md'));
                
                if (scriptReports.length === 0) {
                    list.innerHTML = '<div style="color: var(--text-muted);">Chưa có file kịch bản nào.</div>';
                    return;
                }

                list.innerHTML = scriptReports.map(r => `
                    <div class="card">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <h3 style="font-size: 0.95rem; color: #fff;">📄 ${r.filename}</h3>
                            <span style="font-size: 0.75rem; color: var(--text-dim);">${r.modified_time}</span>
                        </div>
                    </div>
                `).join('');
            } catch (e) {
                console.error('Lỗi tải scripts:', e);
            }
        }

        async function fetchGallery() {
            try {
                const res = await fetch('/api/gallery');
                const images = await res.json();
                const list = document.getElementById('gallery-list');
                if (!images || images.length === 0) {
                    list.innerHTML = '<div style="color: var(--text-muted);">Chưa có ảnh thumbnail nào trong thư viện.</div>';
                    return;
                }
                list.innerHTML = images.map(img => `
                    <div class="gallery-item">
                        <img src="/api/images/${encodeURIComponent(img.filename)}" loading="lazy" alt="Thumbnail">
                        <div class="gallery-caption">${img.filename}</div>
                    </div>
                `).join('');
            } catch (e) {
                console.error('Lỗi tải gallery:', e);
            }
        }

        async function fetchChats() {
            try {
                const res = await fetch('/api/chats?limit=30');
                const chats = await res.json();
                const list = document.getElementById('chat-list');
                if (!chats || chats.length === 0) {
                    list.innerHTML = '<div style="color: var(--text-muted);">Chưa có nhật ký hội thoại.</div>';
                    return;
                }
                list.innerHTML = chats.map(c => `
                    <div class="chat-msg">
                        <div class="msg-header">
                            <span class="bot-tag">${c.bot_name} (${c.bot_role || 'Agent'})</span>
                            <span>${c.created_at} • ${c.user_name}</span>
                        </div>
                        <div class="msg-text">${c.bot_response || c.user_message}</div>
                    </div>
                `).join('');
            } catch (e) {
                console.error('Lỗi tải chats:', e);
            }
        }

        async function runABTest() {
            const topic = document.getElementById('quick-topic').value.trim() || 'Vì sao bầu trời có màu xanh';
            switchTab('ab-testing');
            document.getElementById('ab-placeholder').innerText = '⏳ Đang phân tích chiến lược và tạo 2 phương án đối kháng...';
            document.getElementById('ab-result').style.display = 'none';

            try {
                const res = await fetch(`/api/ab_test?topic=${encodeURIComponent(topic)}`);
                const data = await res.json();
                
                document.getElementById('arm-a-title').innerText = data.arm_a.title_vn;
                document.getElementById('arm-a-hook').innerText = 'Hook 3s: ' + data.arm_a.hook_3s;
                document.getElementById('arm-a-prompt').innerText = data.arm_a.thumbnail_prompt;

                document.getElementById('arm-b-title').innerText = data.arm_b.title_vn;
                document.getElementById('arm-b-hook').innerText = 'Hook 3s: ' + data.arm_b.hook_3s;
                document.getElementById('arm-b-prompt').innerText = data.arm_b.thumbnail_prompt;

                document.getElementById('ab-rec').innerText = data.recommendation || 'Nên thử nghiệm cả 2 phương án.';
                
                document.getElementById('ab-placeholder').style.display = 'none';
                document.getElementById('ab-result').style.display = 'block';
            } catch (e) {
                document.getElementById('ab-placeholder').innerText = '⚠️ Lỗi khi chạy A/B testing: ' + e;
            }
        }

        // Khởi động
        fetchStats();
        setInterval(fetchStats, 5000);
    </script>
</body>
</html>
"""

def create_dashboard_app() -> web.Application:
    app = web.Application()

    async def handle_index(request):
        html_rendered = HTML_TEMPLATE.replace("__NICHE_TOPIC__", NICHE_TOPIC).replace("__DAILY_RUN_TIME__", f"{DAILY_RUN_TIME} ({DAILY_RUN_TIMEZONE})")
        return web.Response(text=html_rendered, content_type="text/html", charset="utf-8")

    async def handle_api_chats(request):
        bot_filter = request.query.get("bot", "all")
        search = request.query.get("search", "")
        chats = chat_logger.get_recent_chats(limit=80, bot_filter=bot_filter, search_query=search)
        return web.json_response(chats)

    async def handle_api_stats(request):
        q_summary = quota_tracker.get_quota_summary(provider=LLM_PROVIDER)
        c_stats = chat_logger.get_stats()
        return web.json_response({
            "quota": q_summary,
            "chat_stats": c_stats
        })

    async def handle_api_reports(request):
        reports_dir = BASE_DIR / "reports"
        if not reports_dir.exists():
            return web.json_response([])
        
        files = []
        for root, _, filenames in os.walk(str(reports_dir)):
            for fn in filenames:
                if fn.endswith(".md"):
                    fp = os.path.join(root, fn)
                    rel_name = os.path.relpath(fp, str(reports_dir)).replace("\\", "/")
                    st = os.stat(fp)
                    files.append({
                        "filename": rel_name,
                        "size": st.st_size,
                        "modified_time": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    })
        files.sort(key=lambda x: x["modified_time"], reverse=True)
        return web.json_response(files)

    async def handle_api_videos(request):
        videos_dir = BASE_DIR / "reports" / "videos"
        if not videos_dir.exists():
            return web.json_response([])

        videos = []
        for fn in os.listdir(videos_dir):
            if fn.endswith(".mp4"):
                fp = videos_dir / fn
                st = fp.stat()
                videos.append({
                    "filename": fn,
                    "size_mb": round(st.st_size / (1024 * 1024), 2),
                    "modified_time": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                })
        videos.sort(key=lambda x: x["modified_time"], reverse=True)
        return web.json_response(videos)

    async def handle_serve_video(request):
        filename = request.match_info.get("filename", "")
        fp = BASE_DIR / "reports" / "videos" / filename
        if fp.exists() and filename.endswith(".mp4"):
            return web.FileResponse(fp)
        return web.json_response({"error": "Video not found"}, status=404)

    async def handle_api_gallery(request):
        img_dir = BASE_DIR / "reports" / "images"
        if not img_dir.exists():
            return web.json_response([])

        images = []
        for fn in os.listdir(img_dir):
            if fn.endswith((".png", ".jpg", ".webp")):
                fp = img_dir / fn
                st = fp.stat()
                images.append({
                    "filename": fn,
                    "modified_time": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                })
        images.sort(key=lambda x: x["modified_time"], reverse=True)
        return web.json_response(images)

    async def handle_serve_image(request):
        filename = request.match_info.get("filename", "")
        fp = BASE_DIR / "reports" / "images" / filename
        if fp.exists() and filename.endswith((".png", ".jpg", ".webp")):
            return web.FileResponse(fp)
        return web.json_response({"error": "Image not found"}, status=404)

    async def handle_api_ab_test(request):
        topic = request.query.get("topic", "Hiện tượng sấm sét").strip()
        data = await growth_experiments.generate_ab_experiment(topic)
        return web.json_response(data)

    app.router.add_get("/", handle_index)
    app.router.add_get("/api/chats", handle_api_chats)
    app.router.add_get("/api/stats", handle_api_stats)
    app.router.add_get("/api/reports", handle_api_reports)
    app.router.add_get("/api/videos", handle_api_videos)
    app.router.add_get("/api/videos/{filename}", handle_serve_video)
    app.router.add_get("/api/gallery", handle_api_gallery)
    app.router.add_get("/api/images/{filename}", handle_serve_image)
    app.router.add_get("/api/ab_test", handle_api_ab_test)

    return app

async def start_dashboard_server(host: str = "0.0.0.0", port: int = 5000):
    env_port_raw = os.getenv("PORT", "").strip()
    target_port = int(env_port_raw) if env_port_raw.isdigit() else port

    app = create_dashboard_app()
    runner = web.AppRunner(app)
    await runner.setup()
    
    ports_to_try = [target_port, 5000, 8080, 10000]
    for p in ports_to_try:
        try:
            site = web.TCPSite(runner, host, p)
            await site.start()
            print(f"[Dashboard Server] [🚀 ONLINE] Giao diện quản lý đã sẵn sàng tại port {p} (http://localhost:{p})", flush=True)
            return p
        except Exception as err:
            if p == ports_to_try[-1]:
                print(f"[Dashboard Server] Cảnh báo: Không thể bind port ({err})", flush=True)
                return None
            continue
