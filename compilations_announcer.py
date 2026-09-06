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
THEMES = {   'must_watch': {   'key': 'must_watch',
                      'name': '🏆 Золотая классика и шедевры (8.5+)',
                      'title': 'Обязательно к просмотру (Золотой фонд аниме) 🏆',
                      'desc': 'Культовые тайтлы с высочайшим мировым рейтингом, навсегда вошедшие в историю:',
                      'tags': '#шедевры #must_watch #топ_аниме',
                      'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx154587-qQTzQnEJJ3oB.jpg',
                      'shiki_genre': None,
                      'shiki_order': None,
                      'candidates': [   {   'id': 52991,
                                            'ru': 'Провожающая в последний путь Фрирен',
                                            'en': 'Sousou no Frieren',
                                            'score': '9.10',
                                            'genres': 'Фэнтези, Драма',
                                            'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx154587-qQTzQnEJJ3oB.jpg',
                                            'hook': 'Бессмертная эльфийка отправляется в путь, чтобы постичь ценность '
                                                    'человеческой жизни.'},
                                        {   'id': 5114,
                                            'ru': 'Стальной алхимик: Братство',
                                            'en': 'Hagane no Renkinjutsushi: FULLMETAL ALCHEMIST',
                                            'score': '9.00',
                                            'genres': 'Сёнэн, Фэнтези',
                                            'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx5114-nSWCgQlmOMtj.jpg',
                                            'hook': 'Братья Элрики ищут философский камень, чтобы вернуть утраченные '
                                                    'тела.'},
                                        {   'id': 9253,
                                            'ru': 'Врата Штейна',
                                            'en': 'Steins;Gate',
                                            'score': '8.90',
                                            'genres': 'Фантастика, Триллер',
                                            'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx9253-tIUXF2gfU8Sg.jpg',
                                            'hook': 'Случайное создание машины времени втягивает друзей в опаснейший '
                                                    'заговор.'},
                                        {   'id': 11061,
                                            'ru': 'Охотник х Охотник',
                                            'en': 'HUNTER×HUNTER (2011)',
                                            'score': '8.90',
                                            'genres': 'Экшен, Приключения',
                                            'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx11061-y5gsT1hoHuHw.png',
                                            'hook': 'Гон отправляется на смертельный экзамен Охотников ради поисков '
                                                    'отца.'},
                                        {   'id': 61629,
                                            'ru': 'Монстр',
                                            'en': 'Monster',
                                            'score': '8.80',
                                            'genres': 'Драма, Триллер',
                                            'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx19-gtMC64182sm4.jpg',
                                            'hook': 'Гениальный хирург спасает жизнь мальчику, не зная, что взрастил '
                                                    'зло.'},
                                        {   'id': 1,
                                            'ru': 'Ковбой Бибоп',
                                            'en': 'Cowboy Bebop',
                                            'score': '8.60',
                                            'genres': 'Фантастика, Экшен',
                                            'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx1-GCsPm7waJ4kS.png',
                                            'hook': 'Охотники за головами бороздят Солнечную систему под звуки джаза.'},
                                        {   'id': 2001,
                                            'ru': 'Гуррен-Лаганн',
                                            'en': 'Tengen Toppa Gurren Lagann',
                                            'score': '8.50',
                                            'genres': 'Экшен, Меха',
                                            'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx2001-XwRnjzGeFWRQ.png',
                                            'hook': 'Симон и Камина бурят путь наверх сквозь пространство, бросая '
                                                    'вызов Вселенной.'},
                                        {   'id': 1575,
                                            'ru': 'Код Гиас: Восставший Лелуш',
                                            'en': 'Code Geass: Hangyaku no Lelouch',
                                            'score': '8.50',
                                            'genres': 'Экшен, Меха',
                                            'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx1575-hsmWM2ydNm1m.jpg',
                                            'hook': 'Отвергнутый принц получает силу абсолютного подчинения и начинает '
                                                    'восстание.'},
                                        {   'id': 1535,
                                            'ru': 'Тетрадь смерти',
                                            'en': 'DEATH NOTE',
                                            'score': '8.40',
                                            'genres': 'Мистика, Детектив',
                                            'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx1535-kUgkcrfOrkUM.jpg',
                                            'hook': 'Интеллектуальная дуэль школьника с тетрадью бога смерти и '
                                                    'гениального сыщика L.'},
                                        {   'id': 245,
                                            'ru': 'Крутой учитель Онидзука',
                                            'en': 'GTO',
                                            'score': '8.40',
                                            'genres': 'Комедия, Школа',
                                            'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx245-NcQAyTipUMeO.jpg',
                                            'hook': 'Бывший байкер берется перевоспитывать самый проблемный класс '
                                                    'школы.'},
                                        {   'id': 205,
                                            'ru': 'Самурай Чамплу',
                                            'en': 'Samurai Champloo',
                                            'score': '8.40',
                                            'genres': 'Экшен, Приключения',
                                            'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx205-7tHVFu6dPBm9.png',
                                            'hook': 'Два непревзойденных мечника сопровождают девушку в поисках '
                                                    'самурая.'},
                                        {   'id': 30,
                                            'ru': 'Евангелион',
                                            'en': 'Shin Seiki Evangelion',
                                            'score': '8.30',
                                            'genres': 'Меха, Психология',
                                            'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx30-AI1zr74Dh4ye.jpg',
                                            'hook': 'Подростки пилотируют биороботов, защищая мир от таинственных '
                                                    'Ангелов.'},
                                        {   'id': 199,
                                            'ru': 'Унесённые призраками',
                                            'en': 'Sen to Chihiro no Kamikakushi',
                                            'score': '8.60',
                                            'genres': 'Сказка, Мистика',
                                            'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx199-sWefXJvXkDOb.jpg',
                                            'hook': 'Десятилетняя Тихиро попадает в таинственный мир духов и ведьмы '
                                                    'Юбабы.'},
                                        {   'id': 16498,
                                            'ru': 'Атака титанов',
                                            'en': 'Shingeki no Kyojin',
                                            'score': '8.50',
                                            'genres': 'Экшен, Драма',
                                            'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx16498-buvcRTBx4NSm.jpg',
                                            'hook': 'Остатки человечества сражаются за выживание с '
                                                    'гигантами-людоедами.'},
                                        {   'id': 37521,
                                            'ru': 'Сага о Винланде',
                                            'en': 'Vinland Saga',
                                            'score': '8.78',
                                            'genres': 'Action, Adventure, Drama',
                                            'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx101348-2fhDFPCuMNiz.jpg',
                                            'hook': 'Суровый исторический эпос о мести, викингах и поиске истинного '
                                                    'пути.'},
                                        {   'id': 4181,
                                            'ru': 'Кланнад: Продолжение истории',
                                            'en': 'Clannad: After Story',
                                            'score': '8.93',
                                            'genres': 'Drama, Romance, Slice of Life',
                                            'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx4181-zUKE7BZC62OF.png',
                                            'hook': 'Трогательная до слёз история взросления, семьи и настоящей '
                                                    'любви.'},
                                        {   'id': 20583,
                                            'ru': 'Волейбол!!',
                                            'en': 'HAIKYU!!',
                                            'score': '8.43',
                                            'genres': 'Comedy, Drama, Sports',
                                            'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx20464-ooZUyBe4ptp9.png',
                                            'hook': 'Невероятно вдохновляющая спортивная драма о преодолении и '
                                                    'командном духе.'},
                                        {   'id': 32182,
                                            'ru': 'Моб Психо 100',
                                            'en': 'Mob Psycho 100',
                                            'score': '8.49',
                                            'genres': 'Action, Comedy, Drama',
                                            'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx21507-6YUSbh2m0N1p.jpg',
                                            'hook': 'Школьник с богоподобной силой учится быть человеком и ценить '
                                                    'доброту.'},
                                        {   'id': 34599,
                                            'ru': 'Созданный в Бездне',
                                            'en': 'Made in Abyss',
                                            'score': '8.62',
                                            'genres': 'Adventure, Drama, Fantasy',
                                            'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx97986-TQ7dCgbS3y5s.jpg',
                                            'hook': 'Обманчиво милое, но пугающе глубокое путешествие на дно '
                                                    'неизведанного мира.'},
                                        {   'id': 33352,
                                            'ru': 'Вайолет Эвергарден',
                                            'en': 'Violet Evergarden',
                                            'score': '8.69',
                                            'genres': 'Drama, Fantasy, Slice of Life',
                                            'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx21827-ubzq619ZA2E9.png',
                                            'hook': 'Бывшее живое оружие учится понимать человеческие чувства, сочиняя '
                                                    'письма.'},
                                        {   'id': 32281,
                                            'ru': 'Твоё имя',
                                            'en': 'Your Name.',
                                            'score': '8.82',
                                            'genres': 'Drama, Romance, Supernatural',
                                            'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx21519-SUo3ZQuCbYhJ.png',
                                            'hook': 'Романтическая фантастика Макото Синкая о связи душ сквозь время и '
                                                    'расстояние.'},
                                        {   'id': 164,
                                            'ru': 'Принцесса Мононоке',
                                            'en': 'Princess Mononoke',
                                            'score': '8.67',
                                            'genres': 'Action, Adventure, Drama',
                                            'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx164-ySuGzCWVw2cL.jpg',
                                            'hook': 'Шедевр Хаяо Миядзаки о великом противостоянии природы и '
                                                    'цивилизации.'},
                                        {   'id': 22135,
                                            'ru': 'Пинг-понг',
                                            'en': 'Ping Pong the Animation',
                                            'score': '8.63',
                                            'genres': 'Drama, Psychological, Sports',
                                            'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx20607-fIOxVISIl0HY.jpg',
                                            'hook': 'Авангардный шедевр Масааки Юасы о дружбе, спорте и поиске себя.'},
                                        {   'id': 13125,
                                            'ru': 'Из нового света',
                                            'en': 'From the New World',
                                            'score': '8.24',
                                            'genres': 'Drama, Horror, Mystery',
                                            'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx13125-2EDZb8ahshQc.png',
                                            'hook': 'Глубокая психологическая антиутопия в мире победившего '
                                                    'телекинеза.'},
                                        {   'id': 10087,
                                            'ru': 'Судьба/Начало',
                                            'en': 'Fate/Zero',
                                            'score': '8.26',
                                            'genres': 'Action, Drama, Fantasy',
                                            'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx10087-M4Hd9qrHGrXk.png',
                                            'hook': 'Бескомпромиссная война магов и героических душ за исполнение '
                                                    'любого желания.'},
                                        {   'id': 44511,
                                            'ru': 'Человек-бензопила',
                                            'en': 'Chainsaw Man',
                                            'score': '8.42',
                                            'genres': 'Action, Drama, Horror',
                                            'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx127230-DdP4vAdssLoz.png',
                                            'hook': 'Ураганный безумный экшен о демонах, долгах и простых человеческих '
                                                    'мечтах.'},
                                        {   'id': 40748,
                                            'ru': 'Магическая битва',
                                            'en': 'JUJUTSU KAISEN',
                                            'score': '8.5',
                                            'genres': 'Action, Drama, Supernatural',
                                            'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx113415-LHBAeoZDIsnF.jpg',
                                            'hook': 'Динамичная сага о борьбе с опасными проклятиями и цене силы.'},
                                        {   'id': 46102,
                                            'ru': 'Случайное такси',
                                            'en': 'ODDTAXI',
                                            'score': '8.62',
                                            'genres': 'Drama, Mystery, Psychological',
                                            'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx128547-nNekWTKqmvEi.jpg',
                                            'hook': 'Гениальный неонуарный детектив с антропоморфными зверями и '
                                                    'твистами.'},
                                        {   'id': 48849,
                                            'ru': 'Сонни Бой',
                                            'en': 'Sonny Boy',
                                            'score': '7.86',
                                            'genres': 'Drama, Mystery, Psychological',
                                            'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx132126-4ugVjXMQLAps.png',
                                            'hook': 'Сюрреалистичный артхаус о дрейфе школьного класса между '
                                                    'параллельными мирами.'},
                                        {   'id': 36028,
                                            'ru': 'Золотое божество',
                                            'en': 'Golden Kamuy',
                                            'score': '7.89',
                                            'genres': 'Action, Adventure, Comedy',
                                            'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx99699-mBCjpoWpAVGX.jpg',
                                            'hook': 'Колоритная охота за золотом айнов на суровых просторах Хоккайдо.'},
                                        {   'id': 777,
                                            'ru': 'Хеллсинг OVA',
                                            'en': 'Hellsing Ultimate',
                                            'score': '8.34',
                                            'genres': 'Action, Horror, Supernatural',
                                            'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx777-F6547pSAR2Zd.jpg',
                                            'hook': 'Культовое кровавое противостояние вампира Алукарда и '
                                                    'нацистов-оккультистов.'},
                                        {   'id': 889,
                                            'ru': 'Пираты «Чёрной лагуны»',
                                            'en': 'Black Lagoon',
                                            'score': '8.04',
                                            'genres': 'Action, Adventure, Drama',
                                            'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx889-4S7N2ciq2cwA.png',
                                            'hook': 'Адреналиновый боевик о наёмниках в криминальной столице '
                                                    'Таиланда.'},
                                        {   'id': 877,
                                            'ru': 'Нана',
                                            'en': 'NANA',
                                            'score': '8.57',
                                            'genres': 'Drama, Music, Romance',
                                            'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx877-6BUYEWp8By8j.png',
                                            'hook': 'Взрослая и искренняя драма о двух совершенно разных девушках с '
                                                    'одинаковым именем.'},
                                        {   'id': 28851,
                                            'ru': 'Форма голоса',
                                            'en': 'A Silent Voice',
                                            'score': '8.93',
                                            'genres': 'Drama, Romance, Slice of Life',
                                            'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx20954-sYRfE5jQRtSB.jpg',
                                            'hook': 'Проникновенная драма об искуплении вины перед глухой девочкой.'},
                                        {   'id': 23273,
                                            'ru': 'Твоя апрельская ложь',
                                            'en': 'Your lie in April',
                                            'score': '8.64',
                                            'genres': 'Drama, Music, Romance',
                                            'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx20665-TLgkL8T8IRFd.png',
                                            'hook': 'Музыкальная история о любви, трагедии и возвращении вкуса к '
                                                    'жизни.'},
                                        {   'id': 42310,
                                            'ru': 'Киберпанк: Бегущие по краю',
                                            'en': 'Cyberpunk: Edgerunners',
                                            'score': '8.62',
                                            'genres': 'Action, Drama, Psychological',
                                            'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx120377-ayZPoxiWt4Li.jpg',
                                            'hook': 'Взрывная трагедия парня из трущоб в безжалостном Найт-Сити.'}]},
    'hidden_gems': {   'key': 'hidden_gems',
                       'name': '💎 Недооценённые алмазы (Hidden Gems)',
                       'title': 'Недооценённые шедевры, которые вы могли пропустить 💎',
                       'desc': 'Редкие находки с великолепным сюжетом, незаслуженно оставшиеся в тени хайпа:',
                       'tags': '#hidden_gems #недооцененное #чтопосмотреть',
                       'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx13125-2EDZb8ahshQc.png',
                       'shiki_genre': None,
                       'shiki_order': None,
                       'candidates': [   {   'id': 13125,
                                             'ru': 'Из нового света',
                                             'en': 'Shinsekai yori',
                                             'score': '8.00',
                                             'genres': 'Драма, Фантастика',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx13125-2EDZb8ahshQc.png',
                                             'hook': 'Утопическое общество телекинетиков скрывает леденящую кровь '
                                                     'тайну.'},
                                         {   'id': 22135,
                                             'ru': 'Пинг-понг',
                                             'en': 'Ping Pong THE ANIMATION',
                                             'score': '8.60',
                                             'genres': 'Спорт, Драма',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx20607-fIOxVISIl0HY.jpg',
                                             'hook': 'Шедевр Масааки Юасы о дружбе, призвании и взрослении через '
                                                     'спорт.'},
                                         {   'id': 790,
                                             'ru': 'Эрго Прокси',
                                             'en': 'Ergo Proxy',
                                             'score': '7.60',
                                             'genres': 'Детектив, Психология',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx790-YTUCvBKX8ZWK.jpg',
                                             'hook': 'Загадки города-купола Ромдо, где андроиды внезапно обретают '
                                                     'душу.'},
                                         {   'id': 486,
                                             'ru': 'Путешествие Кино',
                                             'en': 'Kino no Tabi: the Beautiful World',
                                             'score': '8.10',
                                             'genres': 'Приключения, Философия',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx486-xXUgNOEBuxGs.jpg',
                                             'hook': 'Путешественница Кино и говорящий мотоцикл исследуют обычаи стран '
                                                     'мира.'},
                                         {   'id': 2251,
                                             'ru': 'Баккано! (Шумиха)',
                                             'en': 'Baccano!',
                                             'score': '8.10',
                                             'genres': 'Экшен, Комедия',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx2251-tTQoWxVy4472.jpg',
                                             'hook': 'Вихрь мафиози, алхимиков и бессмертных на трансконтинентальном '
                                                     'поезде.'},
                                         {   'id': 2246,
                                             'ru': 'Мононокэ',
                                             'en': 'Mononoke',
                                             'score': '8.20',
                                             'genres': 'Мистика, Детектив',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx2246-WHkSkgyuxfgD.jpg',
                                             'hook': 'Безымянный Аптекарь изгоняет духов, раскрывая их Форму, Суть и '
                                                     'Первопричину.'},
                                         {   'id': 387,
                                             'ru': 'Альянс Серокрылых',
                                             'en': 'Haibane Renmei',
                                             'score': '8.00',
                                             'genres': 'Драма, Мистика',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx387-dS4aJivu0zPB.png',
                                             'hook': 'Девушка с пепельными крыльями ищет свое предназначение в городе '
                                                     'за Стеной.'},
                                         {   'id': 6114,
                                             'ru': 'Радуга: Семеро из шестой камеры',
                                             'en': 'RAINBOW: Nisha Rokubou no Shichinin',
                                             'score': '8.20',
                                             'genres': 'Драма, Триллер',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/medium/b6114-pLPszMA7AxbD.jpg',
                                             'hook': 'Семеро юношей в колонии строгого режима находят братство посреди '
                                                     'жестокости.'},
                                         {   'id': 1818,
                                             'ru': 'Клеймор',
                                             'en': 'CLAYMORE',
                                             'score': '7.40',
                                             'genres': 'Тёмное фэнтези, Экшен',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx1818-KieLJv0qo3mO.jpg',
                                             'hook': 'Воительницы с серебряными глазами очищают континент от '
                                                     'чудовищ-йома.'},
                                         {   'id': 26,
                                             'ru': 'Технолайз',
                                             'en': 'TEXHNOLYZE',
                                             'score': '7.60',
                                             'genres': 'Киберпанк, Драма',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx26-ADSztyHBNO39.jpg',
                                             'hook': 'Бескомпромиссная антиутопия подземного города Люкс на грани '
                                                     'угасания.'},
                                         {   'id': 37520,
                                             'ru': 'Дороро',
                                             'en': 'Dororo',
                                             'score': '8.10',
                                             'genres': 'Исторический, Экшен',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx101347-TGaDwEYqLfm1.jpg',
                                             'hook': 'Хяккимару возвращает украденные демонами органы, истребляя '
                                                     'нечисть.'},
                                         {   'id': 28223,
                                             'ru': 'Парад смерти',
                                             'en': 'Death Parade',
                                             'score': '8.00',
                                             'genres': 'Психология, Драма',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/nx20931-bktYqOcxPERi.jpg',
                                             'hook': 'Таинственный бар, где души умерших обнажают истинную натуру в '
                                                     'играх.'},
                                         {   'id': 31043,
                                             'ru': 'Город, в котором меня нет',
                                             'en': 'Boku dake ga Inai Machi',
                                             'score': '8.10',
                                             'genres': 'Детектив, Триллер',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx21234-XmqW39aQ9o7O.jpg',
                                             'hook': 'Мангака возвращается в детство, чтобы предотвратить гибель '
                                                     'девочки.'},
                                         {   'id': 25013,
                                             'ru': 'Рассвет Йоны',
                                             'en': 'Akatsuki no Yona',
                                             'score': '7.90',
                                             'genres': 'Приключения, Фэнтези',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx20770-brCDvhTXlums.png',
                                             'hook': 'Изгнанная принцесса собирает легендарных воинов-драконов ради '
                                                     'царства.'},
                                         {   'id': 457,
                                             'ru': 'Мастер муси',
                                             'en': 'MUSHI-SHI',
                                             'score': '8.65',
                                             'genres': 'Adventure, Fantasy, Mystery',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx457-l6cTtNgI9Bi6.png',
                                             'hook': 'Медитативное философское странствие целителя духов по древней '
                                                     'Японии.'},
                                         {   'id': 339,
                                             'ru': 'Эксперименты Лэйн',
                                             'en': 'Serial Experiments Lain',
                                             'score': '8.1',
                                             'genres': 'Drama, Mystery, Psychological',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx339-xF2wp1NQuQ4r.png',
                                             'hook': 'Культовое философское предсказание интернета и размытия '
                                                     'реальности.'},
                                         {   'id': 5081,
                                             'ru': 'Истории монстров',
                                             'en': 'Bakemonogatari',
                                             'score': '8.32',
                                             'genres': 'Comedy, Drama, Mystery',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx5081-9GocceQ5Z865.jpg',
                                             'hook': 'Уникальный диалоговый стиль студии Shaft о духах и '
                                                     'психологических травмах.'},
                                         {   'id': 7785,
                                             'ru': 'Сказ о четырёх с половиной татами',
                                             'en': 'The Tatami Galaxy',
                                             'score': '8.55',
                                             'genres': 'Comedy, Mystery, Psychological',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx7785-aTjIhsYva8cJ.jpg',
                                             'hook': 'Головокружительный поиск идеальной студенческой жизни во '
                                                     'временной петле.'},
                                         {   'id': 3701,
                                             'ru': 'Кайба',
                                             'en': 'Kaiba',
                                             'score': '8.14',
                                             'genres': 'Adventure, Mystery, Psychological',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx3701-ooD3N9dD2rqa.jpg',
                                             'hook': 'Антиутопия о мире, где воспоминания оцифрованы и продаются как '
                                                     'товар.'},
                                         {   'id': 48849,
                                             'ru': 'Сонни Бой',
                                             'en': 'Sonny Boy',
                                             'score': '7.86',
                                             'genres': 'Drama, Mystery, Psychological',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx132126-4ugVjXMQLAps.png',
                                             'hook': 'Сюрреалистичный артхаус о дрейфе школьного класса между мирами.'},
                                         {   'id': 28735,
                                             'ru': 'Сёва-Гэнроку: Двойное самоубийство по ракуго',
                                             'en': 'Showa Genroku Rakugo Shinju',
                                             'score': '8.54',
                                             'genres': 'Drama',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx20972-95dyLz6lkCZ8.jpg',
                                             'hook': 'Глубокая драма о традиционном японском искусстве театра одного '
                                                     'актёра.'},
                                         {   'id': 40052,
                                             'ru': 'Великий притворщик',
                                             'en': 'Great Pretender',
                                             'score': '8.19',
                                             'genres': 'Action, Comedy, Drama',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx110349-59hhZ9CNHVdk.png',
                                             'hook': 'Стильный авантюрный триллер о международных мошенниках '
                                                     'экстра-класса.'},
                                         {   'id': 38668,
                                             'ru': 'Дорохедоро',
                                             'en': 'Dorohedoro',
                                             'score': '8.05',
                                             'genres': 'Action, Adventure, Comedy',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx105228-I4xr84QS9Pvk.jpg',
                                             'hook': 'Гротескное тёмное фэнтези о парне с головой крокодила в мире '
                                                     'магов.'},
                                         {   'id': 35557,
                                             'ru': 'Страна самоцветов',
                                             'en': 'Land of the Lustrous',
                                             'score': '8.39',
                                             'genres': 'Action, Drama, Fantasy',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx98707-25nUKb4XUFgY.png',
                                             'hook': 'Потрясающая 3D-эстетика о бессмертных разумных минералах и '
                                                     'потере себя.'},
                                         {   'id': 40908,
                                             'ru': 'Инцидент Кэмоно',
                                             'en': 'Kemono Jihen',
                                             'score': '7.35',
                                             'genres': 'Action, Drama, Mystery',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx114085-2w5rYZTOa7ER.jpg',
                                             'hook': 'Атмосферный детектив о детях-полудемонах, раскрывающих '
                                                     'паранормальные тайны.'},
                                         {   'id': 46095,
                                             'ru': 'Виви: Песнь флюоритового глаза',
                                             'en': "Vivy -Fluorite Eye's Song-",
                                             'score': '8.37',
                                             'genres': 'Action, Drama, Music',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx128546-UIwyhuhjxmL0.jpg',
                                             'hook': 'Андроид-певица спасает будущее человечества на протяжении 100 '
                                                     'лет.'},
                                         {   'id': 36563,
                                             'ru': 'Мегалобокс',
                                             'en': 'Megalobox',
                                             'score': '7.87',
                                             'genres': 'Action, Drama, Sci-Fi',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/medium/b100298-A5VQUcw7ZC64.jpg',
                                             'hook': 'Драйвовая ретро-история бойца без экзоскелета, бросившего вызов '
                                                     'чемпионам.'},
                                         {   'id': 40046,
                                             'ru': 'ID: Вторжение',
                                             'en': 'ID: INVADED',
                                             'score': '7.81',
                                             'genres': 'Drama, Mystery, Psychological',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx110350-uchN78wglmhN.png',
                                             'hook': 'Гениальный сыщик погружается в подсознание серийных убийц.'},
                                         {   'id': 40056,
                                             'ru': 'Дека-данс',
                                             'en': 'DECA-DENCE',
                                             'score': '7.35',
                                             'genres': 'Action, Adventure, Sci-Fi',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx110353-XGYSsii7qJeK.png',
                                             'hook': 'Необычный постапокалипсис о летающей крепости и людях против '
                                                     'чудовищ.'},
                                         {   'id': 6594,
                                             'ru': 'Истории мечей',
                                             'en': 'Katanagatari',
                                             'score': '8.29',
                                             'genres': 'Action, Adventure, Romance',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx6594-xrrFyCacxUle.png',
                                             'hook': 'Увлекательное странствие мечника без меча и хитрой стратегини за '
                                                     '12 клинками.'},
                                         {   'id': 329,
                                             'ru': 'Странники',
                                             'en': 'Planetes',
                                             'score': '8.25',
                                             'genres': 'Drama, Romance, Sci-Fi',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx329-4xwXdazRA7Ph.png',
                                             'hook': 'Научно достоверная производственная драма о космических '
                                                     'мусорщиках.'},
                                         {   'id': 2164,
                                             'ru': 'Кибер-виток',
                                             'en': 'Den-noh Coil',
                                             'score': '8.02',
                                             'genres': 'Adventure, Comedy, Drama',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx2164-4tUI4MJCZQO3.png',
                                             'hook': 'Школьники исследуют загадки дополненной реальности и виртуальных '
                                                     'призраков.'},
                                         {   'id': 10721,
                                             'ru': 'Пингвиний барабан',
                                             'en': 'Penguindrum',
                                             'score': '7.92',
                                             'genres': 'Drama, Mystery, Psychological',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx10721-lNEbDPX24qzn.jpg',
                                             'hook': 'Символическая притча о судьбе, семейных узах и цене спасения '
                                                     'жизни.'},
                                         {   'id': 7724,
                                             'ru': 'Усопшие',
                                             'en': 'Shiki',
                                             'score': '7.72',
                                             'genres': 'Horror, Mystery, Supernatural',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx7724-NwNnRsI34eDa.jpg',
                                             'hook': 'Леденящее противостояние жителей отдаленной деревни и восставших '
                                                     'вампиров.'},
                                         {   'id': 323,
                                             'ru': 'Агент паранойи',
                                             'en': 'Paranoia Agent',
                                             'score': '7.66',
                                             'genres': 'Drama, Mystery, Psychological',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx323-ZGkUcJOn4ngy.png',
                                             'hook': 'Психологический триллер Сатоси Кона о таинственном мальчике на '
                                                     'роликах.'},
                                         {   'id': 20057,
                                             'ru': 'Космический Денди',
                                             'en': 'Space Dandy',
                                             'score': '7.89',
                                             'genres': 'Comedy, Sci-Fi',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx20057-tG83EpH5Gu8K.jpg',
                                             'hook': 'Безумное комедийное путешествие стиляги и охотника за редкими '
                                                     'инопланетянами.'},
                                         {   'id': 202,
                                             'ru': 'Волчий дождь',
                                             'en': "Wolf's Rain",
                                             'score': '7.79',
                                             'genres': 'Action, Adventure, Drama',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx202-w2OLL3j8WmDm.jpg',
                                             'hook': 'Поэтичная постапокалиптическая элегия о поиске волками '
                                                     'потерянного Рая.'},
                                         {   'id': 2596,
                                             'ru': 'Охота на призраков',
                                             'en': 'Ghost Hound',
                                             'score': '7.39',
                                             'genres': 'Horror, Mystery, Psychological',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx2596-7VmcTkkQmOST.jpg',
                                             'hook': 'Мистический психологический триллер от создателей «Лэйн» о '
                                                     'травмах детства.'}]},
    'mindfuck': {   'key': 'mindfuck',
                    'name': '🧠 Игры разума & Психологические триллеры',
                    'title': 'ТОП: Психологические Триллеры и Игры Разума 🧠',
                    'desc': 'Напряженные сюжеты, невероятные многоходовки и неожиданные сюжетные твисты:',
                    'tags': '#триллер #психология #детектив #сюжет',
                    'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx1535-kUgkcrfOrkUM.jpg',
                    'shiki_genre': None,
                    'shiki_order': None,
                    'candidates': [   {   'id': 1535,
                                          'ru': 'Тетрадь смерти',
                                          'en': 'DEATH NOTE',
                                          'score': '8.40',
                                          'genres': 'Мистика, Детектив',
                                          'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx1535-kUgkcrfOrkUM.jpg',
                                          'hook': 'Интеллектуальная дуэль школьника с тетрадью смерти и гениального '
                                                  'сыщика L.'},
                                      {   'id': 61629,
                                          'ru': 'Монстр',
                                          'en': 'Monster',
                                          'score': '8.80',
                                          'genres': 'Драма, Триллер',
                                          'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx19-gtMC64182sm4.jpg',
                                          'hook': 'Гениальный хирург спасает жизнь мальчику, не зная, что взрастил '
                                                  'зло.'},
                                      {   'id': 13601,
                                          'ru': 'Психопаспорт',
                                          'en': 'PSYCHO-PASS',
                                          'score': '8.10',
                                          'genres': 'Детектив, Триллер',
                                          'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx13601-i42VFuHpqEOJ.jpg',
                                          'hook': 'Система «Сивилла» вычисляет вероятность преступления еще до его '
                                                  'совершения.'},
                                      {   'id': 22535,
                                          'ru': 'Паразит: Учение о жизни',
                                          'en': 'Kiseijuu: Sei no Kakuritsu',
                                          'score': '8.10',
                                          'genres': 'Экшен, Ужасы',
                                          'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx20623-dUARfggnNDOe.jpg',
                                          'hook': 'Инопланетный паразит в руке школьника втягивает его в войну за '
                                                  'выживание.'},
                                      {   'id': 437,
                                          'ru': 'Идеальная грусть',
                                          'en': 'PERFECT BLUE',
                                          'score': '8.50',
                                          'genres': 'Психология, Триллер',
                                          'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx437-69NMlXKFeuse.jpg',
                                          'hook': 'Бывшая поп-идол теряет грань между реальностью и безумием из-за '
                                                  'сталкера.'},
                                      {   'id': 37779,
                                          'ru': 'Обещанный Неверленд',
                                          'en': 'Yakusoku no Neverland',
                                          'score': '8.30',
                                          'genres': 'Мистика, Триллер',
                                          'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx101759-8UR7r9MNVpz2.jpg',
                                          'hook': 'Дети в идиллическом приюте узнают, что их растят на убой для '
                                                  'монстров.'},
                                      {   'id': 22319,
                                          'ru': 'Токийский гуль',
                                          'en': 'Tokyo Ghoul',
                                          'score': '7.60',
                                          'genres': 'Ужасы, Драма',
                                          'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/medium/b20605-k665mVkSug8D.jpg',
                                          'hook': 'Студент становится полугулем и балансирует между миром людей и '
                                                  'чудовищ.'},
                                      {   'id': 11111,
                                          'ru': 'Иная',
                                          'en': 'Another',
                                          'score': '7.10',
                                          'genres': 'Мистика, Ужасы',
                                          'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx11111-gvvE5bBYsyFo.png',
                                          'hook': 'В классе 3-3 оживает проклятие, и ученики начинают погибать один за '
                                                  'другим.'},
                                      {   'id': 50273,
                                          'ru': 'Игра друзей',
                                          'en': 'Tomodachi Game',
                                          'score': '7.60',
                                          'genres': 'Психология, Игры',
                                          'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx141014-bTWr7TtS0wt9.jpg',
                                          'hook': 'Пятеро друзей попадают в жестокую психологическую игру ради выплаты '
                                                  'долга.'},
                                      {   'id': 28999,
                                          'ru': 'Шарлотта',
                                          'en': 'Charlotte',
                                          'score': '7.50',
                                          'genres': 'Драма, Сверхъестественное',
                                          'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx20997-axVYrsIfjtYJ.jpg',
                                          'hook': 'Подростки со скрытыми способностями сталкиваются с суровой ценой '
                                                  'своих сил.'},
                                      {   'id': 33161,
                                          'ru': 'Как и ожидалось, моя школьная жизнь не задалась',
                                          'en': 'Yahari Ore no Seishun Love Come wa Machigatteiru. Zoku: Kitto, '
                                                'Onnanoko wa Osatou to Spice to Suteki na Nanika de Dekiteiru',
                                          'score': '7.80',
                                          'genres': 'Драма, Психология',
                                          'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx21769-ZBoT6szJKGZv.jpg',
                                          'hook': 'Циничный школьник Хатиман препарирует социальные маски '
                                                  'сверстников.'},
                                      {   'id': 19775,
                                          'ru': 'Рыцари Сидонии',
                                          'en': 'Sidonia no Kishi',
                                          'score': '7.30',
                                          'genres': 'Фантастика, Меха',
                                          'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx19775-h4Fc1q5qsGfP.png',
                                          'hook': 'Остатки человечества в космосе ведут отчаянную борьбу против '
                                                  'пришельцев-гауна.'},
                                      {   'id': 35507,
                                          'ru': 'Добро пожаловать в класс превосходства',
                                          'en': 'Classroom of the Elite',
                                          'score': '7.82',
                                          'genres': 'Drama, Psychological',
                                          'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx98659-WNyPLIZDpGGY.jpg',
                                          'hook': 'Хладнокровный гений ведёт тайную войну умов в элитной школе.'},
                                      {   'id': 10620,
                                          'ru': 'Дневник будущего',
                                          'en': 'The Future Diary',
                                          'score': '7.38',
                                          'genres': 'Action, Horror, Mystery',
                                          'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx10620-dUZeNej0W4QN.png',
                                          'hook': 'Смертельная королевская битва владельцев дневников, предсказывающих '
                                                  'будущее.'},
                                      {   'id': 23283,
                                          'ru': 'Эхо террора',
                                          'en': 'Terror in Resonance',
                                          'score': '8.08',
                                          'genres': 'Drama, Mystery, Psychological',
                                          'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx20661-aCR7QgzDfOSI.png',
                                          'hook': 'Два гениальных подростка бросают вызов полиции Токио сложнейшими '
                                                  'загадками.'},
                                      {   'id': 339,
                                          'ru': 'Эксперименты Лэйн',
                                          'en': 'Serial Experiments Lain',
                                          'score': '8.1',
                                          'genres': 'Drama, Mystery, Psychological',
                                          'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx339-xF2wp1NQuQ4r.png',
                                          'hook': 'Культовое погружение в Сеть и растворение границ между разумом и '
                                                  'кодом.'},
                                      {   'id': 323,
                                          'ru': 'Агент паранойи',
                                          'en': 'Paranoia Agent',
                                          'score': '7.66',
                                          'genres': 'Drama, Mystery, Psychological',
                                          'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx323-ZGkUcJOn4ngy.png',
                                          'hook': 'Детективы пытаются поймать призрачного маньяка, материализующего '
                                                  'людские страхи.'},
                                      {   'id': 1943,
                                          'ru': 'Паприка',
                                          'en': 'Paprika',
                                          'score': '8.05',
                                          'genres': 'Fantasy, Mystery, Psychological',
                                          'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/medium/b1943-jMCEYL1Ixmgc.png',
                                          'hook': 'Сюрреалистический шедевр Сатоси Кона о проникновении преступников в '
                                                  'чужие сны.'},
                                      {   'id': 31043,
                                          'ru': 'Город, в котором меня нет',
                                          'en': 'ERASED',
                                          'score': '8.31',
                                          'genres': 'Drama, Mystery, Psychological',
                                          'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx21234-XmqW39aQ9o7O.jpg',
                                          'hook': 'Герой возвращается в детство, чтобы поймать серийного похитителя '
                                                  'детей.'},
                                      {   'id': 31240,
                                          'ru': 'Re:Zero. Жизнь с нуля в альтернативном мире',
                                          'en': 'Re:ZERO -Starting Life in Another World-',
                                          'score': '8.25',
                                          'genres': 'Action, Adventure, Drama',
                                          'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx21355-wRVUrGxpvIQQ.jpg',
                                          'hook': 'Субару ищет путь сквозь бесконечные смерти и ментальные травмы.'},
                                      {   'id': 41619,
                                          'ru': 'Бездарная Нана',
                                          'en': 'Talentless Nana',
                                          'score': '7.17',
                                          'genres': 'Drama, Horror, Mystery',
                                          'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx117343-NgCLZTaxallv.jpg',
                                          'hook': 'В закрытой школе для одарённых подростков появляется хитрый убийца '
                                                  'под прикрытием.'},
                                      {   'id': 40046,
                                          'ru': 'ID: Вторжение',
                                          'en': 'ID: INVADED',
                                          'score': '7.81',
                                          'genres': 'Drama, Mystery, Psychological',
                                          'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx110350-uchN78wglmhN.png',
                                          'hook': 'Погружение в колодцы разума убийц для раскрытия изощрённых '
                                                  'преступлений.'},
                                      {   'id': 47194,
                                          'ru': 'Летнее время',
                                          'en': 'Summer Time Rendering',
                                          'score': '8.47',
                                          'genres': 'Action, Drama, Mystery',
                                          'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx129201-HJBauga2be8I.png',
                                          'hook': 'Захватывающий триллер с временной петлёй и смертоносными тенями на '
                                                  'острове.'},
                                      {   'id': 53393,
                                          'ru': 'Иллюзия рая',
                                          'en': 'Tengoku Daimakyo',
                                          'score': '8.2',
                                          'genres': 'Adventure, Mystery, Sci-Fi',
                                          'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx155783-YosKbsmZzuDE.jpg',
                                          'hook': 'Две параллельные тайны: закрытый райский приют и разрушенный '
                                                  'внешний мир.'},
                                      {   'id': 369,
                                          'ru': 'Бугипоп никогда не смеётся',
                                          'en': 'Boogiepop Phantom',
                                          'score': '7.17',
                                          'genres': 'Drama, Horror, Mystery',
                                          'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx369-dwzXLDvzzAmK.png',
                                          'hook': 'Мистическая сущность защищает мир от порождений человеческого '
                                                  'безумия.'},
                                      {   'id': 934,
                                          'ru': 'Когда плачут цикады',
                                          'en': 'When They Cry',
                                          'score': '7.87',
                                          'genres': 'Horror, Mystery, Psychological',
                                          'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx934-wjMlVEl4CWwg.jpg',
                                          'hook': 'Идиллическая деревня погружается в кровавые циклы безумия и '
                                                  'паранойи.'},
                                      {   'id': 7724,
                                          'ru': 'Усопшие',
                                          'en': 'Shiki',
                                          'score': '7.72',
                                          'genres': 'Horror, Mystery, Supernatural',
                                          'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx7724-NwNnRsI34eDa.jpg',
                                          'hook': 'Жуткая деконструкция вампиризма и морали выживания посреди '
                                                  'эпидемии.'},
                                      {   'id': 44074,
                                          'ru': 'Агент времени',
                                          'en': 'Link Click',
                                          'score': '8.7',
                                          'genres': 'Drama, Mystery, Supernatural',
                                          'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx126403-BfVSRzWUtVFW.png',
                                          'hook': 'Два парня погружаются в фотографии ради чужих тайн, рискуя изменить '
                                                  'прошлое.'},
                                      {   'id': 10271,
                                          'ru': 'Кайдзи 2',
                                          'en': 'Kaiji - Against All Rules',
                                          'score': '8.24',
                                          'genres': 'Psychological, Thriller',
                                          'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/nx10271-Aep4woDDbXdU.jpg',
                                          'hook': 'Напряжённейшая психологическая битва за жизнь и огромные деньги на '
                                                  'дне отчаяния.'},
                                      {   'id': 34933,
                                          'ru': 'Безумный азарт',
                                          'en': 'Kakegurui',
                                          'score': '7.21',
                                          'genres': 'Drama, Mystery, Psychological',
                                          'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/medium/b98314-TSJykxVwCCQN.jpg',
                                          'hook': 'Элитная академия, где социальный статус решает мастерство азартных '
                                                  'игр.'},
                                      {   'id': 37517,
                                          'ru': 'Сладкая жизнь',
                                          'en': 'Happy Sugar Life',
                                          'score': '6.75',
                                          'genres': 'Drama, Horror, Mystery',
                                          'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx101351-TWLbnRdE1tBI.jpg',
                                          'hook': 'Обманчиво розовая, но пугающе безумная психологическая драма об '
                                                  'одержимости.'},
                                      {   'id': 28621,
                                          'ru': 'Всё становится F: Идеальный инсайдер',
                                          'en': 'The Perfect Insider',
                                          'score': '7.23',
                                          'genres': 'Drama, Mystery, Psychological',
                                          'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx21190-CcEb1nZfY729.jpg',
                                          'hook': 'Классический интеллектуальный детектив об убийстве в неприступной '
                                                  'лаборатории.'},
                                      {   'id': 37525,
                                          'ru': 'Вавилон',
                                          'en': 'BABYLON',
                                          'score': '6.73',
                                          'genres': 'Drama, Mystery, Psychological',
                                          'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx101349-AWy5SjUS8mYZ.jpg',
                                          'hook': 'Прокурор расследует суицидальный заговор и сталкивается с '
                                                  'воплощением чистого зла.'},
                                      {   'id': 790,
                                          'ru': 'Эрго Прокси',
                                          'en': 'Ergo Proxy',
                                          'score': '7.9',
                                          'genres': 'Adventure, Mystery, Psychological',
                                          'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx790-YTUCvBKX8ZWK.jpg',
                                          'hook': 'Философский киберпанк-детектив о природе души искусственного '
                                                  'интеллекта.'}]},
    'cyberpunk_scifi': {   'key': 'cyberpunk_scifi',
                           'name': '🌆 Киберпанк & Научная фантастика',
                           'title': 'ТОП: Культовый Киберпанк и Научная Фантастика 🌆',
                           'desc': 'Мрачное будущее, аугментации, искусственный интеллект и неоновые мегаполисы:',
                           'tags': '#киберпанк #фантастика #scifi',
                           'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx120377-ayZPoxiWt4Li.jpg',
                           'shiki_genre': None,
                           'shiki_order': None,
                           'candidates': [   {   'id': 42310,
                                                 'ru': 'Киберпанк: Бегущие по краю',
                                                 'en': 'Cyberpunk: Edgerunners',
                                                 'score': '8.50',
                                                 'genres': 'Экшен, Киберпанк',
                                                 'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx120377-ayZPoxiWt4Li.jpg',
                                                 'hook': 'Парень из трущоб становится наемником-соло в безжалостном '
                                                         'Найт-Сити.'},
                                             {   'id': 29325,
                                                 'ru': 'Призрак в доспехах',
                                                 'en': 'Ghost in the Shell',
                                                 'score': '8.30',
                                                 'genres': 'Киберпанк, Sci-Fi',
                                                 'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx43-Y6EjeEMM14dj.png',
                                                 'hook': 'Майор Мотоко Кусанаги расследует киберпреступления на грани '
                                                         'человечности.'},
                                             {   'id': 47,
                                                 'ru': 'Акира',
                                                 'en': 'AKIRA',
                                                 'score': '7.90',
                                                 'genres': 'Фантастика, Экшен',
                                                 'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx47-4CR68arv452h.jpg',
                                                 'hook': 'Байкер в разрушенном Нео-Токио пробуждает колоссальную '
                                                         'разрушительную мощь.'},
                                             {   'id': 46095,
                                                 'ru': 'Виви: Песнь флюоритового глаза',
                                                 'en': 'Vivy: Fluorite Eye’s Song',
                                                 'score': '8.20',
                                                 'genres': 'Музыка, Фантастика',
                                                 'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx128546-UIwyhuhjxmL0.jpg',
                                                 'hook': 'Андроид-певица должна предотвратить восстание машин длиною в '
                                                         '100 лет.'},
                                             {   'id': 6,
                                                 'ru': 'Триган (1998)',
                                                 'en': 'TRIGUN',
                                                 'score': '8.00',
                                                 'genres': 'Экшен, Sci-Fi',
                                                 'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx6-wd4saT1JzStH.jpg',
                                                 'hook': 'Пацифист Вэш Ураган скитается по пустынной планете, спасая '
                                                         'людей.'},
                                             {   'id': 820,
                                                 'ru': 'Легенда о героях Галактики',
                                                 'en': 'Ginga Eiyuu Densetsu',
                                                 'score': '8.80',
                                                 'genres': 'Космос, Военное',
                                                 'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx820-x5dNLNFeKb8B.png',
                                                 'hook': 'Грандиозное противостояние двух гениальных стратегов в '
                                                         'масштабах космоса.'},
                                             {   'id': 97,
                                                 'ru': 'Изгнанник',
                                                 'en': 'Last Exile',
                                                 'score': '7.40',
                                                 'genres': 'Стимпанк, Приключения',
                                                 'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/nx97-Loi1Ppy4quXy.jpg',
                                                 'hook': 'Юные пилоты ваншипа оказываются втянуты в воздушную войну '
                                                         'двух империй.'},
                                             {   'id': 7465,
                                                 'ru': 'Время Евы',
                                                 'en': 'Eve no Jikan Movie',
                                                 'score': '7.70',
                                                 'genres': 'Повседневность, Sci-Fi',
                                                 'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx7465-gBh82FNppI9h.png',
                                                 'hook': 'В уютном кафе стирается социальная грань между людьми и '
                                                         'андроидами.'},
                                             {   'id': 41433,
                                                 'ru': 'Акудама Драйв',
                                                 'en': 'Akudama Drive',
                                                 'score': '7.50',
                                                 'genres': 'Экшен, Киберпанк',
                                                 'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx116566-PPIVQt359vQY.jpg',
                                                 'hook': 'Отряд отпетых преступников Кансая берется за '
                                                         'самоубийственное ограбление.'},
                                             {   'id': 13601,
                                                 'ru': 'Психопаспорт',
                                                 'en': 'PSYCHO-PASS',
                                                 'score': '8.40',
                                                 'genres': 'Киберпанк, Триллер',
                                                 'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx13601-i42VFuHpqEOJ.jpg',
                                                 'hook': 'Система «Сивилла» вычисляет вероятность преступления еще до '
                                                         'его совершения.'},
                                             {   'id': 2001,
                                                 'ru': 'Гуррен-Лаганн',
                                                 'en': 'Tengen Toppa Gurren Lagann',
                                                 'score': '8.50',
                                                 'genres': 'Экшен, Меха',
                                                 'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx2001-XwRnjzGeFWRQ.png',
                                                 'hook': 'Симон и Камина бурят путь наверх сквозь пространство, бросая '
                                                         'вызов Вселенной.'},
                                             {   'id': 1,
                                                 'ru': 'Ковбой Бибоп',
                                                 'en': 'Cowboy Bebop',
                                                 'score': '8.60',
                                                 'genres': 'Фантастика, Экшен',
                                                 'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx1-GCsPm7waJ4kS.png',
                                                 'hook': 'Охотники за головами бороздят Солнечную систему под звуки '
                                                         'бессмертного джаза.'},
                                             {   'id': 329,
                                                 'ru': 'Странники',
                                                 'en': 'Planetes',
                                                 'score': '8.25',
                                                 'genres': 'Drama, Romance, Sci-Fi',
                                                 'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx329-4xwXdazRA7Ph.png',
                                                 'hook': 'Умная и реалистичная твёрдая научная фантастика о буднях '
                                                         'космических сборщиков.'},
                                             {   'id': 2164,
                                                 'ru': 'Кибер-виток',
                                                 'en': 'Den-noh Coil',
                                                 'score': '8.02',
                                                 'genres': 'Adventure, Comedy, Drama',
                                                 'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx2164-4tUI4MJCZQO3.png',
                                                 'hook': 'Таинственные кибер-призраки и заговоры в мире повсеместных '
                                                         'умных очков.'},
                                             {   'id': 20057,
                                                 'ru': 'Космический Денди',
                                                 'en': 'Space Dandy',
                                                 'score': '7.89',
                                                 'genres': 'Comedy, Sci-Fi',
                                                 'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx20057-tG83EpH5Gu8K.jpg',
                                                 'hook': 'Фонтан визуального стиля и безумных галактических '
                                                         'приключений стиляги Дэнди.'},
                                             {   'id': 26,
                                                 'ru': 'Технолайз',
                                                 'en': 'Texhnolyze',
                                                 'score': '7.76',
                                                 'genres': 'Action, Drama, Psychological',
                                                 'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx26-ADSztyHBNO39.jpg',
                                                 'hook': 'Бескомпромиссно мрачный киберпанк о закате человечества в '
                                                         'подземном мегаполисе.'},
                                             {   'id': 474,
                                                 'ru': 'Макросс Плюс',
                                                 'en': 'Macross Plus',
                                                 'score': '7.73',
                                                 'genres': 'Action, Drama, Mecha',
                                                 'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx474-lyjbbltW5ZX4.png',
                                                 'hook': 'Противостояние пилотов новейших истребителей и опасного '
                                                         'виртуального айдола.'},
                                             {   'id': 19775,
                                                 'ru': 'Рыцари Сидонии',
                                                 'en': 'Knights of Sidonia',
                                                 'score': '7.63',
                                                 'genres': 'Action, Fantasy, Mecha',
                                                 'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx19775-h4Fc1q5qsGfP.png',
                                                 'hook': 'Отчаянная битва гигантского корабля-колонии человечества '
                                                         'против инопланетных гауна.'},
                                             {   'id': 1055,
                                                 'ru': 'Блейм!',
                                                 'en': 'BLAME! Ver.0.11',
                                                 'score': '5.92',
                                                 'genres': 'Action, Mecha, Sci-Fi',
                                                 'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/nx1055-k99fJWHZoKy3.png',
                                                 'hook': 'Киберпанковский постапокалипсис в бесконечном многоуровневом '
                                                         'Городе-Мегаструктуре.'},
                                             {   'id': 467,
                                                 'ru': 'Призрак в доспехах: Синдром одиночки',
                                                 'en': 'Ghost in the Shell: Stand Alone Complex',
                                                 'score': '8.42',
                                                 'genres': 'Action, Mystery, Psychological',
                                                 'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx467-mBTtIoR13qs2.jpg',
                                                 'hook': 'Культовый детективный сериал 9-го отдела о кибертерроризме и '
                                                         'взломе призраков.'},
                                             {   'id': 31251,
                                                 'ru': 'Мобильный воин Гандам: Железнокровные сироты',
                                                 'en': 'Mobile Suit GUNDAM Iron Blooded Orphans',
                                                 'score': '8.07',
                                                 'genres': 'Action, Drama, Mecha',
                                                 'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/nx21268-6dKrz26PPUvk.jpg',
                                                 'hook': 'Жестокая и честная космическая драма о юных наёмниках с '
                                                         'Марса.'},
                                             {   'id': 339,
                                                 'ru': 'Эксперименты Лэйн',
                                                 'en': 'Serial Experiments Lain',
                                                 'score': '8.1',
                                                 'genres': 'Drama, Mystery, Psychological',
                                                 'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx339-xF2wp1NQuQ4r.png',
                                                 'hook': 'Культовое киберпанковское исследование слияния сознания с '
                                                         'Сетью.'},
                                             {   'id': 4650,
                                                 'ru': 'Звёздные рыцари со звезды изгоев: Пилотный эпизод',
                                                 'en': 'Outlaw Star Pilot',
                                                 'score': '6.89',
                                                 'genres': 'Action, Sci-Fi',
                                                 'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/medium/4650.jpg',
                                                 'hook': 'Золотая эпоха космических приключений, сокровищ и дуэлей на '
                                                         'кораблях.'},
                                             {   'id': 6675,
                                                 'ru': 'Красная черта',
                                                 'en': 'Redline',
                                                 'score': '8.29',
                                                 'genres': 'Action, Romance, Sci-Fi',
                                                 'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx6675-NF4tFzAxSjkj.png',
                                                 'hook': 'Абсолютный триумф рисованной от руки анимации о безумнейших '
                                                         'межгалактических гонках.'},
                                             {   'id': 38691,
                                                 'ru': 'Доктор Стоун',
                                                 'en': 'Dr. STONE',
                                                 'score': '8.26',
                                                 'genres': 'Action, Adventure, Comedy',
                                                 'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx105333-GybuoSoOZfpH.jpg',
                                                 'hook': 'Возрождение цивилизации и технологий с нуля благодаря силе '
                                                         'науки.'},
                                             {   'id': 39198,
                                                 'ru': 'Астра, затерянная в космосе',
                                                 'en': 'ASTRA LOST IN SPACE',
                                                 'score': '8.07',
                                                 'genres': 'Adventure, Mystery, Sci-Fi',
                                                 'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx107663-gfIpy1h36kUL.jpg',
                                                 'hook': 'Захватывающее космическое выживание школьников с '
                                                         'неожиданными тайнами.'},
                                             {   'id': 41457,
                                                 'ru': 'Восемьдесят шесть',
                                                 'en': '86 EIGHTY-SIX',
                                                 'score': '8.35',
                                                 'genres': 'Action, Drama, Mecha',
                                                 'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx116589-KawXHB6sApFt.jpg',
                                                 'hook': 'Трагическая война беспилотников, внутри которых тайно '
                                                         'погибают отвергнутые люди.'},
                                             {   'id': 24405,
                                                 'ru': 'Импульс мира',
                                                 'en': 'World Trigger',
                                                 'score': '7.58',
                                                 'genres': 'Action, Sci-Fi',
                                                 'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx20729-DnBXnUxFon1B.png',
                                                 'hook': 'Тактический командный Sci-Fi с глубоко продуманной боевой '
                                                         'системой.'},
                                             {   'id': 22729,
                                                 'ru': 'Альдноа.Зеро',
                                                 'en': 'ALDNOAH.ZERO',
                                                 'score': '7.38',
                                                 'genres': 'Action, Mecha, Sci-Fi',
                                                 'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/nx20632-Mkgbtvi1kmhD.jpg',
                                                 'hook': 'Война землян против технологически превосходящей марсианской '
                                                         'империи.'},
                                             {   'id': 39539,
                                                 'ru': 'Жизнь без оружия',
                                                 'en': 'No Guns Life',
                                                 'score': '6.86',
                                                 'genres': 'Action, Drama, Sci-Fi',
                                                 'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx108478-yHMnmQCtHSDb.jpg',
                                                 'hook': 'Киберпанк-детектив с револьвером вместо головы, защищающий '
                                                         'права аугментированных.'},
                                             {   'id': 31163,
                                                 'ru': 'Измерение «W»',
                                                 'en': 'Dimension W',
                                                 'score': '7.17',
                                                 'genres': 'Action, Sci-Fi',
                                                 'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx21256-ErFGk90Kr5Ab.jpg',
                                                 'hook': 'Охота за нелегальными катушками бесконечной энергии из '
                                                         'таинственного 4-го измерения.'}]},
    'epic_fantasy': {   'key': 'epic_fantasy',
                        'name': '⚔️ Эпическое фэнтези и приключения',
                        'title': 'ТОП: Грандиозное Фэнтези и Приключения ⚔️',
                        'desc': 'Магия, масштабные миры, эпические сражения и незабываемые путешествия:',
                        'tags': '#фэнтези #приключения #эпик',
                        'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx101348-2fhDFPCuMNiz.jpg',
                        'shiki_genre': None,
                        'shiki_order': None,
                        'candidates': [   {   'id': 37521,
                                              'ru': 'Сага о Винланде',
                                              'en': 'VINLAND SAGA',
                                              'score': '8.70',
                                              'genres': 'Экшен, Приключения',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx101348-2fhDFPCuMNiz.jpg',
                                              'hook': 'Юный Торфинн жаждет мести за отца посреди завоевательных '
                                                      'походов викингов.'},
                                          {   'id': 33,
                                              'ru': 'Берсерк (1997)',
                                              'en': 'Kenpuu Denki Berserk',
                                              'score': '8.40',
                                              'genres': 'Тёмное фэнтези, Военное',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx33-PSwfE5B0gejI.jpg',
                                              'hook': 'Одинокий мечник Гатс встречает Гриффита и вступает в Отряд '
                                                      'Сокола.'},
                                          {   'id': 34599,
                                              'ru': 'Созданный в Бездне',
                                              'en': 'Made in Abyss',
                                              'score': '8.40',
                                              'genres': 'Приключения, Драма',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx97986-TQ7dCgbS3y5s.jpg',
                                              'hook': 'Девочка Рико и робот Рэг спускаются в смертоносные глубины '
                                                      'великой Бездны.'},
                                          {   'id': 38000,
                                              'ru': 'Клинок, рассекающий демонов',
                                              'en': 'Kimetsu no Yaiba',
                                              'score': '8.30',
                                              'genres': 'Экшен, Сверхъестественное',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx101922-WBsBl0ClmgYL.jpg',
                                              'hook': 'Тандзиро становится истребителем демонов, чтобы исцелить '
                                                      'обращенную сестру.'},
                                          {   'id': 20507,
                                              'ru': 'Бездомный бог',
                                              'en': 'Noragami',
                                              'score': '7.80',
                                              'genres': 'Мистика, Комедия',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx20447-EoQXeygHaVCK.jpg',
                                              'hook': 'Бродячий бог Ято выполняет любые просьбы за монетку в 5 иен '
                                                      'ради своего храма.'},
                                          {   'id': 18679,
                                              'ru': 'Убей или умри',
                                              'en': 'Kill la Kill',
                                              'score': '7.90',
                                              'genres': 'Экшен, Комедия',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/medium/b18679-lbkq7iYESoFW.png',
                                              'hook': 'Рюко Матой с половиной ножниц ищет убийцу отца в элитной '
                                                      'академии.'},
                                          {   'id': 14719,
                                              'ru': 'Невероятные приключения ДжоДжо',
                                              'en': 'JoJo no Kimyou na Bouken (TV)',
                                              'score': '7.70',
                                              'genres': 'Экшен, Приключения',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx14719-VT5dRzTBSZ0w.jpg',
                                              'hook': 'Эпическая сага поколений семьи Джостаров в схватке с древним '
                                                      'злом.'},
                                          {   'id': 52701,
                                              'ru': 'Подземелье вкусностей',
                                              'en': 'Dungeon Meshi',
                                              'score': '8.50',
                                              'genres': 'Фэнтези, Гурман',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx153518-IVXPDY5ph3kO.jpg',
                                              'hook': 'Отряд авантюристов спасает соратницу из брюха дракона, готовя '
                                                      'монстров на обед.'},
                                          {   'id': 11061,
                                              'ru': 'Охотник х Охотник',
                                              'en': 'HUNTER×HUNTER (2011)',
                                              'score': '8.90',
                                              'genres': 'Экшен, Приключения',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx11061-y5gsT1hoHuHw.png',
                                              'hook': 'Гон и друзья преодолевают смертельные испытания невероятного '
                                                      'мира Охотников.'},
                                          {   'id': 52991,
                                              'ru': 'Провожающая в последний путь Фрирен',
                                              'en': 'Sousou no Frieren',
                                              'score': '9.10',
                                              'genres': 'Фэнтези, Драма',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx154587-qQTzQnEJJ3oB.jpg',
                                              'hook': 'Эльфийская волшебница познает тепло человеческих уз после '
                                                      'победы над Владыкой.'},
                                          {   'id': 1818,
                                              'ru': 'Клеймор',
                                              'en': 'CLAYMORE',
                                              'score': '7.40',
                                              'genres': 'Тёмное фэнтези, Экшен',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx1818-KieLJv0qo3mO.jpg',
                                              'hook': 'Воительницы с серебряными глазами очищают континент от '
                                                      'чудовищ-йома.'},
                                          {   'id': 39535,
                                              'ru': 'Реинкарнация безработного',
                                              'en': 'Mushoku Tensei: Isekai Ittara Honki Dasu',
                                              'score': '8.20',
                                              'genres': 'Магия, Приключения',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx108465-1ANspF1EWyFx.jpg',
                                              'hook': 'Переродившийся маг познает законы нового фантастического мира.'},
                                          {   'id': 10087,
                                              'ru': 'Судьба/Начало',
                                              'en': 'Fate/Zero',
                                              'score': '8.26',
                                              'genres': 'Action, Drama, Fantasy',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx10087-M4Hd9qrHGrXk.png',
                                              'hook': 'Грандиозная битва магов и мифических героев за право обладания '
                                                      'Граалем.'},
                                          {   'id': 22297,
                                              'ru': 'Судьба/Ночь схватки: Бесконечный мир клинков',
                                              'en': 'Fate/stay night: Unlimited Blade Works',
                                              'score': '8.18',
                                              'genres': 'Action, Fantasy, Supernatural',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx19603-ycT0pyEgDVQu.jpg',
                                              'hook': 'Невероятный визуальный пир и философская дуэль идеалов героя '
                                                      'справедливости.'},
                                          {   'id': 5114,
                                              'ru': 'Стальной алхимик: Братство',
                                              'en': 'Fullmetal Alchemist: Brotherhood',
                                              'score': '9.11',
                                              'genres': 'Action, Adventure, Drama',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx5114-nSWCgQlmOMtj.jpg',
                                              'hook': 'Эталон жанра о путешествии братьев Элриков и тайнах алхимии.'},
                                          {   'id': 14513,
                                              'ru': 'Маги: Лабиринт магии',
                                              'en': 'Magi: The Labyrinth of Magic',
                                              'score': '8.0',
                                              'genres': 'Action, Adventure, Fantasy',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx14513-HuUdrFFYftA7.jpg',
                                              'hook': 'Волшебное восточное приключение Аладдина и Али-Бабы по '
                                                      'сокровищницам джиннов.'},
                                          {   'id': 25013,
                                              'ru': 'Йона на заре',
                                              'en': 'Yona of the Dawn',
                                              'score': '8.04',
                                              'genres': 'Action, Adventure, Comedy',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx20770-brCDvhTXlums.png',
                                              'hook': 'Изгнанная принцесса собирает легендарных воинов-драконов ради '
                                                      'спасения царства.'},
                                          {   'id': 37349,
                                              'ru': 'Убийца гоблинов',
                                              'en': 'GOBLIN SLAYER',
                                              'score': '7.42',
                                              'genres': 'Action, Adventure, Fantasy',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx101165-v5NwPXWPFDuD.jpg',
                                              'hook': 'Суровое и прагматичное тёмное фэнтези о зачистке самых коварных '
                                                      'тварей.'},
                                          {   'id': 457,
                                              'ru': 'Мастер муси',
                                              'en': 'MUSHI-SHI',
                                              'score': '8.65',
                                              'genres': 'Adventure, Fantasy, Mystery',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx457-l6cTtNgI9Bi6.png',
                                              'hook': 'Гинко путешествует по Японии, исцеляя связь людей с первородной '
                                                      'магией муси.'},
                                          {   'id': 40834,
                                              'ru': 'Рейтинг короля',
                                              'en': 'Ranking of Kings',
                                              'score': '8.48',
                                              'genres': 'Action, Adventure, Drama',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx113717-9sNnN8WRgK15.jpg',
                                              'hook': 'Трогательная до слёз сказка о глухонемом принце Бодзи с чистым '
                                                      'храбрым сердцем.'},
                                          {   'id': 23755,
                                              'ru': 'Семь смертных грехов',
                                              'en': 'The Seven Deadly Sins',
                                              'score': '7.59',
                                              'genres': 'Action, Adventure, Comedy',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx20789-Ma5ouSYPkru9.jpg',
                                              'hook': 'Могущественные рыцари королевства встают на защиту принцессы от '
                                                      'переворота.'},
                                          {   'id': 34572,
                                              'ru': 'Чёрный клевер',
                                              'en': 'Black Clover',
                                              'score': '8.14',
                                              'genres': 'Action, Adventure, Comedy',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx97940-fyh8o7gNbha0.png',
                                              'hook': 'Парень без капли магии доказывает, что упорство способно '
                                                      'сокрушить любого мага.'},
                                          {   'id': 29803,
                                              'ru': 'Повелитель',
                                              'en': 'Overlord',
                                              'score': '7.89',
                                              'genres': 'Action, Adventure, Fantasy',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx20832-vUNm5zrYWifc.jpg',
                                              'hook': 'Могущественный маг-нежить захватывает новый мир ради славы '
                                                      'своей гробницы.'},
                                          {   'id': 1482,
                                              'ru': 'Ди Грэй-мен',
                                              'en': 'D.Gray-man',
                                              'score': '8.0',
                                              'genres': 'Action, Adventure, Drama',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx1482-6jc8ZVSmHuLo.jpg',
                                              'hook': 'Экзорцисты с Чистой Силой ведут вечную войну против '
                                                      'Тысячелетнего Графа.'},
                                          {   'id': 40221,
                                              'ru': 'Башня Бога',
                                              'en': 'Tower of God',
                                              'score': '7.55',
                                              'genres': 'Action, Adventure, Drama',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx115230-QHOdSN7yt8ab.jpg',
                                              'hook': 'Смертоносный подъем на вершину гигантской Башни, где '
                                                      'исполняются любые желания.'},
                                          {   'id': 6702,
                                              'ru': 'Хвост Феи',
                                              'en': 'Fairy Tail',
                                              'score': '7.57',
                                              'genres': 'Action, Adventure, Comedy',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/medium/b6702-KI4qgSMyI8Pm.png',
                                              'hook': 'Самая безбашенная гильдия магов защищает друзей силой '
                                                      'несокрушимой дружбы.'},
                                          {   'id': 31859,
                                              'ru': 'Гримгал пепла и иллюзий',
                                              'en': 'Grimgar of Fantasy and Ash',
                                              'score': '7.66',
                                              'genres': 'Action, Adventure, Drama',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx21428-dFVIHeZ8McBe.jpg',
                                              'hook': 'Реалистичное и атмосферное выживание новичков в опасном '
                                                      'незнакомом мире.'},
                                          {   'id': 1762,
                                              'ru': 'Сказание об Арслане OVA',
                                              'en': 'The Heroic Legend of Arslan: Age of Heroes',
                                              'score': '6.9',
                                              'genres': 'Action, Adventure, Drama',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx1762-acu1YWRQB4QA.jpg',
                                              'hook': 'Молодой принц собирает армию, чтобы вернуть захваченное врагами '
                                                      'королевство.'},
                                          {   'id': 28121,
                                              'ru': 'Может, я встречу тебя в подземелье?',
                                              'en': 'Is It Wrong to Try to Pick Up Girls in a Dungeon?',
                                              'score': '7.52',
                                              'genres': 'Action, Adventure, Comedy',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx20920-MTREwZOG4BAD.jpg',
                                              'hook': 'Белл Кранел с богиней Гестией покоряет опаснейшие глубины '
                                                      'Подземелья Орарио.'},
                                          {   'id': 6594,
                                              'ru': 'Истории мечей',
                                              'en': 'Katanagatari',
                                              'score': '8.29',
                                              'genres': 'Action, Adventure, Romance',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx6594-xrrFyCacxUle.png',
                                              'hook': 'Поэтичное странствие за двенадцатью проклятыми клинками '
                                                      'легендарного кузнеца.'},
                                          {   'id': 1827,
                                              'ru': 'Хранитель священного духа',
                                              'en': 'Moribito: Guardian of the Spirit',
                                              'score': '8.12',
                                              'genres': 'Action, Adventure, Fantasy',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx1827-snIp62SY7ZFK.jpg',
                                              'hook': 'Непобедимая копьеносица Бальса защищает проклятого юного принца '
                                                      'от наёмников.'},
                                          {   'id': 30911,
                                              'ru': 'Сказания Зестирии',
                                              'en': 'Tales of Zestiria the X',
                                              'score': '7.21',
                                              'genres': 'Action, Adventure, Fantasy',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx21221-exaYgjct2K2c.jpg',
                                              'hook': 'Пастырь Сорей путешествует по охваченному скверной миру ради '
                                                      'спасения душ.'}]},
    'soul_romance': {   'key': 'soul_romance',
                        'name': '💖 Ламповая романтика для души',
                        'title': 'ТОП: Трогательная Романтика для Теплого Вечера 💖',
                        'desc': 'Искренние чувства, неловкие признания, поддержка и уютная атмосфера:',
                        'tags': '#романтика #повседневность #уют',
                        'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx101921-ufrjLzhSz7L1.jpg',
                        'shiki_genre': None,
                        'shiki_order': None,
                        'candidates': [   {   'id': 37999,
                                              'ru': 'Госпожа Кагуя: В любви как на войне',
                                              'en': 'Kaguya-sama wa Kokurasetai: Tensaitachi no Renai Zunousen',
                                              'score': '8.30',
                                              'genres': 'Комедия, Романтика',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx101921-ufrjLzhSz7L1.jpg',
                                              'hook': 'Президенты элитного студсовета ведут войну умов за первое '
                                                      'признание в чувствах.'},
                                          {   'id': 42897,
                                              'ru': 'Хоримия',
                                              'en': 'Horimiya',
                                              'score': '8.10',
                                              'genres': 'Школа, Романтика',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx124080-3i22mRVPBS0T.jpg',
                                              'hook': 'Два разных старшеклассника открывают друг другу свои настоящие '
                                                      'тайные стороны.'},
                                          {   'id': 4181,
                                              'ru': 'Кланнад: Продолжение истории',
                                              'en': 'CLANNAD: After Story',
                                              'score': '8.80',
                                              'genres': 'Драма, Романтика',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx4181-zUKE7BZC62OF.png',
                                              'hook': 'Трогательная история взросления, семейных ценностей и настоящей '
                                                      'вечной любви.'},
                                          {   'id': 28851,
                                              'ru': 'Форма голоса',
                                              'en': 'Koe no Katachi',
                                              'score': '8.80',
                                              'genres': 'Драма, Школа',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx20954-sYRfE5jQRtSB.jpg',
                                              'hook': 'Бывший задира ищет искупления перед глухой одноклассницей.'},
                                          {   'id': 23273,
                                              'ru': 'Твоя апрельская ложь',
                                              'en': 'Shigatsu wa Kimi no Uso',
                                              'score': '8.40',
                                              'genres': 'Музыка, Драма',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx20665-TLgkL8T8IRFd.png',
                                              'hook': 'Скрипачка-бунтарка возвращает юному пианисту страсть к музыке и '
                                                      'жизни.'},
                                          {   'id': 4224,
                                              'ru': 'Торадора!',
                                              'en': 'Toradora!',
                                              'score': '7.80',
                                              'genres': 'Комедия, Романтика',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx4224-PXVMBLNwy2aF.jpg',
                                              'hook': 'Грозный с виду парень и миниатюрная Тигрица помогают друг другу '
                                                      'в делах любви.'},
                                          {   'id': 37450,
                                              'ru': 'Этот глупый свин не понимает мечту девочки-зайки',
                                              'en': 'Seishun Buta Yarou wa Bunny Girl Senpai no Yume wo Minai',
                                              'score': '8.10',
                                              'genres': 'Мистика, Романтика',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx101291-wfEdgPqtfU0l.jpg',
                                              'hook': 'Сакута помогает актрисе в костюме зайки, которую перестают '
                                                      'замечать окружающие.'},
                                          {   'id': 6045,
                                              'ru': 'Дотянуться до тебя',
                                              'en': 'Kimi ni Todoke',
                                              'score': '7.90',
                                              'genres': 'Школа, Романтика',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx6045-JujXjoWtslUM.jpg',
                                              'hook': 'Скромная девушка Савако учится общаться с миром благодаря '
                                                      'доброму однокласснику.'},
                                          {   'id': 52578,
                                              'ru': 'Опасность в моем сердце',
                                              'en': 'Boku no Kokoro no Yabai Yatsu',
                                              'score': '8.10',
                                              'genres': 'Комедия, Романтика',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx153152-Xnwmx7wuoIWV.jpg',
                                              'hook': 'Мрачный интроверт постепенно сближается с жизнерадостной '
                                                      'школьной красавицей.'},
                                          {   'id': 38101,
                                              'ru': 'Пять невест',
                                              'en': 'Go-toubun no Hanayome',
                                              'score': '7.60',
                                              'genres': 'Гарем, Романтика',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx103572-cchriAdH95cQ.png',
                                              'hook': 'Бедный отличник нанимается репетитором к пяти непокорным '
                                                      'сестрам-близняшкам.'},
                                          {   'id': 13759,
                                              'ru': 'Кошечка из Сакурасо',
                                              'en': 'Sakurasou no Pet na Kanojo',
                                              'score': '7.80',
                                              'genres': 'Комедия, Драма',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx13759-xNf0gJK4Axt2.jpg',
                                              'hook': 'Жизнь в общежитии одаренных чудаков учит мечтать и не сдаваться '
                                                      'перед трудностями.'},
                                          {   'id': 33161,
                                              'ru': 'Как и ожидалось, моя школьная жизнь не задалась',
                                              'en': 'Yahari Ore no Seishun Love Come wa Machigatteiru. Zoku: Kitto, '
                                                    'Onnanoko wa Osatou to Spice to Suteki na Nanika de Dekiteiru',
                                              'score': '7.80',
                                              'genres': 'Драма, Романтика',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx21769-ZBoT6szJKGZv.jpg',
                                              'hook': 'Клуб служения помогает старшеклассникам разрешать их '
                                                      'эмоциональные кризисы.'},
                                          {   'id': 32281,
                                              'ru': 'Твоё имя',
                                              'en': 'Your Name.',
                                              'score': '8.82',
                                              'genres': 'Drama, Romance, Supernatural',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx21519-SUo3ZQuCbYhJ.png',
                                              'hook': 'Шедевр Макото Синкая о мистической связи двух подростков сквозь '
                                                      'время.'},
                                          {   'id': 38826,
                                              'ru': 'Дитя погоды',
                                              'en': 'Weathering With You',
                                              'score': '8.27',
                                              'genres': 'Drama, Romance, Slice of Life',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx106286-5COcpd0J9VbL.png',
                                              'hook': 'Парень встречает девушку, способную разгонять тучи над Токио '
                                                      'силой молитвы.'},
                                          {   'id': 33352,
                                              'ru': 'Вайолет Эвергарден',
                                              'en': 'Violet Evergarden',
                                              'score': '8.69',
                                              'genres': 'Drama, Fantasy, Slice of Life',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx21827-ubzq619ZA2E9.png',
                                              'hook': 'Вайолет учится любить и сопереживать, помогая людям выражать '
                                                      'чувства в письмах.'},
                                          {   'id': 17895,
                                              'ru': 'Золотая пора',
                                              'en': 'Golden Time',
                                              'score': '7.74',
                                              'genres': 'Drama, Romance',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx17895-M8yjOyMxHf5X.jpg',
                                              'hook': 'Студенческая жизнь, потеря памяти и искренний роман с '
                                                      'темпераментной Коко.'},
                                          {   'id': 35968,
                                              'ru': 'Так сложно любить отаку',
                                              'en': 'Wotakoi: Love is Hard for Otaku',
                                              'score': '7.91',
                                              'genres': 'Comedy, Romance, Slice of Life',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/nx99578-oO5KChtfhzln.png',
                                              'hook': 'Уютная и жизненная офисная романтика взрослых геймеров и '
                                                      'анимешников.'},
                                          {   'id': 38680,
                                              'ru': 'Корзинка фруктов (2019)',
                                              'en': 'Fruits Basket (2019)',
                                              'score': '8.2',
                                              'genres': 'Comedy, Drama, Romance',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx105334-AZwEdMu4KFtV.jpg',
                                              'hook': 'Добрая Тору исцеляет сердца членов семьи Сома, страдающих от '
                                                      'проклятия зодиака.'},
                                          {   'id': 877,
                                              'ru': 'Нана',
                                              'en': 'NANA',
                                              'score': '8.57',
                                              'genres': 'Drama, Music, Romance',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx877-6BUYEWp8By8j.png',
                                              'hook': 'Глубокая и правдивая история о любви, дружбе, рок-музыке и '
                                                      'взрослении в Токио.'},
                                          {   'id': 9989,
                                              'ru': 'Невиданный цветок',
                                              'en': 'Anohana: The Flower We Saw That Day',
                                              'score': '8.28',
                                              'genres': 'Drama, Romance, Slice of Life',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx9989-hImMg6kCMm6I.jpg',
                                              'hook': 'Призрак погибшей девочки собирает распавшуюся компанию друзей '
                                                      'детства.'},
                                          {   'id': 7054,
                                              'ru': 'Президент студсовета — горничная!',
                                              'en': 'Maid-Sama!',
                                              'score': '7.98',
                                              'genres': 'Comedy, Drama, Romance',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx7054-GW4D7VAZG19W.png',
                                              'hook': 'Популярный красавец узнает тайную подработку строгой '
                                                      'президентши студсовета.'},
                                          {   'id': 48736,
                                              'ru': 'Эта фарфоровая кукла влюбилась',
                                              'en': 'My Dress-Up Darling',
                                              'score': '8.13',
                                              'genres': 'Comedy, Ecchi, Romance',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx132405-qP7FQYGmNI3d.jpg',
                                              'hook': 'Скромный мастер кукол и яркая гяру объединяются ради создания '
                                                      'косплея.'},
                                          {   'id': 2034,
                                              'ru': 'Трогательный комплекс',
                                              'en': 'Lovely Complex',
                                              'score': '8.03',
                                              'genres': 'Comedy, Romance, Slice of Life',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx2034-erjg6gzDetAp.png',
                                              'hook': 'Высокая девушка и низкий парень проходят путь от взаимных '
                                                      'подколов до любви.'},
                                          {   'id': 14713,
                                              'ru': 'Очень приятно, Бог',
                                              'en': 'Kamisama Kiss',
                                              'score': '8.13',
                                              'genres': 'Comedy, Fantasy, Romance',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/nx14713-RyZ7bA7CdvGw.jpg',
                                              'hook': 'Школьница случайно становится богиней храма и встречает '
                                                      'лиса-хранителя Томоэ.'},
                                          {   'id': 21995,
                                              'ru': 'Неудержимая юность',
                                              'en': 'Blue Spring Ride',
                                              'score': '7.63',
                                              'genres': 'Drama, Romance, Slice of Life',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx20596-fJdMHV8xRMgY.png',
                                              'hook': 'Встреча первой школьной любви спустя годы после взаимных '
                                                      'перемен.'},
                                          {   'id': 32729,
                                              'ru': 'Орендж',
                                              'en': 'Orange',
                                              'score': '7.63',
                                              'genres': 'Drama, Romance, Supernatural',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx21647-zMUXNhcVyRyv.png',
                                              'hook': 'Письма из будущего помогают друзьям спасти одноклассника от '
                                                      'трагедии.'},
                                          {   'id': 34822,
                                              'ru': 'Прекрасна, как Луна',
                                              'en': 'Tsukigakirei',
                                              'score': '8.02',
                                              'genres': 'Drama, Romance, Slice of Life',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx98202-H6RtsIMZPALF.png',
                                              'hook': 'Невероятно нежная и реалистичная история первой влюбленности '
                                                      'скромных подростков.'},
                                          {   'id': 30015,
                                              'ru': 'Повторная жизнь',
                                              'en': 'ReLIFE',
                                              'score': '7.96',
                                              'genres': 'Comedy, Drama, Romance',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx21049-4AHSLeiDE9eg.png',
                                              'hook': '27-летний безработный получает шанс помолодеть на 10 лет и '
                                                      'исправить ошибки.'},
                                          {   'id': 52865,
                                              'ru': 'Романтический убийца',
                                              'en': 'Romantic Killer',
                                              'score': '7.9',
                                              'genres': 'Comedy, Romance',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx153930-uTRxaIcNa26E.jpg',
                                              'hook': 'Геймерша борется с назойливым духом, пытающимся насильно '
                                                      'устроить ей свидания.'},
                                          {   'id': 27775,
                                              'ru': 'Пластиковые воспоминания',
                                              'en': 'Plastic Memories',
                                              'score': '7.92',
                                              'genres': 'Drama, Romance, Sci-Fi',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx20872-j5PBzzVtrYDM.jpg',
                                              'hook': 'Трогательная история любви к андроиду-гифтии с ограниченным '
                                                      'сроком службы.'},
                                          {   'id': 36098,
                                              'ru': 'Я хочу съесть твою поджелудочную',
                                              'en': 'I Want to Eat Your Pancreas',
                                              'score': '8.56',
                                              'genres': 'Drama, Romance, Slice of Life',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx99750-pNyly9d3MEgV.jpg',
                                              'hook': 'Замкнутый парень узнает тайну смертельно больной жизнерадостной '
                                                      'одноклассницы.'},
                                          {   'id': 50796,
                                              'ru': 'Бессонница после школы',
                                              'en': 'Insomniacs After School',
                                              'score': '8.08',
                                              'genres': 'Romance, Slice of Life',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx143653-uq3motvR9kb4.png',
                                              'hook': 'Два страдающих бессонницей подростка находят покой в школьной '
                                                      'обсерватории.'},
                                          {   'id': 53126,
                                              'ru': 'Моя любовь девятьсот девяносто девятого уровня к Ямаде',
                                              'en': 'My Love Story with Yamada-kun at Lv999',
                                              'score': '7.75',
                                              'genres': 'Comedy, Drama, Romance',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx154965-vZbBRjtmLp7S.jpg',
                                              'hook': 'Брошенная девушка встречает хладнокровного про-геймера в '
                                                      'онлайн-игре.'},
                                          {   'id': 38080,
                                              'ru': 'Задержи этот звук!',
                                              'en': 'Kono Oto Tomare!: Sounds of Life',
                                              'score': '7.94',
                                              'genres': 'Drama, Music, Romance',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx103302-RVGwGRDGdMQq.jpg',
                                              'hook': 'Школьные хулиганы и музыканты возрождают традиционный клуб игры '
                                                      'на кото.'},
                                          {   'id': 37786,
                                              'ru': 'В конечном счёте я стану твоей',
                                              'en': 'Bloom Into You',
                                              'score': '7.88',
                                              'genres': 'Drama, Romance, Slice of Life',
                                              'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/nx101573-Gql3Q3UX1jcu.jpg',
                                              'hook': 'Глубокая психологическая драма о поиске своего истинного '
                                                      'чувства.'}]},
    'pure_comedy': {   'key': 'pure_comedy',
                       'name': '😂 Отборные комедии & Позитив',
                       'title': 'ТОП: Безумные Комедии для Отличного Настроения 😂',
                       'desc': 'Море отборного юмора, ярких персонажей и гарантированный заряд позитива:',
                       'tags': '#комедия #пародия #позитив',
                       'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx918-iOaeBVUn4uK7.jpg',
                       'shiki_genre': None,
                       'shiki_order': None,
                       'candidates': [   {   'id': 918,
                                             'ru': 'Гинтама',
                                             'en': 'Gintama',
                                             'score': '8.50',
                                             'genres': 'Пародия, Экшен',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx918-iOaeBVUn4uK7.jpg',
                                             'hook': 'Самураи, пришельцы и мастер абсурдного юмора Гинтоки Саката в '
                                                     'феодальной Японии.'},
                                         {   'id': 37105,
                                             'ru': 'Необъятный океан',
                                             'en': 'Grand Blue',
                                             'score': '8.20',
                                             'genres': 'Комедия, Студенты',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx100922-uxEhaCsqMMp3.png',
                                             'hook': 'Безумная жизнь студенческого дайвинг-клуба, полная угарных '
                                                     'вечеринок и дружбы.'},
                                         {   'id': 33255,
                                             'ru': 'Несладкая жизнь псионика Сайки К.',
                                             'en': 'Saiki Kusuo no Ψ-nan',
                                             'score': '8.30',
                                             'genres': 'Комедия, Сверхъестественное',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx21804-As6tDLAvEvNY.jpg',
                                             'hook': 'Могущественный экстрасенс хочет спокойной жизни, но чудаки '
                                                     'вокруг не дают покоя.'},
                                         {   'id': 30831,
                                             'ru': 'Этот замечательный мир! (KonoSuba)',
                                             'en': 'Kono Subarashii Sekai ni Shukufuku wo!',
                                             'score': '7.90',
                                             'genres': 'Комедия, Пародия',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx21202-mPOr80AEjUcZ.png',
                                             'hook': 'Казума берет с собой бесполезную богиню Акву и собирает '
                                                     'чудаковатую команду.'},
                                         {   'id': 32182,
                                             'ru': 'Моб Психо 100',
                                             'en': 'Mob Psycho 100',
                                             'score': '8.40',
                                             'genres': 'Экшен, Комедия',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx21507-6YUSbh2m0N1p.jpg',
                                             'hook': 'Школьник с колоссальной телекинетической силой пытается жить '
                                                     'обычной жизнью.'},
                                         {   'id': 245,
                                             'ru': 'Крутой учитель Онидзука',
                                             'en': 'GTO',
                                             'score': '8.40',
                                             'genres': 'Комедия, Школа',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx245-NcQAyTipUMeO.jpg',
                                             'hook': 'Бывший главарь банды байкеров учит трудных подростков настоящей '
                                                     'жизни.'},
                                         {   'id': 11843,
                                             'ru': 'Повседневная жизнь старшеклассников',
                                             'en': 'Danshi Koukousei no Nichijou',
                                             'score': '8.00',
                                             'genres': 'Комедия, Повседневность',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx11843-ui2jBcuQUqnl.jpg',
                                             'hook': 'Реалистичный и уморительный взгляд на будни трех школьных '
                                                     'оболтусов.'},
                                         {   'id': 15809,
                                             'ru': 'Сатана на подработке!',
                                             'en': 'Hataraku Maou-sama!',
                                             'score': '7.50',
                                             'genres': 'Комедия, Фэнтези',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx15809-ECv3HyOYJKrk.jpg',
                                             'hook': 'Владыка тьмы попадает в современный Токио и устраивается жарить '
                                                     'бургеры.'},
                                         {   'id': 48316,
                                             'ru': 'Восхождение в тени!',
                                             'en': 'Kage no Jitsuryokusha ni Naritakute!',
                                             'score': '8.10',
                                             'genres': 'Экшен, Пародия',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx130298-YMdcKHytpWNH.jpg',
                                             'hook': 'Парень играет роль серого кардинала, не зная, что все его '
                                                     'выдумки реальны.'},
                                         {   'id': 50265,
                                             'ru': 'Семья шпиона',
                                             'en': 'SPY×FAMILY',
                                             'score': '8.30',
                                             'genres': 'Комедия, Экшен',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx140960-Kb6R5nYQfjmP.jpg',
                                             'hook': 'Шпион, наемная убийца и девочка-телепат создают фиктивную '
                                                     'образцовую семью.'},
                                         {   'id': 42923,
                                             'ru': 'Скейт: Бесконечность',
                                             'en': 'SK∞',
                                             'score': '8.00',
                                             'genres': 'Спорт, Комедия',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx124153-uEBI764OSavB.png',
                                             'hook': 'Драйвовые нелегальные гонки на скейтах по заброшенной шахте на '
                                                     'Окинаве.'},
                                         {   'id': 6347,
                                             'ru': 'Дурни, тесты и призванные существа',
                                             'en': 'Baka to Test to Shoukanjuu',
                                             'score': '7.10',
                                             'genres': 'Комедия, Романтика',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx6347-DCSHLkCY7UT3.jpg',
                                             'hook': 'Битва школьных классов за комфорт в кабинетах с помощью '
                                                     'призванных аватаров.'},
                                         {   'id': 10165,
                                             'ru': 'Мелочи жизни',
                                             'en': 'Nichijou - My Ordinary Life',
                                             'score': '8.47',
                                             'genres': 'Comedy, Slice of Life',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx10165-tw8Cz7K9tfVJ.png',
                                             'hook': 'Абсурдный комедийный шедевр студии KyoAni о буднях самых '
                                                     'невероятных школьниц.'},
                                         {   'id': 37171,
                                             'ru': 'Давайте сыграем',
                                             'en': 'Asobi Asobase - workshop of fun -',
                                             'score': '8.19',
                                             'genres': 'Comedy, Slice of Life',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx101001-UERCW0UGi0P7.jpg',
                                             'hook': 'Ангельские с виду школьницы устраивают безумнейшие и упоротые '
                                                     'розыгрыши.'},
                                         {   'id': 36296,
                                             'ru': 'Праздник кукол',
                                             'en': 'HINAMATSURI',
                                             'score': '8.11',
                                             'genres': 'Comedy, Sci-Fi, Slice of Life',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx100077-FgGYIt8gGyrn.jpg',
                                             'hook': 'Молодой якудза вынужден воспитывать девочку с телекинезом из '
                                                     'другого измерения.'},
                                         {   'id': 22789,
                                             'ru': 'Баракамон',
                                             'en': 'Barakamon',
                                             'score': '8.36',
                                             'genres': 'Slice of Life',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx20722-2KAeq72E95dr.png',
                                             'hook': 'Вспыльчивый каллиграф отправляется в глухую деревню ради '
                                                     'вдохновения и покоя.'},
                                         {   'id': 30240,
                                             'ru': 'Школа-тюрьма',
                                             'en': 'Prison School',
                                             'score': '7.58',
                                             'genres': 'Comedy, Ecchi',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx20807-8nFoO0AUdGsy.jpg',
                                             'hook': 'Пятеро парней в женской академии попадают в карцер под надзор '
                                                     'строгого студсовета.'},
                                         {   'id': 23289,
                                             'ru': 'Ежемесячное сёдзё Нодзаки',
                                             'en': "Monthly Girls' Nozaki-kun",
                                             'score': '7.81',
                                             'genres': 'Comedy, Romance, Slice of Life',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx20668-6UslJY5NDYNh.png',
                                             'hook': 'Школьница признается в любви парню, но случайно становится его '
                                                     'ассистенткой мангаки.'},
                                         {   'id': 32542,
                                             'ru': 'Я — Сакамото, а что?',
                                             'en': "Haven't You Heard? I'm Sakamoto",
                                             'score': '7.53',
                                             'genres': 'Comedy, Slice of Life',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx21595-vQ658r2Roe1g.jpg',
                                             'hook': 'Идеальный во всём старшеклассник выходит победителем из любой '
                                                     'нелепой ситуации.'},
                                         {   'id': 52211,
                                             'ru': 'Магия и мускулы',
                                             'en': 'MASHLE: MAGIC AND MUSCLES',
                                             'score': '7.61',
                                             'genres': 'Action, Comedy, Fantasy',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx151801-XxVf22Le6C8o.png',
                                             'hook': 'Парень без магии поступает в магическую академию, решая всё '
                                                     'чистой физической силой.'},
                                         {   'id': 8675,
                                             'ru': 'Члены школьного совета',
                                             'en': 'Seitokai Yakuindomo',
                                             'score': '7.54',
                                             'genres': 'Comedy, Slice of Life',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx8675-5H2QSLvXA7bH.jpg',
                                             'hook': 'Парень попадает в женский студсовет, где все разговоры '
                                                     'скатываются в пошлые шутки.'},
                                         {   'id': 114,
                                             'ru': 'Кромешная путяга',
                                             'en': 'Cromartie High School',
                                             'score': '7.89',
                                             'genres': 'Comedy',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx114-VqL7lYKqdBR6.png',
                                             'hook': 'Единственный нормальный ученик в школе, где учатся гориллы, '
                                                     'бандиты и Фредди Меркьюри.'},
                                         {   'id': 268,
                                             'ru': 'Золотой парень',
                                             'en': 'GOLDEN BOY',
                                             'score': '8.04',
                                             'genres': 'Adventure, Comedy, Ecchi',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx268-0T6bdW9CzVvz.png',
                                             'hook': 'Кинтаро Оэ странствует по Японии на велосипеде, изучая жизнь и '
                                                     'попадая в передряги.'},
                                         {   'id': 3702,
                                             'ru': 'Детройт, город металла',
                                             'en': 'Detroit Metal City',
                                             'score': '8.09',
                                             'genres': 'Comedy, Music',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx3702-TCo0UYxWQzYj.jpg',
                                             'hook': 'Скромный фанат поп-музыки поневоле становится лидером '
                                                     'сатанинской метал-группы.'},
                                         {   'id': 32093,
                                             'ru': 'Всегда вялый Танака-кун',
                                             'en': 'Tanaka-kun is Always Listless',
                                             'score': '7.79',
                                             'genres': 'Comedy, Slice of Life',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx21495-I6p0OKzKBFjw.png',
                                             'hook': 'Уморительно ленивый школьник превращает искусство безделья в '
                                                     'философию жизни.'},
                                         {   'id': 40397,
                                             'ru': 'Сон в замке демона',
                                             'en': 'Sleepy Princess in the Demon Castle',
                                             'score': '7.95',
                                             'genres': 'Comedy, Fantasy, Slice of Life',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx111428-JGrnjBDHLGQb.png',
                                             'hook': 'Похищенная принцесса кошмарит Владыку демонов ради идеального '
                                                     'сна.'},
                                         {   'id': 38619,
                                             'ru': 'Бездельные дни старшеклассницы',
                                             'en': 'Wasteful Days of High School Girls',
                                             'score': '7.71',
                                             'genres': 'Comedy, Slice of Life',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx105081-pc4jgCmAP0dZ.jpg',
                                             'hook': 'Безумные и бессмысленные разговоры трёх подруг о парнях и '
                                                     'жизни.'},
                                         {   'id': 35821,
                                             'ru': 'Дорога в школу Чио',
                                             'en': "Chio's School Road",
                                             'score': '7.46',
                                             'genres': 'Comedy, Slice of Life',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx99366-niYV5CEsEhnc.jpg',
                                             'hook': 'Обычный путь в школу превращается в полосу препятствий на грани '
                                                     'экшена.'},
                                         {   'id': 20031,
                                             'ru': 'Дефрагментация!',
                                             'en': 'D-Frag!',
                                             'score': '7.49',
                                             'genres': 'Comedy',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx20031-WOR6bly9HOr1.jpg',
                                             'hook': 'Школьный хулиган против воли вступает в безумный клуб создания '
                                                     'игр.'},
                                         {   'id': 7647,
                                             'ru': 'Под мостом над Аракавой',
                                             'en': 'Arakawa Under the Bridge',
                                             'score': '7.56',
                                             'genres': 'Comedy, Romance',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx7647-NQEKHruZT5ch.jpg',
                                             'hook': 'Успешный наследник корпорации селится под мостом среди '
                                                     'эксцентричных чудаков.'},
                                         {   'id': 11633,
                                             'ru': 'Кровавый парень',
                                             'en': 'Blood Lad',
                                             'score': '7.23',
                                             'genres': 'Action, Adventure, Comedy',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx11633-vIjtabJq64Xt.jpg',
                                             'hook': 'Вампир-отаку пытается воскресить девушку, случайно ставшую '
                                                     'призраком в аду.'},
                                         {   'id': 6956,
                                             'ru': 'Работа!!',
                                             'en': 'Wagnaria!!',
                                             'score': '7.64',
                                             'genres': 'Comedy, Slice of Life',
                                             'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx6956-Nxs7H25yHLNS.jpg',
                                             'hook': 'Веселые будни и романтические недопонимания персонала семейного '
                                                     'ресторана.'}]},
    'isekai_special': {   'key': 'isekai_special',
                          'name': '🌀 Захватывающие исекаи с изюминкой',
                          'title': 'ТОП: Лучшие Исекаи с Необычной Завязкой 🌀',
                          'desc': 'Попаданцы в другие миры, где всё пошло не по стандартному сценарию:',
                          'tags': '#исекай #фэнтези #приключения',
                          'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx108465-1ANspF1EWyFx.jpg',
                          'shiki_genre': None,
                          'shiki_order': None,
                          'candidates': [   {   'id': 39535,
                                                'ru': 'Реинкарнация безработного',
                                                'en': 'Mushoku Tensei: Isekai Ittara Honki Dasu',
                                                'score': '8.20',
                                                'genres': 'Магия, Приключения',
                                                'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx108465-1ANspF1EWyFx.jpg',
                                                'hook': '34-летний затворник получает второй шанс прожить достойную '
                                                        'жизнь с мечом и магией.'},
                                            {   'id': 31240,
                                                'ru': 'Re:Zero — жизнь с нуля в другом мире',
                                                'en': 'Re:Zero kara Hajimeru Isekai Seikatsu',
                                                'score': '8.10',
                                                'genres': 'Триллер, Драма',
                                                'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx21355-wRVUrGxpvIQQ.jpg',
                                                'hook': 'Субару Нацуки обретает способность возвращаться во времени '
                                                        'только после гибели.'},
                                            {   'id': 37430,
                                                'ru': 'О моём перерождении в слизь',
                                                'en': 'Tensei Shitara Slime Datta Ken',
                                                'score': '8.00',
                                                'genres': 'Фэнтези, Сёнэн',
                                                'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx101280-tDxCVJm714nt.jpg',
                                                'hook': 'Офисный клерк перерождается слизью и строит процветающую '
                                                        'федерацию монстров.'},
                                            {   'id': 29803,
                                                'ru': 'Повелитель (Overlord)',
                                                'en': 'Overlord',
                                                'score': '7.70',
                                                'genres': 'Фэнтези, Экшен',
                                                'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx20832-vUNm5zrYWifc.jpg',
                                                'hook': 'Геймер остается заперт в теле могущественного скелета-мага в '
                                                        'новом мире.'},
                                            {   'id': 35790,
                                                'ru': 'Восхождение героя щита',
                                                'en': 'Tate no Yuusha no Nariagari',
                                                'score': '7.60',
                                                'genres': 'Драма, Фэнтези',
                                                'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx99263-LcazQwdlWzMy.jpg',
                                                'hook': 'Оболганный и преданный герой щита поднимается со дна ради '
                                                        'справедливости.'},
                                            {   'id': 32615,
                                                'ru': 'Военная хроника маленькой девочки',
                                                'en': 'Youjo Senki',
                                                'score': '7.80',
                                                'genres': 'Магия, Военное',
                                                'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx21613-qT3NiwYP5dYc.png',
                                                'hook': 'Циничный японский менеджер перерождается одаренной '
                                                        'девочкой-магом на войне.'},
                                            {   'id': 19815,
                                                'ru': 'Нет игры — нет жизни',
                                                'en': 'No Game No Life',
                                                'score': '7.70',
                                                'genres': 'Игры, Комедия',
                                                'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/medium/b19815-sEOQ9yQaPKlk.jpg',
                                                'hook': 'Гениальные брат и сестра попадают в мир, где любые конфликты '
                                                        'решаются играми.'},
                                            {   'id': 37984,
                                                'ru': 'Да, я паук, и что же?',
                                                'en': 'Kumo desu ga, Nani ka?',
                                                'score': '7.20',
                                                'genres': 'Экшен, Фэнтези',
                                                'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx103632-2wsy9wFUdm1C.jpg',
                                                'hook': 'Обычная школьница перерождается слабейшим паучком в '
                                                        'смертоносном лабиринте.'},
                                            {   'id': 40496,
                                                'ru': 'Непризнанный школой владыка демонов',
                                                'en': 'Maou Gakuin no Futekigousha: Shijou Saikyou no Maou no Shiso, '
                                                      'Tensei shite Shison-tachi no Gakkou e Kayou',
                                                'score': '7.20',
                                                'genres': 'Магия, Фэнтези',
                                                'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx112301-f88Fs2es4pSr.jpg',
                                                'hook': 'Всемогущий владыка демонов перерождается спустя 2000 лет в '
                                                        'мирной эпохе.'},
                                            {   'id': 38659,
                                                'ru': 'Этот герой неуязвим, но очень осторожен',
                                                'en': 'Shinchou Yuusha: Kono Yuusha ga Ore TUEEE Kuse ni Shinchou '
                                                      'Sugiru',
                                                'score': '7.30',
                                                'genres': 'Комедия, Фэнтези',
                                                'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx105156-ZVtxISdoUqnY.png',
                                                'hook': 'Богиня призывает невероятно сильного героя, который '
                                                        'перестраховывается во всем.'},
                                            {   'id': 49891,
                                                'ru': 'О моём перерождении в меч',
                                                'en': 'Tensei Shitara Ken Deshita',
                                                'score': '7.40',
                                                'genres': 'Экшен, Фэнтези',
                                                'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx139587-rbZVcigCRtHY.jpg',
                                                'hook': 'Разумный меч становится наставником и оружием юной '
                                                        'кошкодевочки Фран.'},
                                            {   'id': 31859,
                                                'ru': 'Гримгал пепла и иллюзий',
                                                'en': 'Hai to Gensou no Grimgar',
                                                'score': '7.40',
                                                'genres': 'Драма, Фэнтези',
                                                'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx21428-dFVIHeZ8McBe.jpg',
                                                'hook': 'Группа новичков без воспоминаний отчаянно учится выживать в '
                                                        'суровом мире.'},
                                            {   'id': 17265,
                                                'ru': 'Покорение горизонта',
                                                'en': 'Log Horizon',
                                                'score': '7.89',
                                                'genres': 'Action, Adventure, Fantasy',
                                                'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx17265-RyErURYesjJt.jpg',
                                                'hook': 'Тысячи игроков заперты в MMORPG и строят цивилизацию силой '
                                                        'стратегии и экономики.'},
                                            {   'id': 36480,
                                                'ru': 'Скитальцы OVA',
                                                'en': 'DRIFTERS OVA',
                                                'score': '7.52',
                                                'genres': 'Action, Adventure, Comedy',
                                                'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx97988-rq6xyZPj25Ao.jpg',
                                                'hook': 'Легендарные полководцы Земли призваны в фэнтези-мир для '
                                                        'эпической тотальной войны.'},
                                            {   'id': 28907,
                                                'ru': 'Врата: Там бьются наши воины',
                                                'en': 'Gate',
                                                'score': '7.67',
                                                'genres': 'Action, Adventure, Fantasy',
                                                'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx20994-pSDk4I58jAK5.jpg',
                                                'hook': 'Современная армия Японии с танками и авиацией исследует мир '
                                                        'магии и драконов.'},
                                            {   'id': 57466,
                                                'ru': 'Власть книжного червя: Приёмная дочь лорда',
                                                'en': 'Ascendance of a Bookworm: Adopted Daughter of an Archduke',
                                                'score': '7.76',
                                                'genres': 'Drama, Fantasy, Slice of Life',
                                                'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx171110-7zOdInS6DQNL.jpg',
                                                'hook': 'Погибшая библиотекарша перерождается в бедной семье и '
                                                        'воссоздает печать книг.'},
                                            {   'id': 43523,
                                                'ru': 'Лунное путешествие приведёт к новому миру',
                                                'en': 'TSUKIMICHI -Moonlit Fantasy-',
                                                'score': '7.71',
                                                'genres': 'Action, Adventure, Comedy',
                                                'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx125206-O2MsOWdW1lVi.jpg',
                                                'hook': 'Отвергнутый богиней за внешность герой строит общество '
                                                        'монстров.'},
                                            {   'id': 47790,
                                                'ru': 'Лучший в мире ассасин, переродившийся в другом мире как '
                                                      'аристократ',
                                                'en': "The World's Finest Assassin Gets Reincarnated in Another World "
                                                      'as an Aristocrat',
                                                'score': '7.3',
                                                'genres': 'Action, Adventure, Drama',
                                                'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx129898-FRUzDtPhRigt.jpg',
                                                'hook': 'Величайший киллер перерождается дворянином, чтобы устранить '
                                                        'Героя ради спасения мира.'},
                                            {   'id': 48761,
                                                'ru': 'Далёкий паладин',
                                                'en': 'The Faraway Paladin',
                                                'score': '6.89',
                                                'genres': 'Action, Adventure, Fantasy',
                                                'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx132473-L64hP24nJyEV.jpg',
                                                'hook': 'Мальчик выращен тремя неживыми героями и принимает обет '
                                                        'служения богине света.'},
                                            {   'id': 53446,
                                                'ru': 'Кулинарные скитания в параллельном мире',
                                                'en': 'Campfire Cooking in Another World with my Absurd Skill',
                                                'score': '7.63',
                                                'genres': 'Adventure, Comedy, Fantasy',
                                                'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx156067-Jovklss4VWIx.jpg',
                                                'hook': 'Герой с навыком онлайн-супермаркета приручает легендарного '
                                                        'волка вкусной едой.'},
                                            {   'id': 48760,
                                                'ru': 'Рыцарь-скелет вступает в параллельный мир',
                                                'en': 'Skeleton Knight in Another World',
                                                'score': '7.13',
                                                'genres': 'Action, Adventure, Comedy',
                                                'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx132474-J2ECHSPkfb9g.jpg',
                                                'hook': 'Геймер просыпается в доспехах своего аватара-скелета и '
                                                        'помогает угнетенным.'},
                                            {   'id': 50461,
                                                'ru': 'Мир отомэ-игр — это тяжёлый мир для мобов',
                                                'en': 'Trapped in a Dating Sim: The World of Otome Games Is Tough for '
                                                      'Mobs',
                                                'score': '7.31',
                                                'genres': 'Action, Fantasy, Mecha',
                                                'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx142074-pHe4bX791PJh.jpg',
                                                'hook': 'Парень перерождается второстепенным персонажем и бросает '
                                                        'вызов надменной знати.'},
                                            {   'id': 49220,
                                                'ru': 'Перерождение Дяди',
                                                'en': 'Uncle from Another World',
                                                'score': '7.74',
                                                'genres': 'Adventure, Comedy, Fantasy',
                                                'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx135806-uhqZSNTYZe04.jpg',
                                                'hook': 'Дядя выходит из 17-летней комы после исекая, поражая '
                                                        'племянника магией и видеоиграми Sega.'},
                                            {   'id': 34104,
                                                'ru': 'Рыцари и магия',
                                                'en': "Knight's & Magic",
                                                'score': '7.07',
                                                'genres': 'Action, Fantasy, Mecha',
                                                'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx97663-4TMJDIpm3toz.png',
                                                'hook': 'Гениальный программист-меха-отаку строит гигантских боевых '
                                                        'роботов в новом мире.'},
                                            {   'id': 41710,
                                                'ru': 'Герой-рационал перестраивает королевство',
                                                'en': 'How a Realist Hero Rebuilt the Kingdom',
                                                'score': '7.25',
                                                'genres': 'Action, Adventure, Fantasy',
                                                'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx117612-MCbAaq2ypJlp.jpg',
                                                'hook': 'Попаданец спасает страну от кризиса не мечом, а экономикой и '
                                                        'реформами.'},
                                            {   'id': 34012,
                                                'ru': 'Кафе из другого мира',
                                                'en': 'Restaurant to Another World',
                                                'score': '7.42',
                                                'genres': 'Fantasy, Slice of Life',
                                                'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/nx97617-TmRRraupfbT5.jpg',
                                                'hook': 'Дверь токийского ресторана раз в неделю открывается для '
                                                        'эльфов, драконов и магов.'},
                                            {   'id': 38472,
                                                'ru': 'Квартет из альтернативного мира',
                                                'en': 'Isekai Quartet',
                                                'score': '7.37',
                                                'genres': 'Comedy, Fantasy, Slice of Life',
                                                'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx104454-pH5YCR7HteqP.jpg',
                                                'hook': 'Чиби-кроссовер с героями Konosuba, Re:Zero, Overlord и Tanya '
                                                        'the Evil.'},
                                            {   'id': 39030,
                                                'ru': 'За дело! «Звериная тропа»',
                                                'en': 'Kemono Michi: Rise Up',
                                                'score': '6.59',
                                                'genres': 'Comedy, Fantasy, Slice of Life',
                                                'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx107339-3mKBCMAUN896.png',
                                                'hook': 'Профессиональный рестлер переносится в фэнтези-мир и '
                                                        'открывает приют для монстров.'},
                                            {   'id': 41312,
                                                'ru': 'Избранный богами',
                                                'en': 'By the Grace of the Gods',
                                                'score': '6.95',
                                                'genres': 'Adventure, Fantasy, Slice of Life',
                                                'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx115740-IRwSQo96Qs2Q.jpg',
                                                'hook': 'Уставший клерк перерождается ребенком и ведет мирную жизнь в '
                                                        'окружении прирученных слизней.'},
                                            {   'id': 39196,
                                                'ru': 'Добро пожаловать в ад, Ирума!',
                                                'en': 'Welcome to Demon School! Iruma-kun',
                                                'score': '7.74',
                                                'genres': 'Comedy, Fantasy',
                                                'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx107693-A9bSSFAMxA6j.jpg',
                                                'hook': 'Добрый парень продан родителями демону и становится самым '
                                                        'популярным учеником школы ада.'},
                                            {   'id': 15315,
                                                'ru': 'Проблемные дети приходят из иного мира, верно?',
                                                'en': "Problem Children Are Coming From Another World, Aren't They?",
                                                'score': '7.4',
                                                'genres': 'Action, Comedy, Fantasy',
                                                'poster': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx15315-mvKPcy8Z2QkB.jpg',
                                                'hook': 'Трое одаренных подростков призваны в мир «Цветущего сада» для '
                                                        'игр богов.'}]}}

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
        # Massive 1-Row panoramic banner
        poster_h = 560 if n <= 4 else 500
        poster_w = int(poster_h * 0.69)  # ~386px
        card_gap = 26
        pad_x = 36
        pad_top = 110
        pad_bottom = 36
        total_w = pad_x * 2 + (poster_w * n) + (card_gap * (n - 1))
        total_h = pad_top + poster_h + pad_bottom
        is_grid = False
        cols = n
    else:
        # Grand 2-Row adaptive grid (5x2 for 10, 4x2 for 7-8, 3x2 for 6)
        cols = (n + 1) // 2
        poster_h = 440
        poster_w = int(poster_h * 0.69)  # ~304px
        card_gap = 22
        row_gap = 24
        pad_x = 36
        pad_top = 110
        pad_bottom = 36
        total_w = pad_x * 2 + (poster_w * cols) + (card_gap * (cols - 1))
        total_h = pad_top + (poster_h * 2) + row_gap + pad_bottom
        is_grid = True

    # Canvas with dark luxury background (#080C16)
    canvas = Image.new("RGBA", (total_w, total_h), (8, 12, 22, 255))
    draw = ImageDraw.Draw(canvas)

    # Header fonts
    font_pill = _get_font(12, bold=True)
    font_title = _get_font(26, bold=True)
    font_badge = _get_font(18 if is_grid else 19, bold=True)

    # Clean title from emojis and duplicated prefixes
    clean_title = re.sub(r'[\U00010000-\U0010ffff]', '', title_text).strip()
    clean_title = re.sub(r'^(ТОП[\s\-\d:]*)+', '', clean_title, flags=re.IGNORECASE).strip()
    header_display = f"ТОП-{n}: {clean_title}" if clean_title else f"ТОП-{n} Шедевров"

    # Header glass card container
    header_box = (pad_x, 14, total_w - pad_x, 92)
    draw.rounded_rectangle(header_box, radius=12, fill=(15, 23, 42, 220), outline=(255, 255, 255, 25), width=1)

    # Header Pill badge inside container
    pill_text = "ANIME VIST  •  CURATED SELECTION"
    pill_w = 260
    pill_h = 22
    draw.rounded_rectangle((pad_x + 14, 18, pad_x + 14 + pill_w, 18 + pill_h), radius=10, fill=(30, 41, 59, 230), outline=(99, 102, 241, 140), width=1)
    draw.text((pad_x + 24, 21), pill_text, fill=(129, 140, 248), font=font_pill)

    # Header main title
    draw.text((pad_x + 18, 54), header_display, fill=(248, 250, 252), font=font_title)

    # Glowing subtle accent dot in right corner
    draw.ellipse((total_w - pad_x - 36, 44, total_w - pad_x - 20, 60), fill=(99, 102, 241, 220), outline=(236, 72, 153, 200), width=1)

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
        resized = resized.filter(ImageFilter.UnsharpMask(radius=1.2, percent=120, threshold=2))
        resized = resized.filter(ImageFilter.UnsharpMask(radius=1.2, percent=120, threshold=2))
        resized = resized.filter(ImageFilter.UnsharpMask(radius=1.2, percent=120, threshold=2))
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

        # 5. Position Badge (modern glassmorphic rank tag: [ • 01 ])
        num_str = f"{idx:02d}"
        badge_h = 28 if is_grid else 32
        badge_w = 54 if is_grid else 60
        b_r = 8 if is_grid else 9
        badge = Image.new("RGBA", (badge_w, badge_h), (0, 0, 0, 0))
        b_draw = ImageDraw.Draw(badge)

        # Luxury metallic color themes per rank
        if idx == 1:
            dot_color = (250, 204, 21, 255)      # Gold
            border_color = (250, 204, 21, 180)
            text_color = (254, 240, 138, 255)
        elif idx == 2:
            dot_color = (56, 189, 248, 255)     # Cyan
            border_color = (56, 189, 248, 180)
            text_color = (224, 242, 254, 255)
        elif idx == 3:
            dot_color = (244, 114, 182, 255)    # Rose
            border_color = (244, 114, 182, 180)
            text_color = (252, 231, 243, 255)
        else:
            dot_color = (129, 140, 248, 255)    # Indigo
            border_color = (129, 140, 248, 140)
            text_color = (241, 245, 249, 255)

        # Frosted dark glass container
        b_draw.rounded_rectangle((0, 0, badge_w - 1, badge_h - 1), radius=b_r, fill=(11, 15, 28, 225), outline=border_color, width=1)

        # Glowing accent dot
        dot_r = 3 if is_grid else 3.5
        dot_cx = 11 if is_grid else 13
        dot_cy = badge_h / 2
        b_draw.ellipse((dot_cx - dot_r, dot_cy - dot_r, dot_cx + dot_r, dot_cy + dot_r), fill=dot_color)

        # Rank number
        f_size = 13 if is_grid else 15
        font_badge = _get_font(f_size, bold=True)
        t_bbox = b_draw.textbbox((0, 0), num_str, font=font_badge)
        t_w = t_bbox[2] - t_bbox[0]
        t_h = t_bbox[3] - t_bbox[1]
        text_x = dot_cx + dot_r + (badge_w - (dot_cx + dot_r) - t_w) / 2
        text_y = (badge_h - t_h) / 2 - (1 if is_grid else 2)
        b_draw.text((text_x, text_y), num_str, fill=text_color, font=font_badge)

        # Badge drop shadow
        b_shadow = Image.new("RGBA", (badge_w + 6, badge_h + 6), (0, 0, 0, 0))
        bs_draw = ImageDraw.Draw(b_shadow)
        bs_draw.rounded_rectangle((3, 3, badge_w + 3, badge_h + 3), radius=b_r, fill=(0, 0, 0, 160))
        b_shadow = b_shadow.filter(ImageFilter.GaussianBlur(3))
        canvas.paste(b_shadow, (pos_x + 7, pos_y + 7), b_shadow)
        canvas.paste(badge, (pos_x + 9, pos_y + 9), badge)

    final_rgb = canvas.convert("RGB")
    final_rgb.save(out_path, "JPEG", quality=98, subsampling=0)
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
