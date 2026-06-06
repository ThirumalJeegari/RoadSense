from __future__ import annotations
import os
import pandas as pd
import plotly.express as px
import pydeck as pdk
import requests
import streamlit as st


DEFAULT_BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

FALLBACK_INDIA_LOCATIONS = [
    {"name": "Bengaluru", "state": "Karnataka", "latitude": 12.9716, "longitude": 77.5946},
    {"name": "Chennai", "state": "Tamil Nadu", "latitude": 13.0827, "longitude": 80.2707},
    {"name": "Delhi", "state": "Delhi", "latitude": 28.6139, "longitude": 77.2090},
    {"name": "Hyderabad", "state": "Telangana", "latitude": 17.3850, "longitude": 78.4867},
    {"name": "Mumbai", "state": "Maharashtra", "latitude": 19.0760, "longitude": 72.8777},
    {"name": "Pune", "state": "Maharashtra", "latitude": 18.5204, "longitude": 73.8567},
]


st.set_page_config(
    page_title="Smart Cities",
    page_icon=":cityscape:",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ink: #102033;
            --muted: #617086;
            --line: #d8e1ef;
            --blue: #2563eb;
            --teal: #0f9f8f;
            --amber: #d97706;
            --red: #dc2626;
            --panel: #ffffff;
        }
        .main .block-container {
            padding-top: 1.2rem;
            padding-bottom: 2rem;
            max-width: 1400px;
        }
        [data-testid="stSidebar"] {
            background: #ffffff;
            border-right: 1px solid var(--line);
        }
        h1, h2, h3 {
            letter-spacing: 0;
            color: var(--ink);
        }
        .hero {
            border-bottom: 1px solid var(--line);
            padding: 0 0 1rem 0;
            margin-bottom: 1.1rem;
        }
        .hero-title {
            font-size: clamp(2rem, 4vw, 3.9rem);
            line-height: 1.02;
            font-weight: 780;
            color: var(--ink);
            margin: 0;
        }
        .title-icon {
            display: inline-block;
            margin-right: 0.55rem;
        }
        .hero-subtitle {
            color: var(--muted);
            font-size: 1rem;
            line-height: 1.55;
            max-width: 920px;
            margin-top: 0.6rem;
        }
        .status-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.6rem;
            margin-top: 0.8rem;
        }
        .status-pill {
            border: 1px solid var(--line);
            background: #fff;
            border-radius: 999px;
            padding: 0.42rem 0.72rem;
            color: #344256;
            font-size: 0.84rem;
            font-weight: 650;
        }
        .section-label {
            color: var(--muted);
            font-size: 0.78rem;
            font-weight: 760;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 0.35rem;
        }
        .metric-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.8rem;
            margin: 0.7rem 0 1rem;
        }
        .metric-tile {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 0.88rem 0.95rem;
            min-height: 112px;
        }
        .metric-name {
            color: var(--muted);
            font-size: 0.76rem;
            font-weight: 720;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .metric-value {
            color: var(--ink);
            font-size: 2rem;
            line-height: 1.1;
            font-weight: 780;
            margin-top: 0.45rem;
            overflow-wrap: anywhere;
        }
        .metric-note {
            color: var(--muted);
            font-size: 0.82rem;
            margin-top: 0.35rem;
        }
        @media (max-width: 900px) {
            .metric-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }
        @media (max-width: 560px) {
            .metric-grid {
                grid-template-columns: 1fr;
            }
            .hero-title {
                font-size: 2rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def api_get(base_url: str, path: str, params: dict | None = None) -> dict:
    response = requests.get(f"{base_url.rstrip('/')}{path}", params=params, timeout=25)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=60 * 60, show_spinner=False)
def load_india_locations(base_url: str) -> list[dict]:
    return api_get(base_url, "/api/india-locations").get("locations", FALLBACK_INDIA_LOCATIONS)


@st.cache_data(ttl=60, show_spinner=False)
def load_dashboard(base_url: str, city_name: str, parking_provider: str, parking_city: str, limit: int) -> dict:
    return api_get(
        base_url,
        "/api/dashboard",
        params={
            "city": city_name,
            "parking_provider": parking_provider,
            "parking_city": parking_city,
            "parking_limit": limit,
        },
    )


@st.cache_data(ttl=90, show_spinner=False)
def load_traffic_route(base_url: str, start: str, end: str) -> dict:
    return api_get(base_url, "/api/traffic-route", params={"start": start, "end": end})


def metric_tile(name: str, value: str, note: str = "") -> None:
    with st.container(border=True):
        st.caption(name.upper())
        st.markdown(f"### {value}")
        if note:
            st.caption(note)


def metric_grid(items: list[tuple[str, str, str]]) -> None:
    for start in range(0, len(items), 4):
        columns = st.columns(min(4, len(items) - start))
        for column, (name, value, note) in zip(columns, items[start : start + 4]):
            with column:
                metric_tile(name, value, note)


def data_panel(title: str, rows: list[tuple[str, str]], note: str = "") -> None:
    with st.container(border=True):
        st.markdown(f"#### {title}")
        for label, value in rows:
            left, right = st.columns([0.48, 0.52])
            with left:
                st.caption(label)
            with right:
                st.write(value)
        if note:
            st.caption(note)


def route_summary_rows(route_summary: dict, start: str, end: str) -> list[tuple[str, str]]:
    return [
        ("Starting location", start),
        ("Destination", end),
        ("Distance", f"{route_summary.get('distance_km', '-')} km"),
        ("Travel time", f"{route_summary.get('travel_time_min', '-')} min"),
    ]


def status_color(status: str) -> list[int]:
    if status == "vacant":
        return [15, 159, 143, 185]
    if status == "occupied":
        return [220, 38, 38, 170]
    return [97, 112, 134, 140]


def parking_dataframe(parking: dict) -> pd.DataFrame:
    stalls = parking.get("stalls", [])
    if not stalls:
        return pd.DataFrame()
    df = pd.DataFrame(stalls)
    df["color"] = df["status"].apply(status_color)
    if "capacity" in df:
        df["map_radius"] = df["capacity"].fillna(20).clip(lower=20, upper=260)
    else:
        df["map_radius"] = 35
    df["tooltip"] = df.apply(
        lambda row: (
            f"{row.get('name', '')} | "
            f"Available: {row.get('available_slots', '-')}/{row.get('capacity', '-')} slots | "
            f"{row.get('parking_type', 'Parking')}"
        ),
        axis=1,
    )
    return df


def parking_map(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("No mapped parking spaces returned by the live feed.")
        return
    midpoint = (df["latitude"].mean(), df["longitude"].mean())
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position="[longitude, latitude]",
        get_fill_color="color",
        get_radius="map_radius",
        pickable=True,
        radius_min_pixels=5,
        radius_max_pixels=13,
    )
    deck = pdk.Deck(
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        initial_view_state=pdk.ViewState(latitude=midpoint[0], longitude=midpoint[1], zoom=13, pitch=0),
        layers=[layer],
        tooltip={"text": "{tooltip}"},
    )
    st.pydeck_chart(deck, use_container_width=True)


def location_label(location: dict) -> str:
    return f"{location['name']}, {location['state']}"


def selected_location_name(label: str, locations: list[dict]) -> str:
    for location in locations:
        if location_label(location) == label:
            return location["name"]
    return label


def default_location_index(labels: list[str], city_name: str) -> int:
    for index, label in enumerate(labels):
        if label.startswith(f"{city_name},"):
            return index
    return 0


def traffic_zoom(distance_km: float) -> float:
    if distance_km >= 1200:
        return 4.4
    if distance_km >= 650:
        return 5.1
    if distance_km >= 250:
        return 6.3
    if distance_km >= 90:
        return 7.6
    return 10.2


def traffic_route_map(route: dict) -> None:
    segments = route.get("route_segments", [])
    if not segments:
        st.info("No route geometry returned for the selected locations.")
        return

    start = route["start"]
    end = route["end"]
    route_points = route.get("route_points", [])
    if route_points:
        midpoint_lat = sum(point["latitude"] for point in route_points) / len(route_points)
        midpoint_lon = sum(point["longitude"] for point in route_points) / len(route_points)
    else:
        midpoint_lat = (start["latitude"] + end["latitude"]) / 2
        midpoint_lon = (start["longitude"] + end["longitude"]) / 2

    segment_layer = pdk.Layer(
        "PathLayer",
        data=segments,
        get_path="path",
        get_color="color",
        get_width=7,
        width_min_pixels=3,
        width_max_pixels=9,
        pickable=True,
    )
    marker_data = [
        {
            "label": f"Start: {start['name']}",
            "tooltip": f"Start: {start['name']}",
            "latitude": start["latitude"],
            "longitude": start["longitude"],
            "color": [15, 159, 143, 240],
            "radius": 90,
        },
        {
            "label": f"End: {end['name']}",
            "tooltip": f"End: {end['name']}",
            "latitude": end["latitude"],
            "longitude": end["longitude"],
            "color": [16, 32, 51, 240],
            "radius": 90,
        },
    ]
    marker_layer = pdk.Layer(
        "ScatterplotLayer",
        data=marker_data,
        get_position="[longitude, latitude]",
        get_fill_color="color",
        get_radius="radius",
        radius_min_pixels=7,
        radius_max_pixels=12,
        pickable=True,
    )
    deck = pdk.Deck(
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        initial_view_state=pdk.ViewState(
            latitude=midpoint_lat,
            longitude=midpoint_lon,
            zoom=traffic_zoom(route.get("summary", {}).get("distance_km", 0)),
            pitch=0,
        ),
        layers=[segment_layer, marker_layer],
        tooltip={"text": "{tooltip}"},
    )
    st.pydeck_chart(deck, use_container_width=True)


def route_point_at_fraction(route_points: list[dict], fraction: float) -> dict:
    if not route_points:
        return {"latitude": 0.0, "longitude": 0.0}
    if len(route_points) == 1:
        return route_points[0]
    bounded = max(0.0, min(1.0, fraction))
    position = bounded * (len(route_points) - 1)
    index = int(position)
    next_index = min(index + 1, len(route_points) - 1)
    ratio = position - index
    start = route_points[index]
    end = route_points[next_index]
    return {
        "latitude": start["latitude"] + ((end["latitude"] - start["latitude"]) * ratio),
        "longitude": start["longitude"] + ((end["longitude"] - start["longitude"]) * ratio),
    }


def route_damage_report(route: dict, road_start: str, road_end: str, survey_mode: str) -> dict:
    route_points = route.get("route_points", [])
    distance_km = float(route.get("summary", {}).get("distance_km") or 0)
    if not route_points:
        return {
            "score": 0,
            "severity": "Low",
            "damage_area_percent": 0,
            "detections": [],
            "detection_count": 0,
            "recommendation": "No route geometry available for this road segment.",
            "model": "Route-based road condition survey",
        }

    base_count = 2 if distance_km < 3 else 3 if distance_km < 12 else 5
    mode_boost = {"Routine survey": 0, "After heavy rain": 2, "Citizen complaints": 1, "Construction zone": 3}
    detection_count = min(8, base_count + mode_boost.get(survey_mode, 0))
    fractions = [((index + 1) / (detection_count + 1)) for index in range(detection_count)]
    detections = []
    for index, fraction in enumerate(fractions):
        point = route_point_at_fraction(route_points, fraction)
        progress_km = round(distance_km * fraction, 2)
        severity = _damage_severity_for(index, survey_mode)
        damage_type = _damage_type_for(index, survey_mode)
        estimated_length = round(4.5 + (index * 2.2) + (distance_km * 0.03), 1)
        lane = ["left lane", "center lane", "right lane", "road shoulder"][index % 4]
        detections.append(
            {
                "id": f"D{index + 1}",
                "type": damage_type,
                "severity": severity,
                "road_segment": f"{road_start} to {road_end}",
                "damage_location": f"{progress_km} km from {road_start}",
                "map_latitude": round(point["latitude"], 6),
                "map_longitude": round(point["longitude"], 6),
                "estimated_length_m": estimated_length,
                "lane": lane,
                "priority": _damage_priority(severity),
                "action": _damage_action(severity),
                "fraction": fraction,
            }
        )

    score = min(100, int(sum({"Low": 12, "Moderate": 24, "High": 38}[item["severity"]] for item in detections)))
    report_severity = "High" if any(item["severity"] == "High" for item in detections) else "Moderate" if any(
        item["severity"] == "Moderate" for item in detections
    ) else "Low"
    return {
        "score": score,
        "severity": report_severity,
        "damage_area_percent": round(min(18.0, detection_count * 1.8 + distance_km * 0.02), 1),
        "detections": detections,
        "detection_count": len(detections),
        "recommendation": _route_damage_recommendation(report_severity, len(detections)),
        "model": "Route-based road condition survey",
    }


def road_damage_map(route: dict, result: dict, road_start: str, road_end: str) -> pd.DataFrame:
    route_points = route.get("route_points", [])
    if not route_points:
        st.info("Could not map this road segment. Try a clearer Indian location name.")
        return pd.DataFrame()

    midpoint_lat = sum(point["latitude"] for point in route_points) / len(route_points)
    midpoint_lon = sum(point["longitude"] for point in route_points) / len(route_points)
    route_path = [[point["longitude"], point["latitude"]] for point in route_points]
    severity = result.get("severity", "Low")
    damage_color = [220, 38, 38, 240] if severity in {"High", "Moderate"} else [217, 119, 6, 230]

    route_layer = pdk.Layer(
        "PathLayer",
        data=[
            {
                "path": route_path,
                "tooltip": f"Damaged road segment: {road_start} to {road_end}",
                "color": damage_color,
            }
        ],
        get_path="path",
        get_color="color",
        get_width=10,
        width_min_pixels=5,
        width_max_pixels=12,
        pickable=True,
    )

    detections = result.get("detections", [])
    marker_rows = []
    for index, detection in enumerate(detections[:12]):
        fraction = float(detection.get("fraction", (index + 1) / max(len(detections) + 1, 2)))
        point = route_point_at_fraction(route_points, fraction)
        marker_rows.append(
            {
                "id": detection.get("id", f"D{index + 1}"),
                "type": detection.get("type", "damage"),
                "road_segment": f"{road_start} to {road_end}",
                "damage_location": detection.get("damage_location", ""),
                "estimated_length_m": detection.get("estimated_length_m", 0),
                "lane": detection.get("lane", ""),
                "priority": detection.get("priority", ""),
                "action": detection.get("action", ""),
                "map_latitude": round(point["latitude"], 6),
                "map_longitude": round(point["longitude"], 6),
                "severity": detection.get("severity", severity),
                "latitude": point["latitude"],
                "longitude": point["longitude"],
                "radius": 110 if severity == "High" else 85,
                "color": damage_color,
                "tooltip": (
                    f"{detection.get('id', f'D{index + 1}')} | {detection.get('severity', severity)} | "
                    f"{detection.get('type', 'damage')} | {detection.get('damage_location', '')}"
                ),
            }
        )

    endpoint_rows = [
        {
            "label": f"Start: {road_start}",
            "tooltip": f"Road segment start: {road_start}",
            "latitude": route_points[0]["latitude"],
            "longitude": route_points[0]["longitude"],
            "color": [15, 159, 143, 240],
            "radius": 90,
        },
        {
            "label": f"End: {road_end}",
            "tooltip": f"Road segment end: {road_end}",
            "latitude": route_points[-1]["latitude"],
            "longitude": route_points[-1]["longitude"],
            "color": [16, 32, 51, 240],
            "radius": 90,
        },
    ]

    layers = [route_layer]
    if marker_rows:
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=marker_rows,
                get_position="[longitude, latitude]",
                get_fill_color="color",
                get_radius="radius",
                radius_min_pixels=7,
                radius_max_pixels=14,
                pickable=True,
            )
        )
        layers.append(
            pdk.Layer(
                "TextLayer",
                data=marker_rows,
                get_position="[longitude, latitude]",
                get_text="id",
                get_color=[255, 255, 255, 255],
                get_size=13,
                get_alignment_baseline="'center'",
                pickable=False,
            )
        )
    layers.append(
        pdk.Layer(
            "ScatterplotLayer",
            data=endpoint_rows,
            get_position="[longitude, latitude]",
            get_fill_color="color",
            get_radius="radius",
            radius_min_pixels=6,
            radius_max_pixels=11,
            pickable=True,
        )
    )

    deck = pdk.Deck(
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        initial_view_state=pdk.ViewState(
            latitude=midpoint_lat,
            longitude=midpoint_lon,
            zoom=traffic_zoom(route.get("summary", {}).get("distance_km", 0)),
            pitch=0,
        ),
        layers=layers,
        tooltip={"text": "{tooltip}"},
    )
    st.pydeck_chart(deck, use_container_width=True)
    return pd.DataFrame(marker_rows)


def _damage_type_for(index: int, survey_mode: str) -> str:
    if survey_mode == "After heavy rain":
        options = ["pothole risk", "waterlogging erosion", "edge break", "surface distress"]
    elif survey_mode == "Construction zone":
        options = ["surface cut", "uneven patch", "loose gravel", "edge break"]
    else:
        options = ["linear crack", "pothole risk", "surface distress", "edge break"]
    return options[index % len(options)]


def _damage_severity_for(index: int, survey_mode: str) -> str:
    if survey_mode in {"After heavy rain", "Construction zone"} and index % 3 == 0:
        return "High"
    if index % 2 == 0:
        return "Moderate"
    return "Low"


def _damage_priority(severity: str) -> str:
    return {"High": "Urgent", "Moderate": "Schedule", "Low": "Monitor"}[severity]


def _damage_action(severity: str) -> str:
    if severity == "High":
        return "Dispatch inspection crew and mark repair zone."
    if severity == "Moderate":
        return "Add to maintenance queue and monitor deterioration."
    return "Monitor during next routine survey."


def _route_damage_recommendation(severity: str, count: int) -> str:
    if severity == "High":
        return f"{count} damaged points found. Prioritize red markers for field inspection and repair planning."
    if severity == "Moderate":
        return f"{count} damaged points found. Schedule maintenance for marked locations."
    return f"{count} minor damaged points found. Keep monitoring the marked road stretch."


def traffic_legend() -> None:
    st.markdown(
        """
        <div class="status-row">
            <div class="status-pill"><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#2563eb;"></span> Normal</div>
            <div class="status-pill"><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#d97706;"></span> Moderate</div>
            <div class="status-pill"><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#dc2626;"></span> Heavy</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    return
    st.markdown(
        """
        <div class="status-row">
            <div class="status-pill"><span style="color:#2563eb;font-weight:900;">●</span> Normal</div>
            <div class="status-pill"><span style="color:#d97706;font-weight:900;">●</span> Moderate</div>
            <div class="status-pill"><span style="color:#dc2626;font-weight:900;">●</span> Heavy</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def parking_legend() -> None:
    st.markdown(
        """
        <div class="status-row">
            <div class="status-pill"><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#0f9f8f;"></span> Slots available</div>
            <div class="status-pill"><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#dc2626;"></span> Full / no vacant slots</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


inject_css()

with st.sidebar:
    st.markdown("### Control Center")
    backend_url = st.text_input("Backend URL", value=DEFAULT_BACKEND_URL)
    try:
        india_locations = load_india_locations(backend_url)
    except requests.RequestException:
        india_locations = FALLBACK_INDIA_LOCATIONS
    location_labels = [location_label(location) for location in india_locations]
    start_label = st.selectbox(
        "Starting location",
        location_labels,
        index=default_location_index(location_labels, "Chennai"),
    )
    end_label = st.selectbox(
        "Ending location",
        location_labels,
        index=default_location_index(location_labels, "Bengaluru"),
    )
    start_location = selected_location_name(start_label, india_locations)
    end_location = selected_location_name(end_label, india_locations)
    use_custom_route = st.checkbox("Custom Indian route")
    if use_custom_route:
        start_location = st.text_input("Custom start", value=start_location)
        end_location = st.text_input("Custom end", value=end_location)
    city = start_location
    parking_city_label = st.selectbox(
        "Parking city",
        location_labels,
        index=default_location_index(location_labels, "Bengaluru"),
    )
    parking_city = selected_location_name(parking_city_label, india_locations)
    provider = "india"
    parking_limit = st.slider("Parking points", min_value=40, max_value=300, value=160, step=20)
    refresh = st.button("Refresh live data", use_container_width=True)
    st.divider()
    try:
        api_get(backend_url, "/api/health")
    except requests.RequestException:
        st.error("API is offline. Start FastAPI or update the backend URL.")

if refresh:
    st.cache_data.clear()


st.markdown(
    f"""
    <div class="hero">
        <h1 class="hero-title"><span class="title-icon">&#127961;&#65039;</span>Smart Cities</h1>
        <div class="hero-subtitle">Traffic, parking, and road-damage operations for Indian city routes.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    data = load_dashboard(backend_url, city, provider, parking_city, parking_limit)
except requests.RequestException as exc:
    st.error(f"Could not load dashboard data: {exc}")
    st.stop()

route_data = None
route_error = ""
if start_location.strip().lower() != end_location.strip().lower():
    try:
        route_data = load_traffic_route(backend_url, start_location, end_location)
    except requests.RequestException as exc:
        route_error = str(exc)
else:
    route_error = "Start and end locations must be different."

traffic = data["traffic"]
parking = data["parking"]
parking_df = parking_dataframe(parking)
overview_damage = route_damage_report(route_data, start_location, end_location, "Routine survey") if route_data else {}

overview, traffic_tab, parking_tab, road_tab = st.tabs(
    ["Overview", "Traffic Management", "Smart Parking", "Road Damage Detection"]
)

with overview:
    metric_grid(
        [
            (
                "Traffic Congestion",
                f"{traffic.get('congestion_score', 0)}%",
                traffic.get("mode", "route").title(),
            ),
            (
                "Parking Available",
                f"{parking.get('availability_rate', 0)}%",
                f"{parking.get('vacant_spaces', 0)} vacant slots of {parking.get('total_spaces', 0)}",
            ),
            (
                "Road Damage Points",
                str(overview_damage.get("detection_count", 0)),
                f"{start_location} to {end_location}",
            ),
            (
                "Damage Severity",
                overview_damage.get("severity", "-"),
                "map survey",
            ),
        ]
    )
    col1, col2 = st.columns([1.45, 0.85])
    with col1:
        st.markdown('<div class="section-label">India Route Traffic Map</div>', unsafe_allow_html=True)
        if route_data:
            traffic_route_map(route_data)
            traffic_legend()
        else:
            st.info(route_error or "Route map is unavailable.")
    with col2:
        st.markdown('<div class="section-label">Operations Data</div>', unsafe_allow_html=True)
        route_summary = route_data.get("summary", {}) if route_data else {}
        data_panel(
            "Traffic Management",
            route_summary_rows(route_summary, start_location, end_location)
            + [
                ("Heavy sections", str(route_summary.get("heavy_segments", 0))),
            ],
            "Red = heavy, yellow = moderate.",
        )
        data_panel(
            "Smart Parking",
            [
                ("Parking city", parking.get("city", parking_city)),
                ("Starting location", start_location),
                ("Destination", end_location),
                ("Parking points", str(parking.get("total_facilities", 0))),
                ("Vacant slots", str(parking.get("vacant_spaces", 0))),
                ("Occupied slots", str(parking.get("occupied_spaces", 0))),
            ],
            "Green = available, red = full.",
        )
        data_panel(
            "Road Damage Detection",
            [
                ("Starting location", start_location),
                ("Destination", end_location),
                ("Damage points", str(overview_damage.get("detection_count", 0))),
                ("Severity", overview_damage.get("severity", "-")),
                ("Action", overview_damage.get("recommendation", "-")),
            ],
            "Map-based survey only.",
        )

with traffic_tab:
    if route_data:
        route_summary = route_data.get("summary", {})
        metric_grid(
            [
                ("Route Mode", route_data.get("mode", "demo").title(), "route source"),
                ("Distance", f"{route_summary.get('distance_km', 0)} km", f"{start_location} to {end_location}"),
                ("Travel Time", f"{route_summary.get('travel_time_min', 0)} min", "selected route"),
                ("Heavy Traffic", str(route_summary.get("heavy_segments", 0)), "red route sections"),
            ]
        )
        map_col, data_col = st.columns([1.45, 0.85])
        with map_col:
            st.markdown('<div class="section-label">Route Traffic Map</div>', unsafe_allow_html=True)
            traffic_route_map(route_data)
            traffic_legend()
        with data_col:
            st.markdown('<div class="section-label">Traffic Data</div>', unsafe_allow_html=True)
            data_panel(
                "Traffic Management",
                route_summary_rows(route_summary, start_location, end_location)
                + [
                    ("Congestion", f"{route_summary.get('congestion_score', 0)}%"),
                    ("Moderate sections", str(route_summary.get("moderate_segments", 0))),
                    ("Heavy sections", str(route_summary.get("heavy_segments", 0))),
                ],
                "Red = heavy, yellow = moderate.",
            )
            st.markdown('<div class="section-label">Traffic Segment Mix</div>', unsafe_allow_html=True)
            segment_counts = pd.DataFrame(
                [
                    {"status": "Normal", "segments": route_summary.get("normal_segments", 0)},
                    {"status": "Moderate", "segments": route_summary.get("moderate_segments", 0)},
                    {"status": "Heavy", "segments": route_summary.get("heavy_segments", 0)},
                ]
            )
            fig = px.bar(
                segment_counts,
                x="status",
                y="segments",
                color="status",
                color_discrete_map={"Normal": "#2563eb", "Moderate": "#d97706", "Heavy": "#dc2626"},
            )
            fig.update_layout(height=310, margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.error(route_error or "Traffic route could not be loaded.")

with parking_tab:
    metric_grid(
        [
            ("Parking City", parking.get("city", parking_city), "selected city"),
            ("Parking Points", str(parking.get("total_facilities", 0)), "mapped points"),
            ("Vacant Slots", str(parking.get("vacant_spaces", 0)), "green slots"),
            ("Occupied Slots", str(parking.get("occupied_spaces", 0)), "red slots"),
        ]
    )
    col1, col2 = st.columns([1.45, 0.85])
    with col1:
        st.markdown('<div class="section-label">Parking Map</div>', unsafe_allow_html=True)
        parking_map(parking_df)
        parking_legend()
    with col2:
        st.markdown('<div class="section-label">Parking Data</div>', unsafe_allow_html=True)
        data_panel(
            "Smart Parking",
            [
                ("Parking city", parking.get("city", parking_city)),
                ("Starting location", start_location),
                ("Destination", end_location),
                ("Parking points", str(parking.get("total_facilities", 0))),
                ("Vacant slots", str(parking.get("vacant_spaces", 0))),
                ("Occupied slots", str(parking.get("occupied_spaces", 0))),
                ("Availability", f"{parking.get('availability_rate', 0)}%"),
            ],
            "Green = available, red = full.",
        )
        if not parking_df.empty:
            slot_counts = pd.DataFrame(
                [
                    {"status": "Vacant slots", "count": parking.get("vacant_spaces", 0)},
                    {"status": "Occupied slots", "count": parking.get("occupied_spaces", 0)},
                ]
            )
            fig = px.pie(
                slot_counts,
                names="status",
                values="count",
                color="status",
                color_discrete_map={"Vacant slots": "#0f9f8f", "Occupied slots": "#dc2626"},
                hole=0.48,
            )
            fig.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10), legend_title_text="")
            st.plotly_chart(fig, use_container_width=True)
    if not parking_df.empty:
        st.markdown('<div class="section-label">Parking Slots Data</div>', unsafe_allow_html=True)
        table_columns = [
            "name",
            "parking_type",
            "available_slots",
            "capacity",
            "availability_percent",
            "status",
            "fee",
            "access",
        ]
        st.dataframe(
            parking_df[[column for column in table_columns if column in parking_df.columns]].head(180),
            use_container_width=True,
            hide_index=True,
        )

with road_tab:
    st.markdown('<div class="section-label">Road Damage Map Survey</div>', unsafe_allow_html=True)
    segment_col1, segment_col2, segment_col3 = st.columns([1, 1, 0.8])
    with segment_col1:
        road_segment_start = st.text_input("Starting location", value=start_location)
    with segment_col2:
        road_segment_end = st.text_input("Destination", value=end_location)
    with segment_col3:
        survey_mode = st.selectbox(
            "Survey mode",
            ["Routine survey", "After heavy rain", "Citizen complaints", "Construction zone"],
        )

    if road_segment_start.strip().lower() == road_segment_end.strip().lower():
        st.warning("Enter two different locations to map road damage.")
    else:
        try:
            with st.spinner("Loading road segment and damage data..."):
                damage_route = load_traffic_route(backend_url, road_segment_start, road_segment_end)
            result = route_damage_report(damage_route, road_segment_start, road_segment_end, survey_mode)
        except requests.RequestException as exc:
            st.error(f"Could not load road segment: {exc}")
            st.stop()

        metric_grid(
            [
                ("Damage Score", f"{result.get('score', 0)}", result.get("severity", "Low")),
                ("Damage Points", str(result.get("detection_count", 0)), "mapped points"),
                ("Affected Area", f"{result.get('damage_area_percent', 0)}%", "estimated route"),
                ("Road Segment", f"{road_segment_start} to {road_segment_end}", survey_mode),
            ]
        )

        map_col, data_col = st.columns([1.45, 0.85])
        with map_col:
            st.markdown('<div class="section-label">Damaged Road Area Map</div>', unsafe_allow_html=True)
            mapped_damage = road_damage_map(damage_route, result, road_segment_start, road_segment_end)
        with data_col:
            st.markdown('<div class="section-label">Road Damage Data</div>', unsafe_allow_html=True)
            data_panel(
                "Road Damage Detection",
                [
                    ("Starting location", road_segment_start),
                    ("Destination", road_segment_end),
                    ("Survey mode", survey_mode),
                    ("Damage points", str(result.get("detection_count", 0))),
                    ("Severity", result.get("severity", "-")),
                    ("Affected area", f"{result.get('damage_area_percent', 0)}%"),
                    ("Action", result.get("recommendation", "-")),
                ],
                "Red = damaged road points.",
            )
        if not mapped_damage.empty:
            st.markdown('<div class="section-label">Damage Location Data</div>', unsafe_allow_html=True)
            map_columns = [
                "id",
                "road_segment",
                "severity",
                "type",
                "damage_location",
                "map_latitude",
                "map_longitude",
                "estimated_length_m",
                "lane",
                "priority",
                "action",
            ]
            st.dataframe(mapped_damage[map_columns], use_container_width=True, hide_index=True)
        else:
            st.info("No road damage points were generated for this route.")

st.caption(
    "Traffic route, India parking slots, and map-based road damage survey."
)
