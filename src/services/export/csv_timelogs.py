import csv
import io


class TimeLogCSVExportService:
    def generate(self, ddr_dates_data: list[dict]) -> io.BytesIO:
        rows = []
        for entry in ddr_dates_data:
            date = entry["date"]
            for tl in entry.get("time_logs", []):
                if not isinstance(tl, dict):
                    continue
                rows.append({
                    "date": date,
                    "time_from": tl.get("start_time", ""),
                    "time_to": tl.get("end_time", ""),
                    "activity": tl.get("activity", ""),
                    "details": tl.get("comment") or "",
                    "depth": tl.get("depth_md") if tl.get("depth_md") is not None else "",
                })
        rows.sort(key=lambda r: (r["date"] or "", r["time_from"] or ""))

        buf = io.BytesIO()
        buf.write(b"\xef\xbb\xbf")
        text_buf = io.TextIOWrapper(buf, encoding="utf-8", newline="", write_through=True)
        writer = csv.DictWriter(
            text_buf,
            fieldnames=["date", "time_from", "time_to", "activity", "details", "depth"],
        )
        writer.writeheader()
        writer.writerows(rows)
        text_buf.detach()
        buf.seek(0)
        return buf
