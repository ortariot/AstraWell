import asyncio

from redis.asyncio import Redis
from core.settings import settings


class RedisRepository():
    """
    interface for Redis
    """
    redis = Redis(host=settings.redis_host,
                  port=settings.redis_port,
                  password=settings.redis_password
                  )

    async def get_list(self, key: str):
        """_getting data

        Args:
            key (str): key by element

        """

        data = await self.redis.lrange(key, 0, -1)

        return [item.decode() for item in data]
    
    async def add_list(self, key: str, value):
        """_getting data

        Args:
            key (str): key by element

        """

        data = await self.redis.lpush(key, value)

        return data
    

if __name__ == "__main__":

    redis = RedisRepository()

    res = asyncio(redis.add_list("test", "suka"))


    