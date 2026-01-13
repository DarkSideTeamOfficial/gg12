#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для запуска Telegram бота прогноза погоды
"""

import asyncio
import sys
import os

# Добавляем текущую директорию в путь для импорта модулей
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from weather_bot import main

if __name__ == "__main__":
    print("🌤️ Запуск Telegram бота прогноза погоды...")
    print("=" * 50)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        sys.exit(1)
