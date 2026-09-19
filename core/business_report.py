"""
Business reporting helpers for Excel Business Brain.

Provides:
- PDF executive business report generation
- Excel business summary generation
- Safe, dependency-light formatting around the existing analyzer functions
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Any, Mapping

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from core.business_analyzer import (
    calculate_kpis,
    detect_business_columns,
    generate_insights,
)
from core.data_cleaner import analyze_data_health


def _safe_float(value: Any) -> float | None:
    try:
        if pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_value(name: str, value: Any) -> str:
    number = _safe_float(value)
    if number is None:
        return str(value)

    if name.lower() == "profit margin":
        return f"{number:.1f}%"
    if name.lower() in {"records", "units"}:
        return f"{int(number):,}"
    return f"{number:,.2f}"


def _quality_summary(df: pd.DataFrame) -> dict[str, Any]:
    report = analyze_data_health(df)
    return {
        "score": report.get("score", 100),
        "missing_cells": report.get("missing_cells", 0),
        "duplicates": report.get("duplicates", 0),
        "blank_rows": report.get("blank_rows", 0),
        "type_warnings": report.get("type_warnings", 0),
    }


def _detected_rows(detected: Mapping[str, Any]) -> list[list[str]]:
    rows = [["Business field", "Detected column"]]
    for key, value in detected.items():
        rows.append([str(key).replace("_", " ").title(), str(value or "Not detected")])
    return rows


def build_business_summary_xlsx(
    workbook: Mapping[str, pd.DataFrame],
    filename: str | None = None,
) -> bytes:
    """
    Build a professional Excel summary workbook containing:
    - Executive Summary
    - Data Quality
    - Detected Structure
    - Business Insights
    - Sheet Summary
    """
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        summary_rows: list[dict[str, Any]] = []
        quality_rows: list[dict[str, Any]] = []
        detection_rows: list[dict[str, Any]] = []
        insight_rows: list[dict[str, Any]] = []

        for sheet_name, df in workbook.items():
            kpis, detected = calculate_kpis(df)
            quality = _quality_summary(df)

            summary = {
                "Sheet": sheet_name,
                "Rows": len(df),
                "Columns": len(df.columns),
            }
            for key, value in (kpis or {}).items():
                summary[key] = value
            summary_rows.append(summary)

            quality_rows.append(
                {
                    "Sheet": sheet_name,
                    "Health Score": quality["score"],
                    "Missing Cells": quality["missing_cells"],
                    "Duplicate Rows": quality["duplicates"],
                    "Blank Rows": quality["blank_rows"],
                    "Type Warnings": quality["type_warnings"],
                }
            )

            for key, value in detected.items():
                detection_rows.append(
                    {
                        "Sheet": sheet_name,
                        "Business Field": str(key).replace("_", " ").title(),
                        "Detected Column": value or "Not detected",
                    }
                )

            for insight in generate_insights(df) or []:
                insight_rows.append({"Sheet": sheet_name, "Insight": str(insight)})

        pd.DataFrame(summary_rows).to_excel(
            writer, sheet_name="Executive Summary", index=False
        )
        pd.DataFrame(quality_rows).to_excel(
            writer, sheet_name="Data Quality", index=False
        )
        pd.DataFrame(detection_rows).to_excel(
            writer, sheet_name="Detected Structure", index=False
        )
        pd.DataFrame(insight_rows or [{"Sheet": "", "Insight": "No automatic insights generated."}]).to_excel(
            writer, sheet_name="Business Insights", index=False
        )

        sheet_rows = []
        for sheet_name, df in workbook.items():
            sheet_rows.append(
                {
                    "Sheet": sheet_name,
                    "Rows": len(df),
                    "Columns": len(df.columns),
                    "Missing Cells": int(df.isna().sum().sum()),
                    "Duplicate Rows": int(df.duplicated().sum()),
                }
            )
        pd.DataFrame(sheet_rows).to_excel(
            writer, sheet_name="Workbook Overview", index=False
        )

        for ws in writer.book.worksheets:
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions

            for cell in ws[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="1F2937")
                cell.alignment = Alignment(horizontal="center")

            for column_cells in ws.columns:
                max_len = 0
                column_index = column_cells[0].column
                for cell in column_cells[:100]:
                    value = "" if cell.value is None else str(cell.value)
                    max_len = max(max_len, len(value))
                ws.column_dimensions[get_column_letter(column_index)].width = min(
                    max(max_len + 2, 12), 42
                )

            ws.sheet_view.showGridLines = False

    return output.getvalue()


def build_business_report_pdf(
    workbook: Mapping[str, pd.DataFrame],
    filename: str | None = None,
) -> bytes:
    """
    Generate a clean executive PDF report for all workbook sheets.
    The report intentionally uses the existing business analyzer rather
    than inventing metrics when a field is not detected.
    """
    output = io.BytesIO()

    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title="Excel Business Brain — Business Report",
        author="Excel Business Brain",
    )

    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontSize=22,
        leading=26,
        alignment=TA_LEFT,
        spaceAfter=5 * mm,
    )
    subtitle = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#64748B"),
        spaceAfter=7 * mm,
    )
    heading = ParagraphStyle(
        "ReportHeading",
        parent=styles["Heading2"],
        fontSize=14,
        leading=18,
        spaceBefore=5 * mm,
        spaceAfter=3 * mm,
    )
    body = ParagraphStyle(
        "ReportBody",
        parent=styles["BodyText"],
        fontSize=9.5,
        leading=14,
        spaceAfter=2 * mm,
    )

    story = [
        Paragraph("Excel Business Brain", title),
        Paragraph(
            "Executive business report generated from the uploaded workbook.",
            subtitle,
        ),
        Paragraph(
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            body,
        ),
    ]

    for sheet_name, df in workbook.items():
        kpis, detected = calculate_kpis(df)
        quality = _quality_summary(df)
        insights = generate_insights(df) or []

        story.append(Paragraph(f"Sheet: {sheet_name}", heading))
        story.append(
            Paragraph(
                f"{len(df):,} records · {len(df.columns):,} columns",
                body,
            )
        )

        if kpis:
            kpi_rows = [["Metric", "Value"]]
            for name, value in kpis.items():
                kpi_rows.append([str(name), _format_value(str(name), value)])

            table = Table(kpi_rows, colWidths=[70 * mm, 55 * mm], repeatRows=1)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
                            colors.white,
                            colors.HexColor("#F8FAFC"),
                        ]),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 7),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ]
                )
            )
            story.append(table)
        else:
            story.append(Paragraph("No standard business KPIs were detected.", body))

        story.append(Paragraph("Data Quality", heading))
        quality_rows = [
            ["Health Score", str(quality["score"])],
            ["Missing Cells", str(quality["missing_cells"])],
            ["Duplicate Rows", str(quality["duplicates"])],
            ["Blank Rows", str(quality["blank_rows"])],
            ["Type Warnings", str(quality["type_warnings"])],
        ]
        quality_table = Table(quality_rows, colWidths=[70 * mm, 55 * mm])
        quality_table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F1F5F9")),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(quality_table)

        story.append(Paragraph("Detected Business Structure", heading))
        detected_table = Table(_detected_rows(detected), colWidths=[70 * mm, 75 * mm], repeatRows=1)
        detected_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(detected_table)

        story.append(Paragraph("Business Insights", heading))
        if insights:
            for insight in insights:
                story.append(Paragraph(f"- {str(insight)}", body))
        else:
            story.append(Paragraph("No automatic insights were generated for this sheet.", body))

        story.append(Spacer(1, 4 * mm))

    story.append(Paragraph(
        "Excel Business Brain - automated KPIs, business analysis, data-quality checks and recommendations.",
        subtitle,
    ))

    doc.build(story)
    return output.getvalue()
