from datetime import datetime

import pandas as pd
import streamlit as st

from src.data import (
    load_persisted_benchmarks,
    load_persisted_families,
    operation_choices,
    prepare_benchmark_df,
)


def filter_defaults(df_full: pd.DataFrame) -> dict:
    valid_dates = df_full["StartDT"].dropna()
    today = datetime.today().date()
    min_date = valid_dates.min().date() if not valid_dates.empty else today
    max_date = valid_dates.max().date() if not valid_dates.empty else today
    return {
        "filter_from": min_date,
        "filter_to": max_date,
        "filter_machine": sorted(df_full["MachineName"].dropna().unique()),
        "filter_part": sorted(df_full["PartNumber"].dropna().unique()),
        "filter_operation": operation_choices(df_full["OperationNumber"]),
        "filter_serial": "",
        "filter_order": "",
        "filter_exclude_missing_runtime": True,
        "filter_exclude_zero_runtime": True,
        "filter_exclude_duplicates": False,
        "filter_outlier_mode": "Mild (IQR x3)",
    }


def ensure_filter_defaults(df_full: pd.DataFrame):
    defaults = filter_defaults(df_full)
    valid_sets = {
        "filter_machine": set(defaults["filter_machine"]),
        "filter_part": set(defaults["filter_part"]),
        "filter_operation": set(defaults["filter_operation"]),
    }
    for key, value in defaults.items():
        current = st.session_state.get(key)
        if key in valid_sets:
            if current is None:
                st.session_state[key] = value
                continue
            filtered = [item for item in current if item in valid_sets[key]]
            st.session_state[key] = filtered if filtered else value
        elif key in {"filter_from", "filter_to"}:
            if current is None or current < defaults["filter_from"] or current > defaults["filter_to"]:
                st.session_state[key] = value
        elif key not in st.session_state:
            st.session_state[key] = value


def reset_filters(df_full: pd.DataFrame):
    for key, value in filter_defaults(df_full).items():
        st.session_state[key] = value


def _init():
    if "benchmarks" not in st.session_state:
        st.session_state.benchmarks = load_persisted_benchmarks()
    else:
        st.session_state.benchmarks = prepare_benchmark_df(st.session_state.benchmarks)

    if "families" not in st.session_state:
        st.session_state.families = load_persisted_families()
    elif not isinstance(st.session_state.families, dict):
        st.session_state.families = load_persisted_families()
