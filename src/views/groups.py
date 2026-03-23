from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from src.constants import FAMILIES_PATH, THEME
from src.data import save_families
from src.ui_utils import fmt


def render(df, df_full, session_state):
    st.subheader("Part Family / Group Analysis")
    st.caption(
        f"Persistence: family definitions are stored locally for this deployment in `{FAMILIES_PATH.relative_to(Path(__file__).resolve().parent.parent)}` as JSON. "
        "Anyone using the same app files will see the same family mappings."
    )

    with st.expander("✏️ Define Part Families", expanded=True):
        col1, col2, col3 = st.columns([2, 4, 2])
        fam_name = col1.text_input("Family Name", key="fam_name")
        fam_parts = col2.multiselect("Parts", sorted(df_full["PartNumber"].unique()), key="fam_parts")
        if col3.button("💾 Save Family"):
            if fam_name and fam_parts:
                clean_name = fam_name.strip()
                session_state.families[clean_name] = sorted(set(fam_parts))
                save_families(session_state.families)
                st.success(f"'{clean_name}' saved to {FAMILIES_PATH.name}.")
        if session_state.families:
            fam_tbl = pd.DataFrame([{"Family": name, "Parts": ", ".join(parts)} for name, parts in session_state.families.items()])
            st.dataframe(fam_tbl, use_container_width=True, hide_index=True)
            delete_key = st.selectbox("Delete family", [""] + list(session_state.families.keys()), key="del_f")
            if st.button("🗑 Delete Family") and delete_key:
                del session_state.families[delete_key]
                save_families(session_state.families)
                st.success(f"Deleted '{delete_key}' from {FAMILIES_PATH.name}.")

    if not session_state.families:
        st.info("💡 Define a family above to see group analytics.")
        return

    part_to_family = {part: family for family, parts in session_state.families.items() for part in parts}
    grouped_df = df.copy()
    grouped_df["Family"] = grouped_df["PartNumber"].map(part_to_family).fillna("Unassigned")

    left, right = st.columns(2)
    with left:
        st.subheader("Runtime by Family")
        fig = px.box(grouped_df, x="Family", y="RuntimeHours", color="Family", template=THEME)
        fig.update_layout(height=320, showlegend=False, margin=dict(t=5, b=5))
        st.plotly_chart(fig, use_container_width=True)
    with right:
        st.subheader("Median Runtime – Family × Operation")
        summary = grouped_df.groupby(["Family", "OperationNumber"])["RuntimeHours"].median().reset_index()
        fig = px.bar(summary, x="RuntimeHours", y="Family", color="OperationNumber", orientation="h", barmode="group", template=THEME, labels={"RuntimeHours": "Median (h)"})
        fig.update_layout(height=320, margin=dict(t=5, b=5))
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Family Summary Table")
    summary = grouped_df.groupby(["Family", "OperationNumber"])["RuntimeMinutes"].agg(Count="count", Median="median", Mean="mean", Min="min", Max="max").reset_index()
    for col in ["Median", "Mean", "Min", "Max"]:
        summary[col] = summary[col].apply(fmt)
    st.dataframe(summary, use_container_width=True, hide_index=True)
