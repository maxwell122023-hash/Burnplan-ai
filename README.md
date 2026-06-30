# BurnPlan AI Starter

This is a starter Streamlit app that drafts an APCO prescribed burn plan from a form, fills the uploaded Excel template, and adds an `AI Rule Check` worksheet.

## What it does

- Uses your APCO burn plan Excel template.
- Collects tract, manager, property, objectives, smoke, resources, and weather inputs.
- Drafts plan text for manpower/equipment, smoke precautions, breach potential, emergency resources, and ignition technique.
- Runs basic rule checks for wind, RH, transport wind, mixing height, dispersion index, and KBDI.
- Exports a completed `.xlsx` file.
- Optional OpenAI polishing can rewrite the draft fields if `OPENAI_API_KEY` is set.

## Install

```bash
python -m venv .venv
source .venv/bin/activate   # Mac/Linux
# .venv\Scripts\activate    # Windows
pip install -r requirements.txt
```

## Optional AI setup

Copy `.env.example` to `.env` and add your OpenAI API key.

```bash
cp .env.example .env
```

Then turn on **Use OpenAI polishing** in the sidebar.

## Run

```bash
streamlit run app.py
```

## Important safety note

This tool creates a draft only. A qualified/authorized prescribed burn manager must verify the plan, permits, smoke management, field conditions, and the final go/no-go decision.

## Suggested next upgrades

1. Add map upload and automatically attach burn-unit map.
2. Add AFC permit tracking fields.
3. Add NWS fire-weather import for forecast-grid data.
4. Add user accounts and saved tracts.
5. Add PDF export.
6. Add checklist logs for day-of-burn observed conditions.
