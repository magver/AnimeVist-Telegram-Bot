"""
AnimeVist Web Dashboard & 24/7 Automation Server.
Provides a modern visual interface for managing the Telegram bot,
channel configuration, manual broadcasts, and running background 24/7 monitoring.
Works with standard Python libraries (zero external dependencies).
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

from telegram_sender import TelegramSender, load_config, save_config
from series_announcer import run_series_check
from news_announcer import run_news_check
from patchnote_publisher import publish_patchnote_from_github
from pinned_navigator import publish_pinned_navigator

# Global state
activity_logs = []
daemon_thread = None
daemon_running = True
last_check_time = None

def log_event(message, level="info"):
    timestamp = time.strftime('%H:%M:%S')
    entry = {"time": timestamp, "message": message, "level": level}
    activity_logs.append(entry)
    if len(activity_logs) > 100:
        activity_logs.pop(0)
    print(f"[{timestamp}] [{level.upper()}] {message}")

def background_monitoring_worker():
    global last_check_time, daemon_running
    log_event("Фоновый демон автопостинга 24/7 запущен", "success")
    
    while daemon_running:
        try:
            config = load_config()
            ann_conf = config.get('announcer', {})
            interval = ann_conf.get('check_interval_seconds', 300)
            
            # Check Series
            if ann_conf.get('enable_series_releases', True):
                log_event("Проверка новых серий аниме...")
                cnt = run_series_check()
                if cnt > 0:
                    log_event(f"Опубликовано новых серий: {cnt}", "success")
                else:
                    log_event("Новых серий пока нет")

            # Check News
            if ann_conf.get('enable_anime_news', True):
                log_event("Проверка аниме-новостей...")
                cnt_n = run_news_check()
                if cnt_n > 0:
                    log_event(f"Опубликовано аниме-новостей: {cnt_n}", "success")

            last_check_time = time.strftime('%d.%m.%Y %H:%M:%S')
        except Exception as e:
            log_event(f"Ошибка в цикле мониторинга: {e}", "error")

        # Sleep interval in small chunks for responsive shutdown
        config = load_config()
        sleep_total = config.get('announcer', {}).get('check_interval_seconds', 300)
        for _ in range(int(sleep_total)):
            if not daemon_running:
                break
            time.sleep(1)

def get_channel_auto_detect():
    config = load_config()
    token = config.get('telegram', {}).get('bot_token')
    if not token:
        return {"ok": False, "error": "Токен бота не указан"}
    
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'AnimeVistBot/1.0'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            results = data.get('result', [])
            for u in reversed(results):
                # Channel post update
                if 'channel_post' in u:
                    chat = u['channel_post'].get('chat', {})
                    return {
                        "ok": True,
                        "chat_id": chat.get('id'),
                        "title": chat.get('title'),
                        "username": chat.get('username')
                    }
                # Bot added to channel
                if 'my_chat_member' in u:
                    chat = u['my_chat_member'].get('chat', {})
                    if chat.get('type') == 'channel':
                        return {
                            "ok": True,
                            "chat_id": chat.get('id'),
                            "title": chat.get('title'),
                            "username": chat.get('username')
                        }
            return {"ok": False, "error": "В обновлениях бота пока нет сообщений из канала. Отправьте любое тестовое сообщение в канал или перешлите пост боту."}
    except Exception as e:
        return {"ok": False, "error": str(e)}

HTML_PAGE = """<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AnimeVist — Центр Управления Автоматизацией</title>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #090a0f;
      --card-bg: rgba(18, 20, 29, 0.85);
      --card-border: rgba(0, 240, 255, 0.15);
      --accent: #00f0ff;
      --accent-grad: linear-gradient(135deg, #00f0ff 0%, #7000ff 100%);
      --accent-purple: #7000ff;
      --text: #f0f4f8;
      --text-muted: #8e9bb0;
      --success: #00e676;
      --danger: #ff1744;
      --warning: #ffb300;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Outfit', sans-serif;
      background-color: var(--bg);
      background-image: 
        radial-gradient(circle at 10% 20%, rgba(112, 0, 255, 0.12) 0%, transparent 40%),
        radial-gradient(circle at 90% 80%, rgba(0, 240, 255, 0.1) 0%, transparent 40%);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }
    header {
      border-bottom: 1px solid var(--card-border);
      background: rgba(9, 10, 15, 0.9);
      backdrop-filter: blur(12px);
      padding: 1.2rem 2rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      position: sticky;
      top: 0;
      z-index: 100;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .brand-logo {
      width: 42px;
      height: 42px;
      background: var(--accent-grad);
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 1.3rem;
      box-shadow: 0 0 20px rgba(0, 240, 255, 0.4);
    }
    .brand h1 {
      font-size: 1.35rem;
      font-weight: 700;
      letter-spacing: -0.5px;
    }
    .brand span {
      font-size: 0.8rem;
      color: var(--accent);
      background: rgba(0, 240, 255, 0.1);
      padding: 2px 8px;
      border-radius: 20px;
      border: 1px solid rgba(0, 240, 255, 0.3);
      margin-left: 8px;
    }
    .status-badge {
      display: flex;
      align-items: center;
      gap: 8px;
      background: rgba(0, 230, 118, 0.1);
      border: 1px solid rgba(0, 230, 118, 0.3);
      padding: 6px 14px;
      border-radius: 30px;
      font-size: 0.85rem;
      font-weight: 500;
      color: var(--success);
    }
    .pulse-dot {
      width: 8px;
      height: 8px;
      background: var(--success);
      border-radius: 50%;
      box-shadow: 0 0 10px var(--success);
      animation: pulse 2s infinite;
    }
    @keyframes pulse {
      0% { transform: scale(0.95); opacity: 0.8; }
      50% { transform: scale(1.3); opacity: 1; }
      100% { transform: scale(0.95); opacity: 0.8; }
    }
    .container {
      max-width: 1280px;
      width: 100%;
      margin: 0 auto;
      padding: 2rem;
      flex: 1;
    }
    .tabs {
      display: flex;
      gap: 10px;
      margin-bottom: 2rem;
      border-bottom: 1px solid var(--card-border);
      padding-bottom: 10px;
    }
    .tab-btn {
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-family: inherit;
      font-size: 0.95rem;
      font-weight: 600;
      padding: 10px 20px;
      border-radius: 10px;
      cursor: pointer;
      transition: all 0.2s;
    }
    .tab-btn.active {
      color: #fff;
      background: rgba(0, 240, 255, 0.12);
      border: 1px solid rgba(0, 240, 255, 0.3);
      box-shadow: 0 0 15px rgba(0, 240, 255, 0.15);
    }
    .tab-pane { display: none; }
    .tab-pane.active { display: block; }
    
    .grid-2 {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1.5rem;
    }
    @media (max-width: 860px) {
      .grid-2 { grid-template-columns: 1fr; }
    }
    .card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 1.8rem;
      backdrop-filter: blur(10px);
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
      position: relative;
      overflow: hidden;
    }
    .card::before {
      content: '';
      position: absolute;
      top: 0; left: 0; right: 0; height: 2px;
      background: var(--accent-grad);
      opacity: 0.6;
    }
    .card h2 {
      font-size: 1.2rem;
      margin-bottom: 1.2rem;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .form-group {
      margin-bottom: 1.2rem;
    }
    label {
      display: block;
      font-size: 0.85rem;
      font-weight: 500;
      color: var(--text-muted);
      margin-bottom: 6px;
    }
    input[type="text"], input[type="number"], select {
      width: 100%;
      background: rgba(10, 12, 18, 0.8);
      border: 1px solid rgba(255, 255, 255, 0.12);
      color: #fff;
      padding: 11px 14px;
      border-radius: 10px;
      font-size: 0.95rem;
      font-family: inherit;
      outline: none;
      transition: border-color 0.2s, box-shadow 0.2s;
    }
    input[type="text"]:focus, input[type="number"]:focus {
      border-color: var(--accent);
      box-shadow: 0 0 10px rgba(0, 240, 255, 0.25);
    }
    .toggle-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    }
    .toggle-label {
      font-size: 0.95rem;
      font-weight: 500;
    }
    .toggle-desc {
      font-size: 0.75rem;
      color: var(--text-muted);
    }
    .switch {
      position: relative;
      display: inline-block;
      width: 48px;
      height: 26px;
    }
    .switch input { opacity: 0; width: 0; height: 0; }
    .slider {
      position: absolute; cursor: pointer;
      top: 0; left: 0; right: 0; bottom: 0;
      background-color: rgba(255, 255, 255, 0.2);
      transition: .3s;
      border-radius: 34px;
    }
    .slider:before {
      position: absolute; content: "";
      height: 18px; width: 18px; left: 4px; bottom: 4px;
      background-color: white;
      transition: .3s;
      border-radius: 50%;
    }
    input:checked + .slider { background: var(--accent-grad); }
    input:checked + .slider:before { transform: translateX(22px); }

    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 12px 20px;
      border-radius: 10px;
      font-family: inherit;
      font-size: 0.95rem;
      font-weight: 600;
      cursor: pointer;
      border: none;
      transition: all 0.2s;
    }
    .btn-primary {
      background: var(--accent-grad);
      color: #000;
      box-shadow: 0 0 15px rgba(0, 240, 255, 0.3);
    }
    .btn-primary:hover {
      box-shadow: 0 0 25px rgba(0, 240, 255, 0.6);
      transform: translateY(-1px);
    }
    .btn-secondary {
      background: rgba(255, 255, 255, 0.08);
      color: #fff;
      border: 1px solid rgba(255, 255, 255, 0.15);
    }
    .btn-secondary:hover {
      background: rgba(255, 255, 255, 0.15);
    }
    .btn-block { width: 100%; margin-top: 10px; }

    .action-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      margin-top: 15px;
    }
    .action-btn {
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 12px;
      padding: 16px;
      text-align: left;
      cursor: pointer;
      transition: all 0.2s;
      color: #fff;
    }
    .action-btn:hover {
      background: rgba(0, 240, 255, 0.08);
      border-color: var(--accent);
      transform: translateY(-2px);
    }
    .action-btn .icon { font-size: 1.5rem; margin-bottom: 8px; }
    .action-btn .title { font-weight: 600; font-size: 0.95rem; }
    .action-btn .subtitle { font-size: 0.75rem; color: var(--text-muted); margin-top: 4px; }

    .log-box {
      background: #06070a;
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 12px;
      padding: 14px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.85rem;
      height: 320px;
      overflow-y: auto;
      display: flex;
      flex-direction: column-reverse;
      gap: 6px;
    }
    .log-entry { display: flex; gap: 10px; line-height: 1.4; }
    .log-time { color: var(--text-muted); }
    .log-entry.info { color: #8ec5fc; }
    .log-entry.success { color: #00e676; }
    .log-entry.error { color: #ff5252; }

    .cloud-step {
      background: rgba(255, 255, 255, 0.03);
      border-left: 3px solid var(--accent);
      padding: 14px;
      border-radius: 0 10px 10px 0;
      margin-bottom: 12px;
    }
    .cloud-step h3 { font-size: 0.95rem; margin-bottom: 4px; color: #fff; }
    .cloud-step p { font-size: 0.82rem; color: var(--text-muted); }
    code {
      background: rgba(0, 0, 0, 0.4);
      padding: 2px 6px;
      border-radius: 4px;
      font-family: 'JetBrains Mono', monospace;
      color: var(--accent);
    }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <div class="brand-logo">V</div>
      <div>
        <h1>AnimeVist <span>Автоматизация</span></h1>
      </div>
    </div>
    <div class="status-badge" id="botStatusBadge">
      <div class="pulse-dot"></div>
      <span id="botStatusText">Бот подключен</span>
    </div>
  </header>

  <div class="container">
    <div class="tabs">
      <button class="tab-btn active" onclick="switchTab('tab-dashboard')">📊 Панель управления</button>
      <button class="tab-btn" onclick="switchTab('tab-settings')">⚙️ Настройки Telegram</button>
      <button class="tab-btn" onclick="switchTab('tab-cloud')">☁️ Работа 24/7 без ПК</button>
      <button class="tab-btn" onclick="switchTab('tab-logs')">📜 Журнал событий</button>
    </div>

    <!-- TAB 1: DASHBOARD -->
    <div id="tab-dashboard" class="tab-pane active">
      <div class="grid-2">
        <div class="card">
          <h2>⚡ 4 Пункта Автоматизации</h2>
          <p style="font-size:0.85rem; color:var(--text-muted); margin-bottom:15px;">Мгновенный ручной запуск любого из модулей ведения Telegram-канала:</p>
          
          <div class="action-grid">
            <div class="action-btn" onclick="runAction('releases')">
              <div class="icon">📺</div>
              <div class="title">1. Выход серий</div>
              <div class="subtitle">Постинг новых эпизодов онгоингов (#release)</div>
            </div>

            <div class="action-btn" onclick="runAction('news')">
              <div class="icon">📰</div>
              <div class="title">2. Аниме-новости</div>
              <div class="subtitle">Официальные анонсы и трейлеры (#news)</div>
            </div>

            <div class="action-btn" onclick="runAction('patchnote')">
              <div class="icon">🚀</div>
              <div class="title">3. Патчноут релиза</div>
              <div class="subtitle">Публикация свежего релиза из GitHub (#patchnote)</div>
            </div>

            <div class="action-btn" onclick="runAction('pinned')">
              <div class="icon">📌</div>
              <div class="title">4. Закрепить пост</div>
              <div class="subtitle">Навигатор с ссылками на APK и EXE (Pin)</div>
            </div>
          </div>

          <div style="margin-top:20px;">
            <button class="btn btn-secondary btn-block" onclick="sendTestMessage()">
              💬 Отправить тестовое сообщение в канал
            </button>
          </div>
        </div>

        <div class="card">
          <h2>📡 Статус автопостинга 24/7</h2>
          <div style="padding: 10px 0;">
            <div style="display:flex; justify-content:space-between; margin-bottom:12px;">
              <span style="color:var(--text-muted); font-size:0.9rem;">Фоновый сервис:</span>
              <strong style="color:var(--success);">● Активен (Каждые 5 минут)</strong>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:12px;">
              <span style="color:var(--text-muted); font-size:0.9rem;">Последняя проверка:</span>
              <span id="lastCheckVal" style="font-family:'JetBrains Mono'; font-size:0.85rem;">Только что</span>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:12px;">
              <span style="color:var(--text-muted); font-size:0.9rem;">Канал Telegram:</span>
              <span id="channelNameVal" style="font-family:'JetBrains Mono'; color:var(--accent);">—</span>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:12px;">
              <span style="color:var(--text-muted); font-size:0.9rem;">Имя бота:</span>
              <span id="botNameVal" style="color:#fff;">@vist_announcer_bot</span>
            </div>
          </div>

          <div style="margin-top:15px; border-top:1px solid rgba(255,255,255,0.08); padding-top:15px;">
            <button class="btn btn-secondary btn-block" onclick="autoDetectChannel()">
              🔍 Автоматически обнаружить ID канала из Telegram
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 2: SETTINGS -->
    <div id="tab-settings" class="tab-pane">
      <div class="card" style="max-width: 700px; margin: 0 auto;">
        <h2>⚙️ Настройки Telegram и Модулей</h2>
        
        <div class="form-group">
          <label>Токен Telegram-бота (от @BotFather):</label>
          <input type="text" id="cfg_token" placeholder="8821684307:AAE5...">
        </div>

        <div class="form-group">
          <label>ID или юзернейм канала (@channel или -100...):</label>
          <input type="text" id="cfg_channel" placeholder="@animevist_official">
        </div>

        <div class="form-group">
          <label>Ссылка или ID чата обсуждений:</label>
          <input type="text" id="cfg_chat" placeholder="https://t.me/animevist_chat">
        </div>

        <div class="form-group">
          <label>Интервал фонового опроса (секунды):</label>
          <input type="number" id="cfg_interval" value="300" min="60" step="30">
        </div>

        <div class="toggle-row">
          <div>
            <div class="toggle-label">Автопостинг новых серий (#release)</div>
            <div class="toggle-desc">Опрашивать AnimeVost + Shikimori и публиковать карточки</div>
          </div>
          <label class="switch">
            <input type="checkbox" id="cfg_releases_enabled" checked>
            <span class="slider"></span>
          </label>
        </div>

        <div class="toggle-row">
          <div>
            <div class="toggle-label">Автопостинг аниме-новостей (#news)</div>
            <div class="toggle-desc">Публиковать анонсы новых сезонов и трейлеры из Shikimori</div>
          </div>
          <label class="switch">
            <input type="checkbox" id="cfg_news_enabled" checked>
            <span class="slider"></span>
          </label>
        </div>

        <div style="margin-top: 25px;">
          <button class="btn btn-primary btn-block" onclick="saveSettings()">
            💾 Сохранить настройки
          </button>
        </div>
      </div>
    </div>

    <!-- TAB 3: CLOUD 24/7 -->
    <div id="tab-cloud" class="tab-pane">
      <div class="card" style="max-width: 800px; margin: 0 auto;">
        <h2>☁️ Запуск 24/7 без включенного компьютера</h2>
        <p style="color:var(--text-muted); font-size:0.9rem; margin-bottom:20px;">
          Чтобы система публиковала серии, новости и обновляла закрепленный навигатор непрерывно, даже когда ваш компьютер выключен, сервис можно развернуть на бесплатном облачном хостинге.
        </p>

        <div class="cloud-step">
          <h3>Способ 1: Бесплатный хостинг Render.com (Рекомендуется, 2 минуты)</h3>
          <p>
            1. Зарегистрируйтесь на <a href="https://render.com" target="_blank" style="color:var(--accent);">Render.com</a> (через GitHub).<br>
            2. Загрузите эту папку (<code>tg AnimeVist</code>) в свой приватный или публичный репозиторий GitHub.<br>
            3. В панели Render нажмите <b>New +</b> &rarr; <b>Web Service</b> &rarr; выберите ваш репозиторий.<br>
            4. Выберите среду <b>Python 3</b>, команда запуска: <code>python web_dashboard.py</code>.<br>
            5. Нажмите <b>Create Web Service</b> — Render выдаст вам ссылку на ваш личный веб-интерфейс, и бот будет работать <b>24/7 круглый год бесплатно</b>!
          </p>
        </div>

        <div class="cloud-step">
          <h3>Способ 2: Запуск в Docker на любом сервере / VPS</h3>
          <p>
            В папку уже включены готовые файлы <code>Dockerfile</code> и <code>docker-compose.yml</code>.<br>
            Достаточно одной команды в консоли сервера: <code>docker-compose up -d</code>.
          </p>
        </div>

        <div class="cloud-step">
          <h3>Способ 3: Linux VPS (systemd)</h3>
          <p>
            Файл службы <code>animevist-bot.service</code> уже настроен. Выполните на сервере:<br>
            <code>cp animevist-bot.service /etc/systemd/system/ && systemctl enable --now animevist-bot</code>
          </p>
        </div>
      </div>
    </div>

    <!-- TAB 4: LOGS -->
    <div id="tab-logs" class="tab-pane">
      <div class="card">
        <h2>📜 Журнал работы в реальном времени</h2>
        <div class="log-box" id="logBox">
          <!-- Live logs injected here -->
        </div>
        <div style="margin-top:15px; display:flex; justify-content:flex-end;">
          <button class="btn btn-secondary" onclick="fetchLogs()">🔄 Обновить логи</button>
        </div>
      </div>
    </div>
  </div>

  <script>
    function switchTab(tabId) {
      document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));
      document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
      document.getElementById(tabId).classList.add('active');
      event.target.classList.add('active');
    }

    async function loadData() {
      try {
        const res = await fetch('/api/status');
        const data = await res.json();
        if (data.bot) {
          document.getElementById('botNameVal').innerText = '@' + data.bot.username + ' (' + data.bot.first_name + ')';
          document.getElementById('botStatusText').innerText = 'Бот онлайн: @' + data.bot.username;
        }
        if (data.config) {
          document.getElementById('cfg_token').value = data.config.telegram.bot_token || '';
          document.getElementById('cfg_channel').value = data.config.telegram.channel_id || '';
          document.getElementById('cfg_chat').value = data.config.app.chat_invite_url || '';
          document.getElementById('cfg_interval').value = data.config.announcer.check_interval_seconds || 300;
          document.getElementById('cfg_releases_enabled').checked = data.config.announcer.enable_series_releases !== false;
          document.getElementById('cfg_news_enabled').checked = data.config.announcer.enable_anime_news !== false;
          document.getElementById('channelNameVal').innerText = data.config.telegram.channel_id || 'Не задан';
        }
        if (data.last_check) {
          document.getElementById('lastCheckVal').innerText = data.last_check;
        }
        renderLogs(data.logs || []);
      } catch (e) {
        console.error("Ошибка загрузки данных:", e);
      }
    }

    function renderLogs(logs) {
      const box = document.getElementById('logBox');
      box.innerHTML = logs.map(l => 
        `<div class="log-entry ${l.level}"><span class="log-time">[${l.time}]</span> <span>${l.message}</span></div>`
      ).join('');
    }

    async function fetchLogs() {
      const res = await fetch('/api/logs');
      const logs = await res.json();
      renderLogs(logs);
    }

    async function runAction(action) {
      alert("Запуск действия: " + action + ". Смотрите журнал событий.");
      await fetch('/api/action', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ action: action })
      });
      fetchLogs();
    }

    async function sendTestMessage() {
      const res = await fetch('/api/test-message', { method: 'POST' });
      const data = await res.json();
      alert(data.ok ? "✅ Тестовое сообщение успешно отправлено!" : "❌ Ошибка: " + data.error);
      fetchLogs();
    }

    async function autoDetectChannel() {
      alert("Бот проверяет последние обновления Telegram... Убедитесь, что в канал было отправлено хотя бы 1 сообщение.");
      const res = await fetch('/api/auto-detect-channel', { method: 'POST' });
      const data = await res.json();
      if (data.ok) {
        alert("🎉 Канал обнаружен: " + data.title + " (ID: " + data.chat_id + ")");
        document.getElementById('cfg_channel').value = data.chat_id;
        saveSettings();
      } else {
        alert("⚠️ " + data.error);
      }
    }

    async function saveSettings() {
      const payload = {
        bot_token: document.getElementById('cfg_token').value.trim(),
        channel_id: document.getElementById('cfg_channel').value.trim(),
        chat_invite_url: document.getElementById('cfg_chat').value.trim(),
        interval: parseInt(document.getElementById('cfg_interval').value) || 300,
        enable_releases: document.getElementById('cfg_releases_enabled').checked,
        enable_news: document.getElementById('cfg_news_enabled').checked
      };
      const res = await fetch('/api/save-config', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.ok) {
        alert("✅ Настройки успешно сохранены!");
        loadData();
      } else {
        alert("❌ Ошибка: " + data.error);
      }
    }

    loadData();
    setInterval(fetchLogs, 5000);
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
            resp = {
                "bot": me.get('result') if me.get('ok') else None,
                "config": config,
                "last_check": last_check_time,
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
        data = json.loads(body) if body else {}

        if path == "/api/save-config":
            config = load_config()
            config['telegram']['bot_token'] = data.get('bot_token', config['telegram'].get('bot_token'))
            config['telegram']['channel_id'] = data.get('channel_id', config['telegram'].get('channel_id'))
            config['app']['chat_invite_url'] = data.get('chat_invite_url', config['app'].get('chat_invite_url'))
            config['announcer']['check_interval_seconds'] = data.get('interval', 300)
            config['announcer']['enable_series_releases'] = data.get('enable_releases', True)
            config['announcer']['enable_anime_news'] = data.get('enable_news', True)
            save_config(config)
            log_event("Настройки успешно сохранены через веб-интерфейс", "success")
            self._send_json({"ok": True})

        elif path == "/api/test-message":
            config = load_config()
            sender = TelegramSender()
            channel = config.get('telegram', {}).get('channel_id')
            res = sender.send_message(
                "🤖 <b>AnimeVist — Тест подключения!</b>\n\nВеб-интерфейс успешно подключен к каналу.",
                chat_id=channel
            )
            if res.get('ok'):
                log_event("Тестовое сообщение успешно доставлено в канал", "success")
                self._send_json({"ok": True})
            else:
                desc = res.get('description', 'Неизвестная ошибка')
                log_event(f"Ошибка отправки теста: {desc}", "error")
                self._send_json({"ok": False, "error": desc})

        elif path == "/api/auto-detect-channel":
            res = get_channel_auto_detect()
            if res.get('ok'):
                config = load_config()
                config['telegram']['channel_id'] = str(res['chat_id'])
                save_config(config)
                log_event(f"Канал обнаружен автоматически: {res.get('title')} ({res.get('chat_id')})", "success")
            self._send_json(res)

        elif path == "/api/action":
            act = data.get('action')
            def run_bg(action_name):
                try:
                    if action_name == 'releases':
                        log_event("Запуск ручной проверки серий...")
                        cnt = run_series_check()
                        log_event(f"Проверка серий завершена. Опубликовано: {cnt}", "success")
                    elif action_name == 'news':
                        log_event("Запуск проверки аниме-новостей...")
                        cnt = run_news_check()
                        log_event(f"Проверка новостей завершена. Опубликовано: {cnt}", "success")
                    elif action_name == 'patchnote':
                        log_event("Публикация патчноута релиза из GitHub...")
                        res = publish_patchnote_from_github()
                        log_event("Публикация патчноута завершена", "success" if res else "error")
                    elif action_name == 'pinned':
                        log_event("Отправка и закрепление поста-навигатора...")
                        res = publish_pinned_navigator()
                        log_event("Закрепление навигатора завершено", "success" if res else "error")
                except Exception as e:
                    log_event(f"Ошибка выполнения действия {action_name}: {e}", "error")

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
        # Silence default HTTP access log spam in console
        pass

def start_server(port=None):
    if port is None:
        port = int(os.environ.get("PORT", 5000))
    
    server = HTTPServer(("0.0.0.0", port), DashboardHandler)
    print(f"\n=======================================================")
    print(f"  🌟 ANIME VIST ВЕБ-ИНТЕРФЕЙС УПРАВЛЕНИЯ ЗАПУЩЕН")
    print(f"  🌐 Локальный адрес: http://localhost:{port}")
    print(f"  ☁️ Серверный адрес: http://0.0.0.0:{port}")
    print(f"=======================================================\n")
    log_event(f"Веб-сервер запущен на порту {port}", "info")

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
