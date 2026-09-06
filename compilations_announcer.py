"""
AnimeVist Dynamic & Curated Anime Compilations Engine.
Generates themed Top 3-10 anime collections (Must-Watch, Hidden Gems, Mindfuck, Sci-Fi, etc.),
combines all posters into a single high-resolution collage banner using Pillow,
prevents repeats by tracking seen anime IDs, and posts rich cards with hashtags (#подборка).
"""

import os
import sys
import io
import json
import time
import random
import urllib.request
import re
from PIL import Image, ImageDraw, ImageFont, ImageFilter

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

# Curated Thematic Presets with 12-14 hand-picked masterpieces per theme (>110 total)
THEMES = {
    "must_watch": {
        "key": "must_watch",
        "name": "🏆 Золотая классика и шедевры (8.5+)",
        "title": "Обязательно к просмотру (Золотой фонд аниме) 🏆",
        "desc": "Культовые тайтлы с высочайшим мировым рейтингом, навсегда вошедшие в историю:",
        "tags": "#шедевры #must_watch #топ_аниме",
        "shiki_genre": None,
        "shiki_order": "ranked",
        "candidates": [
            {"id": 52991, "ru": "Провожающая в последний путь Фрирен", "en": "Sousou no Frieren", "score": "9.25", "genres": "Фэнтези, Драма", "poster": "https://shikimori.one/system/animes/original/52991.jpg", "hook": "Бессмертная эльфийка отправляется в путь, чтобы постичь ценность человеческой жизни."},
            {"id": 5114, "ru": "Стальной алхимик: Братство", "en": "Fullmetal Alchemist: Brotherhood", "score": "9.11", "genres": "Сёнэн, Фэнтези", "poster": "https://shikimori.one/system/animes/original/5114.jpg", "hook": "Братья Элрики ищут философский камень, чтобы вернуть утраченные тела."},
            {"id": 9253, "ru": "Врата Штейна", "en": "Steins;Gate", "score": "9.07", "genres": "Фантастика, Триллер", "poster": "https://shikimori.one/system/animes/original/9253.jpg", "hook": "Случайное создание машины времени втягивает друзей в опаснейший заговор."},
            {"id": 11061, "ru": "Охотник х Охотник (2011)", "en": "Hunter x Hunter", "score": "9.04", "genres": "Экшен, Приключения", "poster": "https://shikimori.one/system/animes/original/11061.jpg", "hook": "Гон отправляется на смертельный экзамен Охотников ради поисков отца."},
            {"id": 19, "ru": "Монстр", "en": "Monster", "score": "8.87", "genres": "Драма, Триллер", "poster": "https://shikimori.one/system/animes/original/19.jpg", "hook": "Гениальный хирург спасает жизнь мальчику, не зная, что взрастил зло."},
            {"id": 1, "ru": "Ковбой Бибоп", "en": "Cowboy Bebop", "score": "8.75", "genres": "Фантастика, Экшен", "poster": "https://shikimori.one/system/animes/original/1.jpg", "hook": "Охотники за головами бороздят Солнечную систему под звуки джаза."},
            {"id": 2001, "ru": "Гуррен-Лаганн", "en": "Tengen Toppa Gurren Lagann", "score": "8.63", "genres": "Экшен, Меха", "poster": "https://shikimori.one/system/animes/original/2001.jpg", "hook": "Симон и Камина бурят путь наверх сквозь пространство, бросая вызов Вселенной."},
            {"id": 1575, "ru": "Код Гиас: Восставший Лелуш", "en": "Code Geass", "score": "8.70", "genres": "Экшен, Меха", "poster": "https://shikimori.one/system/animes/original/1575.jpg", "hook": "Отвергнутый принц получает силу абсолютного подчинения и начинает восстание."},
            {"id": 1535, "ru": "Тетрадь смерти", "en": "Death Note", "score": "8.62", "genres": "Мистика, Детектив", "poster": "https://shikimori.one/system/animes/original/1535.jpg", "hook": "Интеллектуальная дуэль школьника с тетрадью бога смерти и гениального сыщика L."},
            {"id": 245, "ru": "Крутой учитель Онидзука", "en": "Great Teacher Onizuka", "score": "8.69", "genres": "Комедия, Школа", "poster": "https://shikimori.one/system/animes/original/245.jpg", "hook": "Бывший байкер берется перевоспитывать самый проблемный класс школы."},
            {"id": 164, "ru": "Самурай Чамплу", "en": "Samurai Champloo", "score": "8.51", "genres": "Экшен, Приключения", "poster": "https://shikimori.one/system/animes/original/164.jpg", "hook": "Два непревзойденных мечника сопровождают девушку в поисках самурая."},
            {"id": 30, "ru": "Евангелион", "en": "Neon Genesis Evangelion", "score": "8.35", "genres": "Меха, Психология", "poster": "https://shikimori.one/system/animes/original/30.jpg", "hook": "Подростки пилотируют биороботов, защищая мир от таинственных Ангелов."},
            {"id": 199, "ru": "Унесённые призраками", "en": "Sen to Chihiro", "score": "8.78", "genres": "Сказка, Мистика", "poster": "https://shikimori.one/system/animes/original/199.jpg", "hook": "Десятилетняя Тихиро попадает в таинственный мир духов и ведьмы Юбабы."},
            {"id": 16498, "ru": "Атака титанов", "en": "Shingeki no Kyojin", "score": "8.54", "genres": "Экшен, Драма", "poster": "https://shikimori.one/system/animes/original/16498.jpg", "hook": "Остатки человечества сражаются за выживание с гигантами-людоедами."}
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
            {"id": 13125, "ru": "Из нового света", "en": "Shinsekai yori", "score": "8.27", "genres": "Драма, Фантастика", "poster": "https://shikimori.one/system/animes/original/13125.jpg", "hook": "Утопическое общество телекинетиков скрывает леденящую кровь тайну."},
            {"id": 22135, "ru": "Пинг-понг", "en": "Ping Pong the Animation", "score": "8.60", "genres": "Спорт, Драма", "poster": "https://shikimori.one/system/animes/original/22135.jpg", "hook": "Шедевр Масааки Юасы о дружбе, призвании и взрослении через спорт."},
            {"id": 1279, "ru": "Эрго Прокси", "en": "Ergo Proxy", "score": "7.91", "genres": "Детектив, Психология", "poster": "https://shikimori.one/system/animes/original/1279.jpg", "hook": "Загадки города-купола Ромдо, где андроиды внезапно обретают душу."},
            {"id": 486, "ru": "Путешествие Кино", "en": "Kino no Tabi", "score": "8.38", "genres": "Приключения, Философия", "poster": "https://shikimori.one/system/animes/original/486.jpg", "hook": "Путешественница Кино и говорящий мотоцикл исследуют обычаи стран мира."},
            {"id": 2251, "ru": "Баккано!", "en": "Baccano!", "score": "8.38", "genres": "Экшен, Комедия", "poster": "https://shikimori.one/system/animes/original/2251.jpg", "hook": "Вихрь мафиози, алхимиков и бессмертных на трансконтинентальном поезде."},
            {"id": 45, "ru": "Мононокэ", "en": "Mononoke", "score": "8.42", "genres": "Мистика, Детектив", "poster": "https://shikimori.one/system/animes/original/45.jpg", "hook": "Безымянный Аптекарь изгоняет духов, раскрывая их Форму, Суть и Первопричину."},
            {"id": 387, "ru": "Альянс Серокрылых", "en": "Haibane Renmei", "score": "7.99", "genres": "Драма, Мистика", "poster": "https://shikimori.one/system/animes/original/387.jpg", "hook": "Девушка с пепельными крыльями ищет свое предназначение в городе за Стеной."},
            {"id": 6594, "ru": "Радуга: Семеро из шестой камеры", "en": "Rainbow", "score": "8.46", "genres": "Драма, Триллер", "poster": "https://shikimori.one/system/animes/original/6594.jpg", "hook": "Семеро юношей в колонии строгого режима находят братство посреди жестокости."},
            {"id": 457, "ru": "Клеймор", "en": "Claymore", "score": "7.80", "genres": "Тёмное фэнтези, Экшен", "poster": "https://shikimori.one/system/animes/original/457.jpg", "hook": "Воительницы с серебряными глазами очищают континент от чудовищ-йома."},
            {"id": 26, "ru": "Технолайз", "en": "Texhnolyze", "score": "7.76", "genres": "Киберпанк, Драма", "poster": "https://shikimori.one/system/animes/original/26.jpg", "hook": "Бескомпромиссная антиутопия подземного города Люкс на грани угасания."},
            {"id": 37520, "ru": "Дороро", "en": "Dororo", "score": "8.24", "genres": "Исторический, Экшен", "poster": "https://shikimori.one/system/animes/original/37520.jpg", "hook": "Хяккимару возвращает украденные демонами органы, истребляя нечисть."},
            {"id": 22043, "ru": "Парад смерти", "en": "Death Parade", "score": "8.16", "genres": "Психология, Драма", "poster": "https://shikimori.one/system/animes/original/22043.jpg", "hook": "Таинственный бар, где души умерших обнажают истинную натуру в играх."},
            {"id": 31043, "ru": "Город, в котором меня нет", "en": "Boku dake ga Inai Machi", "score": "8.31", "genres": "Детектив, Триллер", "poster": "https://shikimori.one/system/animes/original/31043.jpg", "hook": "Мангака возвращается в детство, чтобы предотвратить гибель девочки."},
            {"id": 10620, "ru": "Рассвет Йоны", "en": "Akatsuki no Yona", "score": "8.02", "genres": "Приключения, Фэнтези", "poster": "https://shikimori.one/system/animes/original/10620.jpg", "hook": "Изгнанная принцесса собирает легендарных воинов-драконов ради царства."}
        ]
    },
    "mindfuck": {
        "key": "mindfuck",
        "name": "🧠 Игры разума & Психологические триллеры",
        "title": "ТОП: Психологические Триллеры и Игры Разума 🧠",
        "desc": "Напряженные сюжеты, невероятные многоходовки и неожиданные сюжетные твисты:",
        "tags": "#триллер #психология #детектив #сюжет",
        "shiki_genre": "40,7",
        "shiki_order": "ranked",
        "candidates": [
            {"id": 1535, "ru": "Тетрадь смерти", "en": "Death Note", "score": "8.62", "genres": "Мистика, Детектив", "poster": "https://shikimori.one/system/animes/original/1535.jpg", "hook": "Интеллектуальная дуэль школьника с тетрадью смерти и гениального сыщика L."},
            {"id": 19, "ru": "Монстр", "en": "Monster", "score": "8.87", "genres": "Драма, Триллер", "poster": "https://shikimori.one/system/animes/original/19.jpg", "hook": "Хирург спасает жизнь мальчику, не подозревая, что взрастил абсолютное зло."},
            {"id": 13601, "ru": "Психопаспорт", "en": "Psycho-Pass", "score": "8.34", "genres": "Детектив, Триллер", "poster": "https://shikimori.one/system/animes/original/13601.jpg", "hook": "Система «Сивилла» вычисляет вероятность преступления еще до его совершения."},
            {"id": 22535, "ru": "Паразит: Учение о жизни", "en": "Kiseijuu", "score": "8.34", "genres": "Экшен, Ужасы", "poster": "https://shikimori.one/system/animes/original/22535.jpg", "hook": "Инопланетный паразит в руке школьника втягивает его в войну за выживание."},
            {"id": 37, "ru": "Идеальная грусть", "en": "Perfect Blue", "score": "8.53", "genres": "Психология, Триллер", "poster": "https://shikimori.one/system/animes/original/37.jpg", "hook": "Бывшая поп-идол теряет грань между реальностью и безумием из-за сталкера."},
            {"id": 35849, "ru": "Обещанный Неверленд", "en": "Yakusoku no Neverland", "score": "8.51", "genres": "Мистика, Триллер", "poster": "https://shikimori.one/system/animes/original/35849.jpg", "hook": "Дети в идиллическом приюте узнают, что их растят на убой для монстров."},
            {"id": 20707, "ru": "Токийский гуль", "en": "Tokyo Ghoul", "score": "7.79", "genres": "Ужасы, Драма", "poster": "https://shikimori.one/system/animes/original/20707.jpg", "hook": "Студент становится полугулем и балансирует между миром людей и чудовищ."},
            {"id": 11111, "ru": "Иная", "en": "Another", "score": "7.46", "genres": "Мистика, Ужасы", "poster": "https://shikimori.one/system/animes/original/11111.jpg", "hook": "В классе 3-3 оживает проклятие, и ученики начинают погибать один за другим."},
            {"id": 40052, "ru": "Игра друзей", "en": "Tomodachi Game", "score": "7.69", "genres": "Психология, Игры", "poster": "https://shikimori.one/system/animes/original/40052.jpg", "hook": "Пятеро друзей попадают в жестокую психологическую игру ради выплаты долга."},
            {"id": 24405, "ru": "Шарлотта", "en": "Charlotte", "score": "7.74", "genres": "Драма, Сверхъестественное", "poster": "https://shikimori.one/system/animes/original/24405.jpg", "hook": "Подростки со скрытыми способностями сталкиваются с суровой ценой своих сил."},
            {"id": 14813, "ru": "Как и ожидалось, моя школьная жизнь не задалась", "en": "Oregairu", "score": "8.24", "genres": "Драма, Психология", "poster": "https://shikimori.one/system/animes/original/14813.jpg", "hook": "Циничный школьник Хатиман препарирует социальные маски сверстников."},
            {"id": 28223, "ru": "Рыцари Сидонии", "en": "Knights of Sidonia", "score": "7.65", "genres": "Фантастика, Меха", "poster": "https://shikimori.one/system/animes/original/28223.jpg", "hook": "Остатки человечества в космосе ведут отчаянную борьбу против пришельцев-гауна."}
        ]
    },
    "cyberpunk_scifi": {
        "key": "cyberpunk_scifi",
        "name": "🌆 Киберпанк & Научная фантастика",
        "title": "ТОП: Культовый Киберпанк и Научная Фантастика 🌆",
        "desc": "Мрачное будущее, аугментации, искусственный интеллект и неоновые мегаполисы:",
        "tags": "#киберпанк #фантастика #scifi",
        "shiki_genre": "24,18",
        "shiki_order": "ranked",
        "candidates": [
            {"id": 42310, "ru": "Киберпанк: Бегущие по краю", "en": "Cyberpunk: Edgerunners", "score": "8.62", "genres": "Экшен, Фантастика", "poster": "https://shikimori.one/system/animes/original/42310.jpg", "hook": "Парень из трущоб становится наемником-соло в безжалостном Найт-Сити."},
            {"id": 43, "ru": "Призрак в доспехах", "en": "Ghost in the Shell", "score": "8.28", "genres": "Экшен, Меха", "poster": "https://shikimori.one/system/animes/original/43.jpg", "hook": "Майор Мотоко Кусанаги расследует киберпреступления на грани человечности."},
            {"id": 47, "ru": "Акира", "en": "Akira", "score": "8.15", "genres": "Фантастика, Экшен", "poster": "https://shikimori.one/system/animes/original/47.jpg", "hook": "Байкер в разрушенном Нео-Токио пробуждает колоссальную разрушительную мощь."},
            {"id": 40571, "ru": "Виви: Песнь флюоритового глаза", "en": "Vivy", "score": "8.40", "genres": "Музыка, Фантастика", "poster": "https://shikimori.one/system/animes/original/40571.jpg", "hook": "Андроид-певица должна предотвратить восстание машин длиною в 100 лет."},
            {"id": 2005, "ru": "Триган", "en": "Trigun", "score": "8.21", "genres": "Экшен, Sci-Fi", "poster": "https://shikimori.one/system/animes/original/2005.jpg", "hook": "Пацифист Вэш Ураган скитается по пустынной планете, спасая людей."},
            {"id": 820, "ru": "Легенда о героях Галактики", "en": "Ginga Eiyuu Densetsu", "score": "9.02", "genres": "Космос, Военное", "poster": "https://shikimori.one/system/animes/original/820.jpg", "hook": "Грандиозное противостояние двух гениальных стратегов в масштабах космоса."},
            {"id": 513, "ru": "Изгнанник", "en": "Last Exile", "score": "7.82", "genres": "Стимпанк, Приключения", "poster": "https://shikimori.one/system/animes/original/513.jpg", "hook": "Юные пилоты ваншипа оказываются втянуты в воздушную войну двух империй."},
            {"id": 3167, "ru": "Время Евы", "en": "Eve no Jikan", "score": "7.98", "genres": "Повседневность, Sci-Fi", "poster": "https://shikimori.one/system/animes/original/3167.jpg", "hook": "В уютном кафе стирается социальная грань между людьми и андроидами."},
            {"id": 40748, "ru": "Акудама Драйв", "en": "Akudama Drive", "score": "7.58", "genres": "Экшен, Киберпанк", "poster": "https://shikimori.one/system/animes/original/40748.jpg", "hook": "Отряд отпетых преступников Кансая берется за самоубийственное ограбление."},
            {"id": 31964, "ru": "Измерение W", "en": "Dimension W", "score": "7.14", "genres": "Экшен, Sci-Fi", "poster": "https://shikimori.one/system/animes/original/31964.jpg", "hook": "Коллекционер нелегальных катушек исследует тайны четвертого измерения."},
            {"id": 2001, "ru": "Гуррен-Лаганн", "en": "Tengen Toppa Gurren Lagann", "score": "8.63", "genres": "Экшен, Меха", "poster": "https://shikimori.one/system/animes/original/2001.jpg", "hook": "Симон и Камина бурят путь наверх сквозь пространство, бросая вызов Вселенной."},
            {"id": 1, "ru": "Ковбой Бибоп", "en": "Cowboy Bebop", "score": "8.75", "genres": "Фантастика, Экшен", "poster": "https://shikimori.one/system/animes/original/1.jpg", "hook": "Охотники за головами бороздят Солнечную систему под звуки бессмертного джаза."}
        ]
    },
    "epic_fantasy": {
        "key": "epic_fantasy",
        "name": "⚔️ Эпическое фэнтези и приключения",
        "title": "ТОП: Грандиозное Фэнтези и Приключения ⚔️",
        "desc": "Магия, масштабные миры, эпические сражения и незабываемые путешествия:",
        "tags": "#фэнтези #приключения #эпик",
        "shiki_genre": "10,2",
        "shiki_order": "ranked",
        "candidates": [
            {"id": 37521, "ru": "Сага о Винланде", "en": "Vinland Saga", "score": "8.75", "genres": "Экшен, Приключения", "poster": "https://shikimori.one/system/animes/original/37521.jpg", "hook": "Юный Торфинн жаждет мести за отца посреди завоевательных походов викингов."},
            {"id": 33, "ru": "Берсерк (1997)", "en": "Berserk", "score": "8.57", "genres": "Тёмное фэнтези, Военное", "poster": "https://shikimori.one/system/animes/original/33.jpg", "hook": "Одинокий мечник Гатс встречает Гриффита и вступает в Отряд Сокола."},
            {"id": 34599, "ru": "Созданный в Бездне", "en": "Made in Abyss", "score": "8.66", "genres": "Приключения, Драма", "poster": "https://shikimori.one/system/animes/original/34599.jpg", "hook": "Девочка Рико и робот Рэг спускаются в смертоносные глубины великой Бездны."},
            {"id": 38000, "ru": "Клинок, рассекающий демонов", "en": "Kimetsu no Yaiba", "score": "8.47", "genres": "Экшен, Сверхъестественное", "poster": "https://shikimori.one/system/animes/original/38000.jpg", "hook": "Тандзиро становится истребителем демонов, чтобы исцелить обращенную сестру."},
            {"id": 20507, "ru": "Бездомный бог", "en": "Noragami", "score": "7.96", "genres": "Мистика, Комедия", "poster": "https://shikimori.one/system/animes/original/20507.jpg", "hook": "Бродячий бог Ято выполняет любые просьбы за монетку в 5 иен ради своего храма."},
            {"id": 18679, "ru": "Убей или умри", "en": "Kill la Kill", "score": "8.04", "genres": "Экшен, Комедия", "poster": "https://shikimori.one/system/animes/original/18679.jpg", "hook": "Рюко Матой с половиной ножниц ищет убийцу отца в элитной академии."},
            {"id": 14719, "ru": "Невероятные приключения ДжоДжо", "en": "JoJo no Kimyou na Bouken", "score": "8.11", "genres": "Экшен, Приключения", "poster": "https://shikimori.one/system/animes/original/14719.jpg", "hook": "Эпическая сага поколений семьи Джостаров в схватке с древним злом."},
            {"id": 52701, "ru": "Подземелье вкусностей", "en": "Dungeon Meshi", "score": "8.58", "genres": "Фэнтези, Гурман", "poster": "https://shikimori.one/system/animes/original/52701.jpg", "hook": "Отряд авантюристов спасает соратницу из брюха дракона, готовя монстров на обед."},
            {"id": 22319, "ru": "Токийский гуль: Перерождение", "en": "Tokyo Ghoul:re", "score": "7.63", "genres": "Экшен, Детектив", "poster": "https://shikimori.one/system/animes/original/22319.jpg", "hook": "Следователь Сасаки Хайсэ ведет отряд куинксов, пытаясь вспомнить свое прошлое."},
            {"id": 11061, "ru": "Охотник х Охотник", "en": "Hunter x Hunter", "score": "9.04", "genres": "Экшен, Приключения", "poster": "https://shikimori.one/system/animes/original/11061.jpg", "hook": "Гон и друзья преодолевают смертельные испытания невероятного мира Охотников."},
            {"id": 52991, "ru": "Провожающая в последний путь Фрирен", "en": "Sousou no Frieren", "score": "9.25", "genres": "Фэнтези, Драма", "poster": "https://shikimori.one/system/animes/original/52991.jpg", "hook": "Эльфийская волшебница познает тепло человеческих уз после победы над Владыкой."},
            {"id": 457, "ru": "Клеймор", "en": "Claymore", "score": "7.80", "genres": "Тёмное фэнтези, Экшен", "poster": "https://shikimori.one/system/animes/original/457.jpg", "hook": "Воительницы с серебряными глазами очищают континент от чудовищ-йома."}
        ]
    },
    "soul_romance": {
        "key": "soul_romance",
        "name": "💖 Ламповая романтика для души",
        "title": "ТОП: Трогательная Романтика для Теплого Вечера 💖",
        "desc": "Искренние чувства, неловкие признания, поддержка и уютная атмосфера:",
        "tags": "#романтика #повседневность #уют",
        "shiki_genre": "22",
        "shiki_order": "ranked",
        "candidates": [
            {"id": 37999, "ru": "Госпожа Кагуя: В любви как на войне", "en": "Kaguya-sama", "score": "8.89", "genres": "Комедия, Романтика", "poster": "https://shikimori.one/system/animes/original/37999.jpg", "hook": "Президенты элитного студсовета ведут войну умов за первое признание в чувствах."},
            {"id": 42897, "ru": "Хоримия", "en": "Horimiya", "score": "8.19", "genres": "Школа, Романтика", "poster": "https://shikimori.one/system/animes/original/42897.jpg", "hook": "Два разных старшеклассника открывают друг другу свои настоящие тайные стороны."},
            {"id": 4181, "ru": "Кланнад: Продолжение истории", "en": "Clannad: After Story", "score": "8.93", "genres": "Драма, Романтика", "poster": "https://shikimori.one/system/animes/original/4181.jpg", "hook": "Трогательная история взросления, семейных ценностей и настоящей вечной любви."},
            {"id": 28851, "ru": "Форма голоса", "en": "Koe no Katachi", "score": "8.93", "genres": "Драма, Школа", "poster": "https://shikimori.one/system/animes/original/28851.jpg", "hook": "Бывший задира ищет искупления перед глухой одноклассницей."},
            {"id": 30015, "ru": "Твоя апрельская ложь", "en": "Shigatsu wa Kimi no Uso", "score": "8.64", "genres": "Музыка, Драма", "poster": "https://shikimori.one/system/animes/original/30015.jpg", "hook": "Скрипачка-бунтарка возвращает юному пианисту страсть к музыке и жизни."},
            {"id": 4224, "ru": "Торадора!", "en": "Toradora!", "score": "8.08", "genres": "Комедия, Романтика", "poster": "https://shikimori.one/system/animes/original/4224.jpg", "hook": "Грозный с виду парень и миниатюрная Тигрица помогают друг другу в делах любви."},
            {"id": 30276, "ru": "Этот глупый свин не понимает мечту девочки-зайки", "en": "Seishun Buta Yarou", "score": "8.24", "genres": "Мистика, Романтика", "poster": "https://shikimori.one/system/animes/original/30276.jpg", "hook": "Сакута помогает актрисе в костюме зайки, которую перестают замечать окружающие."},
            {"id": 5081, "ru": "Дотянуться до тебя", "en": "Kimi ni Todoke", "score": "7.99", "genres": "Школа, Романтика", "poster": "https://shikimori.one/system/animes/original/5081.jpg", "hook": "Скромная девушка Савако учится общаться с миром благодаря доброму однокласснику."},
            {"id": 52588, "ru": "Опасность в моем сердце", "en": "Boku no Kokoro no Yabai Yatsu", "score": "8.78", "genres": "Комедия, Романтика", "poster": "https://shikimori.one/system/animes/original/52588.jpg", "hook": "Мрачный интроверт постепенно сближается с жизнерадостной школьной красавицей."},
            {"id": 37450, "ru": "Пять невест", "en": "Gotoubun no Hanayome", "score": "7.64", "genres": "Гарем, Романтика", "poster": "https://shikimori.one/system/animes/original/37450.jpg", "hook": "Бедный отличник нанимается репетитором к пяти непокорным сестрам-близняшкам."},
            {"id": 13759, "ru": "Кошечка из Сакурасо", "en": "Sakurasou no Pet na Kanojo", "score": "8.11", "genres": "Комедия, Драма", "poster": "https://shikimori.one/system/animes/original/13759.jpg", "hook": "Жизнь в общежитии одаренных чудаков учит мечтать и не сдаваться перед трудностями."},
            {"id": 14813, "ru": "Как и ожидалось, моя школьная жизнь не задалась", "en": "Oregairu", "score": "8.24", "genres": "Драма, Романтика", "poster": "https://shikimori.one/system/animes/original/14813.jpg", "hook": "Клуб служения помогает старшеклассникам разрешать их эмоциональные кризисы."}
        ]
    },
    "pure_comedy": {
        "key": "pure_comedy",
        "name": "😂 Отборные комедии & Позитив",
        "title": "ТОП: Безумные Комедии для Отличного Настроения 😂",
        "desc": "Море отборного юмора, ярких персонажей и гарантированный заряд позитива:",
        "tags": "#комедия #пародия #позитив",
        "shiki_genre": "4",
        "shiki_order": "ranked",
        "candidates": [
            {"id": 918, "ru": "Гинтама", "en": "Gintama", "score": "8.93", "genres": "Пародия, Экшен", "poster": "https://shikimori.one/system/animes/original/918.jpg", "hook": "Самураи, пришельцы и мастер абсурдного юмора Гинтоки Саката в феодальной Японии."},
            {"id": 33255, "ru": "Необъятный океан", "en": "Grand Blue", "score": "8.44", "genres": "Комедия, Студенты", "poster": "https://shikimori.one/system/animes/original/33255.jpg", "hook": "Безумная жизнь студенческого дайвинг-клуба, полная угарных вечеринок и дружбы."},
            {"id": 32281, "ru": "Несладкая жизнь псионика Сайки К.", "en": "Saiki Kusuo", "score": "8.41", "genres": "Комедия, Сверхъестественное", "poster": "https://shikimori.one/system/animes/original/32281.jpg", "hook": "Могущественный экстрасенс хочет спокойной жизни, но чудаки вокруг не дают покоя."},
            {"id": 30831, "ru": "Этот замечательный мир! (KonoSuba)", "en": "KonoSuba", "score": "8.10", "genres": "Комедия, Пародия", "poster": "https://shikimori.one/system/animes/original/30831.jpg", "hook": "Казума берет с собой бесполезную богиню Акву и собирает чудаковатую команду."},
            {"id": 32182, "ru": "Моб Психо 100", "en": "Mob Psycho 100", "score": "8.48", "genres": "Экшен, Комедия", "poster": "https://shikimori.one/system/animes/original/32182.jpg", "hook": "Школьник с колоссальной телекинетической силой пытается жить обычной жизнью."},
            {"id": 245, "ru": "Крутой учитель Онидзука", "en": "GTO", "score": "8.69", "genres": "Комедия, Школа", "poster": "https://shikimori.one/system/animes/original/245.jpg", "hook": "Бывший главарь банды байкеров учит трудных подростков настоящей жизни."},
            {"id": 10165, "ru": "Повседневная жизнь старшеклассников", "en": "Danshi Koukousei", "score": "8.23", "genres": "Комедия, Повседневность", "poster": "https://shikimori.one/system/animes/original/10165.jpg", "hook": "Реалистичный и уморительный взгляд на будни трех школьных оболтусов."},
            {"id": 18677, "ru": "Сатана на подработке!", "en": "Hataraku Maou-sama!", "score": "7.74", "genres": "Комедия, Фэнтези", "poster": "https://shikimori.one/system/animes/original/18677.jpg", "hook": "Владыка тьмы попадает в современный Токио и устраивается жарить бургеры."},
            {"id": 38474, "ru": "Восхождение в тени!", "en": "Kage no Jitsuryokusha", "score": "8.24", "genres": "Экшен, Пародия", "poster": "https://shikimori.one/system/animes/original/38474.jpg", "hook": "Парень играет роль серого кардинала, не зная, что все его выдумки реальны."},
            {"id": 50265, "ru": "Семья шпиона", "en": "Spy x Family", "score": "8.48", "genres": "Комедия, Экшен", "poster": "https://shikimori.one/system/animes/original/50265.jpg", "hook": "Шпион, наемная убийца и девочка-телепат создают фиктивную образцовую семью."},
            {"id": 41389, "ru": "Скейт: Бесконечность", "en": "SK8 the Infinity", "score": "8.02", "genres": "Спорт, Комедия", "poster": "https://shikimori.one/system/animes/original/41389.jpg", "hook": "Драйвовые нелегальные гонки на скейтах по заброшенной шахте на Окинаве."},
            {"id": 35843, "ru": "Дурни, тесты и призванные существа", "en": "Baka to Test", "score": "7.54", "genres": "Комедия, Романтика", "poster": "https://shikimori.one/system/animes/original/35843.jpg", "hook": "Битва школьных классов за комфорт в кабинетах с помощью призванных аватаров."}
        ]
    },
    "isekai_special": {
        "key": "isekai_special",
        "name": "🌀 Захватывающие исекаи с изюминкой",
        "title": "ТОП: Лучшие Исекаи с Необычной Завязкой 🌀",
        "desc": "Попаданцы в другие миры, где всё пошло не по стандартному сценарию:",
        "tags": "#исекай #фэнтези #приключения",
        "shiki_genre": "62,10",
        "shiki_order": "ranked",
        "candidates": [
            {"id": 39535, "ru": "Реинкарнация безработного", "en": "Mushoku Tensei", "score": "8.65", "genres": "Магия, Приключения", "poster": "https://shikimori.one/system/animes/original/39535.jpg", "hook": "34-летний затворник получает второй шанс прожить достойную жизнь с мечом и магией."},
            {"id": 31240, "ru": "Re:Zero — жизнь с нуля в другом мире", "en": "Re:Zero", "score": "8.23", "genres": "Триллер, Драма", "poster": "https://shikimori.one/system/animes/original/31240.jpg", "hook": "Субару Нацуки обретает способность возвращаться во времени только после гибели."},
            {"id": 37430, "ru": "О моём перерождении в слизь", "en": "Tensei Slime", "score": "8.12", "genres": "Фэнтези, Сёнэн", "poster": "https://shikimori.one/system/animes/original/37430.jpg", "hook": "Офисный клерк перерождается слизью и строит процветающую федерацию монстров."},
            {"id": 29803, "ru": "Повелитель (Overlord)", "en": "Overlord", "score": "7.92", "genres": "Фэнтези, Экшен", "poster": "https://shikimori.one/system/animes/original/29803.jpg", "hook": "Геймер остается заперт в теле могущественного скелета-мага в новом мире."},
            {"id": 39292, "ru": "Восхождение героя щита", "en": "Tate no Yuusha", "score": "7.94", "genres": "Драма, Фэнтези", "poster": "https://shikimori.one/system/animes/original/39292.jpg", "hook": "Оболганный и преданный герой щита поднимается со дна ради справедливости."},
            {"id": 34618, "ru": "Военная хроника маленькой девочки", "en": "Youjo Senki", "score": "7.96", "genres": "Магия, Военное", "poster": "https://shikimori.one/system/animes/original/34618.jpg", "hook": "Циничный японский менеджер перерождается одаренной девочкой-магом на войне."},
            {"id": 19815, "ru": "Нет игры — нет жизни", "en": "No Game No Life", "score": "8.08", "genres": "Игры, Комедия", "poster": "https://shikimori.one/system/animes/original/19815.jpg", "hook": "Гениальные брат и сестра попадают в мир, где любые конфликты решаются играми."},
            {"id": 40594, "ru": "Да, я паук, и что же?", "en": "Kumo desu ga", "score": "7.39", "genres": "Экшен, Фэнтези", "poster": "https://shikimori.one/system/animes/original/40594.jpg", "hook": "Обычная школьница перерождается слабейшим паучком в смертоносном лабиринте."},
            {"id": 38790, "ru": "Непризнанный школой владыка демонов", "en": "Maou Gakuin", "score": "7.35", "genres": "Магия, Фэнтези", "poster": "https://shikimori.one/system/animes/original/38790.jpg", "hook": "Всемогущий владыка демонов перерождается спустя 2000 лет в мирной эпохе."},
            {"id": 38000, "ru": "Этот герой неуязвим, но очень осторожен", "en": "Cautious Hero", "score": "7.45", "genres": "Комедия, Фэнтези", "poster": "https://shikimori.one/system/animes/original/38000.jpg", "hook": "Богиня призывает невероятно сильного героя, который перестраховывается во всем."},
            {"id": 49891, "ru": "О моём перерождении в меч", "en": "Tensei shitara Ken", "score": "7.42", "genres": "Экшен, Фэнтези", "poster": "https://shikimori.one/system/animes/original/49891.jpg", "hook": "Разумный меч становится наставником и оружием юной кошкодевочки Фран."},
            {"id": 40356, "ru": "Гримгал пепла и иллюзий", "en": "Grimgar", "score": "7.62", "genres": "Драма, Фэнтези", "poster": "https://shikimori.one/system/animes/original/40356.jpg", "hook": "Группа новичков без воспоминаний отчаянно учится выживать в суровом мире."}
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

def _get_font(size, bold=True):
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()

def create_compilation_collage(poster_urls, title_text, output_filename="compilation_collage.jpg"):
    """
    Downloads all poster images and composites them into a single high-resolution,
    aesthetically polished collage banner with rounded corners, drop shadows,
    and glowing position badges (following UI/UX Pro Max guidelines).
    Supports 3 to 10 posters (1 row for <=5, 2 rows grid for 6-10).
    """
    os.makedirs(COLLAGE_DIR, exist_ok=True)
    out_path = os.path.join(COLLAGE_DIR, output_filename)

    images = []
    for u in poster_urls:
        try:
            req = urllib.request.Request(u, headers={'User-Agent': 'AnimeVistBot/1.0'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                img = Image.open(io.BytesIO(resp.read())).convert("RGBA")
                images.append(img)
        except Exception as e:
            print(f"[Compilations] Ошибка загрузки постера {u}: {e}")

    if not images:
        return None

    n = len(images)

    # Layout configuration based on count
    if n <= 5:
        # 1-Row panoramic banner
        poster_h = 440 if n <= 4 else 390
        poster_w = int(poster_h * 0.70)
        card_gap = 16
        pad_x = 24
        pad_top = 92
        pad_bottom = 24
        total_w = pad_x * 2 + (poster_w * n) + (card_gap * (n - 1))
        total_h = pad_top + poster_h + pad_bottom
        is_grid = False
        cols = n
    else:
        # 2-Row adaptive grid (5x2 for 10, 4x2 for 7-8, 3x2 for 6)
        cols = (n + 1) // 2
        poster_h = 320
        poster_w = int(poster_h * 0.70)  # ~224px
        card_gap = 14
        row_gap = 16
        pad_x = 24
        pad_top = 92
        pad_bottom = 24
        total_w = pad_x * 2 + (poster_w * cols) + (card_gap * (cols - 1))
        total_h = pad_top + (poster_h * 2) + row_gap + pad_bottom
        is_grid = True

    # Canvas with dark luxury background (#080C16)
    canvas = Image.new("RGBA", (total_w, total_h), (8, 12, 22, 255))
    draw = ImageDraw.Draw(canvas)

    # Header fonts
    font_pill = _get_font(12, bold=True)
    font_title = _get_font(21, bold=True)
    font_badge = _get_font(18 if is_grid else 19, bold=True)

    # Clean title from emojis and duplicated prefixes
    clean_title = re.sub(r'[\U00010000-\U0010ffff]', '', title_text).strip()
    clean_title = re.sub(r'^(ТОП[\s\-\d:]*)+', '', clean_title, flags=re.IGNORECASE).strip()
    header_display = f"ТОП-{n}: {clean_title}" if clean_title else f"ТОП-{n} Шедевров"

    # Header glass card container
    header_box = (pad_x, 12, total_w - pad_x, 80)
    draw.rounded_rectangle(header_box, radius=12, fill=(15, 23, 42, 220), outline=(255, 255, 255, 25), width=1)

    # Header Pill badge inside container
    pill_text = "ANIME VIST  •  CURATED SELECTION"
    pill_w = 260
    pill_h = 22
    draw.rounded_rectangle((pad_x + 14, 18, pad_x + 14 + pill_w, 18 + pill_h), radius=10, fill=(30, 41, 59, 230), outline=(99, 102, 241, 140), width=1)
    draw.text((pad_x + 24, 21), pill_text, fill=(129, 140, 248), font=font_pill)

    # Header main title
    draw.text((pad_x + 16, 47), header_display, fill=(248, 250, 252), font=font_title)

    # Glowing subtle accent dot in right corner
    draw.ellipse((total_w - pad_x - 30, 38, total_w - pad_x - 18, 50), fill=(99, 102, 241, 220), outline=(236, 72, 153, 200), width=1)

    # Rounded corner mask template for posters
    scale = 2
    r = 12 if is_grid else 14
    mask = Image.new("L", (poster_w * scale, poster_h * scale), 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.rounded_rectangle((0, 0, poster_w * scale, poster_h * scale), radius=r * scale, fill=255)
    mask = mask.resize((poster_w, poster_h), Image.Resampling.LANCZOS)

    # Calculate card coordinates
    cards_coords = []
    if not is_grid:
        curr_x = pad_x
        for idx in range(n):
            cards_coords.append((curr_x, pad_top))
            curr_x += poster_w + card_gap
    else:
        # Row 1 (first cols items)
        curr_x = pad_x
        for idx in range(cols):
            cards_coords.append((curr_x, pad_top))
            curr_x += poster_w + card_gap
        # Row 2 (remaining items)
        row2_count = n - cols
        row2_w = (poster_w * row2_count) + (card_gap * (row2_count - 1))
        grid_content_w = (poster_w * cols) + (card_gap * (cols - 1))
        row2_start_x = pad_x + (grid_content_w - row2_w) // 2
        row2_y = pad_top + poster_h + row_gap
        curr_x = row2_start_x
        for idx in range(row2_count):
            cards_coords.append((curr_x, row2_y))
            curr_x += poster_w + card_gap

    # Composite cards
    for idx, raw in enumerate(images, 1):
        pos_x, pos_y = cards_coords[idx - 1]

        # 1. Drop shadow behind card
        shadow = Image.new("RGBA", (poster_w + 16, poster_h + 16), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(shadow)
        s_draw.rounded_rectangle((8, 8, poster_w + 8, poster_h + 8), radius=r + 2, fill=(0, 0, 0, 150))
        shadow = shadow.filter(ImageFilter.GaussianBlur(8))
        canvas.paste(shadow, (pos_x - 8, pos_y - 4), shadow)

        # 2. Resize and apply vignette
        resized = raw.resize((poster_w, poster_h), Image.Resampling.LANCZOS).convert("RGBA")
        vignette = Image.new("RGBA", (poster_w, poster_h), (0, 0, 0, 0))
        v_draw = ImageDraw.Draw(vignette)
        for y in range(int(poster_h * 0.62), poster_h):
            alpha = int(190 * ((y - poster_h * 0.62) / (poster_h * 0.38)))
            v_draw.line([(0, y), (poster_w, y)], fill=(9, 13, 24, alpha))
        card_composite = Image.alpha_composite(resized, vignette)

        # 3. 1px card border
        border = Image.new("RGBA", (poster_w, poster_h), (0, 0, 0, 0))
        b_draw = ImageDraw.Draw(border)
        b_draw.rounded_rectangle((0, 0, poster_w - 1, poster_h - 1), radius=r, outline=(255, 255, 255, 50), width=1)
        card_with_border = Image.alpha_composite(card_composite, border)

        # 4. Paste card with anti-aliased mask
        card_masked = Image.new("RGBA", (poster_w, poster_h), (0, 0, 0, 0))
        card_masked.paste(card_with_border, (0, 0), mask)
        canvas.paste(card_masked, (pos_x, pos_y), card_masked)

        # 5. Position Badge (vibrant circular gradient pill)
        b_size = 32 if is_grid else 36
        badge = Image.new("RGBA", (b_size, b_size), (0, 0, 0, 0))
        badge_draw = ImageDraw.Draw(badge)
        badge_draw.ellipse((0, 0, b_size - 1, b_size - 1), fill=(99, 102, 241, 240), outline=(255, 255, 255, 180), width=2)

        # Centered number
        num_str = str(idx)
        bbox = badge_draw.textbbox((0, 0), num_str, font=font_badge)
        bw = bbox[2] - bbox[0]
        bh = bbox[3] - bbox[1]
        badge_draw.text(((b_size - bw) / 2, (b_size - bh) / 2 - 2), num_str, fill=(255, 255, 255, 255), font=font_badge)
        canvas.paste(badge, (pos_x + 8, pos_y + 8), badge)

    final_rgb = canvas.convert("RGB")
    final_rgb.save(out_path, "JPEG", quality=95)
    print(f"[Compilations] Высококачественный HD-коллаж успешно сгенерирован ({n} постеров): {out_path}")
    return out_path

_shikimori_cache = {}

def fetch_shikimori_candidates(genre_id=None, order="ranked", limit=20):
    """
    Queries Shikimori API dynamically to discover additional titles with in-memory caching.
    """
    cache_key = f"{genre_id}:{order}:{limit}"
    if cache_key in _shikimori_cache:
        return _shikimori_cache[cache_key]

    params = [f"order={order}", f"limit={limit}"]
    if genre_id:
        params.append(f"genre={genre_id}")
    url = f"https://shikimori.one/api/animes?{'&'.join(params)}"
    req = urllib.request.Request(url, headers={'User-Agent': 'AnimeVistBot/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
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
            _shikimori_cache[cache_key] = results
            return results
    except Exception as e:
        print(f"[Compilations] Shikimori query error: {e}")
        return []

def select_unseen_anime(theme_key, count=4, refresh=False):
    """
    Selects N unseen anime for the compilation to ensure it is NEVER the same.
    Dynamically rotates, shuffles, and handles pools up to 10 anime without duplicate titles.
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

    # Filter by seen
    unseen = [c for c in pool if str(c['id']) not in seen]
    random.shuffle(unseen)

    # If pool is exhausted or less than requested count, recycle seen with shuffling
    if len(unseen) < count:
        print(f"[Compilations] В пуле {len(unseen)} новых тайтлов (запрошено {count}), подключаем ротацию.")
        already_ids = set(c['id'] for c in unseen)
        remainder_pool = [c for c in pool if c['id'] not in already_ids]
        random.shuffle(remainder_pool)
        unseen.extend(remainder_pool)

    selected = unseen[:count]
    return selected

def build_compilation_content(theme_key, count=4, refresh=False):
    theme = THEMES.get(theme_key, THEMES['must_watch'])
    config = load_config()
    app_name = config.get('app', {}).get('name', 'AnimeVist')

    items = select_unseen_anime(theme_key, count=count, refresh=refresh)
    if not items:
        return None, None, None, None

    n = len(items)
    lines = [f"🌟 <b>ТОП-{n}: {theme['title']}</b>\n"]
    if n <= 5 and theme.get('desc'):
        lines.append(f"<i>{theme['desc']}</i>\n")

    emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
    poster_urls = []

    if n <= 5:
        # Full detailed format for 3-5 anime
        for idx, it in enumerate(items):
            em = emojis[idx] if idx < len(emojis) else f"{idx+1}."
            lines.append(f"{em} <b>«{it['ru']}»</b> / <i>{it['en']}</i>")
            lines.append(f"⭐️ <b>{it['score']}</b> | 🎭 {it['genres']}")
            lines.append(f"📝 {it['hook']}\n")
            poster_urls.append(it['poster'])
    else:
        # High-density compact format for 6-10 anime (guarantees fitting strictly in Telegram 1024-char limit)
        for idx, it in enumerate(items):
            em = emojis[idx] if idx < len(emojis) else f"{idx+1}."
            hook_short = it['hook']
            max_hook_len = 24 if n >= 9 else (36 if n >= 7 else 60)
            if len(hook_short) > max_hook_len:
                hook_short = hook_short[:max_hook_len - 2].rstrip() + '..'
            lines.append(f"{em} <b>«{it['ru']}»</b> (⭐️ {it['score']}) — {hook_short}")
            poster_urls.append(it['poster'])
        lines.append("")

    lines.append(f"✨ <i>Смотрите эти тайтлы в приложении {app_name}!</i>")
    lines.append(f"#подборка #топ_аниме {theme['tags']} #чтопосмотреть #{app_name.lower()}")

    caption = "\n".join(lines)

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

def get_compilation_preview(theme_key=None, count=4, refresh=True):
    """
    Returns structured preview data for web dashboard and client console.
    """
    if not theme_key or theme_key == 'auto' or theme_key not in THEMES:
        theme_key = 'must_watch'

    try:
        count = max(3, min(10, int(count)))
    except (ValueError, TypeError):
        count = 4

    theme = THEMES[theme_key]
    caption, poster_urls, reply_markup, items = build_compilation_content(theme_key, count=count, refresh=refresh)

    caption_html = caption.replace('\n', '<br>') if caption else ""
    return {
        "ok": True,
        "theme": theme_key,
        "title": theme['name'],
        "desc": theme['desc'],
        "tags": theme['tags'],
        "count": len(items) if items else count,
        "items": items or [],
        "caption": caption,
        "caption_html": caption_html,
        "poster": poster_urls[0] if poster_urls else "",
        "poster_urls": poster_urls or []
    }

def run_compilation_post(genre_key=None, count=4, dry_run=False):
    sender = TelegramSender()

    # Auto-pick next theme if not specified
    if not genre_key or genre_key == 'auto' or genre_key not in THEMES:
        keys = list(THEMES.keys())
        idx = int(time.time() / 3600) % len(keys)
        genre_key = keys[idx]

    theme = THEMES[genre_key]
    caption, poster_urls, reply_markup, chosen_items = build_compilation_content(genre_key, count=count, refresh=True)

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
        print(f"Caption length: {len(caption)} / 1024")
        print(f"Collage Image: {poster_to_send}")
        print(f"Included {len(chosen_items)} anime: {[c['ru'] for c in chosen_items]}")
        return {"ok": True, "theme": genre_key, "count": len(chosen_items), "caption_length": len(caption), "dry_run": True}

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
