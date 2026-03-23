import plotly.express as px
import streamlit as st

from src.analytics import trimmed_mean
from src.constants import DISP_COLS, THEME
from src.ui_utils import fmt, kpi


def render(df, out_info, selected_trim_pct, trim_mean_name):
    count = len(df)
    runtime = df["RuntimeMinutes"]
    downtime = df["DowntimeMinutes"]

    st.subheader("Key Performance Indicators")
    row1 = st.columns(6)
    kpi(row1[0], "Rows (filtered)", f"{count:,}")
    kpi(row1[1], "Unique Parts", f"{df['PartNumber'].nunique()}")
    kpi(row1[2], "Unique Serials", f"{df['SerialNumber'].nunique()}")
    kpi(row1[3], "Unique Machines", f"{df['MachineName'].nunique()}")
    kpi(row1[4], "Median Runtime", fmt(runtime.median()) or "—")
    kpi(row1[5], "Median Downtime", fmt(downtime.median()) or "—")

    row2 = st.columns(6)
    kpi(row2[0], "Mean Runtime", fmt(runtime.mean()) or "—")
    kpi(row2[1], trim_mean_name, fmt(trimmed_mean(runtime, selected_trim_pct)) or "—")
    kpi(row2[2], "P95 Runtime", fmt(runtime.quantile(0.95)) if count else "—")
    kpi(row2[3], "Max Runtime", fmt(runtime.max()) or "—")
    kpi(row2[4], "Max Downtime", fmt(downtime.max()) or "—")
    kpi(row2[5], "Std Dev Runtime", fmt(runtime.std()) or "—")

    if out_info:
        source_label = "preset rule" if out_info["source"] == "preset" else "manual bounds"
        trim_text = (
            f" | Trim: {out_info['trim_pct'] * 100:.1f}%"
            if out_info.get("trim_pct") is not None and out_info.get("trim_pct") > 0
            else ""
        )
        st.info(
            f"🔎 **Outlier removal** ({out_info['mode']}): **{out_info['removed']}** rows removed | "
            f"Source: {source_label} ({out_info['detail']}) | "
            f"Threshold: {fmt(out_info['lo'])} – {fmt(out_info['hi'])}{trim_text} | "
            f"Kept: {out_info['kept']} rows"
        )

    st.divider()
    left, right = st.columns(2)
    with left:
        st.subheader("Runtime Distribution")
        if not runtime.dropna().empty:
            fig = px.histogram(df, x="RuntimeHours", nbins=40, color_discrete_sequence=["#7c3aed"], labels={"RuntimeHours": "Runtime (h)"}, template=THEME)
            fig.update_layout(height=300, margin=dict(t=5, b=10))
            st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("Median Runtime – Part × Operation")
        if not df.empty:
            tmp = df.groupby(["PartNumber", "OperationNumber"])["RuntimeHours"].median().reset_index()
            tmp["Label"] = tmp["PartNumber"] + " / Op" + tmp["OperationNumber"]
            fig = px.bar(tmp.sort_values("RuntimeHours"), x="RuntimeHours", y="Label", orientation="h", color="RuntimeHours", color_continuous_scale="Purples", labels={"RuntimeHours": "Median (h)", "Label": ""}, template=THEME)
            fig.update_layout(height=300, margin=dict(t=5, b=10), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("Runtime over Time")
    if not df.dropna(subset=["StartDT"]).empty:
        fig = px.scatter(df.dropna(subset=["StartDT"]), x="StartDT", y="RuntimeHours", color="PartNumber", hover_data=["MachineName", "SerialNumber", "OperationNumber"], labels={"RuntimeHours": "Runtime (h)", "StartDT": "Start"}, template=THEME, height=340)
        fig.update_layout(margin=dict(t=5, b=10))
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Top 10 Longest Runtime Events")
    if not df.empty:
        st.dataframe(df.nlargest(10, "RuntimeMinutes")[DISP_COLS].rename(columns={"Rt_disp": "Runtime"}), use_container_width=True, hide_index=True)
