# 🌍 COVID-19 Data Explorer

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/tests-27%20passed-4CAF50?style=flat-square&logo=pytest&logoColor=white" alt="27 tests passed">
  <img src="https://img.shields.io/badge/data-disease.sh%20API-0A2647?style=flat-square" alt="disease.sh API">
  <img src="https://img.shields.io/badge/license-MIT-blue?style=flat-square" alt="MIT License">
</p>

<p align="center">
  <b>An interactive epidemiology dashboard — country comparisons, animated trend lines, vaccination-vs-case correlation, and a choropleth world map, powered by the disease.sh public API with automatic offline fallback.</b>
</p>

---

## 📑 Table of Contents

- [Overview](#-overview)
- [Problem Statement](#-problem-statement)
- [Features](#-features)
- [Live Data with Graceful Offline Fallback](#-live-data-with-graceful-offline-fallback)
- [Technology Stack](#-technology-stack)
- [Architecture](#-architecture)
- [Folder Structure](#-folder-structure)
- [Installation](#-installation)
- [Usage](#-usage)
- [Testing](#-testing)
- [Demo](#-demo)
- [Future Roadmap](#-future-roadmap)
- [Contributing](#-contributing)
- [License](#-license)

## 🎯 Overview

Public health agencies track outbreaks with exactly this kind of tool: live case/death/vaccination data, broken down by country, visualized as trends and maps rather than raw numbers in a spreadsheet. This dashboard pulls from the disease.sh public API and presents it across five focused views — global overview, time-series trends, country-to-country comparison, vaccination impact analysis, and a world map.

## ❓ Problem Statement

Raw epidemiological data is a firehose — hundreds of countries, daily cumulative counts, several metrics per country. Nobody can answer "is this country's outbreak improving?" or "does vaccination coverage actually track with lower case rates?" from a raw JSON API response. This dashboard turns that firehose into five specific, answerable views.

## ✨ Features

- 📊 **Global overview** — total cases/deaths/recovered/active KPIs, plus a top-10 case-fatality-rate leaderboard.
- 📈 **Trend analysis** — 7-day rolling average of daily new cases/deaths, smoothing out weekday reporting noise (the standard epidemiological visualization technique).
- 🌐 **Country comparison** — side-by-side bar charts and tables for any set of selected countries.
- 💉 **Vaccination impact** — a correlation scatter plot (with OLS trendline) exploring whether vaccination coverage associates with lower case rates.
- 🗺️ **Interactive choropleth world map** — color countries by cases/deaths/tests per million, selectable live.
- 🔄 **Live data with automatic offline fallback** — see below.
- ✅ **27 automated tests**, including fully-mocked HTTP tests (zero real network calls in the test suite) and a full-app render verification via Streamlit's `AppTest` framework.

## 🔄 Live Data with Graceful Offline Fallback

This dashboard tries the **live disease.sh API first**. If it's unreachable — no internet, API downtime, or a sandboxed environment with restricted network egress — it automatically and transparently falls back to a bundled local JSON snapshot, and tells the user which mode it's in via a banner at the top of the page:

```
🟢 Showing live data from disease.sh          (when the API is reachable)
📦 Showing a cached data snapshot ...          (when it isn't)
```

This is the same graceful-degradation pattern used in this portfolio's Day 18 SmartNotes AI provider — **an external dependency being down should degrade the experience, not break the app.**

> **Note on this development environment:** this project was built in a sandboxed container with restricted network egress (only package-registry domains are reachable), so `disease.sh` could not be reached during development/testing here. The fallback path was exercised and verified extensively instead — in a normal deployment with open internet access, the live API path runs automatically with zero configuration changes.

## 🛠️ Technology Stack

| Layer | Technology | Why |
|---|---|---|
| UI framework | Streamlit | Interactive dashboard with zero HTML/JS |
| Data source | disease.sh public API | Free, no API key required, comprehensive country-level COVID data |
| HTTP client | `requests` | Simple, well-tested HTTP calls |
| Data processing | Pandas | Rolling averages, comparisons, correlation tables |
| Visualization | Plotly Express / Graph Objects | Interactive charts + choropleth maps |
| Statistics | `statsmodels` | OLS trendline for the vaccination correlation scatter |
| Testing | `pytest` + `streamlit.testing.v1.AppTest` | Mocked HTTP unit tests + full-app render verification |

## 🏗️ Architecture

```
                disease.sh public API
                         ↓
              api_client.py          ← Pure HTTP layer (no fallback logic)
                         ↓
              data_loader.py            ← Live API → fallback to cached JSON snapshot
                         ↓
              analytics.py                 ← Pure functions: rolling avg, comparisons, correlation
                         ↓
              visualizer.py                    ← Plotly charts, Navy Blue brand theme
                         ↓
              app.py                              ← Streamlit UI: tabs, widgets, CSS theme
```

**Key design decision — `api_client.py` has NO fallback logic:** it either succeeds or raises `ApiUnavailableError`. All the "what do we do if this fails" decision-making lives in `data_loader.py` alone. This separation is what makes both layers independently testable: `api_client.py`'s tests mock `requests.get` directly; `data_loader.py`'s tests mock the *client functions* and verify the fallback behavior, without either test file needing to know about the other's internals.

## 📁 Folder Structure

```
day24_covid_explorer/
├── app.py                       # Streamlit entry point (streamlit run app.py)
├── requirements.txt
├── README.md
├── GUIDE.txt                      # Roman Urdu setup guide
├── data/
│   └── cached_covid_data.json       # Offline fallback snapshot (15 countries, 180-day history for 5)
├── src/
│   ├── __init__.py
│   ├── exceptions.py
│   ├── api_client.py                 # Pure disease.sh HTTP client
│   ├── data_loader.py                   # Live-API-first, cache-fallback orchestration
│   ├── analytics.py                        # Pure rolling-avg / comparison / correlation functions
│   └── visualizer.py                          # Plotly chart builders, Navy Blue theme
└── tests/
    ├── test_api_client.py                       # Mocked HTTP tests
    ├── test_data_loader.py                         # Fallback logic + shape normalization tests
    ├── test_analytics.py                              # Hand-verified aggregation math
    └── test_visualizer.py
```

## ⚙️ Installation

```bash
git clone https://github.com/<your-username>/covid19-data-explorer.git
cd covid19-data-explorer
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 🚀 Usage

```bash
streamlit run app.py
```

Opens in your browser (default `http://localhost:8501`). No API key or configuration needed — it fetches live data automatically, or falls back to the bundled snapshot if the API is unreachable.

## 🧪 Testing

```bash
python -m pytest tests/ -v
```

**Result: 27/27 tests passing.** The HTTP layer is tested with fully mocked responses (no real network calls). The full app was additionally verified end-to-end with Streamlit's official `AppTest` framework — all 5 tabs, 5 KPI metrics, 4 charts, and 2 data tables render with zero exceptions.

## 🎬 Demo

Verified live in this sandboxed environment (network-restricted, so the fallback path is what actually ran):

```
WARNING: Live API unavailable (403 Forbidden), falling back to cached snapshot
App ran without exceptions: True
Number of tabs: 5
Number of metrics: 5
 - Total Cases      450,647,000
 - Total Deaths       4,063,150
 - Total Recovered  436,982,781
 - Active Cases       9,782,210
 - Global Fatality Rate   0.9%
```

The fallback triggered automatically, exactly as designed — the dashboard stayed fully functional with zero crashes.

## 🗺️ Future Roadmap

- [ ] Add a date-range slider for custom historical windows
- [ ] Continent-level aggregation view
- [ ] Deploy to Streamlit Community Cloud for a live public demo
- [ ] Add a "compare to previous wave" overlay on the trend chart
- [ ] Cache live API responses locally with a TTL, rather than only falling back on total failure

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for any new logic (mock HTTP calls — never make real API calls in tests)
4. Ensure `pytest tests/` passes before opening a PR

## 📄 License

MIT License — free to use, modify, and distribute.