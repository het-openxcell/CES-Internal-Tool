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
                "For every time_logs.page_number value, use the original whole-PDF page number, "
                "not the chunk-local page number."
            )
        return (
            "You are extracting structured data from a Daily Drilling Report (DDR) PDF for date "
            f"{date}. Return JSON with sections: {sections}. "
            f"Extract ONLY rows and values that belong to date {date}. A page may contain spillover or "
            "continuation content from a different day (e.g. the previous or next day's tour rows, or a "
            "carried-over header line); ignore any row that belongs to another date and do not attribute "
            f"it to {date}. "
            "Also extract well_name (string or null) and surface_location (string or null) "
            "from the report header — these are DDR-level fields, not per-section data. "
            "For 'time_logs', preserve the original row order from the report and emit fields in this "
            f"exact order per row: {time_log_fields}. Use null for missing optional values."
            f"{page_context}"
        )

    @staticmethod
    def occurrence_generation(
        time_logs_text: str,
        valid_types: str,
        keyword_hints_text: str = "",
        corrections_context: str = "",
    ) -> str:
        correction_block = (
            f"PREVIOUSLY CORRECTED — these were fixed by a human before; do not repeat the same mistake:\n"
            f"{corrections_context}\n\n"
            if corrections_context
            else ""
        )
        keyword_context = (
            "\n\nKEYWORD HINTS — phrases grouped by occurrence type. Use ONLY to decide the 'type' field "
            "AFTER you have already identified a real drilling event in the time logs. Rules:\n"
            "- Match on meaning, not exact wording "
            "(e.g. 'total losses' ≈ 'total loss of returns' → Lost Circulation).\n"
            "- Hints are not exhaustive; a valid event may use wording not listed — "
            "still classify into the closest valid type.\n"
            "- Presence of a hint phrase alone does NOT create an occurrence. The time log must show the actual event "
            "(symptoms, response, depth/volume/pressure change). Do not invent occurrences from wording alone.\n"
            "- If time-log context contradicts the hint, trust the context and pick the better type (or skip).\n"
            f"\n{keyword_hints_text}"
            if keyword_hints_text
            else ""
        )
        classification_rules = (
            "\n\nCLASSIFICATION RULES:\n"
            "- Tight holes, reams, and back-reams are minor but MUST always be captured, even a single brief "
            "mention — they often precede major events. Never skip them as too minor.\n"
            "- Do NOT create Kick / Well Control from scheduled safety procedures (kick drills, BOP or function "
            "tests, flow checks, trip drills). Only flag a kick on real influx evidence: pit gain, SICP/SIDPP "
            "pressure reading, or unexpected flow with the well shut in.\n"
            "- Gas Spike applies only to an abnormal gas INCREASE above background (a sudden jump or clearly "
            "elevated units). Routine gas readings, surveys, and logged connection gas are NOT Gas Spikes.\n"
        )
        return (
            f"{correction_block}"
            "You are a drilling engineering expert. From the current time logs below, generate the occurrence table "
            "from scratch. Identify drilling events or problems supported by the time logs. "
            "Use ONLY the valid types listed.\n\n"
            f"VALID TYPES: {valid_types}"
            f"{keyword_context}"
            f"{classification_rules}\n"
            f"CURRENT TIME LOGS:\n{time_logs_text}"
            "\n\nReturn one final JSON object with key 'occurrences'. "
            "Do not return actions or explanations. "
            "Each occurrence must have: date (YYYYMMDD string), type (from valid types), "
            "mmd (float or null), notes (string or null), page_number (integer or null), "
            "source_log_indexes (array of integers or null). "
            "Use source_log_indexes from the bracketed CURRENT TIME LOGS row indexes that support the occurrence. "
            "Write notes as a drilling-engineering summary, not a copy-paste of DDR text. "
            "Summarize what happened, key depths/rates/volumes/materials, response actions, outcome, "
            "and mud weight when relevant. "
            "Combine related time-log rows into one coherent note for the occurrence. "
            "Keep original technical terms, units, depths, and numbers accurate. "
            "Use concise sentence-style notes like a reviewed occurrence table. "
            "Do not include timestamps, row indexes, generic filler, or raw activity-log phrasing unless needed "
            "for meaning."
        )
