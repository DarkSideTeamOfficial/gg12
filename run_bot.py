#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 Единственная точка входа для запуска Telegram бота

Этот файл:
- Запускает HTTP сервер для keep-alive на Render
- Запускает Telegram бота для обработки команд
- Запускает планировщик уведомлений

Использование:
    python run_bot.py
"""

import asyncio
import sys
import os
from aiohttp import web
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Добавляем текущую директорию в путь для импорта модулей
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from weather_bot import main, bot, BOT_TOKEN

# Keep-alive HTTP сервер для предотвращения засыпания на Render
async def health_check(request):
    """Endpoint для проверки здоровья сервиса"""
    return web.Response(text="Bot is running! 🌤️")

async def status(request):
    """Endpoint со статусом бота"""
    return web.json_response({
        "status": "online",
        "bot": "weather-bot",
        "message": "Бот работает и готов к приему команд"
    })

async def start_web_server():
    """Запуск веб-сервера для keep-alive"""
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    app.router.add_get('/status', status)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Render использует переменную PORT
    port = int(os.getenv('PORT', 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    print(f"🌐 HTTP сервер запущен на порту {port}")
    return runner

async def run_bot_with_server():
    """Запуск бота вместе с HTTP сервером"""
    print("🌤️ Запуск Telegram бота прогноза погоды...")
    print("=" * 50)
    
    runner = None
    try:
        # Запускаем HTTP сервер
        runner = await start_web_server()
        
        # Задержка перед запуском бота (чтобы старый экземпляр успел остановиться при деплое)
        # Render обычно дает ~10 секунд на graceful shutdown старому экземпляру
        print("⏳ Ожидание завершения предыдущего экземпляра (если есть)...")
        await asyncio.sleep(10)  # Увеличено до 10 секунд для надежности
        
        # Запускаем бота
        await main()
        
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if runner:
            print("🔄 Остановка HTTP сервера...")
            await runner.cleanup()

if __name__ == "__main__":
    # Проверяем наличие токена
    if not BOT_TOKEN:
        print("❌ Ошибка: Не указан токен бота!")
        print("Пожалуйста, создайте файл .env и укажите BOT_TOKEN=your_token_here")
        sys.exit(1)
    
    # Запускаем бота с HTTP сервером
    asyncio.run(run_bot_with_server())