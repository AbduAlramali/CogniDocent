from src.core.exceptions.cache_exceptions import (
    CacheAuthenticationError,
    CacheClientError,
    CacheConnectionError,
    CacheDecodeError,
    CacheTimeoutError,
    CacheEncodeError,
)
from src.core.interfaces.icache_client import ICacheClient
from src.core.interfaces.ilogger import ILogger
import redis.asyncio as redis
from typing import Any, Callable, Awaitable, Set
import json


class RedisClient(ICacheClient):
    def __init__(self, client: redis.Redis, logger: ILogger):
        self._client = client
        self._logger = logger

    async def _execute(
        self, action: Callable[..., Awaitable[Any]], *args, **kwargs
    ) -> Any:
        """
        Centralized method to execute Redis commands and translate exceptions.
        Takes a Redis method (action) and its arguments, running them safely.
        """
        try:
            return await action(*args, **kwargs)

        except redis.TimeoutError as e:
            self._logger.error("Redis timeout error", exc=e)
            raise CacheTimeoutError("Redis timeout occurred.") from e

        except redis.AuthenticationError as e:
            self._logger.error("Redis authentication error", exc=e)
            raise CacheAuthenticationError("Redis authentication failed.") from e

        except redis.ConnectionError as e:
            self._logger.error("Redis connection lost", exc=e)
            raise CacheConnectionError("Redis connection lost.") from e

        except redis.DataError as e:
            self._logger.error("Invalid data format sent to Redis", exc=e)
            raise CacheEncodeError("Invalid data format sent to Redis.") from e

        except CacheClientError:
            raise

        except Exception as e:
            self._logger.error("Unexpected Redis error", exc=e)
            raise CacheClientError("An unexpected Redis error occurred.") from e

    async def get(self, key: str) -> Any:
        self._logger.info("Fetching from cache", key=key)
        raw_data = await self._execute(self._client.get, key)

        if raw_data is None:
            self._logger.info("Cache miss", key=key)
            return None

        self._logger.info("Cache hit", key=key)
        # If data is already a string (due to decode_responses=True)
        if isinstance(raw_data, str):
            try:
                return json.loads(raw_data)
            except (json.JSONDecodeError, TypeError):
                # It's a plain string, return it as is
                return raw_data

        # If it's bytes, we need to handle it
        try:
            return json.loads(raw_data)
        except (json.JSONDecodeError, TypeError, UnicodeDecodeError):
            try:
                return raw_data.decode("utf-8")
            except Exception as e:
                self._logger.error("Failed to decode cache key", key=key, exc=e)
                raise CacheDecodeError("Failed to decode cache key.") from e

    async def set(
        self,
        key: str,
        value: Any,
        expires_in: int | None = None,
    ) -> None:
        self._logger.info("Setting cache key", key=key, expires_in=expires_in)
        try:
            if isinstance(value, (dict, list)):
                prepared_value = json.dumps(value)
            else:
                prepared_value = value
        except TypeError as e:
            self._logger.error("Failed to serialize value for cache", key=key, exc=e)
            raise CacheEncodeError("Failed to serialize value for cache.") from e

        await self._execute(self._client.set, key, prepared_value, ex=expires_in)
        self._logger.info("Cache key set successfully", key=key)

    async def delete(self, key: str) -> bool:
        self._logger.info("Deleting cache key", key=key)
        deleted_count = await self._execute(self._client.delete, key)
        result = deleted_count > 0
        self._logger.info("Cache key deletion completed", key=key, deleted=result)
        return result

    async def exists(self, key: str) -> bool:
        count = await self._execute(self._client.exists, key)
        return count > 0

    async def expire(self, key: str, seconds: int) -> bool:
        """
        Set a timeout on a key.
        """
        self._logger.info("Setting expiration on cache key", key=key, seconds=seconds)
        # Redis EXPIRE returns 1 if timeout was set, 0 if key doesn't exist
        result = await self._execute(self._client.expire, key, seconds)
        return bool(result)

    async def sadd(self, key: str, *values: str) -> int:
        """
        Add one or more members to a set.
        Returns the number of elements that were added.
        """
        self._logger.info("Adding members to cache set", key=key, count=len(values))
        return await self._execute(self._client.sadd, key, *values)

    async def srem(self, key: str, *values: str) -> int:
        """
        Remove one or more members from a set.
        Returns the number of members that were removed.
        """
        self._logger.info("Removing members from cache set", key=key, count=len(values))
        return await self._execute(self._client.srem, key, *values)

    async def smembers(self, key: str) -> Set[Any]:
        """
        Get all the members in a set and decode them to strings.
        """
        self._logger.info("Fetching members from cache set", key=key)
        raw_members = await self._execute(self._client.smembers, key)

        try:
            # Decode bytes to utf-8 strings for the Use Case layer
            return {
                m.decode("utf-8") if isinstance(m, bytes) else str(m)
                for m in raw_members
            }
        except Exception as e:
            self._logger.error("Failed to decode set members", key=key, exc=e)
            raise CacheDecodeError("Failed to decode set members.") from e
