# BurnPlan AI V3.1.3

## New in this version
- Retrieves the latest NWS Fire Weather Planning Forecast (FWF).
- Uses the selected county to locate the county forecast block.
- Automatically determines the NWS office from latitude/longitude, with a manual override.
- Lets the user select the forecast period before populating forecast fields.
- Keeps **Desired Prescription**, **NWS County Forecast**, and **Observed Day-of-Burn Conditions** separate.
- Adds NWS forecast source details to PDF and Excel exports.
- Adds **Roads** to Firebreak Types.

## Deploy
Upload all files directly to the root of your GitHub repository, replacing the existing files. Commit the changes and reboot the Streamlit app if it does not redeploy automatically. The Streamlit main file remains `app.py`.

## Weather workflow
1. Select county and enter correct latitude/longitude.
2. Open the Prescription & Weather tab.
3. Click **Retrieve County FWF**.
4. Select Today, Tonight, or the available next-day period.
5. Click **Populate Forecast Fields**.
6. Review all imported values before using them.

NWS county FWF data is planning information. It does not replace the approved burn prescription, onsite weather observations, permits, smoke screening, or the burn manager's go/no-go decision.


## V3.1.3.1 fix
Corrected NWS product-detail parsing so FWF product text is read from the current top-level API response while retaining compatibility with nested responses.

## V3.1.3.2 — Save and reopen on burn day

The app now includes a **Save / Day-of-Burn** tab.

1. Complete the plan and download the BurnPlan `.json` record.
2. Keep that file with the project records.
3. On the burn date, reopen the Streamlit app and upload the record in tab 11.
4. Enter observed weather and completion information.
5. Generate an updated final PDF, Excel record, and revised BurnPlan record.

The desired prescription and NWS county forecast remain unchanged when day-of-burn observations are added.

## V3.1.3 complete editable project workflow

- Download a complete `.burnplan` project file containing every burn-plan field and the separate county FWF forecast.
- Upload that project later and edit the entire plan, not only day-of-burn weather.
- Retrieve a newer county FWF inside the uploaded-project editor.
- Forecast updates do not overwrite desired prescription or observed weather.
- Export the updated project, PDF, or Excel record.
