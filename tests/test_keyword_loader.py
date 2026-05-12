from src.services.keywords.loader import KeywordLoader

ALL_TYPES = {
    "Anhydrite",
    "Back Ream",
    "Ballooning",
    "Bit Balling",
    "Bit DBR",
    "Blowout",
    "CO2",
    "Calcite",
    "Cement Plug",
    "Coal",
    "F.I.T. / L.O.T.",
    "Fishing",
    "Foaming",
    "Formation Fracture",
    "Gas Spike",
    "Gravel",
    "H2S",
    "High Torque",
    "Kick / Well Control",
    "Lost Circulation",
    "Mud Ring",
    "Other",
    "Pressure Loss",
    "Pressure Spike",
    "Ream",
    "Sand",
    "Sidetrack",
    "Sloughing",
    "Stuck Pipe",
    "Tight Hole",
    "Tool Failure",
    "Water Flow",
}


def setup_function():
    KeywordLoader.load()


def test_load_populates_keywords() -> None:
    keywords = KeywordLoader.get_keywords()
    assert len(keywords) > 0


def test_keywords_are_str_to_str() -> None:
    keywords = KeywordLoader.get_keywords()
    for k, v in keywords.items():
        assert isinstance(k, str)
        assert isinstance(v, str)


def test_all_types_covered() -> None:
    keywords = KeywordLoader.get_keywords()
    types_in_file = set(keywords.values())
    assert ALL_TYPES <= types_in_file, f"Missing types: {ALL_TYPES - types_in_file}"


def test_unclassified_not_in_keywords() -> None:
    keywords = KeywordLoader.get_keywords()
    assert "Unclassified" not in keywords.values()


def test_at_least_one_keyword_per_type() -> None:
    keywords = KeywordLoader.get_keywords()
    for occurrence_type in ALL_TYPES:
        matches = [k for k, v in keywords.items() if v == occurrence_type]
        assert len(matches) >= 1, f"No keywords for type: {occurrence_type}"


def test_reload_replaces_dict() -> None:
    original = KeywordLoader.get_keywords().copy()
    new_data = {"test keyword": "Test Type"}
    try:
        KeywordLoader.reload(new_data)
        assert KeywordLoader.get_keywords() == new_data
    finally:
        KeywordLoader.reload(original)


def test_reload_atomic_replacement() -> None:
    KeywordLoader.load()
    before = KeywordLoader.get_keywords()
    try:
        KeywordLoader.reload({"a": "A"})
        assert KeywordLoader.get_keywords() == {"a": "A"}
    finally:
        KeywordLoader.reload(before)
