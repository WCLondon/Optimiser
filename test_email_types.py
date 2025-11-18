"""
Test email notification functionality for different email types
"""

import sys
from unittest.mock import MagicMock, patch

# Mock streamlit before importing email_notification
sys.modules['streamlit'] = MagicMock()

from email_notification import send_email_notification


def test_quote_notification_email_type():
    """Test that quote notification email type works correctly (< £50k)"""
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
                to_emails=['reviewer@example.com'],
                client_name='Test Client',
                quote_total=25000.00,
                metric_file_content=b'test metric content',
                reference_number='TEST-001',
                site_location='Test Location',
                promoter_name='Test Promoter',
                contact_email='customer@example.com',
                notes='Test notes',
                email_type='quote_notification'
            )
            
            assert success == True, "Should return True for successful send"
            assert "Email sent successfully" in message
            
            # Check that send_message was called
            mock_server.send_message.assert_called_once()
            
            # Get the message that was sent
            sent_message = mock_server.send_message.call_args[0][0]
            
            # Verify subject contains "Quote Request"
            assert 'Quote Request' in sent_message['Subject'], f"Subject should contain 'Quote Request', got: {sent_message['Subject']}"
            
            print("✓ Test passed: Quote notification email type works correctly")


def test_full_quote_email_type():
    """Test that full quote email type works correctly (>= £50k)"""
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
            
            # Mock HTML body for full quote
            test_html = "<html><body><h1>Test Quote</h1><table>...</table></body></html>"
            
            success, message = send_email_notification(
                to_emails=['reviewer@example.com'],
                client_name='Big Client',
                quote_total=75000.00,
                metric_file_content=b'test metric content',
                reference_number='',  # Should be blank
                site_location='Large Development Site',
                promoter_name='Premium Promoter',
                contact_email='bigcustomer@example.com',
                notes='High value quote',
                email_type='full_quote',
                email_html_body=test_html,
                admin_fee=500.00
            )
            
            assert success == True, "Should return True for successful send"
            assert "Email sent successfully" in message
            
            # Check that send_message was called
            mock_server.send_message.assert_called_once()
            
            # Get the message that was sent
            sent_message = mock_server.send_message.call_args[0][0]
            
            # Verify subject contains "Review & Forwarding"
            assert 'Review & Forwarding' in sent_message['Subject'], f"Subject should contain 'Review & Forwarding', got: {sent_message['Subject']}"
            
            # Verify total with admin fee is in subject
            assert '£75,500' in sent_message['Subject'], f"Subject should contain total with admin, got: {sent_message['Subject']}"
            
            # Verify the message is multipart (has both text and HTML)
            assert sent_message.is_multipart(), "Message should be multipart (text + HTML)"
            
            # Get the parts - should be multipart/mixed with alternative + attachment
            parts = sent_message.get_payload()
            assert len(parts) >= 1, "Should have at least 1 part (alternative content)"
            
            # First part should be multipart/alternative
            assert parts[0].is_multipart(), "First part should be multipart/alternative"
            
            print("✓ Test passed: Full quote email type works correctly")


def test_full_quote_missing_html_body():
    """Test that full quote email type fails without HTML body"""
    with patch('email_notification.st.secrets') as mock_secrets:
        mock_secrets.get = MagicMock(side_effect=lambda key, default: {
            'SMTP_HOST': 'smtp.gmail.com',
            'SMTP_PORT': 587,
            'SMTP_USER': 'test@example.com',
            'SMTP_PASSWORD': 'testpassword',
            'SMTP_FROM_EMAIL': 'test@example.com',
            'SMTP_FROM_NAME': 'Test Sender'
        }.get(key, default))
        
        success, message = send_email_notification(
            to_emails=['reviewer@example.com'],
            client_name='Test Client',
            quote_total=60000.00,
            metric_file_content=b'test content',
            email_type='full_quote',
            # Missing email_html_body
            admin_fee=500.00
        )
        
        assert success == False, "Should return False when HTML body is missing"
        assert "email_html_body is required" in message, f"Expected error about missing HTML body, got: {message}"
        
        print("✓ Test passed: Full quote email type fails without HTML body")


def test_full_quote_email_content():
    """Test that full quote email contains required content"""
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
            
            # Mock HTML body for full quote
            test_html = "<html><body><h1>Test Quote</h1></body></html>"
            
            success, message = send_email_notification(
                to_emails=['reviewer@example.com'],
                client_name='Test Client',
                quote_total=60000.00,
                metric_file_content=b'test content',
                reference_number='',
                site_location='Test Site',
                promoter_name='Test Promoter',
                contact_email='customer@example.com',
                notes='',
                email_type='full_quote',
                email_html_body=test_html,
                admin_fee=500.00
            )
            
            assert success == True
            
            # Get the sent message
            sent_message = mock_server.send_message.call_args[0][0]
            
            # The structure is now multipart/mixed containing multipart/alternative
            parts = sent_message.get_payload()
            
            # First part should be the multipart/alternative (text + HTML)
            alternative_part = parts[0]
            
            # Get the text part from the alternative
            alternative_parts = alternative_part.get_payload()
            text_part = alternative_parts[0]
            
            # Get payload and decode if necessary
            text_content = text_part.get_payload(decode=True)
            if isinstance(text_content, bytes):
                text_content = text_content.decode('utf-8')
            else:
                text_content = str(text_content)
            
            # Verify required content in plain text version
            assert "Prices exclude VAT" in text_content, "Should contain VAT disclaimer"
            assert "legal costs for contract amendments" in text_content, "Should contain legal costs disclaimer"
            assert "Next Steps" in text_content, "Should contain Next Steps section"
            assert "Buy It Now" in text_content, "Should contain Buy It Now option"
            assert "Reservation & Purchase" in text_content, "Should contain Reservation & Purchase option"
            assert "pre-commencement, not a pre-planning" in text_content, "Should contain BNG condition info"
            
            print("✓ Test passed: Full quote email contains all required content")


if __name__ == '__main__':
    print("Running email type tests...")
    print()
    
    test_quote_notification_email_type()
    test_full_quote_email_type()
    test_full_quote_missing_html_body()
    test_full_quote_email_content()
    
    print()
    print("=" * 60)
    print("All email type tests passed! ✓")
    print("=" * 60)
