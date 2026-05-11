def _safe_float(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def density_join(mmd: float | None, mud_records: list[dict]) -> float | None:
    if not mud_records:
        return None
    # F2+F3: filter out records missing or non-numeric depth_md or mud_weight
    valid = [
        r for r in mud_records
        if _safe_float(r.get("depth_md")) is not None and _safe_float(r.get("mud_weight")) is not None
    ]
    if mmd is None:
        # F7: use deepest valid record so ordering of mud_records list does not matter
        if valid:
            deepest = max(valid, key=lambda r: _safe_float(r["depth_md"]))
            return _safe_float(deepest["mud_weight"])
        # F2: last-resort if no valid records — try the last record's mud_weight
        return _safe_float(mud_records[-1].get("mud_weight"))
    if not valid:  # F3: no records with usable depth_md
        return None
    nearest = min(valid, key=lambda r: abs(_safe_float(r["depth_md"]) - mmd))
    return _safe_float(nearest["mud_weight"])
