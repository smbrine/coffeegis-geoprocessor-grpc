import redis.asyncio as aioredis


class RedisWrapper:
    def __init__(self, redis_url: str):
        self.r = aioredis.from_url(
            redis_url,
        )

    async def get(self, name):
        return await self.r.get(name)

    async def set(
        self, name, value, ex, *args, **kwargs
    ):
        return await self.r.set(
            name, value, ex, *args, **kwargs
        )

    async def hget(
        self,
        name,
        key,
        encoding=None,
        fallback=None,
    ):
        res = await self.r.hget(name, key)
        if res and encoding:
            res = res.decode("utf-8")
        return res or fallback

    async def hset(
        self,
        name,
        key,
        value,
        ex=3600,
        *args,
        **kwargs
    ):
        r = await self.r.hset(
            name, key, value, *args, **kwargs
        )
        await self.r.expire(name, ex)
        return r

    async def drop_cache(self, key):
        await self.r.expire(key, 1)
