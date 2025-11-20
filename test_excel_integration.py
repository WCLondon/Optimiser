"""
Integration test to verify end-to-end Excel attachment workflow
"""

import sys
from unittest.mock import MagicMock, patch

# Mock streamlit before importing
sys.modules['streamlit'] = MagicMock()

from email_notification import send_email_notification


def test_end_to_end_xlsx_workflow():
    """Test complete workflow with .xlsx file"""
    with patch('email_notification.st.secrets') as mock_secrets:
        mock_secrets.get = MagicMock(side_effect=lambda key, default: {
            'SMTP_HOST': 'smtp.gmail.com',
            'SMTP_PORT': 587,
            'SMTP_USER': 'test@example.com',
            'SMTP_PASSWORD': 'testpassword',
            'SMTP_FROM_EMAIL': 'test@example.com',
            'SMTP_FROM_NAME': 'Wild Capital BNG'
        }.get(key, default))
        
        with patch('email_notification.smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            # Simulate uploaded .xlsx file
            excel_content = b'PK\x03\x04' + b'\x00' * 100
            original_filename = 'Client_BNG_Metric_v4.xlsx'
            
            # Send email as promoter_app.py would
            success, message = send_email_notification(
                to_emails=['reviewer@example.com'],
                client_name='Test Client Ltd',
                quote_total=25000.00,
                metric_file_content=excel_content,
                metric_filename=f"BNG-A-12345_{original_filename}",
                reference_number='BNG-A-12345',
                site_location='London, SW1A 1AA',
                promoter_name='Test Promoter',
                contact_email='client@example.com',
                notes='Test notes',
                email_type='quote_notification',
                csv_allocation_content='Bank,Habitat,Units\nTest,Grassland,10.0\n'
            )
            
            assert success == True, f"Expected success, got: {message}"
            
            # Verify message was sent
            sent_message = mock_server.send_message.call_args[0][0]
            
            # Find and verify Excel attachment
            excel_attachment = None
            csv_attachment = None
            for part in sent_message.walk():
                if part.get_content_disposition() == 'attachment':
                    filename = part.get_filename()
                    if filename and filename.endswith('.xlsx'):
                        excel_attachment = part
                    elif filename and filename.endswith('.csv'):
                        csv_attachment = part
            
            assert excel_attachment is not None, "Excel attachment must be present"
            assert excel_attachment.get_filename() == 'BNG-A-12345_Client_BNG_Metric_v4.xlsx', \
                f"Filename mismatch: {excel_attachment.get_filename()}"
            assert excel_attachment.get_content_type() == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', \
                f"MIME type mismatch: {excel_attachment.get_content_type()}"
            
            assert csv_attachment is not None, "CSV attachment must be present"
            
            print("✓ End-to-end .xlsx workflow successful")


def test_end_to_end_xlsm_workflow():
    """Test complete workflow with .xlsm file (with macros)"""
    with patch('email_notification.st.secrets') as mock_secrets:
        mock_secrets.get = MagicMock(side_effect=lambda key, default: {
            'SMTP_HOST': 'smtp.gmail.com',
            'SMTP_PORT': 587,
            'SMTP_USER': 'test@example.com',
            'SMTP_PASSWORD': 'testpassword',
            'SMTP_FROM_EMAIL': 'test@example.com',
            'SMTP_FROM_NAME': 'Wild Capital BNG'
        }.get(key, default))
        
        with patch('email_notification.smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            # Simulate uploaded .xlsm file
            excel_content = b'PK\x03\x04' + b'\x00' * 100
            original_filename = 'BNG_Metric_4.0_with_macros.xlsm'
            
            # Send email as quickopt_app.py would for full quote
            success, message = send_email_notification(
                to_emails=['reviewer@example.com'],
                client_name='Big Project Ltd',
                quote_total=75000.00,
                metric_file_content=excel_content,
                metric_filename=f"BNG-A-67890_{original_filename}",
                reference_number='BNG-A-67890',
                site_location='Manchester, M1 1AA',
                promoter_name='WC0323',
                contact_email='bigproject@example.com',
                notes='Large project requiring review',
                email_type='full_quote',
                email_html_body='<html><body>Full quote HTML</body></html>',
                admin_fee=500.00,
                csv_allocation_content='Bank,Habitat,Units\nTest,Woodland,25.0\n'
            )
            
            assert success == True, f"Expected success, got: {message}"
            
            # Verify message was sent
            sent_message = mock_server.send_message.call_args[0][0]
            
            # Find and verify Excel attachment
            excel_attachment = None
            for part in sent_message.walk():
                if part.get_content_disposition() == 'attachment':
                    filename = part.get_filename()
                    if filename and filename.endswith('.xlsm'):
                        excel_attachment = part
                        break
            
            assert excel_attachment is not None, "Excel .xlsm attachment must be present"
            assert excel_attachment.get_filename() == 'BNG-A-67890_BNG_Metric_4.0_with_macros.xlsm', \
                f"Filename mismatch: {excel_attachment.get_filename()}"
            assert excel_attachment.get_content_type() == 'application/vnd.ms-excel.sheet.macroenabled.12', \
                f"MIME type mismatch: {excel_attachment.get_content_type()}"
            
            print("✓ End-to-end .xlsm workflow successful")


def test_end_to_end_xlsb_workflow():
    """Test complete workflow with .xlsb file (binary format)"""
    with patch('email_notification.st.secrets') as mock_secrets:
        mock_secrets.get = MagicMock(side_effect=lambda key, default: {
            'SMTP_HOST': 'smtp.gmail.com',
            'SMTP_PORT': 587,
            'SMTP_USER': 'test@example.com',
            'SMTP_PASSWORD': 'testpassword',
            'SMTP_FROM_EMAIL': 'test@example.com',
            'SMTP_FROM_NAME': 'Wild Capital BNG'
        }.get(key, default))
        
        with patch('email_notification.smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            # Simulate uploaded .xlsb file
            excel_content = b'PK\x03\x04' + b'\x00' * 100
            original_filename = 'BNG_Metric_Binary.xlsb'
            
            # Send email
            success, message = send_email_notification(
                to_emails=['reviewer@example.com'],
                client_name='Binary Test Client',
                quote_total=30000.00,
                metric_file_content=excel_content,
                metric_filename=f"BNG-A-11111_{original_filename}",
                reference_number='BNG-A-11111',
                site_location='Birmingham, B1 1AA',
                promoter_name='Test Promoter',
                contact_email='binary@example.com'
            )
            
            assert success == True, f"Expected success, got: {message}"
            
            # Verify message was sent
            sent_message = mock_server.send_message.call_args[0][0]
            
            # Find and verify Excel attachment
            excel_attachment = None
            for part in sent_message.walk():
                if part.get_content_disposition() == 'attachment':
                    filename = part.get_filename()
                    if filename and filename.endswith('.xlsb'):
                        excel_attachment = part
                        break
            
            assert excel_attachment is not None, "Excel .xlsb attachment must be present"
            assert excel_attachment.get_filename() == 'BNG-A-11111_BNG_Metric_Binary.xlsb', \
                f"Filename mismatch: {excel_attachment.get_filename()}"
            assert excel_attachment.get_content_type() == 'application/vnd.ms-excel.sheet.binary.macroenabled.12', \
                f"MIME type mismatch: {excel_attachment.get_content_type()}"
            
            print("✓ End-to-end .xlsb workflow successful")


if __name__ == '__main__':
    print("Running end-to-end Excel workflow integration tests...")
    print()
    
    test_end_to_end_xlsx_workflow()
    test_end_to_end_xlsm_workflow()
    test_end_to_end_xlsb_workflow()
    
    print()
    print("=" * 60)
    print("All end-to-end integration tests passed! ✓")
    print("=" * 60)
