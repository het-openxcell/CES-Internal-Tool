import asyncio
import typing

from fastapi import FastAPI

from src.repository.crud.ddr import DDRCRUDRepository, ProcessingQueueCRUDRepository
from src.repository.events import dispose_db_connection, initialize_db_connection
from src.services.ddr import DDRProcessingTask
from src.services.keywords.loader import KeywordLoader
from src.services.processing_resume import DDRProcessingResumeService
from src.services.processing_status import ProcessingStatusStreamService
from src.utilities.logging.logger import logger


def execute_backend_server_event_handler(backend_app: FastAPI) -> typing.Any:
    async def launch_backend_server_events() -> None:
        await initialize_db_connection(backend_app=backend_app)
        KeywordLoader.load()
        backend_app.state.processing_status_stream_service = ProcessingStatusStreamService()
        backend_app.state.ddr_resume_task = asyncio.create_task(resume_ddr_processing(backend_app))
        logger.info("Application startup completed")

    return launch_backend_server_events


def terminate_backend_server_event_handler(backend_app: FastAPI) -> typing.Any:
    async def stop_backend_server_events() -> None:
        logger.info("Starting application shutdown...")

        backend_app.state.ddr_resume_task.cancel()
        try:
            await backend_app.state.ddr_resume_task
        except asyncio.CancelledError:
            pass

        await dispose_db_connection(backend_app=backend_app)
        logger.info("Application shutdown completed")

    return stop_backend_server_events


async def resume_ddr_processing(backend_app: FastAPI) -> None:
    async_session_factory = backend_app.state.db.async_session_factory
    async with async_session_factory() as session:
        service = DDRProcessingResumeService(
            ddr_repository=DDRCRUDRepository(async_session=session),
            processing_queue_repository=ProcessingQueueCRUDRepository(async_session=session),
            processing_task=DDRProcessingTask(
                session_factory=async_session_factory,
                status_stream_service=backend_app.state.processing_status_stream_service,
            ),
        )
        await service.resume()
