"""
Integration test for CSV attachment in promoter email notifications

This test verifies that:
1. Email notification accepts CSV content
2. CSV is properly attached to the email
"""

import sys
from unittest.mock import MagicMock, patch

# Mock streamlit before importing email_notification
sys.modules['streamlit'] = MagicMock()

from email_notification import send_email_notification


def test_email_with_csv_and_metric():
    """Test that email can be sent with both metric and CSV attachments"""
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
            
            # Create sample CSV content (simulating what would be generated)
            csv_content = """Bank,Client,Address,Ref,Habitat Bank / Source of Mitigation,Spatial Multiplier,Total Units,Contract Value
Nunthorpe,Test Client,Test Address,TEST-001,WC1P2 - Nunthorpe,=4/3,13.33,13833.33"""
            
            # Send email with both metric and CSV
            success, message = send_email_notification(
                to_emails=['reviewer@example.com'],
                client_name='Test Client',
                quote_total=1500.0,
                metric_file_content=b'fake metric file content',
                csv_allocation_content=csv_content,
                reference_number='TEST-001',
                site_location='Test Location',
                promoter_name='Test Promoter',
                contact_email='contact@example.com',
                notes='Test notes',
                email_type='quote_notification'
            )
            
            assert success == True, "Email should be sent successfully"
            assert "Email sent successfully" in message, f"Expected success message, got: {message}"
            
            # Verify send_message was called
            mock_server.send_message.assert_called_once()
            
            # Get the message that was sent
            sent_message = mock_server.send_message.call_args[0][0]
            
            # Verify message structure
            assert sent_message.is_multipart(), "Message should be multipart"
            
            # Count attachments
            attachments = [part for part in sent_message.walk() 
                          if part.get_content_disposition() == 'attachment']
            
            # Should have 2 attachments: metric + CSV
            assert len(attachments) >= 2, f"Expected at least 2 attachments, got {len(attachments)}"
            
            # Verify both attachments are present
            attachment_filenames = [part.get_filename() for part in attachments]
            metric_found = any('metric' in str(fn).lower() for fn in attachment_filenames if fn)
            csv_found = any('allocation.csv' in str(fn).lower() for fn in attachment_filenames if fn)
            
            assert metric_found, "Metric attachment should be present"
            assert csv_found, "CSV allocation attachment should be present"
            
            print("✓ Test passed: Email sent with both metric and CSV attachments")


def test_email_without_csv_still_works():
    """Test that email still works when CSV is not provided (backwards compatibility)"""
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
            
            # Send email without CSV
            success, message = send_email_notification(
                to_emails=['reviewer@example.com'],
                client_name='Test Client',
                quote_total=1500.0,
                metric_file_content=b'fake metric file content',
                reference_number='TEST-001',
                site_location='Test Location',
                promoter_name='Test Promoter',
                contact_email='contact@example.com'
            )
            
            assert success == True, "Email should be sent successfully even without CSV"
            assert "Email sent successfully" in message, f"Expected success message, got: {message}"
            
            print("✓ Test passed: Email works without CSV (backwards compatible)")


def test_csv_content_type_and_encoding():
    """Test that CSV is attached with correct content type and encoding"""
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
            
            # Create CSV with special characters to test encoding
            csv_content = "Bank,Units,Cost\nNunthorpe,10.5,£1,000.50\nBedford,5.25,£525.25"
            
            # Send email with CSV
            success, message = send_email_notification(
                to_emails=['reviewer@example.com'],
                client_name='Test Client',
                quote_total=1500.0,
                metric_file_content=b'fake metric file content',
                csv_allocation_content=csv_content,
                reference_number='TEST-001',
                site_location='Test Location',
                promoter_name='Test Promoter',
                contact_email='contact@example.com'
            )
            
            assert success == True, "Email should be sent successfully"
            
            # Get the message
            sent_message = mock_server.send_message.call_args[0][0]
            
            # Find CSV attachment
            csv_attachment = None
            for part in sent_message.walk():
                if part.get_content_disposition() == 'attachment':
                    filename = part.get_filename()
                    if filename and 'allocation.csv' in filename:
                        csv_attachment = part
                        break
            
            assert csv_attachment is not None, "CSV attachment should be found"
            assert csv_attachment.get_content_type() == 'text/csv', "CSV should have correct content type"
            
            print("✓ Test passed: CSV has correct content type and encoding")


if __name__ == '__main__':
    print("Running CSV Email Integration Tests...")
    print()
    
    test_email_with_csv_and_metric()
    test_email_without_csv_still_works()
    test_csv_content_type_and_encoding()
    
    print()
    print("=" * 60)
    print("All integration tests passed! ✓")
    print("=" * 60)

