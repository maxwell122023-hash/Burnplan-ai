# BurnPlan AI - V2 Layout

This version reorganizes the app around the prescribed burn workflow instead of one long form.

## What changed
- Removed elevation.
- Added tabs for Project Info, Contacts, Objectives, Burn Unit, Weather, Smoke, Personnel/Equipment, Ignition/Holding, Safety, and Final Record.
- Added more dropdowns, checkboxes, and text areas to cover the APCO Excel template fields.
- Added desired, forecast, and observed weather fields.
- Added personnel roles and equipment selections.
- Keeps the Excel export and AI rule-check sheet.

## Deploy
Upload these files to your GitHub repo and commit changes. Streamlit should redeploy automatically.

Main file path: `app.py`


## Latest V2 edits
- Added Burn Type dropdown: Site Prep, Rangeland, TSI, Fuel Reduction, Wildlife, Pre-Marking.
- Reworked Firebreaks into professional multi-select controls: Blower Line, Dozer Line, Hardwood Bottom, Creek & River, Handline, Disced Line.
- Added Primary Firebreak, Firebreak Condition, Firebreak Notes, and Roads/Access notes.
- Removed company-specific language from the app UI so it reads for professional foresters and burn managers.
