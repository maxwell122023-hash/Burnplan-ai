from __future__ import annotations

from pathlib import Path
from dotenv import load_dotenv
import streamlit as st

from burnplan_engine import BurnInputs, WeatherInputs, fill_template, build_rule_check, nws_point_metadata

load_dotenv()

st.set_page_config(page_title="BurnPlan AI", layout="wide")
st.title("BurnPlan AI - Draft Prescribed Burn Plan")
st.caption("Draft generator for APCO burn plan template. Human review and burn manager approval required before use.")

with st.sidebar:
    st.header("System Controls")
    use_ai = st.toggle("Use OpenAI polishing if API key is set", value=False)
    st.warning("This app drafts a plan only. Do not use it as the final go/no-go decision.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Tract & Manager")
    tract_name = st.text_input("Tract Name")
    burn_address = st.text_input("Burn Address")
    county = st.text_input("County")
    state = st.text_input("State", value="AL")
    burn_mgr_name = st.text_input("Burn Manager Name")
    burn_mgr_cert = st.text_input("Burn Manager Cert #")
    burn_mgr_phone = st.text_input("Burn Manager Phone")
    prepared_by = st.text_input("Plan Prepared By")
    executers_mailing_address = st.text_area("Executer's Mailing Address", height=80)

with col2:
    st.subheader("Property Description")
    latitude = st.number_input("Latitude", value=32.4074, format="%.6f")
    longitude = st.number_input("Longitude", value=-87.0211, format="%.6f")
    burn_acres = st.number_input("Burn Acres", min_value=0.0, step=1.0)
    section = st.text_input("Section")
    township = st.text_input("Township")
    range_ = st.text_input("Range")
    overstory_type = st.text_input("Overstory Type")
    understory_type = st.text_input("Understory Type")
    fuel_type_amount = st.text_input("Fuel Type and Amount")
    topography = st.text_input("Topography")

st.subheader("Plan Narrative")
c1, c2 = st.columns(2)
with c1:
    objectives = st.text_area("Objectives", height=90, placeholder="Example: reduce sweetgum/Bradford pear competition, improve native grass response, reduce fuels...")
    special_features = st.text_area("Special Features to Protect", height=90)
    smoke_sensitive_areas = st.text_area("Smoke Sensitive Areas", height=90, placeholder="Homes, highways, schools, hospitals, powerlines, poultry houses, etc.")
with c2:
    water_sources = st.text_area("Water Sources / Suppression Resources", height=90)
    roads_access = st.text_area("Roads / Access / Firebreaks", height=90)
    neighbors = st.text_area("Neighbors / Notifications", height=90)

st.subheader("Weather Factors")
w1, w2, w3 = st.columns(3)
with w1:
    surface_wind_mph = st.number_input("Surface Wind MPH", min_value=0.0, step=1.0)
    surface_wind_dir = st.text_input("Surface Wind Direction", placeholder="N, NE, SW...")
    min_rh = st.number_input("Min RH %", min_value=0.0, max_value=100.0, step=1.0)
with w2:
    max_temp_f = st.number_input("Max Temperature °F", min_value=-20.0, max_value=130.0, step=1.0)
    transport_wind_mph = st.number_input("Transport Wind MPH", min_value=0.0, step=1.0)
    transport_wind_dir = st.text_input("Transport Wind Direction", placeholder="N, NE, SW...")
with w3:
    mixing_height_ft = st.number_input("Mixing Height FT", min_value=0.0, step=100.0)
    dispersion_index = st.number_input("Dispersion Index", min_value=0.0, step=1.0)
    kbdi = st.number_input("KBDI", min_value=0.0, max_value=800.0, step=10.0)

st.subheader("Fire Behavior / Final Details")
f1, f2, f3 = st.columns(3)
with f1:
    start_time = st.text_input("Start Time")
    completion_time = st.text_input("Completion Time")
with f2:
    permit_number = st.text_input("Permit #")
    actual_burn_date = st.text_input("Actual Burn Date")
with f3:
    st.write("NWS Point Metadata")
    if st.button("Check NWS point links"):
        try:
            props = nws_point_metadata(latitude, longitude)
            st.success(f"Forecast office: {props.get('cwa', 'N/A')}; grid: {props.get('gridX', 'N/A')}, {props.get('gridY', 'N/A')}")
            st.write({k: props.get(k) for k in ['forecast', 'forecastHourly', 'forecastGridData']})
        except Exception as e:
            st.error(f"NWS lookup failed: {e}")

inputs = BurnInputs(
    tract_name=tract_name,
    burn_address=burn_address,
    state=state,
    county=county,
    burn_mgr_name=burn_mgr_name,
    burn_mgr_cert=burn_mgr_cert,
    burn_mgr_phone=burn_mgr_phone,
    executers_mailing_address=executers_mailing_address,
    prepared_by=prepared_by,
    section=section,
    township=township,
    range=range_,
    latitude=latitude,
    longitude=longitude,
    burn_acres=burn_acres,
    overstory_type=overstory_type,
    understory_type=understory_type,
    fuel_type_amount=fuel_type_amount,
    topography=topography,
    special_features=special_features,
    objectives=objectives,
    smoke_sensitive_areas=smoke_sensitive_areas,
    water_sources=water_sources,
    roads_access=roads_access,
    neighbors=neighbors,
    start_time=start_time,
    completion_time=completion_time,
    permit_number=permit_number,
    actual_burn_date=actual_burn_date,
)
weather = WeatherInputs(
    surface_wind_mph=surface_wind_mph if surface_wind_mph else None,
    surface_wind_dir=surface_wind_dir,
    min_rh=min_rh if min_rh else None,
    max_temp_f=max_temp_f if max_temp_f else None,
    transport_wind_mph=transport_wind_mph if transport_wind_mph else None,
    transport_wind_dir=transport_wind_dir,
    mixing_height_ft=mixing_height_ft if mixing_height_ft else None,
    dispersion_index=dispersion_index if dispersion_index else None,
    kbdi=kbdi if kbdi else None,
)

st.subheader("Rule Check")
for status, item, note in build_rule_check(weather):
    if status == "OK":
        st.success(f"{item}: {note}")
    elif status == "REVIEW":
        st.error(f"{item}: {note}")
    else:
        st.info(f"{item}: {note}")

if st.button("Generate Excel Burn Plan", type="primary"):
    out = Path("outputs") / f"burn_plan_{tract_name or 'draft'}.xlsx"
    out = fill_template(inputs, weather, out, use_ai=use_ai)
    st.success(f"Created {out}")
    with open(out, "rb") as f:
        st.download_button("Download Burn Plan Excel", f, file_name=out.name)
