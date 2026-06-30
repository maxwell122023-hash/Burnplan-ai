from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple
import os
import re
import requests
from openpyxl import load_workbook


TEMPLATE_PATH = Path(__file__).with_name("burn_plan_template.xlsx")

# Cell map based on APCO RxBurn Plan Template_(REVISED_6-2-26).xlsx
CELL_MAP = {
    "tract_name": "B2",
    "burn_address": "B3",
    "state": "B4",
    "county": "E4",
    "burn_mgr_name": "B5",
    "burn_mgr_cert": "G5",
    "burn_mgr_phone": "B6",
    "executers_mailing_address": "B7",
    "prepared_by": "B8",
    "date_prepared": "G9",
    "burn_county": "B12",
    "section": "F12",
    "township": "H12",
    "range": "I12",
    "lat_long": "B13",
    "burn_acres": "B14",
    "overstory_type": "B15",
    "understory_type": "B16",
    "fuel_type_amount": "B17",
    "topography": "B18",
    "special_features": "A20",
    "objectives": "A22",
    "manpower_equipment": "A25",
    "adversely_affected_areas": "A27",
    "breach_potential": "A29",
    "smoke_precautions": "A31",
    "emergency_resources": "A33",
    "desired_surface_wind": "E35",
    "forecast_surface_wind": "G35",
    "observed_surface_wind": "I35",
    "desired_humidity": "E36",
    "forecast_humidity": "G36",
    "observed_humidity": "I36",
    "desired_temperature": "E37",
    "forecast_temperature": "G37",
    "observed_temperature": "I37",
    "desired_transport_wind": "E38",
    "forecast_transport_wind": "G38",
    "observed_transport_wind": "I38",
    "desired_mixing_height": "E39",
    "forecast_mixing_height": "G39",
    "observed_mixing_height": "I39",
    "desired_dispersion_index": "E40",
    "forecast_dispersion_index": "G40",
    "observed_dispersion_index": "I40",
    "desired_fine_fuel_moisture": "E41",
    "forecast_fine_fuel_moisture": "G41",
    "observed_fine_fuel_moisture": "I41",
    "desired_kbdi": "E42",
    "forecast_kbdi": "G42",
    "observed_kbdi": "I42",
    "start_time": "B44",
    "completion_time": "E44",
    "hours_to_complete": "B45",
    "flame_length": "F45",
    "ignition_techniques": "B46",
    "permit_number": "B48",
    "actual_burn_date": "G48",
}


@dataclass
class BurnInputs:
    tract_name: str = ""
    burn_address: str = ""
    state: str = "AL"
    county: str = ""
    burn_mgr_name: str = ""
    burn_mgr_cert: str = ""
    burn_mgr_phone: str = ""
    executers_mailing_address: str = ""
    prepared_by: str = ""
    section: str = ""
    township: str = ""
    range: str = ""
    latitude: float | None = None
    longitude: float | None = None
    burn_acres: float | None = None
    overstory_type: str = ""
    understory_type: str = ""
    fuel_type_amount: str = ""
    topography: str = ""
    special_features: str = ""
    objectives: str = ""
    smoke_sensitive_areas: str = ""
    water_sources: str = ""
    roads_access: str = ""
    neighbors: str = ""
    start_time: str = ""
    completion_time: str = ""
    permit_number: str = ""
    actual_burn_date: str = ""


@dataclass
class WeatherInputs:
    surface_wind_mph: float | None = None
    surface_wind_dir: str = ""
    min_rh: float | None = None
    max_temp_f: float | None = None
    transport_wind_mph: float | None = None
    transport_wind_dir: str = ""
    mixing_height_ft: float | None = None
    dispersion_index: float | None = None
    kbdi: float | None = None


def desired_conditions() -> Dict[str, str]:
    return {
        "desired_surface_wind": "5-15 mph, steady direction",
        "desired_humidity": "30-55% typical; avoid extreme low RH",
        "desired_temperature": "Site/objective dependent",
        "desired_transport_wind": "9-20 mph preferred",
        "desired_mixing_height": "> 1700 ft",
        "desired_dispersion_index": "> 26; use caution > 100",
        "desired_fine_fuel_moisture": "Approx. RH / 5",
        "desired_kbdi": "<300 dormant; <450 growing; <550 site prep",
    }


def fmt(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def build_rule_check(weather: WeatherInputs) -> List[Tuple[str, str, str]]:
    """Returns rows of (status, item, note)."""
    checks: List[Tuple[str, str, str]] = []

    def ok(flag: bool, item: str, good: str, bad: str):
        checks.append(("OK" if flag else "REVIEW", item, good if flag else bad))

    if weather.surface_wind_mph is not None:
        ok(5 <= weather.surface_wind_mph <= 15, "Surface wind", "Within 5-15 mph preferred range.", "Outside 5-15 mph preferred range.")
    if weather.min_rh is not None:
        ok(25 <= weather.min_rh <= 60, "Relative humidity", "Within broad planning range.", "RH may be too low/high for objective; review fuel and escape risk.")
    if weather.transport_wind_mph is not None:
        ok(9 <= weather.transport_wind_mph <= 20, "Transport wind", "Within 9-20 mph preferred range.", "Outside 9-20 mph preferred range.")
    if weather.mixing_height_ft is not None:
        ok(weather.mixing_height_ft > 1700, "Mixing height", "Above 1,700 ft.", "Below required 1,700 ft threshold in template.")
    if weather.dispersion_index is not None:
        ok(weather.dispersion_index > 26 and weather.dispersion_index <= 100, "Dispersion index", "Above 26 and not excessive.", "Must be >26; use caution if >100.")
    if weather.kbdi is not None:
        ok(weather.kbdi < 450, "KBDI", "Within conservative dormant/growing planning range.", "High KBDI; review season/objective and mop-up needs.")

    if not checks:
        checks.append(("INFO", "Weather", "Enter forecast/observed weather to run checks."))
    return checks


def basic_ai_draft(inputs: BurnInputs, weather: WeatherInputs) -> Dict[str, str]:
    """Deterministic draft text. Safe fallback when no API key is configured."""
    acres = f"{inputs.burn_acres:g}" if inputs.burn_acres else "the planned"
    objective = inputs.objectives or "reduce hazardous fuels, improve access/visibility, and support stand and wildlife management objectives"
    smoke = inputs.smoke_sensitive_areas or "nearby residences, public roads, utilities, and other smoke-sensitive areas shown on the burn map"
    water = inputs.water_sources or "available water sources and suppression equipment identified before ignition"
    roads = inputs.roads_access or "primary access roads and interior/exterior firebreaks"

    return {
        "special_features": inputs.special_features or f"Protect all marked utilities, boundary lines, SMZs, roads, structures, wildlife openings, and any sensitive resources shown on the attached map.",
        "objectives": objective,
        "manpower_equipment": f"Minimum crew should be sized for {acres} acres, fuel conditions, and holding needs. Recommended resources include burn manager, ignition personnel, holding crew, UTV/ATV or engine, water tank/pump, hand tools, radios/cell phones, PPE, drip torches, fuel, and mop-up tools.",
        "adversely_affected_areas": f"Potentially affected areas include {smoke}. Confirm wind direction keeps smoke away from these areas before ignition.",
        "breach_potential": f"Review all downwind lines, corners, heavy fuel pockets, road edges, and changes in topography. Strengthen weak line sections before ignition and assign holding resources to high-risk points.",
        "smoke_precautions": f"Burn only with favorable transport/surface winds, adequate mixing height, and acceptable dispersion. Notify appropriate parties as needed. Monitor smoke across {roads} and stop ignition if smoke impacts become unsafe.",
        "emergency_resources": f"Confirm AFC permit, county 911, local fire department, nearest hospital, law enforcement, {water}, and evacuation/access routes before ignition.",
        "ignition_techniques": "Use backing fire first along control lines, then flanking/strip-head fire as conditions allow. Adjust firing pattern to maintain desired flame length, smoke lift, and holding safety.",
    }


def optional_openai_polish(draft: Dict[str, str], inputs: BurnInputs, weather: WeatherInputs) -> Dict[str, str]:
    """Polish text using OpenAI if OPENAI_API_KEY exists. Returns fallback on any error."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return draft
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        prompt = {
            "role": "user",
            "content": (
                "Polish these prescribed burn plan draft fields. Keep them concise, conservative, professional, "
                "and suitable for Certified Burn Manager review. Do not invent permit approval or guarantee safety. "
                f"Inputs: {asdict(inputs)} Weather: {asdict(weather)} Draft: {draft}. "
                "Return JSON with the same keys only."
            ),
        }
        resp = client.responses.create(
            model="gpt-5.4-mini",
            input=[prompt],
            text={"format": {"type": "json_object"}},
        )
        import json
        polished = json.loads(resp.output_text)
        return {k: str(polished.get(k, v)) for k, v in draft.items()}
    except Exception:
        return draft


def fill_template(inputs: BurnInputs, weather: WeatherInputs, output_path: str | Path, use_ai: bool = False) -> Path:
    wb = load_workbook(TEMPLATE_PATH)
    ws = wb.active

    data = asdict(inputs)
    data["burn_county"] = inputs.county
    data["lat_long"] = "" if inputs.latitude is None or inputs.longitude is None else f"{inputs.latitude:.6f}, {inputs.longitude:.6f}"
    data["date_prepared"] = datetime.now().strftime("%m/%d/%Y")

    draft = basic_ai_draft(inputs, weather)
    if use_ai:
        draft = optional_openai_polish(draft, inputs, weather)
    data.update(draft)
    data.update(desired_conditions())

    if weather.surface_wind_mph is not None:
        data["forecast_surface_wind"] = f"{weather.surface_wind_mph:g} mph {weather.surface_wind_dir}".strip()
    if weather.min_rh is not None:
        data["forecast_humidity"] = f"{weather.min_rh:g}%"
        data["forecast_fine_fuel_moisture"] = f"~{weather.min_rh/5:.1f}%"
    if weather.max_temp_f is not None:
        data["forecast_temperature"] = f"{weather.max_temp_f:g}°F"
    if weather.transport_wind_mph is not None:
        data["forecast_transport_wind"] = f"{weather.transport_wind_mph:g} mph {weather.transport_wind_dir}".strip()
    if weather.mixing_height_ft is not None:
        data["forecast_mixing_height"] = f"{weather.mixing_height_ft:g} ft"
    if weather.dispersion_index is not None:
        data["forecast_dispersion_index"] = f"{weather.dispersion_index:g}"
    if weather.kbdi is not None:
        data["forecast_kbdi"] = f"{weather.kbdi:g}"

    if inputs.start_time:
        data["start_time"] = inputs.start_time
    if inputs.completion_time:
        data["completion_time"] = inputs.completion_time
    if inputs.actual_burn_date:
        data["actual_burn_date"] = inputs.actual_burn_date

    for key, cell in CELL_MAP.items():
        if key in data and data[key] not in (None, ""):
            ws[cell] = data[key]

    # Add rule-check sheet for review/audit trail.
    if "AI Rule Check" in wb.sheetnames:
        del wb["AI Rule Check"]
    chk = wb.create_sheet("AI Rule Check")
    chk.append(["Status", "Item", "Note"])
    for row in build_rule_check(weather):
        chk.append(list(row))
    chk.append([])
    chk.append(["Important", "Human review required", "This tool creates a draft only. A qualified/authorized burn manager must verify field conditions, permits, smoke management, and go/no-go decision."])
    for col in "ABC":
        chk.column_dimensions[col].width = 26 if col != "C" else 90
    for row in chk.iter_rows():
        for cell in row:
            cell.alignment = cell.alignment.copy(wrap_text=True, vertical="top")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)
    return output_path


def nws_point_metadata(latitude: float, longitude: float) -> Dict[str, Any]:
    """Fetch basic NWS metadata and links. Use in app as a convenience, not a fire-weather replacement."""
    url = f"https://api.weather.gov/points/{latitude},{longitude}"
    headers = {"User-Agent": "BurnPlanAI/0.1 contact@example.com"}
    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()
    return r.json().get("properties", {})
