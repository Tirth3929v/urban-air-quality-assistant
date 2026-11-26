"""Urban Air Quality Assistant — Streamlit Application."""

import os
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

from services.aqi_service import AirQualitySnapshot, fetch_air_quality
from services.genai_service import AirQualityActionPlan, generate_action_plan
from utils.security import sanitize_city_name

load_dotenv()

# Support Streamlit Cloud secrets seamlessly
try:
    if "GEMINI_API_KEY" in st.secrets and not os.getenv("GEMINI_API_KEY"):
        os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]
except Exception:
    pass

st.set_page_config(
    page_title="Urban Air Quality Assistant",
    page_icon="🌿",
    layout="wide",
)


@st.cache_data(ttl=600, show_spinner=False)
def cached_air_quality(city: str) -> AirQualitySnapshot:
    """Cache live air quality lookups for 10 minutes to improve efficiency."""
    return fetch_air_quality(city)


@st.cache_data(ttl=600, show_spinner=False)
def cached_action_plan(
    snapshot: AirQualitySnapshot,
    household_group: str,
    commute_mode: str,
    home_setup: str,
    custom_notes: str,
) -> AirQualityActionPlan:
    """Cache generated Gemini action plans for identical inputs."""
    return generate_action_plan(
        snapshot=snapshot,
        household_group=household_group,
        commute_mode=commute_mode,
        home_setup=home_setup,
        custom_notes=custom_notes,
    )


def format_markdown_report(
    snapshot: AirQualitySnapshot, plan: AirQualityActionPlan
) -> str:
    """Build a downloadable Markdown summary for families."""
    lines = [
        f"# Family Winter Smog Action Plan — {snapshot.city_label}",
        f"- **US AQI:** {snapshot.us_aqi:.0f} | **PM2.5:** {snapshot.pm2_5:.1f} µg/m³ | **NO2:** {snapshot.nitrogen_dioxide:.1f} µg/m³",
        f"- **Dominant Smog Driver:** {snapshot.dominant_driver}",
        f"- **Best 2-Hour Outdoor Window:** {snapshot.cleanest_window}",
        f"- **Estimated Exposure Reduction:** {plan.estimated_exposure_reduction_pct}%",
        f"- **Estimated Weekly CO2 Saved:** {plan.weekly_co2_saved_kg:.1f} kg\n",
        f"## Smog Diagnosis\n{plan.smog_diagnosis}\n",
        "## Low-Emission Daily Routine",
    ]
    for item in plan.daily_routine:
        lines.append(
            f"- **{item.time_of_day} — {item.action_title}:** {item.recommendation} *(Impact: {item.direct_impact})*"
        )
    lines.append("\n## Indoor Air Quality Hacks")
    for hack in plan.indoor_air_hacks:
        lines.append(
            f"- **[{hack.cost_tier}] {hack.hack_title}:** {hack.steps} *(Why: {hack.why_it_works})*"
        )
    lines.append("\n## Sustainable Alternatives")
    for swap in plan.sustainable_alternatives:
        lines.append(
            f"- **{swap.current_habit} → {swap.sustainable_alternative}:** {swap.estimated_emission_cut}"
        )
    return "\n".join(lines)


def main() -> None:
    """Render the Urban Air Quality Assistant interface."""
    st.title("Urban Air Quality Assistant")
    st.caption(
        "Turn live local winter smog data into personalized low-emission routines, indoor air hacks, and quantified impact."
    )

    with st.sidebar:
        st.header("Household & Lifestyle Profile")
        city_input = st.text_input(
            "City Name",
            value="New Delhi",
            max_chars=60,
            help="Enter your city to fetch live PM2.5, PM10, NO2, and 24-hour smog forecasts.",
        )
        household_group = st.selectbox(
            "Household Sensitivity",
            [
                "General Adult Household",
                "Family with Young Children",
                "Household with Seniors (60+)",
                "Asthma / Respiratory Sensitivity",
            ],
            help="Adjusts outdoor exposure thresholds and indoor air protection urgency.",
        )
        commute_mode = st.selectbox(
            "Primary Daily Commute",
            [
                "Two-Wheeler / Scooter",
                "Private Petrol/Diesel Car",
                "Public Transit (Metro / Bus)",
                "Work From Home / Minimal Travel",
                "Walking / Cycling",
            ],
            help="Tailors low-emission commute swaps and peak-hour exposure advice.",
        )
        home_setup = st.selectbox(
            "Home Setup & Equipment",
            [
                "Apartment — No Air Purifier (Budget Hacks)",
                "Apartment — With HEPA Air Purifier",
                "Independent House — Natural Ventilation",
            ],
            help="Selects zero-cost vs. purifier-assisted indoor air quality interventions.",
        )
        custom_notes = st.text_area(
            "Optional Daily Habits (Cooking, Exercise, School Run)",
            placeholder="e.g., Morning walk at 7 AM, heavy frying/tadka in evening, kids school bus at 7:30 AM",
            max_chars=250,
            help="Optional details to personalize your routine (max 250 characters).",
        )
        generate_btn = st.button("Generate Personalized Action Plan", type="primary", use_container_width=True)

    if not generate_btn and "last_snapshot" not in st.session_state:
        st.info("Configure your city and household profile in the sidebar, then click **Generate Personalized Action Plan**.")
        return

    try:
        clean_city = sanitize_city_name(city_input)
        with st.spinner("Fetching live pollutant readings and generating tailored smog solutions..."):
            snapshot = cached_air_quality(clean_city)
            plan = cached_action_plan(
                snapshot=snapshot,
                household_group=household_group,
                commute_mode=commute_mode,
                home_setup=home_setup,
                custom_notes=custom_notes,
            )
            st.session_state["last_snapshot"] = snapshot
            st.session_state["last_plan"] = plan
    except Exception as exc:
        st.error(f"Unable to generate plan: {exc}")
        return

    snapshot = st.session_state["last_snapshot"]
    plan = st.session_state["last_plan"]

    st.subheader(f"Live Air Quality Snapshot: {snapshot.city_label}")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("US AQI", f"{snapshot.us_aqi:.0f}")
    m2.metric("PM2.5", f"{snapshot.pm2_5:.1f} µg/m³")
    m3.metric("NO2 (Traffic)", f"{snapshot.nitrogen_dioxide:.1f} µg/m³")
    m4.metric("Potential Exposure Cut", f"-{plan.estimated_exposure_reduction_pct}%")

    st.info(
        f"**Primary Smog Driver:** {snapshot.dominant_driver}  \n"
        f"**Cleanest 2-Hour Outdoor Window:** {snapshot.cleanest_window}"
    )

    st.markdown(f"**Health & Smog Diagnosis:** {plan.smog_diagnosis}")

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "Low-Emission Daily Routine",
            "Indoor Air Quality Hacks",
            "Sustainable Alternatives",
            "24-Hour PM2.5 Forecast",
        ]
    )

    with tab1:
        for block in plan.daily_routine:
            with st.container(border=True):
                st.markdown(f"### {block.time_of_day}: {block.action_title}")
                st.write(block.recommendation)
                st.caption(f"Direct Impact: {block.direct_impact}")

    with tab2:
        for hack in plan.indoor_air_hacks:
            with st.container(border=True):
                st.markdown(f"### [{hack.cost_tier}] {hack.hack_title}")
                st.write(hack.steps)
                st.caption(f"Why It Works: {hack.why_it_works}")

    with tab3:
        st.metric("Estimated Weekly Household CO2 Avoided", f"{plan.weekly_co2_saved_kg:.1f} kg CO2/week")
        for swap in plan.sustainable_alternatives:
            with st.container(border=True):
                st.markdown(f"**Swap:** {swap.current_habit} → **{swap.sustainable_alternative}**")
                st.caption(f"Impact: {swap.estimated_emission_cut}")

    with tab4:
        if snapshot.hourly_times and snapshot.hourly_pm2_5:
            hours = [t.split("T")[-1] for t in snapshot.hourly_times]
            fig = px.area(
                x=hours,
                y=snapshot.hourly_pm2_5,
                labels={"x": "Local Time (Next 24 Hours)", "y": "PM2.5 (µg/m³)"},
                title=f"24-Hour PM2.5 Trend for {snapshot.city_label}",
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                f"Text Summary: Over the next 24 hours, PM2.5 ranges from {min(snapshot.hourly_pm2_5):.1f} µg/m³ "
                f"to {max(snapshot.hourly_pm2_5):.1f} µg/m³. Best outdoor window: {snapshot.cleanest_window}."
            )

    report_md = format_markdown_report(snapshot, plan)
    st.download_button(
        label="Download Family Smog Action Plan (.md)",
        data=report_md,
        file_name="family_winter_smog_plan.md",
        mime="text/markdown",
    )


if __name__ == "__main__":
    main()
