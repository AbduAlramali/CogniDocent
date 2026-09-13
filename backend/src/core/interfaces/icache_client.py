from abc import ABC, abstractmethod
from typing import Any, Set


class ICacheClient(ABC):
    @abstractmethod
    async def get(self, key: str) -> Any:
        """
        Retrieve a value from the cache.
        Returns None if the key does not exist (cache miss).
        """
        ...

    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        expires_in: int | None = None,
    ) -> None:
        """
        Store a value in the cache.
        :param expires_in: Time-to-live (TTL) in seconds.
                           If None, the key never expires.
        """
        ...

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Remove a key from the cache.
        Returns True if the key was deleted, False if it didn't exist.
        """
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in the cache without fetching its value.
        """
        ...

    @abstractmethod
    async def expire(self, key: str, seconds: int) -> bool:
        """
        Set a timeout on a key.
        Returns True if the timeout was set, False if key doesn't exist.
        """
        ...

    @abstractmethod
    async def sadd(self, key: str, *values: str) -> int:
        """
        Add one or more members to a set.
        Returns the number of elements that were added to the set.
        """
        ...

    @abstractmethod
    async def smembers(self, key: str) -> Set[Any]:
        """
        Get all the members in a set.
        """
        ...

    @abstractmethod
    async def srem(self, key: str, *values: str) -> int:
        """
        Remove one or more members from a set.
        Necessary for logging out a single session while keeping others.
        """
        ...
