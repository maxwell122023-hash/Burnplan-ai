# BurnPlan AI V3.1

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
