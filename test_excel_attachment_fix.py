"""
Test Excel attachment fix - verify correct MIME types and filenames
"""

import sys
from unittest.mock import MagicMock, patch
import smtplib

# Mock streamlit before importing email_notification
sys.modules['streamlit'] = MagicMock()

from email_notification import send_email_notification, get_excel_mime_type


def test_get_excel_mime_type():
    """Test that get_excel_mime_type returns correct MIME types for different Excel formats"""
    
    # Test .xlsx
    maintype, subtype = get_excel_mime_type("test_metric.xlsx")
    assert maintype == 'application', f"Expected 'application', got '{maintype}'"
    assert subtype == 'vnd.openxmlformats-officedocument.spreadsheetml.sheet', \
        f"Expected 'vnd.openxmlformats-officedocument.spreadsheetml.sheet', got '{subtype}'"
    print("✓ .xlsx MIME type correct")
    
    # Test .xlsm
    maintype, subtype = get_excel_mime_type("test_metric.xlsm")
    assert maintype == 'application', f"Expected 'application', got '{maintype}'"
    assert subtype == 'vnd.ms-excel.sheet.macroEnabled.12', \
        f"Expected 'vnd.ms-excel.sheet.macroEnabled.12', got '{subtype}'"
    print("✓ .xlsm MIME type correct")
    
    # Test .xlsb
    maintype, subtype = get_excel_mime_type("test_metric.xlsb")
    assert maintype == 'application', f"Expected 'application', got '{maintype}'"
    assert subtype == 'vnd.ms-excel.sheet.binary.macroEnabled.12', \
        f"Expected 'vnd.ms-excel.sheet.binary.macroEnabled.12', got '{subtype}'"
    print("✓ .xlsb MIME type correct")
    
    # Test uppercase extensions
    maintype, subtype = get_excel_mime_type("TEST_METRIC.XLSX")
    assert maintype == 'application', f"Expected 'application', got '{maintype}'"
    assert subtype == 'vnd.openxmlformats-officedocument.spreadsheetml.sheet', \
        f"Expected correct MIME type for uppercase .XLSX, got '{subtype}'"
    print("✓ Uppercase .XLSX MIME type correct")
    
    # Test unknown extension (fallback)
    maintype, subtype = get_excel_mime_type("test_metric.unknown")
    assert maintype == 'application', f"Expected 'application', got '{maintype}'"
    assert subtype == 'octet-stream', f"Expected 'octet-stream' for unknown extension, got '{subtype}'"
    print("✓ Unknown extension falls back to octet-stream")


def test_xlsx_attachment_with_correct_mime_type():
    """Test that .xlsx files are attached with correct MIME type"""
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
            
            # Create dummy Excel content (Excel files start with PK)
            excel_content = b'PK\x03\x04' + b'\x00' * 100
            
            success, message = send_email_notification(
                to_emails=['recipient@example.com'],
                client_name='Test Client',
                quote_total=1500.0,
                metric_file_content=excel_content,
                metric_filename='BNG-A-12345_Client_Metric.xlsx',
                reference_number='BNG-A-12345',
                site_location='Test Location',
                promoter_name='Test Promoter',
                contact_email='contact@example.com'
            )
            
            assert success == True, "Should return True for successful send"
            
            # Get the message that was sent
            sent_message = mock_server.send_message.call_args[0][0]
            
            # Find the Excel attachment
            excel_attachment = None
            for part in sent_message.walk():
                if part.get_content_disposition() == 'attachment':
                    filename = part.get_filename()
                    if filename and filename.endswith('.xlsx'):
                        excel_attachment = part
                        break
            
            assert excel_attachment is not None, "Excel attachment should be present"
            assert excel_attachment.get_content_type() == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', \
                f"Expected correct MIME type for .xlsx, got {excel_attachment.get_content_type()}"
            assert excel_attachment.get_filename() == 'BNG-A-12345_Client_Metric.xlsx', \
                f"Expected correct filename, got {excel_attachment.get_filename()}"
            
            print("✓ .xlsx attachment has correct MIME type and filename")


def test_xlsm_attachment_with_correct_mime_type():
    """Test that .xlsm files are attached with correct MIME type"""
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
            
            # Create dummy Excel content (Excel files start with PK)
            excel_content = b'PK\x03\x04' + b'\x00' * 100
            
            success, message = send_email_notification(
                to_emails=['recipient@example.com'],
                client_name='Test Client',
                quote_total=1500.0,
                metric_file_content=excel_content,
                metric_filename='BNG-A-12345_Metric_with_Macros.xlsm',
                reference_number='BNG-A-12345',
                site_location='Test Location',
                promoter_name='Test Promoter',
                contact_email='contact@example.com'
            )
            
            assert success == True, "Should return True for successful send"
            
            # Get the message that was sent
            sent_message = mock_server.send_message.call_args[0][0]
            
            # Find the Excel attachment
            excel_attachment = None
            for part in sent_message.walk():
                if part.get_content_disposition() == 'attachment':
                    filename = part.get_filename()
                    if filename and filename.endswith('.xlsm'):
                        excel_attachment = part
                        break
            
            assert excel_attachment is not None, "Excel attachment should be present"
            assert excel_attachment.get_content_type() == 'application/vnd.ms-excel.sheet.macroenabled.12', \
                f"Expected correct MIME type for .xlsm, got {excel_attachment.get_content_type()}"
            assert excel_attachment.get_filename() == 'BNG-A-12345_Metric_with_Macros.xlsm', \
                f"Expected correct filename, got {excel_attachment.get_filename()}"
            
            print("✓ .xlsm attachment has correct MIME type and filename")


def test_xlsb_attachment_with_correct_mime_type():
    """Test that .xlsb files are attached with correct MIME type"""
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
            
            # Create dummy Excel content (Excel files start with PK)
            excel_content = b'PK\x03\x04' + b'\x00' * 100
            
            success, message = send_email_notification(
                to_emails=['recipient@example.com'],
                client_name='Test Client',
                quote_total=1500.0,
                metric_file_content=excel_content,
                metric_filename='BNG-A-12345_Binary_Metric.xlsb',
                reference_number='BNG-A-12345',
                site_location='Test Location',
                promoter_name='Test Promoter',
                contact_email='contact@example.com'
            )
            
            assert success == True, "Should return True for successful send"
            
            # Get the message that was sent
            sent_message = mock_server.send_message.call_args[0][0]
            
            # Find the Excel attachment
            excel_attachment = None
            for part in sent_message.walk():
                if part.get_content_disposition() == 'attachment':
                    filename = part.get_filename()
                    if filename and filename.endswith('.xlsb'):
                        excel_attachment = part
                        break
            
            assert excel_attachment is not None, "Excel attachment should be present"
            assert excel_attachment.get_content_type() == 'application/vnd.ms-excel.sheet.binary.macroenabled.12', \
                f"Expected correct MIME type for .xlsb, got {excel_attachment.get_content_type()}"
            assert excel_attachment.get_filename() == 'BNG-A-12345_Binary_Metric.xlsb', \
                f"Expected correct filename, got {excel_attachment.get_filename()}"
            
            print("✓ .xlsb attachment has correct MIME type and filename")


def test_backward_compatibility_without_metric_filename():
    """Test that the function still works without metric_filename parameter (backward compatibility)"""
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
            
            # Create dummy Excel content
            excel_content = b'PK\x03\x04' + b'\x00' * 100
            
            # Call without metric_filename parameter (backward compatibility)
            success, message = send_email_notification(
                to_emails=['recipient@example.com'],
                client_name='Test Client',
                quote_total=1500.0,
                metric_file_content=excel_content,
                reference_number='BNG-A-12345',
                site_location='Test Location',
                promoter_name='Test Promoter',
                contact_email='contact@example.com'
            )
            
            assert success == True, "Should return True for successful send"
            
            # Get the message that was sent
            sent_message = mock_server.send_message.call_args[0][0]
            
            # Find the Excel attachment
            excel_attachment = None
            for part in sent_message.walk():
                if part.get_content_disposition() == 'attachment':
                    filename = part.get_filename()
                    if filename and 'metric' in filename:
                        excel_attachment = part
                        break
            
            assert excel_attachment is not None, "Excel attachment should be present"
            # Should fall back to .xlsx extension
            assert excel_attachment.get_filename() == 'BNG-A-12345_metric.xlsx', \
                f"Expected fallback filename, got {excel_attachment.get_filename()}"
            assert excel_attachment.get_content_type() == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', \
                f"Expected correct MIME type for .xlsx fallback, got {excel_attachment.get_content_type()}"
            
            print("✓ Backward compatibility maintained - defaults to .xlsx")


if __name__ == '__main__':
    print("Running Excel attachment fix tests...")
    print()
    
    test_get_excel_mime_type()
    print()
    test_xlsx_attachment_with_correct_mime_type()
    test_xlsm_attachment_with_correct_mime_type()
    test_xlsb_attachment_with_correct_mime_type()
    test_backward_compatibility_without_metric_filename()
    
    print()
    print("=" * 60)
    print("All Excel attachment tests passed! ✓")
    print("=" * 60)
