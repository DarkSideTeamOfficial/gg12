#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для автоматической отправки уведомлений о погоде по расписанию
"""

import asyncio
import logging
from datetime import datetime, time
from aiogram import Bot
from database import db
from weather_functions import get_weather, get_detailed_weather, get_weather_json

class WeatherScheduler:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.is_running = False
        self.task = None
    
    async def start(self):
        """Запуск планировщика"""
        if self.is_running:
            return
        
        self.is_running = True
        self.task = asyncio.create_task(self._scheduler_loop())
        logging.info("🌤️ Планировщик погоды запущен")
    
    async def stop(self):
        """Остановка планировщика"""
        if not self.is_running:
            return
        
        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logging.info("🛑 Планировщик погоды остановлен")
    
    async def _scheduler_loop(self):
        """Основной цикл планировщика"""
        while self.is_running:
            try:
                # Получаем текущее время в формате HH:MM
                current_time = datetime.now().strftime("%H:%M")
                
                # Получаем пользователей для отправки уведомлений
                users = db.get_users_for_notification(current_time)
                
                if users:
                    logging.info(f"📤 Отправка уведомлений для {len(users)} пользователей в {current_time}")
                    
                    # Отправляем уведомления всем пользователям
                    for user in users:
                        await self._send_weather_notification(user)
                
                # Ждем 1 минуту до следующей проверки
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"❌ Ошибка в планировщике: {e}")
                await asyncio.sleep(60)  # Ждем минуту при ошибке
    
    async def _send_weather_notification(self, user_data: dict):
        """Отправка уведомления о погоде конкретному пользователю"""
        try:
            user_id = user_data['user_id']
            city = user_data['city']
            weather_type = user_data.get('weather_type', 'brief')
            
            # Определяем тип уведомления по времени
            current_time = datetime.now().strftime("%H:%M")
            is_morning = current_time == user_data.get('morning_time', '08:00')
            
            # Формируем сообщение
            if is_morning:
                greeting = "🌅 Доброе утро!"
            else:
                greeting = "🌙 Добрый вечер!"
            
            # Получаем данные о погоде
            if weather_type == 'detailed':
                weather_info = get_detailed_weather(city)
            else:
                weather_info = get_weather_json(city)
            
            # Отправляем сообщение
            message = f"{greeting}\n\n{weather_info}"
            await self.bot.send_message(user_id, message, parse_mode="Markdown")
            
            logging.info(f"✅ Уведомление отправлено пользователю {user_id} ({city})")
            
        except Exception as e:
            logging.error(f"❌ Ошибка при отправке уведомления пользователю {user_data.get('user_id', 'unknown')}: {e}")
    
    async def send_test_notification(self, user_id: int):
        """Отправка тестового уведомления пользователю"""
        try:
            user_data = db.get_user(user_id)
            if not user_data or not user_data.get('city'):
                await self.bot.send_message(user_id, "❌ Город не настроен. Используйте /subscribe для настройки.")
                return
            
            await self._send_weather_notification(user_data)
            
        except Exception as e:
            logging.error(f"❌ Ошибка при отправке тестового уведомления: {e}")
            await self.bot.send_message(user_id, f"❌ Ошибка при отправке уведомления: {e}")

# Глобальный экземпляр планировщика
scheduler = None

async def start_scheduler(bot: Bot):
    """Запуск планировщика"""
    global scheduler
    if scheduler is None:
        scheduler = WeatherScheduler(bot)
    await scheduler.start()

async def stop_scheduler():
    """Остановка планировщика"""
    global scheduler
    if scheduler:
        await scheduler.stop()

async def send_test_notification(bot: Bot, user_id: int):
    """Отправка тестового уведомления"""
    global scheduler
    if scheduler is None:
        scheduler = WeatherScheduler(bot)
    await scheduler.send_test_notification(user_id)
