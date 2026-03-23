import pandas as pd
import plotly.express as px
import streamlit as st

from src.constants import DISP_COLS, THEME
from src.ui_utils import fmt, kpi


def render(df, df_excl, df_full, out_info, quality):
    st.subheader("Data Quality Report  (full dataset, pre-filter)")
    cols1 = st.columns(4)
    kpi(cols1[0], "Total Rows", f"{quality['total']:,}")
    kpi(cols1[1], "Invalid Runtime", f"{quality['bad_rt']:,}")
    kpi(cols1[2], "Zero Runtime", f"{quality['zero_rt']:,}")
    kpi(cols1[3], "Duplicate Rows", f"{quality['dup']:,}")

    cols2 = st.columns(4)
    kpi(cols2[0], "Invalid Start DT", f"{quality['bad_start']:,}")
    kpi(cols2[1], "Invalid Downtime", f"{quality['bad_dt']:,}")
    kpi(cols2[2], "Rows after filters", f"{len(df):,}")
    kpi(cols2[3], "Outliers removed", f"{out_info.get('removed', 0):,}")

    missing = pd.DataFrame({"Column": list(quality["missing_by_col"].keys()), "Missing": list(quality["missing_by_col"].values())})
    fig = px.bar(missing, x="Column", y="Missing", color="Missing", color_continuous_scale="Reds", template=THEME, height=260)
    fig.update_layout(margin=dict(t=5, b=5))
    st.plotly_chart(fig, use_container_width=True)

    suspicious = df_full[df_full["RuntimeMinutes"] > 24 * 60][["ID", "MachineName", "PartNumber", "OperationNumber", "SerialNumber", "Rt_disp", "StartDate"]].rename(columns={"Rt_disp": "Runtime"})
    if suspicious.empty:
        st.success("✅ No runtimes > 24 h detected.")
    else:
        st.warning(f"⚠️  {len(suspicious)} row(s) with runtime > 24 h — review before analysis.")
        st.dataframe(suspicious, use_container_width=True, hide_index=True)

    if out_info and not df_excl.empty:
        source_label = "Preset rule" if out_info["source"] == "preset" else "Manual bounds"
        trim_text = (
            f" | Trim: {out_info['trim_pct'] * 100:.1f}%"
            if out_info.get("trim_pct") is not None and out_info.get("trim_pct") > 0
            else ""
        )
        st.subheader(f"Excluded Outliers ({out_info['mode']})  — {out_info['removed']} rows")
        st.info(
            f"Source: {source_label} ({out_info['detail']}) | "
            f"Threshold: {fmt(out_info['lo'])} – {fmt(out_info['hi'])}{trim_text} | "
            f"Q1={fmt(out_info['q1'])}  Q3={fmt(out_info['q3'])}  IQR={fmt(out_info['iqr'])}"
        )
        st.dataframe(df_excl[DISP_COLS].rename(columns={"Rt_disp": "Runtime"}), use_container_width=True, hide_index=True)

    st.subheader("Cleaned Data Preview  (filtered)")
    st.dataframe(df[["ID", "MachineName", "OrderNumber", "SerialNumber", "OperationNumber", "PartNumber", "Rt_disp", "Dt_disp", "StartDate", "StartTime"]].rename(columns={"Rt_disp": "Runtime", "Dt_disp": "Downtime"}), use_container_width=True, hide_index=True)
