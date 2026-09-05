# 🤖 AnimeVist Telegram Automation Bot (Standalone)

Полностью автономный сервис и Telegram-бот для ведения официального канала **AnimeVist**, публикации серий, новостей, патчноутов и закрепленных сообщений.

Проект **на 100% отделён от основного приложения AnimeVist** — не имеет зависимостей от React, Electron или Capacitor, работает автономно через открытые API (GitHub Releases, AnimeVost, Shikimori, Telegram Bot API) и может быть развёрнут на любом сервере, VPS или запущен локально на Windows.

---

## 📂 Структура проекта

```
tg AnimeVist/
├── config.json                 # Главный конфиг (токен бота, канал, чат, тайминги)
├── main.py                     # Единый исполняемый файл (CLI и фоновый демон)
├── telegram_sender.py          # Клиент Telegram Bot API (отправка, авто-пин, редактирование)
├── series_announcer.py         # [Пункт 1] Автопостинг выхода новых серий (#release)
├── news_announcer.py           # [Пункт 2] Автопостинг аниме-новостей (#news)
├── patchnote_publisher.py      # [Пункт 3] Публикатор обновлений через GitHub Releases (#patchnote)
├── pinned_navigator.py         # [Пункт 4] Закрепленный навигатор и витрина (Pin)
│
├── start_menu.bat              # Запуск панели управления в 1 клик на Windows
├── run_daemon.bat              # Запуск непрерывного фонового сервиса 24/7 на Windows
├── 1_post_episodes.bat         # Запуск пункта 1 (Новые серии)
├── 2_post_news.bat             # Запуск пункта 2 (Новости)
├── 3_publish_patchnote.bat     # Запуск пункта 3 (Патчноут)
├── 4_pin_navigator.bat         # Запуск пункта 4 (Закрепить навигатор)
│
├── Dockerfile                  # Для запуска в Docker
├── docker-compose.yml          # Запуск в 1 команду: docker-compose up -d
└── animevist-bot.service       # systemd unit файл для Linux VPS
```

---

## ⚙️ Настройка (`config.json`)

Откройте `config.json` и укажите:
* `bot_token`: Токен вашего бота от `@BotFather`
* `channel_id`: Адрес вашего Telegram-канала (например `@animevist_official` или `-100...`)
* `discussion_chat_id`: Ссылка или ID чата обсуждений
* Добавьте бота в канал Администратором с правами:
  * ✅ *Публикация сообщений (Post Messages)*
  * ✅ *Закрепление сообщений (Pin Messages)*

---

## 🚀 Способы запуска

### 1. Локально на Windows (в 1 клик)
* **Панель управления**: дважды кликните по `start_menu.bat`.
* **Фоновый демон 24/7**: дважды кликните по `run_daemon.bat`.
* **Запуск любого из 4 пунктов по отдельности**: используйте файлы `1_post_episodes.bat`, `2_post_news.bat`, `3_publish_patchnote.bat`, `4_pin_navigator.bat`.

### 2. На сервере / VPS через Docker
```bash
docker-compose up -d --build
```

### 3. На Linux VPS через systemd
```bash
cp animevist-bot.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now animevist-bot
```
