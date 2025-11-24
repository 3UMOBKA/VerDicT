from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.types import Update

class LoggingMiddleware(BaseMiddleware):
    async def on_process_update(self, update: Update, data):
        if isinstance(update.message, dict):
            text = update.message.get("text") or ""
            print(f"Received message from {update.message.from_user.id}: {text}")

def register_middlewares(dp):
    dp.middleware.setup(LoggingMiddleware())