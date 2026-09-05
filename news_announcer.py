"""
Standalone AnimeVist Anime News Announcer.
Monitors Shikimori official anime news forum and automatically
posts rich anime news cards (#news) to your Telegram channel.
"""

import os
import sys
import re
import json
import time
import urllib.request

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from telegram_sender import TelegramSender, load_config

SEEN_NEWS_FILE = os.path.join(os.path.dirname(__file__), 'seen_news.json')

def load_seen_news():
    if os.path.exists(SEEN_NEWS_FILE):
        try:
            with open(SEEN_NEWS_FILE, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_seen_news(seen_set):
    with open(SEEN_NEWS_FILE, 'w', encoding='utf-8') as f:
        items = list(seen_set)[-500:]
        json.dump(items, f, ensure_ascii=False, indent=2)

def strip_bbcode(text):
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def fetch_latest_news(limit=5):
    url = f"https://shikimori.one/api/topics?forum=news&limit={limit}"
    req = urllib.request.Request(url, headers={'User-Agent': 'AnimeVistBot/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"[News] Error fetching Shikimori news: {e}")
        return []

def fetch_topic_details(topic_id):
    url = f"https://shikimori.one/api/topics/{topic_id}"
    req = urllib.request.Request(url, headers={'User-Agent': 'AnimeVistBot/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"[News] Error fetching topic details {topic_id}: {e}")
        return None

def run_news_check(dry_run=False):
    config = load_config()
    sender = TelegramSender()
    seen = load_seen_news()

    topics = fetch_latest_news(limit=6)
    if not topics:
        return 0

    if len(seen) == 0:
        print("[News] Initializing seen_news database with recent topics (first run)...")
        for t in topics:
            seen.add(str(t.get('id')))
        save_seen_news(seen)
        print("[News] Initialized. Future new anime announcements will be posted automatically.")
        return 0

    published_count = 0
    max_per_cycle = 2

    for t in topics:
        if published_count >= max_per_cycle:
            break

        topic_id = str(t.get('id'))
        if topic_id in seen:
            continue

        details = fetch_topic_details(topic_id)
        if not details:
            continue

        title = details.get('topic_title', 'Новость из мира аниме')
        raw_body = details.get('body', '')
        clean_summary = strip_bbcode(raw_body)
        if len(clean_summary) > 400:
            clean_summary = clean_summary[:397] + '...'

        linked = details.get('linked') or {}
        image_url = None
        if isinstance(linked, dict) and linked.get('image'):
            orig = linked['image'].get('original')
            if orig:
                image_url = f"https://shikimori.one{orig}"

        app_name = config.get('app', {}).get('name', 'AnimeVist')
        app_url = config.get('app', {}).get('download_page_url', 'https://github.com/magver/AnimeVist-Releases/releases/latest')
        chat_url = config.get('app', {}).get('chat_invite_url', 'https://t.me/animevist_chat')

        caption = (
            f"📰 <b>{title}</b>\n\n"
            f"{clean_summary}\n\n"
            f"💬 <i>Обсуждаем новость в комментариях! Будете смотреть в {app_name}?</i>\n\n"
            f"#news #новости #{app_name.lower()}"
        )

        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": f"📲 Открыть {app_name}", "url": app_url},
                    {"text": "💬 Обсудить", "url": chat_url}
                ]
            ]
        }

        print(f"[News] Новая тема: {title}")
        if dry_run:
            print("[DRY-RUN] Preview:")
            print(caption)
            print("Image:", image_url)
        else:
            if image_url:
                res = sender.send_photo(image_url, caption=caption, reply_markup=reply_markup)
            else:
                res = sender.send_message(caption, reply_markup=reply_markup)
            
            if res.get('ok'):
                print(f"[News] ✅ Опубликовано: topic {topic_id}")
            else:
                print(f"[News] ❌ Ошибка: {res.get('description')}")

        seen.add(topic_id)
        save_seen_news(seen)
        published_count += 1
        time.sleep(2)

    return published_count

if __name__ == '__main__':
    run_news_check()
