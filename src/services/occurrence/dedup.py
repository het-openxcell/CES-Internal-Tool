from src.utilities.logging.logger import logger


def dedup(occurrences: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    result: list[dict] = []
    removed = 0
    for occ in occurrences:
        # F6: include ddr_date_id so same-type/depth events on different dates are not merged
        key = (occ.get("type"), occ.get("mmd"), occ.get("ddr_date_id"))
        if key not in seen:
            seen.add(key)
            result.append(occ)
        else:
            removed += 1
    if removed:
        logger.info("dedup: removed %d duplicate occurrence(s)", removed)
    return result
