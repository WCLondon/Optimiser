"""
Test email notification functionality

This test verifies that the email notification module properly returns
status information and handles errors correctly.
"""

import sys
from unittest.mock import MagicMock, patch, ANY
import smtplib

# Mock streamlit before importing email_notification
sys.modules['streamlit'] = MagicMock()

from email_notification import send_email_notification, sanitize_email_header


def test_sanitize_email_header():
    """Test that email header sanitization properly removes injection characters"""
    # Test basic passthrough
    assert sanitize_email_header("Normal Client Name") == "Normal Client Name"
    assert sanitize_email_header("BNG-A-12345") == "BNG-A-12345"
    
    # Test newline injection prevention
    assert sanitize_email_header("Name\nBcc: attacker@evil.com") == "NameBcc: attacker@evil.com"
    assert sanitize_email_header("Name\r\nBcc: attacker@evil.com") == "NameBcc: attacker@evil.com"
    
    # Test carriage return injection
    assert sanitize_email_header("Client\rName") == "ClientName"
    
    # Test control characters
    assert sanitize_email_header("Client\x00Name") == "ClientName"
    
    # Test empty/None values
    assert sanitize_email_header("") == ""
    assert sanitize_email_header(None) == ""
    
    print("✓ Test passed: Email header sanitization works correctly")


def test_email_notification_missing_credentials():
    """Test that missing SMTP credentials returns proper error status"""
    # Mock st.secrets to return empty credentials
    with patch('email_notification.st.secrets') as mock_secrets:
        mock_secrets.get = MagicMock(side_effect=lambda key, default: {
            'SMTP_HOST': 'smtp.gmail.com',
            'SMTP_PORT': 587,
            'SMTP_USER': '',  # Empty user
            'SMTP_PASSWORD': '',  # Empty password
            'SMTP_FROM_EMAIL': '',
            'SMTP_FROM_NAME': 'Test'
        }.get(key, default))
        
        success, message = send_email_notification(
            to_emails=['test@example.com'],
            client_name='Test Client',
            quote_total=1000.0,
            metric_file_content=b'test content'
        )
        
        assert success == False, "Should return False for missing credentials"
        assert "SMTP credentials not configured" in message, f"Expected error message, got: {message}"
        print("✓ Test passed: Missing credentials returns proper error")


def test_email_notification_success():
    """Test that successful email send returns success status"""
    # Mock streamlit secrets
    with patch('email_notification.st.secrets') as mock_secrets:
        mock_secrets.get = MagicMock(side_effect=lambda key, default: {
            'SMTP_HOST': 'smtp.gmail.com',
            'SMTP_PORT': 587,
            'SMTP_USER': 'test@example.com',
            'SMTP_PASSWORD': 'testpassword',
            'SMTP_FROM_EMAIL': 'test@example.com',
            'SMTP_FROM_NAME': 'Test Sender'
        }.get(key, default))
        
        # Mock SMTP
        with patch('email_notification.smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            success, message = send_email_notification(
                to_emails=['recipient@example.com'],
                client_name='Test Client',
                quote_total=1500.50,
                metric_file_content=b'test metric content',
                reference_number='TEST-001',
                site_location='Test Location',
                promoter_name='Test Promoter',
                contact_email='contact@example.com',
                notes='Test notes'
            )
            
            assert success == True, "Should return True for successful send"
            assert "Email sent successfully" in message, f"Expected success message, got: {message}"
            assert "1 recipient" in message, f"Expected recipient count, got: {message}"
            
            # Verify SMTP methods were called
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once_with('test@example.com', 'testpassword')
            mock_server.send_message.assert_called_once()
            mock_server.quit.assert_called_once()
            
            print("✓ Test passed: Successful send returns success status")


def test_email_notification_smtp_error():
    """Test that SMTP errors are properly caught and returned"""
    with patch('email_notification.st.secrets') as mock_secrets:
        mock_secrets.get = MagicMock(side_effect=lambda key, default: {
            'SMTP_HOST': 'smtp.gmail.com',
            'SMTP_PORT': 587,
            'SMTP_USER': 'test@example.com',
            'SMTP_PASSWORD': 'testpassword',
            'SMTP_FROM_EMAIL': 'test@example.com',
            'SMTP_FROM_NAME': 'Test Sender'
        }.get(key, default))
        
        # Mock SMTP to raise an exception
        with patch('email_notification.smtplib.SMTP') as mock_smtp:
            mock_smtp.side_effect = smtplib.SMTPAuthenticationError(535, b'Authentication failed')
            
            success, message = send_email_notification(
                to_emails=['recipient@example.com'],
                client_name='Test Client',
                quote_total=1000.0,
                metric_file_content=b'test content'
            )
            
            assert success == False, "Should return False when SMTP fails"
            assert "Failed to send email" in message, f"Expected error message, got: {message}"
            assert "Authentication" in message or "535" in message, f"Expected auth error details, got: {message}"
            
            print("✓ Test passed: SMTP errors are properly caught and returned")


def test_email_notification_multiple_recipients():
    """Test that multiple recipients are handled correctly"""
    with patch('email_notification.st.secrets') as mock_secrets:
        mock_secrets.get = MagicMock(side_effect=lambda key, default: {
            'SMTP_HOST': 'smtp.gmail.com',
            'SMTP_PORT': 587,
            'SMTP_USER': 'test@example.com',
            'SMTP_PASSWORD': 'testpassword',
            'SMTP_FROM_EMAIL': 'test@example.com',
            'SMTP_FROM_NAME': 'Test Sender'
        }.get(key, default))
        
        with patch('email_notification.smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            success, message = send_email_notification(
                to_emails=['recipient1@example.com', 'recipient2@example.com', 'recipient3@example.com'],
                client_name='Test Client',
                quote_total=2000.0,
                metric_file_content=b'test content'
            )
            
            assert success == True, "Should return True for successful send"
            assert "3 recipient" in message, f"Expected 3 recipients in message, got: {message}"
            
            print("✓ Test passed: Multiple recipients handled correctly")


def test_email_notification_with_csv_attachment():
    """Test that CSV allocation attachment is properly attached to email"""
    with patch('email_notification.st.secrets') as mock_secrets:
        mock_secrets.get = MagicMock(side_effect=lambda key, default: {
            'SMTP_HOST': 'smtp.gmail.com',
            'SMTP_PORT': 587,
            'SMTP_USER': 'test@example.com',
            'SMTP_PASSWORD': 'testpassword',
            'SMTP_FROM_EMAIL': 'test@example.com',
            'SMTP_FROM_NAME': 'Test Sender'
        }.get(key, default))
        
        with patch('email_notification.smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            # Create sample CSV content
            csv_content = "Bank,Habitat,Units,Cost\nNunthorpe,Grassland,10.0,1000.0\n"
            
            success, message = send_email_notification(
                to_emails=['recipient@example.com'],
                client_name='Test Client',
                quote_total=1500.0,
                metric_file_content=b'test metric content',
                csv_allocation_content=csv_content,
                reference_number='TEST-001',
                site_location='Test Location',
                promoter_name='Test Promoter',
                contact_email='contact@example.com'
            )
            
            assert success == True, "Should return True for successful send"
            assert "Email sent successfully" in message, f"Expected success message, got: {message}"
            
            # Verify that send_message was called (which means attachments were added)
            mock_server.send_message.assert_called_once()
            
            # Get the message that was sent
            sent_message = mock_server.send_message.call_args[0][0]
            
            # Verify message has attachments
            assert sent_message.is_multipart(), "Message should be multipart with attachments"
            
            # Count attachments (should be 2: metric file + CSV file)
            attachments = [part for part in sent_message.walk() if part.get_content_disposition() == 'attachment']
            assert len(attachments) >= 2, f"Expected at least 2 attachments (metric + CSV), got {len(attachments)}"
            
            # Verify CSV attachment is present
            csv_attachment_found = False
            for part in attachments:
                filename = part.get_filename()
                if filename and 'allocation.csv' in filename:
                    csv_attachment_found = True
                    break
            
            assert csv_attachment_found, "CSV allocation attachment should be present in email"
            
            print("✓ Test passed: CSV attachment is properly attached to email")


def test_email_notification_quote_accepted():
    """Test that quote_accepted email type sends correct notification"""
    import base64
    with patch('email_notification.st.secrets') as mock_secrets:
        mock_secrets.get = MagicMock(side_effect=lambda key, default: {
            'SMTP_HOST': 'smtp.gmail.com',
            'SMTP_PORT': 587,
            'SMTP_USER': 'test@example.com',
            'SMTP_PASSWORD': 'testpassword',
            'SMTP_FROM_EMAIL': 'test@example.com',
            'SMTP_FROM_NAME': 'Test Sender'
        }.get(key, default))
        
        with patch('email_notification.smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            # Test quote_accepted email type
            success, message = send_email_notification(
                to_emails=['team@example.com'],
                client_name='John Smith',
                quote_total=25000.0,
                metric_file_content=None,  # No metric file for acceptance
                email_type='quote_accepted',
                reference_number='BNG-A-12345',
                site_location='123 Test Street, London',
                promoter_name='Test Promoter Ltd',
                submitted_by_name='Jane Doe',
                contact_email='john@example.com',
                contact_number='07123456789',
                notes='Client wants to proceed ASAP',
                allocation_summary='- Grassland: 10.5 units @ £2,000/unit = £21,000\n',
                accepted_by='Jane Doe'
            )
            
            assert success == True, "Should return True for successful send"
            assert "Email sent successfully" in message, f"Expected success message, got: {message}"
            
            # Verify that send_message was called
            mock_server.send_message.assert_called_once()
            
            # Get the message that was sent
            sent_message = mock_server.send_message.call_args[0][0]
            
            # Verify subject line contains QUOTE ACCEPTED
            assert 'QUOTE ACCEPTED' in sent_message['Subject'], f"Subject should contain 'QUOTE ACCEPTED', got: {sent_message['Subject']}"
            assert 'BNG-A-12345' in sent_message['Subject'], f"Subject should contain reference number"
            assert 'John Smith' in sent_message['Subject'], f"Subject should contain client name"
            
            # Verify body content (may be base64 encoded)
            body = sent_message.get_payload()
            if isinstance(body, list):
                body = body[0].get_payload()
            
            # Decode if base64 encoded
            try:
                decoded_body = base64.b64decode(body).decode('utf-8')
            except Exception:
                decoded_body = body
            
            assert 'ACCEPTED BY CLIENT' in decoded_body, f"Body should indicate quote acceptance"
            assert '25,000' in decoded_body, f"Body should contain quote total"
            assert 'John Smith' in decoded_body, f"Body should contain client name"
            assert 'BNG-A-12345' in decoded_body, f"Body should contain reference number"
            
            print("✓ Test passed: quote_accepted email type works correctly")


if __name__ == '__main__':
    print("Running email notification tests...")
    print()
    
    test_sanitize_email_header()
    test_email_notification_missing_credentials()
    test_email_notification_success()
    test_email_notification_smtp_error()
    test_email_notification_multiple_recipients()
    test_email_notification_with_csv_attachment()
    test_email_notification_quote_accepted()
    
    print()
    print("=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)
