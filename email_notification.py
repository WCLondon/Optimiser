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
                           email_type: str = 'quote_notification',
                           email_html_body: Optional[str] = None,
                           admin_fee: Optional[float] = None,
                           **kwargs) -> tuple[bool, str]:
    """
    Send email notification about a new quote submission.
    
    Args:
        to_emails: List of recipient email addresses
        client_name: Name of the client
        quote_total: Total quote amount in GBP
        metric_file_content: BNG metric file content
        email_type: Type of email - 'quote_notification' (default) or 'full_quote'
        email_html_body: HTML body for full quote email (required if email_type='full_quote')
        admin_fee: Admin fee for full quote (required if email_type='full_quote')
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
        
        # Different email content based on type
        if email_type == 'full_quote':
            # Full quote email for £50k+ (to be forwarded to customer)
            msg['Subject'] = f"BNG Quote for Review - {client_name} - {site_location}"
            
            if not email_html_body:
                return False, "email_html_body is required for full_quote email type"
            
            # Create email body with customer details at top
            total_with_admin = quote_total + (admin_fee or 0.0)
            
            body_text = f"""
BNG Quote for Review - Please Forward to Customer
====================================================

CUSTOMER DETAILS:
- Client Name: {client_name}
- Contact Email: {contact_email}
- Location: {site_location}
- Quote Total: £{total_with_admin:,.2f} + VAT
- Reference Number: [TO BE FILLED IN MANUALLY]

PROMOTER DETAILS:
- Promoter Name: {promoter_name}
"""
            
            if notes:
                body_text += f"""
ADDITIONAL NOTES:
{notes}
"""
            
            body_text += """

INSTRUCTIONS FOR REVIEWER:
===========================
This quote is £50,000 or over and requires review before sending to the customer.

1. Review the quote details below
2. Fill in the reference number manually
3. Forward this email to the customer ({contact_email})
4. The metric file is attached for your reference

Please find the full quote details below and metric file attached.

---
[Full Quote Details Below - Forward to Customer]
---
""".format(contact_email=contact_email)
            
            # Create plain text version
            msg.attach(MIMEText(body_text, 'plain'))
            
            # Attach the HTML email body (the actual quote for customer)
            msg.attach(MIMEText(email_html_body, 'html'))
            
        else:
            # Simple quote notification (under £50k)
            msg['Subject'] = f"New BNG Quote Request - {reference_number} - {client_name}"
            
            # Create email body
            body = f"""
New BNG Quote Request Submitted
================================

CLIENT DETAILS:
- Client Name: {client_name}
- Reference: {reference_number}
- Location: {site_location}
- Contact Email: {contact_email}
- Quote Total: £{quote_total:,.2f}

PROMOTER DETAILS:
- Promoter Name: {promoter_name}

"""
            
            if notes:
                body += f"""
ADDITIONAL NOTES:
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

