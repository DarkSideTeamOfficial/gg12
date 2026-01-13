#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для получения рекомендаций по одежде через Google Gemini AI
"""

import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

# Инициализация клиента Gemini
_client = None

def _get_client():
    """Получение клиента Gemini (ленивая инициализация)"""
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return None
        _client = genai.Client(api_key=api_key)
    return _client


def get_weather_recommendations(weather_data: dict) -> str:
    """
    Получение рекомендаций по одежде на основе данных о погоде
    
    :param weather_data: Словарь с данными о погоде
    :return: Рекомендации по одежде или пустая строка при ошибке
    """
    client = _get_client()
    if not client:
        return ""  # Если API ключ не настроен, просто не показываем рекомендации
    
    try:
        # Формируем промпт для AI
        prompt = f"""Ты - помощник по выбору одежды. На основе данных о погоде дай краткие и практичные рекомендации (2-3 предложения).

Данные о погоде:
- Температура: {weather_data.get('temp_C', 'N/A')}°C
- Ощущается как: {weather_data.get('FeelsLikeC', 'N/A')}°C
- Погода: {weather_data.get('weather_desc', 'N/A')}
- Влажность: {weather_data.get('humidity', 'N/A')}%
- Ветер: {weather_data.get('windspeed', 'N/A')} км/ч
- Осадки: {weather_data.get('precipMM', '0')} мм

Дай рекомендации:
1. Какую одежду лучше надеть
2. Нужны ли аксессуары (зонт, шапка, перчатки и т.д.)
3. Общие советы

Отвечай кратко, дружелюбно, на русском языке. Без эмодзи в начале."""
        
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt,
        )
        
        return response.text.strip() if response.text else ""
    
    except Exception as e:
        # В случае ошибки просто не показываем рекомендации
        return ""


async def get_weather_recommendations_async(weather_data: dict) -> str:
    """
    Асинхронная версия получения рекомендаций
    (для использования в aiogram обработчиках)
    """
    import asyncio
    # Выполняем в executor, т.к. библиотека синхронная
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, get_weather_recommendations, weather_data)
