from typing import Any


class CorrectionContextBuilder:
    MAX_INJECTED_CORRECTIONS = 20

    def __init__(self, correction_repository: Any) -> None:
        self.correction_repository = correction_repository

    async def build(self, ddr_id: str | None = None) -> str:
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

    async def _recent_corrections(self, ddr_id: str | None) -> list[Any]:
        if ddr_id:
            return await self.correction_repository.get_by_ddr_id(ddr_id, limit=self.MAX_INJECTED_CORRECTIONS)
        return await self.correction_repository.get_recent(self.MAX_INJECTED_CORRECTIONS)
