"""
AnimeVist Professional Web Dashboard & 24/7 Automation Hub.
DevOps Control Center for managing the AnimeVist Telegram Bot,
channel broadcasting, configuration sync, and background autonomous monitoring.
Includes manual posting studio (compilations, episodes, news, custom posts).
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
    sync_config_to_supabase,
    fetch_config_from_supabase,
    test_supabase_connection
)
from series_announcer import run_series_check
from news_announcer import run_news_check
from compilations_announcer import run_compilation_post, list_available_themes, THEMES
from patchnote_publisher import publish_patchnote_from_github
from pinned_navigator import publish_pinned_navigator

# Global runtime state
activity_logs = []
daemon_thread = None
daemon_running = True
daemon_paused = False
last_check_time = None
last_compilation_time = 0
server_start_time = time.time()

def log_event(message, level="info"):
    timestamp = time.strftime('%H:%M:%S')
    entry = {"time": timestamp, "message": str(message), "level": level}
    activity_logs.append(entry)
    if len(activity_logs) > 200:
        activity_logs.pop(0)
    print(f"[{timestamp}] [{level.upper()}] {message}")

def background_monitoring_worker():
    global last_check_time, last_compilation_time, daemon_running, daemon_paused
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
                    log_event("Авто-цикл: проверка новостей (Shikimori, MAL, ANN)...")
                    cnt_n = run_news_check()
                    if cnt_n > 0:
                        log_event(f"Опубликовано аниме-новостей: {cnt_n}", "success")

                # 3. Check Compilations
                if ann_conf.get('enable_compilations', True):
                    comp_hours = float(ann_conf.get('compilations_interval_hours', 6))
                    if time.time() - last_compilation_time >= comp_hours * 3600:
                        log_event("Авто-цикл: публикация плановой Топ-подборки аниме...")
                        res_c = run_compilation_post()
                        if res_c.get('ok'):
                            log_event(f"Опубликована подборка: {res_c.get('theme')}", "success")
                        last_compilation_time = time.time()

                last_check_time = time.strftime('%d.%m.%Y %H:%M:%S')
        except Exception as e:
            log_event(f"Исключение в цикле мониторинга: {e}", "error")

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
                "error": "В обновлениях бота пока нет сообщений из канала. Опубликуйте любое сообщение в канал и повторите поиск."
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
    .status-dot.warn { background: var(--warning); box-shadow: 0 0 8px var(--warning); }
    .status-dot.error { background: var(--danger); box-shadow: 0 0 8px var(--danger); }

    .header-right {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    /* Buttons */
    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 7px;
      font-family: inherit;
      font-size: 0.85rem;
      font-weight: 500;
      padding: 8px 14px;
      border-radius: var(--radius-sm);
      border: 1px solid transparent;
      cursor: pointer;
      transition: all 0.15s ease;
      text-decoration: none;
      white-space: nowrap;
    }
    .btn:active { transform: translateY(1px); }
    .btn-primary { background: var(--accent-blue); color: #fff; }
    .btn-primary:hover { background: var(--accent-blue-hover); box-shadow: 0 2px 10px rgba(59, 130, 246, 0.35); }
    .btn-secondary { background: var(--bg-surface-elevated); color: var(--text-primary); border-color: var(--border-default); }
    .btn-secondary:hover { background: #273549; border-color: #475569; }
    .btn-outline { background: transparent; color: var(--text-secondary); border-color: var(--border-default); }
    .btn-outline:hover { color: #fff; border-color: var(--text-secondary); background: rgba(255, 255, 255, 0.03); }
    .btn-danger { background: var(--danger-bg); color: #fca5a5; border-color: rgba(239, 68, 68, 0.3); }
    .btn-danger:hover { background: rgba(239, 68, 68, 0.25); color: #fff; }
    .btn-sm { padding: 5px 10px; font-size: 0.78rem; border-radius: 4px; }
    .btn-block { width: 100%; }

    /* Navigation Tabs */
    .nav-tabs {
      display: flex;
      gap: 4px;
      background: var(--bg-surface);
      border-bottom: 1px solid var(--border-subtle);
      padding: 0 1.75rem;
    }
    .tab-btn {
      background: transparent;
      border: none;
      color: var(--text-secondary);
      font-family: inherit;
      font-size: 0.88rem;
      font-weight: 500;
      padding: 12px 16px;
      cursor: pointer;
      border-bottom: 2px solid transparent;
      transition: all 0.15s ease;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .tab-btn:hover { color: var(--text-primary); }
    .tab-btn.active { color: #fff; border-bottom-color: var(--accent-blue); font-weight: 600; }

    /* Main Container */
    .app-body {
      flex: 1;
      padding: 1.5rem 1.75rem;
      max-width: 1440px;
      width: 100%;
      margin: 0 auto;
    }
    .tab-content { display: none; }
    .tab-content.active { display: block; animation: fadeIn 0.15s ease; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(3px); } to { opacity: 1; transform: translateY(0); } }

    /* KPI Cards Grid */
    .grid-kpi {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 1rem;
      margin-bottom: 1.5rem;
    }
    .kpi-card {
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      padding: 1.15rem;
      box-shadow: var(--shadow-card);
    }
    .kpi-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      color: var(--text-muted);
      font-size: 0.76rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 6px;
    }
    .kpi-value {
      font-size: 1.45rem;
      font-weight: 700;
      color: #fff;
      font-family: var(--font-mono);
      margin-bottom: 4px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .kpi-desc {
      font-size: 0.78rem;
      color: var(--text-secondary);
    }

    /* Layout Grids */
    .grid-2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(460px, 1fr)); gap: 1.25rem; margin-bottom: 1.5rem; }
    .card {
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      padding: 1.25rem;
      box-shadow: var(--shadow-card);
    }
    .card-title {
      font-size: 1rem;
      font-weight: 600;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 4px;
    }
    .card-subtitle {
      font-size: 0.8rem;
      color: var(--text-secondary);
      margin-bottom: 1rem;
    }

    /* Action Tiles */
    .action-tiles-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 0.85rem;
    }
    .action-tile {
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-sm);
      padding: 1rem;
      cursor: pointer;
      transition: all 0.15s ease;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }
    .action-tile:hover {
      border-color: var(--border-focus);
      background: var(--bg-card-hover);
      transform: translateY(-2px);
    }
    .tile-top { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 8px; }
    .tile-icon { font-size: 1.5rem; }
    .tile-title { font-size: 0.92rem; font-weight: 600; color: #fff; }
    .tile-tag { font-size: 0.7rem; font-family: var(--font-mono); color: var(--accent-cyan); }
    .tile-desc { font-size: 0.78rem; color: var(--text-secondary); line-height: 1.4; margin-bottom: 10px; }
    .tile-footer { display: flex; align-items: center; justify-content: space-between; font-size: 0.75rem; color: var(--text-muted); border-top: 1px solid var(--border-subtle); padding-top: 8px; }

    /* Form Controls */
    .form-group { margin-bottom: 1.15rem; }
    .form-label { display: flex; align-items: center; justify-content: space-between; font-size: 0.82rem; font-weight: 500; color: var(--text-secondary); margin-bottom: 6px; }
    .input-wrapper { position: relative; display: flex; align-items: center; }
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
    .input-toggle-btn { position: absolute; right: 8px; background: transparent; border: none; color: var(--text-muted); cursor: pointer; padding: 4px; font-size: 0.85rem; }
    .input-toggle-btn:hover { color: #fff; }

    /* Switch */
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
    .switch-title { font-size: 0.85rem; font-weight: 500; color: #fff; }
    .switch-sub { font-size: 0.74rem; color: var(--text-muted); }
    .switch { position: relative; display: inline-block; width: 42px; height: 22px; flex-shrink: 0; }
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

    /* Live Preview Box */
    .preview-card {
      background: #0a0f1d;
      border: 1px solid #1e293b;
      border-radius: var(--radius-sm);
      padding: 14px;
      margin-top: 10px;
    }
    .preview-img { width: 100%; max-height: 220px; object-fit: cover; border-radius: 4px; margin-bottom: 10px; display: none; }
    .preview-text { font-size: 0.85rem; color: #f1f5f9; line-height: 1.5; white-space: pre-wrap; word-break: break-word; }
    .preview-btn { margin-top: 10px; display: none; background: #2563eb; color: #fff; padding: 7px 12px; border-radius: 4px; text-align: center; font-size: 0.82rem; font-weight: 600; text-decoration: none; }

    /* Console Terminal */
    .terminal-container {
      background: #05080f;
      border: 1px solid #1e293b;
      border-radius: var(--radius-sm);
      padding: 12px;
      font-family: var(--font-mono);
      font-size: 0.8rem;
      height: 380px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .log-line { display: flex; gap: 8px; line-height: 1.4; }
    .log-ts { color: #64748b; flex-shrink: 0; }
    .log-lvl { font-weight: 600; padding: 0 4px; border-radius: 2px; flex-shrink: 0; }
    .log-lvl.info { color: #38bdf8; }
    .log-lvl.success { color: #34d399; }
    .log-lvl.error { color: #f87171; }
    .log-msg { color: #cbd5e1; word-break: break-word; }

    /* Toast */
    #toastContainer {
      position: fixed; bottom: 24px; right: 24px; z-index: 9999;
      display: flex; flex-direction: column; gap: 8px;
      max-width: 380px; width: calc(100% - 48px);
    }
    .toast {
      background: var(--bg-surface-elevated); border: 1px solid var(--border-default);
      color: #fff; padding: 12px 16px; border-radius: var(--radius-md);
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
      display: flex; align-items: center; justify-content: space-between; gap: 12px;
      animation: slideIn 0.2s ease forwards; font-size: 0.85rem;
    }
    .toast.success { border-color: rgba(16, 185, 129, 0.4); }
    .toast.error { border-color: rgba(239, 68, 68, 0.4); }
    .toast.info { border-color: rgba(59, 130, 246, 0.4); }
    @keyframes slideIn { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
  </style>
</head>
<body>

  <!-- Header -->
  <header>
    <div class="header-left">
      <div class="logo-badge">AV</div>
      <div>
        <div class="brand-title">
          AnimeVist <span>Bot Console</span>
          <span class="version-tag">24/7 v2.3</span>
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
      <button class="btn btn-secondary btn-sm" onclick="sendTestMessage()">
        💬 Тест канала
      </button>
      <button class="btn btn-primary btn-sm" onclick="runAction('releases')">
        📺 Сканировать серии
      </button>
      <button class="btn btn-outline btn-sm" onclick="loadData()" title="Обновить">
        🔄
      </button>
    </div>
  </header>

  <!-- Navigation Tabs -->
  <nav class="nav-tabs">
    <button class="tab-btn active" onclick="switchTab('tab-overview', this)">📊 Мониторинг & KPI</button>
    <button class="tab-btn" onclick="switchTab('tab-actions', this)">⚡ Ручная публикация</button>
    <button class="tab-btn" onclick="switchTab('tab-config', this)">⚙️ Конфигурация</button>
    <button class="tab-btn" onclick="switchTab('tab-storage', this)">💾 Облачное хранилище</button>
    <button class="tab-btn" onclick="switchTab('tab-console', this)">📟 Консоль логов</button>
  </nav>

  <!-- Main Content -->
  <main class="app-body">
    <!-- TAB 1: OVERVIEW -->
    <section id="tab-overview" class="tab-content active">
      <div class="grid-kpi">
        <div class="kpi-card">
          <div class="kpi-header"><span>TELEGRAM BOT</span><span>🤖</span></div>
          <div class="kpi-value" id="kpiBotUser">Загрузка...</div>
          <div class="kpi-desc" id="kpiBotId">ID: —</div>
        </div>

        <div class="kpi-card">
          <div class="kpi-header"><span>ЦЕЛЕВОЙ КАНАЛ</span><span>📢</span></div>
          <div class="kpi-value" id="kpiChannel">—</div>
          <div class="kpi-desc">Официальный вещатель</div>
        </div>

        <div class="kpi-card">
          <div class="kpi-header"><span>ДЕМОН 24/7</span><span>⏱️</span></div>
          <div class="kpi-value" style="color:var(--success);" id="kpiDaemonStatus">Активен</div>
          <div class="kpi-desc" id="kpiInterval">Интервал: 300 сек</div>
        </div>

        <div class="kpi-card">
          <div class="kpi-header"><span>ОБЛАЧНАЯ БАЗА</span><span>🐘</span></div>
          <div class="kpi-value" style="color:var(--success);" id="kpiStorageMode">Supabase Live</div>
          <div class="kpi-desc" id="kpiLastSync">Синхронизация: —</div>
        </div>
      </div>

      <div class="grid-2">
        <div class="card">
          <div class="card-title">⚡ Быстрый Запуск Модулей Вещания</div>
          <div class="card-subtitle">Мгновенная публикация контента в Telegram одним кликом:</div>

          <div class="action-tiles-grid">
            <div class="action-tile" onclick="runAction('releases')">
              <div class="tile-top">
                <div class="tile-icon">📺</div>
                <div>
                  <div class="tile-title">Новые серии</div>
                  <div class="tile-tag">#онгоинг</div>
                </div>
              </div>
              <div class="tile-desc">Точный номер серии, постеры без 404, хештеги жанров.</div>
              <div class="tile-footer"><span>Ручной запуск</span><span class="btn btn-outline btn-sm">Старт ➔</span></div>
            </div>

            <div class="action-tile" onclick="runAction('news')">
              <div class="tile-top">
                <div class="tile-icon">📰</div>
                <div>
                  <div class="tile-title">Аниме-новости</div>
                  <div class="tile-tag">#новости</div>
                </div>
              </div>
              <div class="tile-desc">Мульти-сбор: Shikimori, MyAnimeList, ANN + перевод.</div>
              <div class="tile-footer"><span>Ручной запуск</span><span class="btn btn-outline btn-sm">Старт ➔</span></div>
            </div>

            <div class="action-tile" onclick="switchTab('tab-actions', document.querySelectorAll('.tab-btn')[1])">
              <div class="tile-top">
                <div class="tile-icon">🌟</div>
                <div>
                  <div class="tile-title">Топ-подборки</div>
                  <div class="tile-tag">#подборка</div>
                </div>
              </div>
              <div class="tile-desc">Топ 3-5 аниме: Киберпанк, Фэнтези, Триллеры, Романтика.</div>
              <div class="tile-footer"><span>Выбрать тему</span><span class="btn btn-outline btn-sm">Открыть ➔</span></div>
            </div>

            <div class="action-tile" onclick="runAction('patchnote')">
              <div class="tile-top">
                <div class="tile-icon">🚀</div>
                <div>
                  <div class="tile-title">Патчноут релиза</div>
                  <div class="tile-tag">#patchnote</div>
                </div>
              </div>
              <div class="tile-desc">Публикация свежего релиза приложения из GitHub.</div>
              <div class="tile-footer"><span>Ручной запуск</span><span class="btn btn-outline btn-sm">Старт ➔</span></div>
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
              <span style="color:var(--text-secondary);">Подборки (интервал):</span>
              <span style="font-family:var(--font-mono); color:var(--accent-cyan);" id="overviewCompInterval">Каждые 6 часов</span>
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
              ⏸️ Пауза / Пуск демона
            </button>
          </div>
        </div>
      </div>
    </section>

    <!-- TAB 2: MANUAL ACTIONS & POST STUDIO -->
    <section id="tab-actions" class="tab-content">
      <div class="grid-2">
        <!-- Compilations & Instant Triggers -->
        <div class="card">
          <div class="card-title">🌟 Публикация Топ-Подборки Аниме (#подборка)</div>
          <div class="card-subtitle">Выберите жанр/тему для формирования иллюстрированного поста с высоким рейтингом:</div>

          <div class="form-group">
            <label class="form-label">Тема подборки:</label>
            <select id="compilationGenreSelect">
              <option value="auto">🔄 Автоматический выбор (следующая по очереди)</option>
              <option value="cyberpunk">🌆 Киберпанк & Фантастика</option>
              <option value="psychological">🧠 Психологические триллеры & Детективы</option>
              <option value="fantasy">⚔️ Эпическое фэнтези 8.5+</option>
              <option value="romance">💖 Романтика & Повседневность</option>
              <option value="dark_fantasy">🗡 Тёмное фэнтези & Экшен</option>
              <option value="isekai">🌀 Захватывающие исекаи & Попаданцы</option>
              <option value="classics">🏆 Золотая классика аниме</option>
              <option value="comedy">😂 Безумные комедии для настроения</option>
            </select>
          </div>

          <button class="btn btn-primary btn-block" onclick="publishCompilation()" style="margin-bottom:20px;">
            🌟 Опубликовать выбранную подборку сейчас
          </button>

          <div style="border-top:1px solid var(--border-subtle); padding-top:16px;">
            <div class="card-title" style="font-size:0.92rem;">⚡ Мгновенные публикации серий и новостей:</div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:10px;">
              <button class="btn btn-secondary" onclick="runAction('releases')">
                📺 Новые серии
              </button>
              <button class="btn btn-secondary" onclick="runAction('news')">
                📰 Собрать новости
              </button>
            </div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:10px;">
              <button class="btn btn-outline" onclick="runAction('patchnote')">
                🚀 Патчноут GitHub
              </button>
              <button class="btn btn-outline" onclick="runAction('pinned')">
                📌 Закрепить навигатор
              </button>
            </div>
          </div>
        </div>

        <!-- Custom Post Studio -->
        <div class="card">
          <div class="card-title">✍️ Студия Кастомного Поста в Канал</div>
          <div class="card-subtitle">Создайте произвольный пост с текстом (HTML), фото и инлайн-кнопкой:</div>

          <div class="form-group">
            <label class="form-label">Текст публикации (поддерживает &lt;b&gt;, &lt;i&gt;, &lt;a&gt;, &lt;code&gt;):</label>
            <textarea id="customText" rows="5" placeholder="Привет! 🎬 Мы добавили новую подборку тайтлов..." oninput="updateCustomPreview()"></textarea>
          </div>

          <div class="form-group">
            <label class="form-label">URL изображения / постера (опционально):</label>
            <input type="text" id="customPhoto" placeholder="https://example.com/poster.jpg" oninput="updateCustomPreview()">
          </div>

          <div class="grid-2" style="margin-bottom:0; gap:10px;">
            <div class="form-group">
              <label class="form-label">Текст кнопки (опционально):</label>
              <input type="text" id="customBtnText" placeholder="Смотреть онлайн" oninput="updateCustomPreview()">
            </div>
            <div class="form-group">
              <label class="form-label">Ссылка кнопки (URL):</label>
              <input type="text" id="customBtnUrl" placeholder="https://t.me/..." oninput="updateCustomPreview()">
            </div>
          </div>

          <!-- Preview -->
          <div class="form-label" style="margin-top:10px;">Предварительный просмотр:</div>
          <div class="preview-card">
            <img id="previewImg" class="preview-img" alt="Постер">
            <div id="previewText" class="preview-text">Текст вашего сообщения появится здесь...</div>
            <a id="previewBtn" class="preview-btn" target="_blank">Кнопка</a>
          </div>

          <div style="margin-top:15px;">
            <button class="btn btn-primary btn-block" onclick="sendCustomPost()">
              🚀 Отправить пост в канал
            </button>
          </div>
        </div>
      </div>
    </section>

    <!-- TAB 3: CONFIGURATION -->
    <section id="tab-config" class="tab-content">
      <div class="card" style="max-width: 820px; margin: 0 auto;">
        <div class="card-title">⚙️ Настройки Telegram & Параметров Автоматизации</div>
        <div class="card-subtitle">Все изменения сохраняются в конфигурацию и базу Supabase.</div>

        <h3 style="font-size:0.9rem; color:var(--accent-blue); margin-bottom:12px; text-transform:uppercase; letter-spacing:0.5px;">1. Ключи и авторизация Telegram</h3>
        
        <div class="form-group">
          <div class="form-label">
            <span>Токен Telegram-бота:</span>
            <span style="font-size:0.75rem; color:var(--text-muted);">От @BotFather</span>
          </div>
          <div class="input-wrapper">
            <input type="password" id="cfg_token" placeholder="8958974614:AAF-...">
            <button type="button" class="input-toggle-btn" onclick="togglePasswordVisibility('cfg_token', this)">👁️</button>
          </div>
        </div>

        <div class="grid-2">
          <div class="form-group">
            <div class="form-label">
              <span>ID канала:</span>
              <a href="javascript:void(0)" onclick="autoDetectChannel()" style="color:var(--accent-cyan); text-decoration:none; font-size:0.75rem;">🔍 Найти ID</a>
            </div>
            <input type="text" id="cfg_channel" placeholder="-1004465332635">
          </div>

          <div class="form-group">
            <div class="form-label">
              <span>Ссылка чата обсуждений:</span>
            </div>
            <input type="text" id="cfg_chat" placeholder="https://t.me/animevist_chat">
          </div>
        </div>

        <div class="form-group">
          <div class="form-label">
            <span>ID Telegram Администратора:</span>
          </div>
          <input type="text" id="cfg_admin" placeholder="869155357">
        </div>

        <h3 style="font-size:0.9rem; color:var(--accent-blue); margin-top:24px; margin-bottom:12px; text-transform:uppercase; letter-spacing:0.5px;">2. Режимы и модули вещания</h3>

        <div class="switch-row">
          <div>
            <div class="switch-title">Автопостинг новых серий (#онгоинг)</div>
            <div class="switch-sub">Опрос AnimeVost & Shikimori с точным распознаванием номера серии</div>
          </div>
          <label class="switch">
            <input type="checkbox" id="cfg_releases_enabled" checked>
            <span class="slider"></span>
          </label>
        </div>

        <div class="switch-row">
          <div>
            <div class="switch-title">Автопостинг аниме-новостей (#новости)</div>
            <div class="switch-sub">Сбор из Shikimori, MyAnimeList и ANN с авто-переводом и категоризацией</div>
          </div>
          <label class="switch">
            <input type="checkbox" id="cfg_news_enabled" checked>
            <span class="slider"></span>
          </label>
        </div>

        <div class="switch-row">
          <div>
            <div class="switch-title">Автопостинг топ-подборок аниме (#подборка)</div>
            <div class="switch-sub">Тематические коллекции топ-аниме (Киберпанк, Фэнтези, Триллеры и др.)</div>
          </div>
          <label class="switch">
            <input type="checkbox" id="cfg_compilations_enabled" checked>
            <span class="slider"></span>
          </label>
        </div>

        <div class="switch-row">
          <div>
            <div class="switch-title">Жанровые хештеги к сериям (#фэнтези #онгоинг #серия10)</div>
            <div class="switch-sub">Удобная быстрая фильтрация по жанрам для подписчиков канала</div>
          </div>
          <label class="switch">
            <input type="checkbox" id="cfg_genre_hashtags_enabled" checked>
            <span class="slider"></span>
          </label>
        </div>

        <div class="switch-row">
          <div>
            <div class="switch-title">Кнопка «Обсудить серию в чате»</div>
            <div class="switch-sub">Показывать инлайн-кнопку обсуждения к сериям (если ссылка задана)</div>
          </div>
          <label class="switch">
            <input type="checkbox" id="cfg_chat_button_enabled">
            <span class="slider"></span>
          </label>
        </div>

        <div class="grid-2" style="margin-top:14px;">
          <div class="form-group">
            <div class="form-label">
              <span>Интервал серий/новостей (секунды):</span>
            </div>
            <input type="number" id="cfg_interval" value="300" min="30" step="30">
          </div>
          <div class="form-group">
            <div class="form-label">
              <span>Интервал подборок (часов):</span>
            </div>
            <input type="number" id="cfg_comp_hours" value="6" min="1" step="1">
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
        <div class="card-title">💾 Облачное Хранилище Supabase (Активно)</div>
        <div class="card-subtitle">
          База данных AnimeVist обеспечивает вечное сохранение настроек и истории опубликованных серий без риска потери данных:
        </div>

        <div style="background:var(--bg-surface); border:1px solid rgba(16,185,129,0.3); border-radius:var(--radius-sm); padding:16px; margin-bottom:15px;">
          <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;">
            <h4 style="color:#fff; font-size:0.92rem; display:flex; align-items:center; gap:8px;">
              <span>🐘 Supabase Database</span>
              <span style="font-size:0.7rem; background:rgba(16,185,129,0.15); color:#34d399; padding:2px 8px; border-radius:12px; font-weight:600;">АКТИВНА</span>
            </h4>
            <button class="btn btn-outline btn-sm" onclick="testSupabaseConnection()">
              🔌 Проверить связь
            </button>
          </div>
          <p style="font-size:0.8rem; color:var(--text-secondary); margin-bottom:12px; line-height:1.45;">
            Ваша облачная база данных AnimeVist подключена. Таблица <code>bot_config</code> хранит конфигурацию, а таблица <code>bot_seen_items</code> исключает повторные публикации серий и новостей.
          </p>

          <div class="form-group">
            <label class="form-label">SUPABASE_URL:</label>
            <input type="text" id="storage_supabase_url" value="https://zuciuwunelfqhhhohhyn.supabase.co">
          </div>
          <div class="form-group" style="margin-bottom:0;">
            <label class="form-label">SUPABASE_KEY:</label>
            <input type="password" id="storage_supabase_key">
          </div>
        </div>

        <div style="display:flex; gap:10px;">
          <button class="btn btn-primary btn-block" onclick="syncCloudNow()">
            ☁️ Загрузить бэкап в Supabase
          </button>
          <button class="btn btn-secondary btn-block" onclick="fetchCloudNow()">
            📥 Восстановить из Supabase
          </button>
        </div>
      </div>
    </section>

    <!-- TAB 5: CONSOLE -->
    <section id="tab-console" class="tab-content">
      <div class="card">
        <div class="console-header" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
          <div class="card-title" style="margin:0;">📟 Консоль Автономного Демона 24/7</div>
          <div style="display:flex; gap:8px;">
            <button class="btn btn-outline btn-sm" onclick="clearConsoleView()">🧹 Очистить</button>
            <button class="btn btn-outline btn-sm" onclick="fetchLogsOnly()">🔄 Обновить</button>
          </div>
        </div>

        <div class="terminal-container" id="terminalBox">
          <div class="log-line"><span class="log-ts">[00:00:00]</span> <span class="log-lvl info">INFO</span> <span class="log-msg">Ожидание событий демона...</span></div>
        </div>
      </div>
    </section>
  </main>

  <!-- Toast Container -->
  <div id="toastContainer"></div>

  <script>
    let currentConfig = null;
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

    async function loadData() {
      try {
        const res = await fetch('/api/status');
        const data = await res.json();
        currentConfig = data.config || {};
        const tg = currentConfig.telegram || {};
        const app = currentConfig.app || {};
        const ann = currentConfig.announcer || {};
        const cloud = currentConfig.cloud_storage || {};

        if (data.bot) {
          document.getElementById('headerStatusText').innerText = `@${data.bot.username} Онлайн`;
          document.getElementById('headerDot').className = 'status-dot';
          document.getElementById('kpiBotUser').innerText = `@${data.bot.username}`;
          document.getElementById('kpiBotId').innerText = `ID: ${data.bot.id} (${data.bot.first_name})`;
        } else {
          document.getElementById('headerStatusText').innerText = 'Ошибка подключения к боту';
          document.getElementById('headerDot').className = 'status-dot error';
          document.getElementById('kpiBotUser').innerText = 'Не подключен';
        }

        document.getElementById('kpiChannel').innerText = tg.channel_id || 'Не указан';
        document.getElementById('kpiInterval').innerText = `Серии: ${ann.check_interval_seconds || 300} сек`;
        document.getElementById('overviewLastCheck').innerText = data.last_check || 'Еще не выполнялся';
        document.getElementById('overviewCompInterval').innerText = `Каждые ${ann.compilations_interval_hours || 6} ч`;
        document.getElementById('overviewUptime').innerText = `${data.uptime_minutes || 0} мин`;
        document.getElementById('kpiLastSync').innerText = cloud.last_sync || 'Недавно';

        // Config form
        document.getElementById('cfg_token').value = tg.bot_token || '';
        document.getElementById('cfg_channel').value = tg.channel_id || '';
        document.getElementById('cfg_chat').value = app.chat_invite_url || '';
        document.getElementById('cfg_admin').value = tg.admin_id || '';
        document.getElementById('cfg_releases_enabled').checked = ann.enable_series_releases !== false;
        document.getElementById('cfg_news_enabled').checked = ann.enable_anime_news !== false;
        document.getElementById('cfg_compilations_enabled').checked = ann.enable_compilations !== false;
        document.getElementById('cfg_genre_hashtags_enabled').checked = ann.include_genre_hashtags !== false;
        document.getElementById('cfg_chat_button_enabled').checked = ann.show_chat_button === true;
        document.getElementById('cfg_interval').value = ann.check_interval_seconds || 300;
        document.getElementById('cfg_comp_hours').value = ann.compilations_interval_hours || 6;

        document.getElementById('storage_supabase_url').value = cloud.supabase_url || '';
        document.getElementById('storage_supabase_key').value = cloud.supabase_key || '';

        if (data.logs) {
          rawLogs = data.logs;
          renderLogs();
        }
      } catch (e) {
        showToast("Ошибка связи с сервером дашборда", "error");
      }
    }

    function renderLogs() {
      const box = document.getElementById('terminalBox');
      box.innerHTML = rawLogs.map(l => `
        <div class="log-line">
          <span class="log-ts">[${l.time}]</span>
          <span class="log-lvl ${l.level}">${l.level.toUpperCase()}</span>
          <span class="log-msg">${escapeHtml(l.message)}</span>
        </div>
      `).join('');
      box.scrollTop = box.scrollHeight;
    }

    function escapeHtml(text) {
      return (text || '').replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }

    function clearConsoleView() {
      rawLogs = [];
      renderLogs();
    }

    async function fetchLogsOnly() {
      try {
        const res = await fetch('/api/logs');
        rawLogs = await res.json();
        renderLogs();
      } catch (e) {}
    }

    async function runAction(actionName) {
      showToast(`Инициирован запуск [${actionName}]...`, "info");
      try {
        const res = await fetch('/api/action', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ action: actionName })
        });
        const data = await res.json();
        if (data.ok) {
          showToast(`Действие [${actionName}] запущено`, "success");
        } else {
          showToast(`Ошибка: ${data.error}`, "error");
        }
        setTimeout(fetchLogsOnly, 1200);
      } catch (e) {
        showToast("Ошибка отправки запроса", "error");
      }
    }

    async function publishCompilation() {
      const genre = document.getElementById('compilationGenreSelect').value;
      showToast("Публикация подборки аниме в Telegram...", "info");
      try {
        const res = await fetch('/api/action', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ action: 'compilation', genre: genre === 'auto' ? null : genre })
        });
        const data = await res.json();
        if (data.ok) {
          showToast("Подборка успешно отправлена в канал!", "success");
        } else {
          showToast(`Ошибка: ${data.error}`, "error");
        }
        setTimeout(fetchLogsOnly, 1200);
      } catch (e) {
        showToast("Ошибка публикации подборки", "error");
      }
    }

    function updateCustomPreview() {
      const text = document.getElementById('customText').value;
      const photo = document.getElementById('customPhoto').value.trim();
      const btnText = document.getElementById('customBtnText').value.trim();
      const btnUrl = document.getElementById('customBtnUrl').value.trim();

      const pText = document.getElementById('previewText');
      const pImg = document.getElementById('previewImg');
      const pBtn = document.getElementById('previewBtn');

      pText.innerHTML = text ? text.replace(/\\n/g, '<br>') : 'Текст вашего сообщения появится здесь...';

      if (photo && photo.startsWith('http')) {
        pImg.src = photo;
        pImg.style.display = 'block';
      } else {
        pImg.style.display = 'none';
      }

      if (btnText) {
        pBtn.innerText = btnText;
        pBtn.href = btnUrl || '#';
        pBtn.style.display = 'block';
      } else {
        pBtn.style.display = 'none';
      }
    }

    async function sendCustomPost() {
      const text = document.getElementById('customText').value.trim();
      if (!text) {
        showToast("Введите текст публикации", "error");
        return;
      }
      const photo = document.getElementById('customPhoto').value.trim();
      const btnText = document.getElementById('customBtnText').value.trim();
      const btnUrl = document.getElementById('customBtnUrl').value.trim();

      showToast("Отправка кастомного поста в канал...", "info");
      try {
        const res = await fetch('/api/custom-post', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            text: text,
            photo_url: photo,
            btn_text: btnText,
            btn_url: btnUrl
          })
        });
        const data = await res.json();
        if (data.ok) {
          showToast("Пост успешно опубликован в канале!", "success");
          document.getElementById('customText').value = '';
          updateCustomPreview();
        } else {
          showToast(`Ошибка: ${data.error}`, "error");
        }
        setTimeout(fetchLogsOnly, 1000);
      } catch (e) {
        showToast("Ошибка при отправке поста", "error");
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
        enable_compilations: document.getElementById('cfg_compilations_enabled').checked,
        include_genre_hashtags: document.getElementById('cfg_genre_hashtags_enabled').checked,
        show_chat_button: document.getElementById('cfg_chat_button_enabled').checked,
        compilations_interval_hours: parseFloat(document.getElementById('cfg_comp_hours').value) || 6,
        cloud_storage: {
          provider: 'supabase',
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
      showToast("Синхронизация с Supabase...", "info");
      try {
        const res = await fetch('/api/cloud-sync', { method: 'POST' });
        const data = await res.json();
        if (data.ok) {
          showToast("Бэкап успешно загружен в Supabase!", "success");
          loadData();
        } else {
          showToast(`Ошибка: ${data.error}`, "error", 5000);
        }
      } catch (e) {
        showToast("Ошибка синхронизации", "error");
      }
    }

    async function fetchCloudNow() {
      if (!confirm("Восстановить настройки из базы Supabase?")) return;
      showToast("Загрузка из Supabase...", "info");
      try {
        const res = await fetch('/api/cloud-fetch', { method: 'POST' });
        const data = await res.json();
        if (data.ok) {
          showToast("Настройки успешно восстановлены из Supabase!", "success");
          loadData();
        } else {
          showToast(`Ошибка: ${data.error}`, "error", 5000);
        }
      } catch (e) {
        showToast("Ошибка загрузки", "error");
      }
    }

    async function testSupabaseConnection() {
      showToast("Проверка связи с вашей базой Supabase...", "info");
      try {
        const res = await fetch('/api/test-supabase', { method: 'POST' });
        const data = await res.json();
        if (data.ok) {
          showToast("✅ Supabase успешно отвечает! (HTTP 200)", "success", 4000);
        } else {
          showToast(`❌ Ошибка Supabase: ${data.error}`, "error", 5000);
        }
      } catch (e) {
        showToast("Ошибка запроса к Supabase", "error");
      }
    }

    async function toggleDaemon() {
      try {
        const res = await fetch('/api/toggle-daemon', { method: 'POST' });
        const data = await res.json();
        if (data.paused) {
          showToast("Фоновый демон приостановлен", "info");
          document.getElementById('kpiDaemonStatus').innerText = "Пауза";
          document.getElementById('kpiDaemonStatus').style.color = "var(--warning)";
        } else {
          showToast("Фоновый демон возобновлен", "success");
          document.getElementById('kpiDaemonStatus').innerText = "Активен";
          document.getElementById('kpiDaemonStatus').style.color = "var(--success)";
        }
      } catch (e) {
        showToast("Ошибка переключения демона", "error");
      }
    }

    window.onload = () => {
      loadData();
      setInterval(fetchLogsOnly, 4000);
    };
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
        elif path == "/api/compilations-themes":
            self._send_json(list_available_themes())
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
            if 'enable_compilations' in data: ann['enable_compilations'] = bool(data['enable_compilations'])
            if 'include_genre_hashtags' in data: ann['include_genre_hashtags'] = bool(data['include_genre_hashtags'])
            if 'show_chat_button' in data: ann['show_chat_button'] = bool(data['show_chat_button'])
            if 'compilations_interval_hours' in data: ann['compilations_interval_hours'] = float(data['compilations_interval_hours'])

            if 'cloud_storage' in data and isinstance(data['cloud_storage'], dict):
                cloud.update(data['cloud_storage'])

            save_config(config, sync_to_cloud=True)
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
                log_event("Сообщение успешно доставлено в канал", "success")
                self._send_json({"ok": True})
            else:
                desc = res.get('description', 'Неизвестная ошибка Telegram API')
                log_event(f"Ошибка отправки сообщения: {desc}", "error")
                self._send_json({"ok": False, "error": desc})

        elif path == "/api/custom-post":
            config = load_config()
            sender = TelegramSender()
            channel = config.get('telegram', {}).get('channel_id')

            text = data.get('text', '').strip()
            photo_url = data.get('photo_url', '').strip()
            btn_text = data.get('btn_text', '').strip()
            btn_url = data.get('btn_url', '').strip()

            if not text:
                self._send_json({"ok": False, "error": "Текст сообщения не может быть пустым"})
                return

            reply_markup = None
            if btn_text and btn_url and btn_url.startswith('http'):
                reply_markup = {
                    "inline_keyboard": [
                        [{"text": btn_text, "url": btn_url}]
                    ]
                }

            if photo_url and photo_url.startswith('http'):
                res = sender.send_photo(photo_url, caption=text, chat_id=channel, reply_markup=reply_markup)
            else:
                res = sender.send_message(text, chat_id=channel, reply_markup=reply_markup)

            if res.get('ok'):
                log_event("Кастомный пост успешно опубликован в канале", "success")
                self._send_json({"ok": True})
            else:
                desc = res.get('description', 'Ошибка отправки')
                log_event(f"Ошибка отправки кастомного поста: {desc}", "error")
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
            provider = config.get('cloud_storage', {}).get('provider', 'supabase')
            if provider == 'supabase':
                res = fetch_config_from_supabase(config)
            elif provider == 'telegram':
                res = fetch_config_from_telegram(config)
            else:
                res = fetch_config_from_supabase(config)
            
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
            genre = data.get('genre')

            def run_bg(action_name, genre_param):
                try:
                    if action_name == 'releases':
                        log_event("Ручной запуск сканирования новых серий...")
                        cnt = run_series_check()
                        log_event(f"Сканирование серий завершено. Опубликовано: {cnt}", "success")
                    elif action_name == 'news':
                        log_event("Ручной запуск сбора аниме-новостей...")
                        cnt = run_news_check()
                        log_event(f"Сбор новостей завершен. Опубликовано: {cnt}", "success")
                    elif action_name == 'compilation':
                        log_event(f"Ручной запуск публикации подборки ({genre_param or 'авто'})...")
                        res_c = run_compilation_post(genre_key=genre_param)
                        if res_c.get('ok'):
                            log_event(f"Подборка успешно опубликована: {res_c.get('theme')}", "success")
                        else:
                            log_event(f"Ошибка публикации подборки: {res_c.get('error')}", "error")
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

            threading.Thread(target=run_bg, args=(act, genre), daemon=True).start()
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
        pass

def start_server(port=None):
    if port is None:
        env_port = os.environ.get("PORT")
        if env_port:
            preferred_port = int(env_port)
            ports_to_try = [preferred_port, 5000, 7860, 5001, 8080]
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
