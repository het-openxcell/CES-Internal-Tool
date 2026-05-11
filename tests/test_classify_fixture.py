import json
from pathlib import Path

from src.services.keywords.loader import KeywordLoader
from src.services.occurrence.classify import classify_type


def test_fixture_accuracy() -> None:
    KeywordLoader.load()
    keywords = KeywordLoader.get_keywords()
    fixtures_path = Path(__file__).parent / "fixtures" / "expected_occurrences.json"
    cases = json.loads(fixtures_path.read_text())

    failures = [
        f"  [{c['expected_type']}] expected but got [{classify_type(c['text'], keywords)}] for: {c['text']!r}"
        for c in cases
        if classify_type(c["text"], keywords) != c["expected_type"]
    ]
    correct = len(cases) - len(failures)
    accuracy = correct / len(cases)

    assert accuracy >= 0.90, (
        f"Accuracy {accuracy:.1%} below 90% ({correct}/{len(cases)} correct)\n"
        + "\n".join(failures)
    )
