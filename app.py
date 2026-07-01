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
OVERSTORY_TYPES = ["", "Longleaf pine", "Loblolly pine", "Shortleaf pine", "Mixed pine", "Pine-hardwood", "Bottomland hardwood", "Upland hardwood", "Young plantation", "Open field / grassland", "Other"]
UNDERSTORY_TYPES = ["", "Native warm-season grasses", "Broomsedge / old field", "Pine straw / needle litter", "Hardwood brush", "Sweetgum / red maple regeneration", "Privet / invasive brush", "Gallberry / titi / shrub layer", "Light herbaceous cover", "Heavy rough", "Other"]
FUEL_TYPES = ["", "Pine litter - light", "Pine litter - moderate", "Pine litter - heavy", "Grass - light", "Grass - moderate", "Grass - heavy", "Old field / broomsedge", "Cutover slash", "Hardwood leaf litter", "Mixed pine-hardwood litter", "Brush / woody understory", "Other"]
TOPOGRAPHY_TYPES = ["", "Flat", "Gently rolling", "Rolling", "Steep", "Bottomland", "Ridge / slope", "Mixed"]
BURN_OBJECTIVES = ["Hazardous fuel reduction", "Site preparation", "Hardwood control", "Sweetgum control", "Bradford pear control", "Wildlife habitat improvement", "Native warm-season grass enhancement", "Pine stand management", "Reduce midstory competition", "Improve visibility / access", "Training / demonstration burn", "Other"]
EQUIPMENT = ["Type 6 engine", "Water tank / slip-on unit", "UTV", "ATV", "Dozer", "Tractor", "Disk", "Backpack blower", "Leaf blower", "Drip torches", "Radios", "Hand tools", "Chainsaw", "PPE", "First aid kit"]
PERSONNEL_ROLES = ["Burn Boss", "Ignition Boss", "Holding Boss", "Ignition Crew", "Holding Crew", "Engine Operator", "Dozer Operator", "Lookout / Weather", "Traffic Control", "EMS / First Aid"]
IGNITION_METHODS = ["", "Backing fire", "Flanking fire", "Strip-head fire", "Ring fire", "Spot ignition", "Combination"]


def join_selected(items, other_text=""):
    items = [i for i in items if i and i != "Other"]
    if other_text.strip():
        items.append(other_text.strip())
    return "; ".join(items)


def text_block(label, placeholder="", height=100):
    return st.text_area(label, placeholder=placeholder, height=height)


st.set_page_config(page_title="BurnPlan AI V2", layout="wide")
st.title("BurnPlan AI - Version 2 Layout")
st.caption("Workflow-based burn plan builder. No elevation field included. Draft only — final review by authorized burn manager required.")

with st.sidebar:
    st.header("Controls")
    use_ai = st.toggle("Use OpenAI polishing if API key is set", value=False)
    st.warning("This tool drafts a plan. It does not replace permits, field verification, or go/no-go decisions.")
    st.divider()
    st.write("Template coverage")
    st.caption("This layout now covers the main APCO template sections: tract info, unit description, objectives, manpower/equipment, smoke, breach potential, weather, ignition, permit, and final record.")

tabs = st.tabs([
    "1 Project Info",
    "2 Ownership & Contacts",
    "3 Objectives",
    "4 Burn Unit",
    "5 Weather",
    "6 Smoke",
    "7 Personnel & Equipment",
    "8 Ignition & Holding",
    "9 Contingency & Safety",
    "10 Final Record",
])

with tabs[0]:
    c1, c2 = st.columns(2)
    with c1:
        tract_name = st.text_input("Tract / Burn Unit Name")
        burn_address = st.text_input("Burn Address / Property Location")
        county = st.selectbox("County", ALABAMA_COUNTIES, index=ALABAMA_COUNTIES.index("Dallas"))
        state = st.selectbox("State", ["AL"], index=0)
        prepared_by = st.text_input("Plan Prepared By")
    with c2:
        latitude = st.number_input("Latitude", value=32.4074, format="%.6f")
        longitude = st.number_input("Longitude", value=-87.0211, format="%.6f")
        burn_acres = st.number_input("Burn Acres", min_value=0.0, step=1.0)
        section = st.text_input("Section")
        township = st.text_input("Township")
        range_ = st.text_input("Range")

with tabs[1]:
    c1, c2 = st.columns(2)
    with c1:
        burn_mgr_name = st.text_input("Burn Manager Name")
        burn_mgr_cert = st.text_input("Burn Manager Certification #")
        burn_mgr_phone = st.text_input("Burn Manager Phone")
    with c2:
        executers_mailing_address = st.text_area("Executor / Landowner Mailing Address", height=100)
        neighbors = st.text_area("Neighbors / Notifications", height=100, placeholder="Who needs to be notified before ignition?")

with tabs[2]:
    selected_objectives = st.multiselect("Burn Objectives", BURN_OBJECTIVES, default=["Hazardous fuel reduction"])
    objective_other = st.text_input("Other Objective") if "Other" in selected_objectives else ""
    objectives = st.text_area("Objectives Narrative", value=join_selected(selected_objectives, objective_other), height=140)
    special_features = st.text_area("Special Features to Protect", height=120, placeholder="SMZs, utilities, structures, boundary lines, cultural resources, wildlife openings, regeneration areas, etc.")

with tabs[3]:
    c1, c2 = st.columns(2)
    with c1:
        overstory_choice = st.selectbox("Overstory Type", OVERSTORY_TYPES)
        overstory_other = st.text_input("Other Overstory Type") if overstory_choice == "Other" else ""
        overstory_type = overstory_other or overstory_choice
        understory_choice = st.selectbox("Understory Type", UNDERSTORY_TYPES)
        understory_other = st.text_input("Other Understory Type") if understory_choice == "Other" else ""
        understory_type = understory_other or understory_choice
        fuel_choice = st.selectbox("Fuel Type", FUEL_TYPES)
        fuel_other = st.text_input("Other Fuel Type") if fuel_choice == "Other" else ""
        fuel_load = st.selectbox("Fuel Amount / Load", ["", "Light", "Moderate", "Heavy", "Patchy", "Continuous"])
        fuel_type_amount = "; ".join([x for x in [fuel_other or fuel_choice, fuel_load] if x])
        topography = st.selectbox("Topography", TOPOGRAPHY_TYPES)
    with c2:
        roads_access = st.text_area("Roads / Access / Firebreaks", height=140, placeholder="Primary access, interior roads, exterior breaks, weak points, gates, bridges, etc.")
        water_sources = st.text_area("Water Sources / Suppression Resources", height=120, placeholder="Ponds, hydrants, tanks, engines, pumps, dozer access, etc.")

with tabs[4]:
    st.subheader("Desired Prescription")
    d1, d2, d3, d4 = st.columns(4)
    with d1:
        desired_surface_wind = st.text_input("Desired Surface Wind", "5-15 mph, steady direction")
        desired_humidity = st.text_input("Desired RH", "30-55% typical")
    with d2:
        desired_temperature = st.text_input("Desired Temperature", "Site/objective dependent")
        desired_transport_wind = st.text_input("Desired Transport Wind", "9-20 mph preferred")
    with d3:
        desired_mixing_height = st.text_input("Desired Mixing Height", "> 1700 ft")
        desired_dispersion_index = st.text_input("Desired Dispersion", "> 26; caution > 100")
    with d4:
        desired_fine_fuel_moisture = st.text_input("Desired Fine Fuel Moisture", "Approx. RH / 5")
        desired_kbdi = st.text_input("Desired KBDI", "Site/objective dependent")

    st.subheader("Forecast Weather")
    w1, w2, w3 = st.columns(3)
    with w1:
        surface_wind_mph = st.number_input("Forecast Surface Wind MPH", min_value=0.0, step=1.0)
        surface_wind_dir = st.selectbox("Forecast Surface Wind Direction", WIND_DIRECTIONS, key="surface_wind_dir")
        min_rh = st.number_input("Forecast Min RH %", min_value=0.0, max_value=100.0, step=1.0)
    with w2:
        max_temp_f = st.number_input("Forecast Max Temp °F", min_value=-20.0, max_value=130.0, step=1.0)
        transport_wind_mph = st.number_input("Forecast Transport Wind MPH", min_value=0.0, step=1.0)
        transport_wind_dir = st.selectbox("Forecast Transport Wind Direction", WIND_DIRECTIONS, key="transport_wind_dir")
    with w3:
        mixing_height_ft = st.number_input("Forecast Mixing Height FT", min_value=0.0, step=100.0)
        dispersion_index = st.number_input("Forecast Dispersion Index", min_value=0.0, step=1.0)
        kbdi = st.number_input("Forecast KBDI", min_value=0.0, max_value=800.0, step=10.0)

    with st.expander("Observed Weather / Day-of-Burn Values"):
        o1, o2, o3, o4 = st.columns(4)
        with o1:
            observed_surface_wind = st.text_input("Observed Surface Wind")
            observed_humidity = st.text_input("Observed RH")
        with o2:
            observed_temperature = st.text_input("Observed Temp")
            observed_transport_wind = st.text_input("Observed Transport Wind")
        with o3:
            observed_mixing_height = st.text_input("Observed Mixing Height")
            observed_dispersion_index = st.text_input("Observed Dispersion")
        with o4:
            observed_fine_fuel_moisture = st.text_input("Observed Fine Fuel Moisture")
            observed_kbdi = st.text_input("Observed KBDI")

    if st.button("Check NWS point links"):
        try:
            props = nws_point_metadata(latitude, longitude)
            st.success(f"Forecast office: {props.get('cwa', 'N/A')}; grid: {props.get('gridX', 'N/A')}, {props.get('gridY', 'N/A')}")
            st.write({k: props.get(k) for k in ['forecast', 'forecastHourly', 'forecastGridData']})
        except Exception as e:
            st.error(f"NWS lookup failed: {e}")

with tabs[5]:
    smoke_sensitive_areas = st.text_area("Smoke Sensitive Areas", height=120, placeholder="Homes, public roads, schools, hospitals, airports, railroads, poultry houses, towns, powerlines, etc.")
    adversely_affected_areas = st.text_area("Areas That Could Be Adversely Affected", height=120, placeholder="Where smoke, heat, or escape could create issues.")
    smoke_precautions = st.text_area("Smoke Precautions / Smoke Management Plan", height=140, placeholder="Describe wind direction, mixing height/dispersion requirements, notification plan, road monitoring, and shutdown triggers.")

with tabs[6]:
    st.subheader("Personnel")
    role_values = []
    for role in PERSONNEL_ROLES:
        c1, c2 = st.columns([1, 2])
        with c1:
            st.text(role)
        with c2:
            name = st.text_input(f"Name for {role}", key=f"role_{role}", label_visibility="collapsed")
        if name:
            role_values.append(f"{role}: {name}")

    st.subheader("Equipment")
    selected_equipment = st.multiselect("Equipment on Site", EQUIPMENT, default=["Water tank / slip-on unit", "UTV", "Drip torches", "Radios", "Hand tools", "PPE"])
    additional_equipment = st.text_area("Additional Equipment / Notes", height=80)
    manpower_equipment = "; ".join(role_values + selected_equipment + ([additional_equipment] if additional_equipment else []))

with tabs[7]:
    c1, c2 = st.columns(2)
    with c1:
        ignition_method = st.selectbox("Primary Ignition Method", IGNITION_METHODS)
        ignition_sequence = st.text_area("Ignition Sequence", height=120, placeholder="Example: establish blackline on downwind side, secure flanks, then use strip-head fire as conditions allow.")
    with c2:
        holding_plan = st.text_area("Holding Plan", height=120, placeholder="Holding resources, weak points, road crossings, downwind lines, water staging.")
        breach_potential = st.text_area("Breach Potential / Escape Risk", height=120, placeholder="Identify likely escape points and how they will be controlled.")
    ignition_techniques = "; ".join([x for x in [ignition_method, ignition_sequence, holding_plan] if x])

with tabs[8]:
    emergency_resources = st.text_area("Emergency Resources", height=120, placeholder="AFC permit, 911, fire department, nearest hospital, law enforcement, EMS, water sources, evacuation route.")
    trigger_points = st.text_area("Trigger Points / Stop Work Conditions", height=100, placeholder="Wind shift, RH drop, spotting, smoke on road, line breach, equipment failure, etc.")
    contingency_plan = st.text_area("Contingency / Mop-Up Plan", height=120, placeholder="Reinforcement resources, mop-up standards, patrol plan, recheck schedule.")
    if trigger_points or contingency_plan:
        emergency_resources = "; ".join([x for x in [emergency_resources, f"Trigger points: {trigger_points}" if trigger_points else "", f"Contingency/mop-up: {contingency_plan}" if contingency_plan else ""] if x])

with tabs[9]:
    c1, c2, c3 = st.columns(3)
    with c1:
        start_time = st.text_input("Start Time")
        completion_time = st.text_input("Completion Time")
    with c2:
        hours_to_complete = st.text_input("Hours to Complete")
        flame_length = st.text_input("Observed / Expected Flame Length")
    with c3:
        permit_number = st.text_input("Permit #")
        actual_burn_date = st.text_input("Actual Burn Date")

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

st.divider()
st.subheader("Rule Check")
cols = st.columns(3)
for idx, (status, item, note) in enumerate(build_rule_check(weather)):
    with cols[idx % 3]:
        if status == "OK":
            st.success(f"{item}: {note}")
        elif status == "REVIEW":
            st.error(f"{item}: {note}")
        else:
            st.info(f"{item}: {note}")

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
    manpower_equipment=manpower_equipment,
    adversely_affected_areas=adversely_affected_areas,
    breach_potential=breach_potential,
    smoke_precautions=smoke_precautions,
    emergency_resources=emergency_resources,
    ignition_techniques=ignition_techniques,
    desired_surface_wind=desired_surface_wind,
    desired_humidity=desired_humidity,
    desired_temperature=desired_temperature,
    desired_transport_wind=desired_transport_wind,
    desired_mixing_height=desired_mixing_height,
    desired_dispersion_index=desired_dispersion_index,
    desired_fine_fuel_moisture=desired_fine_fuel_moisture,
    desired_kbdi=desired_kbdi,
    observed_surface_wind=observed_surface_wind,
    observed_humidity=observed_humidity,
    observed_temperature=observed_temperature,
    observed_transport_wind=observed_transport_wind,
    observed_mixing_height=observed_mixing_height,
    observed_dispersion_index=observed_dispersion_index,
    observed_fine_fuel_moisture=observed_fine_fuel_moisture,
    observed_kbdi=observed_kbdi,
    hours_to_complete=hours_to_complete,
    flame_length=flame_length,
    start_time=start_time,
    completion_time=completion_time,
    permit_number=permit_number,
    actual_burn_date=actual_burn_date,
)

if st.button("Generate Excel Burn Plan", type="primary"):
    safe_name = (tract_name or "draft").replace("/", "-").replace("\\", "-")
    out = Path("outputs") / f"burn_plan_{safe_name}.xlsx"
    out = fill_template(inputs, weather, out, use_ai=use_ai)
    st.success(f"Created {out}")
    with open(out, "rb") as f:
        st.download_button("Download Burn Plan Excel", f, file_name=out.name)
