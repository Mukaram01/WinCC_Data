import numpy as np
import pandas as pd
import streamlit as st

from src.constants import BENCHMARK_COLUMNS
from src.data import apply_outliers, build_export_frames
from src.ui_utils import fmt, records_to_df


def trimmed_mean(series: pd.Series, pct: float = 0.10) -> float:
    values = series.dropna().sort_values().values
    n = len(values)
    if n == 0:
        return np.nan
    k = int(np.floor(n * pct))
    if k * 2 >= n:
        return float(np.median(values))
    return float(values[k : n - k].mean())


def trim_pct_label(pct: float) -> str:
    return f"{pct * 100:g}%"


def trimmed_mean_label(pct: float, short: bool = False) -> str:
    prefix = "Trim Mean" if short else "Trimmed Mean"
    return f"{prefix} ({trim_pct_label(pct)})"


def stats_dict(series: pd.Series, trim_pct: float) -> dict:
    cleaned = series.dropna()
    if cleaned.empty:
        return {}
    q1, q3 = cleaned.quantile(0.25), cleaned.quantile(0.75)
    return {
        "Count": int(len(cleaned)),
        "Mean": cleaned.mean(),
        trimmed_mean_label(trim_pct): trimmed_mean(cleaned, trim_pct),
        "Median": cleaned.median(),
        "Std Dev": cleaned.std(),
        "IQR": q3 - q1,
        "Min": cleaned.min(),
        "P5": cleaned.quantile(0.05),
        "P25": q1,
        "P75": q3,
        "P95": cleaned.quantile(0.95),
        "Max": cleaned.max(),
    }


@st.cache_data(show_spinner=False)
def _rt_summary(src: pd.DataFrame, trim_pct: float) -> pd.DataFrame:
    if src.empty:
        return pd.DataFrame()
    grouped = src.groupby(["PartNumber", "OperationNumber"])
    base = grouped["RuntimeMinutes"].agg(
        Count="count", Median="median", Mean="mean", Std="std", Min="min", Max="max"
    ).reset_index()
    trim_mean = grouped["RuntimeMinutes"].apply(lambda s: trimmed_mean(s, trim_pct)).reset_index(name="TrimMean")
    p95 = grouped["RuntimeMinutes"].quantile(0.95).reset_index(name="P95")
    return base.merge(trim_mean, on=["PartNumber", "OperationNumber"]).merge(p95, on=["PartNumber", "OperationNumber"])


@st.cache_data(show_spinner=False)
def _dt_summary(src: pd.DataFrame) -> pd.DataFrame:
    if src.empty:
        return pd.DataFrame()
    return src.groupby(["PartNumber", "OperationNumber"])["DowntimeMinutes"].agg(
        Count="count", Median="median", Mean="mean", Max="max"
    ).reset_index()


@st.cache_data(show_spinner=False)
def machine_summary(src: pd.DataFrame) -> pd.DataFrame:
    if src.empty:
        return pd.DataFrame()
    return src.groupby("MachineName").agg(
        Rows=("ID", "count"),
        MedianRuntime=("RuntimeMinutes", "median"),
        TotalDowntimeMin=("DowntimeMinutes", "sum"),
    ).reset_index()


@st.cache_data(show_spinner=False)
def build_benchmark_comparison(src: pd.DataFrame, benchmark_records: tuple[tuple[object, ...], ...], trim_pct: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    wincc_agg = pd.DataFrame()
    bm_comparison = pd.DataFrame()
    if src.empty:
        return wincc_agg, bm_comparison

    grouped = src.groupby(["PartNumber", "OperationNumber"])
    wincc_agg = grouped["RuntimeMinutes"].agg(
        WinCC_Count="count", WinCC_Median="median", WinCC_Mean="mean"
    ).reset_index()
    trim_mean = grouped["RuntimeMinutes"].apply(lambda s: trimmed_mean(s, trim_pct)).reset_index(name="WinCC_TrimMean")
    wincc_agg = wincc_agg.merge(trim_mean, on=["PartNumber", "OperationNumber"])

    benchmark_df = records_to_df(BENCHMARK_COLUMNS, benchmark_records)
    if benchmark_df.empty:
        bm_comparison = wincc_agg.copy()
        for col in ["OperatorTime_min", "ProductionTime_min", "Family", "Notes"]:
            bm_comparison[col] = np.nan
    else:
        bm_comparison = wincc_agg.merge(
            benchmark_df[["PartNumber", "OperationNumber", "Family", "OperatorTime_min", "ProductionTime_min", "Notes"]],
            on=["PartNumber", "OperationNumber"],
            how="outer",
        )
    return wincc_agg, bm_comparison


@st.cache_data(show_spinner=False)
def build_cmp_display(cmp: pd.DataFrame, trim_label: str) -> pd.DataFrame:
    if cmp.empty:
        return pd.DataFrame()
    rows = []
    for _, row in cmp.iterrows():
        median = row.get("WinCC_Median")
        operator_time = row.get("OperatorTime_min")
        production_time = row.get("ProductionTime_min")
        display_row = {
            "Part": row.get("PartNumber", ""),
            "Op": row.get("OperationNumber", ""),
            "Count": int(row["WinCC_Count"]) if pd.notna(row.get("WinCC_Count")) else "",
            "WinCC Median": fmt(median),
            "WinCC Mean": fmt(row.get("WinCC_Mean")),
            trim_label: fmt(row.get("WinCC_TrimMean")),
            "Operator Time": fmt(operator_time),
            "Prod. Time": fmt(production_time),
        }
        if pd.notna(median) and pd.notna(operator_time) and float(operator_time) != 0:
            delta = float(median) - float(operator_time)
            display_row["Δ vs Operator"] = fmt(abs(delta)) + (" ↑" if delta > 0 else " ↓")
            display_row["% vs Operator"] = f"{delta / float(operator_time) * 100:+.1f}%"
        else:
            display_row["Δ vs Operator"] = "—"
            display_row["% vs Operator"] = "—"
        if pd.notna(median) and pd.notna(production_time) and float(production_time) != 0:
            delta = float(median) - float(production_time)
            display_row["Δ vs Prod."] = fmt(abs(delta)) + (" ↑" if delta > 0 else " ↓")
        else:
            display_row["Δ vs Prod."] = "—"
        rows.append(display_row)
    return pd.DataFrame(rows)


def slice_period(df_full: pd.DataFrame, start_date, end_date) -> pd.DataFrame:
    return df_full[
        (df_full["StartDT"].dt.date >= start_date)
        & (df_full["StartDT"].dt.date <= end_date)
        & df_full["RuntimeMinutes"].notna()
        & (df_full["RuntimeMinutes"] > 0)
    ]


def build_period_row(df_period: pd.DataFrame, label: str, trim_label: str, trim_pct: float) -> dict:
    runtime = df_period["RuntimeMinutes"]
    downtime = df_period["DowntimeMinutes"].fillna(0)
    return {
        "Period": label,
        "Rows": len(df_period),
        "Unique Parts": df_period["PartNumber"].nunique(),
        "Median Runtime": fmt(runtime.median()),
        "Mean Runtime": fmt(runtime.mean()),
        trim_label: fmt(trimmed_mean(runtime, trim_pct)),
        "P95 Runtime": fmt(runtime.quantile(0.95)) if len(runtime) else "—",
        "Std Dev": fmt(runtime.std()),
        "Median Downtime": fmt(downtime.median()),
        "Max Downtime": fmt(downtime.max()),
    }


@st.cache_data(show_spinner=False)
def build_cached_views(
    df_full: pd.DataFrame,
    date_from_iso: str,
    date_to_iso: str,
    machines: tuple[str, ...],
    parts: tuple[str, ...],
    operations: tuple[str, ...],
    serial_filter: str,
    order_filter: str,
    exclude_missing_runtime: bool,
    exclude_zero_runtime: bool,
    exclude_duplicates: bool,
    outlier_mode: str,
    outlier_trim_pct: float | None,
    min_runtime: float | None,
    max_runtime: float | None,
    benchmark_records: tuple[tuple[object, ...], ...],
    trim_pct: float,
    trim_label: str,
) -> dict[str, pd.DataFrame | dict]:
    df = df_full.copy()
    date_from = pd.to_datetime(date_from_iso).date()
    date_to = pd.to_datetime(date_to_iso).date()
    df = df[(df["StartDT"].dt.date >= date_from) & (df["StartDT"].dt.date <= date_to)]
    if machines:
        df = df[df["MachineName"].isin(machines)]
    if parts:
        df = df[df["PartNumber"].isin(parts)]
    if operations:
        df = df[df["OperationNumber"].isin(operations)]
    if serial_filter:
        df = df[df["SerialNumber"].str.contains(serial_filter, na=False, case=False)]
    if order_filter:
        df = df[df["OrderNumber"].str.contains(order_filter, na=False, case=False)]
    if exclude_missing_runtime:
        df = df[df["RuntimeMinutes"].notna()]
    if exclude_zero_runtime:
        df = df[df["RuntimeMinutes"] != 0]
    if exclude_duplicates:
        df = df[~df["_dup"]]

    df, df_excl, out_info = apply_outliers(
        df,
        "RuntimeMinutes",
        outlier_mode,
        min_value=min_runtime,
        max_value=max_runtime,
        trim_pct=outlier_trim_pct,
    )
    df_export, df_excl_export = build_export_frames(df, df_excl)

    rt_summary = _rt_summary(df, trim_pct)
    if not rt_summary.empty:
        for col in ["Median", "Mean", "TrimMean", "Std", "Min", "Max", "P95"]:
            rt_summary[col] = rt_summary[col].apply(fmt)
        rt_summary = rt_summary.rename(columns={"TrimMean": trim_label})

    dt_summary = _dt_summary(df)
    if not dt_summary.empty:
        for col in ["Median", "Mean", "Max"]:
            dt_summary[col] = dt_summary[col].apply(fmt)

    mach_summary = machine_summary(df)
    if not mach_summary.empty:
        mach_summary["Median Runtime"] = mach_summary["MedianRuntime"].apply(fmt)
        mach_summary["Total Downtime"] = mach_summary["TotalDowntimeMin"].apply(fmt)
        mach_summary = mach_summary.drop(columns=["MedianRuntime", "TotalDowntimeMin"])

    wincc_agg, bm_comparison = build_benchmark_comparison(df, benchmark_records, trim_pct)
    cmp_display = build_cmp_display(bm_comparison, trim_label)

    return {
        "df": df,
        "df_excl": df_excl,
        "out_info": out_info,
        "df_export": df_export,
        "df_excl_exp": df_excl_export,
        "rt_summary": rt_summary,
        "dt_summary": dt_summary,
        "mach_summary": mach_summary,
        "wincc_agg": wincc_agg,
        "bm_comparison": bm_comparison,
        "cmp_display": cmp_display,
    }
