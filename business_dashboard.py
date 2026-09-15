import streamlit as st
import pandas as pd
import plotly.express as px
from core.business_analyzer import (
    calculate_kpis, create_dimension_analysis, create_time_analysis,
    generate_insights, why_analysis, detect_business_columns,
    find_dimension_columns
)

st.set_page_config(page_title="Business Dashboard", page_icon="📊", layout="wide")

st.markdown("""
<style>
.block-container {max-width: 1400px; padding-top: 2rem; padding-bottom: 3rem;}
.hero {padding: 1.4rem 1.6rem; border: 1px solid rgba(255,255,255,.10); border-radius: 18px; background: linear-gradient(135deg, rgba(91,65,180,.22), rgba(20,25,45,.55)); margin-bottom: 1.2rem;}
.hero h1 {margin:0 0 .3rem 0; font-size:2.1rem;}
.hero p {margin:0; opacity:.72;}
.section-title {font-size:1.25rem; font-weight:700; margin:1.2rem 0 .7rem;}
.metric-card {border:1px solid rgba(255,255,255,.09); border-radius:16px; padding:1rem; background:rgba(255,255,255,.035);}
.small-label {font-size:.78rem; opacity:.62; text-transform:uppercase; letter-spacing:.06em;}
</style>
""", unsafe_allow_html=True)

if "workbook" not in st.session_state or not st.session_state.workbook:
    st.warning("Upload an Excel or CSV workbook from the main page first.")
    st.stop()

workbook = st.session_state.workbook
sheet_names = list(workbook.keys())

st.markdown("""
<div class="hero">
<h1>📊 Business Dashboard</h1>
<p>Turn spreadsheet data into clear financial and operational decisions.</p>
</div>
""", unsafe_allow_html=True)

selected_sheet = st.selectbox("Workbook sheet", sheet_names)
df = workbook[selected_sheet].copy()

st.caption(f"Analyzing: **{selected_sheet}**  ·  {len(df):,} records  ·  {len(df.columns):,} columns")

kpis, detected = calculate_kpis(df)

st.markdown('<div class="section-title">Key Business Metrics</div>', unsafe_allow_html=True)

if kpis:
    items = list(kpis.items())
    cols = st.columns(min(4, len(items)))
    for i, (name, value) in enumerate(items):
        with cols[i % len(cols)]:
            if name == "Profit Margin":
                display = f"{value:.1f}%"
            elif name in ["Records", "Units"]:
                display = f"{int(value):,}"
            else:
                display = f"{value:,.2f}"
            st.metric(name, display)
else:
    st.info("No standard business metrics were detected in this sheet.")

st.markdown('<div class="section-title">🔎 Detected Data Structure</div>', unsafe_allow_html=True)

detection_df = pd.DataFrame([
    {"Metric": key.title(), "Column": value if value else "Not detected"}
    for key, value in detected.items()
])
st.dataframe(detection_df, use_container_width=True, hide_index=True)

st.markdown('<div class="section-title">🏆 Revenue Analysis</div>', unsafe_allow_html=True)

dimensions = find_dimension_columns(df)
if dimensions and detected["revenue"]:
    selected_dimension = st.selectbox("Analyze revenue by", dimensions)
    analysis = create_dimension_analysis(df, selected_dimension)

    if analysis is not None and not analysis.empty:
        chart = px.bar(
            analysis.head(15),
            x="Category",
            y="Revenue",
            text_auto=".2s",
            title=f"Revenue by {selected_dimension}"
        )
        chart.update_layout(
            margin=dict(l=10, r=10, t=55, b=10),
            xaxis_title="",
            yaxis_title="Revenue",
            hovermode="x unified"
        )
        st.plotly_chart(chart, use_container_width=True)
        st.dataframe(analysis, use_container_width=True, hide_index=True)
else:
    st.info("No suitable categorical revenue relationship was detected in this sheet.")

time_analysis = create_time_analysis(df)
if time_analysis is not None and len(time_analysis) >= 2:
    st.markdown('<div class="section-title">📈 Revenue Trend</div>', unsafe_allow_html=True)
    trend = px.line(time_analysis, x="Period", y="Revenue", markers=True, title="Monthly Revenue Trend")
    trend.update_layout(margin=dict(l=10, r=10, t=55, b=10), xaxis_title="", yaxis_title="Revenue")
    st.plotly_chart(trend, use_container_width=True)

st.markdown('<div class="section-title">💡 Business Insights</div>', unsafe_allow_html=True)
insights = generate_insights(df)
if insights:
    for insight in insights:
        st.info(insight)
else:
    st.info("Not enough business data for automatic insights.")

st.markdown('<div class="section-title">❓ Why?</div>', unsafe_allow_html=True)
metric = st.selectbox("Explain this metric", ["Revenue", "Profit"])
if st.button("🔍 Explain Metric", type="primary"):
    st.success(why_analysis(df, metric))

st.markdown('<div class="section-title">📋 Data Preview</div>', unsafe_allow_html=True)
st.dataframe(df.head(100), use_container_width=True)
