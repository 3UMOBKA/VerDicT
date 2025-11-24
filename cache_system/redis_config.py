import asyncio
import aioredis
from dotenv import load_dotenv
import os

load_dotenv()

async def init_redis_cache():
    global redis_pool
    redis_host = os.getenv('REDIS_HOST', 'localhost')
    redis_port = int(os.getenv('REDIS_PORT', 6379))
    redis_db = int(os.getenv('REDIS_DB', 0))
    redis_pool = await aioredis.create_redis_pool((redis_host, redis_port), db=redis_db)