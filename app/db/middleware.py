from contextvars import ContextVar
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.types import ASGIApp, Receive, Scope, Send
from starlite import MiddlewareProtocol, Request

from app.db.base import async_session


session_context_var: ContextVar[Optional[AsyncSession]] = ContextVar("_session", default=None)


class SQLAlchemySessionMiddleware(MiddlewareProtocol):
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        db = async_session()
        token = session_context_var.set(db)
        try:
            await self.app(scope, receive, send)
        finally:
            await db.close()
            session_context_var.reset(token)


async def set_db():
    """Store db session in the context var and reset it"""
    db = async_session()
    token = session_context_var.set(db)
    try:
        yield
    finally:
        await db.close()
        session_context_var.reset(token)


def get_db():
    """Fetch db session from the context var"""
    session = session_context_var.get()
    if session is None:
        raise Exception("Missing session")
    return session
