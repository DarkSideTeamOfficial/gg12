#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для запуска Telegram бота прогноза погоды с HTTP keep-alive сервером
"""

import asyncio
import sys
import os
from aiohttp import web

# Добавляем текущую директорию в путь для импорта модулей
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from weather_bot import main, bot

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
    
    try:
        # Запускаем HTTP сервер
        runner = await start_web_server()
        
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
        if 'runner' in locals():
            await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(run_bot_with_server())