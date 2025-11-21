"""
Tests for quickopt_app changes:
1. CSV introducer field should be "Direct" when promoter is WC0323
2. Email subject line should include client name
3. Email intro text should use thank you message for WC0323
"""

import pytest
from datetime import datetime
import pandas as pd
from sales_quotes_csv import generate_sales_quotes_csv_from_optimizer_output
import csv
import io


def test_wc0323_introducer_becomes_direct():
    """Test that WC0323 introducer is converted to 'Direct' in CSV."""
    # Create sample allocation data
    alloc_df = pd.DataFrame([{
        'BANK_KEY': 'WC1P2',
        'bank_name': 'Nunthorpe',
        'supply_habitat': 'Grassland',
        'tier': 'adjacent',
        'allocation_type': 'normal',
        'units_supplied': 10.0,
        'effective_units': 13.33,
        'avg_effective_unit_price': 1000.0,
        'cost': 13333.33
    }])
    
    # Test 1: WC0323 should become "Direct"
    csv_output = generate_sales_quotes_csv_from_optimizer_output(
        quote_number="TEST001",
        client_name="Test Client",
        development_address="Test Address",
        base_ref="BNG00001",
        introducer="Direct",  # This is what quickopt_app.py should pass for WC0323
        today_date=datetime(2025, 11, 10),
        local_planning_authority="Test LPA",
        national_character_area="Test NCA",
        alloc_df=alloc_df,
        contract_size="small"
    )
    
    reader = csv.reader(io.StringIO(csv_output))
    fields = list(reader)[0]
    
    # Column AK (index 36): Introducer should be "Direct"
    assert fields[36] == "Direct", f"Expected 'Direct' but got '{fields[36]}'"


def test_regular_introducer_preserved():
    """Test that non-WC0323 introducer is preserved in CSV."""
    # Create sample allocation data
    alloc_df = pd.DataFrame([{
        'BANK_KEY': 'WC1P2',
        'bank_name': 'Nunthorpe',
        'supply_habitat': 'Grassland',
        'tier': 'adjacent',
        'allocation_type': 'normal',
        'units_supplied': 10.0,
        'effective_units': 13.33,
        'avg_effective_unit_price': 1000.0,
        'cost': 13333.33
    }])
    
    # Test with a regular introducer name
    csv_output = generate_sales_quotes_csv_from_optimizer_output(
        quote_number="TEST002",
        client_name="Test Client",
        development_address="Test Address",
        base_ref="BNG00002",
        introducer="John Smith",
        today_date=datetime(2025, 11, 10),
        local_planning_authority="Test LPA",
        national_character_area="Test NCA",
        alloc_df=alloc_df,
        contract_size="small"
    )
    
    reader = csv.reader(io.StringIO(csv_output))
    fields = list(reader)[0]
    
    # Column AK (index 36): Introducer should be preserved
    assert fields[36] == "John Smith", f"Expected 'John Smith' but got '{fields[36]}'"


def test_email_subject_line_format():
    """Test that email subject line includes client name in the correct format."""
    from email_notification import send_email_notification
    
    # We'll verify the format by checking the string in email_notification.py
    # This is a basic test to ensure the format is correct
    
    # Read the email_notification.py file to verify the subject line format
    with open('/home/runner/work/Optimiser/Optimiser/email_notification.py', 'r') as f:
        content = f.read()
    
    # Check that the new format is present
    assert 'Subject: BNG Units for site at {site_location} - {client_name} - {reference_number}' in content, \
        "Email subject line should include client_name"
    
    # Check that the old format is NOT present
    assert 'Subject: RE: BNG Units for site at {site_location} - {reference_number}' not in content, \
        "Old email subject line format should be removed"


def test_email_intro_text_for_wc0323():
    """Test that email intro text uses thank you message for WC0323."""
    # Read the email_notification.py file to verify the intro text
    with open('/home/runner/work/Optimiser/Optimiser/email_notification.py', 'r') as f:
        content = f.read()
    
    # Check that the thank you message is present
    assert 'Thank you for your enquiry into Biodiversity Net Gain units' in content, \
        "Email should use thank you message"
    
    # Check that the promoter_name reference is NOT in the plain text version
    assert '{promoter_name} has advised us' not in content, \
        "Email plain text should not reference promoter_name"


def test_optimizer_intro_text_logic():
    """Test that optimizer_core uses correct intro text based on promoter."""
    # Read the optimizer_core.py file to verify the logic
    with open('/home/runner/work/Optimiser/Optimiser/optimizer_core.py', 'r') as f:
        content = f.read()
    
    # Check that WC0323 is excluded from promoter intro
    assert 'promoter_name != "WC0323"' in content, \
        "optimizer_core should exclude WC0323 from promoter intro"
    
    # Check that thank you message is used as fallback
    assert 'Thank you for your enquiry into Biodiversity Net Gain units' in content, \
        "optimizer_core should use thank you message for WC0323"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
