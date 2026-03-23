import pandas as pd
import plotly.express as px
import streamlit as st

from src.analytics import build_period_row, slice_period
from src.constants import THEME
from src.ui_utils import fmt


def render(df_full, selected_trim_pct, trim_mean_name):
    st.subheader("Period-over-Period Comparison")
    valid_dates = df_full["StartDT"].dropna()
    if valid_dates.empty:
        st.warning("No valid start dates in the dataset.")
        return

    min_date, max_date = valid_dates.min().date(), valid_dates.max().date()
    mid_date = min_date + (max_date - min_date) // 2

    left, right = st.columns(2)
    with left:
        st.markdown("**Period A**")
        period_a_from = st.date_input("From", value=min_date, key="pa_f", min_value=min_date, max_value=max_date)
        period_a_to = st.date_input("To", value=mid_date, key="pa_t", min_value=min_date, max_value=max_date)
    with right:
        st.markdown("**Period B**")
        period_b_from = st.date_input("From", value=mid_date, key="pb_f", min_value=min_date, max_value=max_date)
        period_b_to = st.date_input("To", value=max_date, key="pb_t", min_value=min_date, max_value=max_date)

    dfa = slice_period(df_full, period_a_from, period_a_to)
    dfb = slice_period(df_full, period_b_from, period_b_to)

    cmp_tbl = pd.DataFrame([
        build_period_row(dfa, f"A  ({period_a_from} → {period_a_to})", trim_mean_name, selected_trim_pct),
        build_period_row(dfb, f"B  ({period_b_from} → {period_b_to})", trim_mean_name, selected_trim_pct),
    ]).set_index("Period").T
    st.caption(f"Period comparison trim statistics use {selected_trim_pct * 100:g}% trimming.")
    st.dataframe(cmp_tbl, use_container_width=True)

    if dfa.empty or dfb.empty:
        return

    median_a = dfa["RuntimeMinutes"].median()
    median_b = dfb["RuntimeMinutes"].median()
    delta = median_b - median_a
    pct_delta = delta / median_a * 100 if median_a else 0
    st.metric("Median Runtime  A → B", fmt(median_b), delta=f"{'+' if delta >= 0 else ''}{fmt(abs(delta))} ({pct_delta:+.1f}%)")

    dfa_chart = dfa.copy(); dfa_chart["Period"] = "A"
    dfb_chart = dfb.copy(); dfb_chart["Period"] = "B"
    combined = pd.concat([dfa_chart, dfb_chart])
    grouped = combined.groupby(["PartNumber", "Period"])["RuntimeHours"].median().reset_index()
    fig = px.bar(grouped, x="PartNumber", y="RuntimeHours", color="Period", barmode="group", template=THEME, labels={"RuntimeHours": "Median Runtime (h)"}, height=360)
    fig.update_xaxes(tickangle=-40)
    fig.update_layout(margin=dict(t=5, b=80))
    st.plotly_chart(fig, use_container_width=True)

    period_a_group = dfa.groupby(["PartNumber", "OperationNumber"])["RuntimeMinutes"].median()
    period_b_group = dfb.groupby(["PartNumber", "OperationNumber"])["RuntimeMinutes"].median()
    change = pd.DataFrame({"Period A": period_a_group, "Period B": period_b_group}).reset_index()
    change["Δ"] = change["Period B"] - change["Period A"]
    change["Δ %"] = (change["Δ"] / change["Period A"] * 100).round(1)
    for col in ["Period A", "Period B", "Δ"]:
        change[col] = change[col].apply(lambda x: fmt(x) if pd.notna(x) else "—")
    change["Δ %"] = change["Δ %"].apply(lambda x: f"{x:+.1f}%" if pd.notna(x) else "—")
    st.subheader("Median Runtime Change – Part × Operation")
    st.dataframe(change, use_container_width=True, hide_index=True)
