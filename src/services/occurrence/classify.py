import re

from src.constants.occurrence import DEFAULT_INTERMEDIATE_SHOE_DEPTH, DEFAULT_SURFACE_SHOE_DEPTH


class OccurrenceClassifier:
    @staticmethod
    def classify_type(text: str, keywords: dict[str, str]) -> str:
        for keyword, occurrence_type in sorted(keywords.items(), key=lambda kv: len(kv[0]), reverse=True):
            if re.search(r"\b" + re.escape(keyword) + r"\b", text, re.IGNORECASE):
                return occurrence_type
        return "Unclassified"

    @staticmethod
    def classify_section(
        mmd: float | None,
        surface_shoe: float | None = None,
        intermediate_shoe: float | None = None,
    ) -> str | None:
        surface_shoe = surface_shoe or DEFAULT_SURFACE_SHOE_DEPTH
        intermediate_shoe = intermediate_shoe or DEFAULT_INTERMEDIATE_SHOE_DEPTH
        if surface_shoe >= intermediate_shoe:
            raise ValueError(f"surface_shoe ({surface_shoe}) must be less than intermediate_shoe ({intermediate_shoe})")
        if mmd is None:
            return None
        if mmd <= surface_shoe:
            return "Surface"
        if mmd <= intermediate_shoe:
            return "Int."
        return "Main"
