import pandas as pd

REVENUE_NAMES = ["revenue", "sales", "total sales", "income", "amount", "turnover", "net sales", "gross sales"]
COST_NAMES = ["cost", "costs", "expense", "expenses", "spending", "purchase cost", "cogs"]
PROFIT_NAMES = ["profit", "net profit", "gross profit", "earnings"]
QUANTITY_NAMES = ["quantity", "qty", "units", "sold", "volume", "items"]
DATE_NAMES = ["date", "day", "month", "year", "created", "time", "timestamp"]

def normalize_name(name):
    return str(name).strip().lower().replace("_", " ").replace("-", " ")

def find_column(df, names):
    normalized = {column: normalize_name(column) for column in df.columns}
    for column, value in normalized.items():
        if value in names:
            return column
    for column, value in normalized.items():
        if any(name in value for name in names):
            return column
    return None

def detect_business_columns(df):
    return {
        "revenue": find_column(df, REVENUE_NAMES),
        "cost": find_column(df, COST_NAMES),
        "profit": find_column(df, PROFIT_NAMES),
        "quantity": find_column(df, QUANTITY_NAMES),
        "date": find_column(df, DATE_NAMES),
    }

def calculate_kpis(df):
    detected = detect_business_columns(df)
    kpis = {}
    revenue_col = detected["revenue"]
    cost_col = detected["cost"]
    profit_col = detected["profit"]
    quantity_col = detected["quantity"]

    if revenue_col:
        revenue = pd.to_numeric(df[revenue_col], errors="coerce").fillna(0)
        kpis["Revenue"] = float(revenue.sum())

    if cost_col:
        cost = pd.to_numeric(df[cost_col], errors="coerce").fillna(0)
        kpis["Costs"] = float(cost.sum())

    if profit_col:
        profit = pd.to_numeric(df[profit_col], errors="coerce").fillna(0)
        kpis["Profit"] = float(profit.sum())
    elif revenue_col and cost_col:
        revenue = pd.to_numeric(df[revenue_col], errors="coerce").fillna(0)
        cost = pd.to_numeric(df[cost_col], errors="coerce").fillna(0)
        kpis["Profit"] = float((revenue - cost).sum())

    if "Revenue" in kpis and "Profit" in kpis and kpis["Revenue"] != 0:
        kpis["Profit Margin"] = kpis["Profit"] / kpis["Revenue"] * 100

    if quantity_col:
        quantity = pd.to_numeric(df[quantity_col], errors="coerce").fillna(0)
        kpis["Units"] = float(quantity.sum())

    kpis["Records"] = int(len(df))
    return kpis, detected

def find_dimension_columns(df):
    detected = detect_business_columns(df)
    ignored = {v for v in detected.values() if v is not None}
    priority = ["category", "product", "customer", "region", "department", "segment", "type", "brand", "salesperson"]
    candidates = []

    for column in df.columns:
        if column in ignored:
            continue
        series = df[column]
        if not (pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)):
            continue
        unique_count = int(series.nunique(dropna=True))
        if 2 <= unique_count <= 100:
            name = normalize_name(column)
            rank = min((priority.index(word) for word in priority if word in name), default=999)
            candidates.append((rank, unique_count, column))

    candidates.sort()
    return [x[2] for x in candidates]

def create_dimension_analysis(df, dimension=None):
    detected = detect_business_columns(df)
    revenue_col = detected["revenue"]
    if not revenue_col:
        return None

    if dimension is None:
        dimensions = find_dimension_columns(df)
        dimension = dimensions[0] if dimensions else None

    if dimension is None or dimension not in df.columns:
        return None

    temp = df[[dimension, revenue_col]].copy()
    temp[revenue_col] = pd.to_numeric(temp[revenue_col], errors="coerce").fillna(0)
    temp[dimension] = temp[dimension].fillna("Unknown").astype(str).str.strip()
    result = temp.groupby(dimension, dropna=False)[revenue_col].sum().sort_values(ascending=False).reset_index()
    result.columns = ["Category", "Revenue"]
    return result

def create_time_analysis(df):
    detected = detect_business_columns(df)
    date_col = detected["date"]
    revenue_col = detected["revenue"]
    if not date_col or not revenue_col:
        return None

    dates = pd.to_datetime(df[date_col], errors="coerce")
    revenue = pd.to_numeric(df[revenue_col], errors="coerce").fillna(0)
    temp = pd.DataFrame({"Date": dates, "Revenue": revenue}).dropna(subset=["Date"])
    if temp.empty:
        return None

    temp["Period"] = temp["Date"].dt.to_period("M").astype(str)
    result = temp.groupby("Period")["Revenue"].sum().reset_index()
    return result

def generate_insights(df):
    kpis, detected = calculate_kpis(df)
    insights = []

    if "Revenue" in kpis:
        insights.append(f"Revenue totals {kpis['Revenue']:,.2f}.")
    if "Costs" in kpis:
        insights.append(f"Costs total {kpis['Costs']:,.2f}.")
    if "Profit" in kpis:
        insights.append(
            f"Profit is {kpis['Profit']:,.2f}."
            if kpis["Profit"] >= 0
            else f"Profit is negative at {kpis['Profit']:,.2f}."
        )
    if "Profit Margin" in kpis:
        margin = kpis["Profit Margin"]
        label = "strong" if margin >= 30 else "healthy" if margin >= 15 else "needs attention"
        insights.append(f"Profit margin is {margin:.1f}% ({label}).")

    dimensions = find_dimension_columns(df)
    if dimensions and "Revenue" in kpis:
        analysis = create_dimension_analysis(df, dimensions[0])
        if analysis is not None and not analysis.empty:
            top = analysis.iloc[0]
            share = top["Revenue"] / analysis["Revenue"].sum() * 100 if analysis["Revenue"].sum() else 0
            insights.append(
                f"Top {dimensions[0]} is '{top['Category']}', contributing {share:.1f}% of detected revenue."
            )

    return insights

def why_analysis(df, metric="Revenue"):
    kpis, detected = calculate_kpis(df)
    column = detected["revenue"] if metric == "Revenue" else detected["profit"]

    if metric == "Profit" and not column and detected["revenue"] and detected["cost"]:
        revenue = pd.to_numeric(df[detected["revenue"]], errors="coerce").fillna(0)
        cost = pd.to_numeric(df[detected["cost"]], errors="coerce").fillna(0)
        series = revenue - cost
        source = "Revenue minus Cost"
    elif column:
        series = pd.to_numeric(df[column], errors="coerce")
        source = f"'{column}'"
    else:
        return f"I could not identify a suitable {metric.lower()} field."

    series = series.dropna()
    if series.empty:
        return f"There is not enough numeric data to explain {metric.lower()}."

    avg = series.mean()
    high = series.max()
    low = series.min()
    text = f"{metric} comes from {source}. Average per record is {avg:,.2f}; highest is {high:,.2f}; lowest is {low:,.2f}."

    dimensions = find_dimension_columns(df)
    if dimensions and metric == "Revenue":
        analysis = create_dimension_analysis(df, dimensions[0])
        if analysis is not None and not analysis.empty:
            top = analysis.iloc[0]
            total = analysis["Revenue"].sum()
            share = top["Revenue"] / total * 100 if total else 0
            text += f" The leading {dimensions[0].lower()} is '{top['Category']}', responsible for about {share:.1f}% of revenue."
    return text
