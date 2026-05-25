from typing import Any


class CorrectionContextBuilder:
    MAX_INJECTED_SUMMARIES = 12
    MAX_INJECTED_CORRECTIONS = 20

    def __init__(self, correction_repository: Any, correction_summary_repository: Any | None = None) -> None:
        self.correction_repository = correction_repository
        self.correction_summary_repository = correction_summary_repository

    async def build(self, ddr_id: str | None = None) -> str:
        summary_context = await self._summary_context(ddr_id)
        correction_context = await self._correction_context(ddr_id)
        return "\n".join(part for part in (summary_context, correction_context) if part)

    async def _correction_context(self, ddr_id: str | None = None) -> str:
        corrections = await self._recent_corrections(ddr_id)
        corrections = corrections[: self.MAX_INJECTED_CORRECTIONS]
        if not corrections:
            return ""

        groups: dict[tuple, dict] = {}
        for c in corrections:
            key = (c.field_name, c.original_value, c.corrected_value)
            if key not in groups:
                groups[key] = {"count": 1, "most_recent_reason": c.reason}
            else:
                groups[key]["count"] += 1

        lines = [
            f"Field '{fn}': '{ov}' corrected to '{cv}' ({g['count']} times). Reason: {g['most_recent_reason']}"
            for (fn, ov, cv), g in groups.items()
        ]
        return "\n".join(lines)

    async def _summary_context(self, ddr_id: str | None) -> str:
        if self.correction_summary_repository is None:
            return ""
        summaries: list[Any] = []
        if ddr_id:
            summaries = await self.correction_summary_repository.get_by_ddr_id(
                ddr_id,
                limit=self.MAX_INJECTED_SUMMARIES,
            )
        if not summaries:
            summaries = await self.correction_summary_repository.get_recent(
                limit=self.MAX_INJECTED_SUMMARIES,
            )
        if not summaries:
            return ""
        lines = []
        for summary in summaries[: self.MAX_INJECTED_SUMMARIES]:
            date = getattr(summary, "date", None) or getattr(summary, "ddr_date_id", "date")
            text = getattr(summary, "summary", "") or ""
            if text:
                lines.append(f"[{date}] {text}")
        return "\n".join(lines)

    async def _recent_corrections(self, ddr_id: str | None) -> list[Any]:
        recent = await self.correction_repository.get_recent(self.MAX_INJECTED_CORRECTIONS)
        if not ddr_id:
            return recent
        ddr_specific = await self.correction_repository.get_by_ddr_id(ddr_id, limit=self.MAX_INJECTED_CORRECTIONS)
        seen: set = set()
        merged: list[Any] = []
        for c in [*ddr_specific, *recent]:
            key = getattr(c, "id", None)
            if key is not None and key in seen:
                continue
            if key is not None:
                seen.add(key)
            merged.append(c)
        return merged[: self.MAX_INJECTED_CORRECTIONS]
