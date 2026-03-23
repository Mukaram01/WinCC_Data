from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.constants import BENCHMARKS_PATH, THEME
from src.data import load_benchmark_csv, operation_choices, parse_user_time, prepare_benchmark_df, save_benchmarks


def render(df_full, bm_comparison, cmp_display, trim_mean_name, selected_trim_pct, session_state):
    st.subheader("Benchmark / Routing Time Comparison")
    st.caption(
        "**Source legend** — "
        f"*WinCC Median/Mean/{trim_mean_name}*: calculated from current filtered+cleaned WinCC data  |  "
        "*Operator Time*: manually entered current run data from the operator  |  "
        "*Prod. Time*: proposed target from Production Engineering"
    )
    st.caption(
        f"Persistence: benchmark edits are stored locally for this deployment in `{BENCHMARKS_PATH.relative_to(Path(__file__).resolve().parent.parent)}`. "
        "Anyone using the same app files will see the same saved benchmark rows."
    )

    with st.expander("➕ Add / Edit Benchmark Row", expanded=False):
        col1, col2, col3 = st.columns(3)
        bm_part = col1.selectbox("Part Number", [""] + sorted(df_full["PartNumber"].unique()), key="bm_part")
        bm_op = col2.selectbox("Operation", [""] + operation_choices(df_full["OperationNumber"]), key="bm_op")
        bm_family = col3.text_input("Family (optional)", key="bm_fam")
        col4, col5, col6 = st.columns(3)
        bm_op_t = col4.text_input("Operator Time", placeholder="e.g. 6:31", key="bm_opt")
        bm_pr_t = col5.text_input("Production Proposed Time", placeholder="e.g. 6:00", key="bm_prt")
        bm_notes = col6.text_input("Notes", key="bm_notes")
        if st.button("✅ Save Benchmark Row"):
            if bm_part and bm_op:
                current = session_state.benchmarks.copy()
                current = current[~((current["PartNumber"] == bm_part) & (current["OperationNumber"] == bm_op))]
                new_row = pd.DataFrame([{
                    "PartNumber": bm_part,
                    "OperationNumber": bm_op,
                    "Family": bm_family,
                    "OperatorTime_min": parse_user_time(bm_op_t),
                    "ProductionTime_min": parse_user_time(bm_pr_t),
                    "Notes": bm_notes,
                }])
                session_state.benchmarks = prepare_benchmark_df(pd.concat([current, new_row], ignore_index=True))
                save_benchmarks(session_state.benchmarks)
                st.success(f"Saved {bm_part} / Op {bm_op}. Changes are stored locally in {BENCHMARKS_PATH.name}.")
            else:
                st.warning("Select Part and Operation first.")

    with st.expander("📤 Upload Benchmark CSV", expanded=False):
        uploaded = st.file_uploader("Benchmark CSV", type="csv", key="bm_upload")
        if uploaded:
            benchmark_df, benchmark_error = load_benchmark_csv(uploaded.getvalue())
            if benchmark_error:
                st.error(benchmark_error)
            else:
                session_state.benchmarks = benchmark_df
                save_benchmarks(session_state.benchmarks)
                st.success(f"Loaded successfully and saved locally to {BENCHMARKS_PATH.name}.")

    st.subheader("Comparison Table")
    st.caption(f"Benchmark trim statistics reflect the current selection: {selected_trim_pct * 100:g}%.")
    if cmp_display.empty:
        st.info("No data available. Upload a file and ensure filters return results.")
    else:
        st.dataframe(cmp_display, use_container_width=True, hide_index=True)
        if not bm_comparison.empty and "WinCC_Median" in bm_comparison.columns:
            st.subheader("Comparison Chart")
            chart_data = bm_comparison.dropna(subset=["WinCC_Median"]).copy()
            chart_data["Label"] = chart_data["PartNumber"] + " / Op" + chart_data["OperationNumber"]
            fig = go.Figure()
            fig.add_trace(go.Bar(name="WinCC Median", x=chart_data["Label"], y=chart_data["WinCC_Median"] / 60, marker_color="#7c3aed"))
            fig.add_trace(go.Bar(name=f"WinCC {trim_mean_name}", x=chart_data["Label"], y=chart_data["WinCC_TrimMean"] / 60, marker_color="#89b4fa"))
            if chart_data.get("OperatorTime_min", pd.Series(dtype=float)).notna().any():
                fig.add_trace(go.Bar(name="Operator Time", x=chart_data["Label"], y=chart_data["OperatorTime_min"] / 60, marker_color="#a6e3a1"))
            if chart_data.get("ProductionTime_min", pd.Series(dtype=float)).notna().any():
                fig.add_trace(go.Bar(name="Production Proposed", x=chart_data["Label"], y=chart_data["ProductionTime_min"] / 60, marker_color="#fab387"))
            fig.update_layout(barmode="group", template=THEME, height=380, yaxis_title="Runtime (h)", xaxis_tickangle=-40, margin=dict(t=5, b=80))
            st.plotly_chart(fig, use_container_width=True)

    bm_cur = session_state.benchmarks
    if not bm_cur.empty:
        with st.expander("🗑 Delete a Benchmark Row"):
            labels = (bm_cur["PartNumber"] + " / Op" + bm_cur["OperationNumber"]).tolist()
            selected = st.selectbox("Row to delete", labels, key="bm_del")
            if st.button("Delete row"):
                part, op = selected.split(" / Op")
                session_state.benchmarks = bm_cur[~((bm_cur["PartNumber"] == part) & (bm_cur["OperationNumber"] == op))].reset_index(drop=True)
                save_benchmarks(session_state.benchmarks)
                st.success(f"Deleted {selected}. Changes are stored locally in {BENCHMARKS_PATH.name}.")
