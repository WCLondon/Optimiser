"""
Email notification module for promoter submissions

This module sends email notifications when promoters submit quotes.
"""

import re
from typing import List, Optional
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import streamlit as st


def sanitize_email_header(value: str) -> str:
    """
    Sanitize a value for use in email headers to prevent header injection attacks.
    
    Removes newlines, carriage returns, and other control characters that could
    be used for header injection.
    
    Args:
        value: The string to sanitize
    
    Returns:
        Sanitized string safe for email headers
    """
    if not value:
        return ""
    # Remove any newlines, carriage returns, and control characters
    return re.sub(r'[\r\n\x00-\x1f\x7f]', '', str(value))


def get_excel_mime_type(filename: str) -> tuple[str, str]:
    """
    Determine the correct MIME type for an Excel file based on its extension.
    
    Args:
        filename: The filename with extension
    
    Returns:
        Tuple of (maintype, subtype) for MIMEBase
    """
    filename_lower = filename.lower()
    
    if filename_lower.endswith('.xlsm'):
        # Excel macro-enabled workbook
        return ('application', 'vnd.ms-excel.sheet.macroEnabled.12')
    elif filename_lower.endswith('.xlsb'):
        # Excel binary workbook
        return ('application', 'vnd.ms-excel.sheet.binary.macroEnabled.12')
    elif filename_lower.endswith('.xlsx'):
        # Excel workbook (default)
        return ('application', 'vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    else:
        # Default to generic binary for unknown extensions
        return ('application', 'octet-stream')



def send_email_notification(to_emails: List[str],
                           client_name: str,
                           quote_total: float,
                           metric_file_content: bytes,
                           email_type: str = 'quote_notification',
                           email_html_body: Optional[str] = None,
                           admin_fee: Optional[float] = None,
                           csv_allocation_content: Optional[str] = None,
                           metric_filename: Optional[str] = None,
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
        csv_allocation_content: CSV allocation data to attach (optional)
        metric_filename: Original filename of the metric file (optional, defaults to reference_number_metric.xlsx)
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
        submitted_by_name = kwargs.get('submitted_by_name', None)  # Individual submitter name
        contact_email = kwargs.get('contact_email', 'N/A')
        contact_number = kwargs.get('contact_number', '')
        notes = kwargs.get('notes', '')
        
        # Additional recipient details
        additional_recipient_name = kwargs.get('additional_recipient_name', None)
        additional_recipient_type = kwargs.get('additional_recipient_type', None)
        additional_recipient_email = kwargs.get('additional_recipient_email', None)
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = f"{from_name} <{from_email}>"
        msg['To'] = ', '.join(to_emails)
        
        # Build additional recipient section for emails
        additional_recipient_text = ""
        additional_recipient_html = ""
        if additional_recipient_name:
            additional_recipient_text = f"\n- Additional Recipient ({additional_recipient_type}): {additional_recipient_name}"
            if additional_recipient_email:
                additional_recipient_text += f" ({additional_recipient_email})"
            additional_recipient_html = f"<li><strong>Additional Recipient ({additional_recipient_type}):</strong> {additional_recipient_name}"
            if additional_recipient_email:
                additional_recipient_html += f" ({additional_recipient_email})"
            additional_recipient_html += "</li>"
        
        # Different email content based on type
        if email_type == 'full_quote':
            # Full quote email for £50k+ (to be forwarded to customer)
            # This creates a properly formatted email that reviewers can forward
            
            if not email_html_body:
                return False, "email_html_body is required for full_quote email type"
            
            total_with_admin = quote_total + (admin_fee or 0.0)
            
            # Subject for the email to reviewer - include reference number
            msg['Subject'] = f"BNG Quote for Review & Forwarding - {reference_number} - {client_name} - £{total_with_admin:,.0f}"
            
            # Build promoter details section - include submitter if different from promoter
            promoter_section_text = f"- Promoter Name: {promoter_name}"
            if submitted_by_name and submitted_by_name != promoter_name:
                promoter_section_text += f"\n- Submitted By: {submitted_by_name}"
            
            # Build contact number line if provided
            contact_number_text = f"\n- Contact Number: {contact_number}" if contact_number else ""
            
            # Create the wrapper email to reviewer (plain text)
            reviewer_instructions = f"""
QUOTE READY FOR REVIEW AND FORWARDING
======================================

CUSTOMER DETAILS:
- Client Name: {client_name}
- Contact Email: {contact_email}{contact_number_text}{additional_recipient_text}
- Location: {site_location}
- Quote Total: £{total_with_admin:,.0f} + VAT
- Reference Number: {reference_number}

PROMOTER DETAILS:
{promoter_section_text}
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
2. Forward this email to the customer: {contact_email}
3. The BNG metric file and CSV allocation data are attached for reference

The customer-facing email content is included below with both plain text and HTML formatting.

================================================================================
CUSTOMER-FACING EMAIL CONTENT (FORWARD THE SECTION BELOW)
================================================================================

Subject: BNG Units for site at {site_location} - {client_name} - {reference_number}

"""
            
            # Create plain text version of customer email
            customer_text = f"""Dear {client_name}

Our Ref: {reference_number}

Thank you for your enquiry into Biodiversity Net Gain units for your development in {site_location}, and we're here to help you discharge your BNG condition.

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
            
            # Combine reviewer instructions with customer content for plain text
            full_body_text = reviewer_instructions + customer_text
            
            # Build HTML promoter section - include submitter if different from promoter
            promoter_section_html = f"<li><strong>Promoter Name:</strong> {promoter_name}</li>"
            if submitted_by_name and submitted_by_name != promoter_name:
                promoter_section_html += f"\n            <li><strong>Submitted By:</strong> {submitted_by_name}</li>"
            
            # Build contact number HTML line if provided
            contact_number_html = f"\n            <li><strong>Contact Number:</strong> {contact_number}</li>" if contact_number else ""
            
            # Create HTML version with reviewer instructions and formatted table
            reviewer_instructions_html = f"""
<div style="font-family: Arial, sans-serif; font-size: 12px; line-height: 1.6; background-color: #f9f9f9; padding: 20px; margin-bottom: 20px; border: 2px solid #2A514A; border-radius: 5px;">
    <h2 style="color: #2A514A; margin-top: 0;">📋 QUOTE READY FOR REVIEW AND FORWARDING</h2>
    
    <div style="background-color: white; padding: 15px; border-radius: 5px; margin-bottom: 15px;">
        <h3 style="color: #2A514A; margin-top: 0;">Customer Details:</h3>
        <ul style="list-style: none; padding-left: 0;">
            <li><strong>Client Name:</strong> {client_name}</li>
            <li><strong>Contact Email:</strong> {contact_email}</li>{contact_number_html}
            {additional_recipient_html}
            <li><strong>Location:</strong> {site_location}</li>
            <li><strong>Quote Total:</strong> £{total_with_admin:,.0f} + VAT</li>
            <li><strong>Reference Number:</strong> <span style="background-color: #90EE90; padding: 2px 8px;">{reference_number}</span></li>
        </ul>
    </div>
    
    <div style="background-color: white; padding: 15px; border-radius: 5px; margin-bottom: 15px;">
        <h3 style="color: #2A514A; margin-top: 0;">Promoter Details:</h3>
        <ul style="list-style: none; padding-left: 0;">
            {promoter_section_html}
        </ul>"""
            
            if notes:
                reviewer_instructions_html += f"""
        <h3 style="color: #2A514A;">Additional Notes:</h3>
        <p style="background-color: #FFF9E6; padding: 10px; border-left: 3px solid #F8C237;">{notes}</p>"""
            
            reviewer_instructions_html += f"""
    </div>
    
    <div style="background-color: #2A514A; color: white; padding: 15px; border-radius: 5px;">
        <h3 style="margin-top: 0; color: white;">⚠️ INSTRUCTIONS FOR REVIEWER:</h3>
        <p style="margin: 10px 0;">This quote is £50,000 or over and requires review before sending to the customer.</p>
        <p style="margin: 10px 0;"><strong>ACTION REQUIRED:</strong></p>
        <ol style="margin: 10px 0; padding-left: 20px;">
            <li>Review the customer-facing quote email below</li>
            <li>Forward this email to the customer: <strong>{contact_email}</strong></li>
            <li>The BNG metric file and CSV allocation data are attached for reference</li>
        </ol>
    </div>
</div>

<hr style="border: none; border-top: 3px solid #2A514A; margin: 30px 0;">

<div style="font-family: Arial, sans-serif; font-size: 12px;">
    <h2 style="color: #2A514A; text-align: center;">📧 CUSTOMER-FACING EMAIL CONTENT</h2>
    <p style="text-align: center; color: #666; font-style: italic;">(Forward the section below to the customer)</p>
</div>

<hr style="border: none; border-top: 1px solid #ccc; margin: 20px 0;">

"""
            
            # Combine HTML reviewer instructions with the customer-facing HTML email body
            full_html_body = reviewer_instructions_html + email_html_body
            
            # Create multipart/alternative for the email body (text and HTML)
            msg_alternative = MIMEMultipart('alternative')
            msg_alternative.attach(MIMEText(full_body_text, 'plain'))
            msg_alternative.attach(MIMEText(full_html_body, 'html'))
            
            # Attach the alternative part to the main message
            msg.attach(msg_alternative)
        
        elif email_type == 'manual_review':
            # Manual review email for Small Sites Metric or Nutrient Neutrality Metric
            metric_type = kwargs.get('metric_type', 'Unknown Metric Type')
            
            msg['Subject'] = f"Manual Quote Request ({metric_type}) - {reference_number} - {client_name}"
            
            # Build promoter details section - include submitter if different from promoter
            promoter_section = f"- Promoter Name: {promoter_name}"
            if submitted_by_name and submitted_by_name != promoter_name:
                promoter_section += f"\n- Submitted By: {submitted_by_name}"
            
            # Build contact number line if provided
            contact_number_line = f"\n- Contact Number: {contact_number}" if contact_number else ""
            
            # Create email body
            body = f"""
Manual Quote Request - {metric_type}
{'=' * (24 + len(metric_type))}

⚠️ This quote requires MANUAL PROCESSING - the metric file attached is a {metric_type}
which cannot be automatically processed by the system.

CLIENT DETAILS:
- Client Name: {client_name}
- Reference: {reference_number}
- Location: {site_location}
- Contact Email: {contact_email}{contact_number_line}{additional_recipient_text}

PROMOTER DETAILS:
{promoter_section}

"""
            
            if notes:
                body += f"""
ADDITIONAL NOTES:
{notes}

"""
            
            body += f"""
ACTION REQUIRED:
Please process this {metric_type} manually and provide a quote to the client.

The metric file is attached for your review.

---
This is an automated notification from the Wild Capital BNG Quote System.
"""
            
            msg.attach(MIMEText(body, 'plain'))
        
        elif email_type == 'quote_accepted':
            # Quote acceptance notification from promoter
            allocation_summary = kwargs.get('allocation_summary', '')
            accepted_by = kwargs.get('accepted_by', promoter_name)
            
            # Sanitize user-provided data for email subject to prevent header injection
            safe_ref = sanitize_email_header(reference_number)
            safe_client = sanitize_email_header(client_name)
            msg['Subject'] = f"🎉 QUOTE ACCEPTED - {safe_ref} - {safe_client}"
            
            # Build promoter details section
            promoter_section = f"- Promoter Name: {promoter_name}"
            if submitted_by_name and submitted_by_name != promoter_name:
                promoter_section += f"\n- Accepted By: {submitted_by_name}"
            
            # Build contact number line if provided
            contact_number_line = f"\n- Contact Number: {contact_number}" if contact_number else ""
            
            # Create email body
            body = f"""
🎉 QUOTE ACCEPTED BY CLIENT
=============================

A promoter has marked this quote as ACCEPTED by the client. Please follow up to complete the transaction.

QUOTE DETAILS:
- Reference: {reference_number}
- Quote Total: £{quote_total:,.2f}
- Location: {site_location}

CLIENT DETAILS:
- Client Name: {client_name}
- Contact Email: {contact_email}{contact_number_line}

PROMOTER DETAILS:
{promoter_section}

"""
            
            if allocation_summary:
                body += f"""
ALLOCATION SUMMARY:
{allocation_summary}

"""
            
            if notes:
                body += f"""
ADDITIONAL NOTES FROM PROMOTER:
{notes}

"""
            
            body += """
ACTION REQUIRED:
Please contact the client to proceed with the Allocation Agreement.

---
This is an automated notification from the Wild Capital BNG Quote System.
"""
            
            msg.attach(MIMEText(body, 'plain'))
            
        else:
            # Simple quote notification (under £50k)
            msg['Subject'] = f"New BNG Quote Request - {reference_number} - {client_name}"
            
            # Build promoter details section - include submitter if different from promoter
            promoter_section = f"- Promoter Name: {promoter_name}"
            if submitted_by_name and submitted_by_name != promoter_name:
                promoter_section += f"\n- Submitted By: {submitted_by_name}"
            
            # Build contact number line if provided
            contact_number_line = f"\n- Contact Number: {contact_number}" if contact_number else ""
            
            # Create email body
            body = f"""
New BNG Quote Request Submitted
================================

CLIENT DETAILS:
- Client Name: {client_name}
- Reference: {reference_number}
- Location: {site_location}
- Contact Email: {contact_email}{contact_number_line}{additional_recipient_text}
- Quote Total: £{quote_total:,.2f}

PROMOTER DETAILS:
{promoter_section}

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
            # Determine the attachment filename
            if metric_filename:
                # Use the original filename if provided
                attachment_filename = metric_filename
            else:
                # Fallback to reference number with .xlsx extension
                attachment_filename = f"{reference_number}_metric.xlsx"
            
            # Get the correct MIME type based on the file extension
            maintype, subtype = get_excel_mime_type(attachment_filename)
            
            attachment = MIMEBase(maintype, subtype)
            attachment.set_payload(metric_file_content)
            encoders.encode_base64(attachment)
            attachment.add_header(
                'Content-Disposition',
                f'attachment; filename="{attachment_filename}"'
            )
            msg.attach(attachment)
        
        # Attach CSV allocation file if provided
        if csv_allocation_content:
            csv_attachment = MIMEBase('text', 'csv')
            csv_attachment.set_payload(csv_allocation_content.encode('utf-8'))
            encoders.encode_base64(csv_attachment)
            csv_attachment.add_header(
                'Content-Disposition',
                f'attachment; filename="{reference_number}_allocation.csv"'
            )
            msg.attach(csv_attachment)
        
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

