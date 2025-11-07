"""
Promoter App - BNG Quote Request Interface for Promoters/Introducers

This app allows promoters to submit BNG quote requests on behalf of clients.
Includes login system, form for client details, and automated quote generation.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Optional, Tuple

import metric_reader
from optimizer_core import (
    get_postcode_info, get_lpa_nca_for_point,
    arcgis_point_query, layer_intersect_names, norm_name,
    optimise, generate_client_report_table_fixed, load_backend
)
from pdf_generator_promoter import generate_quote_pdf
from email_notification import send_email_notification
from database import SubmissionsDB

# Constants
LPA_URL = ("https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/"
           "Local_Authority_Districts_December_2024_Boundaries_UK_BFC/FeatureServer/0")
NCA_URL = ("https://services.arcgis.com/JJzESW51TqeY9uat/arcgis/rest/services/"
           "National_Character_Areas_England/FeatureServer/0")

# Loading messages for the optimization process
LOADING_MESSAGES = [
    "Counting hedgerows...",
    "Negotiating a truce between diggers and skylarks…",
    "Whispering sweet nothings to the Metric.",
    "Summoning the spirit of Natural England (please hold).",
    "Hand-feeding the Spatial Risk Multiplier…",
    "Trimming decimal places with topiary shears…",
    "Translating ecologist into developer and back again…",
    "Brewing a double-shot of habitat alpha…",
]

st.set_page_config(page_title="BNG Quote Request", page_icon="🌿", layout="wide")

# ================= Initialize Session State =================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'promoter_name' not in st.session_state:
    st.session_state.promoter_name = ""
if 'submission_complete' not in st.session_state:
    st.session_state.submission_complete = False
if 'submission_data' not in st.session_state:
    st.session_state.submission_data = None


# ================= Helper Functions =================
def authenticate_promoter(username: str, password: str) -> Tuple[bool, Optional[dict]]:
    """
    Authenticate promoter using the database.
    
    For now, uses a simple comparison. In production, this should use
    proper password hashing and secure authentication.
    
    Returns:
        Tuple of (success: bool, promoter_info: dict or None)
    """
    try:
        db = SubmissionsDB()
        # Get all introducers (promoters)
        introducers = db.get_all_introducers()
        
        for introducer in introducers:
            # For now, we use the name as both username and password
            # In production, add a proper password field to the database
            if introducer['name'] == username:
                # SECURITY NOTE: This is a placeholder authentication
                # In production, implement proper password verification
                return True, introducer
        
        return False, None
    except Exception as e:
        st.error(f"Authentication error: {e}")
        return False, None


# ================= LOGIN SYSTEM =================
if not st.session_state.logged_in:
    st.title("Promoter Login")
    st.markdown("### Login to submit BNG quote requests")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit_login = st.form_submit_button("Login")
        
        if submit_login:
            if not username or not password:
                st.error("Please enter both username and password")
            else:
                success, promoter_info = authenticate_promoter(username, password)
                if success:
                    st.session_state.logged_in = True
                    st.session_state.promoter_name = username
                    st.session_state.promoter_info = promoter_info
                    st.success(f"✓ Logged in as {username}")
                    st.rerun()
                else:
                    st.error("Invalid credentials. Please try again.")
    
    st.info("💡 Note: Contact your administrator if you need login credentials.")
    st.stop()


# ================= LOGGED IN - SHOW FORM =================
promoter_name = st.session_state.promoter_name
promoter_info = st.session_state.get('promoter_info', {})

st.title(f"{promoter_name} - BNG Quote Request")

# Show promoter info
st.markdown(f"**Logged in as:** {promoter_name}")

# Get discount info for sidebar and later use
discount_type = promoter_info.get('discount_type', 'no_discount')
discount_value = promoter_info.get('discount_value', 0)

# Logout button in sidebar
with st.sidebar:
    st.markdown(f"### {promoter_name}")
    st.markdown(f"**Discount:** {discount_type}")
    if discount_type == 'tier_up':
        st.markdown("*Upgrades contract size (fractional→small→medium→large)*")
    elif discount_type == 'percentage':
        st.markdown(f"**Value:** {discount_value}%")
    st.markdown("---")
    if st.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.session_state.promoter_name = ""
        st.session_state.promoter_info = {}
        st.rerun()

st.markdown("---")

# ================= CHECK IF SHOWING CONFIRMATION SCREEN =================
if st.session_state.get('submission_complete', False):
    # Show confirmation screen
    st.balloons()
    
    submission_data = st.session_state.submission_data
    
    st.success("✅ **Quote request submitted successfully!**")
    
    st.markdown("---")
    st.subheader("📋 Submission Summary")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Client:** {submission_data['client_name']}")
        st.write(f"**Reference:** {submission_data['reference_number']}")
        st.write(f"**Location:** {submission_data['location']}")
        st.write(f"**Contact:** {submission_data['contact_email']}")
    with col2:
        st.write(f"**Total Cost:** £{round(submission_data['quote_total']):,.0f}")
        st.write(f"**Admin Fee:** £{submission_data['admin_fee']:,.0f}")
        st.write(f"**Contract Size:** {submission_data['contract_size']}")
        st.write(f"**Habitats:** {submission_data['num_habitats']}")
    
    # PDF download button - show prominently if available
    if submission_data.get('pdf_content'):
        st.markdown("---")
        pdf_data = submission_data['pdf_content']
        # Check if it's an error message (text) or actual PDF
        if isinstance(pdf_data, bytes) and not pdf_data.startswith(b'PDF generation error:'):
            st.download_button(
                label="📄 Download PDF Quote",
                data=pdf_data,
                file_name=f"BNG_Quote_{submission_data['client_name'].replace(' ', '_')}.pdf",
                mime="application/pdf",
                type="primary"
            )
        else:
            st.warning("⚠️ PDF generation is not available. Please contact support for a copy of your quote.")
    
    st.markdown("---")
    
    # Show allocation detail in expander
    with st.expander("🔍 Technical Details & Debug Information", expanded=False):
        # Show debug information
        if submission_data.get('debug_info'):
            st.markdown("#### Bank Enrichment & Tier Classification")
            st.text(submission_data['debug_info'])
            st.markdown("---")
        
        # Show allocation detail
        allocation_df = submission_data['allocation_df']
        if not allocation_df.empty:
            st.markdown("#### Allocation Detail")
            display_cols = [
                "demand_habitat", "BANK_KEY", "bank_name", "supply_habitat", 
                "allocation_type", "tier", "units_supplied", "unit_price", "cost"
            ]
            available_cols = [col for col in display_cols if col in allocation_df.columns]
            display_df = allocation_df[available_cols].copy()
            
            # Format numeric columns
            if "units_supplied" in display_df.columns:
                display_df["units_supplied"] = display_df["units_supplied"].apply(lambda x: f"{x:.4f}")
            if "unit_price" in display_df.columns:
                display_df["unit_price"] = display_df["unit_price"].apply(lambda x: f"£{x:,.2f}")
            if "cost" in display_df.columns:
                display_df["cost"] = display_df["cost"].apply(lambda x: f"£{x:,.2f}")
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # Show summary by bank
            st.markdown("#### Summary by Bank")
            bank_summary = allocation_df.groupby("bank_name").agg({
                "units_supplied": "sum",
                "cost": "sum"
            }).reset_index()
            bank_summary.columns = ["Bank", "Total Units", "Total Cost"]
            bank_summary["Total Units"] = bank_summary["Total Units"].apply(lambda x: f"{x:.4f}")
            bank_summary["Total Cost"] = bank_summary["Total Cost"].apply(lambda x: f"£{x:,.2f}")
            st.dataframe(bank_summary, use_container_width=True, hide_index=True)
            
            # Show summary by habitat
            st.markdown("#### Summary by Demand Habitat")
            habitat_summary = allocation_df.groupby("demand_habitat").agg({
                "units_supplied": "sum",
                "cost": "sum"
            }).reset_index()
            habitat_summary.columns = ["Habitat", "Total Units", "Total Cost"]
            habitat_summary["Total Units"] = habitat_summary["Total Units"].apply(lambda x: f"{x:.4f}")
            habitat_summary["Total Cost"] = habitat_summary["Total Cost"].apply(lambda x: f"£{x:,.2f}")
            st.dataframe(habitat_summary, use_container_width=True, hide_index=True)
    
    # Button to submit another quote
    st.markdown("---")
    if st.button("📝 Submit Another Quote", type="primary"):
        st.session_state.submission_complete = False
        st.session_state.submission_data = None
        st.rerun()
    
    st.stop()

# ================= QUOTE REQUEST FORM =================
with st.form("quote_form"):
    st.subheader("👤 Client Details")
    
    col1, col2, col3 = st.columns([1, 2, 2])
    with col1:
        title = st.selectbox("Title *", ["Mr", "Mrs", "Ms", "Dr", "Prof", "Other"], key="title")
    with col2:
        first_name = st.text_input("First Name *", key="fname")
    with col3:
        surname = st.text_input("Surname *", key="sname")
    
    contact_email = st.text_input("Contact Email *", key="email", 
                                   help="Email address for quote delivery")
    
    st.subheader("📍 Site Location")
    site_address = st.text_input("Site Address", key="addr", 
                                  help="Full site address (optional if postcode provided)")
    postcode = st.text_input("Postcode", key="pc", 
                             help="Site postcode (optional if address provided)")
    
    st.subheader("📝 Additional Details")
    notes = st.text_area("Notes (optional)", key="notes", 
                         help="Any additional information about the project")
    
    st.subheader("📄 BNG Metric File")
    metric_file = st.file_uploader("Upload Metric File *", type=['xlsx', 'xlsm', 'xlsb'], key="metric",
                                    help="Upload the BNG Metric 4.0 file for this project")
    
    st.markdown("---")
    consent = st.checkbox("✓ I have permission to share this data *", key="consent")
    
    submitted = st.form_submit_button("🚀 Submit Quote Request", type="primary")


# ================= FORM SUBMISSION PROCESSING =================
if submitted:
    # ===== VALIDATION =====
    if not contact_email or not first_name or not surname or not metric_file or not consent:
        st.error("❌ Please complete all required fields (marked with *)")
        st.stop()
    
    if not site_address and not postcode:
        st.error("❌ Please provide either site address or postcode")
        st.stop()
    
    # Validate email format (basic check)
    if '@' not in contact_email or '.' not in contact_email.split('@')[1]:
        st.error("❌ Please enter a valid email address")
        st.stop()
    
    client_name = f"{title} {first_name} {surname}"
    
    # ===== LOADING SCREEN =====
    st.markdown("---")
    st.markdown("### 🔄 Processing Your Quote Request")
    
    # Create placeholder for rotating messages
    loading_placeholder = st.empty()
    progress_bar = st.progress(0)
    
    try:
        # Rotating loading messages
        message_index = 0
        def show_loading_message(msg):
            loading_placeholder.info(f"⏳ {msg}")
        
        # ===== STEP 1: Load Backend Data =====
        show_loading_message(LOADING_MESSAGES[message_index % len(LOADING_MESSAGES)])
        message_index += 1
        progress_bar.progress(10)
        backend = load_backend()
        
        # ===== STEP 2: Parse Metric File =====
        show_loading_message(LOADING_MESSAGES[message_index % len(LOADING_MESSAGES)])
        message_index += 1
        progress_bar.progress(20)
        demand_data = metric_reader.parse_metric_requirements(metric_file)
        area_df = demand_data['area']
        
        # Rename columns to match optimizer expectations
        if not area_df.empty:
            area_df = area_df.rename(columns={'habitat': 'habitat_name', 'units': 'units_required'})
        
        if area_df.empty:
            st.error("❌ No habitat requirements found in metric file")
            st.stop()
        
        # ===== STEP 3: Geocode Location =====
        show_loading_message(LOADING_MESSAGES[message_index % len(LOADING_MESSAGES)])
        message_index += 1
        progress_bar.progress(30)
        lat, lon = None, None
        target_lpa, target_nca = "", ""
        
        if postcode:
            try:
                lat, lon, _ = get_postcode_info(postcode)
            except Exception as e:
                pass
        
        # ===== STEP 4: Get LPA/NCA =====
        show_loading_message(LOADING_MESSAGES[message_index % len(LOADING_MESSAGES)])
        message_index += 1
        progress_bar.progress(40)
        if lat and lon:
            try:
                target_lpa, target_nca = get_lpa_nca_for_point(lat, lon)
            except Exception as e:
                pass
        
        # ===== STEP 5: Find Neighbors for Tier Calculation =====
        show_loading_message(LOADING_MESSAGES[message_index % len(LOADING_MESSAGES)])
        message_index += 1
        progress_bar.progress(50)
        lpa_neighbors, nca_neighbors = [], []
        if lat and lon:
            try:
                lpa_feat = arcgis_point_query(LPA_URL, lat, lon, "LAD24NM")
                nca_feat = arcgis_point_query(NCA_URL, lat, lon, "NCA_Name")
                
                if lpa_feat and lpa_feat.get("geometry"):
                    lpa_neighbors = layer_intersect_names(LPA_URL, lpa_feat.get("geometry"), "LAD24NM")
                if nca_feat and nca_feat.get("geometry"):
                    nca_neighbors = layer_intersect_names(NCA_URL, nca_feat.get("geometry"), "NCA_Name")
            except Exception as e:
                pass
        
        # ===== STEP 6: Run Optimizer =====
        show_loading_message(LOADING_MESSAGES[message_index % len(LOADING_MESSAGES)])
        message_index += 1
        progress_bar.progress(60)
        
        # Get promoter discount settings
        discount_type = promoter_info.get('discount_type')
        discount_value = promoter_info.get('discount_value')
        
        allocation_df, quote_total, contract_size, debug_info = optimise(
            demand_df=area_df,
            target_lpa=target_lpa,
            target_nca=target_nca,
            lpa_neigh=lpa_neighbors,
            nca_neigh=nca_neighbors,
            lpa_neigh_norm=[norm_name(n) for n in lpa_neighbors],
            nca_neigh_norm=[norm_name(n) for n in nca_neighbors],
            backend=backend,
            promoter_discount_type=discount_type,
            promoter_discount_value=discount_value,
            return_debug_info=True
        )
        
        progress_bar.progress(70)
        
        # ===== STEP 7: Generate PDF (if < £20k) =====
        show_loading_message(LOADING_MESSAGES[message_index % len(LOADING_MESSAGES)])
        message_index += 1
        progress_bar.progress(80)
        
        pdf_content = None
        reference_number = f"PROM-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Calculate admin fee
        from optimizer_core import get_admin_fee_for_contract_size
        admin_fee = get_admin_fee_for_contract_size(contract_size)
        
        # Generate PDF for quotes under £20,000
        if quote_total < 20000:
            try:
                report_df, _ = generate_client_report_table_fixed(
                    alloc_df=allocation_df,
                    demand_df=area_df,
                    total_cost=quote_total,
                    admin_fee=admin_fee,
                    client_name=client_name,
                    ref_number=reference_number,
                    location=postcode or site_address,
                    backend=backend,
                    promoter_name=promoter_name,
                    promoter_discount_type=discount_type,
                    promoter_discount_value=discount_value
                )
                
                pdf_content = generate_quote_pdf(
                    client_name=client_name,
                    reference_number=reference_number,
                    site_location=postcode or site_address,
                    quote_total=quote_total,
                    report_df=report_df,
                    admin_fee=admin_fee
                )
                
                # Store error message if PDF generation produced fallback text
                if pdf_content and b'weasyprint' in pdf_content:
                    # This is the fallback - weasyprint not available
                    pass  # Still save it so user knows
                    
            except Exception as e:
                # Log the error for debugging but continue with submission
                import traceback
                error_msg = f"PDF generation failed: {str(e)}\n{traceback.format_exc()}"
                # Store error in session for display on confirmation screen
                pdf_content = f"PDF generation error: {error_msg}".encode('utf-8')
        
        progress_bar.progress(90)
        
        # ===== STEP 8: Save to Database =====
        show_loading_message("Saving to database...")
        try:
            db = SubmissionsDB()
            submission_id = db.store_submission(
                client_name=client_name,
                reference_number=reference_number,
                site_location=postcode or site_address,
                target_lpa=target_lpa,
                target_nca=target_nca,
                target_lat=lat,
                target_lon=lon,
                lpa_neighbors=lpa_neighbors,
                nca_neighbors=nca_neighbors,
                demand_df=area_df,
                allocation_df=allocation_df,
                contract_size=contract_size,
                total_cost=quote_total,
                admin_fee=admin_fee,
                manual_hedgerow_rows=[],
                manual_watercourse_rows=[],
                manual_area_habitat_rows=[],
                username=promoter_name,
                promoter_name=promoter_name,
                promoter_discount_type=discount_type,
                promoter_discount_value=discount_value
            )
        except Exception as e:
            pass  # Database save failed, but continue
        
        # ===== STEP 9: Send Email Notification =====
        show_loading_message("Sending notifications...")
        try:
            reviewer_emails = st.secrets.get("REVIEWER_EMAILS", "").split(",")
            reviewer_emails = [e.strip() for e in reviewer_emails if e.strip()]
            
            if reviewer_emails:
                send_email_notification(
                    to_emails=reviewer_emails,
                    client_name=client_name,
                    quote_total=quote_total,
                    metric_file_content=metric_file.getvalue(),
                    reference_number=reference_number,
                    site_location=postcode or site_address,
                    promoter_name=promoter_name,
                    contact_email=contact_email,
                    notes=notes
                )
        except Exception as e:
            pass  # Email send failed, but continue
        
        progress_bar.progress(100)
        loading_placeholder.success("✓ Processing complete!")
        
        # ===== SAVE TO SESSION STATE AND SHOW CONFIRMATION =====
        st.session_state.submission_complete = True
        st.session_state.submission_data = {
            'client_name': client_name,
            'reference_number': reference_number,
            'location': postcode or site_address,
            'contact_email': contact_email,
            'quote_total': quote_total,
            'admin_fee': admin_fee,
            'contract_size': contract_size,
            'num_habitats': len(area_df),
            'allocation_df': allocation_df,
            'debug_info': debug_info,
            'pdf_content': pdf_content
        }
        
        # Rerun to show confirmation screen
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ Error processing quote request: {str(e)}")
        import traceback
        with st.expander("Show error details"):
            st.code(traceback.format_exc())
