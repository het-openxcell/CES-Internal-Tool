from src.utilities.logging.logger import logger


class OccurrenceDeduplicator:
    @staticmethod
    def dedup(occurrences: list[dict]) -> list[dict]:
        seen: set[tuple] = set()
        result: list[dict] = []
        removed = 0
        for occ in occurrences:
            key = (occ.get("type"), occ.get("mmd"), occ.get("ddr_date_id"))
            if key not in seen:
                seen.add(key)
                result.append(occ)
            else:
                removed += 1
        if removed:
            logger.info(f"dedup: removed {removed} duplicate occurrence(s)")
        return result
