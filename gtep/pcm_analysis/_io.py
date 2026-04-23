"""Shared IO helpers for Prescient simulation outputs.

Single source of truth for `prescient_output_to_df`. The same function is
duplicated today in `prescient_lmp_analysis_2035.ipynb` (top-of-notebook helper),
`create_prescient_lmp_analysis_with_hydro_q1.py`, and `update_notebook.py`.
New code should import from here; legacy callsites migrate lazily.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def prescient_output_to_df(file_name: str | Path) -> pd.DataFrame:
    """Load a Prescient output CSV and build a canonical Datetime column.

    Prescient emits outputs with Date / Hour / Minute columns at varying
    granularity. This helper combines them into a single `Datetime` column
    placed first, then drops the original time columns.

    Parameters
    ----------
    file_name : str or Path
        Path to a Prescient CSV (hourly_summary.csv, bus_detail.csv,
        thermal_detail.csv, renewables_detail.csv, line_detail.csv,
        daily_summary.csv, runtimes.csv, or any file with Date [+ Hour [+ Minute]]
        columns).

    Returns
    -------
    pd.DataFrame
        Same columns as the input, with Date/Hour/Minute replaced by a single
        leading `Datetime` column.
    """
    df = pd.read_csv(file_name)
    if "Minute" in df.columns:
        df["Datetime"] = (
            pd.to_datetime(df["Date"])
            + pd.to_timedelta(df["Hour"], "hour")
            + pd.to_timedelta(df["Minute"], "minute")
        )
        df.drop(columns=["Date", "Hour", "Minute"], inplace=True)
    elif "Hour" in df.columns:
        df["Datetime"] = pd.to_datetime(df["Date"]) + pd.to_timedelta(df["Hour"], "hour")
        df.drop(columns=["Date", "Hour"], inplace=True)
    else:
        df["Datetime"] = pd.to_datetime(df["Date"])
        df.drop(columns=["Date"], inplace=True)
    cols = df.columns.tolist()
    return df[cols[-1:] + cols[:-1]]
