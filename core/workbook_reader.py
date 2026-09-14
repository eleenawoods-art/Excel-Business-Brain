import io
from typing import Dict

import pandas as pd


def analyze_workbook(df: pd.DataFrame):

    rows = []

    for column in df.columns:

        series = df[column]

        non_null = series.dropna()

        sample = (
            non_null.iloc[0]
            if not non_null.empty
            else ""
        )

        if pd.api.types.is_numeric_dtype(series):

            detected = "Numeric"

        elif pd.api.types.is_datetime64_any_dtype(series):

            detected = "Date/Time"

        elif pd.api.types.is_bool_dtype(series):

            detected = "Boolean"

        else:

            detected = "Text"

        rows.append(
            {
                "column": str(column),
                "detected_type": detected,
                "missing": int(series.isna().sum()),
                "unique_values": int(
                    series.nunique(dropna=True)
                ),
                "sample": str(sample)[:80],
            }
        )

    return rows


def build_workbook_bytes(
    workbook: Dict[str, pd.DataFrame]
) -> bytes:

    buffer = io.BytesIO()

    with pd.ExcelWriter(
        buffer,
        engine="openpyxl"
    ) as writer:

        for sheet_name, df in workbook.items():

            safe_name = (
                str(sheet_name)[:31]
                or "Sheet1"
            )

            df.to_excel(
                writer,
                sheet_name=safe_name,
                index=False
            )

    buffer.seek(0)

    return buffer.getvalue()
