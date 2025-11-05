"""
PDF generation for BNG quotes
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib import colors

from .config import get_settings


def generate_quote_pdf(
    promoter_slug: str,
    contact_email: str,
    site_address: Optional[str],
    site_postcode: Optional[str],
    client_reference: Optional[str],
    quote_total: float,
    allocation_results: Dict[str, Any],
    target_lpa: Optional[str] = None,
    target_nca: Optional[str] = None
) -> bytes:
    """
    Generate a PDF quote document
    
    Args:
        promoter_slug: Promoter identifier
        contact_email: Client contact email
        site_address: Site address
        site_postcode: Site postcode
        client_reference: Client reference
        quote_total: Total quote amount
        allocation_results: Optimization results
        target_lpa: Local Planning Authority
        target_nca: National Character Area
    
    Returns:
        PDF content as bytes
    """
    settings = get_settings()
    
    # Create PDF buffer
    buffer = BytesIO()
    
    # Create PDF document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )
    
    # Container for PDF elements
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#667eea'),
        spaceAfter=12,
        alignment=TA_CENTER
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2d3748'),
        spaceAfter=10,
        spaceBefore=16
    )
    normal_style = styles['Normal']
    
    # Title
    elements.append(Paragraph("Biodiversity Net Gain Quote", title_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Quote details
    quote_date = datetime.now().strftime("%d %B %Y")
    validity_date = (datetime.now() + timedelta(days=settings.quote_validity_days)).strftime("%d %B %Y")
    
    details_data = [
        ['Quote Date:', quote_date],
        ['Valid Until:', validity_date],
        ['Promoter:', promoter_slug],
        ['Contact:', contact_email],
    ]
    
    if client_reference:
        details_data.append(['Reference:', client_reference])
    
    if site_address:
        details_data.append(['Site Address:', site_address])
    
    if site_postcode:
        details_data.append(['Postcode:', site_postcode])
    
    if target_lpa:
        details_data.append(['LPA:', target_lpa])
    
    if target_nca:
        details_data.append(['NCA:', target_nca])
    
    details_table = Table(details_data, colWidths=[1.5*inch, 4.5*inch])
    details_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#4a5568')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#2d3748')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    
    elements.append(details_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Quote Summary
    elements.append(Paragraph("Quote Summary", heading_style))
    
    # Calculate VAT
    subtotal = quote_total
    vat_amount = subtotal * settings.vat_rate
    total_with_vat = subtotal + vat_amount
    
    summary_data = [
        ['Description', 'Amount'],
        ['BNG Units Total', f'£{subtotal:,.2f}'],
        [f'VAT ({int(settings.vat_rate * 100)}%)', f'£{vat_amount:,.2f}'],
        ['Total (inc. VAT)', f'£{total_with_vat:,.2f}'],
    ]
    
    summary_table = Table(summary_data, colWidths=[4.5*inch, 1.5*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -2), 10),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('LINEBELOW', (0, -2), (-1, -2), 1, colors.HexColor('#cbd5e0')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 12),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#667eea')),
        ('TOPPADDING', (0, -1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -2), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    
    elements.append(summary_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Terms and Conditions
    elements.append(Paragraph("Terms & Conditions", heading_style))
    
    terms = [
        f"This quote is valid until {validity_date}.",
        "Prices are subject to availability at the time of order.",
        "Payment terms: 30 days from invoice date.",
        "All prices include VAT at the current rate.",
        "Units will be allocated from our partner banks based on availability and location.",
    ]
    
    for term in terms:
        elements.append(Paragraph(f"• {term}", normal_style))
        elements.append(Spacer(1, 0.1*inch))
    
    elements.append(Spacer(1, 0.2*inch))
    
    # Footer
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#718096'),
        alignment=TA_CENTER
    )
    
    elements.append(Spacer(1, 0.3*inch))
    elements.append(Paragraph(
        "Thank you for your business. For questions, please contact us at the email above.",
        footer_style
    ))
    
    # Build PDF
    doc.build(elements)
    
    # Get PDF content
    pdf_content = buffer.getvalue()
    buffer.close()
    
    return pdf_content
