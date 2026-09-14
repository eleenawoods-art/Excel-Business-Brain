import pandas as pd


def analyze_data_health(
    df: pd.DataFrame
) -> dict:

    rows = len(df)

    cells = max(
        rows * max(len(df.columns), 1),
        1
    )

    duplicates = int(
        df.duplicated().sum()
    )

    missing_cells = int(
        df.isna().sum().sum()
    )

    blank_rows = int(
        df.isna().all(axis=1).sum()
    )

    type_warnings = 0

    issues = []

    if duplicates:

        issues.append(
            f"{duplicates:,} duplicate row(s) detected."
        )

    if missing_cells:

        issues.append(
            f"{missing_cells:,} missing cell(s) detected."
        )

    if blank_rows:

        issues.append(
            f"{blank_rows:,} completely blank row(s) detected."
        )

    for column in df.columns:

        series = df[column].dropna()

        if series.empty:
            continue

        if series.dtype == "object":

            converted = pd.to_numeric(
                series,
                errors="coerce"
            )

            numeric_ratio = float(
                converted.notna().mean()
            )

            if 0.8 <= numeric_ratio < 1:

                type_warnings += 1

                issues.append(
                    f"Column '{column}' contains "
                    f"mixed numeric/text values."
                )

    duplicate_penalty = min(
        25,
        round(
            (duplicates / max(rows, 1)) * 100
        )
    )

    missing_penalty = min(
        35,
        round(
            (missing_cells / cells) * 100
        )
    )

    blank_penalty = min(
        15,
        round(
            (blank_rows / max(rows, 1)) * 100
        )
    )

    type_penalty = min(
        20,
        type_warnings * 5
    )

    score = max(
        0,
        min(
            100,
            100
            - duplicate_penalty
            - missing_penalty
            - blank_penalty
            - type_penalty
        )
    )

    return {
        "score": score,
        "duplicates": duplicates,
        "missing_cells": missing_cells,
        "blank_rows": blank_rows,
        "type_warnings": type_warnings,
        "issues": issues,
    }


def clean_dataframe(
    df: pd.DataFrame
) -> pd.DataFrame:

    # Remove completely empty rows.
    df = df.dropna(
        how="all"
    ).copy()

    # Remove exact duplicate rows.
    df = df.drop_duplicates().copy()

    # Trim whitespace from text cells.
    for column in df.select_dtypes(
        include=["object"]
    ).columns:

        df[column] = df[column].map(
            lambda value:
                value.strip()
                if isinstance(value, str)
                else value
        )

    return df
