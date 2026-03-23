import io

import numpy as np
import pandas as pd
import streamlit as st


def fmt(minutes) -> str:
    if minutes is None or (isinstance(minutes, float) and np.isnan(minutes)):
        return ""
    value = int(round(float(minutes)))
    return f"{value // 60:02d}:{value % 60:02d}"


def kpi(col, label: str, value: str, delta=None):
    with col:
        st.metric(label, value, delta=delta)


def df_to_records(df: pd.DataFrame) -> tuple[tuple[object, ...], ...]:
    if df is None or df.empty:
        return tuple()
    cleaned = df.where(pd.notna(df), None)
    return tuple(tuple(row) for row in cleaned.itertuples(index=False, name=None))


def records_to_df(columns: list[str], records: tuple[tuple[object, ...], ...]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(list(records), columns=columns)


@st.cache_data(show_spinner=False)
def to_excel(sheet_payload: tuple[tuple[str, tuple[str, ...], tuple[tuple[object, ...], ...]], ...]) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for name, columns, records in sheet_payload:
            if not records:
                continue
            pd.DataFrame(list(records), columns=list(columns)).to_excel(
                writer,
                sheet_name=name[:31],
                index=False,
            )
    return buf.getvalue()
