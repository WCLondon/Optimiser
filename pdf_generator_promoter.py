"""
PDF Generator for Promoter Quote Forms
Generates professional PDF quotes using client report table from app.py
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
import pandas as pd
from datetime import datetime
from typing import Optional


def generate_quote_pdf(
    client_name: str,
    reference_number: str,
    site_location: str,
    quote_total: float,
    admin_fee: float,
    report_df: pd.DataFrame,
    email_html: str,
    promoter_name: Optional[str] = None,
    contact_email: Optional[str] = None,
    notes: Optional[str] = None
) -> bytes:
    """
    Generate a professional PDF quote document
    
    Args:
        client_name: Client name
        reference_number: Reference number
        site_location: Site location
        quote_total: Quote total (excluding admin fee)
        admin_fee: Admin fee
        report_df: Client report dataframe from generate_client_report_table_fixed
        email_html: Email HTML body (contains formatted table)
        promoter_name: Optional promoter name
        contact_email: Optional contact email
        notes: Optional notes
    
    Returns:
        PDF file content as bytes
    """
    buffer = BytesIO()
    
    # Create PDF document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=50
    )
    
    # Container for PDF elements
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#2E7D32'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2E7D32'),
        spaceAfter=12,
        spaceBefore=12
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=10
    )
    
    small_style = ParagraphStyle(
        'Small',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.grey
    )
    
    # Title
    elements.append(Paragraph("BNG UNITS QUOTE", title_style))
    elements.append(Spacer(1, 0.3*inch))
    
    # Company info
    elements.append(Paragraph("<b>Wild Capital</b>", body_style))
    elements.append(Paragraph("National supplier of BNG Units and environmental mitigation credits", body_style))
    elements.append(Spacer(1, 0.3*inch))
    
    # Quote details header
    quote_data = [
        ['Quote Reference:', reference_number],
        ['Client Name:', client_name],
        ['Site Location:', site_location],
        ['Quote Date:', datetime.now().strftime('%d %B %Y')],
    ]
    
    if promoter_name:
        quote_data.append(['Promoter:', promoter_name])
    
    if contact_email:
        quote_data.append(['Contact Email:', contact_email])
    
    quote_table = Table(quote_data, colWidths=[2*inch, 4*inch])
    quote_table.setStyle(TableStyle([
        ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 10),
        ('FONT', (1, 0), (1, -1), 'Helvetica', 10),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(quote_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # About Us section
    elements.append(Paragraph("<b>About Us</b>", heading_style))
    elements.append(Paragraph(
        "Wild Capital is a national supplier of BNG Units and environmental mitigation credits "
        "(Nutrient Neutrality, SANG), backed by institutional finance. We create and manage a "
        "large portfolio of nature recovery projects, owning the freehold to all mitigation land "
        "for the highest integrity and long-term assurance.",
        body_style
    ))
    
    elements.append(Paragraph("<b>Our key advantages:</b>", body_style))
    advantages = [
        "<b>Permanent Nature Recovery:</b> We dedicate all land to conservation in perpetuity, not just for the 30-year minimum.",
        "<b>Independently Managed Endowment:</b> Long-term management funds are fully insured and overseen by independent asset managers.",
        "<b>Independent Governance:</b> Leading third-party ecologists and contractors oversee all monitoring and habitat management.",
        "<b>Full Ownership and Responsibility:</b> We hold the freehold and assume complete responsibility for all delivery and management."
    ]
    
    for advantage in advantages:
        elements.append(Paragraph(f"• {advantage}", body_style))
    
    elements.append(Spacer(1, 0.2*inch))
    
    # Quote total
    total_with_admin = quote_total + admin_fee
    elements.append(Paragraph(
        f"<b>Your Quote: £{total_with_admin:,.0f} + VAT</b>",
        heading_style
    ))
    elements.append(Spacer(1, 0.1*inch))
    
    # Pricing breakdown
    elements.append(Paragraph("<b>Pricing Breakdown:</b>", body_style))
    
    if not report_df.empty:
        # Convert DataFrame to table data
        # Remove internal columns if they exist
        display_df = report_df.copy()
        cols_to_remove = ['Distinctiveness_Supply', '# Units_Supply']
        for col in cols_to_remove:
            if col in display_df.columns:
                display_df = display_df.drop(columns=[col])
        
        # Prepare table data
        table_data = [display_df.columns.tolist()] + display_df.values.tolist()
        
        # Calculate column widths based on content
        num_cols = len(display_df.columns)
        col_widths = [doc.width / num_cols] * num_cols
        
        # Create table
        data_table = Table(table_data, colWidths=col_widths)
        data_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E7D32')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            
            # Data rows
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 1), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
        ]))
        
        elements.append(data_table)
    else:
        elements.append(Paragraph("<i>No habitat details available</i>", body_style))
    
    elements.append(Spacer(1, 0.2*inch))
    
    # Cost summary
    summary_data = [
        ['Subtotal (Units):', f'£{quote_total:,.0f}'],
        ['Admin Fee:', f'£{admin_fee:,.0f}'],
        ['<b>Total (excl. VAT):</b>', f'<b>£{total_with_admin:,.0f}</b>'],
    ]
    
    summary_table = Table(summary_data, colWidths=[4*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONT', (0, 0), (-1, -2), 'Helvetica', 10),
        ('FONT', (0, -1), (-1, -1), 'Helvetica-Bold', 11),
        ('LINEABOVE', (0, -1), (-1, -1), 2, colors.HexColor('#2E7D32')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Notes
    if notes:
        elements.append(Paragraph("<b>Additional Notes:</b>", heading_style))
        elements.append(Paragraph(notes, body_style))
        elements.append(Spacer(1, 0.2*inch))
    
    # Footer notes
    elements.append(Paragraph(
        "<i>Prices exclude VAT. Any legal costs for contract amendments will be charged to the client "
        "and must be paid before allocation.</i>",
        small_style
    ))
    
    elements.append(Spacer(1, 0.2*inch))
    
    elements.append(Paragraph(
        "<b>Next Steps:</b> We're here to help! Please contact us if you have any questions or would like to proceed. "
        "We'll guide you through the allocation process and ensure a smooth transaction.",
        body_style
    ))
    
    # Build PDF
    doc.build(elements)
    
    # Get PDF bytes
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    return pdf_bytes
