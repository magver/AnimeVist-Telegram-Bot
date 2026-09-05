---
title: AnimeVist Telegram Bot & Dashboard
emoji: 🎬
colorFrom: cyan
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# 🤖 AnimeVist Telegram Automation Bot (Standalone)

Полностью автономный сервис и Telegram-бот для ведения официального канала **AnimeVist**, публикации серий, новостей, патчноутов и закрепленных сообщений.

Проект **на 100% отделён от основного приложения AnimeVist** — не имеет зависимостей от React, Electron или Capacitor, работает автономно через открытые API (GitHub Releases, AnimeVost, Shikimori, Telegram Bot API) и может быть развёрнут в облаке без кредитных карт или запущен локально на Windows.

---

## ☁️ Работа 24/7 без включенного ПК (100% БЕСПЛАТНО, БЕЗ КАРТЫ)

### Вариант 1: Встроенный GitHub Actions (0 настроек, 0 карт, уже работает!)
В репозитории уже настроен автоматический планировщик:
* **Автопостинг каждые 15 минут**: файл `.github/workflows/auto_announcer.yml` запускается на серверах GitHub круглосуточно без вашего участия.
* **Ручное управление**: перейдите во вкладку **Actions** в этом репозитории $\rightarrow$ выберите **«Manual Actions»** $\rightarrow$ нажмите **«Run workflow»** для запуска любого из 4 действий через красивый интерфейс GitHub прямо с телефона или компьютера.

### Вариант 2: Hugging Face Spaces (Полноценный веб-интерфейс 24/7 без карты)
1. Зарегистрируйтесь бесплатно на [**huggingface.co**](https://huggingface.co) (без карты, 30 секунд).
2. Нажмите **New Space** $\rightarrow$ выберите **Docker** (Blank).
3. Во вкладке Settings нажмите **«Connect to GitHub»** и выберите этот репозиторий (`AnimeVist-Telegram-Bot`).
4. Hugging Face запустит веб-интерфейс на постоянном адресе `https://huggingface.co/spaces/...`, который будет работать **24/7 круглый год бесплатно**!

---

## 📂 Структура проекта

```
tg AnimeVist/
├── config.json                 # Главный конфиг (токен бота, канал, чат, тайминги)
├── web_dashboard.py            # Визуальный веб-интерфейс управления + фоновый демон
├── main.py                     # Единый CLI-хаб
├── telegram_sender.py          # Клиент Telegram Bot API (отправка, авто-пин, редактирование)
├── series_announcer.py         # [Пункт 1] Автопостинг выхода новых серий (#release)
├── news_announcer.py           # [Пункт 2] Автопостинг аниме-новостей (#news)
├── patchnote_publisher.py      # [Пункт 3] Публикатор обновлений через GitHub Releases (#patchnote)
├── pinned_navigator.py         # [Пункт 4] Закрепленный навигатор и витрина (Pin)
│
├── .github/workflows/          # Автоматический запуск 24/7 в облаке GitHub (без карт!)
│   ├── auto_announcer.yml      # Таймер каждые 15 минут
│   └── manual_broadcast.yml    # Кнопки ручного запуска в интерфейсе GitHub
│
├── start_web_dashboard.bat     # Запуск веб-панели на ПК в браузере (http://localhost:5000)
├── start_menu.bat              # Консольное меню управления на Windows
├── run_daemon.bat              # Непрерывный фоновый мониторинг на Windows
├── 1_post_episodes.bat         # Ручной запуск: Новые серии
├── 2_post_news.bat             # Ручной запуск: Новости
├── 3_publish_patchnote.bat     # Ручной запуск: Патчноут
└── 4_pin_navigator.bat         # Ручной запуск: Закрепить навигатор
```
