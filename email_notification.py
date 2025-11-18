"""
Email notification module for promoter submissions

This module sends email notifications when promoters submit quotes.
"""

from typing import List, Optional
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import streamlit as st


def send_email_notification(to_emails: List[str],
                           client_name: str,
                           quote_total: float,
                           metric_file_content: bytes,
                           **kwargs) -> tuple[bool, str]:
    """
    Send email notification about a new quote submission.
    
    Args:
        to_emails: List of recipient email addresses
        client_name: Name of the client
        quote_total: Total quote amount in GBP
        metric_file_content: BNG metric file content
        **kwargs: Additional parameters (reference_number, site_location, etc.)
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Get SMTP configuration from Streamlit secrets
        smtp_host = st.secrets.get("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(st.secrets.get("SMTP_PORT", 587))
        smtp_user = st.secrets.get("SMTP_USER", "")
        smtp_password = st.secrets.get("SMTP_PASSWORD", "")
        from_email = st.secrets.get("SMTP_FROM_EMAIL", smtp_user)
        from_name = st.secrets.get("SMTP_FROM_NAME", "Wild Capital BNG Quotes")
        
        if not smtp_user or not smtp_password:
            msg = "SMTP credentials not configured in secrets. Please add SMTP_USER and SMTP_PASSWORD to .streamlit/secrets.toml"
            print(f"[EMAIL] {msg}")
            return False, msg
        
        # Extract additional parameters
        reference_number = kwargs.get('reference_number', 'N/A')
        site_location = kwargs.get('site_location', 'N/A')
        promoter_name = kwargs.get('promoter_name', 'N/A')
        contact_email = kwargs.get('contact_email', 'N/A')
        notes = kwargs.get('notes', '')
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = f"{from_name} <{from_email}>"
        msg['To'] = ', '.join(to_emails)
        msg['Subject'] = f"New BNG Quote Request - {reference_number} - {client_name}"
        
        # Create email body
        body = f"""
New BNG Quote Request Submitted

Client Details:
- Client Name: {client_name}
- Reference: {reference_number}
- Location: {site_location}
- Contact Email: {contact_email}
- Quote Total: £{quote_total:,.2f}

Promoter Details:
- Promoter Name: {promoter_name}

"""
        
        if notes:
            body += f"""
Additional Notes:
{notes}

"""
        
        body += """
Please find the BNG metric file attached.

---
This is an automated notification from the Wild Capital BNG Quote System.
"""
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Attach metric file
        if metric_file_content:
            attachment = MIMEBase('application', 'octet-stream')
            attachment.set_payload(metric_file_content)
            encoders.encode_base64(attachment)
            attachment.add_header(
                'Content-Disposition',
                f'attachment; filename="{reference_number}_metric.xlsx"'
            )
            msg.attach(attachment)
        
        # Send email
        print(f"[EMAIL] Connecting to {smtp_host}:{smtp_port}")
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        
        print(f"[EMAIL] Sending to {to_emails}")
        server.send_message(msg)
        server.quit()
        
        print(f"[EMAIL] ✓ Email sent successfully to {to_emails}")
        return True, f"Email sent successfully to {len(to_emails)} recipient(s)"
        
    except Exception as e:
        error_msg = f"Failed to send email: {str(e)}"
        print(f"[EMAIL] ✗ {error_msg}")
        import traceback
        traceback.print_exc()
        return False, error_msg

