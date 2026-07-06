"""
app.py
======
Streamlit entry point. Run with: streamlit run app.py

UX/UI note: this dashboard uses a TAB-based layout (Overview / Trends
/ Compare Countries / Vaccination Impact / World Map) with a custom
Navy Blue theme injected via CSS -- deliberately different from the
Day 21 sales dashboard's single-scroll layout, while sharing the same
brand color, so the portfolio feels like one designer's work across
projects rather than a copy-pasted template.
"""

from __future__ import annotations

import logging

import streamlit as st

from src.analytics import (
    build_country_comparison_table,
    build_vaccination_correlation_table,
    compute_case_fatality_rate,
    compute_rolling_average,
)
from src.data_loader import load_covid_dataset
from src.exceptions import CovidDataError
from src.visualizer import (
    build_country_comparison_chart,
    build_rolling_average_chart,
    build_vaccination_correlation_chart,
    build_world_choropleth_map,
)

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

st.set_page_config(page_title="COVID-19 Data Explorer", page_icon="🌍", layout="wide")

# --- Navy Blue brand theme, injected via CSS ---------------------------
# Streamlit's built-in theming can't target every element we want to
# restyle (metric card borders, tab underlines), so a scoped CSS block
# is injected instead. Kept to color/border/spacing only -- no layout
# hacks that would break on a Streamlit version bump.
st.markdown(
    """
    <style>
    :root {
        --navy-darkest: #0A2647;
        --navy-dark: #144272;
        --navy-medium: #205295;
        --navy-light: #2C74B3;
    }
    div[data-testid="stMetric"] {
        background-color: #F4F8FB;
        border: 1px solid #D6E4F0;
        border-left: 5px solid var(--navy-dark);
        border-radius: 8px;
        padding: 12px 16px;
    }
    div[data-testid="stMetricLabel"] {
        color: var(--navy-dark);
        font-weight: 600;
    }
    h1, h2, h3 {
        color: var(--navy-darkest);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #F4F8FB;
        border-radius: 6px 6px 0 0;
        color: var(--navy-dark);
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: var(--navy-dark) !important;
        color: white !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=3600)
def _load_dataset():
    """Load the COVID dataset, cached for 1 hour so repeated Streamlit
    reruns (every widget interaction) don't re-fetch/re-parse the same
    data dozens of times per session.
    """
    return load_covid_dataset()


def render_header(dataset) -> None:
    """Render the dashboard title and data-freshness indicator."""
    st.title("🌍 COVID-19 Data Explorer")
    st.caption("Interactive epidemiology dashboard — powered by the disease.sh public API")

    if dataset.source == "cached":
        st.info(
            "📦 Showing a cached data snapshot (live API unreachable from this environment). "
            "In a normal deployment, this dashboard fetches live data from disease.sh automatically.",
            icon="ℹ️",
        )
    else:
        st.success("🟢 Showing live data from disease.sh", icon="🟢")


def render_global_kpis(dataset) -> None:
    """Render top-level global KPI cards."""
    countries = dataset.countries
    total_cases = int(countries["cases"].sum())
    total_deaths = int(countries["deaths"].sum())
    total_recovered = int(countries["recovered"].sum())
    total_active = int(countries["active"].sum())
    global_cfr = round(100 * total_deaths / total_cases, 2) if total_cases else 0.0

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Cases", f"{total_cases:,}")
    col2.metric("Total Deaths", f"{total_deaths:,}")
    col3.metric("Total Recovered", f"{total_recovered:,}")
    col4.metric("Active Cases", f"{total_active:,}")
    col5.metric("Global Fatality Rate", f"{global_cfr}%")


def render_overview_tab(dataset) -> None:
    """Overview tab: KPIs + top-10 countries by case fatality rate."""
    render_global_kpis(dataset)
    st.divider()

    st.subheader("Top 10 Countries by Case Fatality Rate")
    with_cfr = compute_case_fatality_rate(dataset.countries)
    top_cfr = with_cfr.sort_values("case_fatality_rate", ascending=False).head(10)
    st.dataframe(
        top_cfr[["country", "cases", "deaths", "case_fatality_rate"]],
        width="stretch",
        hide_index=True,
    )


def render_trends_tab(dataset) -> None:
    """Trends tab: rolling-average case/death charts for one country."""
    available_countries = list(dataset.historical.keys())
    selected_country = st.selectbox("Select a country", available_countries)

    historical = dataset.historical[selected_country]
    metric = st.radio("Metric", ["cases", "deaths"], horizontal=True)

    rolling_data = compute_rolling_average(historical, column=metric)
    st.plotly_chart(
        build_rolling_average_chart(rolling_data, label=metric.capitalize()),
        width="stretch",
    )


def render_comparison_tab(dataset) -> None:
    """Country comparison tab: bar chart + table for selected countries."""
    all_countries = sorted(dataset.countries["country"].unique())
    default_selection = [c for c in ["USA", "India", "Brazil", "Germany"] if c in all_countries]
    selected = st.multiselect("Compare countries", all_countries, default=default_selection)

    if not selected:
        st.warning("Select at least one country to compare.")
        return

    comparison = build_country_comparison_table(dataset.countries, selected)
    st.plotly_chart(build_country_comparison_chart(comparison), width="stretch")

    with st.expander("📋 View comparison table"):
        st.dataframe(comparison, width="stretch", hide_index=True)


def render_vaccination_tab(dataset) -> None:
    """Vaccination-impact tab: correlation scatter plot."""
    correlation_data = build_vaccination_correlation_table(
        dataset.countries, dataset.vaccination_totals
    )
    if correlation_data.empty:
        st.warning("No vaccination data available for the current dataset.")
        return

    st.plotly_chart(build_vaccination_correlation_chart(correlation_data), width="stretch")
    st.caption(
        "Each point is one country. The trendline shows the overall relationship between "
        "vaccination coverage and cases per million across this dataset — correlation, not "
        "causation; many confounding factors (testing rates, reporting practices, timing of "
        "waves) affect this relationship."
    )


def render_map_tab(dataset) -> None:
    """World map tab: choropleth colored by a selectable metric."""
    metric = st.selectbox(
        "Color by",
        ["casesPerOneMillion", "deathsPerOneMillion", "testsPerOneMillion"],
        format_func=lambda m: {
            "casesPerOneMillion": "Cases per Million",
            "deathsPerOneMillion": "Deaths per Million",
            "testsPerOneMillion": "Tests per Million",
        }[m],
    )
    st.plotly_chart(build_world_choropleth_map(dataset.countries, metric=metric), width="stretch")


def main() -> None:
    """Render the full dashboard."""
    try:
        dataset = _load_dataset()
    except CovidDataError as exc:
        st.error(f"❌ Could not load COVID data: {exc}")
        st.stop()

    render_header(dataset)

    tab_overview, tab_trends, tab_compare, tab_vaccination, tab_map = st.tabs(
        ["📊 Overview", "📈 Trends", "🌐 Compare Countries", "💉 Vaccination Impact", "🗺️ World Map"]
    )

    with tab_overview:
        render_overview_tab(dataset)
    with tab_trends:
        render_trends_tab(dataset)
    with tab_compare:
        render_comparison_tab(dataset)
    with tab_vaccination:
        render_vaccination_tab(dataset)
    with tab_map:
        render_map_tab(dataset)


if __name__ == "__main__":
    main()