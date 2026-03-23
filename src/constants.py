from pathlib import Path

THEME = "plotly_dark"

REQUIRED = [
    "ID", "MachineName", "OrderNumber", "SerialNumber",
    "OperationNumber", "PartNumber", "RuntimeHHMM", "DowntimeHHMM",
    "StartDate", "StartTime", "PlannedEndDate", "PlannedEndTime",
]

ECOLS = [
    "ID", "MachineName", "OrderNumber", "SerialNumber",
    "OperationNumber", "PartNumber",
    "Rt_disp", "Dt_disp", "RuntimeMinutes", "DowntimeMinutes",
    "StartDate", "StartTime", "PlannedEndDate", "PlannedEndTime",
]

DISP_COLS = [
    "ID", "MachineName", "PartNumber", "OperationNumber",
    "SerialNumber", "Rt_disp", "StartDate", "StartTime",
]

BENCHMARK_REQUIRED = ["PartNumber", "OperationNumber"]
BENCHMARK_OPTIONAL = [
    "Family", "OperatorTime_min", "ProductionTime_min", "Notes",
    "OperatorTime_HHMM", "ProductionTime_HHMM",
]
BENCHMARK_COLUMNS = [
    "PartNumber", "OperationNumber", "Family",
    "OperatorTime_min", "ProductionTime_min", "Notes",
]

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
BENCHMARKS_PATH = DATA_DIR / "benchmarks.csv"
FAMILIES_PATH = DATA_DIR / "families.json"
