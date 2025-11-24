from aiogram.dispatcher import Dispatcher
from bot_core.handlers import register_handlers
from bot_core.middlewares import register_middlewares

from db_layer.models import *
from db_layer.repository import *

def register_user(message):
    user_data = {
        'telegram_id': message.chat.id,
        'username': message.chat.username,
        'first_name': message.chat.first_name,
        'last_name': message.chat.last_name
    }
    existing_user = get_user_by_telegram_id(user_data['telegram_id'])
    if not existing_user:
        add_user(user_data)
        send_message(message.chat.id, "Вы зарегистрированы!")
    else:
        send_message(message.chat.id, "Вы уже зарегистрированы.")

def setup_dispatcher(dispatcher: Dispatcher):
    """
    Устанавливает обработчики и промежуточные слои (middlewares) для бота.
    """
    # Регистрация обработчиков
    register_handlers(dispatcher)
    
    # Регистрация middleware
    register_middlewares(dispatcher)