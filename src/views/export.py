import streamlit as st

from src.ui_utils import df_to_records, fmt, to_excel


def render(df_export, df_excl_exp, rt_summary, dt_summary, mach_summary, cmp_display, benchmarks, trimmed_mean_name):
    st.subheader("💾 Download Reports")

    st.markdown("#### 1 · Cleaned Filtered Data")
    st.download_button("⬇️ cleaned_data.csv", df_export.to_csv(index=False).encode("utf-8"), "cleaned_data.csv", "text/csv", key="dl_clean")
    st.caption(f"{len(df_export):,} rows, {len(df_export.columns)} columns")

    st.markdown("#### 2 · Excluded Outlier Rows")
    if not df_excl_exp.empty:
        st.download_button("⬇️ excluded_outliers.csv", df_excl_exp.to_csv(index=False).encode("utf-8"), "excluded_outliers.csv", "text/csv", key="dl_excl")
        st.caption(f"{len(df_excl_exp):,} outlier rows")
    else:
        st.info("No outlier rows to export (removal off, or none detected).")

    st.markdown("#### 3 · Benchmark Table")
    bm_export = benchmarks.copy()
    if not bm_export.empty:
        bm_export["OperatorTime_HHMM"] = bm_export["OperatorTime_min"].apply(fmt)
        bm_export["ProductionTime_HHMM"] = bm_export["ProductionTime_min"].apply(fmt)
        st.download_button("⬇️ benchmarks.csv", bm_export.to_csv(index=False).encode("utf-8"), "benchmarks.csv", "text/csv", key="dl_bm")
    else:
        st.info("No benchmarks entered yet.")

    st.markdown("#### 4 · Full Management Report (Excel, multi-sheet)")
    st.caption(f"Runtime and benchmark exports use {trimmed_mean_name} based on the current sidebar selection.")
    excel_sheets = [
        ("Filtered Data", df_export),
        ("Excluded Outliers", df_excl_exp),
        ("Runtime Summary", rt_summary),
        ("Downtime Summary", dt_summary),
        ("Machine Summary", mach_summary),
        ("Benchmark Comparison", cmp_display),
    ]
    if not bm_export.empty:
        excel_sheets.append(("Benchmarks", bm_export))
    payload = tuple((name, tuple(frame.columns), df_to_records(frame)) for name, frame in excel_sheets)
    xl_bytes = to_excel(payload)
    st.download_button("⬇️ management_report.xlsx", xl_bytes, "management_report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_xl")
    built = [name for name, frame in excel_sheets if not frame.empty]
    st.caption(f"Sheets included: {', '.join(built)}")

    st.divider()
    st.markdown("💡 **Print to PDF:** Use your browser's *File → Print → Save as PDF* to capture any tab as a report.")
