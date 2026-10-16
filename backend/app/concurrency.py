import asyncio
from functools import wraps

from starlette.concurrency import run_in_threadpool


class DatabaseConcurrencyMiddleware:
    """Leave pool capacity for cleanup and the round clock during request bursts."""

    def __init__(self, app, max_concurrent=10):
        self.app = app
        # The SQLAlchemy pool allows 15 connections. Admit fewer DB requests so
        # auth dependencies cannot occupy every worker while endpoints queue.
        self.slots = asyncio.Semaphore(max_concurrent)

    async def __call__(self, scope, receive, send):
        kind = scope['type']
        path = scope.get('path', '')
        if not ((kind == 'http' and path.startswith('/api/')) or
                (kind == 'websocket' and path.startswith('/ws/'))):
            return await self.app(scope, receive, send)

        await self.slots.acquire()
        released = False

        def release():
            nonlocal released
            if not released:
                released = True
                self.slots.release()

        async def send_message(message):
            # Established sockets use no database connection and need no slot.
            if message['type'] in ('websocket.accept', 'websocket.close'):
                release()
            await send(message)

        try:
            await self.app(scope, receive, send_message)
        finally:
            release()


def database_worker(function):
    """Keep synchronous SQLAlchemy/Redis work off the ASGI event loop."""
    @wraps(function)
    async def endpoint(*args, **kwargs):
        return await run_in_threadpool(function, *args, **kwargs)

    return endpoint
