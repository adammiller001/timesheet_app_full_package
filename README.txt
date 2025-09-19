Daily Timesheet App (Modular)
============================
Run locally:
1) Unzip everything.
2) Double‑click run.bat (creates .venv, installs deps, launches app/app.py).

Repo layout:
- app/                      → Streamlit app modules
- TimeSheet Apps.xlsx       → data workbook (read/write)
- TimeEntries.xlsx          → per‑job export template (sheet: 'TimeEntries')
- Daily Time.xlsx           → daily report template
- requirements.txt          → Python deps
- run.bat / run_debug.bat   → launchers
