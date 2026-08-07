from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from app.exports.timeentries_export import per_job_exports
from app.reports.daily_time import daily_time_report


EXPORT_DIR = Path(__file__).resolve().parents[2] / "exports"


def export_daily_time(export_date: date, _: pd.DataFrame | None = None) -> tuple[Path | None, list[Path]]:
    """Create export files using templates from the live Google workbook."""
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    daily_path: Path | None = None
    daily_bytes = daily_time_report("", export_date)
    if daily_bytes:
        daily_path = EXPORT_DIR / f"{export_date.strftime('%m-%d-%Y')} - Daily Time.xlsx"
        daily_path.write_bytes(daily_bytes)

    job_paths: list[Path] = []
    for file_name, file_bytes in per_job_exports("", export_date):
        out_path = EXPORT_DIR / file_name
        out_path.write_bytes(file_bytes)
        job_paths.append(out_path)

    return daily_path, job_paths
