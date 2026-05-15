from src.constants.occurrence import DEFAULT_INTERMEDIATE_SHOE_DEPTH, DEFAULT_SURFACE_SHOE_DEPTH
from src.models.schemas.ddr import DDRDateStatus
from src.services.keywords.loader import KeywordLoader
from src.services.occurrence.classify import OccurrenceClassifier
from src.services.occurrence.dedup import OccurrenceDeduplicator
from src.services.occurrence.density_join import DensityJoinService
from src.services.occurrence.infer_mmd import MMDInferenceService


class OccurrenceGenerationService:
    def __init__(self, ddr_date_repository, occurrence_repository) -> None:
        self.ddr_date_repository = ddr_date_repository
        self.occurrence_repository = occurrence_repository

    async def generate_for_ddr(
        self,
        ddr_id: str,
        ddr_well_name: str | None = None,
        ddr_surface_location: str | None = None,
        surface_shoe: float = DEFAULT_SURFACE_SHOE_DEPTH,
        intermediate_shoe: float = DEFAULT_INTERMEDIATE_SHOE_DEPTH,
    ) -> int:
        if surface_shoe >= intermediate_shoe:
            raise ValueError(
                f"surface_shoe ({surface_shoe}) must be less than intermediate_shoe ({intermediate_shoe})"
            )

        keywords = KeywordLoader.get_keywords()
        rows = await self.ddr_date_repository.read_dates_by_ddr_id(ddr_id)
        successful_rows = [r for r in rows if r.status == DDRDateStatus.SUCCESS]

        all_occurrences: list[dict] = []
        for row in successful_rows:
            final_json = row.final_json or {}
            time_logs = final_json.get("time_logs") or []
            mud_records = final_json.get("mud_records") or []

            for i, tl in enumerate(time_logs):
                if not isinstance(tl, dict):
                    continue
                activity = tl.get("activity") or ""
                comment = tl.get("comment") or ""
                text = f"{activity} {comment}".strip() if comment else activity
                occ_type = OccurrenceClassifier.classify_type(text, keywords)
                if occ_type == "Unclassified":
                    continue
                mmd = MMDInferenceService.infer_mmd(i, time_logs)
                section = OccurrenceClassifier.classify_section(mmd, surface_shoe, intermediate_shoe)
                density = DensityJoinService.density_join(mmd, mud_records)
                all_occurrences.append({
                    "ddr_id": ddr_id,
                    "ddr_date_id": row.id,
                    "type": occ_type,
                    "mmd": mmd,
                    "section": section,
                    "density": density,
                    "well_name": ddr_well_name,
                    "surface_location": ddr_surface_location,
                    "notes": text if text else None,
                    "date": row.date,
                    "page_number": tl.get("page_number"),
                })

        deduped = OccurrenceDeduplicator.dedup(all_occurrences)
        await self.occurrence_repository.replace_for_ddr(ddr_id, deduped)
        return len(deduped)
