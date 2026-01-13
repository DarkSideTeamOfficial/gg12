import asyncio
import logging
import requests
import os
from datetime import datetime, time
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import db
from scheduler import start_scheduler, stop_scheduler, send_test_notification
from weather_functions import get_weather, get_detailed_weather, get_weather_json, get_weather_data_dict
from ai_recommendations import get_weather_recommendations_async

# Загружаем переменные окружения из .env файла
load_dotenv()

# Получаем токен бота из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Вспомогательная функция для отправки AI рекомендаций
async def _send_ai_recommendations(chat_id: int, city: str):
    """Отправка AI рекомендаций отдельным сообщением (не блокирует основной ответ)"""
    try:
        weather_data = get_weather_data_dict(city)
        if weather_data:
            recommendations = await get_weather_recommendations_async(weather_data)
            if recommendations:
                await bot.send_message(
                    chat_id,
                    f"💡 *Рекомендации:*\n\n{recommendations}",
                    parse_mode="Markdown"
                )
    except Exception as e:
        logging.error(f"Ошибка при получении AI рекомендаций: {e}")
        # Не показываем ошибку пользователю, просто не отправляем рекомендации

# Состояния для FSM
class WeatherSettings(StatesGroup):
    waiting_for_city = State()
    waiting_for_morning_time = State()
    waiting_for_evening_time = State()
    waiting_for_forecast_city = State()  # Для запроса города для подробного прогноза


@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    
    # Проверяем, есть ли у пользователя сохраненный город
    user_data = db.get_user(user_id)
    has_city = user_data and user_data.get('city')
    
    welcome_text = """
🌤️ Добро пожаловать в бота прогноза погоды!

Выберите действие:
"""
    
    # Создаем клавиатуру с кнопками
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌤️ Моя погода (кратко)", callback_data="my_weather_brief"),
            InlineKeyboardButton(text="📊 Моя погода (подробно)", callback_data="my_weather_detailed")
        ],
        [
            InlineKeyboardButton(text="🔍 Погода в городе", callback_data="weather_city"),
            InlineKeyboardButton(text="📈 Подробный прогноз", callback_data="forecast_city")
        ],
        [
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings_menu"),
            InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help_info")
        ]
    ])
    
    if not has_city:
        welcome_text += "\n💡 Совет: Настройте город в настройках для быстрого доступа к погоде!"
    
    await message.answer(welcome_text, reply_markup=keyboard)

@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    help_text = """
🌤️ Помощь по использованию бота

Основные команды:
/weather <город> - получить краткий прогноз погоды
/forecast <город> - получить подробный прогноз погоды

Команды подписки:
/subscribe - настроить автоматическую отправку погоды
/unsubscribe - отключить автоматические уведомления
/settings - посмотреть текущие настройки
/my_weather - получить погоду для вашего города
/test_notification - отправить тестовое уведомление

Управление:
/start - начать работу с ботом
/help - показать эту справку

Примеры использования:
/weather Москва
/forecast Санкт-Петербург
/subscribe

Бот поддерживает города на разных языках!
"""
    await message.answer(help_text)

@dp.message(Command("weather"))
async def cmd_weather(message: Message):
    """Обработчик команды /weather для краткого прогноза"""
    # Извлекаем название города из команды
    command_parts = message.text.split(maxsplit=1)
    if len(command_parts) < 2:
        await message.answer("❌ Пожалуйста, укажите название города.\nПример: /weather Москва")
        return
    
    city = command_parts[1].strip()
    if not city:
        await message.answer("❌ Пожалуйста, укажите название города.\nПример: /weather Москва")
        return
    
    # Показываем, что бот печатает
    await bot.send_chat_action(message.chat.id, "typing")
    
    try:
        # Получаем данные о погоде (используем JSON формат для надежности)
        weather_info = get_weather_json(city)
        await message.answer(weather_info, parse_mode="Markdown")
        
        # Отправляем AI рекомендации отдельным сообщением
        asyncio.create_task(_send_ai_recommendations(message.chat.id, city))
    except Exception as e:
        await message.answer(f"❌ Произошла ошибка при получении погоды: {str(e)}")

@dp.message(Command("forecast"))
async def cmd_forecast(message: Message):
    """Обработчик команды /forecast для подробного прогноза"""
    # Извлекаем название города из команды
    command_parts = message.text.split(maxsplit=1)
    if len(command_parts) < 2:
        await message.answer("❌ Пожалуйста, укажите название города.\nПример: /forecast Москва")
        return
    
    city = command_parts[1].strip()
    if not city:
        await message.answer("❌ Пожалуйста, укажите название города.\nПример: /forecast Москва")
        return
    
    # Показываем, что бот печатает
    await bot.send_chat_action(message.chat.id, "typing")
    
    try:
        # Получаем подробные данные о погоде
        weather_info = get_detailed_weather(city)
        await message.answer(weather_info, parse_mode="Markdown")
        
        # Отправляем AI рекомендации отдельным сообщением
        asyncio.create_task(_send_ai_recommendations(message.chat.id, city))
    except Exception as e:
        await message.answer(f"❌ Произошла ошибка при получении прогноза: {str(e)}")

@dp.message(Command("subscribe"))
async def cmd_subscribe(message: Message, state: FSMContext):
    """Обработчик команды /subscribe для настройки подписки"""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    
    # Добавляем пользователя в базу данных
    db.add_user(user_id, username, first_name, last_name)
    
    # Получаем текущие настройки пользователя
    user_data = db.get_user(user_id)
    
    if user_data and user_data.get('city'):
        # Если город уже установлен, показываем настройки
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏙️ Изменить город", callback_data="change_city")],
            [InlineKeyboardButton(text="⏰ Настроить время", callback_data="change_time")],
            [InlineKeyboardButton(text="📊 Тип прогноза", callback_data="change_type")],
            [InlineKeyboardButton(text="✅ Готово", callback_data="done")]
        ])
        
        settings_text = f"""
🌤️ Настройки автоматической отправки погоды

🏙️ Город: {user_data['city']}
⏰ Утреннее время: {user_data.get('morning_time', '08:00')}
🌙 Вечернее время: {user_data.get('evening_time', '20:00')}
📊 Тип прогноза: {'Подробный' if user_data.get('weather_type') == 'detailed' else 'Краткий'}

Выберите, что хотите изменить:
"""
        await message.answer(settings_text, reply_markup=keyboard)
    else:
        # Если город не установлен, просим ввести город
        await state.set_state(WeatherSettings.waiting_for_city)
        await message.answer("🏙️ Введите название города для автоматической отправки погоды:")

@dp.message(Command("unsubscribe"))
async def cmd_unsubscribe(message: Message):
    """Обработчик команды /unsubscribe"""
    user_id = message.from_user.id
    
    if db.deactivate_user(user_id):
        await message.answer("❌ Автоматические уведомления о погоде отключены.")
    else:
        await message.answer("❌ Ошибка при отключении уведомлений.")

@dp.message(Command("settings"))
async def cmd_settings(message: Message):
    """Обработчик команды /settings"""
    user_id = message.from_user.id
    user_data = db.get_user(user_id)
    
    if not user_data:
        await message.answer("❌ Вы не подписаны на уведомления. Используйте /subscribe для настройки.")
        return
    
    if not user_data.get('city'):
        await message.answer("❌ Город не установлен. Используйте /subscribe для настройки.")
        return
    
    settings_text = f"""
🌤️ Ваши настройки погоды

🏙️ Город: {user_data['city']}
⏰ Утреннее время: {user_data.get('morning_time', '08:00')}
🌙 Вечернее время: {user_data.get('evening_time', '20:00')}
📊 Тип прогноза: {'Подробный' if user_data.get('weather_type') == 'detailed' else 'Краткий'}
📅 Статус: {'Активен' if user_data.get('is_active') else 'Неактивен'}

Используйте /subscribe для изменения настроек.
"""
    await message.answer(settings_text)

@dp.message(Command("my_weather"))
async def cmd_my_weather(message: Message):
    """Обработчик команды /my_weather"""
    user_id = message.from_user.id
    user_data = db.get_user(user_id)
    
    if not user_data or not user_data.get('city'):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚙️ Настроить город", callback_data="settings_menu")]
        ])
        await message.answer(
            "❌ Город не установлен. Используйте /subscribe для настройки.",
            reply_markup=keyboard
        )
        return
    
    city = user_data['city']
    weather_type = user_data.get('weather_type', 'brief')
    
    # Показываем, что бот печатает
    await bot.send_chat_action(message.chat.id, "typing")
    
    # Получаем данные о погоде
    if weather_type == 'detailed':
        weather_info = get_detailed_weather(city)
    else:
        weather_info = get_weather_json(city)
    
    await message.answer(weather_info, parse_mode="Markdown")
    
    # Отправляем AI рекомендации отдельным сообщением
    asyncio.create_task(_send_ai_recommendations(message.chat.id, city))

@dp.message(Command("test_notification"))
async def cmd_test_notification(message: Message):
    """Обработчик команды /test_notification для тестирования уведомлений"""
    user_id = message.from_user.id
    user_data = db.get_user(user_id)
    
    if not user_data or not user_data.get('city'):
        await message.answer("❌ Город не настроен. Используйте /subscribe для настройки.")
        return
    
    await message.answer("📤 Отправляю тестовое уведомление...")
    await send_test_notification(bot, user_id)

# Обработчики callback-запросов
@dp.callback_query(F.data == "change_city")
async def callback_change_city(callback: CallbackQuery, state: FSMContext):
    """Обработчик изменения города"""
    await state.set_state(WeatherSettings.waiting_for_city)
    await callback.message.edit_text("🏙️ Введите название города:")
    await callback.answer()

@dp.callback_query(F.data == "change_time")
async def callback_change_time(callback: CallbackQuery):
    """Обработчик изменения времени"""
    user_id = callback.from_user.id
    user_data = db.get_user(user_id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏰ Утреннее время", callback_data="set_morning")],
        [InlineKeyboardButton(text="🌙 Вечернее время", callback_data="set_evening")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_settings")]
    ])
    
    time_text = f"""⏰ Настройка времени уведомлений

🌅 Утреннее время: {user_data.get('morning_time', '08:00')}
🌙 Вечернее время: {user_data.get('evening_time', '20:00')}

Выберите, что хотите изменить:"""
    
    await callback.message.edit_text(time_text, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data == "change_type")
async def callback_change_type(callback: CallbackQuery):
    """Обработчик изменения типа прогноза"""
    user_id = callback.from_user.id
    user_data = db.get_user(user_id)
    current_type = user_data.get('weather_type', 'brief')
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{'✅' if current_type == 'brief' else '❌'} Краткий прогноз", callback_data="type_brief")],
        [InlineKeyboardButton(text=f"{'✅' if current_type == 'detailed' else '❌'} Подробный прогноз", callback_data="type_detailed")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_settings")]
    ])
    await callback.message.edit_text("📊 Выберите тип прогноза:", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data.startswith("type_"))
async def callback_set_type(callback: CallbackQuery):
    """Обработчик установки типа прогноза"""
    user_id = callback.from_user.id
    weather_type = callback.data.split("_")[1]
    
    db.update_notification_settings(user_id, weather_type=weather_type)
    await callback.answer(f"✅ Тип прогноза изменен на {'краткий' if weather_type == 'brief' else 'подробный'}")

@dp.callback_query(F.data == "done")
async def callback_done(callback: CallbackQuery):
    """Обработчик завершения настройки"""
    await callback.message.edit_text("✅ Настройки сохранены! Теперь вы будете получать автоматические уведомления о погоде.")
    await callback.answer()

@dp.callback_query(F.data == "set_morning")
async def callback_set_morning(callback: CallbackQuery, state: FSMContext):
    """Обработчик настройки утреннего времени"""
    await state.set_state(WeatherSettings.waiting_for_morning_time)
    await callback.message.edit_text("🌅 Введите время для утренних уведомлений (формат: ЧЧ:ММ)\nНапример: 08:00")
    await callback.answer()

@dp.callback_query(F.data == "set_evening")
async def callback_set_evening(callback: CallbackQuery, state: FSMContext):
    """Обработчик настройки вечернего времени"""
    await state.set_state(WeatherSettings.waiting_for_evening_time)
    await callback.message.edit_text("🌙 Введите время для вечерних уведомлений (формат: ЧЧ:ММ)\nНапример: 20:00")
    await callback.answer()

@dp.callback_query(F.data == "back_to_settings")
async def callback_back_to_settings(callback: CallbackQuery):
    """Обработчик возврата к настройкам"""
    user_id = callback.from_user.id
    user_data = db.get_user(user_id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏙️ Изменить город", callback_data="change_city")],
        [InlineKeyboardButton(text="⏰ Настроить время", callback_data="change_time")],
        [InlineKeyboardButton(text="📊 Тип прогноза", callback_data="change_type")],
        [InlineKeyboardButton(text="✅ Готово", callback_data="done")]
    ])
    
    settings_text = f"""
🌤️ Настройки автоматической отправки погоды

🏙️ Город: {user_data['city']}
⏰ Утреннее время: {user_data.get('morning_time', '08:00')}
🌙 Вечернее время: {user_data.get('evening_time', '20:00')}
📊 Тип прогноза: {'Подробный' if user_data.get('weather_type') == 'detailed' else 'Краткий'}

Выберите, что хотите изменить:
"""
    await callback.message.edit_text(settings_text, reply_markup=keyboard)
    await callback.answer()

# Новые обработчики для Inline кнопок главного меню
@dp.callback_query(F.data == "my_weather_brief")
async def callback_my_weather_brief(callback: CallbackQuery):
    """Обработчик кнопки 'Моя погода (кратко)'"""
    user_id = callback.from_user.id
    user_data = db.get_user(user_id)
    
    if not user_data or not user_data.get('city'):
        await callback.answer("❌ Город не настроен. Используйте /subscribe", show_alert=True)
        return
    
    city = user_data['city']
    await callback.answer("⏳ Получаю погоду...")
    
    await bot.send_chat_action(callback.message.chat.id, "typing")
    weather_info = get_weather_json(city)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Подробный прогноз", callback_data="my_weather_detailed")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    
    await callback.message.answer(weather_info, parse_mode="Markdown", reply_markup=keyboard)
    
    # Отправляем AI рекомендации отдельным сообщением
    asyncio.create_task(_send_ai_recommendations(callback.message.chat.id, city))
    
    await callback.answer()

@dp.callback_query(F.data == "my_weather_detailed")
async def callback_my_weather_detailed(callback: CallbackQuery):
    """Обработчик кнопки 'Моя погода (подробно)'"""
    user_id = callback.from_user.id
    user_data = db.get_user(user_id)
    
    if not user_data or not user_data.get('city'):
        await callback.answer("❌ Город не настроен. Используйте /subscribe", show_alert=True)
        return
    
    city = user_data['city']
    await callback.answer("⏳ Получаю подробный прогноз...")
    
    await bot.send_chat_action(callback.message.chat.id, "typing")
    weather_info = get_detailed_weather(city)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌤️ Краткий прогноз", callback_data="my_weather_brief")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    
    # Отправляем погоду сразу
    await callback.message.answer(weather_info, parse_mode="Markdown", reply_markup=keyboard)
    
    # Получаем и отправляем рекомендации отдельным сообщением (асинхронно, без блокировки)
    asyncio.create_task(_send_ai_recommendations(callback.message.chat.id, city))
    
    await callback.answer()

@dp.callback_query(F.data == "weather_city")
async def callback_weather_city(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Погода в городе'"""
    await callback.message.edit_text("🏙️ Введите название города для получения краткого прогноза погоды:")
    await state.set_state(WeatherSettings.waiting_for_city)
    await callback.answer()

@dp.callback_query(F.data == "forecast_city")
async def callback_forecast_city(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Подробный прогноз'"""
    await callback.message.edit_text("🏙️ Введите название города для получения подробного прогноза погоды:")
    await state.set_state(WeatherSettings.waiting_for_forecast_city)
    await callback.answer()

@dp.callback_query(F.data == "settings_menu")
async def callback_settings_menu(callback: CallbackQuery):
    """Обработчик кнопки 'Настройки'"""
    user_id = callback.from_user.id
    user_data = db.get_user(user_id)
    
    if not user_data or not user_data.get('city'):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏙️ Настроить город", callback_data="change_city")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        await callback.message.edit_text(
            "⚙️ Настройки\n\n❌ Город не установлен. Настройте город для автоматических уведомлений.",
            reply_markup=keyboard
        )
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏙️ Изменить город", callback_data="change_city")],
            [InlineKeyboardButton(text="⏰ Настроить время", callback_data="change_time")],
            [InlineKeyboardButton(text="📊 Тип прогноза", callback_data="change_type")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        settings_text = f"""
⚙️ Настройки автоматической отправки погоды

🏙️ Город: {user_data['city']}
⏰ Утреннее время: {user_data.get('morning_time', '08:00')}
🌙 Вечернее время: {user_data.get('evening_time', '20:00')}
📊 Тип прогноза: {'Подробный' if user_data.get('weather_type') == 'detailed' else 'Краткий'}

Выберите, что хотите изменить:
"""
        await callback.message.edit_text(settings_text, reply_markup=keyboard)
    
    await callback.answer()

@dp.callback_query(F.data == "help_info")
async def callback_help_info(callback: CallbackQuery):
    """Обработчик кнопки 'Помощь'"""
    help_text = """
ℹ️ Помощь по использованию бота

🌤️ Моя погода - получить погоду для вашего города (из настроек)
🔍 Погода в городе - получить краткий прогноз для любого города
📈 Подробный прогноз - получить детальный прогноз на 3 дня

⚙️ Настройки - настроить автоматические уведомления

Команды:
/start - главное меню
/subscribe - настроить подписку
/settings - посмотреть настройки
/help - эта справка
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(help_text, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery):
    """Обработчик кнопки 'Главное меню'"""
    user_id = callback.from_user.id
    user_data = db.get_user(user_id)
    has_city = user_data and user_data.get('city')
    
    welcome_text = "🏠 Главное меню:\n\nВыберите действие:"
    if not has_city:
        welcome_text += "\n💡 Совет: Настройте город в настройках для быстрого доступа к погоде!"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌤️ Моя погода (кратко)", callback_data="my_weather_brief"),
            InlineKeyboardButton(text="📊 Моя погода (подробно)", callback_data="my_weather_detailed")
        ],
        [
            InlineKeyboardButton(text="🔍 Погода в городе", callback_data="weather_city"),
            InlineKeyboardButton(text="📈 Подробный прогноз", callback_data="forecast_city")
        ],
        [
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings_menu"),
            InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help_info")
        ]
    ])
    
    await callback.message.edit_text(welcome_text, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data.startswith("forecast_"))
async def callback_forecast_by_city(callback: CallbackQuery):
    """Обработчик подробного прогноза для конкретного города"""
    city = callback.data.replace("forecast_", "")
    
    if city == "city":
        # Если это запрос на ввод города, обработается через FSM
        return
    
    await callback.answer("⏳ Получаю подробный прогноз...")
    await bot.send_chat_action(callback.message.chat.id, "typing")
    
    weather_info = get_detailed_weather(city)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌤️ Краткий прогноз", callback_data=f"weather_{city}")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    
    await callback.message.answer(weather_info, parse_mode="Markdown", reply_markup=keyboard)
    
    # Отправляем AI рекомендации отдельным сообщением
    asyncio.create_task(_send_ai_recommendations(callback.message.chat.id, city))
    
    await callback.answer()

@dp.callback_query(F.data.startswith("weather_"))
async def callback_weather_by_city(callback: CallbackQuery):
    """Обработчик краткого прогноза для конкретного города"""
    city = callback.data.replace("weather_", "")
    
    if city == "city":
        # Если это запрос на ввод города, обработается через FSM
        return
    
    await callback.answer("⏳ Получаю погоду...")
    await bot.send_chat_action(callback.message.chat.id, "typing")
    
    weather_info = get_weather_json(city)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Подробный прогноз", callback_data=f"forecast_{city}")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    
    await callback.message.answer(weather_info, parse_mode="Markdown", reply_markup=keyboard)
    
    # Отправляем AI рекомендации отдельным сообщением
    asyncio.create_task(_send_ai_recommendations(callback.message.chat.id, city))
    
    await callback.answer()

# Обработчики состояний FSM
@dp.message(WeatherSettings.waiting_for_city)
async def process_city(message: Message, state: FSMContext):
    """Обработчик ввода города (для настроек или быстрого запроса)"""
    city = message.text.strip()
    user_id = message.from_user.id
    
    if not city:
        await message.answer("❌ Пожалуйста, введите название города:")
        return
    
    # Проверяем контекст - это настройка или быстрый запрос
    # Если пользователь уже есть в БД, это настройка
    user_data = db.get_user(user_id)
    
    if user_data:
        # Это настройка города для подписки
        db.update_notification_settings(user_id, city=city)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏙️ Изменить город", callback_data="change_city")],
            [InlineKeyboardButton(text="⏰ Настроить время", callback_data="change_time")],
            [InlineKeyboardButton(text="📊 Тип прогноза", callback_data="change_type")],
            [InlineKeyboardButton(text="✅ Готово", callback_data="done")]
        ])
        
        settings_text = f"""
🌤️ Настройки автоматической отправки погоды

🏙️ Город: {city}
⏰ Утреннее время: {user_data.get('morning_time', '08:00')}
🌙 Вечернее время: {user_data.get('evening_time', '20:00')}
📊 Тип прогноза: {'Подробный' if user_data.get('weather_type') == 'detailed' else 'Краткий'}

Выберите, что хотите изменить:
"""
        await message.answer(settings_text, reply_markup=keyboard)
    else:
        # Это быстрый запрос погоды
        await bot.send_chat_action(message.chat.id, "typing")
        weather_info = get_weather_json(city)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Подробный прогноз", callback_data=f"forecast_{city}")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await message.answer(weather_info, parse_mode="Markdown", reply_markup=keyboard)
        
        # Отправляем AI рекомендации отдельным сообщением
        asyncio.create_task(_send_ai_recommendations(message.chat.id, city))
    
    await state.clear()

@dp.message(WeatherSettings.waiting_for_forecast_city)
async def process_forecast_city(message: Message, state: FSMContext):
    """Обработчик ввода города для подробного прогноза"""
    city = message.text.strip()
    
    if not city:
        await message.answer("❌ Пожалуйста, введите название города:")
        return
    
    await bot.send_chat_action(message.chat.id, "typing")
    weather_info = get_detailed_weather(city)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌤️ Краткий прогноз", callback_data=f"weather_{city}")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    
    await message.answer(weather_info, parse_mode="Markdown", reply_markup=keyboard)
    
    # Отправляем AI рекомендации отдельным сообщением
    asyncio.create_task(_send_ai_recommendations(message.chat.id, city))
    
    await state.clear()

@dp.message(WeatherSettings.waiting_for_morning_time)
async def process_morning_time(message: Message, state: FSMContext):
    """Обработчик ввода утреннего времени"""
    time_text = message.text.strip()
    user_id = message.from_user.id
    
    # Проверяем формат времени
    import re
    if not re.match(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', time_text):
        await message.answer("❌ Неверный формат времени. Используйте формат ЧЧ:ММ (например: 08:00)")
        return
    
    # Обновляем утреннее время
    db.update_notification_settings(user_id, morning_time=time_text)
    
    # Показываем обновленные настройки
    user_data = db.get_user(user_id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏙️ Изменить город", callback_data="change_city")],
        [InlineKeyboardButton(text="⏰ Настроить время", callback_data="change_time")],
        [InlineKeyboardButton(text="📊 Тип прогноза", callback_data="change_type")],
        [InlineKeyboardButton(text="✅ Готово", callback_data="done")]
    ])
    
    settings_text = f"""
🌤️ Настройки автоматической отправки погоды

🏙️ Город: {user_data['city']}
⏰ Утреннее время: {time_text}
🌙 Вечернее время: {user_data.get('evening_time', '20:00')}
📊 Тип прогноза: {'Подробный' if user_data.get('weather_type') == 'detailed' else 'Краткий'}

Выберите, что хотите изменить:
"""
    await message.answer(settings_text, reply_markup=keyboard)
    await state.clear()

@dp.message(WeatherSettings.waiting_for_evening_time)
async def process_evening_time(message: Message, state: FSMContext):
    """Обработчик ввода вечернего времени"""
    time_text = message.text.strip()
    user_id = message.from_user.id
    
    # Проверяем формат времени
    import re
    if not re.match(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', time_text):
        await message.answer("❌ Неверный формат времени. Используйте формат ЧЧ:ММ (например: 20:00)")
        return
    
    # Обновляем вечернее время
    db.update_notification_settings(user_id, evening_time=time_text)
    
    # Показываем обновленные настройки
    user_data = db.get_user(user_id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏙️ Изменить город", callback_data="change_city")],
        [InlineKeyboardButton(text="⏰ Настроить время", callback_data="change_time")],
        [InlineKeyboardButton(text="📊 Тип прогноза", callback_data="change_type")],
        [InlineKeyboardButton(text="✅ Готово", callback_data="done")]
    ])
    
    settings_text = f"""
🌤️ Настройки автоматической отправки погоды

🏙️ Город: {user_data['city']}
⏰ Утреннее время: {user_data.get('morning_time', '08:00')}
🌙 Вечернее время: {time_text}
📊 Тип прогноза: {'Подробный' if user_data.get('weather_type') == 'detailed' else 'Краткий'}

Выберите, что хотите изменить:
"""
    await message.answer(settings_text, reply_markup=keyboard)
    await state.clear()

@dp.message(F.text)
async def handle_text(message: Message, state: FSMContext):
    """Обработчик текстовых сообщений"""
    text = message.text.strip()
    user_id = message.from_user.id
    
    # Проверяем, не находится ли пользователь в состоянии ввода города/времени
    current_state = await state.get_state()
    if current_state:
        # Если пользователь в процессе настройки, пропускаем обработку
        return
    
    # Если это не команда, считаем что это название города
    city = text
    
    # Показываем, что бот печатает
    await bot.send_chat_action(message.chat.id, "typing")
    
    # Получаем данные о погоде (краткий прогноз по умолчанию)
    weather_info = get_weather_json(city)
    
    # Добавляем кнопки для подробного прогноза
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Подробный прогноз", callback_data=f"forecast_{city}")]
    ])
    
    await message.answer(weather_info, parse_mode="Markdown", reply_markup=keyboard)

async def main():
    """Основная функция для запуска бота"""
    import signal
    import sys
    
    print("🌤️ Запуск бота прогноза погоды...")
    print("Для остановки нажмите Ctrl+C")
    
    # Флаг для graceful shutdown
    shutdown_event = asyncio.Event()
    
    def signal_handler(sig, frame):
        """Обработчик сигналов для graceful shutdown"""
        print("\n🛑 Получен сигнал остановки, завершаю работу...")
        shutdown_event.set()
    
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Запускаем планировщик уведомлений
        await start_scheduler(bot)
        print("📅 Планировщик уведомлений запущен")
        
        # Запускаем бота с обработкой конфликтов
        polling_task = asyncio.create_task(_start_polling_with_retry())
        
        # Ждем либо завершения polling, либо сигнала остановки
        done, pending = await asyncio.wait(
            [polling_task, asyncio.create_task(shutdown_event.wait())],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Отменяем незавершенные задачи
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Останавливаем планировщик
        await stop_scheduler()
        print("📅 Планировщик уведомлений остановлен")
        
        # Закрываем все соединения с базой данных
        db.close_all_connections()
        print("🔌 Соединения с базой данных закрыты")
        
        # Закрываем сессию бота
        await bot.session.close()
        print("👋 Бот полностью остановлен")


async def _start_polling_with_retry():
    """Запуск polling с обработкой конфликтов и автоматическим переподключением"""
    from aiogram.exceptions import TelegramConflictError
    
    # Проверяем, можем ли мы получить обновления (проверка на конфликт)
    print("🔍 Проверка доступности бота...")
    try:
        # Пытаемся получить информацию о боте
        bot_info = await bot.get_me()
        print(f"✅ Бот подключен: @{bot_info.username}")
    except Exception as e:
        print(f"⚠️ Ошибка при проверке бота: {e}")
        # Продолжаем, возможно это временная проблема
    
    # Запускаем polling
    # aiogram сам обрабатывает конфликты внутри start_polling,
    # но мы можем добавить дополнительную логику
    print("🚀 Запуск polling...")
    try:
        await dp.start_polling(bot, close_bot_session=False)
    except TelegramConflictError as e:
        print(f"❌ Конфликт с другим экземпляром бота: {e}")
        print("💡 Убедитесь, что только один экземпляр бота запущен")
        raise
    except Exception as e:
        print(f"❌ Ошибка при запуске polling: {e}")
        raise

# Примечание: Для запуска бота используйте run_bot.py
# Этот файл содержит только логику бота и функцию main()
