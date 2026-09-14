import re
from typing import Tuple

import pandas as pd


FORMULA_RE = re.compile(
    r"^="
)

ERROR_VALUES = {
    "#REF!",
    "#DIV/0!",
    "#VALUE!",
    "#NAME?",
    "#N/A",
    "#NUM!",
    "#NULL!"
}


def _is_formula(value):

    return (
        isinstance(value, str)
        and bool(
            FORMULA_RE.match(
                value.strip()
            )
        )
    )


def analyze_formulas(
    df: pd.DataFrame
) -> dict:

    formula_cells = 0

    errors = []

    details = []

    formula_columns = {}

    for column in df.columns:

        formulas = []

        for idx, value in df[column].items():

            if _is_formula(value):

                formula_cells += 1

                formulas.append(
                    (idx, value)
                )

                upper = value.upper()

                for error in ERROR_VALUES:

                    if error in upper:

                        errors.append(
                            (
                                column,
                                idx,
                                error
                            )
                        )

        if formulas:

            formula_columns[
                column
            ] = formulas

    for column, formulas in formula_columns.items():

        if len(formulas) >= 3:

            normalized = []

            for _, formula in formulas:

                normalized.append(
                    re.sub(
                        r"(\$?[A-Z]{1,3}\$?)\d+",
                        r"\1#",
                        formula.upper()
                    )
                )

            common = max(
                set(normalized),
                key=normalized.count
            )

            inconsistent = [
                (idx, formula)

                for (idx, formula), norm
                in zip(
                    formulas,
                    normalized
                )

                if norm != common
            ]

            for idx, formula in inconsistent[:20]:

                details.append(
                    f"Column '{column}', "
                    f"row {idx + 2}: formula "
                    f"pattern differs from the "
                    f"dominant pattern: {formula}"
                )

            min_row = min(
                i for i, _ in formulas
            )

            max_row = max(
                i for i, _ in formulas
            )

            for row in range(
                min_row,
                max_row + 1
            ):

                if pd.isna(
                    df.at[
                        row,
                        column
                    ]
                ):

                    details.append(
                        f"Column '{column}', "
                        f"row {row + 2}: blank "
                        f"inside a formula-heavy range."
                    )

    for column, row, error in errors[:20]:

        details.append(
            f"Column '{column}', "
            f"row {row + 2}: Excel "
            f"error value {error} detected."
        )

    return {
        "formula_cells": formula_cells,
        "issues": len(details),
        "details": details[:50],
    }


def apply_safe_formula_fixes(
    df: pd.DataFrame
) -> Tuple[pd.DataFrame, int]:

    fixes = 0

    for column in df.columns:

        formula_rows = [
            idx
            for idx, value
            in df[column].items()
            if _is_formula(value)
        ]

        if len(formula_rows) < 3:
            continue

        min_row = min(
            formula_rows
        )

        max_row = max(
            formula_rows
        )

        for row in range(
            min_row + 1,
            max_row
        ):

            if not pd.isna(
                df.at[
                    row,
                    column
                ]
            ):
                continue

            above = df.at[
                row - 1,
                column
            ]

            below = df.at[
                row + 1,
                column
            ]

            if not (
                _is_formula(above)
                and _is_formula(below)
            ):
                continue

            above_norm = re.sub(
                r"(\$?[A-Z]{1,3}\$?)\d+",
                r"\1#",
                above.upper()
            )

            below_norm = re.sub(
                r"(\$?[A-Z]{1,3}\$?)\d+",
                r"\1#",
                below.upper()
            )

            if above_norm != below_norm:
                continue

            df.at[
                row,
                column
            ] = above

            fixes += 1

    return df, fixes
