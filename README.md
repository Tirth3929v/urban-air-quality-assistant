# Urban Air Quality Assistant

A Generative AI web application that turns live local winter smog telemetry into personalized low-emission daily routines, budget-tiered indoor air quality hacks, and quantified exposure/emission savings for urban families.

## Key Features
- **Live Pollutant-Signature Grounding:** Fetches real-time `PM2.5`, `PM10`, `NO2`, `CO`, `O3`, and `US AQI` plus 24-hour hourly forecasts via Open-Meteo APIs (zero API key required).
- **Cleanest 2-Hour Window Finder:** Automatically scans the next 24 hours of hourly `PM2.5` forecasts to pinpoint the safest 2-hour window for ventilation or outdoor errands.
- **Structured Gemini 2.5 Flash Reasoning:** Uses Pydantic `response_schema` with `gemini-2.5-flash` (and automatic `503`/`429` fallback to `gemini-2.5-flash-lite` and `gemini-2.0-flash`) to deliver deterministic, tailored daily schedules, zero-cost/low-cost indoor hacks, and sustainable habit swaps.
- **Interactive "What-If" Habit Simulator:** Lets households toggle individual habits to recalculate live personal `PM2.5` exposure reduction, weekly `CO2` avoided, and annual tree equivalents.
- **Vernacular Family Checklist:** One-click translation into **Hindi** and **Gujarati** with downloadable Markdown action cards.

## Architecture
1. `app.py` — Accessible Streamlit dashboard with `@st.cache_data` caching and Plotly visualizations.
2. `services/aqi_service.py` — Pooled HTTP session, geocoding, 6-pollutant telemetry retrieval, EPA AQI categorization, smog-driver classification, and 2-hour clean-window optimization.
3. `services/genai_service.py` — Gemini 2.5 Flash structured plan generation, multi-model fallback resilience, and vernacular checklist translation.
4. `utils/security.py` — Regex city allowlisting, character-length caps, HTML escaping, error sanitization, and XML delimiter boundaries (`<user_context>`) against prompt injection.
5. `utils/metrics.py` — Deterministic impact scaling for the interactive habit simulator.

## Security, Accessibility & Testing
- **Security Controls:** Strict city-name regex allowlisting, XML delimiter boundaries (`<user_context>`, `<report_content>`), HTML escaping (`escape_for_display`), safe error masking (`sanitize_error_message`), `.env` exclusion, and 10s outbound API timeouts.
- **Accessibility:** High-contrast `.streamlit/config.toml` theme, semantic `h1` → `h2` → `h3` heading hierarchy, non-color-dependent EPA AQI severity badges, Okabe-Ito colorblind-safe charts (`#0072B2`, `#D55E00`), and plain-text chart summaries.
- **CI & Testing:** Automated GitHub Actions workflow (`.github/workflows/ci.yml`) running `ruff check .` and `pytest -v --cov=services --cov=utils`.

## Quick Start
```bash
git clone https://github.com/Tirth3929v/urban-air-quality-assistant.git
cd urban-air-quality-assistant
pip install -r requirements.txt
cp .env.example .env  # Add your GEMINI_API_KEY
ruff check .
pytest -v --cov=services --cov=utils
streamlit run app.py
```
