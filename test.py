import asyncio

from db.cache import RedisRepository


if __name__ == "__main__":

    redis = RedisRepository()

    # asyncio.run(redis.add_list("test", "test"))

    
    res = asyncio.run(redis.get_list("neiro_getway"))


    print(res)