import streamlit as st
import pandas as pd
import plotly.express as px

from core.business_analyzer import (
    calculate_kpis,
    create_dimension_analysis,
    create_time_analysis,
    generate_insights,
    why_analysis,
    detect_business_columns,
    find_dimension_columns,
)

st.set_page_config(
    page_title="Business Dashboard",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Business Dashboard")
st.caption(
    "Turn Excel data into a clear business overview with KPIs, trends, "
    "performance analysis, alerts and recommendations."
)

# ---------------------------------------------------------
# WORKBOOK CHECK
# ---------------------------------------------------------

if "workbook" not in st.session_state or not st.session_state.workbook:
    st.warning("Please upload an Excel workbook from the main page first.")
    st.stop()

workbook = st.session_state.workbook

if not isinstance(workbook, dict) or not workbook:
    st.warning("No usable workbook data was found. Please upload the workbook again.")
    st.stop()

sheet_names = list(workbook.keys())

if not sheet_names:
    st.warning("The workbook does not contain any worksheets.")
    st.stop()

selected_sheet = st.selectbox(
    "📄 Select worksheet",
    sheet_names,
)

df = workbook[selected_sheet].copy()

if df is None or df.empty:
    st.info("The selected worksheet is empty.")
    st.stop()

df = df.dropna(axis=0, how="all")
df = df.dropna(axis=1, how="all")

if df.empty:
    st.info("The selected worksheet does not contain usable data.")
    st.stop()

# ---------------------------------------------------------
# BUSINESS ANALYSIS
# ---------------------------------------------------------

try:
    kpis, detected = calculate_kpis(df)
except Exception as exc:
    kpis = {}
    detected = {}
    st.error(f"Business analysis could not be completed: {exc}")

if not isinstance(kpis, dict):
    kpis = {}

if not isinstance(detected, dict):
    detected = {}

revenue_col = detected.get("revenue")
cost_col = detected.get("cost")
profit_col = detected.get("profit")
quantity_col = detected.get("quantity")
date_col = detected.get("date")

# ---------------------------------------------------------
# DATA QUALITY VALUES
# ---------------------------------------------------------

missing_cells = int(df.isna().sum().sum())
duplicate_rows = int(df.duplicated().sum())
total_cells = int(df.shape[0] * df.shape[1])

completeness = (
    ((total_cells - missing_cells) / total_cells) * 100
    if total_cells
    else 0
)

# ---------------------------------------------------------
# EXECUTIVE OVERVIEW
# ---------------------------------------------------------

st.divider()
st.subheader("📌 Executive Overview")

overview = st.columns(6)

metric_order = [
    ("Revenue", "currency"),
    ("Costs", "currency"),
    ("Profit", "currency"),
    ("Profit Margin", "percent"),
    ("Units", "number"),
    ("Records", "number"),
]

for column, (name, kind) in zip(overview, metric_order):
    with column:
        value = kpis.get(name)

        if value is None:
            st.metric(name, "—")

        elif kind == "currency":
            st.metric(
                name,
                f"{float(value):,.2f}",
            )

        elif kind == "percent":
            st.metric(
                name,
                f"{float(value):.1f}%",
            )

        elif kind == "number":
            st.metric(
                name,
                f"{float(value):,.0f}",
            )

# ---------------------------------------------------------
# BUSINESS SIGNALS
# ---------------------------------------------------------

st.subheader("🎯 Business Signals")

signal_cols = st.columns(3)

# Profitability signal
with signal_cols[0]:

    if (
        "Revenue" in kpis
        and "Profit" in kpis
        and kpis.get("Revenue")
    ):
        margin = (
            float(kpis["Profit"])
            / float(kpis["Revenue"])
            * 100
        )

        if margin < 0:
            st.error("🔴 Profit is negative")

        elif margin < 15:
            st.warning("🟠 Profit margin needs attention")

        elif margin < 30:
            st.info("🟡 Profit margin is moderate")

        else:
            st.success("🟢 Profit margin is strong")

    else:
        st.info("Profitability signal unavailable")

# Cost signal
with signal_cols[1]:

    if revenue_col and cost_col:

        revenue_values = pd.to_numeric(
            df[revenue_col],
            errors="coerce",
        ).fillna(0)

        cost_values = pd.to_numeric(
            df[cost_col],
            errors="coerce",
        ).fillna(0)

        revenue_total = float(revenue_values.sum())
        cost_total = float(cost_values.sum())

        if revenue_total:
            cost_ratio = (
                cost_total
                / revenue_total
                * 100
            )
        else:
            cost_ratio = 0

        if cost_ratio >= 80:
            st.error(
                f"🔴 Costs consume {cost_ratio:.1f}% of revenue"
            )

        elif cost_ratio >= 60:
            st.warning(
                f"🟠 Costs consume {cost_ratio:.1f}% of revenue"
            )

        else:
            st.success(
                f"🟢 Costs consume {cost_ratio:.1f}% of revenue"
            )

    else:
        st.info("Cost-to-revenue signal unavailable")

# Data quality signal
with signal_cols[2]:

    if missing_cells == 0 and duplicate_rows == 0:
        st.success("🟢 Data quality looks clean")

    elif missing_cells <= 5 and duplicate_rows <= 2:
        st.info("🟡 Minor data-quality issues detected")

    else:
        st.warning("🟠 Data quality needs review")

# ---------------------------------------------------------
# AUTOMATIC BUSINESS STRUCTURE
# ---------------------------------------------------------

st.divider()
st.subheader("🔎 Automatically Detected Business Structure")

detection_rows = []

for key, value in detected.items():
    detection_rows.append(
        {
            "Business Metric": str(key)
            .replace("_", " ")
            .title(),
            "Detected Column": value or "Not detected",
        }
    )

detection_df = pd.DataFrame(detection_rows)

if not detection_df.empty:
    st.dataframe(
        detection_df,
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No business structure was detected.")

# ---------------------------------------------------------
# BUSINESS TRENDS
# ---------------------------------------------------------

st.divider()
st.subheader("📈 Business Trends")

try:
    time_analysis = create_time_analysis(df)
except Exception:
    time_analysis = None

if (
    isinstance(time_analysis, pd.DataFrame)
    and not time_analysis.empty
    and {"Period", "Revenue"}.issubset(
        time_analysis.columns
    )
):

    trend_chart = px.line(
        time_analysis,
        x="Period",
        y="Revenue",
        markers=True,
        title="Revenue Trend",
    )

    st.plotly_chart(
        trend_chart,
        use_container_width=True,
    )

    if len(time_analysis) >= 2:

        first_revenue = float(
            time_analysis.iloc[0]["Revenue"]
        )

        latest_revenue = float(
            time_analysis.iloc[-1]["Revenue"]
        )

        if first_revenue:

            change = (
                (
                    latest_revenue
                    - first_revenue
                )
                / abs(first_revenue)
                * 100
            )

            if change > 0:
                st.success(
                    f"Revenue changed by {change:.1f}% "
                    "from the first available period "
                    "to the latest available period."
                )

            elif change < 0:
                st.warning(
                    f"Revenue changed by {change:.1f}% "
                    "from the first available period "
                    "to the latest available period."
                )

            else:
                st.info(
                    "Revenue is unchanged between "
                    "the first and latest available periods."
                )

else:

    st.info(
        "No usable date + revenue combination was detected "
        "for a time trend. Add a date column and a "
        "revenue/sales column to unlock this analysis."
    )

# ---------------------------------------------------------
# PERFORMANCE BY BUSINESS DIMENSION
# ---------------------------------------------------------

st.divider()
st.subheader("🏆 Performance by Business Dimension")

try:
    dimensions = find_dimension_columns(df)
except Exception:
    dimensions = []

if dimensions:

    selected_dimension = st.selectbox(
        "Analyze dimension",
        dimensions,
        format_func=lambda value: str(value),
    )

    try:
        dimension_analysis = create_dimension_analysis(
            df,
            selected_dimension,
        )
    except Exception:
        dimension_analysis = None

    if (
        isinstance(dimension_analysis, pd.DataFrame)
        and not dimension_analysis.empty
    ):

        chart_data = dimension_analysis.head(20)

        chart = px.bar(
            chart_data,
            x="Category",
            y="Revenue",
            title=f"Revenue by {selected_dimension}",
        )

        st.plotly_chart(
            chart,
            use_container_width=True,
        )

        total_dimension_revenue = float(
            dimension_analysis["Revenue"].sum()
        )

        performance_table = dimension_analysis.copy()

        if total_dimension_revenue:
            performance_table["Revenue Share"] = (
                performance_table["Revenue"]
                / total_dimension_revenue
                * 100
            ).round(1)

        st.dataframe(
            performance_table,
            use_container_width=True,
            hide_index=True,
        )

        top_row = dimension_analysis.iloc[0]

        if total_dimension_revenue:

            top_share = (
                float(top_row["Revenue"])
                / total_dimension_revenue
                * 100
            )

        else:
            top_share = 0

        if top_share >= 70:

            st.warning(
                "⚠️ Revenue is highly concentrated: "
                f"'{top_row['Category']}' represents "
                f"{top_share:.1f}% of detected revenue."
            )

        else:

            st.info(
                f"Top {str(selected_dimension).lower()}: "
                f"'{top_row['Category']}' with "
                f"{top_share:.1f}% of detected revenue."
            )

else:

    st.info(
        "No suitable business dimension was detected. "
        "Columns such as Category, Product, Region, "
        "Customer or Department can unlock this analysis."
    )

# ---------------------------------------------------------
# PROFITABILITY ANALYSIS
# ---------------------------------------------------------

st.divider()
st.subheader("💰 Profitability Analysis")

if revenue_col and cost_col:

    profitability = pd.DataFrame(
        {
            "Revenue": pd.to_numeric(
                df[revenue_col],
                errors="coerce",
            ).fillna(0),

            "Costs": pd.to_numeric(
                df[cost_col],
                errors="coerce",
            ).fillna(0),
        }
    )

    profitability["Profit"] = (
        profitability["Revenue"]
        - profitability["Costs"]
    )

    profitability["Margin %"] = profitability.apply(
        lambda row:
        (
            row["Profit"]
            / row["Revenue"]
            * 100
        )
        if row["Revenue"] != 0
        else 0,
        axis=1,
    )

    profit_cols = st.columns(3)

    with profit_cols[0]:
        st.metric(
            "Average Revenue / Record",
            f"{profitability['Revenue'].mean():,.2f}",
        )

    with profit_cols[1]:
        st.metric(
            "Average Profit / Record",
            f"{profitability['Profit'].mean():,.2f}",
        )

    with profit_cols[2]:

        negative_records = int(
            (profitability["Profit"] < 0).sum()
        )

        st.metric(
            "Loss-Making Records",
            f"{negative_records:,}",
        )

    if negative_records:

        st.warning(
            f"⚠️ {negative_records:,} record(s) have "
            "costs higher than revenue. These records "
            "should be investigated."
        )

    else:

        st.success(
            "No record-level losses were detected "
            "from Revenue minus Costs."
        )

elif profit_col:

    profit_values = pd.to_numeric(
        df[profit_col],
        errors="coerce",
    ).dropna()

    if not profit_values.empty:

        st.metric(
            "Average Profit / Record",
            f"{profit_values.mean():,.2f}",
        )

        st.info(
            "A direct Profit column was detected, but "
            "a Cost column was not available for a full "
            "Revenue-vs-Cost profitability analysis."
        )

else:

    st.info(
        "Add Revenue and Cost columns to unlock "
        "record-level profitability analysis."
    )

# ---------------------------------------------------------
# BUSINESS INSIGHTS
# ---------------------------------------------------------

st.divider()
st.subheader("💡 Business Insights")

try:
    insights = generate_insights(df)
except Exception as exc:
    insights = []
    st.warning(
        f"Insight generation could not be completed: {exc}"
    )

if isinstance(insights, str):
    insights = [insights]

if insights:

    for insight in insights:
        st.info(f"💡 {insight}")

else:

    st.info(
        "Not enough business data for automatic insights."
    )

# ---------------------------------------------------------
# RECOMMENDATIONS
# ---------------------------------------------------------

st.subheader("🚀 Recommended Areas to Investigate")

recommendations = []

if "Profit Margin" in kpis:

    margin = float(kpis["Profit Margin"])

    if margin < 15:

        recommendations.append(
            "Review pricing, operating costs and "
            "low-margin transactions because overall "
            "profit margin is below 15%."
        )

    elif margin < 30:

        recommendations.append(
            "Review the largest cost categories and "
            "lower-margin transactions to identify "
            "opportunities to improve profitability."
        )

    else:

        recommendations.append(
            "Monitor the current margin and identify "
            "which products/categories are contributing "
            "most to profitable revenue."
        )

if revenue_col and cost_col:

    revenue_total = float(
        pd.to_numeric(
            df[revenue_col],
            errors="coerce",
        )
        .fillna(0)
        .sum()
    )

    cost_total = float(
        pd.to_numeric(
            df[cost_col],
            errors="coerce",
        )
        .fillna(0)
        .sum()
    )

    if (
        revenue_total
        and cost_total / revenue_total > 0.8
    ):

        recommendations.append(
            "Costs are taking a large share of revenue. "
            "Investigate the biggest cost drivers before "
            "increasing sales volume."
        )

if dimensions:

    try:

        recommendation_analysis = create_dimension_analysis(
            df,
            dimensions[0],
        )

        if (
            isinstance(
                recommendation_analysis,
                pd.DataFrame,
            )
            and not recommendation_analysis.empty
        ):

            total = float(
                recommendation_analysis["Revenue"].sum()
            )

            if total:

                top = recommendation_analysis.iloc[0]

                share = (
                    float(top["Revenue"])
                    / total
                    * 100
                )

                if share >= 50:

                    recommendations.append(
                        f"Revenue is concentrated in "
                        f"'{top['Category']}'. Review this "
                        "area closely and consider "
                        "diversification risk."
                    )

    except Exception:
        pass

if missing_cells:

    recommendations.append(
        f"Review {missing_cells:,} missing cell(s) "
        "before relying on the workbook for final "
        "business reporting."
    )

if duplicate_rows:

    recommendations.append(
        f"Review {duplicate_rows:,} duplicate row(s) "
        "to confirm they are intentional and not "
        "inflating business totals."
    )

if not recommendations:

    recommendations.append(
        "Continue monitoring revenue, costs, profitability "
        "and business dimensions as new workbook data "
        "is added."
    )

for recommendation in recommendations:
    st.success(f"• {recommendation}")

# ---------------------------------------------------------
# WHY ANALYSIS
# ---------------------------------------------------------

st.divider()
st.subheader("❓ Why Analysis")

available_metrics = []

if revenue_col:
    available_metrics.append("Revenue")

if profit_col or (revenue_col and cost_col):
    available_metrics.append("Profit")

if not available_metrics:

    st.info(
        "Revenue or Profit data is required "
        "to use Why Analysis."
    )

else:

    selected_metric = st.selectbox(
        "What do you want explained?",
        available_metrics,
    )

    if st.button(
        "🔍 Explain This Metric",
        type="primary",
    ):

        try:

            explanation = why_analysis(
                df,
                selected_metric,
            )

            st.success(explanation)

        except Exception as exc:

            st.error(
                "Metric explanation could not be "
                f"generated: {exc}"
            )

# ---------------------------------------------------------
# DATA QUALITY
# ---------------------------------------------------------

st.divider()
st.subheader("🧹 Data Quality Overview")

quality_cols = st.columns(4)

with quality_cols[0]:
    st.metric(
        "Missing Cells",
        f"{missing_cells:,}",
    )

with quality_cols[1]:
    st.metric(
        "Duplicate Rows",
        f"{duplicate_rows:,}",
    )

with quality_cols[2]:
    st.metric(
        "Data Completeness",
        f"{completeness:.1f}%",
    )

with quality_cols[3]:
    st.metric(
        "Total Cells",
        f"{total_cells:,}",
    )

# ---------------------------------------------------------
# DATA PREVIEW
# ---------------------------------------------------------

st.divider()
st.subheader("📋 Data Preview")

preview_max = min(
    500,
    max(10, len(df)),
)

preview_limit = st.slider(
    "Rows to preview",
    min_value=10,
    max_value=preview_max,
    value=min(100, preview_max),
    step=10,
)

st.dataframe(
    df.head(preview_limit),
    use_container_width=True,
    hide_index=True,
)

csv_data = df.to_csv(
    index=False
).encode("utf-8")

st.download_button(
    "⬇️ Download Current Sheet as CSV",
    data=csv_data,
    file_name=f"{selected_sheet}_business_data.csv",
    mime="text/csv",
)

# ---------------------------------------------------------
# FOOTER
# ---------------------------------------------------------

st.divider()

st.caption(
    "Excel Business Brain • Automated KPIs, trends, "
    "performance analysis, profitability checks, "
    "insights and business recommendations."
)
