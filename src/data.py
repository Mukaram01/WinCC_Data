import io
import json
import re

import numpy as np
import pandas as pd
import streamlit as st

from src.constants import (
    BENCHMARK_COLUMNS,
    BENCHMARK_OPTIONAL,
    BENCHMARK_REQUIRED,
    BENCHMARKS_PATH,
    DATA_DIR,
    ECOLS,
    FAMILIES_PATH,
    REQUIRED,
)
from src.ui_utils import fmt


def parse_hhmm(val) -> float | None:
    if pd.isna(val):
        return None
    match = re.match(r"^(\d+):(\d{2})$", str(val).strip())
    if match:
        hours, minutes = int(match.group(1)), int(match.group(2))
        if minutes < 60:
            return float(hours * 60 + minutes)
    return None


def parse_user_time(val) -> float | None:
    if not val or str(val).strip() == "":
        return None
    text = str(val).strip()
    match = re.match(r"^(\d+):(\d{2})$", text)
    if match:
        return int(match.group(1)) * 60 + int(match.group(2))
    match = re.match(r"^(\d+)\s*h\s*(\d+)\s*m?$", text, re.I)
    if match:
        return int(match.group(1)) * 60 + int(match.group(2))
    try:
        value = float(text)
        return value if value > 24 else value * 60
    except ValueError:
        return None


def operation_choices(values) -> list[str]:
    cleaned = []
    for val in values:
        if pd.isna(val):
            continue
        text = str(val).strip()
        if text:
            cleaned.append(text)

    def sort_key(value: str):
        try:
            return (0, int(float(value)), value)
        except (TypeError, ValueError):
            return (1, value)

    return sorted(set(cleaned), key=sort_key)


def normalize_operation_number(series: pd.Series) -> pd.Series:
    out = series.astype("string").str.strip()
    out = out.replace({"": pd.NA, "<NA>": pd.NA, "nan": pd.NA, "None": pd.NA})
    return out.str.zfill(4)


def clean_text_value(value):
    if value is None or pd.isna(value):
        return pd.NA
    text = str(value).strip()
    return text if text else pd.NA


def prepare_benchmark_df(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=BENCHMARK_COLUMNS)

    prepared = df.copy()
    for col in BENCHMARK_COLUMNS:
        if col not in prepared.columns:
            prepared[col] = pd.NA

    prepared["PartNumber"] = prepared["PartNumber"].astype("string").str.strip()
    prepared["OperationNumber"] = normalize_operation_number(prepared["OperationNumber"])
    prepared["Family"] = prepared["Family"].apply(clean_text_value)
    prepared["Notes"] = prepared["Notes"].apply(clean_text_value)

    for col in ["OperatorTime_min", "ProductionTime_min"]:
        prepared[col] = pd.to_numeric(prepared[col], errors="coerce")

    prepared = prepared.dropna(subset=["PartNumber", "OperationNumber"])
    prepared = prepared.drop_duplicates(subset=["PartNumber", "OperationNumber"], keep="last")
    return prepared[BENCHMARK_COLUMNS].reset_index(drop=True)


def load_persisted_benchmarks() -> pd.DataFrame:
    if not BENCHMARKS_PATH.exists():
        return pd.DataFrame(columns=BENCHMARK_COLUMNS)
    try:
        raw = pd.read_csv(BENCHMARKS_PATH, dtype=str)
    except Exception as exc:
        st.warning(f"Could not load persisted benchmarks from {BENCHMARKS_PATH.name}: {exc}")
        return pd.DataFrame(columns=BENCHMARK_COLUMNS)
    return prepare_benchmark_df(raw)


def save_benchmarks(df: pd.DataFrame) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    persisted = prepare_benchmark_df(df).copy()
    for col in ["Family", "Notes"]:
        persisted[col] = persisted[col].fillna("")
    persisted.to_csv(BENCHMARKS_PATH, index=False)


def load_persisted_families() -> dict[str, list[str]]:
    if not FAMILIES_PATH.exists():
        return {}
    try:
        raw = json.loads(FAMILIES_PATH.read_text())
    except Exception as exc:
        st.warning(f"Could not load persisted families from {FAMILIES_PATH.name}: {exc}")
        return {}

    if not isinstance(raw, dict):
        st.warning(f"Ignoring invalid families data in {FAMILIES_PATH.name}; expected a JSON object.")
        return {}

    families: dict[str, list[str]] = {}
    for family_name, parts in raw.items():
        clean_name = str(family_name).strip()
        if not clean_name or not isinstance(parts, list):
            continue
        clean_parts = []
        seen = set()
        for part in parts:
            part_text = str(part).strip()
            if part_text and part_text not in seen:
                clean_parts.append(part_text)
                seen.add(part_text)
        families[clean_name] = clean_parts
    return families


def save_families(families: dict[str, list[str]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    clean_families = {
        str(name).strip(): sorted({str(part).strip() for part in parts if str(part).strip()})
        for name, parts in families.items()
        if str(name).strip()
    }
    FAMILIES_PATH.write_text(json.dumps(clean_families, indent=2, sort_keys=True))


@st.cache_data(show_spinner=False)
def load_benchmark_csv(data: bytes) -> tuple[pd.DataFrame | None, str | None]:
    try:
        raw = pd.read_csv(io.BytesIO(data), encoding="utf-8-sig", dtype=str)
    except Exception as exc:
        return None, f"Could not read benchmark CSV: {exc}"

    raw.columns = [c.strip() for c in raw.columns]
    missing = [c for c in BENCHMARK_REQUIRED if c not in raw.columns]
    if missing:
        recognized = ", ".join(BENCHMARK_REQUIRED + BENCHMARK_OPTIONAL)
        return None, (
            "Benchmark CSV is missing required columns: "
            f"{', '.join(missing)}. Recognized columns: {recognized}."
        )

    df = raw.copy()
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].str.strip()

    invalid = []
    for col in BENCHMARK_REQUIRED:
        if df[col].isna().all() or (df[col] == "").all():
            invalid.append(f"{col} has no usable values")
    if invalid:
        return None, "Benchmark CSV has invalid required data: " + "; ".join(invalid) + "."

    df["PartNumber"] = df["PartNumber"].astype("string").str.strip()
    df["OperationNumber"] = normalize_operation_number(df["OperationNumber"])

    if df["PartNumber"].isna().any() or df["OperationNumber"].isna().any():
        bad_rows = sorted(df.index[df["PartNumber"].isna() | df["OperationNumber"].isna()].tolist())
        preview = ", ".join(str(i + 2) for i in bad_rows[:5])
        suffix = "..." if len(bad_rows) > 5 else ""
        return None, (
            "Benchmark CSV has blank or invalid PartNumber/OperationNumber values "
            f"in row(s): {preview}{suffix}."
        )

    for source_col, target_col in {
        "OperatorTime_HHMM": "OperatorTime_min",
        "ProductionTime_HHMM": "ProductionTime_min",
    }.items():
        if source_col not in df.columns:
            continue
        parsed = df[source_col].apply(parse_user_time)
        nonblank = df[source_col].notna() & (df[source_col] != "")
        invalid_rows = df.index[nonblank & parsed.isna()].tolist()
        if invalid_rows:
            preview = ", ".join(str(i + 2) for i in invalid_rows[:5])
            suffix = "..." if len(invalid_rows) > 5 else ""
            return None, f"Benchmark CSV has invalid time values: {source_col} has invalid values in row(s): {preview}{suffix}."
        df[target_col] = parsed

    for col in ["OperatorTime_min", "ProductionTime_min"]:
        df[col] = pd.to_numeric(df[col], errors="coerce") if col in df.columns else np.nan

    for col in ["Family", "Notes"]:
        if col not in df.columns:
            df[col] = pd.NA

    return prepare_benchmark_df(df), None


@st.cache_data(show_spinner=False)
def load_csv(data: bytes):
    try:
        raw = pd.read_csv(io.BytesIO(data), sep=";", encoding="utf-8-sig", dtype=str)
    except Exception as exc:
        return None, None, {"error": str(exc)}

    raw.columns = [c.strip() for c in raw.columns]
    missing = [c for c in REQUIRED if c not in raw.columns]
    if missing:
        return None, None, {"error": f"Missing columns: {missing}"}

    df = raw.copy()
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].str.strip()

    df["ID"] = pd.to_numeric(df["ID"], errors="coerce")
    df["OperationNumber"] = normalize_operation_number(df["OperationNumber"])
    df["RuntimeMinutes"] = df["RuntimeHHMM"].apply(parse_hhmm)
    df["DowntimeMinutes"] = df["DowntimeHHMM"].apply(parse_hhmm)
    df["RuntimeHours"] = df["RuntimeMinutes"] / 60
    df["DowntimeHours"] = df["DowntimeMinutes"] / 60
    df["Rt_disp"] = df["RuntimeMinutes"].apply(fmt)
    df["Dt_disp"] = df["DowntimeMinutes"].apply(fmt)

    def combine_datetime(date_col, time_col):
        return pd.to_datetime(
            df[date_col] + " " + df[time_col],
            format="%d/%m/%Y %H:%M",
            errors="coerce",
        )

    df["StartDT"] = combine_datetime("StartDate", "StartTime")
    df["PlannedDT"] = combine_datetime("PlannedEndDate", "PlannedEndTime")

    dup_cols = [
        "MachineName", "OrderNumber", "SerialNumber",
        "OperationNumber", "PartNumber", "StartDate", "StartTime",
    ]
    df["_dup"] = df.duplicated(subset=dup_cols, keep=False)

    quality = {
        "total": len(df),
        "dup": int(df["_dup"].sum()),
        "bad_rt": int(df["RuntimeMinutes"].isna().sum()),
        "zero_rt": int((df["RuntimeMinutes"] == 0).sum()),
        "bad_dt": int(df["DowntimeMinutes"].isna().sum()),
        "bad_start": int(df["StartDT"].isna().sum()),
        "missing_by_col": {col: int(df[col].isna().sum()) for col in REQUIRED},
    }
    return df, raw, quality


@st.cache_data(show_spinner=False)
def apply_outliers(
    df: pd.DataFrame,
    col: str,
    mode: str,
    min_value: float | None = None,
    max_value: float | None = None,
    trim_pct: float | None = None,
):
    if mode == "None" or df[col].dropna().empty:
        return df.copy(), pd.DataFrame(columns=df.columns), {}

    vals = df[col].dropna()
    q1, q3 = vals.quantile(0.25), vals.quantile(0.75)
    iqr = q3 - q1
    trim_fraction = None if trim_pct is None else float(trim_pct)
    if trim_fraction is not None and trim_fraction >= 1:
        trim_fraction = trim_fraction / 100.0

    if mode == "Custom bounds":
        lo = 0.0 if min_value is None else float(min_value)
        hi = float("inf") if max_value is None else float(max_value)
        if hi < lo:
            lo, hi = hi, lo
        source = "custom"
        detail = "Manual min/max inputs"
    elif "Mild" in mode:
        lo = max(0.0, q1 - 3.0 * iqr)
        hi = q3 + 3.0 * iqr
        source = "preset"
        detail = mode
    else:
        lo = max(0.0, max(q1 - 1.5 * iqr, vals.quantile(0.02)))
        hi = min(q3 + 1.5 * iqr, vals.quantile(0.98))
        source = "preset"
        detail = mode

    if trim_fraction is not None and trim_fraction > 0:
        lower_trim = vals.quantile(trim_fraction)
        upper_trim = vals.quantile(1 - trim_fraction)
        lo = max(lo, lower_trim)
        hi = min(hi, upper_trim)

    mask = df[col].between(lo, hi, inclusive="both") | df[col].isna()
    info = {
        "lo": lo,
        "hi": hi,
        "q1": q1,
        "q3": q3,
        "iqr": iqr,
        "removed": int((~mask).sum()),
        "kept": int(mask.sum()),
        "mode": mode,
        "source": source,
        "detail": detail,
        "trim_pct": trim_fraction,
        "min_value": min_value,
        "max_value": max_value,
    }
    return df[mask].copy(), df[~mask].copy(), info


def build_export_frames(df: pd.DataFrame, df_excl: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df_export = df[ECOLS].rename(columns={"Rt_disp": "Runtime_HHMM", "Dt_disp": "Downtime_HHMM"})
    df_excl_export = (
        df_excl[ECOLS].rename(columns={"Rt_disp": "Runtime_HHMM", "Dt_disp": "Downtime_HHMM"})
        if not df_excl.empty
        else pd.DataFrame(columns=ECOLS)
    )
    return df_export, df_excl_export
