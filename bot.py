import asyncio
import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message

# Загружаем переменные из .env файла (для локальной разработки)
load_dotenv()

# Токен бота из переменной окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Создаем объекты бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Я эхо-бот.\n"
        "Отправь мне любое сообщение, и я отправлю его обратно!"
    )


# Обработчик всех остальных сообщений (эхо)
@dp.message()
async def echo_message(message: Message):
    try:
        await message.send_copy(chat_id=message.chat.id)
    except TypeError:
        # Если не удалось скопировать сообщение (например, неподдерживаемый тип),
        # отправляем текстовое сообщение
        await message.answer(message.text or "Не могу повторить это сообщение")


# Главная функция запуска бота
async def main():
    # Удаляем вебхуки (на всякий случай)
    await bot.delete_webhook(drop_pending_updates=True)
    # Запускаем polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
