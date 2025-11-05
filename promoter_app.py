"""
Streamlit Promoter Quote Form with Login
Single app for all promoters - login determines which promoter's submissions are tracked
Username: Promoter name from database
Password: Promoter name + "1" (e.g., EPT → EPT1)
"""

import streamlit as st
import pandas as pd
import tempfile
import os
from datetime import datetime, timedelta
from pathlib import Path
from io import BytesIO
from typing import Optional, Dict, List

# Import existing modules
import metric_reader
import repo
from database import SubmissionsDB

# Configure page
st.set_page_config(
    page_title="BNG Quote Request",
    page_icon="🌿",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Constants
AUTO_QUOTE_THRESHOLD = 20000.0  # £20,000
MAX_FILE_SIZE_MB = 15

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'promoter_name' not in st.session_state:
    st.session_state.promoter_name = None
if 'submission_complete' not in st.session_state:
    st.session_state.submission_complete = False
if 'submission_result' not in st.session_state:
    st.session_state.submission_result = None


def get_promoters() -> List[Dict]:
    """
    Load promoters from database
    Returns list of promoter dictionaries with name, discount info, etc.
    """
    try:
        # Fetch promoters from introducers table
        engine = repo.get_db_engine()
        with engine.connect() as conn:
            from sqlalchemy import text
            result = conn.execute(text("""
                SELECT DISTINCT 
                    name,
                    discount_type,
                    discount_value
                FROM introducers 
                WHERE name IS NOT NULL 
                AND name != ''
                ORDER BY name
            """))
            
            promoters = []
            for row in result:
                promoters.append({
                    'name': row[0],
                    'discount_type': row[1],
                    'discount_value': row[2]
                })
            
            return promoters
    except Exception as e:
        st.error(f"Error loading promoters: {str(e)}")
        # Return some default promoters for testing
        return [
            {'name': 'EPT', 'discount_type': None, 'discount_value': None},
            {'name': 'Arbtech', 'discount_type': None, 'discount_value': None},
            {'name': 'Cypher', 'discount_type': None, 'discount_value': None}
        ]


def authenticate(username: str, password: str) -> bool:
    """
    Authenticate promoter
    Username: Promoter name (case-insensitive)
    Password: Promoter name + "1"
    """
    promoters = get_promoters()
    
    # Check if username exists (case-insensitive)
    for promoter in promoters:
        if promoter['name'].upper() == username.upper():
            # Password is promoter name + "1"
            expected_password = promoter['name'] + "1"
            if password == expected_password:
                return True
    
    return False


def show_login_page():
    """Display login page"""
    st.markdown("""
    <div class="promoter-header">
        <div class="form-title">BNG Quote System</div>
        <div class="form-subtitle">Promoter Login</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Get available promoters
    promoters = get_promoters()
    promoter_names = [p['name'] for p in promoters]
    
    st.info(f"📋 Available promoters: {', '.join(promoter_names)}")
    
    with st.form("login_form"):
        st.subheader("Login")
        
        username = st.text_input(
            "Username",
            placeholder="Enter promoter name",
            help="Your promoter name (e.g., EPT, Arbtech)"
        )
        
        password = st.text_input(
            "Password",
            type="password",
            placeholder="Enter password",
            help="Password is your promoter name + 1"
        )
        
        submit = st.form_submit_button("🔐 Login", use_container_width=True)
        
        if submit:
            if not username or not password:
                st.error("Please enter both username and password")
            elif authenticate(username, password):
                st.session_state.authenticated = True
                st.session_state.promoter_name = username.upper()
                st.success(f"✅ Welcome, {username.upper()}!")
                st.rerun()
            else:
                st.error("❌ Invalid username or password")
                st.caption("💡 Hint: Password is your promoter name + 1 (e.g., EPT → EPT1)")
    
    # Show example
    st.markdown("---")
    st.caption("**Example:**")
    st.caption("• Username: `EPT` → Password: `EPT1`")
    st.caption("• Username: `Arbtech` → Password: `Arbtech1`")


def logout():
    """Clear session and logout"""
    st.session_state.authenticated = False
    st.session_state.promoter_name = None
    st.session_state.submission_complete = False
    st.session_state.submission_result = None
    st.rerun()

# Check authentication
if not st.session_state.authenticated:
    # Custom CSS for login page
    st.markdown("""
<style>
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Center content */
    .main > div {
        padding-top: 2rem;
        max-width: 700px;
        margin: 0 auto;
    }
    
    /* Header styling */
    .promoter-header {
        text-align: center;
        padding: 2rem 0;
    }
    
    .promoter-tag {
        display: inline-block;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 8px 20px;
        border-radius: 25px;
        font-weight: 600;
        font-size: 14px;
        margin-bottom: 1rem;
    }
    
    .form-title {
        color: #2d3748;
        font-size: 32px;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    
    .form-subtitle {
        color: #718096;
        font-size: 16px;
        margin-bottom: 2rem;
    }
    
    /* Success/Error boxes */
    .success-box {
        background: #c6f6d5;
        border-left: 4px solid #48bb78;
        padding: 1rem;
        border-radius: 6px;
        margin: 1rem 0;
    }
    
    .error-box {
        background: #fed7d7;
        border-left: 4px solid #f56565;
        padding: 1rem;
        border-radius: 6px;
        margin: 1rem 0;
    }
    
    /* Form styling */
    .stTextInput > label, .stTextArea > label {
        font-weight: 600;
        color: #2d3748;
    }
    
    /* Button styling */
    .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-weight: 600;
        padding: 0.75rem 2rem;
        border-radius: 8px;
        border: none;
        font-size: 16px;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
    }
</style>
""", unsafe_allow_html=True)
    
    # Show login page
    show_login_page()
    st.stop()

# User is authenticated - show the form
PROMOTER_SLUG = st.session_state.promoter_name

# Add logout button in sidebar
with st.sidebar:
    st.write(f"**Logged in as:** {PROMOTER_SLUG}")
    if st.button("🚪 Logout"):
        logout()

# Header
st.markdown(f"""
<div class="promoter-header">
    <div class="promoter-tag">{PROMOTER_SLUG}</div>
    <div class="form-title">BNG Quote Request</div>
    <div class="form-subtitle">Fast, simple biodiversity net gain quotes</div>
</div>
""", unsafe_allow_html=True)

# Show success or error if submission was made
if st.session_state.submission_complete and st.session_state.submission_result:
    result = st.session_state.submission_result
    
    if result['success']:
        if result['auto_quoted']:
            st.markdown('<div class="success-box">', unsafe_allow_html=True)
            st.success("✅ Quote Generated Successfully!")
            st.write(f"**Quote Total:** £{result['quote_total']:,.2f}")
            st.write(f"**Submission ID:** #{result['submission_id']}")
            
            if result.get('pdf_content'):
                st.download_button(
                    label="📄 Download Quote PDF",
                    data=result['pdf_content'],
                    file_name=f"BNG_Quote_{PROMOTER_SLUG}_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf"
                )
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="success-box">', unsafe_allow_html=True)
            st.success("✅ Quote Request Received!")
            st.write(f"**Quote Total:** £{result['quote_total']:,.2f}")
            st.write(f"**Submission ID:** #{result['submission_id']}")
            st.info("""
            Because this quote exceeds £20,000, it requires manual review.
            Our team will contact you shortly with a detailed proposal.
            """)
            st.markdown('</div>', unsafe_allow_html=True)
        
        if st.button("Submit Another Quote"):
            st.session_state.submission_complete = False
            st.session_state.submission_result = None
            st.rerun()
    else:
        st.markdown('<div class="error-box">', unsafe_allow_html=True)
        st.error(f"❌ Error: {result.get('error', 'Unknown error occurred')}")
        st.markdown('</div>', unsafe_allow_html=True)
        
        if st.button("Try Again"):
            st.session_state.submission_complete = False
            st.session_state.submission_result = None
            st.rerun()
    
    st.stop()

# Form
with st.form("promoter_form"):
    st.subheader("Contact Information")
    contact_email = st.text_input(
        "Contact Email *",
        placeholder="your.email@example.com",
        help="We'll send the quote and any follow-up information to this email"
    )
    
    st.subheader("Site Location")
    col1, col2 = st.columns(2)
    with col1:
        site_address = st.text_input(
            "Site Address",
            placeholder="123 Main Street, Town",
            help="Full site address (optional if postcode provided)"
        )
    with col2:
        site_postcode = st.text_input(
            "Postcode",
            placeholder="SW1A 1AA",
            help="Site postcode (optional if address provided)"
        )
    
    st.caption("⚠️ Please provide at least one of address or postcode")
    
    st.subheader("Additional Details")
    client_reference = st.text_input(
        "Client Reference (optional)",
        placeholder="Project reference or identifier"
    )
    
    notes = st.text_area(
        "Notes (optional)",
        placeholder="Any additional information or special requirements",
        height=100
    )
    
    st.subheader("BNG Metric File")
    metric_file = st.file_uploader(
        "Upload Metric File *",
        type=['xlsx'],
        help=f"Excel file (.xlsx) only, maximum {MAX_FILE_SIZE_MB} MB"
    )
    
    st.subheader("Consent")
    consent = st.checkbox(
        "I confirm that I have permission to share this data for the purpose of obtaining a BNG quote *",
        value=False
    )
    
    st.markdown("---")
    submitted = st.form_submit_button("🚀 Submit Quote Request", use_container_width=True)

# Process form submission
if submitted:
    # Validation
    errors = []
    
    if not contact_email:
        errors.append("Contact email is required")
    elif '@' not in contact_email:
        errors.append("Please enter a valid email address")
    
    if not site_address and not site_postcode:
        errors.append("Please provide either a site address or postcode")
    
    if not metric_file:
        errors.append("Please upload a BNG metric file")
    elif metric_file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
        errors.append(f"File size exceeds {MAX_FILE_SIZE_MB} MB limit")
    
    if not consent:
        errors.append("You must provide consent to share data")
    
    if errors:
        st.error("Please fix the following errors:")
        for error in errors:
            st.write(f"• {error}")
    else:
        # Process submission
        with st.spinner("Processing your quote request..."):
            try:
                # Save uploaded file to temp location
                with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                    tmp_file.write(metric_file.getvalue())
                    tmp_file_path = tmp_file.name
                
                # Read metric file
                try:
                    demand_data = metric_reader.read_bng_metric(tmp_file_path)
                except Exception as e:
                    st.session_state.submission_result = {
                        'success': False,
                        'error': f"Failed to read metric file: {str(e)}"
                    }
                    st.session_state.submission_complete = True
                    os.unlink(tmp_file_path)
                    st.rerun()
                
                # Extract demand habitats
                demand_habitats = demand_data.get('area_habitats', [])
                hedgerow_habitats = demand_data.get('hedgerow_habitats', [])
                watercourse_habitats = demand_data.get('watercourse_habitats', [])
                
                # Calculate simplified quote total
                # In production, this would run the full optimizer
                total_units = sum(h.get('units_required', 0) for h in demand_habitats)
                total_units += sum(h.get('units_required', 0) for h in hedgerow_habitats)
                total_units += sum(h.get('units_required', 0) for h in watercourse_habitats)
                
                # Simplified pricing (£10,000 per unit average)
                quote_total = total_units * 10000.0
                
                # Apply threshold logic
                auto_quoted = quote_total < AUTO_QUOTE_THRESHOLD
                
                # Save to database
                db = SubmissionsDB()
                
                # Create submission data
                submission_data = {
                    'submission_date': datetime.now(),
                    'client_name': contact_email.split('@')[0],  # Use email prefix as name
                    'reference_number': client_reference if client_reference else f"PROM-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                    'site_location': site_address if site_address else site_postcode,
                    'target_lpa': None,  # Would be resolved from postcode
                    'target_nca': None,
                    'demand_habitats': demand_habitats,
                    'contract_size': 'Standard',
                    'total_cost': quote_total,
                    'admin_fee': 0,
                    'total_with_admin': quote_total,
                    'num_banks_selected': 0,
                    'banks_used': [],
                    'allocation_results': {
                        'demand': demand_habitats,
                        'hedgerows': hedgerow_habitats,
                        'watercourses': watercourse_habitats,
                        'total_units': total_units
                    },
                    'username': 'promoter',
                    'promoter_name': PROMOTER_SLUG,
                    'promoter_discount_type': None,
                    'promoter_discount_value': None
                }
                
                # Save submission
                submission_id = db.insert_submission(**submission_data)
                
                # Clean up temp file
                os.unlink(tmp_file_path)
                
                # Generate PDF if auto-quoted
                pdf_content = None
                if auto_quoted:
                    # TODO: Generate actual PDF
                    # For now, create a simple placeholder
                    pdf_content = b"PDF placeholder content"
                
                # Store result
                st.session_state.submission_result = {
                    'success': True,
                    'auto_quoted': auto_quoted,
                    'quote_total': quote_total,
                    'submission_id': submission_id,
                    'pdf_content': pdf_content
                }
                st.session_state.submission_complete = True
                st.rerun()
                
            except Exception as e:
                st.session_state.submission_result = {
                    'success': False,
                    'error': str(e)
                }
                st.session_state.submission_complete = True
                if 'tmp_file_path' in locals() and os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)
                st.rerun()

# Footer
st.markdown("---")
st.caption(f"Promoter: {PROMOTER_SLUG} | Powered by Wild Capital BNG Optimiser")
