"""
PDF generator for promoter quotes using reportlab for reliable PDF generation.
"""

from typing import Optional
import pandas as pd
from io import BytesIO


def generate_quote_pdf(client_name: str,
                      reference_number: str,
                      site_location: str,
                      quote_total: float,
                      report_df: pd.DataFrame,
                      admin_fee: float = 500.0) -> tuple[Optional[bytes], str]:
    """
    Generate a PDF quote document for a client using reportlab.
    
    Args:
        client_name: Name of the client
        reference_number: Quote reference number
        site_location: Site location/address
        quote_total: Total quote amount in GBP (without admin fee)
        report_df: DataFrame with allocation details
        admin_fee: Admin fee amount (£300 for fractional, £500 for small/medium)
    
    Returns:
        Tuple of (PDF content as bytes or None if failed, debug message string)
    """
    debug_messages = []
    debug_messages.append(f"Starting PDF generation for {client_name}")
    
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_RIGHT
        debug_messages.append("✓ reportlab imported successfully")
    except ImportError as e:
        error_msg = f"✗ reportlab import failed: {e}"
        debug_messages.append(error_msg)
        return None, "\n".join(debug_messages)
    
    try:
        # Create PDF buffer
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
        story = []
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2A514A'),
            spaceAfter=12,
            alignment=TA_CENTER
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#2A514A'),
            spaceAfter=6
        )
        
        # Title
        story.append(Paragraph("Biodiversity Net Gain Quote", title_style))
        story.append(Paragraph(f"<b>Reference:</b> {reference_number}", styles['Normal']))
        story.append(Spacer(1, 0.5*cm))
        
        # Client details
        client_data = [
            [Paragraph(f"<b>Client:</b> {client_name}", styles['Normal'])],
            [Paragraph(f"<b>Site Location:</b> {site_location}", styles['Normal'])],
            [Paragraph(f"<b>Quote Date:</b> {pd.Timestamp.now().strftime('%d %B %Y')}", styles['Normal'])]
        ]
        client_table = Table(client_data, colWidths=[16*cm])
        client_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f5f5f5')),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('RIGHTPADDING', (0,0), (-1,-1), 10),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#2A514A')),
        ]))
        story.append(client_table)
        story.append(Spacer(1, 0.5*cm))
        
        # Heading
        story.append(Paragraph("Habitat Offset Requirements", heading_style))
        story.append(Spacer(1, 0.3*cm))
        
        # Build table data
        table_data = []
        
        # Header rows
        table_data.append([
            Paragraph('<b>Development Impact</b>', styles['Normal']),
            '', '',
            Paragraph('<b>Mitigation Supplied from Wild Capital</b>', styles['Normal']),
            '', '', '', ''
        ])
        table_data.append([
            Paragraph('<b>Distinct-<br/>iveness</b>', styles['Normal']),
            Paragraph('<b>Habitats Lost</b>', styles['Normal']),
            Paragraph('<b># Units</b>', styles['Normal']),
            Paragraph('<b>Distinct-<br/>iveness</b>', styles['Normal']),
            Paragraph('<b>Habitats Supplied</b>', styles['Normal']),
            Paragraph('<b># Units</b>', styles['Normal']),
            Paragraph('<b>Price Per Unit</b>', styles['Normal']),
            Paragraph('<b>Offset Cost</b>', styles['Normal'])
        ])
        
        # Data rows - use Paragraphs for wrapping
        if not report_df.empty:
            for _, row in report_df.iterrows():
                table_data.append([
                    Paragraph(str(row.get("Distinctiveness", "")), styles['Normal']),
                    Paragraph(str(row.get("Habitats Lost", "")), styles['Normal']),
                    Paragraph(str(row.get("# Units", "")), styles['Normal']),
                    Paragraph(str(row.get("Distinctiveness_Supply", "")), styles['Normal']),
                    Paragraph(str(row.get("Habitats Supplied", "")), styles['Normal']),
                    Paragraph(str(row.get("# Units_Supply", "")), styles['Normal']),
                    Paragraph(str(row.get("Price Per Unit", "")), styles['Normal']),
                    Paragraph(str(row.get("Offset Cost", "")), styles['Normal'])
                ])
        
        # Admin fee row
        table_data.append([
            '', '', '', '', '', '',
            Paragraph('<b>Planning Discharge Pack</b>', styles['Normal']),
            Paragraph(f"£{admin_fee:,.0f}", styles['Normal'])
        ])
        
        # Total row - convert string values to float before summing
        def safe_float_sum(series):
            """Safely sum a series that may contain string or numeric values"""
            total = 0.0
            for val in series:
                try:
                    # Remove commas and convert to float
                    if isinstance(val, str):
                        val = val.replace(',', '')
                    total += float(val)
                except (ValueError, TypeError):
                    continue
            return total
        
        total_demand_units = safe_float_sum(report_df['# Units']) if '# Units' in report_df.columns else 0
        total_supply_units = safe_float_sum(report_df['# Units_Supply']) if '# Units_Supply' in report_df.columns else 0
        total_with_admin = quote_total + admin_fee
        
        def format_units_total(value):
            """Format units for display in the total row"""
            if value == 0:
                return "0.00"
            # Ensure value is numeric
            if isinstance(value, str):
                value = float(value.replace(',', ''))
            formatted = f"{value:.3f}"
            parts = formatted.split('.')
            if len(parts) == 2:
                integer_part = parts[0]
                decimal_part = parts[1].rstrip('0')
                if len(decimal_part) < 2:
                    decimal_part = decimal_part.ljust(2, '0')
                return f"{integer_part}.{decimal_part}"
            return formatted
        
        table_data.append([
            Paragraph('<b>Total</b>', styles['Normal']),
            '',
            Paragraph(format_units_total(total_demand_units), styles['Normal']),
            '', '',
            Paragraph(format_units_total(total_supply_units), styles['Normal']),
            '',
            Paragraph(f"£{total_with_admin:,.0f}", styles['Normal'])
        ])
        
        # Create table with better column widths for wrapping
        col_widths = [2.0*cm, 3.2*cm, 1.4*cm, 2.0*cm, 3.2*cm, 1.4*cm, 2.0*cm, 1.8*cm]
        data_table = Table(table_data, colWidths=col_widths)
        
        # Table styling
        table_style = [
            # Header row 1 - spanning headers
            ('SPAN', (0,0), (2,0)),  # Development Impact
            ('SPAN', (3,0), (7,0)),  # Mitigation Supplied
            ('BACKGROUND', (0,0), (2,0), colors.HexColor('#F8C237')),
            ('BACKGROUND', (3,0), (7,0), colors.HexColor('#2A514A')),
            ('TEXTCOLOR', (3,0), (7,0), colors.white),
            ('ALIGN', (0,0), (7,0), 'CENTER'),
            
            # Header row 2 - column names
            ('BACKGROUND', (0,1), (2,1), colors.HexColor('#F8C237')),
            ('BACKGROUND', (3,1), (7,1), colors.HexColor('#2A514A')),
            ('TEXTCOLOR', (3,1), (7,1), colors.white),
            ('ALIGN', (2,1), (2,1), 'RIGHT'),
            ('ALIGN', (5,1), (7,1), 'RIGHT'),
            
            # Data rows alignment
            ('ALIGN', (2,2), (2,-3), 'RIGHT'),
            ('ALIGN', (5,2), (7,-3), 'RIGHT'),
            
            # Admin fee row
            ('SPAN', (0,-2), (5,-2)),
            ('ALIGN', (6,-2), (7,-2), 'RIGHT'),
            
            # Total row
            ('BACKGROUND', (0,-1), (7,-1), colors.HexColor('#f0f0f0')),
            ('ALIGN', (2,-1), (2,-1), 'RIGHT'),
            ('ALIGN', (5,-1), (5,-1), 'RIGHT'),
            ('ALIGN', (7,-1), (7,-1), 'RIGHT'),
            
            # All cells - ensure proper padding and wrapping
            ('BOX', (0,0), (-1,-1), 1, colors.black),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.black),
            ('LEFTPADDING', (0,0), (-1,-1), 4),
            ('RIGHTPADDING', (0,0), (-1,-1), 4),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('WORDWRAP', (0,0), (-1,-1), True),  # Enable word wrapping
        ]
        
        data_table.setStyle(TableStyle(table_style))
        story.append(data_table)
        story.append(Spacer(1, 0.5*cm))
        
        # Footer
        footer_text = """
        <b>Next Steps:</b><br/>
        BNG is a pre-commencement, not a pre-planning, condition.<br/>
        To accept this quote, please contact us. The price is fixed for 30 days, but unit availability is only guaranteed once the Allocation Agreement is signed.<br/>
        Once you sign the agreement, pay the settlement fee and provide us with your metric and decision notice, we will allocate the units to you.<br/>
        <b>Contact:</b> 01962 436574 | <b>Email:</b> info@wild-capital.co.uk
        """
        story.append(Paragraph(footer_text, styles['Normal']))
        
        # Build PDF
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        debug_messages.append(f"✓ PDF generated successfully, size: {len(pdf_bytes)} bytes")
        return pdf_bytes, "\n".join(debug_messages)
        
    except Exception as e:
        error_msg = f"✗ PDF generation failed: {e}"
        debug_messages.append(error_msg)
        import traceback
        traceback_str = traceback.format_exc()
        debug_messages.append(f"Traceback:\n{traceback_str}")
        return None, "\n".join(debug_messages)
