# BurnPlan AI V3 Alpha

Professional prescribed fire planning app for foresters and burn managers.

## What's new
- Prescription Engine recommendations by Burn Type
- Burn Type templates: Site Prep, Rangeland, TSI, Fuel Reduction, Wildlife, Pre-Marking
- Apply Prescription Recommendations button
- Special Precautions checklist
- Nighttime Smoke Screening Yes/No
- PDF export with professional report layout
- Plan Approval signature lines:
  - Prepared By: Name, Signature, Date
  - Witnessed By: Name, Signature, Date
- Excel export retained as optional/editable backup

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit
Set the main file path to:

```text
app.py
```

Optional OpenAI polishing can be enabled by adding this to Streamlit Secrets:

```toml
OPENAI_API_KEY = "your_key_here"
```

## Important
This app creates a draft burn plan only. Final review, permitting, field verification, weather verification, smoke screening, and go/no-go decisions remain the responsibility of the qualified burn manager.
