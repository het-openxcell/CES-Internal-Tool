from src.services.pipeline.page_numbers import TimeLogPageNumberNormalizer


def test_single_source_page_fills_missing_and_invalid_values() -> None:
    payload = {"time_logs": [{"page_number": None}, {"page_number": 99}]}

    result = TimeLogPageNumberNormalizer().normalize(payload, [5])

    assert [row["page_number"] for row in result["time_logs"]] == [5, 5]


def test_multiple_source_pages_maps_local_pages_to_original_pages() -> None:
    payload = {"time_logs": [{"page_number": 1}, {"page_number": 2}, {"page_number": 5}, {"page_number": 99}]}

    result = TimeLogPageNumberNormalizer().normalize(payload, [5, 6])

    assert [row["page_number"] for row in result["time_logs"]] == [5, 6, 5, None]


def test_ambiguous_page_keeps_original_when_payload_does_not_look_chunk_local() -> None:
    payload = {"time_logs": [{"page_number": 2}, {"page_number": 3}]}

    result = TimeLogPageNumberNormalizer().normalize(payload, [2, 3])

    assert [row["page_number"] for row in result["time_logs"]] == [2, 3]


def test_ambiguous_page_maps_local_when_payload_has_chunk_local_sequence() -> None:
    payload = {"time_logs": [{"page_number": 1}, {"page_number": 2}]}

    result = TimeLogPageNumberNormalizer().normalize(payload, [2, 3])

    assert [row["page_number"] for row in result["time_logs"]] == [2, 3]


def test_no_source_pages_leaves_payload_unchanged() -> None:
    payload = {"time_logs": [{"page_number": 1}]}

    result = TimeLogPageNumberNormalizer().normalize(payload, None)

    assert result is payload
