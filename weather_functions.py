#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль с функциями для получения прогноза погоды через wttr.in API
"""

import requests
from datetime import datetime
from typing import Optional

# Константы
API_BASE_URL = "https://wttr.in"
REQUEST_TIMEOUT = 30
WEEKDAYS_RU = {
    'Monday': 'Понедельник',
    'Tuesday': 'Вторник',
    'Wednesday': 'Среда',
    'Thursday': 'Четверг',
    'Friday': 'Пятница',
    'Saturday': 'Суббота',
    'Sunday': 'Воскресенье'
}

# Перевод направлений ветра на русский
WIND_DIRECTIONS_RU = {
    'N': 'С', 'NNE': 'ССВ', 'NE': 'СВ', 'ENE': 'ВСВ',
    'E': 'В', 'ESE': 'ВЮВ', 'SE': 'ЮВ', 'SSE': 'ЮЮВ',
    'S': 'Ю', 'SSW': 'ЮЮЗ', 'SW': 'ЮЗ', 'WSW': 'ЗЮЗ',
    'W': 'З', 'WNW': 'ЗСЗ', 'NW': 'СЗ', 'NNW': 'ССЗ'
}


def _make_request(url: str) -> Optional[requests.Response]:
    """Базовая функция для выполнения HTTP запроса"""
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        return response if response.status_code == 200 else None
    except requests.exceptions.RequestException as e:
        return None


def _format_date(date_str: str) -> str:
    """Форматирование даты в читаемый вид"""
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        weekday_en = date_obj.strftime('%A')
        weekday_ru = WEEKDAYS_RU.get(weekday_en, weekday_en)
        return date_obj.strftime(f'%d.%m.%Y ({weekday_ru})')
    except:
        return date_str


def _translate_wind_direction(wind_dir: str) -> str:
    """Перевод направления ветра на русский"""
    return WIND_DIRECTIONS_RU.get(wind_dir, wind_dir)


def get_weather_data_dict(city: str) -> dict:
    """Получение данных о погоде в виде словаря для AI рекомендаций"""
    url = f"{API_BASE_URL}/{city}?lang=ru&format=j1"
    response = _make_request(url)
    
    if not response:
        return {}
    
    try:
        data = response.json()
        current = data['current_condition'][0]
        
        weather_desc_ru = current.get('lang_ru', [{}])[0].get('value', '')
        if not weather_desc_ru:
            weather_desc_ru = current['weatherDesc'][0]['value']
        
        return {
            'temp_C': current.get('temp_C', ''),
            'FeelsLikeC': current.get('FeelsLikeC', ''),
            'weather_desc': weather_desc_ru,
            'humidity': current.get('humidity', ''),
            'windspeed': current.get('windspeedKmph', ''),
            'precipMM': current.get('precipMM', '0'),
            'winddir': _translate_wind_direction(current.get('winddir16Point', ''))
        }
    except:
        return {}


def get_weather(city: str) -> str:
    """Получение краткого прогноза погоды"""
    url = f"{API_BASE_URL}/{city}?lang=ru&format=3&T"
    response = _make_request(url)
    
    if response:
        return f"🌤️ Погода в {city}:\n{response.text.strip()}"
    return f"❌ Не удалось получить данные о погоде для города {city}"


def get_weather_json(city: str) -> str:
    """Получение текущей погоды в удобном формате с расширенной информацией"""
    url = f"{API_BASE_URL}/{city}?lang=ru&format=j1"
    response = _make_request(url)
    
    if not response:
        return f"❌ Не удалось получить данные о погоде для города {city}"
    
    try:
        data = response.json()
        current = data['current_condition'][0]
        
        # Получаем русское описание погоды (если доступно)
        weather_desc_ru = current.get('lang_ru', [{}])[0].get('value', '')
        if not weather_desc_ru:
            weather_desc_ru = current['weatherDesc'][0]['value']
        
        # Получаем название города из nearest_area (более точное)
        location_name = city
        if 'nearest_area' in data and len(data['nearest_area']) > 0:
            area = data['nearest_area'][0]
            if 'areaName' in area and len(area['areaName']) > 0:
                location_name = area['areaName'][0]['value']
        
        # Получаем данные прогноза на сегодня (если доступно)
        today_info = ""
        if 'weather' in data and len(data['weather']) > 0:
            today = data['weather'][0]
            max_temp = today.get('maxtempC', '')
            min_temp = today.get('mintempC', '')
            if max_temp and min_temp:
                today_info = f"\n📅 Сегодня: *{min_temp}°C* / *{max_temp}°C* (мин/макс)"
        
        # Переводим направление ветра
        wind_dir_ru = _translate_wind_direction(current['winddir16Point'])
        
        # Формируем сообщение
        result = f"""🌤️ *Погода в {location_name}*

🌡️ Температура: *{current['temp_C']}°C* (ощущается как {current['FeelsLikeC']}°C)
☁️ Погода: *{weather_desc_ru}*
💧 Влажность: *{current['humidity']}%*
💨 Ветер: *{current['windspeedKmph']} км/ч* {wind_dir_ru}
📊 Давление: *{current['pressure']} гПа*"""
        
        # Добавляем дополнительные данные, если доступны
        if 'precipMM' in current and float(current['precipMM']) > 0:
            result += f"\n🌧️ Осадки: *{current['precipMM']} мм*"
        
        if 'cloudcover' in current:
            result += f"\n☁️ Облачность: *{current['cloudcover']}%*"
        
        if 'visibility' in current:
            result += f"\n👁️ Видимость: *{current['visibility']} км*"
        
        if 'uvIndex' in current and int(current['uvIndex']) > 0:
            result += f"\n☀️ УФ-индекс: *{current['uvIndex']}*"
        
        # Добавляем прогноз на сегодня
        if today_info:
            result += today_info
        
        # Добавляем информацию о восходе/закате (если доступно)
        if 'weather' in data and len(data['weather']) > 0:
            today = data['weather'][0]
            if 'astronomy' in today and len(today['astronomy']) > 0:
                astro = today['astronomy'][0]
                if 'sunrise' in astro and 'sunset' in astro:
                    result += f"\n🌅 Восход: {astro['sunrise']} | 🌇 Закат: {astro['sunset']}"
                if 'sunHour' in today and float(today['sunHour']) > 0:
                    result += f"\n☀️ Солнечных часов: *{today['sunHour']} ч*"
        
        # Добавляем информацию о снеге (если есть)
        if 'weather' in data and len(data['weather']) > 0:
            today = data['weather'][0]
            if 'totalSnow_cm' in today and float(today.get('totalSnow_cm', 0)) > 0:
                result += f"\n❄️ Снег: *{today['totalSnow_cm']} см*"
        
        # Добавляем информацию о стране/регионе (если доступно)
        if 'nearest_area' in data and len(data['nearest_area']) > 0:
            area = data['nearest_area'][0]
            region_info = []
            if 'country' in area and len(area['country']) > 0:
                region_info.append(area['country'][0]['value'])
            if 'region' in area and len(area['region']) > 0:
                region_info.append(area['region'][0]['value'])
            if region_info:
                result += f"\n🌍 {', '.join(region_info)}"
        
        # Добавляем время наблюдения
        if 'observation_time' in current:
            result += f"\n🕐 Время наблюдения: {current['observation_time']}"
        
        return result
    
    except (KeyError, IndexError, ValueError) as e:
        return f"❌ Ошибка обработки данных о погоде"


def get_detailed_weather(city: str) -> str:
    """Получение подробного прогноза погоды на 3 дня"""
    url = f"{API_BASE_URL}/{city}?lang=ru&format=j1"
    response = _make_request(url)
    
    if not response:
        return f"❌ Не удалось получить данные о погоде для города {city}"
    
    try:
        data = response.json()
        current = data['current_condition'][0]
        weather = data['weather'][:3]  # Берем только 3 дня
        
        # Получаем русское описание погоды
        weather_desc_ru = current.get('lang_ru', [{}])[0].get('value', '')
        if not weather_desc_ru:
            weather_desc_ru = current['weatherDesc'][0]['value']
        
        # Получаем название города из nearest_area
        location_name = city
        if 'nearest_area' in data and len(data['nearest_area']) > 0:
            area = data['nearest_area'][0]
            if 'areaName' in area and len(area['areaName']) > 0:
                location_name = area['areaName'][0]['value']
        
        # Переводим направление ветра
        wind_dir_ru = _translate_wind_direction(current['winddir16Point'])
        
        # Текущая погода
        result = f"🌤️ *Подробный прогноз погоды для {location_name}*\n{'=' * 40}\n\n"
        result += f"🌡️ *СЕЙЧАС ({location_name}):*\n"
        result += f"🌡️ Температура: *{current['temp_C']}°C* (ощущается как {current['FeelsLikeC']}°C)\n"
        result += f"☁️ Погода: *{weather_desc_ru}*\n"
        result += f"💧 Влажность: *{current['humidity']}%*\n"
        result += f"💨 Ветер: *{current['windspeedKmph']} км/ч* {wind_dir_ru}\n"
        result += f"📊 Давление: *{current['pressure']} гПа*\n"
        result += f"👁️ Видимость: *{current['visibility']} км*\n"
        result += f"☁️ Облачность: *{current.get('cloudcover', '0')}%*\n"
        
        # Восход/закат для сегодня
        if 'astronomy' in weather[0] and len(weather[0]['astronomy']) > 0:
            astro = weather[0]['astronomy'][0]
            if 'sunrise' in astro and 'sunset' in astro:
                result += f"🌅 Восход: {astro['sunrise']} | 🌇 Закат: {astro['sunset']}\n"
        
        result += "\n"
        
        # Прогноз на 3 дня
        result += "📅 *ПРОГНОЗ НА 3 ДНЯ:*\n"
        
        for i, day in enumerate(weather):
            formatted_date = _format_date(day['date'])
            hourly = day['hourly'][0]
            
            # Получаем русское описание
            weather_desc_ru = hourly.get('lang_ru', [{}])[0].get('value', '')
            if not weather_desc_ru:
                weather_desc_ru = hourly['weatherDesc'][0]['value']
            
            result += f"\n📆 *{formatted_date}:*\n"
            result += f"🌡️ Температура: *{day['mintempC']}°C* - *{day['maxtempC']}°C* (мин/макс)\n"
            result += f"📊 Средняя: *{day.get('avgtempC', 'N/A')}°C*\n"
            result += f"☁️ Погода: *{weather_desc_ru}*\n"
            
            # Снег (если есть)
            if 'totalSnow_cm' in day and float(day.get('totalSnow_cm', 0)) > 0:
                result += f"❄️ Снег: *{day['totalSnow_cm']} см*\n"
            
            # Солнечные часы
            if 'sunHour' in day and float(day.get('sunHour', 0)) > 0:
                result += f"☀️ Солнечных часов: *{day['sunHour']} ч*\n"
            
            # Восход/закат
            if 'astronomy' in day and len(day['astronomy']) > 0:
                astro = day['astronomy'][0]
                if 'sunrise' in astro and 'sunset' in astro:
                    result += f"🌅 Восход: {astro['sunrise']} | 🌇 Закат: {astro['sunset']}\n"
        
        return result
    
    except (KeyError, IndexError) as e:
        return f"❌ Ошибка обработки данных о погоде"
