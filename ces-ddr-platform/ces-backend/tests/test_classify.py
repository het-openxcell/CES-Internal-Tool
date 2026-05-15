import pytest
from pydantic import ValidationError

from src.models.schemas.occurrence import OccurrenceInCreate
from src.services.occurrence.classify import OccurrenceClassifier


def _base_occurrence(**kwargs: object) -> dict:
    return {"ddr_id": "d1", "ddr_date_id": "dd1", "well_name": "W1", "type": "Stuck Pipe", **kwargs}


def test_occurrence_section_accepts_none() -> None:
    obj = OccurrenceInCreate(**_base_occurrence(section=None))
    assert obj.section is None


def test_occurrence_section_accepts_valid_values() -> None:
    for section in ("Surface", "Int.", "Main"):
        obj = OccurrenceInCreate(**_base_occurrence(section=section))
        assert obj.section == section


def test_occurrence_section_rejects_invalid_value() -> None:
    with pytest.raises(ValidationError):
        OccurrenceInCreate(**_base_occurrence(section="Deep"))


def test_occurrence_section_rejects_empty_string() -> None:
    with pytest.raises(ValidationError):
        OccurrenceInCreate(**_base_occurrence(section=""))


def test_classify_type_returns_matching_type() -> None:
    keywords = {"stuck pipe": "Stuck Pipe", "lost circulation": "Lost Circulation"}
    assert OccurrenceClassifier.classify_type("stuck pipe encountered", keywords) == "Stuck Pipe"
    assert OccurrenceClassifier.classify_type("lost circulation during drilling", keywords) == "Lost Circulation"


def test_classify_type_word_order_matters() -> None:
    # keyword "stuck pipe" does not match "pipe stuck" — substring must appear verbatim
    keywords = {"stuck pipe": "Stuck Pipe", "lost circulation": "Lost Circulation"}
    assert OccurrenceClassifier.classify_type("pipe stuck in formation", keywords) == "Unclassified"


def test_classify_type_case_insensitive() -> None:
    keywords = {"stuck pipe": "Stuck Pipe"}
    assert OccurrenceClassifier.classify_type("STUCK PIPE AT 2000m", keywords) == "Stuck Pipe"
    assert OccurrenceClassifier.classify_type("Stuck Pipe encountered", keywords) == "Stuck Pipe"


def test_classify_type_first_match_wins() -> None:
    keywords = {"stuck pipe": "Stuck Pipe", "pipe": "Other Type"}
    assert OccurrenceClassifier.classify_type("stuck pipe", keywords) == "Stuck Pipe"


def test_classify_type_unclassified_when_no_match() -> None:
    keywords = {"stuck pipe": "Stuck Pipe"}
    assert OccurrenceClassifier.classify_type("normal drilling operations", keywords) == "Unclassified"


def test_classify_type_empty_keywords_returns_unclassified() -> None:
    assert OccurrenceClassifier.classify_type("stuck pipe in hole", {}) == "Unclassified"


def test_classify_type_empty_text_returns_unclassified() -> None:
    keywords = {"stuck pipe": "Stuck Pipe"}
    assert OccurrenceClassifier.classify_type("", keywords) == "Unclassified"


def test_classify_type_multiword_keyword() -> None:
    keywords = {"lost circulation": "Lost Circulation"}
    assert OccurrenceClassifier.classify_type("experienced lost circulation at 2000m", keywords) == "Lost Circulation"


def test_classify_section_surface_boundary() -> None:
    assert OccurrenceClassifier.classify_section(0.0) == "Surface"
    assert OccurrenceClassifier.classify_section(600.0) == "Surface"


def test_classify_section_intermediate_boundary() -> None:
    assert OccurrenceClassifier.classify_section(600.1) == "Int."
    assert OccurrenceClassifier.classify_section(2500.0) == "Int."


def test_classify_section_main() -> None:
    assert OccurrenceClassifier.classify_section(2500.1) == "Main"
    assert OccurrenceClassifier.classify_section(5000.0) == "Main"


def test_classify_section_none_mmd() -> None:
    assert OccurrenceClassifier.classify_section(None) is None


def test_classify_section_custom_shoes() -> None:
    assert OccurrenceClassifier.classify_section(400.0, surface_shoe=500.0, intermediate_shoe=2000.0) == "Surface"
    assert OccurrenceClassifier.classify_section(500.0, surface_shoe=500.0, intermediate_shoe=2000.0) == "Surface"
    assert OccurrenceClassifier.classify_section(501.0, surface_shoe=500.0, intermediate_shoe=2000.0) == "Int."
    assert OccurrenceClassifier.classify_section(1500.0, surface_shoe=500.0, intermediate_shoe=2000.0) == "Int."
    assert OccurrenceClassifier.classify_section(2000.0, surface_shoe=500.0, intermediate_shoe=2000.0) == "Int."
    assert OccurrenceClassifier.classify_section(2001.0, surface_shoe=500.0, intermediate_shoe=2000.0) == "Main"


def test_classify_section_raises_on_inverted_shoes() -> None:
    with pytest.raises(ValueError, match="surface_shoe"):
        OccurrenceClassifier.classify_section(1000.0, surface_shoe=2000.0, intermediate_shoe=500.0)


def test_classify_section_raises_when_shoes_equal() -> None:
    with pytest.raises(ValueError, match="surface_shoe"):
        OccurrenceClassifier.classify_section(500.0, surface_shoe=600.0, intermediate_shoe=600.0)
