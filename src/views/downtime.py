import plotly.express as px
import streamlit as st

from src.constants import THEME
from src.ui_utils import fmt, kpi


def render(df, dt_summary):
    downtime = df["DowntimeMinutes"].fillna(0)
    cols = st.columns(6)
    kpi(cols[0], "Rows", f"{len(df):,}")
    kpi(cols[1], "Non-zero Downtime", f"{(downtime > 0).sum():,}")
    kpi(cols[2], "Median Downtime", fmt(downtime.median()) or "—")
    kpi(cols[3], "Mean Downtime", fmt(downtime.mean()) or "—")
    kpi(cols[4], "Max Downtime", fmt(downtime.max()) or "—")
    kpi(cols[5], "P95 Downtime", fmt(downtime.quantile(0.95)) or "—")

    st.divider()
    nonzero = df[df["DowntimeMinutes"] > 0].copy()

    left, right = st.columns(2)
    with left:
        st.subheader("Downtime Distribution (non-zero only)")
        if not nonzero.empty:
            fig = px.histogram(nonzero, x="DowntimeHours", nbins=40, color_discrete_sequence=["#f38ba8"], labels={"DowntimeHours": "Downtime (h)"}, template=THEME)
            fig.update_layout(height=300, margin=dict(t=5, b=5))
            st.plotly_chart(fig, use_container_width=True)
    with right:
        st.subheader("Total Downtime by Machine")
        machine_dt = df.groupby("MachineName")["DowntimeHours"].sum().reset_index().sort_values("DowntimeHours")
        fig = px.bar(machine_dt, x="DowntimeHours", y="MachineName", orientation="h", color="DowntimeHours", color_continuous_scale="Reds", template=THEME)
        fig.update_layout(height=300, margin=dict(t=5, b=5))
        st.plotly_chart(fig, use_container_width=True)

    lower, upper = st.columns(2)
    with lower:
        st.subheader("Total Downtime by Part")
        part_dt = df.groupby("PartNumber")["DowntimeHours"].sum().reset_index().sort_values("DowntimeHours")
        fig = px.bar(part_dt, x="DowntimeHours", y="PartNumber", orientation="h", color="DowntimeHours", color_continuous_scale="Oranges", template=THEME)
        fig.update_layout(height=300, margin=dict(t=5, b=5))
        st.plotly_chart(fig, use_container_width=True)
    with upper:
        st.subheader("Downtime Box Plot by Operation")
        fig = px.box(df, x="OperationNumber", y="DowntimeHours", color="OperationNumber", template=THEME)
        fig.update_layout(height=300, margin=dict(t=5, b=5), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Downtime over Time")
    fig = px.scatter(df.dropna(subset=["StartDT"]), x="StartDT", y="DowntimeHours", color="MachineName", hover_data=["PartNumber", "SerialNumber", "OperationNumber"], template=THEME, height=340)
    fig.update_layout(margin=dict(t=5, b=5))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Top 20 Longest Downtime Events")
    display_cols = ["ID", "MachineName", "PartNumber", "OperationNumber", "SerialNumber", "Dt_disp", "Rt_disp", "StartDate", "StartTime"]
    if not df.empty:
        st.dataframe(df.nlargest(20, "DowntimeMinutes")[display_cols].rename(columns={"Dt_disp": "Downtime", "Rt_disp": "Runtime"}), use_container_width=True, hide_index=True)

    if not df["DowntimeMinutes"].dropna().empty and df["DowntimeMinutes"].max() > 0:
        worst = df.loc[df["DowntimeMinutes"].idxmax()]
        st.error(
            f"🔴 **Longest downtime:** {worst['Dt_disp']}  |  Machine: {worst['MachineName']}  "
            f"|  Part: {worst['PartNumber']}  |  Op: {worst['OperationNumber']}  "
            f"|  Serial: {worst['SerialNumber']}  |  Started: {worst['StartDate']} {worst['StartTime']}"
        )

    st.subheader("Downtime Summary Table – Part × Operation")
    st.dataframe(dt_summary, use_container_width=True, hide_index=True)
