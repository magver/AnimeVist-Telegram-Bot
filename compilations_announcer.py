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
                                                    'гигантами-людоедами.'}]},
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
                                                     'царства.'}]},
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
                                                  'пришельцев-гауна.'}]},
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
                                                         'бессмертного джаза.'}]},
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
                                              'hook': 'Переродившийся маг познает законы нового фантастического '
                                                      'мира.'}]},
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
                                                      'эмоциональные кризисы.'}]},
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
                                                     'призванных аватаров.'}]},
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
                                                        'суровом мире.'}]}}

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
