"""
AnimeVist Dynamic & Curated Anime Compilations Engine.
Generates themed Top 3-5 anime collections (Must-Watch, Hidden Gems, Mindfuck, Sci-Fi, etc.),
combines all posters into a single high-resolution collage banner using Pillow,
prevents repeats by tracking seen anime IDs, and posts rich cards with hashtags (#подборка).
"""

import os
import sys
import io
import json
import time
import urllib.request
import urllib.parse
from PIL import Image, ImageDraw

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from telegram_sender import (
    TelegramSender,
    load_config,
    load_seen_from_supabase,
    save_seen_to_supabase
)

SEEN_ANIMES_FILE = os.path.join(os.path.dirname(__file__), 'seen_compilation_animes.json')
LAST_COMPILATION_FILE = os.path.join(os.path.dirname(__file__), 'last_compilation_time.json')
COLLAGE_DIR = os.path.join(os.path.dirname(__file__), 'scratch')

# Curated Thematic Presets
THEMES = {
    "must_watch": {
        "key": "must_watch",
        "name": "🏆 Обязательно к просмотру (Шедевры 8.5+)",
        "title": "Обязательно к просмотру (Золотой фонд аниме) 🏆",
        "desc": "Культовые тайтлы с высочайшим мировым рейтингом, навсегда вошедшие в историю:",
        "tags": "#шедевры #must_watch #топ_аниме",
        "shiki_genre": None,
        "shiki_order": "ranked",
        "candidates": [
            {"id": 52991, "ru": "Провожающая в последний путь Фрирен", "en": "Sousou no Frieren", "score": "9.25", "genres": "Фэнтези, Драма", "poster": "https://shikimori.one/system/animes/original/52991.jpg", "hook": "Бессмертная эльфийка отправляется в путь, чтобы постичь ценность человеческой жизни."},
            {"id": 5114, "ru": "Стальной алхимик: Братство", "en": "Fullmetal Alchemist: Brotherhood", "score": "9.11", "genres": "Сёнэн, Фэнтези", "poster": "https://shikimori.one/system/animes/original/5114.jpg", "hook": "Братья Элрики ищут философский камень, чтобы вернуть утраченные тела."},
            {"id": 9253, "ru": "Врата Штейна", "en": "Steins;Gate", "score": "9.07", "genres": "Фантастика, Триллер", "poster": "https://shikimori.one/system/animes/original/9253.jpg", "hook": "Случайное создание машины времени в микроволновке втягивает друзей в опасный заговор."},
            {"id": 11061, "ru": "Охотник х Охотник (2011)", "en": "Hunter x Hunter", "score": "9.04", "genres": "Экшен, Приключения", "poster": "https://shikimori.one/system/animes/original/11061.jpg", "hook": "Гон отправляется на смертельный экзамен Охотников ради поисков легендарного отца."},
            {"id": 19, "ru": "Монстр", "en": "Monster", "score": "8.87", "genres": "Драма, Триллер", "poster": "https://shikimori.one/system/animes/original/19.jpg", "hook": "Гениальный хирург спасает жизнь мальчику, не зная, что взрастил абсолютное зло."},
            {"id": 1, "ru": "Ковбой Бибоп", "en": "Cowboy Bebop", "score": "8.75", "genres": "Фантастика, Экшен", "poster": "https://shikimori.one/system/animes/original/1.jpg", "hook": "Охотники за головами бороздят Солнечную систему под звуки бессмертного джаза."},
            {"id": 2001, "ru": "Гуррен-Лаганн", "en": "Tengen Toppa Gurren Lagann", "score": "8.63", "genres": "Экшен, Меха", "poster": "https://shikimori.one/system/animes/original/2001.jpg", "hook": "Симон и Камина бурят путь наверх сквозь пространство, бросая вызов Вселенной."}
        ]
    },
    "hidden_gems": {
        "key": "hidden_gems",
        "name": "💎 Недооценённые алмазы (Hidden Gems)",
        "title": "Недооценённые шедевры, которые вы могли пропустить 💎",
        "desc": "Редкие находки с великолепным сюжетом, незаслуженно оставшиеся в тени хайпа:",
        "tags": "#hidden_gems #недооцененное #чтопосмотреть",
        "shiki_genre": None,
        "shiki_order": "ranked",
        "candidates": [
            {"id": 13125, "ru": "Из нового света", "en": "Shinsekai yori", "score": "8.27", "genres": "Драма, Фантастика", "poster": "https://shikimori.one/system/animes/original/13125.jpg", "hook": "Идеальное утопическое общество телекинетиков скрывает леденящую тайну."},
            {"id": 22535, "ru": "Паразит: Учение о жизни", "en": "Kiseijuu: Sei no Kakuritsu", "score": "8.34", "genres": "Экшен, Ужасы", "poster": "https://shikimori.one/system/animes/original/22535.jpg", "hook": "Инопланетный паразит заменяет руку школьника, превращая его жизнь в войну за выживание."},
            {"id": 1279, "ru": "Эрго Прокси", "en": "Ergo Proxy", "score": "7.91", "genres": "Детектив, Психология", "poster": "https://shikimori.one/system/animes/original/1279.jpg", "hook": "Загадки постапокалиптического города-купола, где андроиды внезапно обретают душу."},
            {"id": 457, "ru": "Клеймор", "en": "Claymore", "score": "7.80", "genres": "Тёмное фэнтези, Экшен", "poster": "https://shikimori.one/system/animes/original/457.jpg", "hook": "Воительницы-полудемоны с серебряными глазами очищают континент от чудовищ-йома."},
            {"id": 486, "ru": "Кино не таби: Прекрасный мир", "en": "Kino no Tabi", "score": "8.38", "genres": "Приключения, Философия", "poster": "https://shikimori.one/system/animes/original/486.jpg", "hook": "Путешественница Кино и говорящий мотоцикл исследуют причудливые обычаи стран мира."}
        ]
    },
    "mindfuck": {
        "key": "mindfuck",
        "name": "🧠 Игры разума & Психологические триллеры",
        "title": "ТОП: Психологические Триллеры и Игры Разума 🧠",
        "desc": "Напряженные сюжеты, невероятные многоходовки и неожиданные сюжетные твисты:",
        "tags": "#триллер #психология #детектив #сюжет",
        "shiki_genre": 40,
        "shiki_order": "ranked",
        "candidates": [
            {"id": 1535, "ru": "Тетрадь смерти", "en": "Death Note", "score": "8.62", "genres": "Мистика, Детектив", "poster": "https://shikimori.one/system/animes/original/1535.jpg", "hook": "Интеллектуальная дуэль школьника с тетрадью бога смерти и гениального сыщика L."},
            {"id": 19, "ru": "Монстр", "en": "Monster", "score": "8.87", "genres": "Драма, Триллер", "poster": "https://shikimori.one/system/animes/original/19.jpg", "hook": "Хирург спасает жизнь мальчику, не подозревая, что взрастил абсолютное зло."},
            {"id": 13601, "ru": "Психопаспорт", "en": "Psycho-Pass", "score": "8.34", "genres": "Детектив, Триллер", "poster": "https://shikimori.one/system/animes/original/13601.jpg", "hook": "Система «Сивилла» вычисляет вероятность преступления еще до его совершения."},
            {"id": 9253, "ru": "Врата Штейна", "en": "Steins;Gate", "score": "9.07", "genres": "Фантастика, Триллер", "poster": "https://shikimori.one/system/animes/original/9253.jpg", "hook": "Случайное изобретение машины времени в микроволновке втягивает друзей в заговор."},
            {"id": 40591, "ru": "Госпожа Кагуя: Война разума", "en": "Kaguya-sama", "score": "8.89", "genres": "Психология, Комедия", "poster": "https://shikimori.one/system/animes/original/40591.jpg", "hook": "Интеллектуальная битва двух гениев за первое признание в чувствах."}
        ]
    },
    "cyberpunk_scifi": {
        "key": "cyberpunk_scifi",
        "name": "🌆 Киберпанк & Научная фантастика",
        "title": "ТОП: Культовый Киберпанк и Научная Фантастика 🌆",
        "desc": "Мрачное будущее, аугментации, искусственный интеллект и неоновые мегаполисы:",
        "tags": "#киберпанк #фантастика #scifi",
        "shiki_genre": 24,
        "shiki_order": "ranked",
        "candidates": [
            {"id": 42310, "ru": "Киберпанк: Бегущие по краю", "en": "Cyberpunk: Edgerunners", "score": "8.62", "genres": "Экшен, Фантастика", "poster": "https://shikimori.one/system/animes/original/42310.jpg", "hook": "Парень из трущоб теряет всё и становится наемником в безжалостном Найт-Сити."},
            {"id": 43, "ru": "Призрак в доспехах", "en": "Ghost in the Shell", "score": "8.28", "genres": "Экшен, Меха", "poster": "https://shikimori.one/system/animes/original/43.jpg", "hook": "Майор Мотоко Кусанаги расследует киберпреступления на грани человечности."},
            {"id": 13601, "ru": "Психопаспорт", "en": "Psycho-Pass", "score": "8.34", "genres": "Детектив, Триллер", "poster": "https://shikimori.one/system/animes/original/13601.jpg", "hook": "Будущее, где криминальный коэффициент людей сканируется автоматическими системами."},
            {"id": 1279, "ru": "Эрго Прокси", "en": "Ergo Proxy", "score": "7.91", "genres": "Детектив, Психология", "poster": "https://shikimori.one/system/animes/original/1279.jpg", "hook": "Тайны города-купола, где андроиды внезапно обретают самосознание."}
        ]
    },
    "epic_fantasy": {
        "key": "epic_fantasy",
        "name": "⚔️ Эпическое фэнтези и приключения 8.5+",
        "title": "ТОП: Грандиозное Фэнтези и Приключения (8.5+) ⚔️",
        "desc": "Магия, масштабные миры, эпические сражения и незабываемые путешествия:",
        "tags": "#фэнтези #приключения #эпик",
        "shiki_genre": 10,
        "shiki_order": "ranked",
        "candidates": [
            {"id": 52991, "ru": "Провожающая в последний путь Фрирен", "en": "Sousou no Frieren", "score": "9.25", "genres": "Фэнтези, Драма", "poster": "https://shikimori.one/system/animes/original/52991.jpg", "hook": "Эльфийская волшебница познает тепло человеческих уз после победы над Владыкой Демонов."},
            {"id": 37521, "ru": "Сага о Винланде", "en": "Vinland Saga", "score": "8.75", "genres": "Экшен, Приключения", "poster": "https://shikimori.one/system/animes/original/37521.jpg", "hook": "Юный Торфинн жаждет мести за отца посреди суровых завоевательных походов викингов."},
            {"id": 11061, "ru": "Охотник х Охотник", "en": "Hunter x Hunter", "score": "9.04", "genres": "Экшен, Приключения", "poster": "https://shikimori.one/system/animes/original/11061.jpg", "hook": "Гон и друзья преодолевают смертельные испытания невероятного мира Охотников."},
            {"id": 33, "ru": "Берсерк (1997)", "en": "Berserk", "score": "8.57", "genres": "Тёмное фэнтези, Военное", "poster": "https://shikimori.one/system/animes/original/33.jpg", "hook": "Одинокий мечник Гатс встречает харизматичного Гриффита и вступает в Отряд Сокола."}
        ]
    },
    "soul_romance": {
        "key": "soul_romance",
        "name": "💖 Ламповая романтика для души",
        "title": "ТОП: Трогательная Романтика для Теплого Вечера 💖",
        "desc": "Искренние чувства, неловкие признания, поддержка и уютная атмосфера:",
        "tags": "#романтика #повседневность #уют",
        "shiki_genre": 22,
        "shiki_order": "ranked",
        "candidates": [
            {"id": 37999, "ru": "Госпожа Кагуя: В любви как на войне", "en": "Kaguya-sama", "score": "8.89", "genres": "Комедия, Романтика", "poster": "https://shikimori.one/system/animes/original/37999.jpg", "hook": "Президенты студсовета ведут битву умов за первое признание в любви."},
            {"id": 42897, "ru": "Хоримия", "en": "Horimiya", "score": "8.19", "genres": "Школа, Романтика", "poster": "https://shikimori.one/system/animes/original/42897.jpg", "hook": "Два разных старшеклассника открывают друг другу свои настоящие тайные стороны."},
            {"id": 4181, "ru": "Кланнад: Продолжение истории", "en": "Clannad: After Story", "score": "8.93", "genres": "Драма, Романтика", "hook": "Трогательная история взросления, семейных ценностей и настоящей любви.", "poster": "https://shikimori.one/system/animes/original/4181.jpg"},
            {"id": 14813, "ru": "Как и ожидалось, моя школьная жизнь не задалась", "en": "Oregairu", "score": "8.24", "genres": "Драма, Романтика", "poster": "https://shikimori.one/system/animes/original/14813.jpg", "hook": "Циничный школьник Хатиман помогает одноклассникам находить общий язык."}
        ]
    },
    "pure_comedy": {
        "key": "pure_comedy",
        "name": "😂 Отборные комедии & Позитив",
        "title": "ТОП: Безумные Комедии для Отличного Настроения 😂",
        "desc": "Море отборного юмора, ярких персонажей и гарантированный заряд позитива:",
        "tags": "#комедия #пародия #позитив",
        "shiki_genre": 4,
        "shiki_order": "ranked",
        "candidates": [
            {"id": 918, "ru": "Гинтама", "en": "Gintama", "score": "8.93", "genres": "Пародия, Экшен", "poster": "https://shikimori.one/system/animes/original/918.jpg", "hook": "Самураи, пришельцы и мастер абсурдного юмора Гинтоки Саката в феодальной Японии."},
            {"id": 33255, "ru": "Необъятный океан", "en": "Grand Blue", "score": "8.44", "genres": "Комедия, Студенты", "poster": "https://shikimori.one/system/animes/original/33255.jpg", "hook": "Безумная жизнь студенческого дайвинг-клуба, полная вечеринок и дружбы."},
            {"id": 32281, "ru": "Несладкая жизнь псионика Сайки К.", "en": "Saiki Kusuo", "score": "8.41", "genres": "Комедия, Сверхъестественное", "poster": "https://shikimori.one/system/animes/original/32281.jpg", "hook": "Могущественный экстрасенс хочет спокойной жизни, но чудаки вокруг не дают покоя."},
            {"id": 30831, "ru": "Этот замечательный мир! (KonoSuba)", "en": "KonoSuba", "score": "8.10", "genres": "Комедия, Пародия", "poster": "https://shikimori.one/system/animes/original/30831.jpg", "hook": "Казума берет с собой бесполезную богиню Акву и собирает чудаковатую команду."}
        ]
    },
    "isekai_special": {
        "key": "isekai_special",
        "name": "🌀 Захватывающие исекаи с изюминкой",
        "title": "ТОП: Лучшие Исекаи с Необычной Завязкой 🌀",
        "desc": "Попаданцы в другие миры, где всё пошло не по стандартному сценарию:",
        "tags": "#исекай #фэнтези #приключения",
        "shiki_genre": None,
        "shiki_order": "ranked",
        "candidates": [
            {"id": 39535, "ru": "Реинкарнация безработного", "en": "Mushoku Tensei", "score": "8.65", "genres": "Магия, Приключения", "poster": "https://shikimori.one/system/animes/original/39535.jpg", "hook": "34-летний затворник получает второй шанс прожить достойную жизнь с мечом и магией."},
            {"id": 31240, "ru": "Re:Zero — жизнь с нуля в другом мире", "en": "Re:Zero", "score": "8.23", "genres": "Триллер, Драма", "poster": "https://shikimori.one/system/animes/original/31240.jpg", "hook": "Субару Нацуки обретает способность возвращаться во времени только после своей гибели."},
            {"id": 37430, "ru": "О моём перерождении в слизь", "en": "Tensei Slime", "score": "8.12", "genres": "Фэнтези, Сёнэн", "poster": "https://shikimori.one/system/animes/original/37430.jpg", "hook": "Офисный клерк перерождается слизью и строит процветающую федерацию монстров."},
            {"id": 29803, "ru": "Повелитель (Overlord)", "en": "Overlord", "score": "7.92", "genres": "Фэнтези, Экшен", "poster": "https://shikimori.one/system/animes/original/29803.jpg", "hook": "Геймер остается заперт в теле могущественного скелета-мага в новом неизведанном мире."}
        ]
    }
}

def load_seen_compilation_animes():
    seen = set()
    if os.path.exists(SEEN_ANIMES_FILE):
        try:
            with open(SEEN_ANIMES_FILE, 'r', encoding='utf-8') as f:
                seen.update(json.load(f))
        except Exception:
            pass
    try:
        remote_seen = load_seen_from_supabase(category='compilation_anime')
        seen.update(str(s) for s in remote_seen)
    except Exception:
        pass
    return seen

def save_seen_compilation_animes(seen_set):
    try:
        with open(SEEN_ANIMES_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(seen_set)[-1000:], f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    try:
        save_seen_to_supabase(seen_set, category='compilation_anime')
    except Exception:
        pass

def load_last_compilation_time():
    if os.path.exists(LAST_COMPILATION_FILE):
        try:
            with open(LAST_COMPILATION_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return float(data.get('timestamp', 0))
        except Exception:
            pass
    return 0

def save_last_compilation_time(ts=None):
    if ts is None:
        ts = time.time()
    try:
        with open(LAST_COMPILATION_FILE, 'w', encoding='utf-8') as f:
            json.dump({"timestamp": ts, "formatted": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))}, f, indent=2)
    except Exception:
        pass

def download_image(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'AnimeVistBot/1.0'})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return Image.open(io.BytesIO(resp.read()))

def create_compilation_collage(poster_urls, title_text, output_filename="compilation_collage.jpg"):
    """
    Downloads all poster images and composites them into a single high-resolution collage.
    """
    os.makedirs(COLLAGE_DIR, exist_ok=True)
    out_path = os.path.join(COLLAGE_DIR, output_filename)

    images = []
    for u in poster_urls:
        try:
            img = download_image(u).convert("RGB")
            images.append(img)
        except Exception as e:
            print(f"[Compilations] Ошибка загрузки постера {u}: {e}")

    if not images:
        return None

    n = len(images)
    target_h = 420 if n <= 4 else 380
    resized = []
    for img in images:
        ratio = target_h / img.height
        new_w = int(img.width * ratio)
        resized.append(img.resize((new_w, target_h), Image.Resampling.LANCZOS))

    gap = 4
    total_w = sum(img.width for img in resized) + (n - 1) * gap
    banner_h = 48
    final_h = target_h + banner_h

    collage = Image.new("RGB", (total_w, final_h), (9, 13, 22))
    draw = ImageDraw.Draw(collage)

    # Header banner
    draw.rectangle([(0, 0), (total_w, banner_h)], fill=(15, 23, 42))
    draw.line([(0, banner_h), (total_w, banner_h)], fill=(59, 130, 246), width=2)
    draw.text((14, 13), f"AnimeVist • {title_text}", fill=(248, 250, 252))

    # Paste sub-posters and add badges
    curr_x = 0
    for idx, img in enumerate(resized, 1):
        collage.paste(img, (curr_x, banner_h))
        bx = curr_x + 8
        by = banner_h + 8
        draw.rectangle([(bx, by), (bx + 28, by + 28)], fill=(37, 99, 235))
        draw.text((bx + 10, by + 6), str(idx), fill=(255, 255, 255))
        curr_x += img.width + gap

    collage.save(out_path, "JPEG", quality=92)
    print(f"[Compilations] Фотоколлаж успешно сгенерирован ({n} постеров): {out_path}")
    return out_path

def fetch_shikimori_candidates(genre_id=None, order="ranked", limit=20):
    """
    Queries Shikimori API dynamically to discover additional titles.
    """
    params = [f"order={order}", f"limit={limit}"]
    if genre_id:
        params.append(f"genre={genre_id}")
    url = f"https://shikimori.one/api/animes?{'&'.join(params)}"
    req = urllib.request.Request(url, headers={'User-Agent': 'AnimeVistBot/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            results = []
            for a in data:
                img_path = a.get('image', {}).get('original', '')
                if not img_path or 'missing' in img_path:
                    continue
                results.append({
                    "id": a.get('id'),
                    "ru": a.get('russian') or a.get('name'),
                    "en": a.get('name'),
                    "score": a.get('score', '—'),
                    "genres": "Аниме, Приключения",
                    "poster": f"https://shikimori.one{img_path}",
                    "hook": "Захватывающий сюжет с высоким рейтингом зрителей."
                })
            return results
    except Exception as e:
        print(f"[Compilations] Shikimori query error: {e}")
        return []

def select_unseen_anime(theme_key, count=4):
    """
    Selects N unseen anime for the compilation to ensure it is NEVER the same.
    Falls back to least recently used if all candidates have been posted.
    """
    theme = THEMES.get(theme_key, THEMES['must_watch'])
    seen = load_seen_compilation_animes()

    pool = list(theme.get('candidates', []))

    # If dynamic search supported, query Shikimori
    if theme.get('shiki_genre') or theme.get('shiki_order'):
        dyn = fetch_shikimori_candidates(theme.get('shiki_genre'), theme.get('shiki_order'), limit=20)
        existing_ids = set(c['id'] for c in pool)
        for d in dyn:
            if d['id'] not in existing_ids:
                pool.append(d)

    unseen = [c for c in pool if str(c['id']) not in seen]

    # If not enough unseen, reset seen for this pool
    if len(unseen) < count:
        print("[Compilations] Пул тайтлов исчерпан, ротация начинается заново.")
        unseen = pool

    selected = unseen[:count]
    return selected

def build_compilation_content(theme_key, count=4):
    theme = THEMES.get(theme_key, THEMES['must_watch'])
    config = load_config()
    app_name = config.get('app', {}).get('name', 'AnimeVist')

    items = select_unseen_anime(theme_key, count=count)
    if not items:
        return None, None, None

    lines = [
        f"🌟 <b>ТОП-{len(items)}: {theme['title']}</b>\n",
        f"<i>{theme['desc']}</i>\n"
    ]

    emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣']
    poster_urls = []
    for idx, it in enumerate(items):
        em = emojis[idx] if idx < len(emojis) else f"{idx+1}."
        lines.append(f"{em} <b>«{it['ru']}»</b> / <i>{it['en']}</i>")
        lines.append(f"⭐️ <b>{it['score']}</b> | 🎭 {it['genres']}")
        lines.append(f"📝 {it['hook']}\n")
        poster_urls.append(it['poster'])

    lines.append(f"✨ <i>Смотрите эти тайтлы в высоком качестве в приложении {app_name}!</i>\n")
    lines.append(f"#подборка #топ_аниме {theme['tags']} #чтопосмотреть #{app_name.lower()}")

    caption = "\n".join(lines)

    # Optional chat button
    reply_markup = None
    show_chat = config.get('announcer', {}).get('show_chat_button', False)
    chat_url = config.get('app', {}).get('chat_invite_url', '').strip()
    if show_chat and chat_url and chat_url.startswith('http'):
        reply_markup = {
            "inline_keyboard": [
                [{"text": "💬 Обсудить подборку в чате", "url": chat_url}]
            ]
        }

    return caption, poster_urls, reply_markup, items

def run_compilation_post(genre_key=None, count=4, dry_run=False):
    sender = TelegramSender()
    
    # Auto-pick next theme if not specified
    if not genre_key or genre_key == 'auto' or genre_key not in THEMES:
        keys = list(THEMES.keys())
        last_t = load_last_compilation_time()
        idx = int(time.time() / 3600) % len(keys)
        genre_key = keys[idx]

    theme = THEMES[genre_key]
    caption, poster_urls, reply_markup, chosen_items = build_compilation_content(genre_key, count=count)

    if not chosen_items:
        print("[Compilations] Ошибка формирования подборки (нет тайтлов).")
        return {"ok": False, "error": "No titles available"}

    # Generate combined collage poster
    clean_title = theme['title'].replace('🌟', '').replace('🏆', '').replace('🧠', '').replace('⚔️', '').replace('💖', '').replace('😂', '').replace('🌀', '').replace('💎', '').replace('🌆', '').strip()
    collage_path = create_compilation_collage(poster_urls, f"ТОП-{len(chosen_items)}: {clean_title}")

    poster_to_send = collage_path if (collage_path and os.path.exists(collage_path)) else poster_urls[0]

    if dry_run:
        print("\n[DRY-RUN] Preview Compilation:")
        print(caption)
        print(f"Collage Image: {poster_to_send}")
        print(f"Included {len(chosen_items)} anime: {[c['ru'] for c in chosen_items]}")
        return {"ok": True, "theme": genre_key, "count": len(chosen_items), "dry_run": True}

    res = sender.send_photo(poster_to_send, caption=caption, reply_markup=reply_markup)
    if res.get('ok'):
        print(f"[Compilations] ✅ Успешно опубликована подборка: {theme['name']} ({len(chosen_items)} аниме)")
        # Save seen anime IDs to prevent repetition
        seen = load_seen_compilation_animes()
        for it in chosen_items:
            seen.add(str(it['id']))
        save_seen_compilation_animes(seen)
        save_last_compilation_time()
        return {"ok": True, "theme": genre_key, "count": len(chosen_items), "message": f"Опубликовано: {theme['name']}"}
    else:
        err = res.get('description', 'Unknown error')
        print(f"[Compilations] ❌ Ошибка публикации: {err}")
        return {"ok": False, "theme": genre_key, "error": err}

def list_available_themes():
    return [{"key": k, "name": v["name"]} for k, v in THEMES.items()]

def should_run_auto_compilation():
    config = load_config()
    ann = config.get('announcer', {})
    if not ann.get('enable_compilations', True):
        return False
    hours = float(ann.get('compilations_interval_hours', 12))
    last = load_last_compilation_time()
    return (time.time() - last) >= (hours * 3600)

if __name__ == '__main__':
    if '--auto-if-due' in sys.argv:
        if not should_run_auto_compilation():
            print("[Compilations] Интервал между подборками ещё не истёк. Пропуск.")
            sys.exit(0)

    genre = None
    count = 4
    dry = '--dry-run' in sys.argv
    for arg in sys.argv:
        if arg.startswith('--genre='):
            genre = arg.split('=', 1)[1]
        elif arg.startswith('--count='):
            try:
                count = int(arg.split('=', 1)[1])
            except ValueError:
                pass
        elif arg in THEMES:
            genre = arg
    run_compilation_post(genre_key=genre, count=count, dry_run=dry)
