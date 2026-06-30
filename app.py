from __future__ import annotations

from pathlib import Path
from dotenv import load_dotenv
import streamlit as st

from burnplan_engine import BurnInputs, WeatherInputs, fill_template, build_rule_check, nws_point_metadata

load_dotenv()

ALABAMA_COUNTIES = [
    "Autauga", "Baldwin", "Barbour", "Bibb", "Blount", "Bullock", "Butler", "Calhoun", "Chambers",
    "Cherokee", "Chilton", "Choctaw", "Clarke", "Clay", "Cleburne", "Coffee", "Colbert", "Conecuh",
    "Coosa", "Covington", "Crenshaw", "Cullman", "Dale", "Dallas", "DeKalb", "Elmore", "Escambia",
    "Etowah", "Fayette", "Franklin", "Geneva", "Greene", "Hale", "Henry", "Houston", "Jackson",
    "Jefferson", "Lamar", "Lauderdale", "Lawrence", "Lee", "Limestone", "Lowndes", "Macon", "Madison",
    "Marengo", "Marion", "Marshall", "Mobile", "Monroe", "Montgomery", "Morgan", "Perry", "Pickens",
    "Pike", "Randolph", "Russell", "Shelby", "St. Clair", "Sumter", "Talladega", "Tallapoosa",
    "Tuscaloosa", "Walker", "Washington", "Wilcox", "Winston"
]

WIND_DIRECTIONS = ["", "N", "NE", "E", "SE", "S", "SW", "W", "NW", "Variable"]

OVERSTORY_TYPES = [
    "", "Longleaf pine", "Loblolly pine", "Shortleaf pine", "Mixed pine", "Pine-hardwood",
    "Bottomland hardwood", "Upland hardwood", "Young plantation", "Open field / grassland", "Other"
]

UNDERSTORY_TYPES = [
    "", "Native warm-season grasses", "Broomsedge / old field", "Pine straw / needle litter",
    "Hardwood brush", "Sweetgum / red maple regeneration", "Privet / invasive brush",
    "Gallberry / titi / shrub layer", "Light herbaceous cover", "Heavy rough", "Other"
]

FUEL_TYPES = [
    "", "Pine litter - light", "Pine litter - moderate", "Pine litter - heavy",
    "Grass - light", "Grass - moderate", "Grass - heavy",
    "Old field / broomsedge", "Cutover slash", "Hardwood leaf litter",
    "Mixed pine-hardwood litter", "Brush / woody understory", "Other"
]

TOPOGRAPHY_TYPES = ["", "Flat", "Gently rolling", "Rolling", "Steep", "Bottomland", "Ridge / slope", "Mixed"]

BURN_OBJECTIVES = [
    "Hazardous fuel reduction",
    "Site preparation",
    "Hardwood control",
    "Sweetgum control",
    "Bradford pear control",
    "Wildlife habitat improvement",
    "Native warm-season grass enhancement",
    "Pine stand management",
    "Reduce midstory competition",
    "Improve visibility / access",
    "Training / demonstration burn",
    "Other"
]

def join_selected(items, other_text=""):
    items = [i for i in items if i and i != "Other"]
    if other_text.strip():
        items.append(other_text.strip())
    return "; ".join(items)


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
    county = st.selectbox("County", ALABAMA_COUNTIES, index=ALABAMA_COUNTIES.index("Dallas"))
    state = st.selectbox("State", ["AL"], index=0)
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
    overstory_choice = st.selectbox("Overstory Type", OVERSTORY_TYPES)
    overstory_other = st.text_input("Other Overstory Type") if overstory_choice == "Other" else ""
    overstory_type = overstory_other or overstory_choice

    understory_choice = st.selectbox("Understory Type", UNDERSTORY_TYPES)
    understory_other = st.text_input("Other Understory Type") if understory_choice == "Other" else ""
    understory_type = understory_other or understory_choice

    fuel_choice = st.selectbox("Fuel Type", FUEL_TYPES)
    fuel_load = st.selectbox("Fuel Amount / Load", ["", "Light", "Moderate", "Heavy", "Patchy", "Continuous"] )
    fuel_other = st.text_input("Other Fuel Type") if fuel_choice == "Other" else ""
    fuel_type_amount = "; ".join([x for x in [fuel_other or fuel_choice, fuel_load] if x])

    topography = st.selectbox("Topography", TOPOGRAPHY_TYPES)

st.subheader("Plan Narrative")
c1, c2 = st.columns(2)
with c1:
    selected_objectives = st.multiselect("Burn Objectives", BURN_OBJECTIVES, default=["Hazardous fuel reduction"])
    objective_other = st.text_input("Other Objective") if "Other" in selected_objectives else ""
    objectives = st.text_area(
        "Objectives Narrative",
        value=join_selected(selected_objectives, objective_other),
        height=90,
        placeholder="Example: reduce sweetgum/Bradford pear competition, improve native grass response, reduce fuels..."
    )
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
    surface_wind_dir = st.selectbox("Surface Wind Direction", WIND_DIRECTIONS, key="surface_wind_dir")
    min_rh = st.number_input("Min RH %", min_value=0.0, max_value=100.0, step=1.0)
with w2:
    max_temp_f = st.number_input("Max Temperature °F", min_value=-20.0, max_value=130.0, step=1.0)
    transport_wind_mph = st.number_input("Transport Wind MPH", min_value=0.0, step=1.0)
    transport_wind_dir = st.selectbox("Transport Wind Direction", WIND_DIRECTIONS, key="transport_wind_dir")
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
