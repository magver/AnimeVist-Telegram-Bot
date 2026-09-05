"""
Standalone AnimeVist Automation Service & Telegram Bot.
Independent system for managing announcements, releases, news, and navigation.

Usage:
  python main.py                  - Интерактивная панель управления
  python main.py --daemon         - Непрерывный фоновый сервис 24/7 (для VPS или локально)
  python main.py --test           - Проверка подключения Telegram-бота
  python main.py --releases       - Разовый запуск проверки новых серий
  python main.py --news           - Разовый запуск проверки аниме-новостей
  python main.py --patchnote      - Опубликовать свежий релиз из GitHub
  python main.py --pinned         - Отправить и закрепить навигационный пост
"""

import os
import sys
import time
import argparse

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from telegram_sender import TelegramSender, load_config
from series_announcer import run_series_check
from news_announcer import run_news_check
from patchnote_publisher import publish_patchnote_from_github, publish_custom_patchnote
from pinned_navigator import publish_pinned_navigator, get_latest_version_from_github

def test_connection():
    print("\n[Проверка] Тестирование подключения Telegram-бота...")
    sender = TelegramSender()
    me = sender.get_me()
    if me.get('ok'):
        bot_user = me['result']
        print(f"✅ Успешное подключение к боту: @{bot_user.get('username')} ({bot_user.get('first_name')})")
        config = load_config()
        channel = config.get('telegram', {}).get('channel_id')
        print(f"📢 Целевой канал: {channel}")
        print("💡 Убедитесь, что бот добавлен в канал с правами Администратора (публикация и закрепление сообщений).")
        return True
    else:
        print(f"❌ Ошибка подключения к Telegram: {me.get('description')}")
        print("💡 Проверьте 'bot_token' в файле config.json")
        return False

def daemon_loop():
    config = load_config()
    interval = config.get('announcer', {}).get('check_interval_seconds', 300)
    app_name = config.get('app', {}).get('name', 'AnimeVist')

    print(f"\n=======================================================")
    print(f"  {app_name} Standalone Automation Daemon Запущен 24/7")
    print(f"  Интервал проверки: {interval} секунд")
    print(f"  Для остановки нажмите Ctrl+C")
    print(f"=======================================================\n")

    while True:
        try:
            now_str = time.strftime('%Y-%m-%d %H:%M:%S')
            print(f"[{now_str}] 🔍 Проверка выхода новых серий...")
            if config.get('announcer', {}).get('enable_series_releases', True):
                run_series_check()

            print(f"[{now_str}] 📰 Проверка новостей аниме-индустрии...")
            if config.get('announcer', {}).get('enable_anime_news', True):
                run_news_check()

        except KeyboardInterrupt:
            print("\n[Daemon] Остановка сервиса пользователем...")
            break
        except Exception as e:
            print(f"[Daemon] Исключение в цикле: {e}")

        print(f"Ожидание {interval} секунд перед следующим циклом...\n")
        time.sleep(interval)

def interactive_menu():
    config = load_config()
    app_name = config.get('app', {}).get('name', 'AnimeVist')

    while True:
        print("\n" + "="*56)
        print(f"   🤖 {app_name.upper()} STANDALONE BOT & AUTOMATION HUB")
        print("="*56)
        print("1. 📡 Запустить фоновый демон 24/7 (Серии + Новости)")
        print("2. 🔍 [Пункт 1] Проверить новые серии (#release) прямо сейчас")
        print("3. 📰 [Пункт 2] Проверить новости аниме (#news) прямо сейчас")
        print("4. 🚀 [Пункт 3] Опубликовать патчноут релиза (#patchnote)")
        print("5. 📌 [Пункт 4] Отправить и закрепить навигатор и FAQ (Pin)")
        print("6. 🔌 Проверить подключение бота к Telegram")
        print("0. ❌ Выход")
        print("="*56)

        choice = input("Выберите действие [0-6]: ").strip()
        if choice == '1':
            daemon_loop()
        elif choice == '2':
            run_series_check()
        elif choice == '3':
            run_news_check()
        elif choice == '4':
            print("\n1. Взять релиз автоматически из GitHub Releases")
            print("2. Ввести версию и описание вручную")
            sub = input("Выберите вариант [1-2]: ").strip()
            if sub == '1':
                publish_patchnote_from_github()
            elif sub == '2':
                v = input("Версия (например 1.0.30): ").strip()
                t = input("Заголовок релиза: ").strip() or "Обновление стабильности"
                print("Введите пункты 'Что нового' (пустая строка для завершения):")
                h_list = []
                while True:
                    line = input(" • ").strip()
                    if not line:
                        break
                    h_list.append(line)
                publish_custom_patchnote(version=v, title=t, highlights=h_list)
        elif choice == '5':
            confirm = input("Отправить и закрепить пост в канале? [y/N]: ").strip().lower()
            if confirm in ['y', 'yes', 'д', 'да']:
                publish_pinned_navigator()
        elif choice == '6':
            test_connection()
        elif choice == '0':
            print("Работа завершена.")
            break
        else:
            print("Неверный выбор, повторите ввод.")

def main():
    parser = argparse.ArgumentParser(description="Standalone AnimeVist Automation Service")
    parser.add_argument('--daemon', action='store_true', help="Run continuous monitoring daemon")
    parser.add_argument('--test', action='store_true', help="Test Telegram bot connection")
    parser.add_argument('--releases', action='store_true', help="Run single series check")
    parser.add_argument('--news', action='store_true', help="Run single news check")
    parser.add_argument('--patchnote', action='store_true', help="Publish latest patchnote from GitHub")
    parser.add_argument('--pinned', action='store_true', help="Publish pinned navigation post")

    args = parser.parse_args()

    if args.test:
        test_connection()
    elif args.daemon:
        daemon_loop()
    elif args.releases:
        run_series_check()
    elif args.news:
        run_news_check()
    elif args.patchnote:
        publish_patchnote_from_github()
    elif args.pinned:
        publish_pinned_navigator()
    else:
        interactive_menu()

if __name__ == '__main__':
    main()
