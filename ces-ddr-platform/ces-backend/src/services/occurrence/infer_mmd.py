class MMDInferenceService:
    @staticmethod
    def infer_mmd(time_log_index: int, time_logs: list[dict], max_lookback: int = 5) -> float | None:
        if not 0 <= time_log_index < len(time_logs):
            raise ValueError(f"time_log_index {time_log_index} out of range for time_logs of length {len(time_logs)}")
        row = time_logs[time_log_index]
        if not isinstance(row, dict):
            return None
        depth = row.get("depth_md")
        if depth is not None:
            try:
                return float(depth)
            except (TypeError, ValueError):
                pass
        stop = max(time_log_index - 1 - max_lookback, -1)
        for index in range(time_log_index - 1, stop, -1):
            previous_row = time_logs[index]
            if not isinstance(previous_row, dict):
                continue
            previous_depth = previous_row.get("depth_md")
            if previous_depth is not None:
                try:
                    return float(previous_depth)
                except (TypeError, ValueError):
                    continue
        return None
