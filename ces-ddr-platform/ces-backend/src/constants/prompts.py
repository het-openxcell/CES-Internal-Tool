class LLMPrompts:
    @staticmethod
    def ddr_extraction(
        date: str,
        sections: str,
        time_log_fields: str,
        original_page_numbers: list[int] | None = None,
    ) -> str:
        page_context = ""
        if original_page_numbers:
            pages = ", ".join(str(page_number) for page_number in original_page_numbers)
            page_context = (
                f" This date chunk comes from original whole-PDF page number(s): {pages}. "
                "For every time_logs.page_number value, use the original whole-PDF page number, not the chunk-local page number."
            )
        return (
            "You are extracting structured data from a Daily Drilling Report (DDR) PDF for date "
            f"{date}. Return JSON with sections: {sections}. "
            "Also extract well_name (string or null) and surface_location (string or null) "
            "from the report header — these are DDR-level fields, not per-section data. "
            "For 'time_logs', preserve the original row order from the report and emit fields in this "
            f"exact order per row: {time_log_fields}. Use null for missing optional values."
            f"{page_context}"
        )

    @staticmethod
    def occurrence_generation(time_logs_text: str, valid_types: str) -> str:
        return (
            "You are a drilling engineering expert. From all current time logs below, generate the occurrence table "
            "from scratch. Identify drilling events or problems. Use ONLY the valid types listed.\n\n"
            f"VALID TYPES: {valid_types}\n\n"
            f"CURRENT TIME LOGS:\n{time_logs_text}"
            "\n\nReturn one final JSON object with key 'occurrences'. "
            "Do not return actions or explanations. "
            "Each occurrence must have: date (YYYYMMDD string), type (from valid types), "
            "mmd (float or null), notes (string or null), page_number (integer or null). "
            "Write notes as a drilling-engineering summary, not a copy-paste of DDR text. "
            "Summarize what happened, key depths/rates/volumes/materials, response actions, outcome, and mud weight when relevant. "
            "Combine related time-log rows into one coherent note for the occurrence. "
            "Keep original technical terms, units, depths, and numbers accurate. "
            "Use concise sentence-style notes like a reviewed occurrence table. "
            "Do not include timestamps, row indexes, generic filler, or raw activity-log phrasing unless needed for meaning."
        )
