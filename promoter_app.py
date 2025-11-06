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

st.set_page_config(page_title="BNG Quote Request", page_icon="🌿", layout="wide")

# ================= Initialize Session State =================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'promoter_name' not in st.session_state:
    st.session_state.promoter_name = ""


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
col1, col2 = st.columns([2, 1])
with col1:
    st.markdown(f"**Logged in as:** {promoter_name}")
with col2:
    discount_type = promoter_info.get('discount_type', 'no_discount')
    discount_value = promoter_info.get('discount_value', 0)
    if discount_type == 'tier_up':
        st.markdown(f"**Discount:** Tier Up (contract size upgrade)")
    elif discount_type == 'percentage' and discount_value:
        st.markdown(f"**Discount:** {discount_value}% off")
    else:
        st.markdown(f"**Discount:** None")

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

# ================= QUOTE REQUEST FORM =================
with st.form("quote_form"):
    st.subheader("📧 Contact Information")
    contact_email = st.text_input("Contact Email *", key="email", 
                                   help="Email address for quote delivery")
    
    st.subheader("👤 Client Details")
    col1, col2, col3 = st.columns([1, 2, 2])
    with col1:
        title = st.selectbox("Title *", ["Mr", "Mrs", "Ms", "Dr", "Prof", "Other"], key="title")
    with col2:
        first_name = st.text_input("First Name *", key="fname")
    with col3:
        surname = st.text_input("Surname *", key="sname")
    
    st.subheader("📍 Site Location")
    site_address = st.text_input("Site Address", key="addr", 
                                  help="Full site address (optional if postcode provided)")
    postcode = st.text_input("Postcode", key="pc", 
                             help="Site postcode (optional if address provided)")
    
    st.subheader("📝 Additional Details")
    notes = st.text_area("Notes (optional)", key="notes", 
                         help="Any additional information about the project")
    
    st.subheader("📄 BNG Metric File")
    metric_file = st.file_uploader("Upload Metric File *", type=['xlsx', 'xlsb'], key="metric",
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
    
    try:
        st.info("🔄 Processing your quote request...")
        
        # ===== STEP 1: Load Backend Data =====
        with st.spinner("Loading reference data..."):
            backend = load_backend()
            st.success("✓ Reference data loaded")
        
        # ===== STEP 2: Parse Metric File =====
        with st.spinner("Parsing BNG metric file..."):
            demand_data = metric_reader.parse_metric_requirements(metric_file)
            area_df = demand_data['area']
            
            # Rename columns to match optimizer expectations
            # metric_reader returns: habitat, units
            # optimizer expects: habitat_name, units_required
            if not area_df.empty:
                area_df = area_df.rename(columns={'habitat': 'habitat_name', 'units': 'units_required'})
            
            if area_df.empty:
                st.error("❌ No habitat requirements found in metric file")
                st.stop()
            
            st.success(f"✓ Found {len(area_df)} habitat requirements")
            st.write(f"**Total units required:** {area_df['units_required'].sum():.2f}")
        
        # ===== STEP 3: Geocode Location =====
        lat, lon = None, None
        target_lpa, target_nca = "", ""
        
        if postcode:
            with st.spinner(f"Geocoding postcode: {postcode}"):
                try:
                    lat, lon, _ = get_postcode_info(postcode)
                    st.success(f"✓ Location: {lat:.4f}, {lon:.4f}")
                except Exception as e:
                    st.warning(f"⚠️ Could not geocode postcode: {e}")
        
        # ===== STEP 4: Get LPA/NCA =====
        if lat and lon:
            with st.spinner("Identifying LPA and NCA..."):
                try:
                    target_lpa, target_nca = get_lpa_nca_for_point(lat, lon)
                    st.success(f"✓ Target LPA: {target_lpa}")
                    st.success(f"✓ Target NCA: {target_nca}")
                except Exception as e:
                    st.warning(f"⚠️ Could not determine LPA/NCA: {e}")
        
        # ===== STEP 5: Find Neighbors for Tier Calculation =====
        lpa_neighbors, nca_neighbors = [], []
        if lat and lon:
            with st.spinner("Finding neighboring LPAs and NCAs..."):
                try:
                    lpa_feat = arcgis_point_query(LPA_URL, lat, lon, "LAD24NM")
                    nca_feat = arcgis_point_query(NCA_URL, lat, lon, "NCA_Name")
                    
                    if lpa_feat and lpa_feat.get("geometry"):
                        lpa_neighbors = layer_intersect_names(LPA_URL, lpa_feat.get("geometry"), "LAD24NM")
                    if nca_feat and nca_feat.get("geometry"):
                        nca_neighbors = layer_intersect_names(NCA_URL, nca_feat.get("geometry"), "NCA_Name")
                    
                    st.success(f"✓ Found {len(lpa_neighbors)} neighboring LPAs, {len(nca_neighbors)} neighboring NCAs")
                except Exception as e:
                    st.warning(f"⚠️ Could not find neighbors: {e}")
        
        # ===== STEP 6: Run Optimizer =====
        with st.spinner("Running optimization..."):
            # Get promoter discount settings
            discount_type = promoter_info.get('discount_type')
            discount_value = promoter_info.get('discount_value')
            
            # Display promoter discount info
            if discount_type and discount_type != 'no_discount':
                if discount_type == 'tier_up':
                    st.info(f"🎯 Promoter discount: **Tier Up** - Upgrades contract size (fractional→small→medium→large)")
                elif discount_type == 'percentage':
                    st.info(f"🎯 Promoter discount: **{discount_value}% off** unit prices")
            
            allocation_df, quote_total, contract_size = optimise(
                demand_df=area_df,
                target_lpa=target_lpa,
                target_nca=target_nca,
                lpa_neigh=lpa_neighbors,
                nca_neigh=nca_neighbors,
                lpa_neigh_norm=[norm_name(n) for n in lpa_neighbors],
                nca_neigh_norm=[norm_name(n) for n in nca_neighbors],
                backend=backend,
                promoter_discount_type=discount_type,
                promoter_discount_value=discount_value
            )
            
            st.success(f"✓ Optimization complete: {len(allocation_df)} allocations")
            st.success(f"💰 **Total cost: £{quote_total:,.2f}**")
            st.info(f"📋 Contract size: **{contract_size}**")
        
        # ===== STEP 7: Generate PDF (if < £20k) =====
        pdf_content = None
        reference_number = f"PROM-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        if quote_total < 20000:
            with st.spinner("Generating PDF quote..."):
                try:
                    # Calculate admin fee using the contract size from optimizer
                    from optimizer_core import get_admin_fee_for_contract_size
                    admin_fee = get_admin_fee_for_contract_size(contract_size)
                    
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
                        report_df=report_df
                    )
                    
                    st.success(f"✓ PDF generated ({len(pdf_content)} bytes)")
                    
                    # Provide download button
                    st.download_button(
                        label="⬇️ Download Quote PDF",
                        data=pdf_content,
                        file_name=f"BNG_Quote_{client_name.replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        type="primary"
                    )
                except Exception as e:
                    st.warning(f"⚠️ Could not generate PDF: {e}")
        else:
            st.info(f"📋 Quote total (£{quote_total:,.2f}) exceeds £20,000 - forwarded for manual review")
        
        # ===== STEP 8: Save to Database =====
        with st.spinner("Saving submission to database..."):
            try:
                # Calculate admin fee using the contract size from optimizer
                from optimizer_core import get_admin_fee_for_contract_size
                admin_fee = get_admin_fee_for_contract_size(contract_size)
                
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
                st.success(f"✓ Submission saved (ID: #{submission_id})")
            except Exception as e:
                st.error(f"❌ Could not save to database: {e}")
                import traceback
                with st.expander("Database error details"):
                    st.code(traceback.format_exc())
        
        # ===== STEP 9: Send Email Notification =====
        with st.spinner("Sending email notification..."):
            try:
                # Get reviewer emails from secrets
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
                    st.success("✓ Email notification sent to reviewers")
                else:
                    st.warning("⚠️ No reviewer emails configured in secrets")
            except Exception as e:
                st.warning(f"⚠️ Could not send email: {e}")
        
        # ===== SUCCESS MESSAGE =====
        st.markdown("---")
        st.success("✅ **Quote request submitted successfully!**")
        st.balloons()
        
        # Show summary
        st.subheader("📋 Submission Summary")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Client:** {client_name}")
            st.write(f"**Reference:** {reference_number}")
            st.write(f"**Location:** {postcode or site_address}")
            st.write(f"**Contact:** {contact_email}")
        with col2:
            st.write(f"**Total Cost:** £{quote_total:,.2f}")
            st.write(f"**Habitats:** {len(area_df)}")
            st.write(f"**Allocations:** {len(allocation_df)}")
            st.write(f"**Promoter:** {promoter_name}")
        
    except NotImplementedError as e:
        st.error(f"❌ Feature not yet implemented: {e}")
        st.info("💡 The optimizer core functions need to be fully extracted from app.py")
    except Exception as e:
        st.error(f"❌ Error processing quote request: {str(e)}")
        import traceback
        with st.expander("Show error details"):
            st.code(traceback.format_exc())
