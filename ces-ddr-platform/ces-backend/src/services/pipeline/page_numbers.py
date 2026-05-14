from copy import copy
from typing import Any


class TimeLogPageNumberNormalizer:
    def normalize(self, final_json: dict[str, Any], source_page_numbers: list[int] | None) -> dict[str, Any]:
        pages = self._clean_pages(source_page_numbers)
        if not pages:
            return final_json
        normalized = copy(final_json)
        raw_time_logs = final_json.get("time_logs")
        if not isinstance(raw_time_logs, list):
            return normalized
        local_page_mode = self._looks_like_chunk_local_pages(raw_time_logs, pages)
        normalized["time_logs"] = [
            self._normalize_time_log(time_log, pages, local_page_mode) for time_log in raw_time_logs
        ]
        return normalized

    def _normalize_time_log(self, time_log: Any, pages: list[int], local_page_mode: bool) -> Any:
        if not isinstance(time_log, dict):
            return time_log
        normalized = dict(time_log)
        normalized["page_number"] = self._normalize_page_number(
            normalized.get("page_number"),
            pages,
            local_page_mode,
        )
        return normalized

    def _normalize_page_number(self, page_number: Any, pages: list[int], local_page_mode: bool) -> int | None:
        if len(pages) == 1:
            return pages[0]
        if isinstance(page_number, int):
            if local_page_mode and 1 <= page_number <= len(pages):
                return pages[page_number - 1]
            if page_number in pages:
                return page_number
            if 1 <= page_number <= len(pages):
                return pages[page_number - 1]
        return None

    def _looks_like_chunk_local_pages(self, time_logs: list[Any], pages: list[int]) -> bool:
        if len(pages) <= 1:
            return False
        raw_pages = [time_log.get("page_number") for time_log in time_logs if isinstance(time_log, dict)]
        numeric_pages = [page for page in raw_pages if isinstance(page, int)]
        if not numeric_pages:
            return False
        local_values = set(range(1, len(pages) + 1))
        return all(page in local_values for page in numeric_pages) and any(page not in pages for page in numeric_pages)

    def _clean_pages(self, source_page_numbers: list[int] | None) -> list[int]:
        if not source_page_numbers:
            return []
        return sorted({page for page in source_page_numbers if isinstance(page, int) and page > 0})
