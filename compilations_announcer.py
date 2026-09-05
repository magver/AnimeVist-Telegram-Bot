"""
AnimeVist Curated Anime Compilations Announcer.
Generates and publishes themed Top 3-5 anime collections with ratings,
rich synopses, cover posters, and navigation hashtags (#подборка).
Supports automated periodic rotation and instant manual dispatch.
"""

import os
import sys
import json
import time
import urllib.request
import urllib.parse

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

SEEN_COMPILATIONS_FILE = os.path.join(os.path.dirname(__file__), 'seen_compilations.json')

THEMES = {
    "cyberpunk": {
        "key": "cyberpunk",
        "name": "Киберпанк & Фантастика",
        "title": "ТОП-4: Культовый Киберпанк и Фантастика 🌆",
        "desc": "Мрачное будущее, передовые технологии и неоновые мегаполисы:",
        "tags": "#киберпанк #фантастика",
        "default_poster": "https://shikimori.one/system/animes/original/42310.jpg",
        "items": [
            {"id": 42310, "ru": "Киберпанк: Бегущие по краю", "en": "Cyberpunk: Edgerunners", "score": "8.62", "genres": "Экшен, Фантастика", "hook": "Парень из трущоб теряет всё и становится наемником в безжалостном Найт-Сити."},
            {"id": 13601, "ru": "Психопаспорт", "en": "Psycho-Pass", "score": "8.34", "genres": "Детектив, Триллер", "hook": "Система «Сивилла» вычисляет вероятность преступления еще до его совершения."},
            {"id": 43, "ru": "Призрак в доспехах", "en": "Ghost in the Shell", "score": "8.28", "genres": "Экшен, Меха", "hook": "Майор Мотоко Кусанаги расследует киберпреступления на грани человечности."},
            {"id": 1279, "ru": "Эрго Прокси", "en": "Ergo Proxy", "score": "7.91", "genres": "Детектив, Психология", "hook": "Загадки постапокалиптического купольного города, где андроиды обретают душу."}
        ]
    },
    "psychological": {
        "key": "psychological",
        "name": "Психологические Триллеры",
        "title": "ТОП-4: Психологические Триллеры и Детективы 🧠",
        "desc": "Напряженные сюжеты, игры разума и неожиданные сюжетные твисты:",
        "tags": "#триллер #психология #детектив",
        "default_poster": "https://shikimori.one/system/animes/original/1535.jpg",
        "items": [
            {"id": 1535, "ru": "Тетрадь смерти", "en": "Death Note", "score": "8.62", "genres": "Мистика, Детектив", "hook": "Интеллектуальная дуэль школьника с тетрадью бога смерти и гениального сыщика L."},
            {"id": 19, "ru": "Монстр", "en": "Monster", "score": "8.87", "genres": "Драма, Триллер", "hook": "Гениальный хирург спасает жизнь мальчику, не подозревая, что взрастил монстра."},
            {"id": 9253, "ru": "Врата Штейна", "en": "Steins;Gate", "score": "9.07", "genres": "Фантастика, Триллер", "hook": "Случайное изобретение машины времени в микроволновке втягивает друзей в заговор."},
            {"id": 13125, "ru": "Из нового света", "en": "Shinsekai yori", "score": "8.27", "genres": "Драма, Фантастика", "hook": "Идеальное утопическое общество телекинетиков скрывает леденящую тайну."}
        ]
    },
    "fantasy": {
        "key": "fantasy",
        "name": "Эпическое Фэнтези 8.5+",
        "title": "ТОП-4: Шедевры Фэнтези с Оценкой 8.5+ ⚔️",
        "desc": "Грандиозные миры, магия и незабываемые приключения:",
        "tags": "#фэнтези #приключения #эпик",
        "default_poster": "https://shikimori.one/system/animes/original/52991.jpg",
        "items": [
            {"id": 52991, "ru": "Провожающая в последний путь Фрирен", "en": "Sousou no Frieren", "score": "9.25", "genres": "Фэнтези, Драма", "hook": "Бессмертная эльфийка отправляется в путь, чтобы понять мимолетность человеческой жизни."},
            {"id": 5114, "ru": "Стальной алхимик: Братство", "en": "Fullmetal Alchemist: Brotherhood", "score": "9.11", "genres": "Сёнэн, Фэнтези", "hook": "Братья Элрики ищут философский камень, чтобы вернуть утраченные тела."},
            {"id": 11061, "ru": "Охотник х Охотник (2011)", "en": "Hunter x Hunter", "score": "9.04", "genres": "Экшен, Приключения", "hook": "Гон Фрикс отправляется на смертельно опасный экзамен Охотников в поисках отца."},
            {"id": 457, "ru": "Магическая битва / Клеймор", "en": "Claymore", "score": "7.80", "genres": "Тёмное фэнтези, Экшен", "hook": "Воительницы-полудемоны с серебряными глазами очищают континент от чудовищ."}
        ]
    },
    "romance": {
        "key": "romance",
        "name": "Романтика & Повседневность",
        "title": "ТОП-4: Романтика, от которой Теплеет на Душе 💖",
        "desc": "Искренние чувства, неловкие признания и ламповая атмосфера:",
        "tags": "#романтика #повседневность #комедия",
        "default_poster": "https://shikimori.one/system/animes/original/37999.jpg",
        "items": [
            {"id": 37999, "ru": "Госпожа Кагуя: В любви как на войне", "en": "Kaguya-sama wa Kokurasetai", "score": "8.89", "genres": "Комедия, Романтика", "hook": "Два гениальных президента студсовета ведут войну умов за первое признание в любви."},
            {"id": 42897, "ru": "Хоримия", "en": "Horimiya", "score": "8.19", "genres": "Школа, Романтика", "hook": "Два совершенно разных старшеклассника открывают друг другу свои тайные стороны."},
            {"id": 14813, "ru": "Как и ожидалось, моя школьная жизнь не задалась", "en": "Oregairu", "score": "8.24", "genres": "Драма, Романтика", "hook": "Циничный школьник Хатиман против своей воли помогает чужим социальным проблемам."},
            {"id": 4181, "ru": "Кланнад: Продолжение истории", "en": "Clannad: After Story", "score": "8.93", "genres": "Драма, Романтика", "hook": "Трогательная до слез история взросления, семьи и настоящей безусловной любви."}
        ]
    },
    "dark_fantasy": {
        "key": "dark_fantasy",
        "name": "Тёмное Фэнтези & Экшен",
        "title": "ТОП-4: Бескомпромиссное Тёмное Фэнтези и Экшен 🗡",
        "desc": "Суровые законы выживания, жестокие схватки и неоднозначные герои:",
        "tags": "#тёмное_фэнтези #экшен #драма",
        "default_poster": "https://shikimori.one/system/animes/original/37521.jpg",
        "items": [
            {"id": 37521, "ru": "Сага о Винланде", "en": "Vinland Saga", "score": "8.75", "genres": "Экшен, Приключения", "hook": "Юный Торфинн жаждет мести за отца в кровавую эпоху завоеваний викингов."},
            {"id": 33, "ru": "Берсерк (1997)", "en": "Berserk", "score": "8.57", "genres": "Тёмное фэнтези, Военное", "hook": "Одинокий наемник Гатс встречает Гриффита и вступает в Отряд Сокола."},
            {"id": 16498, "ru": "Атака титанов", "en": "Attack on Titan", "score": "8.55", "genres": "Экшен, Детектив", "hook": "Остатки человечества ведут отчаянную войну с гигантскими людоедами за стенами."},
            {"id": 40748, "ru": "Магическая битва", "en": "Jujutsu Kaisen", "score": "8.59", "genres": "Сверхъестественное, Экшен", "hook": "Юдзи Итадори проглатывает проклятый палец древнего демона ради спасения друзей."}
        ]
    },
    "isekai": {
        "key": "isekai",
        "name": "Лучшие Исекаи & Попаданцы",
        "title": "ТОП-4: Захватывающие Исекаи с Оригинальным Сюжетом 🌀",
        "desc": "Попаданцы в другие миры, где всё пошло не по стандартному сценарию:",
        "tags": "#исекай #фэнтези #приключения",
        "default_poster": "https://shikimori.one/system/animes/original/39535.jpg",
        "items": [
            {"id": 39535, "ru": "Реинкарнация безработного", "en": "Mushoku Tensei", "score": "8.65", "genres": "Магия, Приключения", "hook": "34-летний затворник получает второй шанс прожить достойную жизнь в мире меча и магии."},
            {"id": 31240, "ru": "Re:Zero — жизнь с нуля в другом мире", "en": "Re:Zero", "score": "8.23", "genres": "Триллер, Драма", "hook": "Субару Нацуки обретает способность возвращаться во времени только после своей гибели."},
            {"id": 30831, "ru": "Этот замечательный мир! (KonoSuba)", "en": "KonoSuba", "score": "8.10", "genres": "Комедия, Пародия", "hook": "Хикикомори Казума берет с собой бесполезную богиню Акву и собирает чудаковатую пати."},
            {"id": 37430, "ru": "О моём перерождении в слизь", "en": "Tensei shitara Slime Datta Ken", "score": "8.12", "genres": "Фэнтези, Сёнэн", "hook": "Офисный клерк перерождается монстром-слизью и строит процветающую федерацию монстров."}
        ]
    },
    "classics": {
        "key": "classics",
        "name": "Золотая Классика Аниме",
        "title": "ТОП-4: Золотая Классика, которую Обязан Посмотреть Каждый 🏆",
        "desc": "Легендарные тайтлы, навсегда изменившие мировую анимацию:",
        "tags": "#классика #шедевр #топ_аниме",
        "default_poster": "https://shikimori.one/system/animes/original/1.jpg",
        "items": [
            {"id": 1, "ru": "Ковбой Бибоп", "en": "Cowboy Bebop", "score": "8.75", "genres": "Фантастика, Вестерн", "hook": "Охотники за головами бороздят Солнечную систему под звуки бессмертного джаза."},
            {"id": 30, "ru": "Евангелион", "en": "Neon Genesis Evangelion", "score": "8.36", "genres": "Меха, Психология", "hook": "Подростки пилотируют биороботов против таинственных Ангелов посреди душевных кризисов."},
            {"id": 2001, "ru": "Гуррен-Лаганн", "en": "Tengen Toppa Gurren Lagann", "score": "8.63", "genres": "Экшен, Меха", "hook": "Симон и Камина бурят путь наверх сквозь пространство, бросая вызов самой Вселенной."},
            {"id": 245, "ru": "Крутой учитель Онидзука", "en": "Great Teacher Onizuka", "score": "8.70", "genres": "Комедия, Школа", "hook": "Бывший байкер становится учителем самого проблемного класса школы."}
        ]
    },
    "comedy": {
        "key": "comedy",
        "name": "Комедии & Позитив",
        "title": "ТОП-4: Безумные Комедии для Отличного Настроения 😂",
        "desc": "Море отборного юмора, ярких персонажей и гарантированный заряд смеха:",
        "tags": "#комедия #пародия #позитив",
        "default_poster": "https://shikimori.one/system/animes/original/918.jpg",
        "items": [
            {"id": 918, "ru": "Гинтама", "en": "Gintama", "score": "8.93", "genres": "Пародия, Экшен", "hook": "Самураи, инопланетяне-аманто и мастер абсурдного юмора Гинтоки Саката."},
            {"id": 33255, "ru": "Необъятный океан", "en": "Grand Blue", "score": "8.44", "genres": "Комедия, Студенты", "hook": "Студенческая жизнь дайвинг-клуба, полная вечеринок, абсурда и крепкой дружбы."},
            {"id": 32281, "ru": "Несладкая жизнь псионика Сайки К.", "en": "Saiki Kusuo no Psi-nan", "score": "8.41", "genres": "Комедия, Сверхъестественное", "hook": "Могущественный экстрасенс хочет обычной тихой жизни, но чудаки вокруг не дают покоя."},
            {"id": 34572, "ru": "Чёрный клевер / Моб Психо 100", "en": "Mob Psycho 100", "score": "8.48", "genres": "Экшен, Комедия", "hook": "Скромный школьник с чудовищной психической силой пытается жить простой жизнью."}
        ]
    }
}

def load_seen_compilations():
    seen = []
    if os.path.exists(SEEN_COMPILATIONS_FILE):
        try:
            with open(SEEN_COMPILATIONS_FILE, 'r', encoding='utf-8') as f:
                seen = json.load(f)
        except Exception:
            pass
    try:
        remote_seen = load_seen_from_supabase(category='compilation')
        for r in remote_seen:
            if r not in seen:
                seen.append(r)
    except Exception:
        pass
    return seen

def save_seen_compilations(seen_list):
    try:
        with open(SEEN_COMPILATIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(seen_list[-50:], f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    try:
        save_seen_to_supabase(set(seen_list), category='compilation')
    except Exception:
        pass

def get_next_theme_key(requested_key=None):
    if requested_key and requested_key in THEMES:
        return requested_key
    seen = load_seen_compilations()
    all_keys = list(THEMES.keys())
    for k in all_keys:
        if k not in seen:
            return k
    # If all seen, cycle back
    if seen:
        last = seen[-1]
        if last in all_keys:
            idx = (all_keys.index(last) + 1) % len(all_keys)
            return all_keys[idx]
    return all_keys[0]

def build_compilation_post(theme_key):
    theme = THEMES.get(theme_key, THEMES['cyberpunk'])
    config = load_config()
    app_name = config.get('app', {}).get('name', 'AnimeVist')

    lines = [
        f"🌟 <b>{theme['title']}</b>\n",
        f"<i>{theme['desc']}</i>\n"
    ]

    emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣']
    for i, it in enumerate(theme['items']):
        em = emojis[i] if i < len(emojis) else f"{i+1}."
        lines.append(f"{em} <b>«{it['ru']}»</b> / <i>{it['en']}</i>")
        lines.append(f"⭐️ <b>{it['score']}</b> | 🎭 {it['genres']}")
        lines.append(f"📝 {it['hook']}\n")

    lines.append(f"✨ <i>Смотрите эти тайтлы в высоком качестве в приложении {app_name}!</i>\n")
    lines.append(f"#подборка #топ_аниме {theme['tags']} #чтопосмотреть #{app_name.lower()}")

    caption = "\n".join(lines)
    poster = theme.get('default_poster')

    reply_markup = None
    show_chat = config.get('announcer', {}).get('show_chat_button', False)
    chat_url = config.get('app', {}).get('chat_invite_url', '').strip()
    if show_chat and chat_url and chat_url.startswith('http'):
        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "💬 Обсудить подборку в чате", "url": chat_url}
                ]
            ]
        }

    return caption, poster, reply_markup

def run_compilation_post(genre_key=None, dry_run=False):
    sender = TelegramSender()
    theme_key = get_next_theme_key(genre_key)
    theme = THEMES[theme_key]

    print(f"[Compilations] Формирование подборки: {theme['name']} ({theme_key})")
    caption, poster, reply_markup = build_compilation_post(theme_key)

    if dry_run:
        print("[DRY-RUN] Preview Compilation:")
        print(caption)
        print("Poster:", poster)
        print("Reply markup:", reply_markup)
        return {"ok": True, "theme": theme_key, "dry_run": True}

    res = sender.send_photo(poster, caption=caption, reply_markup=reply_markup)
    if res.get('ok'):
        print(f"[Compilations] ✅ Успешно опубликована подборка: {theme['name']}")
        seen = load_seen_compilations()
        seen.append(theme_key)
        save_seen_compilations(seen)
        return {"ok": True, "theme": theme_key, "message": f"Опубликовано: {theme['name']}"}
    else:
        err = res.get('description', 'Unknown error')
        print(f"[Compilations] ❌ Ошибка публикации: {err}")
        return {"ok": False, "theme": theme_key, "error": err}

def list_available_themes():
    return [{"key": k, "name": v["name"]} for k, v in THEMES.items()]

if __name__ == '__main__':
    genre = None
    dry = '--dry-run' in sys.argv
    for arg in sys.argv:
        if arg.startswith('--genre='):
            genre = arg.split('=', 1)[1]
        elif arg in THEMES:
            genre = arg
    run_compilation_post(genre_key=genre, dry_run=dry)
