"""
PDF generator for promoter quotes

This module generates PDF quotes for the promoter interface using the same 
HTML table styling as app.py for consistency.
"""

from typing import Optional
import pandas as pd


def generate_quote_pdf(client_name: str,
                      reference_number: str,
                      site_location: str,
                      quote_total: float,
                      report_df: pd.DataFrame,
                      admin_fee: float = 500.0) -> bytes:
    """
    Generate a PDF quote document for a client using HTML table.
    
    Args:
        client_name: Name of the client
        reference_number: Quote reference number
        site_location: Site location/address
        quote_total: Total quote amount in GBP (without admin fee)
        report_df: DataFrame with allocation details (from generate_client_report_table_fixed)
        admin_fee: Admin fee amount (£300 for fractional, £500 for small/medium)
    
    Returns:
        PDF content as bytes
    """
    try:
        from weasyprint import HTML
    except ImportError:
        # Fallback if weasyprint is not available
        pdf_content = f"""PDF Quote
Client: {client_name}
Reference: {reference_number}
Location: {site_location}
Habitat Offset Cost: £{quote_total:,.2f}
Admin Fee: £{admin_fee:,.2f}
Total: £{(quote_total + admin_fee):,.2f}

Note: Full PDF generation requires weasyprint library.
Please install with: pip install weasyprint
""".encode('utf-8')
        return pdf_content
    
    # Calculate total with admin fee
    total_with_admin = quote_total + admin_fee
    
    # Process report_df rows and generate HTML table rows with section headers
    html_rows = ""
    
    if not report_df.empty:
        # Check if we have section indicators in the dataframe
        current_section = None
        
        for _, row in report_df.iterrows():
            # Check if this is a section header row
            if "Section" in row and row["Section"]:
                section_name = row["Section"]
                if section_name != current_section:
                    current_section = section_name
                    html_rows += f"""
            <tr style="background-color: #D9F2D0;">
                <td colspan="8" style="padding: 6px; border: 1px solid #000; font-weight: bold; color: #000;">{section_name}</td>
            </tr>
            """
            
            # Add data row
            html_rows += f"""
            <tr>
                <td style="padding: 6px; border: 1px solid #000;">{row.get("Distinctiveness", "")}</td>
                <td style="padding: 6px; border: 1px solid #000;">{row.get("Habitats Lost", "")}</td>
                <td style="padding: 6px; border: 1px solid #000; text-align: right;">{row.get("# Units", "")}</td>
                <td style="padding: 6px; border: 1px solid #000;">{row.get("Distinctiveness_Supply", "")}</td>
                <td style="padding: 6px; border: 1px solid #000;">{row.get("Habitats Supplied", "")}</td>
                <td style="padding: 6px; border: 1px solid #000; text-align: right;">{row.get("# Units_Supply", "")}</td>
                <td style="padding: 6px; border: 1px solid #000; text-align: right;">{row.get("Price Per Unit", "")}</td>
                <td style="padding: 6px; border: 1px solid #000; text-align: right;">{row.get("Offset Cost", "")}</td>
            </tr>
            """
    
    # Calculate totals
    total_demand_units = report_df['# Units'].sum() if '# Units' in report_df.columns else 0
    total_supply_units = report_df['# Units_Supply'].sum() if '# Units_Supply' in report_df.columns else 0
    
    # Format units with up to 3 decimal places
    def format_units_total(value):
        if value == 0:
            return "0.00"
        formatted = f"{value:.3f}"
        parts = formatted.split('.')
        if len(parts) == 2:
            integer_part = parts[0]
            decimal_part = parts[1].rstrip('0')
            if len(decimal_part) < 2:
                decimal_part = decimal_part.ljust(2, '0')
            return f"{integer_part}.{decimal_part}"
        return formatted
    
    # Build complete HTML document
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>BNG Quote - {reference_number}</title>
        <style>
            @page {{
                size: A4;
                margin: 2cm;
            }}
            body {{
                font-family: Arial, sans-serif;
                font-size: 11px;
                line-height: 1.4;
            }}
            .header {{
                text-align: center;
                margin-bottom: 20px;
            }}
            .header h1 {{
                color: #2A514A;
                margin: 0;
                font-size: 24px;
            }}
            .header p {{
                margin: 5px 0;
                color: #666;
            }}
            .client-details {{
                margin-bottom: 20px;
                padding: 10px;
                background-color: #f5f5f5;
                border-left: 4px solid #2A514A;
            }}
            .client-details p {{
                margin: 5px 0;
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
                margin: 20px 0;
                font-size: 11px;
            }}
            th {{
                padding: 8px;
                border: 1px solid #000;
                font-weight: bold;
            }}
            td {{
                padding: 6px;
                border: 1px solid #000;
            }}
            .footer {{
                margin-top: 30px;
                padding-top: 20px;
                border-top: 2px solid #2A514A;
                font-size: 10px;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Biodiversity Net Gain Quote</h1>
            <p><strong>Reference:</strong> {reference_number}</p>
        </div>
        
        <div class="client-details">
            <p><strong>Client:</strong> {client_name}</p>
            <p><strong>Site Location:</strong> {site_location}</p>
            <p><strong>Quote Date:</strong> {pd.Timestamp.now().strftime('%d %B %Y')}</p>
        </div>
        
        <h2 style="color: #2A514A; font-size: 14px;">Habitat Offset Requirements</h2>
        
        <table>
            <thead>
                <tr>
                    <th colspan="3" style="text-align: center; background-color: #F8C237; color: #000;">Development Impact</th>
                    <th colspan="5" style="text-align: center; background-color: #2A514A; color: #FFFFFF;">Mitigation Supplied from Wild Capital</th>
                </tr>
                <tr>
                    <th style="background-color: #F8C237; color: #000;">Distinctiveness</th>
                    <th style="background-color: #F8C237; color: #000;">Habitats Lost</th>
                    <th style="background-color: #F8C237; color: #000;"># Units</th>
                    <th style="background-color: #2A514A; color: #FFFFFF;">Distinctiveness</th>
                    <th style="background-color: #2A514A; color: #FFFFFF;">Habitats Supplied</th>
                    <th style="background-color: #2A514A; color: #FFFFFF;"># Units</th>
                    <th style="background-color: #2A514A; color: #FFFFFF;">Price Per Unit</th>
                    <th style="background-color: #2A514A; color: #FFFFFF;">Offset Cost</th>
                </tr>
            </thead>
            <tbody>
                {html_rows}
                <tr>
                    <td colspan="7" style="text-align: right; font-weight: bold;">Planning Discharge Pack</td>
                    <td style="text-align: right;">£{admin_fee:,.0f}</td>
                </tr>
                <tr style="background-color: #f0f0f0; font-weight: bold;">
                    <td>Total</td>
                    <td></td>
                    <td style="text-align: right;">{format_units_total(total_demand_units)}</td>
                    <td></td>
                    <td></td>
                    <td style="text-align: right;">{format_units_total(total_supply_units)}</td>
                    <td></td>
                    <td style="text-align: right;">£{total_with_admin:,.0f}</td>
                </tr>
            </tbody>
        </table>
        
        <div class="footer">
            <p><strong>Next Steps:</strong></p>
            <p>BNG is a pre-commencement, not a pre-planning, condition.</p>
            <p>To accept this quote, please contact us. The price is fixed for 30 days, but unit availability is only guaranteed once the Allocation Agreement is signed.</p>
            <p>Once you sign the agreement, pay the settlement fee and provide us with your metric and decision notice, we will allocate the units to you.</p>
            <p><strong>Contact:</strong> 01962 436574 | <strong>Email:</strong> info@wildlifecredits.co.uk</p>
        </div>
    </body>
    </html>
    """
    
    # Generate PDF from HTML
    pdf_bytes = HTML(string=html_content).write_pdf()
    
    return pdf_bytes
