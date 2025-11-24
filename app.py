from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio
import logging
import os
from dotenv import load_dotenv
from bot_core.handlers import router  

    
# Загружаем переменные среды из .env
load_dotenv('.env')

# Настройка логгирования
logging.basicConfig(level=logging.INFO)

# Подключаемся к хранилищу состояний
storage = MemoryStorage()

# Создаем экземпляр бота и диспетчер
bot = Bot(token=os.getenv('BOT_TOKEN'))
dp = Dispatcher(storage=storage)

# Регистрируем наши обработчики
dp.include_router(router)

# Основная функция для запуска бота с использованием стандартного поллинга
async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
    
    
    
    
