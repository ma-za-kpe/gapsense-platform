"""Tests for transactional database lifecycle behavior."""

from collections.abc import Callable
from types import TracebackType
from typing import Any, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from gapsense.core import database


class FakeSession:
    """Observable async session used to test transaction ownership."""

    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False
        self.closed = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def close(self) -> None:
        self.closed = True


class FakeSessionContext:
    """Async context manager matching the sessionmaker contract."""

    def __init__(self, session: FakeSession) -> None:
        self.session = session

    async def __aenter__(self) -> FakeSession:
        return self.session

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None


class FakeConnection:
    """Records schema operations passed through an engine transaction."""

    def __init__(self) -> None:
        self.operation: Callable[..., Any] | None = None

    async def run_sync(self, operation: Callable[..., Any]) -> None:
        self.operation = operation


class FakeBeginContext:
    """Async transaction context returned by the fake engine."""

    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection

    async def __aenter__(self) -> FakeConnection:
        return self.connection

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None


class FakeEngine:
    """Observable engine implementing the lifecycle surface under test."""

    def __init__(self) -> None:
        self.connection = FakeConnection()
        self.disposed = False

    def begin(self) -> FakeBeginContext:
        return FakeBeginContext(self.connection)

    async def dispose(self) -> None:
        self.disposed = True


async def test_get_db_commits_and_closes_successful_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Successful request work is committed and its session is closed."""
    session = FakeSession()
    monkeypatch.setattr(database, "AsyncSessionLocal", lambda: FakeSessionContext(session))
    dependency = database.get_db()

    assert await anext(dependency) is cast(AsyncSession, session)
    with pytest.raises(StopAsyncIteration):
        await anext(dependency)

    assert session.committed is True
    assert session.rolled_back is False
    assert session.closed is True


async def test_get_db_rolls_back_closes_and_reraises_request_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Failed request work is rolled back, closed, and never swallowed."""
    session = FakeSession()
    monkeypatch.setattr(database, "AsyncSessionLocal", lambda: FakeSessionContext(session))
    dependency = database.get_db()
    await anext(dependency)

    with pytest.raises(RuntimeError, match="request failed"):
        await dependency.athrow(RuntimeError("request failed"))

    assert session.committed is False
    assert session.rolled_back is True
    assert session.closed is True


async def test_database_schema_and_engine_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Development schema initialization and shutdown use the configured engine."""
    engine = FakeEngine()
    monkeypatch.setattr(database, "engine", engine)

    await database.init_db()
    await database.close_db()

    assert engine.connection.operation is not None
    assert engine.connection.operation.__name__ == "create_all"
    assert engine.disposed is True
