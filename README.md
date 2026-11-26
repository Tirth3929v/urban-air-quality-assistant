# Urban Air Quality Assistant

A Generative AI web application that turns live local winter smog telemetry into personalized low-emission daily routines, budget-tiered indoor air quality hacks, and quantified exposure/emission savings for urban families.

## Key Features
- **Live Pollutant-Signature Grounding:** Fetches real-time `PM2.5`, `PM10`, `NO2`, `CO`, `O3`, and `US AQI` plus 24-hour hourly forecasts via Open-Meteo APIs (zero API key required).
- **Cleanest 2-Hour Window Finder:** Automatically scans the next 24 hours of hourly `PM2.5` forecasts to pinpoint the safest 2-hour window for ventilation or outdoor errands.
- **Structured Gemini 2.5 Flash Reasoning:** Uses Pydantic `response_schema` with `gemini-2.5-flash` to deliver deterministic, tailored daily schedules, zero-cost/low-cost indoor hacks, and sustainable habit swaps.
- **Interactive "What-If" Habit Simulator:** Lets households toggle individual habits to recalculate live personal `PM2.5` exposure reduction, weekly `CO2` avoided, and annual tree equivalents.
- **Vernacular Family Checklist:** One-click translation into **Hindi** and **Gujarati** with downloadable Markdown action cards.

## Architecture
1. `app.py` — Accessible Streamlit dashboard with `@st.cache_data` caching and Plotly visualizations.
2. `services/aqi_service.py` — Geocoding, 6-pollutant telemetry retrieval, smog-driver classification, and 2-hour clean-window optimization.
3. `services/genai_service.py` — Gemini 2.5 Flash structured plan generation and vernacular checklist translation.
4. `utils/security.py` — Regex city allowlisting, character-length caps, HTML escaping, and XML delimiter boundaries (`<user_context>`) against prompt injection.
5. `utils/metrics.py` — Deterministic impact scaling for the interactive habit simulator.

## Quick Start
```bash
git clone https://github.com/<your-username>/urban-air-quality-assistant.git
cd urban-air-quality-assistant
pip install -r requirements.txt
cp .env.example .env  # Add your GEMINI_API_KEY
pytest -v
streamlit run app.py
```
