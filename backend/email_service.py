"""
Email service for sending review notifications
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from .config import get_settings


async def send_review_email(
    promoter_slug: str,
    contact_email: str,
    site_address: Optional[str],
    site_postcode: Optional[str],
    client_reference: Optional[str],
    notes: Optional[str],
    quote_total: float,
    submission_id: int,
    metric_url: str
) -> bool:
    """
    Send review email to designated reviewers for manual quote review
    
    Args:
        promoter_slug: Promoter identifier
        contact_email: Submitter's email
        site_address: Site address
        site_postcode: Site postcode
        client_reference: Client reference
        notes: Additional notes
        quote_total: Quote total amount
        submission_id: Database submission ID
        metric_url: Signed URL to metric file
    
    Returns:
        True if email sent successfully
    """
    settings = get_settings()
    
    # Get reviewer emails
    reviewers = settings.reviewer_emails
    if not reviewers:
        print("Warning: No reviewer emails configured")
        return False
    
    # Build location string
    location_parts = []
    if site_address:
        location_parts.append(site_address)
    if site_postcode:
        location_parts.append(site_postcode)
    location_str = ", ".join(location_parts) if location_parts else "Not specified"
    
    # Email subject
    subject = f"BNG Quote Review – {promoter_slug} – {location_str[:50]} – £{quote_total:,.2f}"
    
    # Email body (HTML)
    html_body = f"""
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 8px 8px 0 0;
                text-align: center;
            }}
            .content {{
                background: #f7fafc;
                padding: 20px;
                border: 1px solid #e2e8f0;
            }}
            .detail-row {{
                margin: 12px 0;
                padding: 8px;
                background: white;
                border-left: 3px solid #667eea;
            }}
            .label {{
                font-weight: bold;
                color: #4a5568;
            }}
            .value {{
                color: #2d3748;
            }}
            .highlight {{
                font-size: 18px;
                color: #667eea;
                font-weight: bold;
            }}
            .button {{
                display: inline-block;
                background: #667eea;
                color: white;
                padding: 12px 24px;
                text-decoration: none;
                border-radius: 6px;
                margin: 16px 0;
            }}
            .footer {{
                margin-top: 20px;
                padding-top: 20px;
                border-top: 1px solid #e2e8f0;
                font-size: 12px;
                color: #718096;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>BNG Quote Review Required</h2>
                <p>Manual review needed for quote exceeding £20,000</p>
            </div>
            
            <div class="content">
                <div class="detail-row">
                    <span class="label">Submission ID:</span>
                    <span class="value">#{submission_id}</span>
                </div>
                
                <div class="detail-row">
                    <span class="label">Promoter:</span>
                    <span class="value">{promoter_slug}</span>
                </div>
                
                <div class="detail-row">
                    <span class="label">Contact Email:</span>
                    <span class="value">{contact_email}</span>
                </div>
                
                <div class="detail-row">
                    <span class="label">Location:</span>
                    <span class="value">{location_str}</span>
                </div>
                
                {f'<div class="detail-row"><span class="label">Client Reference:</span><span class="value">{client_reference}</span></div>' if client_reference else ''}
                
                <div class="detail-row">
                    <span class="label">Quote Total:</span>
                    <span class="value highlight">£{quote_total:,.2f}</span>
                </div>
                
                {f'<div class="detail-row"><span class="label">Notes:</span><span class="value">{notes}</span></div>' if notes else ''}
                
                <div style="text-align: center; margin-top: 24px;">
                    <a href="{metric_url}" class="button">Download Metric File</a>
                </div>
                
                <div class="footer">
                    <p>
                        <strong>Next Steps:</strong><br>
                        1. Review the metric file using the link above<br>
                        2. Contact the client at {contact_email}<br>
                        3. Prepare a detailed proposal<br>
                        4. Update the submission status in the admin dashboard
                    </p>
                    <p>
                        <em>Note: The metric file download link expires in 24 hours.</em>
                    </p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Plain text version
    text_body = f"""
    BNG Quote Review Required
    
    A new quote submission requires manual review (exceeds £20,000 threshold).
    
    Submission ID: #{submission_id}
    Promoter: {promoter_slug}
    Contact Email: {contact_email}
    Location: {location_str}
    {f'Client Reference: {client_reference}' if client_reference else ''}
    Quote Total: £{quote_total:,.2f}
    {f'Notes: {notes}' if notes else ''}
    
    Download Metric File: {metric_url}
    
    Next Steps:
    1. Review the metric file
    2. Contact the client at {contact_email}
    3. Prepare a detailed proposal
    4. Update the submission status in the admin dashboard
    
    Note: The metric file download link expires in 24 hours.
    """
    
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
        msg['To'] = ", ".join(reviewers)
        
        # Attach both plain text and HTML versions
        msg.attach(MIMEText(text_body, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))
        
        # Send email
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            if settings.smtp_user and settings.smtp_password:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        
        print(f"Review email sent successfully for submission #{submission_id}")
        return True
        
    except Exception as e:
        print(f"Failed to send review email: {str(e)}")
        return False
