from __future__ import annotations
from typing import Optional
import httpx

client: Optional[httpx.AsyncClient] = None


def initialize() -> httpx.AsyncClient:
    global client
    if client is None:
        client = httpx.AsyncClient()
    return client


async def close() -> None:
    global client
    if client is not None:
        await client.aclose()
        client = None

