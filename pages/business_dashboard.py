import streamlit as st
import pandas as pd
import plotly.express as px

from core.business_analyzer import (
    calculate_kpis,
    create_dimension_analysis,
    generate_insights,
    why_analysis,
    detect_business_columns,
)

st.set_page_config(
    page_title="Business Dashboard",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Business Dashboard")
st.caption("Automatically analyze your uploaded Excel workbook and turn raw data into business insights.")

# --------------------------------------------------
# WORKBOOK CHECK
# --------------------------------------------------

if "workbook" not in st.session_state or not st.session_state.workbook:
    st.warning("Please upload an Excel workbook from the main page first.")
    st.stop()

workbook = st.session_state.workbook

if not isinstance(workbook, dict) or not workbook:
    st.warning("No usable workbook data was found. Please upload the workbook again.")
    st.stop()

# --------------------------------------------------
# SHEET SELECTION
# --------------------------------------------------

sheet_names = list(workbook.keys())

if not sheet_names:
    st.warning("The uploaded workbook does not contain any sheets.")
    st.stop()

selected_sheet = st.selectbox(
    "📄 Select worksheet",
    sheet_names,
)

df = workbook[selected_sheet].copy()

if df is None or df.empty:
    st.info("The selected worksheet is empty.")
    st.stop()

# Clean completely empty rows/columns for more reliable analysis.
df = df.dropna(axis=0, how="all").dropna(axis=1, how="all")

if df.empty:
    st.info("The selected worksheet does not contain usable data.")
    st.stop()

# --------------------------------------------------
# WORKBOOK SUMMARY
# --------------------------------------------------

st.divider()
st.subheader("📌 Workbook Summary")

summary_cols = st.columns(4)

with summary_cols[0]:
    st.metric("Worksheet", selected_sheet)

with summary_cols[1]:
    st.metric("Records", f"{len(df):,}")

with summary_cols[2]:
    st.metric("Columns", f"{len(df.columns):,}")

with summary_cols[3]:
    numeric_count = len(df.select_dtypes(include="number").columns)
    st.metric("Numeric Columns", f"{numeric_count:,}")

# --------------------------------------------------
# KPI SECTION
# --------------------------------------------------

st.divider()
st.subheader("📈 Key Business Metrics")

try:
    kpis, detected = calculate_kpis(df)
except Exception as exc:
    kpis = {}
    detected = {}
    st.warning(f"Automatic KPI analysis could not be completed: {exc}")

if not isinstance(kpis, dict):
    kpis = {}

if not isinstance(detected, dict):
    detected = {}

if not kpis:
    st.info("No standard business metrics were automatically detected in this worksheet.")
else:
    kpi_items = list(kpis.items())
    columns = st.columns(min(4, max(1, len(kpi_items))))

    for index, (name, value) in enumerate(kpi_items):
        with columns[index % len(columns)]:
            try:
                if name == "Profit Margin":
                    display_value = f"{float(value):.1f}%"
                elif name in {"Records", "Units"}:
                    display_value = f"{float(value):,.0f}"
                else:
                    display_value = f"{float(value):,.2f}"

                st.metric(name, display_value)
            except (TypeError, ValueError):
                st.metric(name, str(value))

# --------------------------------------------------
# DETECTED BUSINESS STRUCTURE
# --------------------------------------------------

st.divider()
st.subheader("🔎 Automatically Detected Business Structure")

if detected:
    detection_df = pd.DataFrame(
        [
            {
                "Business Metric": str(key).replace("_", " ").title(),
                "Detected Column": value if value else "Not detected",
            }
            for key, value in detected.items()
        ]
    )

    st.dataframe(
        detection_df,
        use_container_width=True,
        hide_index=True,
    )
else:
    # Fallback detection so the dashboard remains useful even if the analyzer
    # does not return a detection dictionary.
    try:
        fallback_detected = detect_business_columns(df)

        if isinstance(fallback_detected, dict) and fallback_detected:
            detection_df = pd.DataFrame(
                [
                    {
                        "Business Metric": str(key).replace("_", " ").title(),
                        "Detected Column": value if value else "Not detected",
                    }
                    for key, value in fallback_detected.items()
                ]
            )
            st.dataframe(
                detection_df,
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No standard business columns were automatically detected.")
    except Exception:
        st.info("No standard business columns were automatically detected.")

# --------------------------------------------------
# CATEGORY ANALYSIS
# --------------------------------------------------

st.divider()
st.subheader("🏆 Revenue by Category")

try:
    dimension_analysis = create_dimension_analysis(df)
except Exception as exc:
    dimension_analysis = None
    st.warning(f"Category analysis could not be completed: {exc}")

if (
    isinstance(dimension_analysis, pd.DataFrame)
    and not dimension_analysis.empty
    and {"Category", "Revenue"}.issubset(dimension_analysis.columns)
):
    chart_data = dimension_analysis.head(20).copy()

    chart = px.bar(
        chart_data,
        x="Category",
        y="Revenue",
        title="Top Revenue Categories",
    )

    st.plotly_chart(
        chart,
        use_container_width=True,
    )

    st.dataframe(
        dimension_analysis,
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info(
        "No suitable category/revenue relationship was detected. "
        "Make sure the worksheet contains a category field and a revenue/sales field."
    )

# --------------------------------------------------
# BUSINESS INSIGHTS
# --------------------------------------------------

st.divider()
st.subheader("💡 Business Insights")

try:
    insights = generate_insights(df)
except Exception as exc:
    insights = []
    st.warning(f"Automatic insight generation could not be completed: {exc}")

if insights:
    if isinstance(insights, str):
        insights = [insights]

    for insight in insights:
        st.info(f"💡 {insight}")
else:
    st.info("Not enough business data for automatic insights.")

# --------------------------------------------------
# WHY FEATURE
# --------------------------------------------------

st.divider()
st.subheader("❓ Why?")

metric_options = []

if "Revenue" in kpis:
    metric_options.append("Revenue")

if "Profit" in kpis:
    metric_options.append("Profit")

# Keep these available even when the KPI detector did not identify them.
for option in ["Revenue", "Profit"]:
    if option not in metric_options:
        metric_options.append(option)

selected_metric = st.selectbox(
    "What do you want explained?",
    metric_options,
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

        if explanation:
            st.success(explanation)
        else:
            st.info("There is not enough information to explain this metric.")
    except Exception as exc:
        st.error(f"Metric explanation could not be generated: {exc}")

# --------------------------------------------------
# DATA QUALITY
# --------------------------------------------------

st.divider()
st.subheader("🧹 Data Quality Overview")

quality_cols = st.columns(3)

missing_cells = int(df.isna().sum().sum())
duplicate_rows = int(df.duplicated().sum())
total_cells = int(df.shape[0] * df.shape[1])

with quality_cols[0]:
    st.metric("Missing Cells", f"{missing_cells:,}")

with quality_cols[1]:
    st.metric("Duplicate Rows", f"{duplicate_rows:,}")

with quality_cols[2]:
    completeness = (
        ((total_cells - missing_cells) / total_cells) * 100
        if total_cells
        else 0
    )
    st.metric("Data Completeness", f"{completeness:.1f}%")

# --------------------------------------------------
# DATA PREVIEW + CSV EXPORT
# --------------------------------------------------

st.divider()
st.subheader("📋 Data Preview")

preview_limit = st.slider(
    "Rows to preview",
    min_value=10,
    max_value=min(500, max(10, len(df))),
    value=min(100, max(10, len(df))),
    step=10,
)

st.dataframe(
    df.head(preview_limit),
    use_container_width=True,
    hide_index=True,
)

csv_data = df.to_csv(index=False).encode("utf-8")

st.download_button(
    "⬇️ Download Current Sheet as CSV",
    data=csv_data,
    file_name=f"{selected_sheet}_business_data.csv",
    mime="text/csv",
)

# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.divider()
st.caption(
    "Excel Business Brain • Automated business analysis, KPIs, category analysis, insights and data-quality checks."
)
