from __future__ import annotations

from pathlib import Path
from dataclasses import asdict
from datetime import datetime
from dotenv import load_dotenv
import json
import streamlit as st

from burnplan_engine import (
    BurnInputs, WeatherInputs, fill_template, export_pdf, build_rule_check,
    nws_point_metadata, fetch_county_fwf, weather_from_fwf_period,
    get_prescription_template, desired_conditions,
)

load_dotenv()

ALABAMA_COUNTIES = ["Autauga","Baldwin","Barbour","Bibb","Blount","Bullock","Butler","Calhoun","Chambers","Cherokee","Chilton","Choctaw","Clarke","Clay","Cleburne","Coffee","Colbert","Conecuh","Coosa","Covington","Crenshaw","Cullman","Dale","Dallas","DeKalb","Elmore","Escambia","Etowah","Fayette","Franklin","Geneva","Greene","Hale","Henry","Houston","Jackson","Jefferson","Lamar","Lauderdale","Lawrence","Lee","Limestone","Lowndes","Macon","Madison","Marengo","Marion","Marshall","Mobile","Monroe","Montgomery","Morgan","Perry","Pickens","Pike","Randolph","Russell","Shelby","St. Clair","Sumter","Talladega","Tallapoosa","Tuscaloosa","Walker","Washington","Wilcox","Winston"]
WIND_DIRECTIONS = ["", "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW", "Variable"]
BURN_TYPES = ["", "Site Prep", "Rangeland", "TSI", "Fuel Reduction", "Wildlife", "Pre-Marking"]
FIREBREAK_TYPES = ["Blower Line", "Dozer Line", "Hardwood Bottom", "Creek", "River", "Handline", "Disced Line", "Roads"]
OVERSTORY_TYPES = ["", "Longleaf pine", "Loblolly pine", "Shortleaf pine", "Mixed pine", "Pine-hardwood", "Bottomland hardwood", "Upland hardwood", "Young plantation", "Open field / grassland", "Other"]
UNDERSTORY_TYPES = ["", "Native warm-season grasses", "Broomsedge / old field", "Pine straw / needle litter", "Hardwood brush", "Sweetgum / red maple regeneration", "Privet / invasive brush", "Gallberry / titi / shrub layer", "Light herbaceous cover", "Heavy rough", "Other"]
FUEL_TYPES = ["", "Pine litter - light", "Pine litter - moderate", "Pine litter - heavy", "Grass - light", "Grass - moderate", "Grass - heavy", "Old field / broomsedge", "Cutover slash", "Hardwood leaf litter", "Mixed pine-hardwood litter", "Brush / woody understory", "Other"]
TOPOGRAPHY_TYPES = ["", "Flat", "Gently rolling", "Rolling", "Steep", "Bottomland", "Ridge / slope", "Mixed"]
BURN_OBJECTIVES = ["Hazardous fuel reduction", "Site preparation", "Hardwood control", "Sweetgum control", "Wildlife habitat improvement", "Native warm-season grass enhancement", "Pine stand management", "Reduce midstory competition", "Pre-marking visibility", "Training / demonstration burn", "Other"]
EQUIPMENT = ["Type 6 engine", "Water tank / slip-on unit", "UTV", "ATV", "Dozer", "Tractor", "Disk", "Backpack blower", "Leaf blower", "Drip torches", "Radios", "Hand tools", "Chainsaw", "PPE", "First aid kit"]
PERSONNEL_ROLES = ["Burn Boss", "Ignition Boss", "Holding Boss", "Ignition Crew", "Holding Crew", "Engine Operator", "Dozer Operator", "Lookout / Weather", "Traffic Control", "EMS / First Aid"]
IGNITION_METHODS = ["", "Backing fire", "Flanking fire", "Strip-head fire", "Ring fire", "Spot ignition", "Grid ignition", "Combination"]
SPECIAL_PRECAUTIONS = ["Shooting houses", "Game cameras", "Orchards", "TES species to protect", "Snags", "Power lines / wooden poles", "Gas lines", "Heavy fuel near line", "Public roads", "Adjacent homes", "Outbuildings", "Gates / access control", "Passive firelines checked", "Neighbor notification", "Firelines inspected", "Buried cable", "Wooden fence posts", "Cemetery", "Bee hives", "Feeders", "Equipment in the woods", "Livestock", "Thatch under green grass"]

def join_selected(items, other_text=""):
    items = [i for i in items if i and i != "Other"]
    if other_text.strip(): items.append(other_text.strip())
    return "; ".join(items)

def set_prescription_defaults(burn_type: str):
    rec = desired_conditions(burn_type)
    for key, val in rec.items():
        st.session_state[key] = val
    t = get_prescription_template(burn_type)
    if t.get("ignition_techniques"):
        st.session_state["ignition_sequence"] = t["ignition_techniques"]
    if t.get("flame_length"):
        st.session_state["flame_length"] = t["flame_length"]
    if t.get("nighttime_viable") and not st.session_state.get("nighttime_smoke_screening"):
        st.session_state["nighttime_smoke_screening"] = "Yes" if t["nighttime_viable"].lower().startswith("yes") else "No" if t["nighttime_viable"].lower().startswith("no") else ""

st.set_page_config(page_title="BurnPlan AI V3.1", layout="wide")
st.title("BurnPlan AI - Prescription & County Fire Weather")
st.caption("Professional prescribed fire planning for foresters and burn managers. Draft only — final review by the responsible burn manager required.")

with st.sidebar:
    st.header("Controls")
    use_ai = st.toggle("Use OpenAI polishing if API key is set", value=False)
    st.warning("This tool drafts a plan. It does not replace permits, field verification, or go/no-go decisions.")
    st.divider()
    st.write("V3.1")
    st.caption("Adds county-based NWS Fire Weather Forecast import while keeping desired, forecast, and observed weather separate.")

tabs = st.tabs(["1 Project Info", "2 Ownership & Contacts", "3 Objectives", "4 Burn Unit", "5 Prescription & Weather", "6 Smoke & Precautions", "7 Personnel & Equipment", "8 Ignition & Holding", "9 Contingency & Safety", "10 Final Record", "11 Save / Day-of-Burn"])

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
        burn_type = st.selectbox("Burn Type", BURN_TYPES, help="Selecting a burn type can load recommended prescription values.")
        if st.button("Apply Prescription Recommendations", disabled=not bool(burn_type)):
            set_prescription_defaults(burn_type)
            st.success(f"Loaded prescription recommendations for {burn_type}.")

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
    objectives = st.text_area("Objectives Narrative", value=join_selected(selected_objectives, objective_other), height=120)
    special_features = st.text_area("Special Features to Protect", height=100, placeholder="SMZs, utilities, structures, boundary lines, cultural resources, wildlife openings, regeneration areas, etc.")

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
        selected_firebreaks = st.multiselect("Firebreak Types", FIREBREAK_TYPES)
        water_sources = st.text_area("Water Sources / Suppression Resources", height=120, placeholder="Ponds, hydrants, tanks, engines, pumps, dozer access, etc.")

with tabs[4]:
    st.subheader("Prescription Engine Recommendation")
    rec = get_prescription_template(burn_type)
    if burn_type and rec:
        st.info("These recommendations are starting points from your objective recommendation reference. Edit them for site-specific conditions.")
        st.table({"Recommendation": {k.replace("_", " ").title(): v for k, v in rec.items()}})
    else:
        st.warning("Select a Burn Type on Project Info, then click Apply Prescription Recommendations.")

    st.subheader("Desired Prescription")
    d1, d2, d3, d4 = st.columns(4)
    defaults = desired_conditions(burn_type)
    with d1:
        desired_surface_wind = st.text_input("Desired Surface Wind", value=st.session_state.get("desired_surface_wind", defaults["desired_surface_wind"]), key="desired_surface_wind")
        desired_humidity = st.text_input("Desired RH", value=st.session_state.get("desired_humidity", defaults["desired_humidity"]), key="desired_humidity")
    with d2:
        desired_temperature = st.text_input("Desired Temperature", value=st.session_state.get("desired_temperature", defaults["desired_temperature"]), key="desired_temperature")
        desired_transport_wind = st.text_input("Desired Transport Wind", value=st.session_state.get("desired_transport_wind", defaults["desired_transport_wind"]), key="desired_transport_wind")
    with d3:
        desired_mixing_height = st.text_input("Desired Mixing Height", value=st.session_state.get("desired_mixing_height", defaults["desired_mixing_height"]), key="desired_mixing_height")
        desired_dispersion_index = st.text_input("Desired Dispersion", value=st.session_state.get("desired_dispersion_index", defaults["desired_dispersion_index"]), key="desired_dispersion_index")
    with d4:
        desired_fine_fuel_moisture = st.text_input("Desired Fine Fuel Moisture", value=st.session_state.get("desired_fine_fuel_moisture", defaults["desired_fine_fuel_moisture"]), key="desired_fine_fuel_moisture")
        desired_kbdi = st.text_input("Desired KBDI", value=st.session_state.get("desired_kbdi", defaults["desired_kbdi"]), key="desired_kbdi")

    st.subheader("NWS County Fire Weather Forecast")
    st.caption("This forecast is kept separate from the desired prescription and observed day-of-burn weather.")
    f1, f2 = st.columns([2, 1])
    with f1:
        office_choice = st.selectbox("NWS Forecast Office", ["Auto from Latitude / Longitude", "BMX", "HUN", "MOB", "TAE"], help="Auto is recommended. The county name is used to select the county block within that office's FWF product.")
    with f2:
        retrieve_fwf = st.button("Retrieve County FWF", use_container_width=True)
    if retrieve_fwf:
        try:
            office = office_choice
            if office_choice.startswith("Auto"):
                props = nws_point_metadata(latitude, longitude)
                office = props.get("cwa", "")
            if not office:
                raise ValueError("Could not determine the NWS forecast office. Select an office manually.")
            st.session_state["fwf_result"] = fetch_county_fwf(county, office)
            st.session_state.pop("fwf_period", None)
            st.success(f"Retrieved the latest {office} FWF for {county} County.")
        except Exception as e:
            st.session_state.pop("fwf_result", None)
            st.error(f"County FWF retrieval failed: {e}")

    fwf_result = st.session_state.get("fwf_result")
    if fwf_result and fwf_result.get("county") == county:
        p1, p2 = st.columns([2, 1])
        with p1:
            selected_fwf_period = st.selectbox("Forecast Period to Populate", fwf_result["periods"], key="fwf_period")
        with p2:
            apply_fwf = st.button("Populate Forecast Fields", use_container_width=True)
        if apply_fwf:
            mapped = weather_from_fwf_period(fwf_result, selected_fwf_period)
            field_keys = ["surface_wind_mph", "surface_wind_dir", "min_rh", "max_temp_f", "transport_wind_mph", "transport_wind_dir", "mixing_height_ft", "dispersion_index", "forecast_period", "forecast_county", "forecast_office", "forecast_issued", "forecast_product_id", "chance_precip_pct", "precip_type", "precip_amount", "stability_class", "max_lvori", "dispersion_category", "remarks"]
            for key in field_keys:
                value = mapped.get(key)
                if key in {"surface_wind_mph", "min_rh", "max_temp_f", "transport_wind_mph", "mixing_height_ft", "dispersion_index"}:
                    value = float(value or 0.0)
                st.session_state[f"forecast_{key}"] = value
            st.session_state["fwf_raw_fields"] = mapped.get("raw_fields", {})
            st.success("Forecast fields populated. Desired prescription and observed conditions were not changed.")
            st.rerun()
        st.caption(f"Source: NWS {fwf_result.get('office')} | Issued: {fwf_result.get('issued', '')} | Product: {fwf_result.get('product_id', '')}")

    w1, w2, w3 = st.columns(3)
    with w1:
        surface_wind_mph = st.number_input("Forecast Surface Wind MPH", min_value=0.0, step=1.0, key="forecast_surface_wind_mph")
        surface_wind_dir = st.selectbox("Forecast Surface Wind Direction", WIND_DIRECTIONS, key="forecast_surface_wind_dir")
        min_rh = st.number_input("Forecast Min RH %", min_value=0.0, max_value=100.0, step=1.0, key="forecast_min_rh")
    with w2:
        max_temp_f = st.number_input("Forecast Max Temp °F", min_value=-20.0, max_value=130.0, step=1.0, key="forecast_max_temp_f")
        transport_wind_mph = st.number_input("Forecast Transport Wind MPH", min_value=0.0, step=1.0, key="forecast_transport_wind_mph")
        transport_wind_dir = st.selectbox("Forecast Transport Wind Direction", WIND_DIRECTIONS, key="forecast_transport_wind_dir")
    with w3:
        mixing_height_ft = st.number_input("Forecast Mixing Height FT", min_value=0.0, step=100.0, key="forecast_mixing_height_ft")
        dispersion_index = st.number_input("Forecast Dispersion Index", min_value=0.0, step=1.0, key="forecast_dispersion_index")
        kbdi = st.number_input("Forecast KBDI (manual if available)", min_value=0.0, max_value=800.0, step=10.0, key="forecast_kbdi")

    if st.session_state.get("forecast_product_id"):
        with st.expander("Imported NWS County Forecast Details", expanded=False):
            st.write({
                "County": st.session_state.get("forecast_forecast_county", county),
                "Period": st.session_state.get("forecast_forecast_period", ""),
                "Office": st.session_state.get("forecast_forecast_office", ""),
                "Issued": st.session_state.get("forecast_forecast_issued", ""),
                "Chance Precipitation (%)": st.session_state.get("forecast_chance_precip_pct"),
                "Precipitation Type": st.session_state.get("forecast_precip_type", ""),
                "Precipitation Amount": st.session_state.get("forecast_precip_amount", ""),
                "Stability Class": st.session_state.get("forecast_stability_class", ""),
                "Max LVORI": st.session_state.get("forecast_max_lvori"),
                "Dispersion Category": st.session_state.get("forecast_dispersion_category", ""),
                "Remarks": st.session_state.get("forecast_remarks", ""),
            })
            if st.session_state.get("fwf_raw_fields"):
                st.table({"FWF Field": list(st.session_state["fwf_raw_fields"].keys()), "Selected Period Value": list(st.session_state["fwf_raw_fields"].values())})

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
    smoke_sensitive_areas = st.text_area("Smoke Sensitive Areas", height=100, placeholder="Homes, public roads, schools, hospitals, airports, railroads, poultry houses, towns, powerlines, etc.")
    nighttime_smoke_screening = st.selectbox("Nighttime Smoke Screening", ["", "Yes", "No"], key="nighttime_smoke_screening")
    selected_precautions = st.multiselect("Special Precautions Checklist", SPECIAL_PRECAUTIONS)
    extra_precautions = st.text_area("Additional Special Precautions", height=80)
    special_precautions = join_selected(selected_precautions, extra_precautions)
    smoke_precautions = st.text_area("Smoke Precautions / Smoke Management Plan", height=120, placeholder="Describe wind direction, mixing height/dispersion requirements, notification plan, road monitoring, and shutdown triggers.")

with tabs[6]:
    st.subheader("Personnel")
    role_values = []
    for role in PERSONNEL_ROLES:
        c1, c2 = st.columns([1, 2])
        with c1: st.text(role)
        with c2: name = st.text_input(f"Name for {role}", key=f"role_{role}", label_visibility="collapsed")
        if name: role_values.append(f"{role}: {name}")
    st.subheader("Equipment")
    selected_equipment = st.multiselect("Equipment on Site", EQUIPMENT, default=["Water tank / slip-on unit", "UTV", "Drip torches", "Radios", "Hand tools", "PPE"])
    additional_equipment = st.text_area("Additional Equipment / Notes", height=80)
    manpower_equipment = "; ".join(role_values + selected_equipment + ([additional_equipment] if additional_equipment else []))

with tabs[7]:
    c1, c2 = st.columns(2)
    with c1:
        ignition_method = st.selectbox("Primary Ignition Method", IGNITION_METHODS)
        ignition_sequence = st.text_area("Ignition Sequence", height=120, key="ignition_sequence", placeholder="Example: establish blackline on downwind side, secure flanks, then use strip-head fire as conditions allow.")
    with c2:
        holding_plan = st.text_area("Holding Plan", height=120, placeholder="Holding resources, weak points, road crossings, downwind lines, water staging.")
        breach_potential = st.text_area("Breach Potential / Escape Risk", height=120, placeholder="Identify likely escape points and how they will be controlled.")
    ignition_techniques = "; ".join([x for x in [ignition_method, ignition_sequence, holding_plan] if x])

with tabs[8]:
    emergency_resources = st.text_area("Emergency Resources", height=120, placeholder="Permit, 911, fire department, nearest hospital, law enforcement, EMS, water sources, evacuation route.")
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
        flame_length = st.text_input("Observed / Expected Flame Length", key="flame_length")
    with c3:
        permit_number = st.text_input("Permit #")
        actual_burn_date = st.text_input("Actual Burn Date")
    st.subheader("Plan Approval")
    s1, s2 = st.columns(2)
    with s1:
        prepared_by_name = st.text_input("Prepared By - Name")
        prepared_by_date = st.text_input("Prepared By - Date")
        st.caption("Signature line will be added to the PDF.")
    with s2:
        witnessed_by_name = st.text_input("Witnessed By - Name")
        witnessed_by_date = st.text_input("Witnessed By - Date")
        st.caption("Signature line will be added to the PDF.")

weather = WeatherInputs(
    surface_wind_mph=surface_wind_mph if surface_wind_mph else None, surface_wind_dir=surface_wind_dir,
    min_rh=min_rh if min_rh else None, max_temp_f=max_temp_f if max_temp_f else None,
    transport_wind_mph=transport_wind_mph if transport_wind_mph else None, transport_wind_dir=transport_wind_dir,
    mixing_height_ft=mixing_height_ft if mixing_height_ft else None, dispersion_index=dispersion_index if dispersion_index else None, kbdi=kbdi if kbdi else None,
    forecast_period=st.session_state.get("forecast_forecast_period", ""),
    forecast_county=st.session_state.get("forecast_forecast_county", ""),
    forecast_office=st.session_state.get("forecast_forecast_office", ""),
    forecast_issued=st.session_state.get("forecast_forecast_issued", ""),
    forecast_product_id=st.session_state.get("forecast_forecast_product_id", ""),
    chance_precip_pct=st.session_state.get("forecast_chance_precip_pct"),
    precip_type=st.session_state.get("forecast_precip_type", ""), precip_amount=st.session_state.get("forecast_precip_amount", ""),
    stability_class=st.session_state.get("forecast_stability_class", ""), max_lvori=st.session_state.get("forecast_max_lvori"),
    dispersion_category=st.session_state.get("forecast_dispersion_category", ""), remarks=st.session_state.get("forecast_remarks", ""),
)

st.divider(); st.subheader("Rule Check")
cols = st.columns(3)
for idx, (status, item, note) in enumerate(build_rule_check(weather)):
    with cols[idx % 3]:
        if status == "OK": st.success(f"{item}: {note}")
        elif status == "REVIEW": st.error(f"{item}: {note}")
        else: st.info(f"{item}: {note}")

roads_access = "Firebreak types: " + "; ".join(selected_firebreaks) if selected_firebreaks else ""
inputs = BurnInputs(
    tract_name=tract_name, burn_address=burn_address, state=state, county=county, burn_mgr_name=burn_mgr_name,
    burn_mgr_cert=burn_mgr_cert, burn_mgr_phone=burn_mgr_phone, executers_mailing_address=executers_mailing_address,
    prepared_by=prepared_by, latitude=latitude, longitude=longitude, burn_acres=burn_acres, burn_type=burn_type,
    overstory_type=overstory_type, understory_type=understory_type, fuel_type_amount=fuel_type_amount, topography=topography,
    special_features=special_features, objectives=objectives, smoke_sensitive_areas=smoke_sensitive_areas, water_sources=water_sources,
    roads_access=roads_access, neighbors=neighbors, manpower_equipment=manpower_equipment, nighttime_smoke_screening=nighttime_smoke_screening,
    special_precautions=special_precautions, breach_potential=breach_potential, smoke_precautions=smoke_precautions, emergency_resources=emergency_resources,
    ignition_techniques=ignition_techniques, desired_surface_wind=desired_surface_wind, desired_humidity=desired_humidity,
    desired_temperature=desired_temperature, desired_transport_wind=desired_transport_wind, desired_mixing_height=desired_mixing_height,
    desired_dispersion_index=desired_dispersion_index, desired_fine_fuel_moisture=desired_fine_fuel_moisture, desired_kbdi=desired_kbdi,
    observed_surface_wind=observed_surface_wind, observed_humidity=observed_humidity, observed_temperature=observed_temperature,
    observed_transport_wind=observed_transport_wind, observed_mixing_height=observed_mixing_height, observed_dispersion_index=observed_dispersion_index,
    observed_fine_fuel_moisture=observed_fine_fuel_moisture, observed_kbdi=observed_kbdi, hours_to_complete=hours_to_complete,
    flame_length=flame_length, start_time=start_time, completion_time=completion_time, permit_number=permit_number, actual_burn_date=actual_burn_date,
    prepared_by_name=prepared_by_name, prepared_by_date=prepared_by_date, witnessed_by_name=witnessed_by_name, witnessed_by_date=witnessed_by_date,
)

c_excel, c_pdf = st.columns(2)
with c_excel:
    if st.button("Generate Excel Burn Plan", type="primary"):
        safe_name = (tract_name or "draft").replace("/", "-").replace("\\", "-")
        out = fill_template(inputs, weather, Path("outputs") / f"burn_plan_{safe_name}.xlsx", use_ai=use_ai)
        st.success(f"Created {out}")
        with open(out, "rb") as f: st.download_button("Download Burn Plan Excel", f, file_name=out.name)
with c_pdf:
    if st.button("Generate PDF Burn Plan"):
        safe_name = (tract_name or "draft").replace("/", "-").replace("\\", "-")
        pdf_out = export_pdf(inputs, weather, Path("outputs") / f"burn_plan_{safe_name}.pdf", use_ai=use_ai)
        st.success(f"Created {pdf_out}")
        with open(pdf_out, "rb") as f: st.download_button("Download Burn Plan PDF", f, file_name=pdf_out.name, mime="application/pdf")


with tabs[10]:
    st.subheader("Open, Edit, and Update a Complete Burn Plan")
    st.write(
        "Use the editable BurnPlan project file to reopen the entire plan later. "
        "After upload, you can change plan details, retrieve a newer county fire-weather forecast, "
        "enter day-of-burn observations, and generate updated PDF or Excel records."
    )

    # The .burnplan file is the complete editable project record. It contains all
    # plan inputs and the separate NWS county forecast, but not the rendered PDF.
    complete_payload = {
        "format": "BurnPlan AI Project",
        "version": "3.1.3",
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "burn_inputs": asdict(inputs),
        "forecast_weather": asdict(weather),
    }
    complete_bytes = json.dumps(complete_payload, indent=2).encode("utf-8")
    safe_current_name = (tract_name or "draft").replace("/", "-").replace("\\", "-")
    st.download_button(
        "Download Complete Editable BurnPlan Project",
        data=complete_bytes,
        file_name=f"{safe_current_name}.burnplan",
        mime="application/json",
        use_container_width=True,
        help="Keep this file with the PDF. Upload it later to reopen and edit the complete plan.",
    )

    st.divider()
    uploaded_project = st.file_uploader(
        "Upload complete BurnPlan project",
        type=["burnplan", "json"],
        key="complete_project_upload",
        help="Upload the .burnplan project file created by this app. Older BurnPlan JSON record files are also accepted.",
    )

    def _load_editor_state(payload: dict) -> None:
        input_data = payload.get("burn_inputs", {})
        forecast_data = payload.get("forecast_weather", {})
        for field_name in BurnInputs.__dataclass_fields__:
            st.session_state[f"edit_{field_name}"] = input_data.get(field_name, BurnInputs.__dataclass_fields__[field_name].default)
        for field_name in WeatherInputs.__dataclass_fields__:
            st.session_state[f"edit_weather_{field_name}"] = forecast_data.get(field_name, WeatherInputs.__dataclass_fields__[field_name].default)
        st.session_state["editor_project_loaded"] = True
        st.session_state["editor_source_saved_at"] = payload.get("saved_at", "")

    if uploaded_project is not None:
        upload_signature = f"{uploaded_project.name}:{uploaded_project.size}"
        if st.session_state.get("loaded_upload_signature") != upload_signature:
            try:
                payload = json.loads(uploaded_project.getvalue().decode("utf-8"))
                recognized = payload.get("format") in {"BurnPlan AI Project", "BurnPlan AI Record"}
                if not recognized:
                    raise ValueError("This is not a recognized BurnPlan AI editable project file.")
                _load_editor_state(payload)
                st.session_state["loaded_upload_signature"] = upload_signature
                st.success("Complete burn plan loaded. All fields below are editable.")
                st.rerun()
            except Exception as exc:
                st.error(f"Could not open the BurnPlan project: {exc}")

    if st.session_state.get("editor_project_loaded"):
        st.success(
            f"Loaded: {st.session_state.get('edit_tract_name') or 'Unnamed Burn'} — "
            f"{st.session_state.get('edit_county') or 'County not entered'}"
        )
        if st.session_state.get("editor_source_saved_at"):
            st.caption(f"Original project saved: {st.session_state['editor_source_saved_at']}")

        edit_tabs = st.tabs([
            "Project", "Unit & Objectives", "Prescription", "County Forecast",
            "Smoke & Resources", "Ignition & Safety", "Burn-Day Record", "Export"
        ])

        with edit_tabs[0]:
            a, b = st.columns(2)
            with a:
                st.text_input("Tract / Burn Unit Name", key="edit_tract_name")
                st.text_input("Burn Address / Property Location", key="edit_burn_address")
                current_county = st.session_state.get("edit_county", "")
                county_index = ALABAMA_COUNTIES.index(current_county) if current_county in ALABAMA_COUNTIES else 0
                st.selectbox("County", ALABAMA_COUNTIES, index=county_index, key="edit_county")
                st.selectbox("State", ["AL"], key="edit_state")
                st.text_input("Plan Prepared By", key="edit_prepared_by")
                current_type = st.session_state.get("edit_burn_type", "")
                type_index = BURN_TYPES.index(current_type) if current_type in BURN_TYPES else 0
                st.selectbox("Burn Type", BURN_TYPES, index=type_index, key="edit_burn_type")
            with b:
                st.number_input("Latitude", format="%.6f", key="edit_latitude")
                st.number_input("Longitude", format="%.6f", key="edit_longitude")
                st.number_input("Burn Acres", min_value=0.0, step=1.0, key="edit_burn_acres")
                st.text_input("Burn Manager Name", key="edit_burn_mgr_name")
                st.text_input("Burn Manager Certification #", key="edit_burn_mgr_cert")
                st.text_input("Burn Manager Phone", key="edit_burn_mgr_phone")
                st.text_area("Executor / Landowner Mailing Address", key="edit_executers_mailing_address")

        with edit_tabs[1]:
            a, b = st.columns(2)
            with a:
                st.text_area("Objectives", key="edit_objectives", height=100)
                st.text_area("Special Features to Protect", key="edit_special_features", height=100)
                st.text_input("Overstory Type", key="edit_overstory_type")
                st.text_input("Understory Type", key="edit_understory_type")
                st.text_input("Fuel Type / Amount", key="edit_fuel_type_amount")
                st.text_input("Topography", key="edit_topography")
            with b:
                current_breaks = [x.strip() for x in str(st.session_state.get("edit_roads_access", "")).split(";") if x.strip()]
                selected_breaks = st.multiselect(
                    "Firebreak Types",
                    FIREBREAK_TYPES,
                    default=[x for x in current_breaks if x in FIREBREAK_TYPES],
                    key="edit_firebreak_selector",
                )
                # Store firebreaks in the existing compatibility field.
                st.session_state["edit_roads_access"] = "; ".join(selected_breaks)
                st.text_area("Water Sources / Suppression Resources", key="edit_water_sources", height=100)
                st.text_area("Neighbors / Notifications", key="edit_neighbors", height=100)
                st.text_area("Personnel and Equipment", key="edit_manpower_equipment", height=130)

        with edit_tabs[2]:
            st.caption("The desired prescription remains separate from both forecast and observed weather.")
            a, b = st.columns(2)
            with a:
                st.text_input("Desired Surface Wind", key="edit_desired_surface_wind")
                st.text_input("Desired Relative Humidity", key="edit_desired_humidity")
                st.text_input("Desired Temperature", key="edit_desired_temperature")
                st.text_input("Desired Transport Wind", key="edit_desired_transport_wind")
            with b:
                st.text_input("Desired Mixing Height", key="edit_desired_mixing_height")
                st.text_input("Desired Dispersion Index", key="edit_desired_dispersion_index")
                st.text_input("Desired Fine Fuel Moisture", key="edit_desired_fine_fuel_moisture")
                st.text_input("Desired KBDI", key="edit_desired_kbdi")

        with edit_tabs[3]:
            st.caption("Retrieve a new NWS county FWF without changing the desired prescription or observed burn weather.")
            a, b = st.columns([2, 1])
            with a:
                editor_office = st.selectbox(
                    "NWS Forecast Office",
                    ["Auto from Latitude / Longitude", "BMX", "HUN", "MOB", "TAE"],
                    key="editor_office_choice",
                )
            with b:
                editor_retrieve = st.button("Retrieve New County FWF", use_container_width=True, key="editor_retrieve_fwf")

            if editor_retrieve:
                try:
                    office = editor_office
                    if editor_office.startswith("Auto"):
                        props = nws_point_metadata(float(st.session_state["edit_latitude"]), float(st.session_state["edit_longitude"]))
                        office = props.get("cwa", "")
                    if not office:
                        raise ValueError("Could not determine the NWS forecast office. Select an office manually.")
                    result = fetch_county_fwf(st.session_state["edit_county"], office)
                    st.session_state["editor_fwf_result"] = result
                    st.success(f"Retrieved latest {office} FWF for {st.session_state['edit_county']} County.")
                except Exception as exc:
                    st.session_state.pop("editor_fwf_result", None)
                    st.error(f"County FWF retrieval failed: {exc}")

            editor_fwf = st.session_state.get("editor_fwf_result")
            if editor_fwf and editor_fwf.get("county") == st.session_state.get("edit_county"):
                a, b = st.columns([2, 1])
                with a:
                    editor_period = st.selectbox("Forecast Period", editor_fwf["periods"], key="editor_fwf_period")
                with b:
                    if st.button("Populate Uploaded Plan Forecast", use_container_width=True, key="editor_apply_fwf"):
                        mapped = weather_from_fwf_period(editor_fwf, editor_period)
                        for field_name in WeatherInputs.__dataclass_fields__:
                            if field_name in mapped:
                                st.session_state[f"edit_weather_{field_name}"] = mapped[field_name]
                        st.success("County forecast updated. Desired and observed weather were not changed.")
                        st.rerun()

            a, b, c = st.columns(3)
            with a:
                st.number_input("Forecast Surface Wind MPH", min_value=0.0, step=1.0, key="edit_weather_surface_wind_mph")
                current_dir = st.session_state.get("edit_weather_surface_wind_dir", "")
                dir_index = WIND_DIRECTIONS.index(current_dir) if current_dir in WIND_DIRECTIONS else 0
                st.selectbox("Forecast Surface Wind Direction", WIND_DIRECTIONS, index=dir_index, key="edit_weather_surface_wind_dir")
                st.number_input("Forecast Minimum RH %", min_value=0.0, max_value=100.0, step=1.0, key="edit_weather_min_rh")
                st.number_input("Forecast Maximum Temperature °F", step=1.0, key="edit_weather_max_temp_f")
            with b:
                st.number_input("Forecast Transport Wind MPH", min_value=0.0, step=1.0, key="edit_weather_transport_wind_mph")
                current_tdir = st.session_state.get("edit_weather_transport_wind_dir", "")
                tdir_index = WIND_DIRECTIONS.index(current_tdir) if current_tdir in WIND_DIRECTIONS else 0
                st.selectbox("Forecast Transport Wind Direction", WIND_DIRECTIONS, index=tdir_index, key="edit_weather_transport_wind_dir")
                st.number_input("Forecast Mixing Height FT", min_value=0.0, step=100.0, key="edit_weather_mixing_height_ft")
                st.number_input("Forecast Dispersion Index", min_value=0.0, step=1.0, key="edit_weather_dispersion_index")
            with c:
                st.text_input("Forecast Period", key="edit_weather_forecast_period")
                st.text_input("Forecast Office", key="edit_weather_forecast_office")
                st.text_input("Forecast Issued", key="edit_weather_forecast_issued")
                st.text_input("Forecast Product ID", key="edit_weather_forecast_product_id")
                st.number_input("Forecast KBDI", min_value=0.0, max_value=800.0, step=10.0, key="edit_weather_kbdi")

            with st.expander("Additional County Forecast Details"):
                st.number_input("Chance of Precipitation %", min_value=0.0, max_value=100.0, step=1.0, key="edit_weather_chance_precip_pct")
                st.text_input("Precipitation Type", key="edit_weather_precip_type")
                st.text_input("Precipitation Amount", key="edit_weather_precip_amount")
                st.text_input("Stability Class", key="edit_weather_stability_class")
                st.number_input("Maximum LVORI", min_value=0.0, step=1.0, key="edit_weather_max_lvori")
                st.text_input("Dispersion Category", key="edit_weather_dispersion_category")
                st.text_area("Forecast Remarks", key="edit_weather_remarks")

        with edit_tabs[4]:
            a, b = st.columns(2)
            with a:
                st.text_area("Smoke Sensitive Areas", key="edit_smoke_sensitive_areas", height=100)
                current_night = st.session_state.get("edit_nighttime_smoke_screening", "")
                night_options = ["", "Yes", "No"]
                night_index = night_options.index(current_night) if current_night in night_options else 0
                st.selectbox("Nighttime Smoke Screening", night_options, index=night_index, key="edit_nighttime_smoke_screening")
                st.text_area("Smoke Precautions / Management Plan", key="edit_smoke_precautions", height=120)
            with b:
                st.text_area("Special Precautions", key="edit_special_precautions", height=120)
                st.text_area("Emergency Resources", key="edit_emergency_resources", height=120)

        with edit_tabs[5]:
            st.text_area("Ignition Techniques / Sequence / Holding Plan", key="edit_ignition_techniques", height=150)
            st.text_area("Breach Potential / Escape Risk", key="edit_breach_potential", height=120)

        with edit_tabs[6]:
            st.caption("Observed values are the actual day-of-burn record and remain separate from the county forecast.")
            a, b, c = st.columns(3)
            with a:
                st.text_input("Actual Burn Date", key="edit_actual_burn_date")
                st.text_input("Start Time", key="edit_start_time")
                st.text_input("Completion Time", key="edit_completion_time")
                st.text_input("Hours to Complete", key="edit_hours_to_complete")
            with b:
                st.text_input("Observed Surface Wind", key="edit_observed_surface_wind")
                st.text_input("Observed RH", key="edit_observed_humidity")
                st.text_input("Observed Temperature", key="edit_observed_temperature")
                st.text_input("Observed Transport Wind", key="edit_observed_transport_wind")
            with c:
                st.text_input("Observed Mixing Height", key="edit_observed_mixing_height")
                st.text_input("Observed Dispersion Index", key="edit_observed_dispersion_index")
                st.text_input("Observed Fine Fuel Moisture", key="edit_observed_fine_fuel_moisture")
                st.text_input("Observed KBDI", key="edit_observed_kbdi")
                st.text_input("Observed / Expected Flame Length", key="edit_flame_length")
                st.text_input("Permit Number", key="edit_permit_number")

            st.markdown("#### Approval")
            a, b = st.columns(2)
            with a:
                st.text_input("Prepared By - Name", key="edit_prepared_by_name")
                st.text_input("Prepared By - Date", key="edit_prepared_by_date")
            with b:
                st.text_input("Witnessed By - Name", key="edit_witnessed_by_name")
                st.text_input("Witnessed By - Date", key="edit_witnessed_by_date")

        def _editor_dataclasses():
            input_values = {}
            for field_name, field_def in BurnInputs.__dataclass_fields__.items():
                input_values[field_name] = st.session_state.get(f"edit_{field_name}", field_def.default)
            weather_values = {}
            numeric_weather = {
                "surface_wind_mph", "min_rh", "max_temp_f", "transport_wind_mph",
                "mixing_height_ft", "dispersion_index", "kbdi", "chance_precip_pct", "max_lvori"
            }
            for field_name, field_def in WeatherInputs.__dataclass_fields__.items():
                value = st.session_state.get(f"edit_weather_{field_name}", field_def.default)
                if field_name in numeric_weather and value in (0, 0.0, ""):
                    value = None
                weather_values[field_name] = value
            return BurnInputs(**input_values), WeatherInputs(**weather_values)

        with edit_tabs[7]:
            edited_inputs, edited_weather = _editor_dataclasses()
            updated_project = {
                "format": "BurnPlan AI Project",
                "version": "3.1.3",
                "saved_at": datetime.now().isoformat(timespec="seconds"),
                "burn_inputs": asdict(edited_inputs),
                "forecast_weather": asdict(edited_weather),
            }
            updated_bytes = json.dumps(updated_project, indent=2).encode("utf-8")
            safe_loaded_name = (edited_inputs.tract_name or "draft").replace("/", "-").replace("\\", "-")

            st.download_button(
                "Download Updated Complete Project",
                data=updated_bytes,
                file_name=f"{safe_loaded_name}.burnplan",
                mime="application/json",
                use_container_width=True,
            )

            a, b = st.columns(2)
            with a:
                if st.button("Generate Updated PDF", type="primary", use_container_width=True, key="editor_generate_pdf"):
                    pdf_out = export_pdf(edited_inputs, edited_weather, Path("outputs") / f"burn_plan_{safe_loaded_name}_updated.pdf", use_ai=use_ai)
                    with open(pdf_out, "rb") as f:
                        st.download_button("Download Updated PDF", f.read(), file_name=pdf_out.name, mime="application/pdf", use_container_width=True)
            with b:
                if st.button("Generate Updated Excel", use_container_width=True, key="editor_generate_excel"):
                    xlsx_out = fill_template(edited_inputs, edited_weather, Path("outputs") / f"burn_plan_{safe_loaded_name}_updated.xlsx", use_ai=use_ai)
                    with open(xlsx_out, "rb") as f:
                        st.download_button("Download Updated Excel", f.read(), file_name=xlsx_out.name, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

