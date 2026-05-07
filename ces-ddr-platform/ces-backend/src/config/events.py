import asyncio
import typing

import loguru
from fastapi import FastAPI

from src.repository.events import dispose_db_connection, initialize_db_connection


def execute_backend_server_event_handler(backend_app: FastAPI) -> typing.Any:
    async def launch_backend_server_events() -> None:
        await initialize_db_connection(backend_app=backend_app)
        loguru.logger.info("Application startup completed")

    return launch_backend_server_events


def terminate_backend_server_event_handler(backend_app: FastAPI) -> typing.Any:
    @loguru.logger.catch
    async def stop_backend_server_events() -> None:
        loguru.logger.info("Starting application shutdown...")

        if hasattr(backend_app.state, "token_cleanup_task"):
            backend_app.state.token_cleanup_task.cancel()
            try:
                await backend_app.state.token_cleanup_task
            except asyncio.CancelledError:
                pass

        await dispose_db_connection(backend_app=backend_app)
        loguru.logger.info("Application shutdown completed")

    return stop_backend_server_events
