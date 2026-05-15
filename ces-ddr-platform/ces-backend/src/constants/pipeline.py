DDR_METADATA_KEYS = frozenset({"well_name", "surface_location"})

GEMINI_BACKOFF_SECONDS = (1.0, 2.0, 4.0, 8.0)
GEMINI_RATE_LIMIT_SIGNALS = ("429", "rate limit", "resource_exhausted", "quota", "too many requests")

NO_BOUNDARY_PLACEHOLDER_DATE = "00000000"
NO_BOUNDARY_REASON = "No date boundaries detected"

DATE_SERIAL_PATTERN = r"\b[A-Z0-9]{2,10}_(\d{8})_\d[A-Z]\b"
TRUNCATED_DATE_SERIAL_PATTERN = r"(?<!\d)(0[2-9]\d{5})_\d[A-Z]\b"
RAW_TEXT_PREVIEW_CHARS = 500
