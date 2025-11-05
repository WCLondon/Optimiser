"""
Simple email service for promoter form
Sends notification emails with metric file attachments
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import Optional
import os


def send_manual_review_email(
    promoter_name: str,
    contact_email: str,
    site_location: str,
    client_reference: Optional[str],
    notes: Optional[str],
    quote_total: float,
    submission_id: int,
    metric_file_content: bytes,
    metric_file_name: str
) -> bool:
    """
    Send notification email to team with metric file attached
    Sends for all submissions (both auto-quote and manual review) for record keeping
    
    Args:
        promoter_name: Promoter identifier
        contact_email: Submitter's email
        site_location: Site location
        client_reference: Client reference
        notes: Additional notes
        quote_total: Quote total amount
        submission_id: Database submission ID
        metric_file_content: Metric file bytes
        metric_file_name: Metric file name
    
    Returns:
        True if email sent successfully
    """
    # Get email configuration from environment
    smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_user = os.getenv('SMTP_USER', '')
    smtp_password = os.getenv('SMTP_PASSWORD', '')
    from_email = os.getenv('SMTP_FROM_EMAIL', smtp_user)
    from_name = os.getenv('SMTP_FROM_NAME', 'BNG Quotes')
    reviewer_emails_str = os.getenv('REVIEWER_EMAILS', '')
    
    # Parse reviewer emails
    reviewer_emails = [email.strip() for email in reviewer_emails_str.split(',') if email.strip()]
    
    if not reviewer_emails:
        print("Warning: No reviewer emails configured")
        return False
    
    if not smtp_user or not smtp_password:
        print("Warning: SMTP credentials not configured")
        return False
    
    # Determine if auto-quote or manual review
    auto_quote_threshold = float(os.getenv('AUTO_QUOTE_THRESHOLD', '20000.0'))
    is_auto_quote = quote_total < auto_quote_threshold
    quote_type = "Auto-Quote" if is_auto_quote else "Manual Review"
    
    # Build email subject
    subject = f"BNG {quote_type} – {promoter_name} – {site_location} – £{quote_total:,.2f}"
    
    # Build email body
    body_lines = [
        f"New BNG quote submission received ({quote_type}).",
        f"",
        f"**Submission Details:**",
        f"- Submission ID: #{submission_id}",
        f"- Promoter: {promoter_name}",
        f"- Contact Email: {contact_email}",
        f"- Site Location: {site_location}",
    ]
    
    if client_reference:
        body_lines.append(f"- Client Reference: {client_reference}")
    
    body_lines.extend([
        f"",
        f"**Quote Information:**",
        f"- Total: £{quote_total:,.2f}",
        f"- Type: {quote_type}",
    ])
    
    if is_auto_quote:
        body_lines.append(f"- Status: PDF generated and sent to customer")
    else:
        body_lines.append(f"- Status: Requires manual review (≥£{auto_quote_threshold:,.0f})")
    
    body_lines.append(f"")
    
    if notes:
        body_lines.extend([
            f"**Additional Notes:**",
            f"{notes}",
            f""
        ])
    
    body_lines.extend([
        f"The BNG metric file is attached to this email for your records.",
        f"",
    ])
    
    if not is_auto_quote:
        body_lines.append(f"Please review and follow up with the client directly.")
    
    body_text = "\n".join(body_lines)
    
    # Create HTML version
    status_color = "#28a745" if is_auto_quote else "#ffc107"
    status_text = "PDF generated and sent to customer" if is_auto_quote else f"Requires manual review (≥£{auto_quote_threshold:,.0f})"
    
    body_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6;">
        <h2>BNG Quote Submission ({quote_type})</h2>
        <p>New BNG quote submission received.</p>
        
        <h3>Submission Details</h3>
        <ul>
            <li><strong>Submission ID:</strong> #{submission_id}</li>
            <li><strong>Promoter:</strong> {promoter_name}</li>
            <li><strong>Contact Email:</strong> {contact_email}</li>
            <li><strong>Site Location:</strong> {site_location}</li>
            {f'<li><strong>Client Reference:</strong> {client_reference}</li>' if client_reference else ''}
        </ul>
        
        <h3>Quote Information</h3>
        <ul>
            <li><strong>Total:</strong> £{quote_total:,.2f}</li>
            <li><strong>Type:</strong> {quote_type}</li>
            <li><strong>Status:</strong> <span style="color: {status_color};">{status_text}</span></li>
        </ul>
        
        {f'<h3>Additional Notes</h3><p>{notes}</p>' if notes else ''}
        
        <p>The BNG metric file is attached to this email for your records.</p>
        {f'<p><strong>Action required:</strong> Please review and follow up with the client directly.</p>' if not is_auto_quote else ''}
    </body>
    </html>
    """
    
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{from_name} <{from_email}>"
        msg['To'] = ', '.join(reviewer_emails)
        
        # Attach text and HTML parts
        part1 = MIMEText(body_text, 'plain')
        part2 = MIMEText(body_html, 'html')
        msg.attach(part1)
        msg.attach(part2)
        
        # Attach metric file
        attachment = MIMEApplication(metric_file_content)
        attachment.add_header('Content-Disposition', 'attachment', filename=metric_file_name)
        msg.attach(attachment)
        
        # Send email
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        
        print(f"Review email sent successfully to {', '.join(reviewer_emails)}")
        return True
        
    except Exception as e:
        print(f"Failed to send review email: {str(e)}")
        return False
