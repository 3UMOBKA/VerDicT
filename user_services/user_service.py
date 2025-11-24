from db_layer.repository import add_user, get_user_by_telegram_id

async def create_new_user(data):
    return add_user(data)

async def fetch_user_by_tg_id(tg_id):
    return get_user_by_telegram_id(tg_id)