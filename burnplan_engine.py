from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple
import os
import re
import requests
from openpyxl import load_workbook
from openpyxl.cell.cell import MergedCell


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
    latitude: float | None = None
    longitude: float | None = None
    burn_acres: float | None = None
    burn_type: str = ""
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
    manpower_equipment: str = ""
    nighttime_smoke_screening: str = ""
    breach_potential: str = ""
    smoke_precautions: str = ""
    emergency_resources: str = ""
    ignition_techniques: str = ""
    desired_surface_wind: str = ""
    desired_humidity: str = ""
    desired_temperature: str = ""
    desired_transport_wind: str = ""
    desired_mixing_height: str = ""
    desired_dispersion_index: str = ""
    desired_fine_fuel_moisture: str = ""
    desired_kbdi: str = ""
    observed_surface_wind: str = ""
    observed_humidity: str = ""
    observed_temperature: str = ""
    observed_transport_wind: str = ""
    observed_mixing_height: str = ""
    observed_dispersion_index: str = ""
    observed_fine_fuel_moisture: str = ""
    observed_kbdi: str = ""
    hours_to_complete: str = ""
    flame_length: str = ""
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
    if inputs.burn_type and inputs.burn_type not in objective:
        objective = f"Burn type: {inputs.burn_type}. " + objective
    smoke = inputs.smoke_sensitive_areas or "nearby residences, public roads, utilities, and other smoke-sensitive areas shown on the burn map"
    water = inputs.water_sources or "available water sources and suppression equipment identified before ignition"
    roads = inputs.roads_access or "interior and exterior firebreaks"

    return {
        "special_features": inputs.special_features or f"Protect all marked utilities, boundary lines, SMZs, roads, structures, wildlife openings, and any sensitive resources shown on the attached map.",
        "objectives": objective,
        "manpower_equipment": inputs.manpower_equipment or f"Minimum crew should be sized for {acres} acres, fuel conditions, and holding needs. Recommended resources include burn manager, ignition personnel, holding crew, UTV/ATV or engine, water tank/pump, hand tools, radios/cell phones, PPE, drip torches, fuel, and mop-up tools.",
        "adversely_affected_areas": f"Nighttime smoke screening: {inputs.nighttime_smoke_screening or 'Not specified'}.",
        "breach_potential": inputs.breach_potential or f"Review all downwind lines, corners, heavy fuel pockets, road edges, and changes in topography. Strengthen weak line sections before ignition and assign holding resources to high-risk points.",
        "smoke_precautions": inputs.smoke_precautions or f"Burn only with favorable transport/surface winds, adequate mixing height, and acceptable dispersion. Notify appropriate parties as needed. Monitor smoke across {roads} and stop ignition if smoke impacts become unsafe.",
        "emergency_resources": inputs.emergency_resources or f"Confirm AFC permit, county 911, local fire department, nearest hospital, law enforcement, {water}, and evacuation/access routes before ignition.",
        "ignition_techniques": inputs.ignition_techniques or "Use backing fire first along control lines, then flanking/strip-head fire as conditions allow. Adjust firing pattern to maintain desired flame length, smoke lift, and holding safety.",
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
    for k, v in desired_conditions().items():
        if not data.get(k):
            data[k] = v

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

    def write_cell_safe(cell_ref: str, value: Any) -> None:
        """Write to the top-left cell when a target cell is inside a merged range."""
        target = ws[cell_ref]
        if isinstance(target, MergedCell):
            for merged_range in ws.merged_cells.ranges:
                if cell_ref in merged_range:
                    top_left = ws.cell(row=merged_range.min_row, column=merged_range.min_col)
                    top_left.value = value
                    return
        target.value = value

    for key, cell in CELL_MAP.items():
        if key in data and data[key] not in (None, ""):
            write_cell_safe(cell, data[key])

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



def export_pdf(inputs: BurnInputs, weather: WeatherInputs, output_path: str | Path, use_ai: bool = False) -> Path:
    """Create a professional PDF burn plan record from the app inputs."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    draft = basic_ai_draft(inputs, weather)
    if use_ai:
        draft = optional_openai_polish(draft, inputs, weather)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CoverTitle", parent=styles["Title"], fontSize=24, leading=30, alignment=TA_CENTER, spaceAfter=18))
    styles.add(ParagraphStyle(name="SectionHeader", parent=styles["Heading2"], fontSize=14, leading=18, textColor=colors.HexColor("#1f3b2d"), spaceBefore=12, spaceAfter=6))
    styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=9, leading=12))

    def clean(v: Any) -> str:
        if v is None:
            return ""
        return str(v).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def para(text: Any, style="BodyText"):
        return Paragraph(clean(text), styles[style])

    def section(title: str):
        return para(title, "SectionHeader")

    def table(rows, widths=None):
        t = Table([[para(c, "Small") for c in row] for row in rows], colWidths=widths)
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8efe9")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        return t

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        burn_id = inputs.tract_name or "Draft Burn Plan"
        canvas.drawString(0.55 * inch, 0.35 * inch, f"BurnPlan AI - {burn_id}")
        canvas.drawRightString(7.95 * inch, 0.35 * inch, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(str(output_path), pagesize=letter, rightMargin=0.55*inch, leftMargin=0.55*inch, topMargin=0.6*inch, bottomMargin=0.6*inch)
    story = []

    story.append(Spacer(1, 1.0 * inch))
    story.append(para("Prescribed Burn Plan", "CoverTitle"))
    story.append(para(inputs.tract_name or "Draft Burn Unit", "Title"))
    story.append(Spacer(1, 0.2 * inch))
    story.append(table([
        ["County", inputs.county],
        ["State", inputs.state],
        ["Acres", f"{inputs.burn_acres:g}" if inputs.burn_acres else ""],
        ["Burn Type", inputs.burn_type],
        ["Burn Manager", inputs.burn_mgr_name],
        ["Prepared By", inputs.prepared_by],
        ["Date Prepared", datetime.now().strftime("%m/%d/%Y")],
    ], widths=[2.1*inch, 4.7*inch]))
    story.append(Spacer(1, 0.25 * inch))
    story.append(para("Draft only. Final review, permitting, site verification, weather verification, smoke screening, and go/no-go decisions remain the responsibility of the qualified burn manager.", "Small"))
    story.append(PageBreak())

    story.append(section("1. Project Information"))
    story.append(table([
        ["Tract / Burn Unit", inputs.tract_name], ["Location", inputs.burn_address], ["County / State", f"{inputs.county}, {inputs.state}"],
        ["Latitude / Longitude", "" if inputs.latitude is None or inputs.longitude is None else f"{inputs.latitude:.6f}, {inputs.longitude:.6f}"],
        ["Burn Acres", f"{inputs.burn_acres:g}" if inputs.burn_acres else ""], ["Burn Type", inputs.burn_type],
    ], widths=[2.0*inch, 4.8*inch]))

    story.append(section("2. Ownership & Contacts"))
    story.append(table([
        ["Burn Manager", inputs.burn_mgr_name], ["Certification #", inputs.burn_mgr_cert], ["Phone", inputs.burn_mgr_phone],
        ["Executor / Landowner Address", inputs.executers_mailing_address], ["Neighbors / Notifications", inputs.neighbors],
    ], widths=[2.0*inch, 4.8*inch]))

    story.append(section("3. Objectives"))
    story.append(para(draft.get("objectives", inputs.objectives)))
    story.append(Spacer(1, 6))
    story.append(para(f"Special Features to Protect: {draft.get('special_features', inputs.special_features)}"))

    story.append(section("4. Burn Unit Description"))
    story.append(table([
        ["Overstory", inputs.overstory_type], ["Understory", inputs.understory_type], ["Fuel Type / Load", inputs.fuel_type_amount],
        ["Topography", inputs.topography], ["Firebreaks", inputs.roads_access], ["Water Sources / Suppression Resources", inputs.water_sources],
    ], widths=[2.0*inch, 4.8*inch]))

    story.append(section("5. Weather Prescription"))
    story.append(table([
        ["Item", "Desired", "Forecast", "Observed"],
        ["Surface Wind", inputs.desired_surface_wind, f"{weather.surface_wind_mph or ''} mph {weather.surface_wind_dir}".strip(), inputs.observed_surface_wind],
        ["RH", inputs.desired_humidity, f"{weather.min_rh or ''}%" if weather.min_rh else "", inputs.observed_humidity],
        ["Temperature", inputs.desired_temperature, f"{weather.max_temp_f or ''} F" if weather.max_temp_f else "", inputs.observed_temperature],
        ["Transport Wind", inputs.desired_transport_wind, f"{weather.transport_wind_mph or ''} mph {weather.transport_wind_dir}".strip(), inputs.observed_transport_wind],
        ["Mixing Height", inputs.desired_mixing_height, f"{weather.mixing_height_ft or ''} ft" if weather.mixing_height_ft else "", inputs.observed_mixing_height],
        ["Dispersion", inputs.desired_dispersion_index, f"{weather.dispersion_index or ''}" if weather.dispersion_index else "", inputs.observed_dispersion_index],
        ["KBDI", inputs.desired_kbdi, f"{weather.kbdi or ''}" if weather.kbdi else "", inputs.observed_kbdi],
    ], widths=[1.35*inch, 1.8*inch, 1.8*inch, 1.85*inch]))

    story.append(section("6. Smoke Management"))
    story.append(table([
        ["Smoke Sensitive Areas", inputs.smoke_sensitive_areas],
        ["Nighttime Smoke Screening", inputs.nighttime_smoke_screening],
        ["Smoke Precautions", draft.get("smoke_precautions", inputs.smoke_precautions)],
    ], widths=[2.0*inch, 4.8*inch]))

    story.append(section("7. Personnel & Equipment"))
    story.append(para(draft.get("manpower_equipment", inputs.manpower_equipment)))

    story.append(section("8. Ignition & Holding Plan"))
    story.append(para(draft.get("ignition_techniques", inputs.ignition_techniques)))
    story.append(Spacer(1, 6))
    story.append(para(f"Breach Potential / Escape Risk: {draft.get('breach_potential', inputs.breach_potential)}"))

    story.append(section("9. Contingency & Safety"))
    story.append(para(draft.get("emergency_resources", inputs.emergency_resources)))

    story.append(section("10. Final Burn Record"))
    story.append(table([
        ["Permit #", inputs.permit_number], ["Actual Burn Date", inputs.actual_burn_date], ["Start Time", inputs.start_time],
        ["Completion Time", inputs.completion_time], ["Hours to Complete", inputs.hours_to_complete], ["Observed / Expected Flame Length", inputs.flame_length],
    ], widths=[2.0*inch, 4.8*inch]))

    story.append(section("Rule Check"))
    story.append(table([["Status", "Item", "Note"]] + build_rule_check(weather), widths=[1.0*inch, 1.6*inch, 4.2*inch]))

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return output_path
