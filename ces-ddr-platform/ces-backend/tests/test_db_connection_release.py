import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from src.securities.authorizations import jwt_authentication
from src.services.ddr_status import DDRStatusSnapshotFactory
from src.services.processing_status import ProcessingStatusStreamService


class TrackingSession:
    def __init__(self, user: Any = None) -> None:
        self.user = user
        self.closed = False

    async def __aenter__(self) -> "TrackingSession":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    async def execute(self, statement: Any = None, **_: Any) -> Any:
        return SimpleNamespace(scalar_one_or_none=lambda: self.user)

    async def close(self) -> None:
        self.closed = True


class EventLoopRunner:
    @staticmethod
    def run(coroutine: Any) -> Any:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coroutine)
        finally:
            loop.close()


class SnapshotRepository:
    def __init__(self, session: TrackingSession, ddr: Any = None, rows: list[Any] | None = None) -> None:
        self.async_session = session
        self.ddr = ddr
        self.rows = rows or []

    async def read_by_id(self, ddr_id: str) -> Any:
        return self.ddr

    async def read_dates_by_ddr_id(self, ddr_id: str) -> list[Any]:
        return self.rows


def test_get_current_user_reuses_request_session() -> None:
    session = TrackingSession(user=SimpleNamespace(id="user-1", is_active=True, roles=[]))

    user = EventLoopRunner.run(jwt_authentication.get_current_user(user_id="user-1", async_session=session))

    assert user is not None
    assert session.closed is False


def test_get_current_user_reuses_request_session_for_inactive_user() -> None:
    session = TrackingSession(user=SimpleNamespace(id="user-1", is_active=False, roles=[]))

    assert EventLoopRunner.run(jwt_authentication.get_current_user(user_id="user-1", async_session=session)) is None
    assert session.closed is False


def test_authenticate_token_propagates_database_errors(monkeypatch) -> None:
    class FailingSession(TrackingSession):
        async def execute(self, statement: Any = None, **_: Any) -> Any:
            raise TimeoutError("QueuePool limit reached")

    monkeypatch.setattr(
        jwt_authentication.jwt_generator,
        "retrieve_details_from_token",
        lambda token: {"user_id": "user-1", "jti": "jti-1", "token_type": "access", "raw_payload": {}},
    )

    with pytest.raises(TimeoutError):
        EventLoopRunner.run(
            jwt_authentication.authenticate_token(
                request=SimpleNamespace(state=SimpleNamespace()),
                token="token",
                async_session=FailingSession(),
            )
        )


def test_snapshot_factory_releases_sessions_before_streaming() -> None:
    ddr_session = TrackingSession()
    date_session = TrackingSession()
    ddr = SimpleNamespace(id="ddr-1", status="processing")
    rows = [SimpleNamespace(id="date-1", ddr_id="ddr-1", date="20241031", status="queued", error_log=None)]
    factory = DDRStatusSnapshotFactory(
        "ddr-1",
        SnapshotRepository(ddr_session, ddr=ddr),
        SnapshotRepository(date_session, rows=rows),
        ProcessingStatusStreamService(),
    )

    EventLoopRunner.run(factory.events())

    assert ddr_session.closed is True
    assert date_session.closed is True


def test_snapshot_factory_releases_sessions_for_missing_ddr() -> None:
    ddr_session = TrackingSession()
    date_session = TrackingSession()
    factory = DDRStatusSnapshotFactory(
        "missing",
        SnapshotRepository(ddr_session),
        SnapshotRepository(date_session),
        ProcessingStatusStreamService(),
    )

    assert EventLoopRunner.run(factory.events()) == []
    assert ddr_session.closed is True
    assert date_session.closed is True
