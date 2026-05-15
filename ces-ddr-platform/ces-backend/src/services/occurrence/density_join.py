class DensityJoinService:
    @staticmethod
    def density_join(mmd: float | None, mud_records: list[dict]) -> float | None:
        if not mud_records:
            return None
        valid = [
            record
            for record in mud_records
            if DensityJoinService.safe_float(record.get("depth_md")) is not None
            and DensityJoinService.safe_float(record.get("mud_weight")) is not None
        ]
        if mmd is None:
            if valid:
                deepest = max(valid, key=lambda record: DensityJoinService.safe_float(record["depth_md"]) or 0.0)
                return DensityJoinService.safe_float(deepest["mud_weight"])
            return DensityJoinService.safe_float(mud_records[-1].get("mud_weight"))
        if not valid:
            return None
        nearest = min(valid, key=lambda record: abs((DensityJoinService.safe_float(record["depth_md"]) or 0.0) - mmd))
        return DensityJoinService.safe_float(nearest["mud_weight"])

    @staticmethod
    def safe_float(value: object) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
