def infer_mmd(time_log_index: int, time_logs: list[dict]) -> float | None:
    # Precondition (F8): time_logs must be scoped to a single ddr_date — caller must not
    # pass a concatenated multi-date list; the backward scan does not respect date boundaries.
    if not 0 <= time_log_index < len(time_logs):  # F1: bounds guard
        raise ValueError(
            f"time_log_index {time_log_index} out of range for time_logs of length {len(time_logs)}"
        )
    row = time_logs[time_log_index]
    if not isinstance(row, dict):  # F9: non-dict element
        return None
    d = row.get("depth_md")
    if d is not None:
        try:
            return float(d)  # F4: guard non-numeric strings from LLM output
        except (TypeError, ValueError):
            pass  # treat unparseable depth as absent; fall through to backward scan
    for i in range(time_log_index - 1, -1, -1):
        row_i = time_logs[i]
        if not isinstance(row_i, dict):  # F9
            continue
        d = row_i.get("depth_md")
        if d is not None:
            try:
                return float(d)  # F4
            except (TypeError, ValueError):
                continue
    return None
