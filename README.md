---
title: AnimeVist Telegram Bot & Dashboard
emoji: 🎬
colorFrom: blue
colorTo: slate
sdk: docker
app_port: 7860
pinned: false
---

# 🤖 AnimeVist Telegram Automation Bot & DevOps Console (24/7 Standalone)

Полностью автономный сервис и Telegram-бот для ведения официального канала **AnimeVist**, автопостинга серий (#release), новостей (#news), патчноутов (#patchnote) и закрепленного навигатора (FAQ/Pin).

Проект **на 100% отделён от клиентского приложения AnimeVist** — не требует React, Node.js или Electron, работает на чистой стандартной библиотеке Python 3 (0 сторонних зависимостей) и снабжён современной **веб-панелью управления (DevOps Console)** с защитой от сброса настроек на бесплатных облачных хостингах.

---

## ⚡ Актуальные бесплатные серверы БЕЗ привязки банковских карт

| Платформа | Модель работы | Банковская карта | Особенности & Вердикт |
| :--- | :--- | :---: | :--- |
| **Hugging Face Spaces (Docker)** | 24/7 Web + Bot | ❌ **Не нужна** | **ТОП-1 РЕКОМЕНДАЦИЯ.** 2 vCPU, 16 GB RAM бесплатно. Дает постоянный HTTPS-домен для веб-панели, контейнер **не засыпает**, деплой из GitHub за 2 минуты. |
| **Serv00.com (FreeBSD + SSH)** | 24/7 Хостинг | ❌ **Не нужна** | Полноценный Unix-хостинг с SSH, Python 3, Cron и поддержкой фоновых процессов. |
| **Alwaysdata.com** | 24/7 Хостинг | ❌ **Не нужна** | Французский хостинг (100 MB), SSH, Python, постоянный домен, фоновые демоны. |
| **Render.com** | Web Service | ❌ **Не нужна** (через GitHub) | 750 бесплатных часов. Засыпает через 15 мин бездействия (решается бесплатным внешним пингом раз в 10 мин с *cron-job.org*). |
| **Встроенный GitHub Actions** | Cron каждые 15 мин | ❌ **Не нужна** | Сервер не нужен вообще: `.github/workflows/auto_announcer.yml` запускается по расписанию в облаке GitHub бесплатно. |

---

## 💾 Решение проблемы эемерной файловой системы (Сохранение настроек)

На бесплатных облачных PaaS/контейнерах (Hugging Face Spaces, Render) локальная файловая система сбрасывается при каждом перезапуске контейнера. В сервисе реализованы 4 механизма сохранения:

1. **Telegram Cloud Storage (Рекомендуется — 0 внешних регистраций)**:
   * Бот использует закрытый служебный чат или ваш личный Telegram ID.
   * При сохранении настроек или истории серий бот отправляет и закрепляет защищенное сообщение `#ANIMEVIST_BOT_CONFIG_BACKUP`.
   * При старте бот автоматически считывает конфигурацию из Telegram. 100% бесплатно и навсегда!
2. **Переменные окружения (Environment Variables)**:
   * Вы можете передать параметры в настройках хостинга: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHANNEL_ID`, `CHECK_INTERVAL`, `STORAGE_CHAT_ID`.
3. **Upstash Redis (REST)**:
   * Бесплатный key-value сторадж без карт (10,000 запросов/день).
4. **Supabase (PostgreSQL REST)**:
   * Бесплатный тариф без карт.

---

## 🚀 Пошаговый запуск 24/7 в Hugging Face Spaces (2 минуты)

1. Зарегистрируйтесь на [**huggingface.co**](https://huggingface.co) (через GitHub, карта не требуется).
2. Нажмите **New Space**:
   * **Space name**: `animevist-bot`
   * **License**: `mit`
   * **Select the Space SDK**: выберите **Docker** (Blank).
3. Перейдите во вкладку **Settings** созданного Space:
   * В блоке **Connect GitHub repository** подключите ваш репозиторий `magver/AnimeVist-Telegram-Bot`.
   * В блоке **Variables and secrets** (при желании) можно добавить переменную `TELEGRAM_BOT_TOKEN` и `TELEGRAM_CHANNEL_ID`.
4. Hugging Face автоматически запустит контейнер и откроет веб-панель на адресе `https://<username>-animevist-bot.hf.space`. Бот работает **24/7 автономно**!

---

## 💻 Локальный запуск на Windows

1. Дважды кликните по файлу:
   * `start_web_dashboard.bat` — запуск современной веб-панели управления в браузере (`http://localhost:5000`).
   * `start_menu.bat` — интерактивное консольное меню управления.
   * `run_daemon.bat` — фоновый непрерывный мониторинг в терминале.

---

## 📂 Структура репозитория

```
AnimeVist-Telegram-Bot/
├── config.json                 # Локальный файл конфигурации (токен, канал, модули, storage)
├── web_dashboard.py            # Профессиональная веб-консоль управления + фоновый демон 24/7
├── telegram_sender.py          # Клиент Telegram Bot API + адаптеры облачного хранилища
├── main.py                     # CLI-хаб с флагами (--daemon, --test, --releases, --news)
├── series_announcer.py         # [Модуль 1] Автопостинг выхода новых серий (#release)
├── news_announcer.py           # [Модуль 2] Автопостинг аниме-новостей (#news)
├── patchnote_publisher.py      # [Модуль 3] Публикатор обновлений через GitHub Releases (#patchnote)
├── pinned_navigator.py         # [Модуль 4] Закрепленный навигатор и витрина (Pin FAQ)
│
├── Dockerfile                  # Готовый контейнер для Hugging Face Spaces / Docker
├── render.yaml                 # Конфигурация для Render.com
├── requirements.txt            # Список зависимостей (чистый Python, 0 внешних пакетов)
│
├── .github/workflows/          # Автоматизация в облаке GitHub Actions
│   ├── auto_announcer.yml      # Cron-таймер каждые 15 минут
│   └── manual_broadcast.yml    # Кнопки ручного запуска в интерфейсе GitHub
│
├── start_web_dashboard.bat     # Быстрый запуск веб-консоли на ПК
├── start_menu.bat              # Консольное меню Windows
├── run_daemon.bat              # Фоновый демон Windows
├── 1_post_episodes.bat         # Ручной запуск: Новые серии
├── 2_post_news.bat             # Ручной запуск: Новости
├── 3_publish_patchnote.bat     # Ручной запуск: Патчноут
└── 4_pin_navigator.bat         # Ручной запуск: Закрепить навигатор
```
