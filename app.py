"""Urban Air Quality Assistant — Streamlit Application."""

import os

import plotly.express as px
import requests
import streamlit as st
from dotenv import load_dotenv

from services.aqi_service import AirQualitySnapshot, categorize_us_aqi, fetch_air_quality
from services.genai_service import (
    AirQualityActionPlan,
    generate_action_plan,
    translate_action_plan,
)
from utils.metrics import calculate_simulated_impact
from utils.security import escape_for_display, sanitize_city_name, sanitize_error_message

load_dotenv()

# Support Streamlit Cloud secrets seamlessly
try:
    if "GEMINI_API_KEY" in st.secrets and not os.getenv("GEMINI_API_KEY"):
        os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]
except (FileNotFoundError, KeyError, RuntimeError, PermissionError):
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


@st.cache_data(ttl=600, show_spinner=False)
def cached_translated_report(report_md: str, language: str) -> str:
    """Cache translated family checklists for 10 minutes."""
    return translate_action_plan(report_md, language)


def format_markdown_report(
    snapshot: AirQualitySnapshot, plan: AirQualityActionPlan
) -> str:
    """Build a downloadable Markdown summary for families."""
    aqi_category, _ = categorize_us_aqi(snapshot.us_aqi)
    lines = [
        f"# Family Winter Smog Action Plan — {snapshot.city_label}",
        (
            f"- **US AQI:** {snapshot.us_aqi:.0f} ({aqi_category}) | "
            f"**PM2.5:** {snapshot.pm2_5:.1f} µg/m³ | "
            f"**NO2:** {snapshot.nitrogen_dioxide:.1f} µg/m³"
        ),
        f"- **Dominant Smog Driver:** {snapshot.dominant_driver}",
        f"- **Best 2-Hour Outdoor Window:** {snapshot.cleanest_window}",
        f"- **Estimated Exposure Reduction:** {plan.estimated_exposure_reduction_pct}%",
        f"- **Estimated Weekly CO2 Saved:** {plan.weekly_co2_saved_kg:.1f} kg\n",
        f"## Smog Diagnosis\n{plan.smog_diagnosis}\n",
        "## Low-Emission Daily Routine",
    ]
    for item in plan.daily_routine:
        lines.append(
            f"- **{item.time_of_day} — {item.action_title}:** {item.recommendation} "
            f"*(Impact: {item.direct_impact})*"
        )
    lines.append("\n## Indoor Air Quality Hacks")
    for hack in plan.indoor_air_hacks:
        lines.append(
            f"- **[{hack.cost_tier}] {hack.hack_title}:** {hack.steps} *(Why: {hack.why_it_works})*"
        )
    lines.append("\n## Sustainable Alternatives")
    for swap in plan.sustainable_alternatives:
        lines.append(
            f"- **{swap.current_habit} → {swap.sustainable_alternative}:** "
            f"{swap.estimated_emission_cut}"
        )
    return "\n".join(lines)


def render_sidebar() -> tuple[str, str, str, str, str, bool]:
    """Render sidebar controls and return user profile inputs."""
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
            placeholder="e.g., Morning walk at 7 AM, heavy frying/tadka in evening",
            max_chars=250,
            help="Optional details to personalize your routine (max 250 characters).",
        )
        generate_btn = st.button(
            "Generate Personalized Action Plan",
            type="primary",
            use_container_width=True,
        )
    return city_input, household_group, commute_mode, home_setup, custom_notes, generate_btn


def render_live_snapshot(snapshot: AirQualitySnapshot, plan: AirQualityActionPlan) -> None:
    """Render live pollutant metrics, EPA severity badge, and diagnosis."""
    st.header(f"Live Air Quality Snapshot: {snapshot.city_label}")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("US AQI", f"{snapshot.us_aqi:.0f}")
    m2.metric("PM2.5", f"{snapshot.pm2_5:.1f} µg/m³")
    m3.metric("NO2 (Traffic)", f"{snapshot.nitrogen_dioxide:.1f} µg/m³")
    m4.metric("Potential Exposure Cut", f"-{plan.estimated_exposure_reduction_pct}%")

    aqi_category, aqi_guidance = categorize_us_aqi(snapshot.us_aqi)
    st.info(
        f"**EPA Severity:** [{aqi_category}] {aqi_guidance}  \n"
        f"**Primary Smog Driver:** {snapshot.dominant_driver}  \n"
        f"**Cleanest 2-Hour Outdoor Window:** {snapshot.cleanest_window}"
    )
    st.markdown(f"**Health & Smog Diagnosis:** {plan.smog_diagnosis}")


def render_simulator_tab(snapshot: AirQualitySnapshot, plan: AirQualityActionPlan) -> None:
    """Render interactive What-If Habit Simulator with Okabe-Ito colorblind-safe chart."""
    st.markdown("Select the habits your family commits to adopting this week:")
    c_left, c_right = st.columns(2)
    exp_selected = 0
    exp_total = len(plan.daily_routine) + len(plan.indoor_air_hacks)
    co2_selected = 0
    co2_total = len(plan.sustainable_alternatives)

    with c_left:
        st.subheader("Personal Exposure Protection Habits")
        for idx, item in enumerate(plan.daily_routine):
            if st.checkbox(
                f"{item.time_of_day}: {item.action_title}", value=True, key=f"sim_r_{idx}"
            ):
                exp_selected += 1
        for idx, hack in enumerate(plan.indoor_air_hacks):
            if st.checkbox(f"[{hack.cost_tier}] {hack.hack_title}", value=True, key=f"sim_h_{idx}"):
                exp_selected += 1

    with c_right:
        st.subheader("Community Emission-Cutting Swaps")
        for idx, swap in enumerate(plan.sustainable_alternatives):
            if st.checkbox(
                f"Switch to: {swap.sustainable_alternative}", value=True, key=f"sim_s_{idx}"
            ):
                co2_selected += 1

    sim = calculate_simulated_impact(
        max_exposure_pct=plan.estimated_exposure_reduction_pct,
        max_weekly_co2_kg=plan.weekly_co2_saved_kg,
        exposure_habits_selected=exp_selected,
        exposure_habits_total=exp_total,
        emission_swaps_selected=co2_selected,
        emission_swaps_total=co2_total,
    )

    s1, s2, s3 = st.columns(3)
    s1.metric("Active Exposure Shield", f"-{sim.active_exposure_pct}% PM2.5")
    s2.metric("Active CO2 Prevented", f"{sim.active_weekly_co2_kg:.1f} kg/week")
    s3.metric("Annual Tree Equivalent", f"{sim.annual_trees_equivalent:.1f} trees/yr")

    effective_pm25 = round(snapshot.pm2_5 * (1 - sim.active_exposure_pct / 100.0), 1)
    comp_fig = px.bar(
        x=["Unprotected Outdoor PM2.5", "With Selected Family Shield"],
        y=[snapshot.pm2_5, effective_pm25],
        color=["Unprotected Outdoor PM2.5", "With Selected Family Shield"],
        color_discrete_sequence=["#D55E00", "#0072B2"],
        labels={"x": "Scenario", "y": "Estimated PM2.5 Exposure (µg/m³)"},
        title="Estimated Personal PM2.5 Exposure Reduction",
    )
    comp_fig.update_layout(showlegend=False)
    st.plotly_chart(comp_fig, use_container_width=True)
    st.caption(
        f"Text Summary: Selecting {exp_selected}/{exp_total} exposure habits lowers "
        f"estimated personal PM2.5 exposure from {snapshot.pm2_5:.1f} µg/m³ "
        f"to {effective_pm25:.1f} µg/m³."
    )


def render_checklist_section(snapshot: AirQualitySnapshot, plan: AirQualityActionPlan) -> None:
    """Render vernacular checklist translator and Markdown download button."""
    st.divider()
    st.header("Shareable Family Action Checklist")
    checklist_lang = st.radio(
        "Checklist Language",
        ["English", "Hindi", "Gujarati"],
        horizontal=True,
        help="Translate the family action plan so elders and household members can read it easily.",
    )
    report_md = format_markdown_report(snapshot, plan)
    if checklist_lang != "English":
        with st.spinner(f"Translating checklist to {checklist_lang}..."):
            report_md = cached_translated_report(report_md, checklist_lang)

    with st.expander("Preview Printable / Shareable Checklist", expanded=False):
        st.markdown(report_md)

    st.download_button(
        label=f"Download Family Smog Plan ({checklist_lang} .md)",
        data=report_md,
        file_name=f"family_winter_smog_plan_{checklist_lang.lower()}.md",
        mime="text/markdown",
    )


def main() -> None:
    """Render the Urban Air Quality Assistant interface."""
    st.title("Urban Air Quality Assistant")
    st.caption(
        "Turn live local winter smog data into personalized low-emission routines, "
        "indoor air hacks, and quantified impact."
    )

    city_input, household_group, commute_mode, home_setup, custom_notes, generate_btn = (
        render_sidebar()
    )

    if not generate_btn and "last_snapshot" not in st.session_state:
        st.info(
            "Configure your city and household profile in the sidebar, then click "
            "**Generate Personalized Action Plan**."
        )
        return

    try:
        clean_city = sanitize_city_name(city_input)
        with st.spinner("Fetching live pollutant readings and generating tailored smog plan..."):
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
    except (ValueError, requests.RequestException, RuntimeError) as exc:
        st.error(escape_for_display(sanitize_error_message(exc)))
        return

    snapshot = st.session_state["last_snapshot"]
    plan = st.session_state["last_plan"]
    render_live_snapshot(snapshot, plan)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "Low-Emission Daily Routine",
            "Indoor Air Quality Hacks",
            "Sustainable Alternatives",
            "What-If Habit Simulator",
            "24-Hour PM2.5 Forecast",
        ]
    )

    with tab1:
        for block in plan.daily_routine:
            with st.container(border=True):
                st.subheader(f"{block.time_of_day}: {block.action_title}")
                st.write(block.recommendation)
                st.caption(f"Direct Impact: {block.direct_impact}")

    with tab2:
        for hack in plan.indoor_air_hacks:
            with st.container(border=True):
                st.subheader(f"[{hack.cost_tier}] {hack.hack_title}")
                st.write(hack.steps)
                st.caption(f"Why It Works: {hack.why_it_works}")

    with tab3:
        st.metric(
            "Estimated Weekly Household CO2 Avoided",
            f"{plan.weekly_co2_saved_kg:.1f} kg CO2/week",
        )
        for swap in plan.sustainable_alternatives:
            with st.container(border=True):
                st.markdown(f"**Swap:** {swap.current_habit} → **{swap.sustainable_alternative}**")
                st.caption(f"Impact: {swap.estimated_emission_cut}")

    with tab4:
        render_simulator_tab(snapshot, plan)

    with tab5:
        if snapshot.hourly_times and snapshot.hourly_pm2_5:
            hours = [t.split("T")[-1] for t in snapshot.hourly_times]
            fig = px.area(
                x=hours,
                y=snapshot.hourly_pm2_5,
                color_discrete_sequence=["#0072B2"],
                labels={"x": "Local Time (Next 24 Hours)", "y": "PM2.5 (µg/m³)"},
                title=f"24-Hour PM2.5 Trend for {snapshot.city_label}",
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                f"Text Summary: Over the next 24 hours, PM2.5 ranges from "
                f"{min(snapshot.hourly_pm2_5):.1f} µg/m³ to "
                f"{max(snapshot.hourly_pm2_5):.1f} µg/m³. "
                f"Best outdoor window: {snapshot.cleanest_window}."
            )

    render_checklist_section(snapshot, plan)


if __name__ == "__main__":
    main()
