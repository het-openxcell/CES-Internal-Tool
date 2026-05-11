def density_join(mmd: float | None, mud_records: list[dict]) -> float | None:
    if not mud_records:
        return None
    # F2+F3: filter out records missing depth_md or mud_weight before any join
    valid = [
        r for r in mud_records
        if r.get("depth_md") is not None and r.get("mud_weight") is not None
    ]
    if mmd is None:
        # F7: use deepest valid record so ordering of mud_records list does not matter
        if valid:
            deepest = max(valid, key=lambda r: float(r["depth_md"]))
            return float(deepest["mud_weight"])
        # F2: last-resort if no valid records — try the last record's mud_weight
        w = mud_records[-1].get("mud_weight")
        return float(w) if w is not None else None
    if not valid:  # F3: no records with usable depth_md
        return None
    nearest = min(valid, key=lambda r: abs(float(r["depth_md"]) - mmd))
    return float(nearest["mud_weight"])
