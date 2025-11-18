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

from email_notification import send_email_notification


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


if __name__ == '__main__':
    print("Running email notification tests...")
    print()
    
    test_email_notification_missing_credentials()
    test_email_notification_success()
    test_email_notification_smtp_error()
    test_email_notification_multiple_recipients()
    
    print()
    print("=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)
