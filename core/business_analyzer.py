import pandas as pd
import numpy as np


REVENUE_NAMES = [
    "revenue", "sales", "total sales", "income",
    "amount", "turnover", "net sales", "gross sales"
]

COST_NAMES = [
    "cost", "costs", "expense", "expenses",
    "spending", "purchase cost", "cogs"
]

PROFIT_NAMES = [
    "profit", "net profit", "gross profit",
    "earnings", "margin"
]

QUANTITY_NAMES = [
    "quantity", "qty", "units", "sold",
    "volume", "items"
]

DATE_NAMES = [
    "date", "day", "month", "year",
    "created", "time", "timestamp"
]


def normalize_name(name):
    return (
        str(name)
        .strip()
        .lower()
        .replace("_", " ")
        .replace("-", " ")
    )


def find_column(df, names):

    normalized = {
        column: normalize_name(column)
        for column in df.columns
    }

    # Exact match first
    for column, normalized_name in normalized.items():

        if normalized_name in names:
            return column

    # Partial match
    for column, normalized_name in normalized.items():

        for name in names:

            if name in normalized_name:
                return column

    return None


def numeric_columns(df):

    return [
        column
        for column in df.columns
        if pd.api.types.is_numeric_dtype(
            df[column]
        )
    ]


def detect_business_columns(df):

    revenue = find_column(
        df,
        REVENUE_NAMES
    )

    cost = find_column(
        df,
        COST_NAMES
    )

    profit = find_column(
        df,
        PROFIT_NAMES
    )

    quantity = find_column(
        df,
        QUANTITY_NAMES
    )

    date = find_column(
        df,
        DATE_NAMES
    )

    return {
        "revenue": revenue,
        "cost": cost,
        "profit": profit,
        "quantity": quantity,
        "date": date
    }


def calculate_kpis(df):

    detected = detect_business_columns(df)

    revenue_col = detected["revenue"]
    cost_col = detected["cost"]
    profit_col = detected["profit"]
    quantity_col = detected["quantity"]

    kpis = {}

    if revenue_col:

        revenue = pd.to_numeric(
            df[revenue_col],
            errors="coerce"
        ).fillna(0)

        kpis["Revenue"] = float(
            revenue.sum()
        )

    if cost_col:

        cost = pd.to_numeric(
            df[cost_col],
            errors="coerce"
        ).fillna(0)

        kpis["Costs"] = float(
            cost.sum()
        )

    if profit_col:

        profit = pd.to_numeric(
            df[profit_col],
            errors="coerce"
        ).fillna(0)

        kpis["Profit"] = float(
            profit.sum()
        )

    elif revenue_col and cost_col:

        revenue = pd.to_numeric(
            df[revenue_col],
            errors="coerce"
        ).fillna(0)

        cost = pd.to_numeric(
            df[cost_col],
            errors="coerce"
        ).fillna(0)

        kpis["Profit"] = float(
            (revenue - cost).sum()
        )

    if revenue_col and (
        "Profit" in kpis
    ):

        if kpis["Revenue"] != 0:

            kpis["Profit Margin"] = (
                kpis["Profit"]
                / kpis["Revenue"]
                * 100
            )

    if quantity_col:

        quantity = pd.to_numeric(
            df[quantity_col],
            errors="coerce"
        ).fillna(0)

        kpis["Units"] = float(
            quantity.sum()
        )

    kpis["Records"] = int(
        len(df)
    )

    return kpis, detected


def find_dimension_column(df):

    ignored = {
        normalize_name(column)
        for column in [
            find_column(df, REVENUE_NAMES),
            find_column(df, COST_NAMES),
            find_column(df, PROFIT_NAMES),
            find_column(df, QUANTITY_NAMES),
        ]
        if column
    }

    candidates = []

    for column in df.columns:

        if normalize_name(column) in ignored:
            continue

        if (
            df[column].dtype == "object"
            or pd.api.types.is_categorical_dtype(
                df[column]
            )
        ):

            unique_count = (
                df[column]
                .nunique(dropna=True)
            )

            if 2 <= unique_count <= 100:

                candidates.append(
                    (
                        column,
                        unique_count
                    )
                )

    if candidates:

        candidates.sort(
            key=lambda x: x[1]
        )

        return candidates[0][0]

    return None


def create_dimension_analysis(df):

    detected = detect_business_columns(df)

    revenue_col = detected["revenue"]

    dimension = find_dimension_column(
        df
    )

    if not dimension:
        return None

    if not revenue_col:
        return None

    temp = df[
        [dimension, revenue_col]
    ].copy()

    temp[revenue_col] = pd.to_numeric(
        temp[revenue_col],
        errors="coerce"
    ).fillna(0)

    result = (
        temp
        .groupby(dimension, dropna=False)[
            revenue_col
        ]
        .sum()
        .sort_values(
            ascending=False
        )
        .reset_index()
    )

    result.columns = [
        "Category",
        "Revenue"
    ]

    return result


def generate_insights(df):

    kpis, detected = calculate_kpis(
        df
    )

    insights = []

    if "Revenue" in kpis:

        insights.append(
            f"Total detected revenue is "
            f"{kpis['Revenue']:,.2f}."
        )

    if "Profit" in kpis:

        if kpis["Profit"] > 0:

            insights.append(
                f"The workbook shows a positive "
                f"profit of {kpis['Profit']:,.2f}."
            )

        elif kpis["Profit"] < 0:

            insights.append(
                f"The workbook shows a negative "
                f"profit of {abs(kpis['Profit']):,.2f}."
            )

    if "Profit Margin" in kpis:

        margin = kpis[
            "Profit Margin"
        ]

        if margin < 10:

            insights.append(
                f"Profit margin is only "
                f"{margin:.1f}%, which may deserve "
                f"attention."
            )

        elif margin >= 30:

            insights.append(
                f"Profit margin is strong at "
                f"{margin:.1f}%."
            )

    dimension_analysis = (
        create_dimension_analysis(df)
    )

    if dimension_analysis is not None:

        if len(dimension_analysis) > 0:

            top = dimension_analysis.iloc[0]

            insights.append(
                f"Top detected category is "
                f"'{top['Category']}' with revenue "
                f"of {top['Revenue']:,.2f}."
            )

            if len(dimension_analysis) >= 2:

                bottom = (
                    dimension_analysis
                    .iloc[-1]
                )

                insights.append(
                    f"Lowest detected category is "
                    f"'{bottom['Category']}' with "
                    f"revenue of "
                    f"{bottom['Revenue']:,.2f}."
                )

    return insights


def why_analysis(df, metric="Revenue"):

    kpis, detected = calculate_kpis(
        df
    )

    if metric == "Revenue":

        column = detected["revenue"]

    elif metric == "Profit":

        column = detected["profit"]

    else:

        column = detected["revenue"]

    if not column:

        return (
            "I could not identify a suitable "
            f"{metric.lower()} column."
        )

    series = pd.to_numeric(
        df[column],
        errors="coerce"
    ).dropna()

    if series.empty:

        return (
            f"There is not enough numeric data "
            f"to explain {metric.lower()}."
        )

    average = series.mean()
    maximum = series.max()
    minimum = series.min()

    max_index = series.idxmax()
    min_index = series.idxmin()

    explanation = (
        f"{metric} is based on the '{column}' "
        f"column. The average value per record "
        f"is {average:,.2f}. The highest recorded "
        f"value is {maximum:,.2f} at row "
        f"{max_index + 2}, while the lowest is "
        f"{minimum:,.2f} at row "
        f"{min_index + 2}."
    )

    return explanation
