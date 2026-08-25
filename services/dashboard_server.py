import os
import json
import asyncio
from datetime import datetime
from aiohttp import web
from config import NICHE_TOPIC, DAILY_RUN_TIME, DAILY_RUN_TIMEZONE, LLM_PROVIDER
from services.quota_tracker import quota_tracker
from services.chat_logger import chat_logger

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 4 AI - Control Hub & Quota Monitor</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #07090e;
            --bg-card: rgba(15, 21, 34, 0.85);
            --bg-card-hover: rgba(22, 31, 51, 0.95);
            --border-color: rgba(255, 255, 255, 0.08);
            --border-glow: rgba(139, 92, 246, 0.35);
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
            background: rgba(7, 9, 14, 0.85);
            backdrop-filter: blur(16px);
            border-bottom: 1px solid var(--border-color);
            position: sticky;
            top: 0;
            z-index: 50;
            padding: 1rem 2rem;
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
            width: 44px;
            height: 44px;
            border-radius: 12px;
            background: linear-gradient(135deg, var(--accent-purple), var(--accent-groq));
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.4rem;
            box-shadow: 0 0 25px rgba(249, 115, 22, 0.35);
        }

        .brand-title {
            font-size: 1.25rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            background: linear-gradient(to right, #ffffff, #cbd5e1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .brand-subtitle {
            font-size: 0.8rem;
            color: var(--text-muted);
            font-weight: 500;
        }

        .header-badges {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .badge {
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            padding: 0.4rem 0.8rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border-color);
        }

        .badge-live {
            background: rgba(16, 185, 129, 0.15);
            border-color: rgba(16, 185, 129, 0.3);
            color: #34d399;
        }

        .badge-live::before {
            content: '';
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: #10b981;
            box-shadow: 0 0 10px #10b981;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.4; transform: scale(0.85); }
        }

        .container {
            max-width: 1400px;
            width: 100%;
            margin: 0 auto;
            padding: 2rem;
            display: flex;
            flex-direction: column;
            gap: 2rem;
        }

        /* SECTION TITLE */
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: -0.5rem;
        }

        .section-title {
            font-size: 1.15rem;
            font-weight: 800;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            letter-spacing: -0.01em;
        }

        /* QUOTA VISUAL PANELS GRID */
        /* QUOTA VISUAL PANELS GRID */
        .quota-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
            gap: 1.5rem;
        }

        .quota-card {
            background: var(--bg-card);
            backdrop-filter: blur(14px);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 1.5rem;
            display: flex;
            flex-direction: column;
            gap: 1.25rem;
            position: relative;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
        }

        .quota-card-groq {
            border-top: 3px solid var(--accent-groq);
        }

        .quota-card-gemini {
            border-top: 3px solid #3b82f6;
        }

        .quota-card-yt {
            border-top: 3px solid var(--accent-rose);
        }

        .quota-card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .quota-title-box {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .quota-icon {
            width: 38px;
            height: 38px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.25rem;
        }

        .icon-groq {
            background: rgba(249, 115, 22, 0.15);
            border: 1px solid rgba(249, 115, 22, 0.3);
            color: #fb923c;
        }

        .icon-gemini {
            background: rgba(59, 130, 246, 0.15);
            border: 1px solid rgba(59, 130, 246, 0.3);
            color: #60a5fa;
        }

        .icon-yt {
            background: rgba(244, 63, 94, 0.15);
            border: 1px solid rgba(244, 63, 94, 0.3);
            color: #fb7185;
        }

        .quota-name {
            font-size: 1.05rem;
            font-weight: 700;
            color: #ffffff;
        }

        .quota-model-sub {
            font-size: 0.78rem;
            color: var(--text-muted);
            font-family: 'JetBrains Mono', monospace;
        }

        /* PROGRESS BARS */
        .progress-block {
            display: flex;
            flex-direction: column;
            gap: 0.45rem;
        }

        .progress-label-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.82rem;
            font-weight: 600;
        }

        .progress-label {
            color: var(--text-muted);
        }

        .progress-value-badge {
            font-family: 'JetBrains Mono', monospace;
            font-weight: 700;
            color: #ffffff;
        }

        .progress-bar-bg {
            width: 100%;
            height: 10px;
            background: rgba(255, 255, 255, 0.06);
            border-radius: 9999px;
            overflow: hidden;
            position: relative;
        }

        .progress-bar-fill {
            height: 100%;
            border-radius: 9999px;
            transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .fill-groq-req {
            background: linear-gradient(90deg, #f97316, #fb923c);
            box-shadow: 0 0 10px rgba(249, 115, 22, 0.5);
        }

        .fill-groq-tok {
            background: linear-gradient(90deg, #8b5cf6, #c084fc);
            box-shadow: 0 0 10px rgba(139, 92, 246, 0.5);
        }

        .fill-gemini {
            background: linear-gradient(90deg, #2563eb, #38bdf8);
            box-shadow: 0 0 10px rgba(56, 189, 248, 0.5);
        }

        .fill-yt {
            background: linear-gradient(90deg, #ef4444, #f43f5e);
            box-shadow: 0 0 10px rgba(239, 68, 68, 0.5);
        }

        /* QUOTA INFO GRID */
        .quota-stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.75rem;
            background: rgba(0, 0, 0, 0.25);
            border-radius: 12px;
            padding: 0.875rem 1rem;
            border: 1px solid rgba(255, 255, 255, 0.04);
        }

        .stat-item {
            display: flex;
            flex-direction: column;
            gap: 0.2rem;
        }

        .stat-label {
            font-size: 0.72rem;
            color: var(--text-dim);
            text-transform: uppercase;
            letter-spacing: 0.04em;
            font-weight: 600;
        }

        .stat-val {
            font-size: 0.92rem;
            font-weight: 700;
            color: #e2e8f0;
            font-family: 'JetBrains Mono', monospace;
        }

        /* SUMMARY METRICS ROW */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 1.25rem;
        }

        .metric-card {
            background: var(--bg-card);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1.25rem 1.5rem;
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
            transition: all 0.2s ease;
        }

        .metric-card:hover {
            border-color: var(--border-glow);
            transform: translateY(-2px);
        }

        .metric-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.78rem;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .metric-value {
            font-size: 1.85rem;
            font-weight: 800;
            letter-spacing: -0.03em;
            color: #ffffff;
        }

        .metric-footer {
            font-size: 0.8rem;
            color: var(--text-dim);
        }

        /* CARD FOR CHAT LOGS */
        .card {
            background: var(--bg-card);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }

        .card-header {
            padding: 1.25rem 1.75rem;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
        }

        .card-title {
            font-size: 1.1rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 0.6rem;
        }

        .controls-group {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            flex-wrap: wrap;
        }

        .search-box {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 0.5rem 0.875rem;
            color: var(--text-main);
            font-size: 0.875rem;
            font-family: inherit;
            outline: none;
            width: 240px;
            transition: all 0.2s;
        }

        .search-box:focus {
            border-color: var(--accent-purple);
            background: rgba(255, 255, 255, 0.08);
            box-shadow: 0 0 12px rgba(139, 92, 246, 0.2);
        }

        .select-filter {
            background: #161f30;
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 0.5rem 0.875rem;
            color: var(--text-main);
            font-size: 0.875rem;
            font-family: inherit;
            outline: none;
            cursor: pointer;
        }

        .btn {
            background: linear-gradient(135deg, var(--accent-purple), var(--accent-blue));
            color: white;
            border: none;
            border-radius: 10px;
            padding: 0.55rem 1.1rem;
            font-size: 0.875rem;
            font-weight: 600;
            font-family: inherit;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            transition: all 0.2s;
        }

        .btn:hover {
            opacity: 0.92;
            transform: translateY(-1px);
            box-shadow: 0 4px 15px rgba(139, 92, 246, 0.35);
        }

        .btn-secondary {
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid var(--border-color);
            color: var(--text-main);
        }

        .btn-secondary:hover {
            background: rgba(255, 255, 255, 0.12);
            box-shadow: none;
        }

        /* CHAT TIMELINE */
        .chat-feed {
            padding: 1.5rem;
            display: flex;
            flex-direction: column;
            gap: 1.25rem;
            max-height: 680px;
            overflow-y: auto;
        }

        .chat-feed::-webkit-scrollbar { width: 6px; }
        .chat-feed::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.15);
            border-radius: 4px;
        }

        .chat-item {
            background: rgba(255, 255, 255, 0.025);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 1.25rem;
            display: flex;
            flex-direction: column;
            gap: 0.875rem;
            transition: all 0.2s ease;
        }

        .chat-item:hover {
            background: rgba(255, 255, 255, 0.045);
            border-color: rgba(255, 255, 255, 0.15);
        }

        .chat-item-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 0.5rem;
        }

        .user-tag-info {
            display: flex;
            align-items: center;
            gap: 0.6rem;
        }

        .user-avatar-badge {
            width: 32px;
            height: 32px;
            border-radius: 8px;
            background: linear-gradient(135deg, #4f46e5, #06b6d4);
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 0.9rem;
            color: #ffffff;
        }

        .user-name-text {
            font-weight: 700;
            font-size: 0.95rem;
            color: #f1f5f9;
        }

        .user-id-sub {
            font-size: 0.75rem;
            color: var(--text-dim);
            font-family: 'JetBrains Mono', monospace;
        }

        .chat-badges {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .badge-channel {
            background: rgba(59, 130, 246, 0.12);
            color: #60a5fa;
            border: 1px solid rgba(59, 130, 246, 0.25);
            font-size: 0.72rem;
            padding: 0.2rem 0.5rem;
            border-radius: 6px;
            font-weight: 600;
        }

        .badge-bot {
            background: rgba(139, 92, 246, 0.15);
            color: #c084fc;
            border: 1px solid rgba(139, 92, 246, 0.3);
            font-size: 0.72rem;
            padding: 0.2rem 0.5rem;
            border-radius: 6px;
            font-weight: 600;
        }

        .chat-time {
            font-size: 0.75rem;
            color: var(--text-dim);
            font-family: 'JetBrains Mono', monospace;
        }

        .msg-bubble-user {
            background: rgba(255, 255, 255, 0.04);
            border-left: 3px solid var(--accent-blue);
            border-radius: 0 10px 10px 0;
            padding: 0.75rem 1rem;
            font-size: 0.92rem;
            color: #e2e8f0;
            line-height: 1.5;
        }

        .msg-bubble-bot {
            background: rgba(139, 92, 246, 0.06);
            border-left: 3px solid var(--accent-purple);
            border-radius: 0 10px 10px 0;
            padding: 0.875rem 1.1rem;
            font-size: 0.92rem;
            color: #f8fafc;
            line-height: 1.6;
            white-space: pre-wrap;
        }

        .empty-state {
            text-align: center;
            padding: 3.5rem 1rem;
            color: var(--text-dim);
            font-size: 0.95rem;
        }

        /* TABS */
        .tab-buttons {
            display: flex;
            gap: 0.5rem;
            border-bottom: 1px solid var(--border-color);
            padding: 0 1.5rem;
        }

        .tab-btn {
            background: transparent;
            border: none;
            color: var(--text-muted);
            font-weight: 600;
            font-size: 0.9rem;
            padding: 1rem 1.25rem;
            cursor: pointer;
            position: relative;
            transition: all 0.2s;
        }

        .tab-btn.active {
            color: var(--accent-purple);
        }

        .tab-btn.active::after {
            content: '';
            position: absolute;
            bottom: -1px;
            left: 0;
            right: 0;
            height: 2px;
            background: var(--accent-purple);
            box-shadow: 0 0 10px var(--accent-purple);
        }

        .tab-pane { display: none; }
        .tab-pane.active { display: block; }

        /* REPORTS LIST */
        .reports-list {
            padding: 1.5rem;
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        }

        .report-card {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1rem 1.25rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: all 0.2s;
        }

        .report-card:hover {
            background: rgba(255, 255, 255, 0.05);
            border-color: var(--border-glow);
        }

        .report-name {
            font-weight: 600;
            font-size: 0.95rem;
            color: #f1f5f9;
            font-family: 'JetBrains Mono', monospace;
        }

        .report-date {
            font-size: 0.8rem;
            color: var(--text-dim);
        }

        /* MODAL */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0, 0, 0, 0.75);
            backdrop-filter: blur(8px);
            z-index: 100;
            align-items: center;
            justify-content: center;
            padding: 2rem;
        }

        .modal.open { display: flex; }

        .modal-content {
            background: #0f172a;
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 20px;
            max-width: 900px;
            width: 100%;
            max-height: 85vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        .modal-header {
            padding: 1.25rem 1.5rem;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .modal-body {
            padding: 1.5rem;
            overflow-y: auto;
            font-size: 0.9rem;
            line-height: 1.6;
            color: #cbd5e1;
            white-space: pre-wrap;
            font-family: 'JetBrains Mono', monospace;
        }
    </style>
</head>
<body>
    <header>
        <div class="brand">
            <div class="brand-logo">⚡</div>
            <div>
                <div class="brand-title">AI 4 AI • Control Hub</div>
                <div class="brand-subtitle">Trung Tâm Quản Lý Quota & Lịch Sử Tương Tác Bot</div>
            </div>
        </div>

        <div class="header-badges">
            <div class="badge badge-live">5 BOTS ACTIVE</div>
            <div class="badge" style="border-color: rgba(249, 115, 22, 0.3); color: #fb923c;">
                ⚡ Groq: <strong>openai/gpt-oss-120b</strong>
            </div>
            <div class="badge" style="border-color: rgba(139, 92, 246, 0.3); color: #c084fc;">
                🚀 Niche: <strong>__NICHE_TOPIC__</strong>
            </div>
            <div class="badge" style="color: #94a3b8;">
                ⏰ Lịch Chạy: <strong>__DAILY_RUN_TIME__</strong>
            </div>
        </div>
    </header>

    <div class="container">
        <!-- SECTION 1: VISUAL QUOTA PANELS -->
        <div class="section-header">
            <div class="section-title">
                <span>⚡ Bảng Giám Sát Hạn Mức API Thời Gian Thực (Live Quota Gauges)</span>
            </div>
            <span class="badge badge-live" style="font-size: 0.72rem;">Live Auto-sync 3s</span>
        </div>

        <div class="quota-grid">
            <!-- GROQ API QUOTA CARD -->
            <div class="quota-card quota-card-groq">
                <div class="quota-card-header">
                    <div class="quota-title-box">
                        <div class="quota-icon icon-groq">🧠</div>
                        <div>
                            <div class="quota-name">Groq LLM Engine (gpt-oss-120b)</div>
                            <div class="quota-model-sub">Rate Limits & Hạn Mức Tốc Độ Tức Thì</div>
                        </div>
                    </div>
                    <span class="badge" id="groq-status-badge" style="background: rgba(16, 185, 129, 0.15); color: #34d399; border-color: rgba(16, 185, 129, 0.3);">
                        🟢 Sẵn Sàng
                    </span>
                </div>

                <!-- GROQ REQUESTS PROGRESS -->
                <div class="progress-block">
                    <div class="progress-label-row">
                        <span class="progress-label">⚡ Số Request Khả Dụng (RPM):</span>
                        <span class="progress-value-badge" id="groq-req-badge">30 / 30 RPM (100%)</span>
                    </div>
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill fill-groq-req" id="groq-req-fill" style="width: 100%;"></div>
                    </div>
                </div>

                <!-- GROQ TOKENS PROGRESS -->
                <div class="progress-block">
                    <div class="progress-label-row">
                        <span class="progress-label">📊 Ngân Sách Tokens (TPM):</span>
                        <span class="progress-value-badge" id="groq-tok-badge">6,000 / 6,000 TPM (100%)</span>
                    </div>
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill fill-groq-tok" id="groq-tok-fill" style="width: 100%;"></div>
                    </div>
                </div>

                <!-- GROQ STATS DETAILS -->
                <div class="quota-stats-grid">
                    <div class="stat-item">
                        <span class="stat-label">Tổng Tokens Đã Dùng</span>
                        <span class="stat-val" id="groq-total-tokens">0 tokens</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Tổng Requests Đã Gọi</span>
                        <span class="stat-val" id="groq-total-requests">0 calls</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Reset Request Sau</span>
                        <span class="stat-val" id="groq-reset-req" style="color: #fb923c;">Tức thì</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Reset Tokens Sau</span>
                        <span class="stat-val" id="groq-reset-tok" style="color: #c084fc;">Tức thì</span>
                    </div>
                </div>
            </div>

            <!-- GOOGLE GEMINI & FLOW ENGINE CARD -->
            <div class="quota-card quota-card-gemini">
                <div class="quota-card-header">
                    <div class="quota-title-box">
                        <div class="quota-icon icon-gemini">🧬</div>
                        <div>
                            <div class="quota-name">Google Gemini 3.6 Flash & Flow Studio</div>
                            <div class="quota-model-sub">AI Prompt Master & Tạo Ảnh Siêu Thực 4K</div>
                        </div>
                    </div>
                    <span class="badge" id="gemini-status-badge" style="background: rgba(59, 130, 246, 0.15); color: #60a5fa; border-color: rgba(59, 130, 246, 0.3);">
                        🟢 Đang Kết Nối
                    </span>
                </div>

                <!-- GEMINI DAILY REQUESTS PROGRESS -->
                <div class="progress-block">
                    <div class="progress-label-row">
                        <span class="progress-label">🧬 Hạn Mức Gọi Ngày (RPD):</span>
                        <span class="progress-value-badge" id="gemini-rpd-badge">1,500 / 1,500 RPD (100%)</span>
                    </div>
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill fill-gemini" id="gemini-rpd-fill" style="width: 100%;"></div>
                    </div>
                </div>

                <!-- GEMINI STATS DETAILS -->
                <div class="quota-stats-grid">
                    <div class="stat-item">
                        <span class="stat-label">Thời Lượng Xử Lý (Latency)</span>
                        <span class="stat-val" id="gemini-latency-val" style="color: #38bdf8;">~850 ms</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Ảnh Flow Đã Xuất</span>
                        <span class="stat-val" id="gemini-flow-images" style="color: #a855f7;">0 ảnh</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Tổng Requests Gemini</span>
                        <span class="stat-val" id="gemini-total-calls">0 calls</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Lần Sử Dụng Gần Nhất</span>
                        <span class="stat-val" id="gemini-last-used" style="color: #34d399; font-size: 0.78rem;">Sẵn sàng</span>
                    </div>
                </div>
            </div>

            <!-- YOUTUBE API QUOTA CARD -->
            <div class="quota-card quota-card-yt">
                <div class="quota-card-header">
                    <div class="quota-title-box">
                        <div class="quota-icon icon-yt">📹</div>
                        <div>
                            <div class="quota-name">YouTube Data API v3</div>
                            <div class="quota-model-sub">Hạn Mức Quét Video & Breakout Hàng Ngày</div>
                        </div>
                    </div>
                    <span class="badge" id="yt-status-badge" style="background: rgba(16, 185, 129, 0.15); color: #34d399; border-color: rgba(16, 185, 129, 0.3);">
                        🟢 An Toàn
                    </span>
                </div>

                <!-- YOUTUBE UNITS PROGRESS -->
                <div class="progress-block">
                    <div class="progress-label-row">
                        <span class="progress-label">📹 Units Khả Dụng Trong Ngày:</span>
                        <span class="progress-value-badge" id="yt-units-badge">10,000 / 10,000 units (100%)</span>
                    </div>
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill fill-yt" id="yt-units-fill" style="width: 100%;"></div>
                    </div>
                </div>

                <!-- YOUTUBE STATS DETAILS -->
                <div class="quota-stats-grid">
                    <div class="stat-item">
                        <span class="stat-label">Units Đã Tiêu Thụ</span>
                        <span class="stat-val" id="yt-used-val">0 units</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Hạn Mức Ngày (Quota Limit)</span>
                        <span class="stat-val">10,000 units</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Thời Gian Reset Tiếp Theo</span>
                        <span class="stat-val" id="yt-reset-time" style="color: #38bdf8;">14:00 (VN)</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Đếm Ngược Reset</span>
                        <span class="stat-val" id="yt-countdown" style="color: #fb7185;">Đang tính...</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- SECTION 2: METRICS SUMMARY -->
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-header">
                    <span>Tổng Cuộc Trò Chuyện</span>
                    <span>💬</span>
                </div>
                <div class="metric-value" id="stat-total-chats">0</div>
                <div class="metric-footer" id="stat-unique-users">0 người dùng đã tương tác</div>
            </div>

            <div class="metric-card">
                <div class="metric-header">
                    <span>Server Discord</span>
                    <span>🛡️</span>
                </div>
                <div class="metric-value" style="font-size: 1.25rem;">1031727865567395840</div>
                <div class="metric-footer">Đồng bộ toàn bộ kênh & DM</div>
            </div>

            <div class="metric-card">
                <div class="metric-header">
                    <span>Trạng Thái Cảnh Báo</span>
                    <span>🚨</span>
                </div>
                <div class="metric-value" style="font-size: 1.3rem; color: #34d399;" id="alert-status-text">Bình Thường (> 20%)</div>
                <div class="metric-footer">Tự động báo động khi Quota < 20%</div>
            </div>
        </div>

        <!-- SECTION 3: CHAT HISTORY & REPORTS -->
        <div class="card">
            <div class="tab-buttons">
                <button class="tab-btn active" onclick="switchTab('chats')">💬 Lịch Sử Tương Tác Bot (Live)</button>
                <button class="tab-btn" onclick="switchTab('reports')">📄 File Báo Cáo Chuyên Sâu</button>
            </div>

            <!-- TAB 1: LIVE CHAT LOGS -->
            <div id="pane-chats" class="tab-pane active">
                <div class="card-header">
                    <div class="card-title">
                        <span>Lịch Sử Chat Thời Gian Thực</span>
                        <span class="badge badge-live" style="font-size: 0.7rem;">Auto-sync 3s</span>
                    </div>

                    <div class="controls-group">
                        <select id="filter-bot" class="select-filter" onchange="fetchChats()">
                            <option value="all">👑 Tất Cả 5 Bot</option>
                            <option value="Orchestrator">👑 Orchestrator Bot</option>
                            <option value="Market Agent">📊 Market Agent</option>
                            <option value="News Agent">📰 News Agent</option>
                            <option value="Thumbnail Agent">🎨 Thumbnail Agent</option>
                            <option value="Quota Monitor">🛡️ Quota Monitor</option>
                        </select>

                        <input type="text" id="search-input" class="search-box" placeholder="🔍 Tìm tên, nội dung chat..." oninput="debounceSearch()">
                        
                        <button class="btn btn-secondary" onclick="fetchChats()">🔄 Làm Mới</button>
                    </div>
                </div>

                <div class="chat-feed" id="chat-container">
                    <div class="empty-state">Đang tải lịch sử trò chuyện...</div>
                </div>
            </div>

            <!-- TAB 2: REPORTS LIST -->
            <div id="pane-reports" class="tab-pane">
                <div class="card-header">
                    <div class="card-title">
                        <span>Kho Lưu Trữ Báo Cáo Nghiên Cứu Thị Trường (Markdown)</span>
                    </div>
                    <button class="btn btn-secondary" onclick="fetchReports()">🔄 Cập Nhật Danh Sách</button>
                </div>
                <div class="reports-list" id="reports-container">
                    <div class="empty-state">Đang tải danh sách báo cáo...</div>
                </div>
            </div>
        </div>
    </div>

    <!-- REPORT PREVIEW MODAL -->
    <div id="report-modal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h3 id="modal-title" style="font-size: 1.1rem; color: #fff;">Xem Báo Cáo</h3>
                <button class="btn btn-secondary" onclick="closeModal()">✕ Đóng</button>
            </div>
            <div class="modal-body" id="modal-body"></div>
        </div>
    </div>

    <script>
        let searchTimeout = null;

        function debounceSearch() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(fetchChats, 300);
        }

        function switchTab(tabId) {
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));

            if (tabId === 'chats') {
                document.querySelectorAll('.tab-btn')[0].classList.add('active');
                document.getElementById('pane-chats').classList.add('active');
                fetchChats();
            } else {
                document.querySelectorAll('.tab-btn')[1].classList.add('active');
                document.getElementById('pane-reports').classList.add('active');
                fetchReports();
            }
        }

        async function fetchStats() {
            try {
                const res = await fetch('/api/stats');
                const data = await res.json();
                const q = data.quota;
                const c = data.chat_stats;
                
                // Cập nhật Groq API Quota
                document.getElementById('groq-req-badge').innerText = `${q.llm_remaining_requests} / ${q.llm_limit_requests} RPM (${q.llm_requests_pct}%)`;
                document.getElementById('groq-req-fill').style.width = `${Math.min(100, Math.max(0, q.llm_requests_pct))}%`;
                
                document.getElementById('groq-tok-badge').innerText = `${q.llm_remaining_tokens.toLocaleString()} / ${q.llm_limit_tokens.toLocaleString()} TPM (${q.llm_tokens_pct}%)`;
                document.getElementById('groq-tok-fill').style.width = `${Math.min(100, Math.max(0, q.llm_tokens_pct))}%`;
                
                document.getElementById('groq-total-tokens').innerText = `${q.llm_total_tokens.toLocaleString()} tokens`;
                document.getElementById('groq-total-requests').innerText = `${q.llm_total_requests} calls`;
                document.getElementById('groq-reset-req').innerText = q.llm_reset_requests;
                document.getElementById('groq-reset-tok').innerText = q.llm_reset_tokens;

                // Cập nhật Google Gemini & Flow Engine
                if (q.gemini_active) {
                    document.getElementById('gemini-status-badge').innerText = '🟢 Đang Kết Nối';
                    document.getElementById('gemini-rpd-badge').innerText = `${q.gemini_remaining.toLocaleString()} / ${q.gemini_daily_limit.toLocaleString()} RPD (${q.gemini_pct_remaining}%)`;
                    document.getElementById('gemini-rpd-fill').style.width = `${Math.min(100, Math.max(0, q.gemini_pct_remaining))}%`;
                    document.getElementById('gemini-latency-val').innerText = q.gemini_last_latency_ms > 0 ? `${q.gemini_last_latency_ms} ms (TB: ${q.gemini_avg_latency_ms} ms)` : '~850 ms';
                    document.getElementById('gemini-flow-images').innerText = `${q.gemini_flow_images_generated} ảnh`;
                    document.getElementById('gemini-total-calls').innerText = `${q.gemini_total_requests} calls`;
                    document.getElementById('gemini-last-used').innerText = q.gemini_last_used;
                } else {
                    document.getElementById('gemini-status-badge').innerText = '⚪ Chưa Cấu Hình';
                }

                // Cập nhật YouTube API Quota
                document.getElementById('yt-units-badge').innerText = `${q.yt_remaining.toLocaleString()} / ${q.yt_limit.toLocaleString()} units (${q.yt_pct_remaining.toFixed(1)}%)`;
                document.getElementById('yt-units-fill').style.width = `${Math.min(100, Math.max(0, q.yt_pct_remaining))}%`;
                document.getElementById('yt-used-val').innerText = `${q.yt_used.toLocaleString()} units`;
                document.getElementById('yt-reset-time').innerText = q.yt_reset_time_vn;
                document.getElementById('yt-countdown').innerText = q.yt_countdown;

                // Cập nhật Chat Stats
                document.getElementById('stat-total-chats').innerText = c.total_messages.toLocaleString();
                document.getElementById('stat-unique-users').innerText = `${c.unique_users} người dùng đã tương tác`;

                // Cập nhật Status Alert
                const isLow = q.yt_pct_remaining <= 20 || q.llm_requests_pct <= 20;
                const alertEl = document.getElementById('alert-status-text');
                if (isLow) {
                    alertEl.innerText = '⚠️ Sắp Hết Quota (< 20%)';
                    alertEl.style.color = '#f43f5e';
                } else {
                    alertEl.innerText = '🟢 Bình Thường (> 20%)';
                    alertEl.style.color = '#34d399';
                }
            } catch (err) {
                console.error("Fetch stats error:", err);
            }
        }

        async function fetchChats() {
            try {
                const botFilter = document.getElementById('filter-bot').value;
                const search = document.getElementById('search-input').value;
                
                const url = `/api/chats?bot=${encodeURIComponent(botFilter)}&search=${encodeURIComponent(search)}`;
                const res = await fetch(url);
                const chats = await res.json();

                const container = document.getElementById('chat-container');
                if (!chats || chats.length === 0) {
                    container.innerHTML = '<div class="empty-state">Chưa có dữ liệu trò chuyện nào phù hợp. Hãy thử tag bot trên Discord để bắt đầu!</div>';
                    return;
                }

                container.innerHTML = chats.map(c => {
                    const initial = (c.user_name || 'U').charAt(0).toUpperCase();
                    const isDM = c.context_type === 'DM';
                    const locationTag = isDM ? '🔒 Tin Nhắn Riêng (DM)' : c.channel_name;

                    return `
                        <div class="chat-item">
                            <div class="chat-item-header">
                                <div class="user-tag-info">
                                    <div class="user-avatar-badge">${initial}</div>
                                    <div>
                                        <div class="user-name-text">@${escapeHtml(c.user_name)}</div>
                                        <div class="user-id-sub">ID: ${c.user_id}</div>
                                    </div>
                                </div>
                                <div class="chat-badges">
                                    <span class="badge-channel">${escapeHtml(locationTag)}</span>
                                    <span class="badge-bot">🤖 ${escapeHtml(c.bot_role || c.bot_name)}</span>
                                    <span class="chat-time">${c.timestamp}</span>
                                </div>
                            </div>

                            <div class="msg-bubble-user">
                                <strong style="color: var(--accent-blue); font-size: 0.85rem;">👤 Người dùng nhắn:</strong><br>
                                ${escapeHtml(c.user_message)}
                            </div>

                            <div class="msg-bubble-bot">
                                <strong style="color: var(--accent-purple); font-size: 0.85rem;">🤖 ${escapeHtml(c.bot_name)} phản hồi:</strong><br>
                                ${escapeHtml(c.bot_response)}
                            </div>
                        </div>
                    `;
                }).join('');
            } catch (err) {
                console.error("Fetch chats error:", err);
            }
        }

        async function fetchReports() {
            try {
                const res = await fetch('/api/reports');
                const reports = await res.json();

                const container = document.getElementById('reports-container');
                if (!reports || reports.length === 0) {
                    container.innerHTML = '<div class="empty-state">Chưa có file báo cáo nào trong thư mục reports/.</div>';
                    return;
                }

                container.innerHTML = reports.map(r => `
                    <div class="report-card">
                        <div>
                            <div class="report-name">📄 ${r.filename}</div>
                            <div class="report-date">${r.modified_time} • ${(r.size / 1024).toFixed(1)} KB</div>
                        </div>
                        <button class="btn btn-secondary" onclick="viewReport('${r.filename}')">👁️ Xem Nội Dung</button>
                    </div>
                `).join('');
            } catch (err) {
                console.error("Fetch reports error:", err);
            }
        }

        async function viewReport(filename) {
            try {
                const res = await fetch(`/api/reports/${encodeURIComponent(filename)}`);
                const data = await res.json();
                document.getElementById('modal-title').innerText = `📄 ${filename}`;
                document.getElementById('modal-body').innerText = data.content;
                document.getElementById('report-modal').classList.add('open');
            } catch (err) {
                alert("Không thể tải nội dung báo cáo: " + err);
            }
        }

        function closeModal() {
            document.getElementById('report-modal').classList.remove('open');
        }

        function escapeHtml(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.innerText = text;
            return div.innerHTML;
        }

        // Tự động polling mỗi 3 giây
        fetchStats();
        fetchChats();
        setInterval(() => {
            fetchStats();
            fetchChats();
        }, 3000);
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
        reports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")
        if not os.path.exists(reports_dir):
            return web.json_response([])
        
        files = []
        for fn in sorted(os.listdir(reports_dir), reverse=True):
            if fn.endswith(".md"):
                fp = os.path.join(reports_dir, fn)
                st = os.stat(fp)
                files.append({
                    "filename": fn,
                    "size": st.st_size,
                    "modified_time": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                })
        return web.json_response(files)

    async def handle_api_report_content(request):
        filename = request.match_info.get("filename", "")
        reports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")
        fp = os.path.join(reports_dir, filename)
        if os.path.exists(fp) and filename.endswith(".md"):
            with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            return web.json_response({"content": content})
        return web.json_response({"error": "File not found"}, status=404)

    app.router.add_get("/", handle_index)
    app.router.add_get("/api/chats", handle_api_chats)
    app.router.add_get("/api/stats", handle_api_stats)
    app.router.add_get("/api/reports", handle_api_reports)
    app.router.add_get("/api/reports/{filename}", handle_api_report_content)

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
