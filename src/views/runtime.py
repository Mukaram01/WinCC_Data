import plotly.express as px
import streamlit as st

from src.analytics import stats_dict, trimmed_mean
from src.constants import THEME
from src.ui_utils import fmt, kpi


def render(df, rt_summary, selected_trim_pct, trimmed_mean_name):
    runtime = df["RuntimeMinutes"]
    if runtime.dropna().empty:
        st.warning("No runtime data for current filter selection.")
        return

    st.subheader("Runtime Statistics")
    summary = stats_dict(runtime, selected_trim_pct)
    cols = st.columns(4)
    for idx, (label, value) in enumerate(summary.items()):
        kpi(cols[idx % 4], label, str(int(value)) if label == "Count" else fmt(value))

    st.divider()
    left, right = st.columns(2)
    with left:
        st.subheader("Histogram")
        fig = px.histogram(df, x="RuntimeHours", nbins=50, color_discrete_sequence=["#7c3aed"], labels={"RuntimeHours": "Runtime (h)"}, template=THEME)
        fig.update_layout(height=300, margin=dict(t=5, b=5))
        st.plotly_chart(fig, use_container_width=True)
    with right:
        st.subheader("Box Plot by Part")
        fig = px.box(df, x="PartNumber", y="RuntimeHours", color="PartNumber", template=THEME)
        fig.update_layout(height=300, margin=dict(t=5, b=5), showlegend=False)
        fig.update_xaxes(tickangle=-40)
        st.plotly_chart(fig, use_container_width=True)

    lower, upper = st.columns(2)
    with lower:
        st.subheader("Box Plot by Operation")
        fig = px.box(df, x="OperationNumber", y="RuntimeHours", color="OperationNumber", template=THEME)
        fig.update_layout(height=300, margin=dict(t=5, b=5), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    with upper:
        st.subheader("Box Plot by Machine")
        fig = px.box(df, x="MachineName", y="RuntimeHours", color="MachineName", template=THEME)
        fig.update_layout(height=300, margin=dict(t=5, b=5), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Ranked Bar")
    stat_sel = st.selectbox("Statistic", ["Median", "Mean", trimmed_mean_name, "P95", "Max"], key="rt_stat")
    functions = {
        "Median": lambda x: x.median(),
        "Mean": lambda x: x.mean(),
        "Max": lambda x: x.max(),
        trimmed_mean_name: lambda x: trimmed_mean(x, selected_trim_pct),
        "P95": lambda x: x.quantile(0.95),
    }
    tmp = df.groupby(["PartNumber", "OperationNumber"])["RuntimeHours"].apply(functions[stat_sel]).reset_index()
    tmp.columns = ["PartNumber", "OperationNumber", "Value"]
    tmp["Label"] = tmp["PartNumber"] + " / Op" + tmp["OperationNumber"]
    fig = px.bar(tmp.sort_values("Value"), x="Value", y="Label", orientation="h", color="Value", color_continuous_scale="Purples", labels={"Value": f"{stat_sel} Runtime (h)", "Label": ""}, template=THEME)
    fig.update_layout(height=max(280, len(tmp) * 28), margin=dict(t=5, b=5))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Runtime over Time")
    fig = px.scatter(df.dropna(subset=["StartDT"]), x="StartDT", y="RuntimeHours", color="MachineName", hover_data=["PartNumber", "OperationNumber", "SerialNumber"], template=THEME, height=340)
    fig.update_layout(margin=dict(t=5, b=5))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Runtime Summary Table – Part × Operation")
    st.caption(f"{trimmed_mean_name} uses the current sidebar selection.")
    st.dataframe(rt_summary, use_container_width=True, hide_index=True)
