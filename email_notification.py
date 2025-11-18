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
            # This creates a properly formatted email that reviewers can forward
            
            if not email_html_body:
                return False, "email_html_body is required for full_quote email type"
            
            total_with_admin = quote_total + (admin_fee or 0.0)
            
            # Subject for the email to reviewer
            msg['Subject'] = f"BNG Quote for Review & Forwarding - {client_name} - £{total_with_admin:,.0f}"
            
            # Create the wrapper email to reviewer (plain text)
            reviewer_instructions = f"""
QUOTE READY FOR REVIEW AND FORWARDING
======================================

CUSTOMER DETAILS:
- Client Name: {client_name}
- Contact Email: {contact_email}
- Location: {site_location}
- Quote Total: £{total_with_admin:,.0f} + VAT
- Reference Number: [TO BE FILLED IN MANUALLY]

PROMOTER DETAILS:
- Promoter Name: {promoter_name}
"""
            
            if notes:
                reviewer_instructions += f"""
ADDITIONAL NOTES:
{notes}
"""
            
            reviewer_instructions += f"""

INSTRUCTIONS FOR REVIEWER:
===========================
This quote is £50,000 or over and requires review before sending to the customer.

ACTION REQUIRED:
1. Review the customer-facing quote email below
2. Fill in the reference number manually in the subject line
3. Forward this email to the customer: {contact_email}
4. The BNG metric file is attached for reference

The customer-facing email content is included below with both plain text and HTML formatting.

================================================================================
CUSTOMER-FACING EMAIL CONTENT (FORWARD THE SECTION BELOW)
================================================================================

Subject: RE: BNG Units for site at {site_location} - [REFERENCE NUMBER]

"""
            
            # Create plain text version of customer email
            customer_text = f"""Dear {client_name}

Our Ref: [REFERENCE NUMBER TO BE FILLED IN]

{promoter_name} has advised us that you need Biodiversity Net Gain units for your development in {site_location}, and we're here to help you discharge your BNG condition.

About Us

Wild Capital is a national supplier of BNG Units and environmental mitigation credits (Nutrient Neutrality, SANG), backed by institutional finance.

Your Quote - £{total_with_admin:,.0f} + VAT

[Please view the HTML version of this email for the detailed pricing breakdown table]

Prices exclude VAT. Any legal costs for contract amendments will be charged to the client and must be paid before allocation.

Next Steps

BNG is a pre-commencement, not a pre-planning, condition.

To accept the quote, let us know—we'll request some basic details before sending the Allocation Agreement. The price is fixed for 30 days, but unit availability is only guaranteed once the agreement is signed.

We offer two contract options:

1. Buy It Now: Pay in full on signing; units allocated immediately.
2. Reservation & Purchase: Pay a reservation fee to hold units for up to 6 months, with the option to draw them down anytime in that period.

If you have any questions, please reply to this email or call 01962 436574.

Best regards,
Wild Capital Team
"""
            
            # Combine reviewer instructions with customer content
            full_body_text = reviewer_instructions + customer_text
            
            # Create multipart message with both text and HTML
            # The HTML part contains the formatted quote table
            msg.attach(MIMEText(full_body_text, 'plain'))
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
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        
        server.send_message(msg)
        server.quit()
        
        return True, f"Email sent successfully to {len(to_emails)} recipient(s)"
        
    except Exception as e:
        error_msg = f"Failed to send email: {str(e)}"
        return False, error_msg

