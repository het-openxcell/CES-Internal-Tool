import inspect
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, cast

from src.config.manager import settings

F = TypeVar("F", bound=Callable[..., Any])


class LangSmithTracingService:
    @classmethod
    def trace(
        cls,
        *,
        name: str,
        run_type: str = "chain",
        process_inputs: Callable[[dict], dict] | None = None,
        process_outputs: Callable[[dict], dict] | None = None,
    ) -> Callable[[F], F]:
        def decorator(func: F) -> F:
            if not cls.is_enabled():
                return func
            from langsmith import Client, traceable, tracing_context

            client = Client(
                api_key=settings.LANGSMITH_API_KEY,
                api_url=settings.LANGSMITH_ENDPOINT,
            )
            traced = traceable(
                name=name,
                run_type=run_type,
                project_name=settings.LANGSMITH_PROJECT,
                client=client,
                process_inputs=process_inputs,
                process_outputs=process_outputs,
                tags=cls.tags(),
            )(func)

            if inspect.iscoroutinefunction(func):
                @wraps(func)
                async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                    with tracing_context(
                        enabled=True,
                        project_name=settings.LANGSMITH_PROJECT,
                        client=client,
                        tags=cls.tags(),
                    ):
                        return await traced(*args, **kwargs)

                return cast(F, async_wrapper)

            @wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                with tracing_context(
                    enabled=True,
                    project_name=settings.LANGSMITH_PROJECT,
                    client=client,
                    tags=cls.tags(),
                ):
                    return traced(*args, **kwargs)

            return cast(F, sync_wrapper)

        return decorator

    @classmethod
    def is_enabled(cls) -> bool:
        return bool(settings.LANGSMITH_TRACING and settings.LANGSMITH_API_KEY)

    @classmethod
    def tags(cls) -> list[str]:
        return [tag.strip() for tag in settings.LANGSMITH_TAGS.split(",") if tag.strip()]

    @staticmethod
    def safe_inputs(inputs: dict) -> dict:
        return LangSmithTracingService._safe_payload(inputs)

    @staticmethod
    def safe_outputs(outputs: dict) -> dict:
        return LangSmithTracingService._safe_payload(outputs)

    @staticmethod
    def _safe_payload(payload: Any) -> Any:
        if isinstance(payload, bytes):
            return {"type": "bytes", "size": len(payload)}
        if isinstance(payload, dict):
            return {key: LangSmithTracingService._safe_payload(value) for key, value in payload.items()}
        if isinstance(payload, list):
            return [LangSmithTracingService._safe_payload(item) for item in payload[:20]]
        if isinstance(payload, tuple):
            return tuple(LangSmithTracingService._safe_payload(item) for item in payload[:20])
        if isinstance(payload, str) and len(payload) > settings.LANGSMITH_MAX_STRING_LENGTH:
            return f"{payload[: settings.LANGSMITH_MAX_STRING_LENGTH]}..."
        return payload
