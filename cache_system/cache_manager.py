import redis
from cache_system.redis_config import REDIS_HOST, REDIS_PORT

class CacheManager:
    def __init__(self):
        self.r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

    def set_cache(self, key, value):
        self.r.set(key, value)

    def get_cache(self, key):
        return self.r.get(key)