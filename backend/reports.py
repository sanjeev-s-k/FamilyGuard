import io
from datetime import datetime
from typing import Dict, Any
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable


def generate_transaction_pdf(report_data: Dict[str, Any]) -> io.BytesIO:
    """
    Generates a PDF document for FamilyGuard Transaction Receipt & AI Monitoring Report.
    Labelled as an official transaction receipt and AI monitoring report, not a payment invoice.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    # Custom styles
    brand_style = ParagraphStyle(
        'BrandTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=22,
        textColor=colors.HexColor('#003087'),  # PayPal Deep Blue
        spaceAfter=4
    )

    tagline_style = ParagraphStyle(
        'Tagline',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=10,
        textColor=colors.HexColor('#0070E0'),  # PayPal Electric Blue
        spaceAfter=15
    )

    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        textColor=colors.HexColor('#001C64'),
        spaceAfter=15
    )

    section_header = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        textColor=colors.HexColor('#003087'),
        spaceBefore=10,
        spaceAfter=8
    )

    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        textColor=colors.HexColor('#1F2937'),
        leading=14
    )

    story = []

    # Header
    story.append(Paragraph("PayPal Developer Sandbox • FamilyGuard", brand_style))
    story.append(Paragraph("Cross-Border Parental Payment Monitoring System • 1 USD = 85.00 INR", tagline_style))
    story.append(Paragraph(
        "OFFICIAL AUDIT NOTICE: This record verifies cross-border overseas student expenditure and AI safety risk telemetry. "
        "Generated via PayPal Sandbox REST API environment.",
        disclaimer_style
    ))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#0070E0'), spaceAfter=15))

    # Transaction Overview Table
    currency = report_data.get("currency", "USD")
    amount = report_data.get("transaction_amount", 0.0)
    risk_level = report_data.get("risk_assessment", "LOW")
    inr_amt = amount * 85.0 if currency == "USD" else amount

    risk_badge_color = colors.HexColor('#10B981')  # Green
    if risk_level == "MEDIUM":
        risk_badge_color = colors.HexColor('#F59E0B')  # Amber
    elif risk_level == "HIGH":
        risk_badge_color = colors.HexColor('#EF4444')  # Red

    tx_table_data = [
        [
            Paragraph("<b>Transaction Code:</b>", body_style),
            Paragraph(f"<b>{report_data.get('transaction_id', 'N/A')}</b>", body_style),
            Paragraph("<b>Date & Time:</b>", body_style),
            Paragraph(str(report_data.get("transaction_date", "N/A")), body_style)
        ],
        [
            Paragraph("<b>Student (Abroad):</b>", body_style),
            Paragraph(str(report_data.get("child_name", "Arjun")), body_style),
            Paragraph("<b>Payment Status:</b>", body_style),
            Paragraph(f"<b>{report_data.get('payment_status', 'COMPLETED')}</b>", body_style)
        ],
        [
            Paragraph("<b>Merchant Name:</b>", body_style),
            Paragraph(str(report_data.get("merchant", "N/A")), body_style),
            Paragraph("<b>Category:</b>", body_style),
            Paragraph(str(report_data.get("category", "Shopping")), body_style)
        ],
        [
            Paragraph("<b>Amount (USD / INR):</b>", body_style),
            Paragraph(f"<b>${amount:,.2f} USD (₹{inr_amt:,.2f} INR)</b>", body_style),
            Paragraph("<b>Payment Gateway:</b>", body_style),
            Paragraph("PayPal Sandbox REST API", body_style)
        ]
    ]

    tx_table = Table(tx_table_data, colWidths=[130, 140, 120, 140])
    tx_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(tx_table)
    story.append(Spacer(1, 15))

    # Spending Limits & Allowance Impact Table
    story.append(Paragraph("Parental Spending Allowance Impact", section_header))
    limits_table_data = [
        [
            Paragraph("<b>Daily Spending Prior:</b>", body_style),
            Paragraph(f"{currency} {report_data.get('daily_spending_before', 0.0):,.2f}", body_style),
            Paragraph("<b>Configured Daily Limit:</b>", body_style),
            Paragraph(f"{currency} {report_data.get('daily_limit', 500.0):,.2f}", body_style)
        ],
        [
            Paragraph("<b>Daily Spending After:</b>", body_style),
            Paragraph(f"<b>{currency} {report_data.get('daily_spending_after', 0.0):,.2f}</b>", body_style),
            Paragraph("<b>Remaining Allowance:</b>", body_style),
            Paragraph(f"<b>{currency} {report_data.get('remaining_spending_allowance', 0.0):,.2f}</b>", body_style)
        ]
    ]
    limits_table = Table(limits_table_data, colWidths=[130, 140, 130, 130])
    limits_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#EFF6FF')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#BFDBFE')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(limits_table)
    story.append(Spacer(1, 15))

    # AI Transaction Assessment Section
    story.append(Paragraph("AI Safety & Risk Assessment Engine", section_header))
    ai_box_data = [
        [
            Paragraph("<b>Risk Classification:</b>", body_style),
            Paragraph(f"<b><font color='{risk_badge_color.hexval()}'>{risk_level}</font></b>", body_style),
            Paragraph("<b>Requires Review:</b>", body_style),
            Paragraph("YES" if report_data.get("requires_review") else "NO", body_style)
        ],
        [
            Paragraph("<b>AI Explanation:</b>", body_style),
            Paragraph(str(report_data.get("ai_explanation", "Standard verified transaction.")), body_style),
            Paragraph("", body_style),
            Paragraph("", body_style)
        ],
        [
            Paragraph("<b>Spending Summary:</b>", body_style),
            Paragraph(str(report_data.get("ai_spending_summary", "Within normal spending limits.")), body_style),
            Paragraph("", body_style),
            Paragraph("", body_style)
        ],
        [
            Paragraph("<b>Parent Guidance:</b>", body_style),
            Paragraph(str(report_data.get("ai_recommendation", "No action needed.")), body_style),
            Paragraph("", body_style),
            Paragraph("", body_style)
        ]
    ]
    ai_table = Table(ai_box_data, colWidths=[120, 410, 0, 0])
    ai_table.setStyle(TableStyle([
        ('SPAN', (1, 1), (3, 1)),
        ('SPAN', (1, 2), (3, 2)),
        ('SPAN', (1, 3), (3, 3)),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F3F4F6')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
    ]))
    story.append(ai_table)
    story.append(Spacer(1, 25))

    # Footer note
    footer_text = (
        f"Generated automatically by FamilyGuard Parental Monitoring Platform on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}. "
        "Cryptographically logged and verified in parent financial audit vault."
    )
    story.append(Paragraph(footer_text, ParagraphStyle('Footer', parent=styles['Italic'], fontSize=8, textColor=colors.HexColor('#9CA3AF'))))

    doc.build(story)
    buffer.seek(0)
    return buffer
