"""
AtlasMind - Corporate PDF Report Exporter
Generates executive-branded PDF summaries of query answers and policy citations
using ReportLab.
"""

import io
from datetime import datetime
from typing import List, Dict, Any

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from src.config import EXPORTS_DIR


def generate_query_pdf(query_text: str, answer_text: str, citations: List[Dict[str, Any]], 
                       user_role: str, language: str, latency_ms: int) -> bytes:
    """Generate corporate-branded PDF document byte stream."""
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
    
    # Custom Brand Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#ED1C24") # Honda Red
    )
    subtitle_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#1E2229") # Dark Slate
    )
    meta_style = ParagraphStyle(
        'DocMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#718096")
    )
    section_h2 = ParagraphStyle(
        'SectionH2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1E2229"),
        spaceBefore=8,
        spaceAfter=4
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#1A202C")
    )
    quote_style = ParagraphStyle(
        'DocQuote',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#2D3748")
    )
    
    elements = []
    
    # 1. Header Banner
    elements.append(Paragraph("ATLAS HONDA LIMITED", title_style))
    elements.append(Paragraph("AtlasMind – Internal AI Knowledge Assistant | Verification Dossier", subtitle_style))
    elements.append(Paragraph("Mother Plant: F-36, Estate Avenue, S.I.T.E., Karachi – 75730, Pakistan", meta_style))
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#ED1C24"), spaceAfter=12))
    
    # 2. Metadata Grid
    meta_data = [
        [
            Paragraph(f"<b>Query Timestamp:</b> {datetime.now().strftime('%d-%b-%Y %H:%M:%S')}", body_style),
            Paragraph(f"<b>User Persona / Role:</b> {user_role}", body_style)
        ],
        [
            Paragraph(f"<b>System Retrieval Latency:</b> {latency_ms} ms", body_style),
            Paragraph(f"<b>Language Selection:</b> {language}", body_style)
        ]
    ]
    meta_table = Table(meta_data, colWidths=[260, 260])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8F9FA")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 12))
    
    # 3. Employee Inquired Question
    elements.append(Paragraph("INQUIRED QUESTION / PROMPT", section_h2))
    elements.append(Paragraph(f"<b>\"{query_text}\"</b>", body_style))
    elements.append(Spacer(1, 10))
    
    # 4. Verified Policy Guidance
    elements.append(Paragraph("VERIFIED CORPORATE POLICY GUIDANCE", section_h2))
    
    # Clean and convert markdown safely for ReportLab
    import re
    import html
    
    # Process line by line
    for raw_line in answer_text.split("\n"):
        line = raw_line.strip()
        if not line:
            elements.append(Spacer(1, 3))
            continue
            
        # Strip headers
        line = re.sub(r"^#+\s*", "", line)
        # Escape XML characters first
        line = html.escape(line)
        # Convert escaped bold tags back: **text** -> <b>text</b>
        line = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", line)
        # Convert `code` to font
        line = re.sub(r"`(.*?)`", r"<font face='Courier'>\1</font>", line)
        
        # Handle bullet points
        if line.startswith("- ") or line.startswith("* "):
            bullet_text = line[2:]
            elements.append(Paragraph(f"&bull; {bullet_text}", body_style))
        elif line.startswith("&gt; "):
            quote_text = line[5:]
            elements.append(Paragraph(quote_text, quote_style))
        else:
            elements.append(Paragraph(line, body_style))
            
        elements.append(Spacer(1, 2))
            
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E2E8F0"), spaceAfter=10))
    
    # 5. Grounded Citations & Audit Sources
    elements.append(Paragraph("OFFICIAL AUDIT SOURCES & DOCUMENT CITATIONS", section_h2))
    if citations:
        citation_rows = [["Doc ID", "Official Policy Name", "Section Reference", "Confidence"]]
        for c in citations:
            citation_rows.append([
                c.get("doc_id", "N/A"),
                c.get("doc_title", "N/A")[:32],
                c.get("section_title", "N/A")[:30],
                f"{int(c.get('score', 0) * 100)}%"
            ])
        cite_table = Table(citation_rows, colWidths=[65, 200, 200, 55])
        cite_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E2229")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (3, 0), (3, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F9FA")]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(cite_table)
    else:
        elements.append(Paragraph("No direct citations required.", quote_style))
        
    elements.append(Spacer(1, 20))
    
    # 6. Legal / Demonstration Disclaimer Footer
    footer_text = (
        "CONFIDENTIAL & PROPRIETARY – ATLAS HONDA LIMITED. "
        "Generated via AtlasMind RAG Platform Prototype. "
        "Complies with Sindh Factories Act, ISO 14001, and ISO 45001 governance standards. "
        "For official regulatory filings, cross-reference hardcopy files in Central HR & Legal Repository."
    )
    elements.append(Paragraph(footer_text, meta_style))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
