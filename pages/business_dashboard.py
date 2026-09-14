import streamlit as st
import pandas as pd
import plotly.express as px

from core.business_analyzer import (
    calculate_kpis,
    create_dimension_analysis,
    generate_insights,
    why_analysis,
    detect_business_columns
)


st.title("📊 Business Dashboard")

if "workbook" not in st.session_state:

    st.warning(
        "Please upload a workbook from the main page first."
    )

    st.stop()


workbook = st.session_state.workbook

if not workbook:

    st.warning(
        "Please upload a workbook first."
    )

    st.stop()


sheet_names = list(
    workbook.keys()
)

selected_sheet = st.selectbox(
    "Select sheet",
    sheet_names
)

df = workbook[
    selected_sheet
].copy()


# --------------------------------------------------
# KPI SECTION
# --------------------------------------------------

st.subheader("Key Business Metrics")

kpis, detected = calculate_kpis(
    df
)

if not kpis:

    st.info(
        "No standard business metrics were "
        "automatically detected in this sheet."
    )

else:

    kpi_items = list(
        kpis.items()
    )

    columns = st.columns(
        min(4, len(kpi_items))
    )

    for index, (
        name,
        value
    ) in enumerate(kpi_items):

        with columns[
            index % len(columns)
        ]:

            if name == "Profit Margin":

                st.metric(
                    name,
                    f"{value:.1f}%"
                )

            elif name == "Records":

                st.metric(
                    name,
                    f"{int(value):,}"
                )

            elif name == "Units":

                st.metric(
                    name,
                    f"{value:,.0f}"
                )

            else:

                st.metric(
                    name,
                    f"{value:,.2f}"
                )


# --------------------------------------------------
# DETECTED BUSINESS STRUCTURE
# --------------------------------------------------

st.divider()

st.subheader(
    "🔎 Automatically Detected Business Structure"
)

detection_df = pd.DataFrame(
    [
        {
            "Business Metric": key.title(),
            "Detected Column": value or "Not detected"
        }
        for key, value in detected.items()
    ]
)

st.dataframe(
    detection_df,
    use_container_width=True,
    hide_index=True
)


# --------------------------------------------------
# CATEGORY ANALYSIS
# --------------------------------------------------

st.divider()

st.subheader(
    "🏆 Revenue by Category"
)

dimension_analysis = (
    create_dimension_analysis(df)
)

if dimension_analysis is not None:

    chart = px.bar(
        dimension_analysis.head(20),
        x="Category",
        y="Revenue",
        title="Top Revenue Categories"
    )

    st.plotly_chart(
        chart,
        use_container_width=True
    )

    st.dataframe(
        dimension_analysis,
        use_container_width=True,
        hide_index=True
    )

else:

    st.info(
        "No suitable category/revenue relationship "
        "was detected."
    )


# --------------------------------------------------
# INSIGHTS
# --------------------------------------------------

st.divider()

st.subheader(
    "💡 Business Insights"
)

insights = generate_insights(
    df
)

if insights:

    for insight in insights:

        st.info(
            f"💡 {insight}"
        )

else:

    st.info(
        "Not enough business data for automatic insights."
    )


# --------------------------------------------------
# WHY FEATURE
# --------------------------------------------------

st.divider()

st.subheader(
    "❓ Why?"
)

metric_options = [
    "Revenue",
    "Profit"
]

selected_metric = st.selectbox(
    "What do you want explained?",
    metric_options
)

if st.button(
    "🔍 Explain This Metric",
    type="primary"
):

    explanation = why_analysis(
        df,
        selected_metric
    )

    st.success(
        explanation
    )


# --------------------------------------------------
# DATA PREVIEW
# --------------------------------------------------

st.divider()

st.subheader(
    "📋 Data Preview"
)

st.dataframe(
    df.head(100),
    use_container_width=True
)
