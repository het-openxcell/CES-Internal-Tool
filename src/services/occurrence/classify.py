import re

VALID_SECTIONS: frozenset[str] = frozenset({"Surface", "Int.", "Main"})

VALID_OCCURRENCE_TYPES: frozenset[str] = frozenset({
    "BHA Failure",
    "Back Ream",
    "Bit Failure",
    "Casing Issue",
    "Cementing Issue",
    "Deviation",
    "Fishing",
    "H2S",
    "Kick / Well Control",
    "Lost Circulation",
    "Pack Off",
    "Ream",
    "Stuck Pipe",
    "Tight Hole",
    "Vibration",
    "Washout",
})

DEFAULT_SURFACE_SHOE_DEPTH: float = 600.0
DEFAULT_INTERMEDIATE_SHOE_DEPTH: float = 2500.0


def classify_type(text: str, keywords: dict[str, str]) -> str:
    for keyword, occurrence_type in sorted(keywords.items(), key=lambda kv: len(kv[0]), reverse=True):
        if re.search(r"\b" + re.escape(keyword) + r"\b", text, re.IGNORECASE):
            return occurrence_type
    return "Unclassified"


def classify_section(
    mmd: float | None,
    surface_shoe: float = DEFAULT_SURFACE_SHOE_DEPTH,
    intermediate_shoe: float = DEFAULT_INTERMEDIATE_SHOE_DEPTH,
) -> str | None:
    if surface_shoe >= intermediate_shoe:
        raise ValueError(f"surface_shoe ({surface_shoe}) must be less than intermediate_shoe ({intermediate_shoe})")
    if mmd is None:
        return None
    if mmd <= surface_shoe:
        return "Surface"
    if mmd <= intermediate_shoe:
        return "Int."
    return "Main"
