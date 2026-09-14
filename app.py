import io
import streamlit as st
import pandas as pd

from core.workbook_reader import analyze_workbook, build_workbook_bytes
from core.data_cleaner import analyze_data_health, clean_dataframe
from core.formula_analyzer import analyze_formulas, apply_safe_formula_fixes

st.set_page_config(
    page_title="Excel Business Brain",
    page_icon="🧠",
    layout="wide",
)

st.markdown("""
<style>
.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
}
.main-title {
    font-size: 2.4rem;
    font-weight: 800;
    margin-bottom: .2rem;
}
.subtitle {
    color: #64748b;
    font-size: 1.05rem;
    margin-bottom: 1.5rem;
}
.issue {
    padding: .8rem 1rem;
    border-radius: 10px;
    margin: .4rem 0;
    background: #f8fafc;
}
</style>
""", unsafe_allow_html=True)

if "workbook" not in st.session_state:
    st.session_state.workbook = None

if "filename" not in st.session_state:
    st.session_state.filename = None

if "cleaned" not in st.session_state:
    st.session_state.cleaned = {}

st.markdown(
    '<div class="main-title">🧠 Excel Business Brain</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">Turn messy spreadsheets into business-ready decisions.</div>',
    unsafe_allow_html=True
)

uploaded = st.file_uploader(
    "Upload an Excel or CSV workbook",
    type=["xlsx", "xls", "csv"],
    help="For best results, upload an .xlsx workbook."
)

if uploaded:

    if st.session_state.filename != uploaded.name:

        try:

            data = uploaded.getvalue()

            if uploaded.name.lower().endswith(".csv"):

                df = pd.read_csv(io.BytesIO(data))

                st.session_state.workbook = {
                    "Sheet1": df
                }

            else:

                st.session_state.workbook = pd.read_excel(
                    io.BytesIO(data),
                    sheet_name=None
                )

            st.session_state.filename = uploaded.name
            st.session_state.cleaned = {}

        except Exception as exc:

            st.error(f"Could not read this file: {exc}")
            st.stop()

if not st.session_state.workbook:

    st.info("Upload a workbook above to begin the analysis.")
    st.stop()

workbook = st.session_state.workbook

st.success(
    f"Loaded **{st.session_state.filename}** — "
    f"{len(workbook)} sheet(s)."
)

total_rows = sum(
    len(df) for df in workbook.values()
)

total_columns = sum(
    len(df.columns) for df in workbook.values()
)

c1, c2, c3 = st.columns(3)

c1.metric(
    "Sheets",
    len(workbook)
)

c2.metric(
    "Total Rows",
    f"{total_rows:,}"
)

c3.metric(
    "Total Columns",
    f"{total_columns:,}"
)

tabs = st.tabs([
    "📋 Workbook",
    "🧹 Data Health",
    "🛡️ Formula Guardian",
    "📥 Export"
])

# --------------------------------------------------
# WORKBOOK
# --------------------------------------------------

with tabs[0]:

    st.subheader("Workbook overview")

    for sheet_name, df in workbook.items():

        with st.expander(
            f"{sheet_name} — "
            f"{len(df):,} rows × {len(df.columns):,} columns"
        ):

            st.dataframe(
                df.head(100),
                use_container_width=True
            )

            profile = analyze_workbook(df)

            st.write("**Detected columns**")

            st.dataframe(
                pd.DataFrame(profile),
                use_container_width=True
            )

# --------------------------------------------------
# DATA HEALTH
# --------------------------------------------------

with tabs[1]:

    st.subheader("Data Health")

    all_health = []

    for sheet_name, df in workbook.items():

        report = analyze_data_health(df)

        report["sheet"] = sheet_name

        all_health.append(report)

    health_df = pd.DataFrame(all_health)

    avg_score = (
        round(health_df["score"].mean())
        if not health_df.empty
        else 100
    )

    st.metric(
        "Overall Data Health",
        f"{avg_score}/100"
    )

    for _, row in health_df.iterrows():

        st.markdown(
            f"### {row['sheet']} — {row['score']}/100"
        )

        cols = st.columns(4)

        cols[0].metric(
            "Duplicates",
            row["duplicates"]
        )

        cols[1].metric(
            "Missing Cells",
            row["missing_cells"]
        )

        cols[2].metric(
            "Blank Rows",
            row["blank_rows"]
        )

        cols[3].metric(
            "Type Warnings",
            row["type_warnings"]
        )

        if row["issues"]:

            for issue in row["issues"]:

                st.markdown(
                    f'<div class="issue">⚠️ {issue}</div>',
                    unsafe_allow_html=True
                )

        else:

            st.success(
                "No major data-health issues detected."
            )

    if st.button(
        "🧹 Clean Safe Data Issues",
        type="primary"
    ):

        st.session_state.cleaned = {
            name: clean_dataframe(df.copy())
            for name, df in workbook.items()
        }

        st.success(
            "Safe cleaning completed. "
            "Review the Export tab before downloading."
        )

# --------------------------------------------------
# FORMULA GUARDIAN
# --------------------------------------------------

with tabs[2]:

    st.subheader("Formula Guardian")

    st.caption(
        "Checks formula errors, missing formulas in "
        "formula-heavy columns, and formula inconsistencies."
    )

    reports = []

    for sheet_name, df in workbook.items():

        report = analyze_formulas(df)

        report["sheet"] = sheet_name

        reports.append(report)

    formula_df = pd.DataFrame(reports)

    total_issues = (
        int(formula_df["issues"].sum())
        if not formula_df.empty
        else 0
    )

    total_formulas = (
        int(formula_df["formula_cells"].sum())
        if not formula_df.empty
        else 0
    )

    c1, c2 = st.columns(2)

    c1.metric(
        "Formula Cells",
        f"{total_formulas:,}"
    )

    c2.metric(
        "Issues Found",
        f"{total_issues:,}"
    )

    for _, row in formula_df.iterrows():

        st.markdown(
            f"### {row['sheet']}"
        )

        if row["details"]:

            for detail in row["details"]:

                st.warning(detail)

        else:

            st.success(
                "No formula-structure problems detected."
            )

    if st.button(
        "🔧 Apply Safe Formula Fixes"
    ):

        fixed = {}
        fix_count = 0

        for name, df in workbook.items():

            new_df, count = apply_safe_formula_fixes(
                df.copy()
            )

            fixed[name] = new_df
            fix_count += count

        st.session_state.cleaned = fixed

        st.success(
            f"Applied {fix_count} safe formula fix(es)."
        )

# --------------------------------------------------
# EXPORT
# --------------------------------------------------

with tabs[3]:

    st.subheader("Export")

    export_book = (
        st.session_state.cleaned
        or workbook
    )

    st.write(
        "Download the original workbook or the "
        "version produced by the safe cleaning/fix actions."
    )

    output = build_workbook_bytes(
        export_book
    )

    base = st.session_state.filename.rsplit(
        ".",
        1
    )[0]

    st.download_button(
        "📥 Download Excel Workbook",
        data=output,
        file_name=f"{base}_business_brain.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        type="primary"
    )

    st.divider()

    st.caption(
        "Coming next: automatic KPI dashboard, AI insights, "
        "anomaly detection, forecasting and PDF business reports."
    )
