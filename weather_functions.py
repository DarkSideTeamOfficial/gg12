#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль с функциями для получения прогноза погоды
"""

import requests
import re

def get_weather(city: str) -> str:
    """Получение прогноза погоды для указанного города на русском языке"""
    try:
        # Запрос к wttr.in с русской локализацией и отключением цветов
        url = f"https://wttr.in/{city}?lang=ru&format=3&T"
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            weather_data = response.text.strip()
            return f"🌤️ Погода в {city}:\n{weather_data}"
        else:
            return f"❌ Не удалось получить данные о погоде для города {city}"
            
    except requests.exceptions.RequestException as e:
        return f"❌ Ошибка при получении данных о погоде: {str(e)}"
    except Exception as e:
        return f"❌ Произошла ошибка: {str(e)}"

def get_detailed_weather(city: str) -> str:
    """Получение подробного прогноза погоды"""
    try:
        # Запрос к wttr.in в JSON формате для получения прогноза на несколько дней
        url = f"https://wttr.in/{city}?lang=ru&format=j1"
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            current = data['current_condition'][0]
            weather = data['weather']
            
            # Формируем красивое сообщение
            result = f"🌤️ *Подробный прогноз погоды для {city}*\n"
            result += "=" * 40 + "\n\n"
            
            # Текущая погода
            result += "🌡️ *СЕЙЧАС:*\n"
            result += f"🌡️ Температура: *{current['temp_C']}°C* (ощущается как {current['FeelsLikeC']}°C)\n"
            result += f"☁️ Погода: *{current['weatherDesc'][0]['value']}*\n"
            result += f"💧 Влажность: *{current['humidity']}%*\n"
            result += f"💨 Ветер: *{current['windspeedKmph']} км/ч {current['winddir16Point']}*\n"
            result += f"📊 Давление: *{current['pressure']} гПа*\n"
            result += f"👁️ Видимость: *{current['visibility']} км*\n\n"
            
            # Прогноз на 3 дня
            result += "📅 *ПРОГНОЗ НА 3 ДНЯ:*\n"
            result += "💡 *Температура указана как минимум/максимум за день*\n"
            result += "─" * 30 + "\n"
            
            for i, day in enumerate(weather[:3]):
                date = day['date']
                max_temp = day['maxtempC']
                min_temp = day['mintempC']
                desc = day['hourly'][0]['weatherDesc'][0]['value']
                precip = day['hourly'][0]['precipMM']
                
                # Преобразуем дату в более читаемый формат
                from datetime import datetime
                try:
                    date_obj = datetime.strptime(date, '%Y-%m-%d')
                    # Словарь для перевода дней недели на русский
                    weekdays_ru = {
                        'Monday': 'Понедельник',
                        'Tuesday': 'Вторник', 
                        'Wednesday': 'Среда',
                        'Thursday': 'Четверг',
                        'Friday': 'Пятница',
                        'Saturday': 'Суббота',
                        'Sunday': 'Воскресенье'
                    }
                    weekday_en = date_obj.strftime('%A')
                    weekday_ru = weekdays_ru.get(weekday_en, weekday_en)
                    formatted_date = date_obj.strftime(f'%d.%m.%Y ({weekday_ru})')
                except:
                    formatted_date = date
                
                result += f"\n📆 *{formatted_date}:*\n"
                result += f"🌡️ Температура: *{min_temp}°C* - *{max_temp}°C* (мин/макс)\n"
                result += f"☁️ Погода: *{desc}*\n"
                result += f"🌧️ Осадки: *{precip} мм*\n"
                
                if i < 2:  # Добавляем разделитель между днями
                    result += "─" * 20 + "\n"
            
            return result
        else:
            return f"❌ Не удалось получить данные о погоде для города {city}"
            
    except requests.exceptions.RequestException as e:
        return f"❌ Ошибка при получении данных о погоде: {str(e)}"
    except Exception as e:
        return f"❌ Произошла ошибка: {str(e)}"

def get_weather_json(city: str) -> str:
    """Получение прогноза погоды в JSON формате (более надежно)"""
    try:
        # Запрос к wttr.in в JSON формате
        url = f"https://wttr.in/{city}?lang=ru&format=j1"
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            current = data['current_condition'][0]
            
            # Формируем красивое сообщение
            temp = current['temp_C']
            feels_like = current['FeelsLikeC']
            desc = current['weatherDesc'][0]['value']
            humidity = current['humidity']
            wind_speed = current['windspeedKmph']
            wind_dir = current['winddir16Point']
            pressure = current['pressure']
            
            weather_text = f"""🌤️ *Погода в {city}*

🌡️ Температура: *{temp}°C* (ощущается как {feels_like}°C)
☁️ Погода: *{desc}*
💧 Влажность: *{humidity}%*
💨 Ветер: *{wind_speed} км/ч {wind_dir}*
📊 Давление: *{pressure} гПа*"""
            
            return weather_text
        else:
            return f"❌ Не удалось получить данные о погоде для города {city}"
            
    except requests.exceptions.RequestException as e:
        return f"❌ Ошибка при получении данных о погоде: {str(e)}"
    except Exception as e:
        return f"❌ Произошла ошибка: {str(e)}"
