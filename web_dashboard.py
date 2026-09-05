"""
AnimeVist Professional Web Dashboard & 24/7 Automation Hub.
Modern, sleek DevOps Control Center for managing the AnimeVist Telegram Bot,
channel broadcasting, configuration sync, and background autonomous monitoring.
Zero external dependencies (pure Python standard library).
"""

import os
import sys
import json
import time
import threading
import urllib.request
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from telegram_sender import (
    TelegramSender,
    load_config,
    save_config,
    sync_config_to_cloud,
    sync_config_to_telegram,
    fetch_config_from_telegram,
    sync_config_to_upstash,
    fetch_config_from_upstash,
    sync_config_to_supabase,
    fetch_config_from_supabase,
    test_supabase_connection
)
from series_announcer import run_series_check
from news_announcer import run_news_check
from patchnote_publisher import publish_patchnote_from_github
from pinned_navigator import publish_pinned_navigator

# Global runtime state
activity_logs = []
daemon_thread = None
daemon_running = True
daemon_paused = False
last_check_time = None
server_start_time = time.time()

def log_event(message, level="info"):
    timestamp = time.strftime('%H:%M:%S')
    entry = {"time": timestamp, "message": str(message), "level": level}
    activity_logs.append(entry)
    if len(activity_logs) > 200:
        activity_logs.pop(0)
    print(f"[{timestamp}] [{level.upper()}] {message}")

def background_monitoring_worker():
    global last_check_time, daemon_running, daemon_paused
    log_event("Служба автономного мониторинга 24/7 инициализирована", "success")

    while daemon_running:
        try:
            if not daemon_paused:
                config = load_config()
                ann_conf = config.get('announcer', {})

                # 1. Check Series Releases
                if ann_conf.get('enable_series_releases', True):
                    log_event("Авто-цикл: сканирование релизов AnimeVost & Shikimori...")
                    cnt = run_series_check()
                    if cnt > 0:
                        log_event(f"Опубликовано новых серий в канал: {cnt}", "success")
                    else:
                        log_event("Свежих непубликовавшихся эпизодов не найдено", "info")

                # 2. Check Anime News
                if ann_conf.get('enable_anime_news', True):
                    log_event("Авто-цикл: проверка аниме-новостей Shikimori...")
                    cnt_n = run_news_check()
                    if cnt_n > 0:
                        log_event(f"Опубликовано аниме-новостей: {cnt_n}", "success")

                last_check_time = time.strftime('%d.%m.%Y %H:%M:%S')
        except Exception as e:
            log_event(f"Исключение в цикле мониторинга: {e}", "error")

        # Sleep interval in 1s increments for instant response to shutdown/pause
        config = load_config()
        sleep_total = config.get('announcer', {}).get('check_interval_seconds', 300)
        for _ in range(max(10, int(sleep_total))):
            if not daemon_running:
                break
            time.sleep(1)

def get_channel_auto_detect():
    config = load_config()
    token = config.get('telegram', {}).get('bot_token')
    if not token:
        return {"ok": False, "error": "Токен бота не указан в настройках"}

    url = f"https://api.telegram.org/bot{token}/getUpdates"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'AnimeVistBot/1.0'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            results = data.get('result', [])
            for u in reversed(results):
                if 'channel_post' in u:
                    chat = u['channel_post'].get('chat', {})
                    return {
                        "ok": True,
                        "chat_id": chat.get('id'),
                        "title": chat.get('title'),
                        "username": chat.get('username')
                    }
                if 'my_chat_member' in u:
                    chat = u['my_chat_member'].get('chat', {})
                    if chat.get('type') == 'channel':
                        return {
                            "ok": True,
                            "chat_id": chat.get('id'),
                            "title": chat.get('title'),
                            "username": chat.get('username')
                        }
            return {
                "ok": False,
                "error": "В обновлениях бота пока нет сообщений из канала. Опубликуйте любое сообщение в канал (или перешлите пост боту) и повторите поиск."
            }
    except Exception as e:
        return {"ok": False, "error": str(e)}

HTML_PAGE = """<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AnimeVist — Консоль Управления Ботом 24/7</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-base: #090d16;
      --bg-surface: #0f172a;
      --bg-surface-elevated: #1e293b;
      --bg-card: #131d31;
      --bg-card-hover: #18243d;
      --bg-input: #0a0f1d;
      --border-subtle: #1e293b;
      --border-default: #334155;
      --border-focus: #3b82f6;
      --text-primary: #f8fafc;
      --text-secondary: #94a3b8;
      --text-muted: #64748b;
      --accent-blue: #3b82f6;
      --accent-blue-hover: #2563eb;
      --accent-cyan: #06b6d4;
      --success: #10b981;
      --success-bg: rgba(16, 185, 129, 0.12);
      --warning: #f59e0b;
      --warning-bg: rgba(245, 158, 11, 0.12);
      --danger: #ef4444;
      --danger-bg: rgba(239, 68, 68, 0.12);
      --radius-sm: 6px;
      --radius-md: 10px;
      --radius-lg: 14px;
      --shadow-card: 0 4px 20px -2px rgba(0, 0, 0, 0.4);
      --font-mono: 'JetBrains Mono', monospace;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background-color: var(--bg-base);
      color: var(--text-primary);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      line-height: 1.5;
      font-size: 14px;
    }

    /* Top App Header */
    header {
      background: var(--bg-surface);
      border-bottom: 1px solid var(--border-subtle);
      padding: 0.85rem 1.75rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      position: sticky;
      top: 0;
      z-index: 100;
    }
    .header-left {
      display: flex;
      align-items: center;
      gap: 14px;
    }
    .logo-badge {
      width: 36px;
      height: 36px;
      background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
      border: 1px solid rgba(59, 130, 246, 0.4);
      border-radius: var(--radius-md);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 1.1rem;
      color: #fff;
    }
    .brand-title {
      font-size: 1.05rem;
      font-weight: 700;
      letter-spacing: -0.2px;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .version-tag {
      font-size: 0.72rem;
      background: rgba(59, 130, 246, 0.15);
      color: #93c5fd;
      border: 1px solid rgba(59, 130, 246, 0.3);
      padding: 1px 7px;
      border-radius: 20px;
      font-weight: 600;
    }
    .brand-sub {
      font-size: 0.75rem;
      color: var(--text-secondary);
    }

    .header-center {
      display: flex;
      align-items: center;
      gap: 16px;
    }
    .status-pill {
      display: flex;
      align-items: center;
      gap: 8px;
      background: var(--bg-input);
      border: 1px solid var(--border-subtle);
      padding: 5px 12px;
      border-radius: 20px;
      font-size: 0.8rem;
    }
    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--success);
      box-shadow: 0 0 8px var(--success);
    }
    .status-dot.offline {
      background: var(--danger);
      box-shadow: 0 0 8px var(--danger);
    }

    .header-right {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    /* Layout & Navigation */
    .app-body {
      max-width: 1360px;
      width: 100%;
      margin: 0 auto;
      padding: 1.5rem 1.75rem;
      flex: 1;
    }

    .nav-tabs {
      display: flex;
      gap: 6px;
      background: var(--bg-surface);
      padding: 5px;
      border-radius: var(--radius-md);
      border: 1px solid var(--border-subtle);
      margin-bottom: 1.5rem;
      overflow-x: auto;
    }
    .tab-btn {
      background: transparent;
      border: none;
      color: var(--text-secondary);
      font-family: inherit;
      font-size: 0.86rem;
      font-weight: 500;
      padding: 8px 16px;
      border-radius: var(--radius-sm);
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      white-space: nowrap;
      transition: all 0.15s ease;
    }
    .tab-btn:hover {
      color: #fff;
      background: rgba(255, 255, 255, 0.04);
    }
    .tab-btn.active {
      color: #fff;
      background: var(--bg-surface-elevated);
      font-weight: 600;
      border: 1px solid var(--border-default);
    }

    .tab-content { display: none; }
    .tab-content.active { display: block; }

    /* Grid & Cards */
    .grid-kpi {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 1rem;
      margin-bottom: 1.5rem;
    }
    @media (max-width: 1024px) {
      .grid-kpi { grid-template-columns: repeat(2, 1fr); }
    }
    @media (max-width: 600px) {
      .grid-kpi { grid-template-columns: 1fr; }
    }

    .kpi-card {
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      padding: 1.25rem;
      box-shadow: var(--shadow-card);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }
    .kpi-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      color: var(--text-secondary);
      font-size: 0.8rem;
      font-weight: 500;
      margin-bottom: 8px;
    }
    .kpi-value {
      font-size: 1.35rem;
      font-weight: 700;
      color: #fff;
      margin-bottom: 4px;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .kpi-desc {
      font-size: 0.75rem;
      color: var(--text-muted);
    }

    .grid-2 {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1.25rem;
    }
    @media (max-width: 900px) {
      .grid-2 { grid-template-columns: 1fr; }
    }

    .card {
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      padding: 1.5rem;
      box-shadow: var(--shadow-card);
      margin-bottom: 1.25rem;
    }
    .card-title {
      font-size: 1.05rem;
      font-weight: 600;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 1rem;
      padding-bottom: 0.75rem;
      border-bottom: 1px solid var(--border-subtle);
    }
    .card-subtitle {
      font-size: 0.8rem;
      color: var(--text-secondary);
      margin-top: -0.5rem;
      margin-bottom: 1.25rem;
    }

    /* Buttons */
    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 8px 14px;
      border-radius: var(--radius-sm);
      font-family: inherit;
      font-size: 0.85rem;
      font-weight: 500;
      cursor: pointer;
      border: 1px solid transparent;
      transition: all 0.15s ease;
      text-decoration: none;
      white-space: nowrap;
    }
    .btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
    .btn-primary {
      background: var(--accent-blue);
      color: #fff;
    }
    .btn-primary:hover:not(:disabled) {
      background: var(--accent-blue-hover);
    }
    .btn-secondary {
      background: var(--bg-surface-elevated);
      color: var(--text-primary);
      border-color: var(--border-default);
    }
    .btn-secondary:hover:not(:disabled) {
      background: #28364c;
      border-color: #475569;
    }
    .btn-outline {
      background: transparent;
      color: var(--text-secondary);
      border-color: var(--border-default);
    }
    .btn-outline:hover:not(:disabled) {
      background: rgba(255, 255, 255, 0.05);
      color: #fff;
    }
    .btn-success {
      background: rgba(16, 185, 129, 0.15);
      color: #34d399;
      border-color: rgba(16, 185, 129, 0.3);
    }
    .btn-success:hover:not(:disabled) {
      background: rgba(16, 185, 129, 0.25);
    }
    .btn-sm { padding: 5px 10px; font-size: 0.78rem; }
    .btn-block { width: 100%; }

    /* Action Tiles */
    .action-tiles-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }
    @media (max-width: 650px) {
      .action-tiles-grid { grid-template-columns: 1fr; }
    }
    .action-tile {
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      padding: 1.1rem;
      cursor: pointer;
      transition: all 0.15s ease;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      position: relative;
    }
    .action-tile:hover {
      border-color: var(--border-default);
      background: var(--bg-card-hover);
      transform: translateY(-1px);
    }
    .tile-top {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 8px;
    }
    .tile-icon {
      width: 34px;
      height: 34px;
      background: rgba(59, 130, 246, 0.1);
      border: 1px solid rgba(59, 130, 246, 0.25);
      border-radius: var(--radius-sm);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.1rem;
    }
    .tile-title {
      font-size: 0.92rem;
      font-weight: 600;
      color: #fff;
    }
    .tile-tag {
      font-size: 0.7rem;
      font-family: var(--font-mono);
      color: var(--accent-cyan);
    }
    .tile-desc {
      font-size: 0.78rem;
      color: var(--text-secondary);
      line-height: 1.4;
      margin-bottom: 10px;
    }
    .tile-footer {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 0.75rem;
      color: var(--text-muted);
      border-top: 1px solid var(--border-subtle);
      padding-top: 8px;
    }

    /* Form Controls */
    .form-group {
      margin-bottom: 1.25rem;
    }
    .form-label {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 0.82rem;
      font-weight: 500;
      color: var(--text-secondary);
      margin-bottom: 6px;
    }
    .input-wrapper {
      position: relative;
      display: flex;
      align-items: center;
    }
    input[type="text"], input[type="password"], input[type="number"], textarea, select {
      width: 100%;
      background: var(--bg-input);
      border: 1px solid var(--border-default);
      color: #fff;
      padding: 9px 12px;
      border-radius: var(--radius-sm);
      font-size: 0.88rem;
      font-family: inherit;
      outline: none;
      transition: border-color 0.15s, box-shadow 0.15s;
    }
    input[type="text"]:focus, input[type="password"]:focus, input[type="number"]:focus, textarea:focus, select:focus {
      border-color: var(--border-focus);
      box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
    }
    .input-toggle-btn {
      position: absolute;
      right: 8px;
      background: transparent;
      border: none;
      color: var(--text-muted);
      cursor: pointer;
      padding: 4px;
      font-size: 0.85rem;
    }
    .input-toggle-btn:hover { color: #fff; }

    .preset-chips {
      display: flex;
      gap: 6px;
      margin-top: 6px;
    }
    .preset-chip {
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      color: var(--text-secondary);
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 0.75rem;
      cursor: pointer;
    }
    .preset-chip:hover {
      border-color: var(--border-default);
      color: #fff;
    }

    /* Modern Switch Control */
    .switch-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 12px;
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-sm);
      margin-bottom: 8px;
    }
    .switch-title {
      font-size: 0.85rem;
      font-weight: 500;
      color: #fff;
    }
    .switch-sub {
      font-size: 0.74rem;
      color: var(--text-muted);
    }
    .switch {
      position: relative;
      display: inline-block;
      width: 42px;
      height: 22px;
      flex-shrink: 0;
    }
    .switch input { opacity: 0; width: 0; height: 0; }
    .slider {
      position: absolute; cursor: pointer;
      top: 0; left: 0; right: 0; bottom: 0;
      background-color: #334155;
      transition: .2s;
      border-radius: 22px;
    }
    .slider:before {
      position: absolute; content: "";
      height: 16px; width: 16px; left: 3px; bottom: 3px;
      background-color: white;
      transition: .2s;
      border-radius: 50%;
    }
    input:checked + .slider { background-color: var(--accent-blue); }
    input:checked + .slider:before { transform: translateX(20px); }

    /* Live Terminal Console */
    .console-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 10px;
      flex-wrap: wrap;
      gap: 10px;
    }
    .console-filters {
      display: flex;
      gap: 6px;
      align-items: center;
    }
    .filter-btn {
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      color: var(--text-muted);
      padding: 4px 10px;
      border-radius: var(--radius-sm);
      font-size: 0.75rem;
      cursor: pointer;
    }
    .filter-btn.active {
      background: var(--bg-surface-elevated);
      color: #fff;
      border-color: var(--border-default);
    }
    .terminal-window {
      background: #05080f;
      border: 1px solid #1a2333;
      border-radius: var(--radius-md);
      font-family: var(--font-mono);
      font-size: 0.8rem;
      height: 420px;
      overflow-y: auto;
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 5px;
    }
    .log-line {
      display: flex;
      gap: 12px;
      line-height: 1.45;
      border-radius: 4px;
      padding: 2px 4px;
    }
    .log-line:hover { background: rgba(255, 255, 255, 0.03); }
    .log-ts { color: var(--text-muted); flex-shrink: 0; }
    .log-lvl {
      padding: 1px 6px;
      border-radius: 3px;
      font-size: 0.7rem;
      font-weight: 600;
      flex-shrink: 0;
    }
    .log-lvl.info { background: rgba(59, 130, 246, 0.15); color: #60a5fa; }
    .log-lvl.success { background: rgba(16, 185, 129, 0.15); color: #34d399; }
    .log-lvl.error { background: rgba(239, 68, 68, 0.15); color: #f87171; }
    .log-msg { color: #e2e8f0; word-break: break-word; }

    /* Cloud Guide Steps */
    .guide-step {
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      padding: 1.25rem;
      margin-bottom: 1rem;
    }
    .guide-badge {
      display: inline-block;
      background: rgba(59, 130, 246, 0.15);
      color: #93c5fd;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 0.72rem;
      font-weight: 600;
      margin-bottom: 8px;
    }
    .code-block {
      background: #05080f;
      border: 1px solid #1e293b;
      border-radius: var(--radius-sm);
      padding: 8px 12px;
      font-family: var(--font-mono);
      font-size: 0.78rem;
      color: #93c5fd;
      margin: 8px 0;
      display: flex;
      justify-content: space-between;
      align-items: center;
      overflow-x: auto;
    }

    /* Toast Notification System */
    #toastContainer {
      position: fixed;
      bottom: 24px;
      right: 24px;
      z-index: 9999;
      display: flex;
      flex-direction: column;
      gap: 8px;
      max-width: 380px;
      width: calc(100% - 48px);
    }
    .toast {
      background: var(--bg-surface-elevated);
      border: 1px solid var(--border-default);
      color: #fff;
      padding: 12px 16px;
      border-radius: var(--radius-md);
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      animation: slideIn 0.2s ease forwards;
      font-size: 0.85rem;
    }
    .toast.success { border-color: rgba(16, 185, 129, 0.4); }
    .toast.error { border-color: rgba(239, 68, 68, 0.4); }
    .toast.info { border-color: rgba(59, 130, 246, 0.4); }
    @keyframes slideIn {
      from { transform: translateY(20px); opacity: 0; }
      to { transform: translateY(0); opacity: 1; }
    }
  </style>
</head>
<body>

  <!-- Top System Header -->
  <header>
    <div class="header-left">
      <div class="logo-badge">AV</div>
      <div>
        <div class="brand-title">
          AnimeVist <span>Bot Console</span>
          <span class="version-tag">24/7 v2.2</span>
        </div>
        <div class="brand-sub">Операционный центр автоматизации Telegram-канала</div>
      </div>
    </div>

    <div class="header-center">
      <div class="status-pill">
        <div class="status-dot" id="headerDot"></div>
        <span id="headerStatusText">Подключение к боту...</span>
      </div>
    </div>

    <div class="header-right">
      <button class="btn btn-secondary btn-sm" onclick="sendTestMessage()" title="Отправить проверочное сообщение в канал">
        💬 Тест канала
      </button>
      <button class="btn btn-primary btn-sm" onclick="runAction('releases')" title="Запустить проверку прямо сейчас">
        ⚡ Сканировать серии
      </button>
      <button class="btn btn-outline btn-sm" onclick="loadData()" title="Перезагрузить статус">
        🔄
      </button>
    </div>
  </header>

  <!-- Main Body Container -->
  <main class="app-body">
    <!-- Tab Navigation -->
    <nav class="nav-tabs">
      <button class="tab-btn active" onclick="switchTab('tab-overview', this)">📊 Мониторинг & KPI</button>
      <button class="tab-btn" onclick="switchTab('tab-actions', this)">⚡ Центр действий</button>
      <button class="tab-btn" onclick="switchTab('tab-config', this)">⚙️ Конфигурация</button>
      <button class="tab-btn" onclick="switchTab('tab-storage', this)">💾 Облачное хранилище</button>
      <button class="tab-btn" onclick="switchTab('tab-guide', this)">☁️ Развертывание 24/7</button>
      <button class="tab-btn" onclick="switchTab('tab-console', this)">📟 Консоль логов</button>
    </nav>

    <!-- TAB 1: OVERVIEW -->
    <section id="tab-overview" class="tab-content active">
      <div class="grid-kpi">
        <div class="kpi-card">
          <div class="kpi-header">
            <span>TELEGRAM BOT</span>
            <span>🤖</span>
          </div>
          <div class="kpi-value" id="kpiBotUser">Загрузка...</div>
          <div class="kpi-desc" id="kpiBotId">ID: —</div>
        </div>

        <div class="kpi-card">
          <div class="kpi-header">
            <span>ЦЕЛЕВОЙ КАНАЛ</span>
            <span>📢</span>
          </div>
          <div class="kpi-value" id="kpiChannel">—</div>
          <div class="kpi-desc" id="kpiChannelLink">Официальный вещатель</div>
        </div>

        <div class="kpi-card">
          <div class="kpi-header">
            <span>ДЕМОН 24/7</span>
            <span>⏱️</span>
          </div>
          <div class="kpi-value" style="color:var(--success);" id="kpiDaemonStatus">Активен</div>
          <div class="kpi-desc" id="kpiInterval">Интервал: 300 сек (5 мин)</div>
        </div>

        <div class="kpi-card">
          <div class="kpi-header">
            <span>ХРАНИЛИЩЕ НАСТРОЕК</span>
            <span>💾</span>
          </div>
          <div class="kpi-value" id="kpiStorageMode">Local JSON</div>
          <div class="kpi-desc" id="kpiLastSync">Синхронизация: —</div>
        </div>
      </div>

      <div class="grid-2">
        <div class="card">
          <div class="card-title">⚡ 4 Основных Модуля Автопостинга</div>
          <div class="card-subtitle">Запуск любого модуля одним кликом для немедленной публикации в Telegram:</div>

          <div class="action-tiles-grid">
            <div class="action-tile" onclick="runAction('releases')">
              <div class="tile-top">
                <div class="tile-icon">📺</div>
                <div>
                  <div class="tile-title">1. Выход серий</div>
                  <div class="tile-tag">#release</div>
                </div>
              </div>
              <div class="tile-desc">Парсинг AnimeVost + Shikimori и публикация карточки свежего эпизода.</div>
              <div class="tile-footer">
                <span>Ручной запуск</span>
                <span class="btn btn-outline btn-sm">Старт ➔</span>
              </div>
            </div>

            <div class="action-tile" onclick="runAction('news')">
              <div class="tile-top">
                <div class="tile-icon">📰</div>
                <div>
                  <div class="tile-title">2. Аниме-новости</div>
                  <div class="tile-tag">#news</div>
                </div>
              </div>
              <div class="tile-desc">Официальные анонсы, трейлеры и новости аниме-индустрии.</div>
              <div class="tile-footer">
                <span>Ручной запуск</span>
                <span class="btn btn-outline btn-sm">Старт ➔</span>
              </div>
            </div>

            <div class="action-tile" onclick="runAction('patchnote')">
              <div class="tile-top">
                <div class="tile-icon">🚀</div>
                <div>
                  <div class="tile-title">3. Патчноут релиза</div>
                  <div class="tile-tag">#patchnote</div>
                </div>
              </div>
              <div class="tile-desc">Авто-публикация свежего релиза приложения из GitHub Releases.</div>
              <div class="tile-footer">
                <span>Ручной запуск</span>
                <span class="btn btn-outline btn-sm">Старт ➔</span>
              </div>
            </div>

            <div class="action-tile" onclick="runAction('pinned')">
              <div class="tile-top">
                <div class="tile-icon">📌</div>
                <div>
                  <div class="tile-title">4. Закрепленный навигатор</div>
                  <div class="tile-tag">Pin FAQ</div>
                </div>
              </div>
              <div class="tile-desc">Главный пост-навигатор со ссылками на APK, EXE и чат обсуждений.</div>
              <div class="tile-footer">
                <span>Ручной запуск</span>
                <span class="btn btn-outline btn-sm">Старт ➔</span>
              </div>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-title">📡 Состояние Циклов Автопостинга</div>
          <div style="display:flex; flex-direction:column; gap:12px; margin-bottom:18px;">
            <div style="display:flex; justify-content:space-between; padding-bottom:8px; border-bottom:1px solid var(--border-subtle);">
              <span style="color:var(--text-secondary);">Фоновый поток:</span>
              <strong style="color:var(--success);" id="daemonThreadState">Работает непрерывно</strong>
            </div>
            <div style="display:flex; justify-content:space-between; padding-bottom:8px; border-bottom:1px solid var(--border-subtle);">
              <span style="color:var(--text-secondary);">Последний опрос:</span>
              <span style="font-family:var(--font-mono); color:#fff;" id="overviewLastCheck">Только что</span>
            </div>
            <div style="display:flex; justify-content:space-between; padding-bottom:8px; border-bottom:1px solid var(--border-subtle);">
              <span style="color:var(--text-secondary);">Чат обсуждений:</span>
              <span style="font-family:var(--font-mono); color:var(--accent-cyan);" id="overviewChatId">—</span>
            </div>
            <div style="display:flex; justify-content:space-between; padding-bottom:8px; border-bottom:1px solid var(--border-subtle);">
              <span style="color:var(--text-secondary);">Время работы сервера:</span>
              <span style="font-family:var(--font-mono); color:#fff;" id="overviewUptime">0 мин</span>
            </div>
          </div>

          <div style="display:flex; gap:10px;">
            <button class="btn btn-secondary btn-block" onclick="autoDetectChannel()">
              🔍 Найти ID канала автоматически
            </button>
            <button class="btn btn-outline btn-block" onclick="toggleDaemon()">
              ⏸️ Приостановить/Возобновить
            </button>
          </div>
        </div>
      </div>
    </section>

    <!-- TAB 2: ACTIONS -->
    <section id="tab-actions" class="tab-content">
      <div class="grid-2">
        <div class="card">
          <div class="card-title">💬 Экспресс-Отправка Сообщения в Канал</div>
          <div class="card-subtitle">Отправка форматированного объявления с поддержкой HTML-тегов (&lt;b&gt;, &lt;i&gt;, &lt;a&gt;, &lt;code&gt;):</div>

          <div class="form-group">
            <label class="form-label">Текст сообщения:</label>
            <textarea id="customMsgText" rows="6" placeholder="Привет! 🎬 Мы опубликовали новое обновление..."></textarea>
          </div>

          <div style="display:flex; justify-content:space-between; align-items:center;">
            <label style="display:flex; align-items:center; gap:8px; font-size:0.8rem; color:var(--text-secondary); cursor:pointer;">
              <input type="checkbox" id="customMsgDisablePreview"> Отключить предпросмотр ссылок
            </label>
            <button class="btn btn-primary" onclick="sendCustomMessage()">
              🚀 Опубликовать в канал
            </button>
          </div>
        </div>

        <div class="card">
          <div class="card-title">🛠️ Сервисные Проверки и Инструменты</div>
          <div class="card-subtitle">Диагностика соединений с API Telegram, Shikimori и GitHub:</div>

          <div style="display:flex; flex-direction:column; gap:10px;">
            <button class="btn btn-secondary" onclick="sendTestMessage()">
              📢 1. Отправить проверочное сообщение от бота
            </button>
            <button class="btn btn-secondary" onclick="autoDetectChannel()">
              🔍 2. Обнаружить ID канала из последних входящих сообщений
            </button>
            <button class="btn btn-secondary" onclick="runAction('patchnote')">
              📦 3. Проверить последний релиз на GitHub (magver/AnimeVist-Releases)
            </button>
            <button class="btn btn-secondary" onclick="syncCloudNow()">
              ☁️ 4. Сделать немедленный бэкап настроек в облако
            </button>
          </div>
        </div>
      </div>
    </section>

    <!-- TAB 3: CONFIGURATION -->
    <section id="tab-config" class="tab-content">
      <div class="card" style="max-width: 820px; margin: 0 auto;">
        <div class="card-title">⚙️ Настройки Telegram & Параметров Автоматизации</div>
        <div class="card-subtitle">Все изменения сохраняются в конфигурацию и мгновенно вступают в силу без перезапуска сервера.</div>

        <h3 style="font-size:0.9rem; color:var(--accent-blue); margin-bottom:12px; text-transform:uppercase; letter-spacing:0.5px;">1. Ключи и авторизация Telegram</h3>
        
        <div class="form-group">
          <div class="form-label">
            <span>Токен Telegram-бота (от @BotFather):</span>
            <span style="font-size:0.75rem; color:var(--text-muted);">Никогда не публикуйте публично</span>
          </div>
          <div class="input-wrapper">
            <input type="password" id="cfg_token" placeholder="8958974614:AAF-...">
            <button type="button" class="input-toggle-btn" onclick="togglePasswordVisibility('cfg_token', this)">👁️</button>
          </div>
        </div>

        <div class="grid-2">
          <div class="form-group">
            <div class="form-label">
              <span>ID или юзернейм канала:</span>
              <a href="javascript:void(0)" onclick="autoDetectChannel()" style="color:var(--accent-cyan); text-decoration:none; font-size:0.75rem;">🔍 Найти ID</a>
            </div>
            <input type="text" id="cfg_channel" placeholder="-1004465332635 или @animevist">
          </div>

          <div class="form-group">
            <div class="form-label">
              <span>ID или ссылка чата обсуждений:</span>
            </div>
            <input type="text" id="cfg_chat" placeholder="https://t.me/animevist_chat">
          </div>
        </div>

        <div class="form-group">
          <div class="form-label">
            <span>ID Telegram Администратора:</span>
            <span style="font-size:0.75rem; color:var(--text-muted);">Для отправки сервисных алертов</span>
          </div>
          <input type="text" id="cfg_admin" placeholder="869155357">
        </div>

        <h3 style="font-size:0.9rem; color:var(--accent-blue); margin-top:24px; margin-bottom:12px; text-transform:uppercase; letter-spacing:0.5px;">2. Режимы автопостинга</h3>

        <div class="switch-row">
          <div>
            <div class="switch-title">Автопостинг выхода новых серий (#release)</div>
            <div class="switch-sub">Опрашивать AnimeVost + Shikimori каждые N секунд и публиковать карточки серий</div>
          </div>
          <label class="switch">
            <input type="checkbox" id="cfg_releases_enabled" checked>
            <span class="slider"></span>
          </label>
        </div>

        <div class="switch-row">
          <div>
            <div class="switch-title">Автопостинг аниме-новостей (#news)</div>
            <div class="switch-sub">Публиковать официальные новости, трейлеры и анонсы новых сезонов</div>
          </div>
          <label class="switch">
            <input type="checkbox" id="cfg_news_enabled" checked>
            <span class="slider"></span>
          </label>
        </div>

        <div class="form-group" style="margin-top:14px;">
          <div class="form-label">
            <span>Интервал фонового опроса (секунды):</span>
            <span id="intervalReadable" style="color:var(--text-muted); font-size:0.75rem;">5 минут</span>
          </div>
          <input type="number" id="cfg_interval" value="300" min="30" step="30" oninput="updateIntervalReadable(this.value)">
          <div class="preset-chips">
            <span class="preset-chip" onclick="setPresetInterval(60)">1 мин</span>
            <span class="preset-chip" onclick="setPresetInterval(180)">3 мин</span>
            <span class="preset-chip" onclick="setPresetInterval(300)">5 мин (реком.)</span>
            <span class="preset-chip" onclick="setPresetInterval(600)">10 мин</span>
            <span class="preset-chip" onclick="setPresetInterval(1800)">30 мин</span>
          </div>
        </div>

        <div style="margin-top:25px;">
          <button class="btn btn-primary btn-block" onclick="saveSettings()">
            💾 Сохранить и применить конфигурацию
          </button>
        </div>
      </div>
    </section>

    <!-- TAB 4: CLOUD STORAGE -->
    <section id="tab-storage" class="tab-content">
      <div class="card" style="max-width: 820px; margin: 0 auto;">
        <div class="card-title">💾 Облачное Хранилище Настроек (Защита от сброса)</div>
        <div class="card-subtitle">
          На бесплатных контейнерных хостингах (Hugging Face, Render, Docker) файловая система эемерна — файлы сбрасываются при перезапуске контейнера. Выберите надежный способ хранения:
        </div>

        <div class="form-group">
          <label class="form-label">Провайдер хранения конфигурации:</label>
          <select id="storage_provider" onchange="onStorageProviderChange(this.value)">
            <option value="telegram">🟢 Telegram Cloud Storage (Встроенное, без сторонних сервисов — РЕКОМЕНДУЕТСЯ)</option>
            <option value="local">📁 Локальный файл config.json (Для ПК и постоянных VPS)</option>
            <option value="upstash">⚡ Upstash Redis (Бесплатный REST Serverless Key-Value)</option>
            <option value="supabase">🐘 Supabase (Бесплатный PostgreSQL REST)</option>
          </select>
        </div>

        <!-- Telegram Cloud Options -->
        <div id="storage-opts-telegram" style="background:var(--bg-surface); border:1px solid var(--border-subtle); border-radius:var(--radius-sm); padding:14px; margin-bottom:15px;">
          <h4 style="color:#fff; font-size:0.88rem; margin-bottom:6px;">🔐 Telegram Cloud Storage</h4>
          <p style="font-size:0.8rem; color:var(--text-secondary); margin-bottom:12px;">
            Бот отправляет зашифрованный JSON бэкап настроек в ваш личный служебный чат или канал и закрепляет его. При старте контейнера настройки считываются автоматически! 100% бесплатно и навсегда.
          </p>
          <div class="form-group" style="margin-bottom:0;">
            <label class="form-label">ID служебного чата/канала для хранения:</label>
            <input type="text" id="storage_tg_chat" placeholder="Ваш Telegram ID (например 869155357) или ID приватного канала">
          </div>
        </div>

        <!-- Upstash Options -->
        <div id="storage-opts-upstash" style="display:none; background:var(--bg-surface); border:1px solid var(--border-subtle); border-radius:var(--radius-sm); padding:14px; margin-bottom:15px;">
          <h4 style="color:#fff; font-size:0.88rem; margin-bottom:6px;">⚡ Upstash Redis REST</h4>
          <p style="font-size:0.8rem; color:var(--text-secondary); margin-bottom:12px;">
            Бесплатный тариф без карт на upstash.com (10 000 запросов в день).
          </p>
          <div class="form-group">
            <label class="form-label">UPSTASH_REDIS_REST_URL:</label>
            <input type="text" id="storage_upstash_url" placeholder="https://...upstash.io">
          </div>
          <div class="form-group" style="margin-bottom:0;">
            <label class="form-label">UPSTASH_REDIS_REST_TOKEN:</label>
            <input type="password" id="storage_upstash_token" placeholder="AXXX...">
          </div>
        </div>

        <!-- Supabase Options -->
        <div id="storage-opts-supabase" style="display:none; background:var(--bg-surface); border:1px solid rgba(16,185,129,0.3); border-radius:var(--radius-sm); padding:16px; margin-bottom:15px;">
          <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;">
            <h4 style="color:#fff; font-size:0.92rem; display:flex; align-items:center; gap:8px;">
              <span>🐘 Supabase Database (Экосистема AnimeVist)</span>
              <span style="font-size:0.7rem; background:rgba(16,185,129,0.15); color:#34d399; padding:2px 8px; border-radius:12px; font-weight:600;">АКТИВНА</span>
            </h4>
            <button class="btn btn-outline btn-sm" onclick="testSupabaseConnection()">
              🔌 Проверить связь
            </button>
          </div>
          <p style="font-size:0.8rem; color:var(--text-secondary); margin-bottom:12px; line-height:1.45;">
            Ваша существующая облачная база данных AnimeVist уже подключена! Бот может хранить свои настройки (таблица <code>bot_config</code>) и историю опубликованных серий (таблица <code>bot_seen_items</code>) прямо в вашей базе. Данные никогда не сотрутся.
          </p>

          <div style="background:#05080f; border:1px solid #1e293b; border-radius:6px; padding:10px 12px; margin-bottom:14px; font-size:0.78rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <span style="color:#93c5fd; font-weight:600;">⚡ Настройка таблиц в Supabase (1 раз):</span>
              <button class="btn btn-outline btn-sm" style="font-size:0.72rem; padding:2px 8px;" onclick="copySupabaseSql()">
                📋 Скопировать SQL-код
              </button>
            </div>
            <p style="color:var(--text-muted); font-size:0.74rem;">
              Откройте <a href="https://supabase.com/dashboard" target="_blank" style="color:var(--accent-blue);">Supabase Dashboard</a> &rarr; <b>SQL Editor</b> &rarr; вставьте скопированный скрипт из файла <code>supabase_bot_schema.sql</code> и нажмите <b>Run</b>.
            </p>
          </div>

          <div class="form-group">
            <label class="form-label">SUPABASE_URL:</label>
            <input type="text" id="storage_supabase_url" placeholder="https://zuciuwunelfqhhhohhyn.supabase.co">
          </div>
          <div class="form-group" style="margin-bottom:0;">
            <label class="form-label">SUPABASE_ANON_KEY:</label>
            <input type="password" id="storage_supabase_key" placeholder="eyJhbG...">
          </div>
        </div>

        <div style="display:flex; gap:12px; margin-top:20px;">
          <button class="btn btn-primary btn-block" onclick="syncCloudNow()">
            ☁️ Сделать бэкап в облако прямо сейчас
          </button>
          <button class="btn btn-secondary btn-block" onclick="fetchCloudNow()">
            📥 Восстановить конфигурацию из облака
          </button>
        </div>
      </div>
    </section>

    <!-- TAB 5: CLOUD HOSTING GUIDE -->
    <section id="tab-guide" class="tab-content">
      <div class="card" style="max-width: 900px; margin: 0 auto;">
        <div class="card-title">☁️ Развертывание 24/7 БЕЗ привязки банковских карт</div>
        <div class="card-subtitle">
          Актуальный рейтинг и пошаговые инструкции запуска сервиса в облаке для непрерывной работы без включенного ПК:
        </div>

        <div class="guide-step">
          <span class="guide-badge" style="background:rgba(16,185,129,0.15); color:#34d399;">ТОП-1 РЕКОМЕНДАЦИЯ (2 минуты)</span>
          <h3 style="color:#fff; font-size:1rem; margin-bottom:6px;">Hugging Face Spaces (Docker 24/7)</h3>
          <p style="color:var(--text-secondary); font-size:0.84rem; line-height:1.5;">
            <b>Плюсы:</b> 100% бесплатно, <b>банковская карта не требуется вовсе</b>, дает 2 vCPU и 16 GB RAM, постоянный HTTPS-домен, контейнер <b>не засыпает</b>.<br><br>
            <b>Инструкция по деплою:</b><br>
            1. Зарегистрируйтесь на <a href="https://huggingface.co" target="_blank" style="color:var(--accent-blue);">huggingface.co</a> (через GitHub или почту).<br>
            2. Нажмите <b>Create New Space</b> &rarr; выберите <b>Docker (Blank)</b>.<br>
            3. В настройках Space (Settings) нажмите <b>«Connect GitHub Repository»</b> и укажите репозиторий <code>AnimeVist-Telegram-Bot</code>.<br>
            4. Hugging Face автоматически соберет Dockerfile и запустит панель на постоянном публичном адресе с поддержкой 24/7!
          </p>
        </div>

        <div class="guide-step">
          <span class="guide-badge">КЛАССИЧЕСКИЙ ХОСТИНГ</span>
          <h3 style="color:#fff; font-size:1rem; margin-bottom:6px;">Serv00.com (FreeBSD + SSH)</h3>
          <p style="color:var(--text-secondary); font-size:0.84rem; line-height:1.5;">
            <b>Плюсы:</b> Бесплатный виртуальный хостинг с полноценным SSH-доступом и поддержкой Python без ввода карты.<br><br>
            <b>Команды в консоли SSH:</b>
          </p>
          <div class="code-block">
            <span>git clone https://github.com/magver/AnimeVist-Telegram-Bot.git && cd AnimeVist-Telegram-Bot</span>
            <button class="btn btn-outline btn-sm" onclick="copyCode(this)">Скопировать</button>
          </div>
          <div class="code-block">
            <span>nohup python3 web_dashboard.py > bot.log 2>&1 &</span>
            <button class="btn btn-outline btn-sm" onclick="copyCode(this)">Скопировать</button>
          </div>
        </div>

        <div class="guide-step">
          <span class="guide-badge">БЕЗ СЕРВЕРОВ ВООБЩЕ</span>
          <h3 style="color:#fff; font-size:1rem; margin-bottom:6px;">Встроенный GitHub Actions</h3>
          <p style="color:var(--text-secondary); font-size:0.84rem; line-height:1.5;">
            В репозиторий уже встроены файлы <code>.github/workflows/auto_announcer.yml</code>.<br>
            Сервер не нужен вообще: GitHub сам запускает проверку серий и новостей по таймеру каждые 15 минут в облаке GitHub бесплатно!
          </p>
        </div>
      </div>
    </section>

    <!-- TAB 6: LIVE CONSOLE -->
    <section id="tab-console" class="tab-content">
      <div class="card">
        <div class="console-header">
          <div style="display:flex; align-items:center; gap:10px;">
            <div class="card-title" style="margin-bottom:0; padding-bottom:0; border:none;">📟 Системный Журнал в Реальном Времени</div>
            <span class="status-dot"></span>
          </div>

          <div class="console-filters">
            <input type="text" id="logSearchInput" placeholder="Поиск по логам..." style="padding:4px 8px; font-size:0.75rem; width:160px;" oninput="filterLogs()">
            <button class="filter-btn active" onclick="setLogFilter('all', this)">Все</button>
            <button class="filter-btn" onclick="setLogFilter('success', this)">Успех</button>
            <button class="filter-btn" onclick="setLogFilter('info', this)">Инфо</button>
            <button class="filter-btn" onclick="setLogFilter('error', this)">Ошибки</button>
            <button class="btn btn-outline btn-sm" onclick="clearConsoleView()">Очистить</button>
            <button class="btn btn-secondary btn-sm" onclick="copyAllLogs()">Копировать</button>
          </div>
        </div>

        <div class="terminal-window" id="terminalBox">
          <!-- Real-time log entries inserted here -->
        </div>

        <div style="margin-top:10px; display:flex; justify-content:space-between; align-items:center;">
          <label style="display:flex; align-items:center; gap:6px; font-size:0.75rem; color:var(--text-muted); cursor:pointer;">
            <input type="checkbox" id="autoScrollCheck" checked> Автопрокрутка к новым записям
          </label>
          <span style="font-size:0.75rem; color:var(--text-muted);" id="logCountText">Всего записей: 0</span>
        </div>
      </div>
    </section>
  </main>

  <!-- Toast Notification Container -->
  <div id="toastContainer"></div>

  <script>
    let currentLogFilter = 'all';
    let rawLogs = [];

    function showToast(message, type = 'info', duration = 3500) {
      const c = document.getElementById('toastContainer');
      const t = document.createElement('div');
      t.className = `toast ${type}`;
      
      const icon = type === 'success' ? '✅' : (type === 'error' ? '❌' : 'ℹ️');
      t.innerHTML = `<span>${icon} ${message}</span><button style="background:transparent; border:none; color:#94a3b8; cursor:pointer; font-size:1rem;" onclick="this.parentElement.remove()">&times;</button>`;
      
      c.appendChild(t);
      setTimeout(() => {
        t.style.opacity = '0';
        t.style.transform = 'translateY(10px)';
        t.style.transition = 'all 0.2s';
        setTimeout(() => t.remove(), 200);
      }, duration);
    }

    function switchTab(tabId, el) {
      document.querySelectorAll('.tab-content').forEach(p => p.classList.remove('active'));
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      const target = document.getElementById(tabId);
      if (target) target.classList.add('active');
      if (el) el.classList.add('active');
    }

    function togglePasswordVisibility(id, btn) {
      const input = document.getElementById(id);
      if (input.type === 'password') {
        input.type = 'text';
        btn.innerText = '🙈';
      } else {
        input.type = 'password';
        btn.innerText = '👁️';
      }
    }

    function setPresetInterval(sec) {
      document.getElementById('cfg_interval').value = sec;
      updateIntervalReadable(sec);
    }

    function updateIntervalReadable(val) {
      const v = parseInt(val) || 300;
      const min = Math.round(v / 60);
      document.getElementById('intervalReadable').innerText = `${min} мин (${v} сек)`;
    }

    function onStorageProviderChange(val) {
      document.getElementById('storage-opts-telegram').style.display = val === 'telegram' ? 'block' : 'none';
      document.getElementById('storage-opts-upstash').style.display = val === 'upstash' ? 'block' : 'none';
      document.getElementById('storage-opts-supabase').style.display = val === 'supabase' ? 'block' : 'none';
    }

    async function loadData() {
      try {
        const res = await fetch('/api/status');
        const data = await res.json();
        
        // Bot Identity
        if (data.bot) {
          const username = '@' + data.bot.username;
          document.getElementById('headerStatusText').innerText = `Онлайн: ${username}`;
          document.getElementById('headerDot').className = 'status-dot';
          document.getElementById('kpiBotUser').innerText = username;
          document.getElementById('kpiBotId').innerText = `ID: ${data.bot.id} (${data.bot.first_name})`;
        } else {
          document.getElementById('headerStatusText').innerText = 'Бот оффлайн (проверьте токен)';
          document.getElementById('headerDot').className = 'status-dot offline';
          document.getElementById('kpiBotUser').innerText = 'Не подключен';
        }

        // Config fields
        if (data.config) {
          const tg = data.config.telegram || {};
          const app = data.config.app || {};
          const ann = data.config.announcer || {};
          const cloud = data.config.cloud_storage || {};

          document.getElementById('cfg_token').value = tg.bot_token || '';
          document.getElementById('cfg_channel').value = tg.channel_id || '';
          document.getElementById('cfg_chat').value = app.chat_invite_url || '';
          document.getElementById('cfg_admin').value = tg.admin_id || '';
          
          document.getElementById('cfg_interval').value = ann.check_interval_seconds || 300;
          updateIntervalReadable(ann.check_interval_seconds || 300);

          document.getElementById('cfg_releases_enabled').checked = ann.enable_series_releases !== false;
          document.getElementById('cfg_news_enabled').checked = ann.enable_anime_news !== false;

          document.getElementById('kpiChannel').innerText = tg.channel_id || 'Не задан';
          document.getElementById('kpiInterval').innerText = `Интервал: ${ann.check_interval_seconds || 300} сек`;
          document.getElementById('overviewChatId').innerText = app.chat_invite_url || '—';

          // Cloud Storage fields
          const provider = cloud.provider || 'local';
          document.getElementById('storage_provider').value = provider;
          onStorageProviderChange(provider);
          document.getElementById('storage_tg_chat').value = cloud.telegram_storage_chat_id || tg.admin_id || '';
          document.getElementById('storage_upstash_url').value = cloud.upstash_rest_url || '';
          document.getElementById('storage_upstash_token').value = cloud.upstash_rest_token || '';
          document.getElementById('storage_supabase_url').value = cloud.supabase_url || '';
          document.getElementById('storage_supabase_key').value = cloud.supabase_key || '';

          document.getElementById('kpiStorageMode').innerText = provider.toUpperCase();
          document.getElementById('kpiLastSync').innerText = cloud.last_sync ? `Синхр: ${cloud.last_sync}` : 'Бэкап не выполнялся';
        }

        if (data.last_check) {
          document.getElementById('overviewLastCheck').innerText = data.last_check;
        }

        if (data.uptime_minutes !== undefined) {
          document.getElementById('overviewUptime').innerText = `${data.uptime_minutes} мин`;
        }

        if (data.daemon_running !== undefined) {
          const statusText = data.daemon_paused ? 'Приостановлен' : 'Активен';
          document.getElementById('kpiDaemonStatus').innerText = statusText;
          document.getElementById('kpiDaemonStatus').style.color = data.daemon_paused ? 'var(--warning)' : 'var(--success)';
        }

        if (data.logs) {
          rawLogs = data.logs;
          renderLogs();
        }
      } catch (e) {
        console.error("Ошибка загрузки данных:", e);
      }
    }

    function renderLogs() {
      const box = document.getElementById('terminalBox');
      const query = (document.getElementById('logSearchInput').value || '').toLowerCase();
      
      const filtered = rawLogs.filter(l => {
        if (currentLogFilter !== 'all' && l.level !== currentLogFilter) return false;
        if (query && !l.message.toLowerCase().includes(query)) return false;
        return true;
      });

      box.innerHTML = filtered.map(l => `
        <div class="log-line">
          <span class="log-ts">[${l.time}]</span>
          <span class="log-lvl ${l.level}">${l.level.toUpperCase()}</span>
          <span class="log-msg">${escapeHtml(l.message)}</span>
        </div>
      `).join('');

      document.getElementById('logCountText').innerText = `Всего записей: ${filtered.length}`;

      if (document.getElementById('autoScrollCheck').checked) {
        box.scrollTop = box.scrollHeight;
      }
    }

    function escapeHtml(text) {
      return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
    }

    function setLogFilter(filter, el) {
      currentLogFilter = filter;
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      if (el) el.classList.add('active');
      renderLogs();
    }

    function filterLogs() {
      renderLogs();
    }

    function clearConsoleView() {
      rawLogs = [];
      renderLogs();
      showToast("Консоль очищена", "info");
    }

    function copyAllLogs() {
      const text = rawLogs.map(l => `[${l.time}] [${l.level.toUpperCase()}] ${l.message}`).join('\\n');
      navigator.clipboard.writeText(text);
      showToast("Все логи скопированы в буфер обмена", "success");
    }

    function copyCode(btn) {
      const code = btn.parentElement.querySelector('span').innerText;
      navigator.clipboard.writeText(code);
      showToast("Команда скопирована", "success");
    }

    async function runAction(actionName) {
      showToast(`Запуск действия [${actionName}]...`, "info");
      try {
        const res = await fetch('/api/action', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ action: actionName })
        });
        const data = await res.json();
        if (data.ok) {
          showToast(`Действие [${actionName}] успешно инициировано`, "success");
        } else {
          showToast(`Ошибка: ${data.error}`, "error");
        }
        setTimeout(fetchLogsOnly, 1200);
      } catch (e) {
        showToast("Ошибка связи с сервером", "error");
      }
    }

    async function sendTestMessage() {
      showToast("Отправка проверочного сообщения в Telegram...", "info");
      try {
        const res = await fetch('/api/test-message', { method: 'POST' });
        const data = await res.json();
        if (data.ok) {
          showToast("Сообщение успешно доставлено в канал!", "success");
        } else {
          showToast(`Ошибка отправки: ${data.error}`, "error");
        }
        setTimeout(fetchLogsOnly, 800);
      } catch (e) {
        showToast("Сетевая ошибка при отправке", "error");
      }
    }

    async function sendCustomMessage() {
      const text = document.getElementById('customMsgText').value.trim();
      if (!text) {
        showToast("Пожалуйста, введите текст сообщения", "error");
        return;
      }
      const disablePreview = document.getElementById('customMsgDisablePreview').checked;
      showToast("Публикация сообщения в канал...", "info");

      try {
        const res = await fetch('/api/test-message', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ text: text, disable_preview: disablePreview })
        });
        const data = await res.json();
        if (data.ok) {
          showToast("Сообщение успешно опубликовано в канале!", "success");
          document.getElementById('customMsgText').value = '';
        } else {
          showToast(`Ошибка: ${data.error}`, "error");
        }
        setTimeout(fetchLogsOnly, 800);
      } catch (e) {
        showToast("Ошибка при публикации", "error");
      }
    }

    async function autoDetectChannel() {
      showToast("Поиск ID канала в обновлениях бота...", "info");
      try {
        const res = await fetch('/api/auto-detect-channel', { method: 'POST' });
        const data = await res.json();
        if (data.ok) {
          showToast(`Канал найден: ${data.title} (${data.chat_id})`, "success");
          document.getElementById('cfg_channel').value = data.chat_id;
          saveSettings();
        } else {
          showToast(data.error, "error", 5000);
        }
      } catch (e) {
        showToast("Ошибка при авто-детектировании", "error");
      }
    }

    async function saveSettings() {
      const payload = {
        bot_token: document.getElementById('cfg_token').value.trim(),
        channel_id: document.getElementById('cfg_channel').value.trim(),
        chat_invite_url: document.getElementById('cfg_chat').value.trim(),
        admin_id: document.getElementById('cfg_admin').value.trim(),
        interval: parseInt(document.getElementById('cfg_interval').value) || 300,
        enable_releases: document.getElementById('cfg_releases_enabled').checked,
        enable_news: document.getElementById('cfg_news_enabled').checked,
        cloud_storage: {
          provider: document.getElementById('storage_provider').value,
          telegram_storage_chat_id: document.getElementById('storage_tg_chat').value.trim(),
          upstash_rest_url: document.getElementById('storage_upstash_url').value.trim(),
          upstash_rest_token: document.getElementById('storage_upstash_token').value.trim(),
          supabase_url: document.getElementById('storage_supabase_url').value.trim(),
          supabase_key: document.getElementById('storage_supabase_key').value.trim()
        }
      };

      try {
        const res = await fetch('/api/save-config', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.ok) {
          showToast("Конфигурация успешно сохранена!", "success");
          loadData();
        } else {
          showToast(`Ошибка сохранения: ${data.error}`, "error");
        }
      } catch (e) {
        showToast("Сетевая ошибка сохранения", "error");
      }
    }

    async function syncCloudNow() {
      showToast("Синхронизация конфигурации с облаком...", "info");
      try {
        const res = await fetch('/api/cloud-sync', { method: 'POST' });
        const data = await res.json();
        if (data.ok) {
          showToast("Конфиг успешно забэкаплен в облако!", "success");
          loadData();
        } else {
          showToast(`Ошибка бэкапа: ${data.error}`, "error", 5000);
        }
      } catch (e) {
        showToast("Ошибка синхронизации", "error");
      }
    }

    async function fetchCloudNow() {
      if (!confirm("Восстановить настройки из облака? Текущие несохраненные параметры будут перезаписаны.")) return;
      showToast("Запрос конфигурации из облака...", "info");
      try {
        const res = await fetch('/api/cloud-fetch', { method: 'POST' });
        const data = await res.json();
        if (data.ok) {
          showToast("Конфигурация успешно восстановлена из облака!", "success");
          loadData();
        } else {
          showToast(`Ошибка загрузки: ${data.error}`, "error", 5000);
        }
      } catch (e) {
        showToast("Ошибка загрузки из облака", "error");
      }
    }

    async function testSupabaseConnection() {
      showToast("Проверка связи с вашей базой Supabase...", "info");
      try {
        const res = await fetch('/api/test-supabase', { method: 'POST' });
        const data = await res.json();
        if (data.ok) {
          showToast("✅ База Supabase успешно отвечает! (HTTP 200)", "success", 4000);
        } else {
          showToast(`❌ Ошибка Supabase: ${data.error}`, "error", 5000);
        }
      } catch (e) {
        showToast("Ошибка запроса к Supabase", "error");
      }
    }

    function copySupabaseSql() {
      const sql = `-- ==============================================================================
-- AnimeVist Telegram Bot — Таблицы для Supabase (Синхронизация и Автономность 24/7)
-- ==============================================================================

CREATE TABLE IF NOT EXISTS public.bot_config (
    id TEXT PRIMARY KEY,
    config JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.bot_config ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow anon read and write on bot_config" ON public.bot_config;
CREATE POLICY "Allow anon read and write on bot_config" 
ON public.bot_config 
FOR ALL 
TO anon, authenticated 
USING (true) 
WITH CHECK (true);

CREATE TABLE IF NOT EXISTS public.bot_seen_items (
    item_id TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    title TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.bot_seen_items ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow anon read and write on bot_seen_items" ON public.bot_seen_items;
CREATE POLICY "Allow anon read and write on bot_seen_items" 
ON public.bot_seen_items 
FOR ALL 
TO anon, authenticated 
USING (true) 
WITH CHECK (true);

CREATE INDEX IF NOT EXISTS idx_bot_seen_category ON public.bot_seen_items(category);`;

      navigator.clipboard.writeText(sql);
      showToast("SQL-скрипт скопирован в буфер! Вставьте в Supabase SQL Editor и нажмите Run.", "success", 4500);
    }

    async function toggleDaemon() {
      try {
        const res = await fetch('/api/toggle-daemon', { method: 'POST' });
        const data = await res.json();
        showToast(data.paused ? "Фоновый демон приостановлен" : "Фоновый демон возобновлен", "info");
        loadData();
      } catch (e) {
        showToast("Ошибка изменения состояния демона", "error");
      }
    }

    async function fetchLogsOnly() {
      try {
        const res = await fetch('/api/logs');
        const logs = await res.json();
        rawLogs = logs;
        renderLogs();
      } catch (e) {}
    }

    // Initialize
    loadData();
    setInterval(fetchLogsOnly, 4000);
  </script>
</body>
</html>
"""

class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
        elif path == "/api/status":
            sender = TelegramSender()
            me = sender.get_me()
            config = load_config()
            uptime_min = int((time.time() - server_start_time) / 60)
            resp = {
                "bot": me.get('result') if me.get('ok') else None,
                "config": config,
                "last_check": last_check_time,
                "daemon_running": daemon_running,
                "daemon_paused": daemon_paused,
                "uptime_minutes": uptime_min,
                "logs": activity_logs
            }
            self._send_json(resp)
        elif path == "/api/logs":
            self._send_json(activity_logs)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else '{}'
        try:
            data = json.loads(body) if body else {}
        except Exception:
            data = {}

        if path == "/api/save-config":
            config = load_config()
            tg = config.setdefault('telegram', {})
            app = config.setdefault('app', {})
            ann = config.setdefault('announcer', {})
            cloud = config.setdefault('cloud_storage', {})

            if 'bot_token' in data: tg['bot_token'] = data['bot_token']
            if 'channel_id' in data: tg['channel_id'] = data['channel_id']
            if 'chat_invite_url' in data: app['chat_invite_url'] = data['chat_invite_url']
            if 'admin_id' in data: tg['admin_id'] = data['admin_id']
            if 'interval' in data: ann['check_interval_seconds'] = int(data['interval'])
            if 'enable_releases' in data: ann['enable_series_releases'] = bool(data['enable_releases'])
            if 'enable_news' in data: ann['enable_anime_news'] = bool(data['enable_news'])

            if 'cloud_storage' in data and isinstance(data['cloud_storage'], dict):
                cloud.update(data['cloud_storage'])

            save_config(config, sync_to_cloud=False)
            log_event("Конфигурация успешно обновлена через веб-интерфейс", "success")
            self._send_json({"ok": True})

        elif path == "/api/test-message":
            config = load_config()
            sender = TelegramSender()
            channel = config.get('telegram', {}).get('channel_id')
            custom_text = data.get('text')
            disable_preview = data.get('disable_preview', False)

            if custom_text:
                msg_text = custom_text
            else:
                msg_text = (
                    "🤖 <b>AnimeVist — Тест подключения!</b>\n\n"
                    "Панель управления и бот успешно настроены и подключены к каналу."
                )

            res = sender.send_message(msg_text, chat_id=channel, disable_preview=disable_preview)
            if res.get('ok'):
                log_event("Сообщение успешно доставлено в целевой канал", "success")
                self._send_json({"ok": True})
            else:
                desc = res.get('description', 'Неизвестная ошибка Telegram API')
                log_event(f"Ошибка отправки сообщения: {desc}", "error")
                self._send_json({"ok": False, "error": desc})

        elif path == "/api/auto-detect-channel":
            res = get_channel_auto_detect()
            if res.get('ok'):
                config = load_config()
                config.setdefault('telegram', {})['channel_id'] = str(res['chat_id'])
                save_config(config)
                log_event(f"Канал обнаружен автоматически: {res.get('title')} ({res.get('chat_id')})", "success")
            self._send_json(res)

        elif path == "/api/cloud-sync":
            config = load_config()
            res = sync_config_to_cloud(config)
            if res.get('ok'):
                log_event("Резервная копия настроек успешно загружена в облако", "success")
            else:
                log_event(f"Ошибка облачной синхронизации: {res.get('error')}", "error")
            self._send_json(res)

        elif path == "/api/cloud-fetch":
            config = load_config()
            provider = config.get('cloud_storage', {}).get('provider', 'telegram')
            if provider == 'telegram':
                res = fetch_config_from_telegram(config)
            elif provider == 'upstash':
                res = fetch_config_from_upstash(config)
            elif provider == 'supabase':
                res = fetch_config_from_supabase(config)
            else:
                res = {"ok": False, "error": f"Провайдер {provider} не поддерживает авто-восстановление по REST"}
            
            if res.get('ok'):
                log_event("Настройки успешно восстановлены из облака", "success")
            else:
                log_event(f"Ошибка восстановления: {res.get('error')}", "error")
            self._send_json(res)

        elif path == "/api/test-supabase":
            config = load_config()
            res = test_supabase_connection(config)
            self._send_json(res)

        elif path == "/api/toggle-daemon":
            global daemon_paused
            daemon_paused = not daemon_paused
            state_str = "приостановлен" if daemon_paused else "возобновлен"
            log_event(f"Фоновый демон автопостинга {state_str} оператором", "info")
            self._send_json({"ok": True, "paused": daemon_paused})

        elif path == "/api/action":
            act = data.get('action')
            def run_bg(action_name):
                try:
                    if action_name == 'releases':
                        log_event("Ручной запуск сканирования новых серий...")
                        cnt = run_series_check()
                        log_event(f"Сканирование серий завершено. Опубликовано: {cnt}", "success")
                    elif action_name == 'news':
                        log_event("Ручной запуск проверки аниме-новостей...")
                        cnt = run_news_check()
                        log_event(f"Проверка новостей завершена. Опубликовано: {cnt}", "success")
                    elif action_name == 'patchnote':
                        log_event("Публикация свежего патчноута из GitHub Releases...")
                        res = publish_patchnote_from_github()
                        log_event("Публикация патчноута завершена", "success" if res else "error")
                    elif action_name == 'pinned':
                        log_event("Отправка и закрепление навигационного поста...")
                        res = publish_pinned_navigator()
                        log_event("Закрепление навигатора завершено", "success" if res else "error")
                except Exception as e:
                    log_event(f"Ошибка выполнения действия [{action_name}]: {e}", "error")

            threading.Thread(target=run_bg, args=(act,), daemon=True).start()
            self._send_json({"ok": True})
        else:
            self.send_response(404)
            self.end_headers()

    def _send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def log_message(self, format, *args):
        # Silence default HTTP access log spam
        pass

def start_server(port=None):
    if port is None:
        # Default to 7860 for Hugging Face Spaces compatibility, fallback to 5000
        env_port = os.environ.get("PORT")
        if env_port:
            preferred_port = int(env_port)
            ports_to_try = [preferred_port, 7860, 5000, 5001, 8080]
        else:
            ports_to_try = [5000, 7860, 5001, 8080]
    else:
        ports_to_try = [port]

    server = None
    actual_port = None
    for p in ports_to_try:
        try:
            server = HTTPServer(("0.0.0.0", p), DashboardHandler)
            actual_port = p
            break
        except OSError:
            continue

    if server is None:
        server = HTTPServer(("0.0.0.0", 0), DashboardHandler)
        actual_port = server.server_port

    print(f"\n================================================================")
    print(f"  🎬 ANIME VIST — КОНСОЛЬ УПРАВЛЕНИЯ БОТОМ ЗАПУЩЕНА (24/7)")
    print(f"  🌐 Локальный веб-интерфейс: http://localhost:{actual_port}")
    print(f"  ☁️ Серверный хост-адрес:    http://0.0.0.0:{actual_port}")
    print(f"================================================================\n")
    log_event(f"Веб-сервер активен на порту {actual_port}", "info")

    import webbrowser
    def open_browser():
        time.sleep(0.8)
        try:
            webbrowser.open(f"http://localhost:{actual_port}")
        except Exception:
            pass
    threading.Thread(target=open_browser, daemon=True).start()

    # Start 24/7 background worker thread
    global daemon_thread
    daemon_thread = threading.Thread(target=background_monitoring_worker, daemon=True)
    daemon_thread.start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nОстановка сервера...")
        server.server_close()

if __name__ == '__main__':
    start_server()
