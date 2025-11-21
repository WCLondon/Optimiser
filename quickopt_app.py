"""
QuickOpt App - Internal BNG Quote Request Interface

This app is for internal office use to submit BNG quote requests.
Uses WC0323 login for internal access. All quotes are sent for review regardless of size.
Includes form for client details and automated quote generation.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Optional, Tuple

import metric_reader
from optimizer_core import (
    get_postcode_info, get_lpa_nca_for_point,
    arcgis_point_query, layer_intersect_names, norm_name,
    optimise, generate_client_report_table_fixed, load_backend,
    http_get, safe_json, sstr
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


# ================= Helper Functions =================
def fetch_all_lpas_from_arcgis():
    """
    Fetch all unique LPA names from the ArcGIS LPA layer.
    Uses a simple query to get all records.
    Cached to avoid repeated API calls.
    """
    try:
        params = {
            "f": "json",
            "where": "1=1",
            "outFields": "LAD24NM",
            "returnGeometry": "false",
            "returnDistinctValues": "true"
        }
        r = http_get(f"{LPA_URL}/query", params=params)
        js = safe_json(r)
        features = js.get("features", [])
        lpas = [sstr((f.get("attributes") or {}).get("LAD24NM")) for f in features]
        return sorted({lpa for lpa in lpas if lpa})
    except Exception as e:
        st.warning(f"Could not fetch LPA list: {e}")
        return []


def fetch_all_ncas_from_arcgis():
    """
    Fetch all unique NCA names from the ArcGIS NCA layer.
    Uses a simple query to get all records.
    Cached to avoid repeated API calls.
    """
    try:
        params = {
            "f": "json",
            "where": "1=1",
            "outFields": "NCA_Name",
            "returnGeometry": "false",
            "returnDistinctValues": "true"
        }
        r = http_get(f"{NCA_URL}/query", params=params)
        js = safe_json(r)
        features = js.get("features", [])
        ncas = [sstr((f.get("attributes") or {}).get("NCA_Name")) for f in features]
        return sorted({nca for nca in ncas if nca})
    except Exception as e:
        st.warning(f"Could not fetch NCA list: {e}")
        return []


st.set_page_config(page_title="QuickOpt - Internal BNG Quote", page_icon="🌿", layout="wide")

# ================= Initialize Session State =================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'promoter_name' not in st.session_state:
    st.session_state.promoter_name = ""
if 'submission_complete' not in st.session_state:
    st.session_state.submission_complete = False
if 'submission_data' not in st.session_state:
    st.session_state.submission_data = None

# Cache LPA and NCA lists in session state
if 'all_lpas_list' not in st.session_state:
    st.session_state.all_lpas_list = fetch_all_lpas_from_arcgis()
if 'all_ncas_list' not in st.session_state:
    st.session_state.all_ncas_list = fetch_all_ncas_from_arcgis()


def authenticate_promoter(username: str, password: str) -> Tuple[bool, Optional[dict]]:
    """
    Authenticate internal user using hardcoded WC0323 credentials.
    
    For internal office use only. Uses WC0323 as the default user.
    
    Returns:
        Tuple of (success: bool, promoter_info: dict or None)
    """
    # Hardcoded credentials for internal use
    INTERNAL_USERNAME = "WC0323"
    INTERNAL_PASSWORD = "Wimborne"
    
    if username == INTERNAL_USERNAME and password == INTERNAL_PASSWORD:
        # Return success with internal user info
        internal_user_info = {
            'name': INTERNAL_USERNAME,
            'discount_type': 'no_discount',
            'discount_value': 0
        }
        return True, internal_user_info
    
    return False, None


# ================= LOGIN SYSTEM =================
if not st.session_state.logged_in:
    st.title("QuickOpt - Internal Login")
    st.markdown("### Login to submit internal BNG quote requests")
    
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
    
    st.info("💡 Note: This is for internal office use only. Use WC0323 credentials.")
    st.stop()


# ================= LOGGED IN - SHOW FORM =================
promoter_name = st.session_state.promoter_name
promoter_info = st.session_state.get('promoter_info', {})

st.title(f"QuickOpt - Internal BNG Quote Request")

# Show user info
st.markdown(f"**Logged in as:** {promoter_name} (Internal)")

# Get discount info for sidebar and later use
discount_type = promoter_info.get('discount_type', 'no_discount')
discount_value = promoter_info.get('discount_value', 0)

# Logout button in sidebar
with st.sidebar:
    st.markdown(f"### {promoter_name}")
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
    
    # Show email notification status prominently
    email_sent = submission_data.get('email_sent', False)
    email_status = submission_data.get('email_status_message', '')
    email_debug_info = submission_data.get('email_debug_info', [])
    
    if email_sent:
        st.success(f"✅ **Email Notification Sent:** {email_status}")
    elif email_status:
        st.warning(f"⚠️ **Email Notification Issue:** {email_status}")
        st.info("💡 Your quote was saved successfully, but the email notification could not be sent. Please contact your administrator to check the email configuration.")
        
        # Show debug information in an expander
        if email_debug_info:
            with st.expander("🔍 Email Debug Information", expanded=True):
                st.markdown("**Diagnostic Information:**")
                for info in email_debug_info:
                    st.text(info)
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Client:** {submission_data['client_name']}")
        st.write(f"**Reference:** {submission_data['reference_number']}")
        st.write(f"**Location:** {submission_data['location']}")
        st.write(f"**Contact:** {submission_data['contact_email']}")
    with col2:
        # For internal use, always show quote under review
        st.write(f"**Status:** Under Review")
        st.info("This quote has been sent for review. You will be contacted with pricing details.")
        st.write(f"**Contract Size:** {submission_data['contract_size']}")
        st.write(f"**Habitats:** {submission_data['num_habitats']}")
    
    # Display SUO discount if applicable
    if submission_data.get('suo_applicable', False) and submission_data.get('suo_results'):
        st.markdown("---")
        st.markdown("### 🎯 Surplus Uplift Offset (SUO) - Cost Discount Applied")
        
        suo_results = submission_data['suo_results']
        discount_pct = suo_results['discount_fraction'] * 100
        
        st.success(f"✅ SUO Discount Applied: {discount_pct:.1f}% cost reduction based on eligible on-site surplus")
        
        # Show SUO summary metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Eligible Surplus", f"{suo_results['eligible_surplus']:.2f} units", 
                     help="Total surplus from Medium+ distinctiveness habitats")
        with col2:
            st.metric("Usable (50% headroom)", f"{suo_results['usable_surplus']:.2f} units",
                     help="50% of eligible surplus available for offset")
        with col3:
            st.metric("Discount Applied", f"{discount_pct:.1f}%",
                     help="Percentage discount on allocation costs")
    
    # No PDF download for internal app - all quotes under review
    st.markdown("---")
    st.info("📧 The quote has been sent to the review team for processing.")
    
    st.markdown("---")
    
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
        title = st.selectbox("Title", ["Mr", "Mrs", "Ms", "Dr", "Prof", "Other", "N/A"], key="title")
    with col2:
        first_name = st.text_input("First Name", key="fname", 
                                   help="Optional - leave blank if client details not available")
    with col3:
        surname = st.text_input("Surname", key="sname",
                               help="Optional - leave blank if client details not available")
    
    contact_email = st.text_input("Contact Email", key="email", 
                                   help="Optional - leave blank if client details not available")
    
    st.subheader("📍 Site Location")
    st.caption("Provide address/postcode OR select LPA/NCA")
    
    site_address = st.text_input("Site Address (First Line)", key="addr", 
                                  help="First line of address (optional)")
    postcode = st.text_input("Postcode", key="pc", 
                             help="Site postcode (optional)")
    
    st.markdown("**OR use LPA/NCA if address not available:**")
    
    # LPA/NCA selection with autocomplete dropdowns
    lpa_options = [""] + st.session_state.all_lpas_list
    nca_options = [""] + st.session_state.all_ncas_list
    
    manual_lpa = st.selectbox(
        "Local Planning Authority", 
        options=lpa_options,
        index=0,
        key="manual_lpa",
        help="Select LPA if address/postcode not available (type to search)"
    )
    manual_nca = st.selectbox(
        "National Character Area", 
        options=nca_options,
        index=0,
        key="manual_nca",
        help="Select NCA if address/postcode not available (type to search)"
    )
    
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
    if not metric_file or not consent:
        st.error("❌ Please complete all required fields (marked with *)")
        st.stop()
    
    # At least one of: address/postcode OR LPA/NCA must be provided
    has_location = bool(site_address or postcode)
    has_lpa_nca = bool(manual_lpa and manual_nca)
    
    if not has_location and not has_lpa_nca:
        st.error("❌ Please provide either site address/postcode OR LPA and NCA")
        st.stop()
    
    # Validate email format if provided
    if contact_email and ('@' not in contact_email or '.' not in contact_email.split('@')[1]):
        st.error("❌ Please enter a valid email address")
        st.stop()
    
    # Build client name - use promoter name as fallback
    if first_name and surname:
        client_name = f"{title} {first_name} {surname}" if title and title != "N/A" else f"{first_name} {surname}"
    else:
        client_name = promoter_name  # Fallback to promoter name
    
    # Build location string - combine address and postcode if both provided
    if site_address and postcode:
        location = f"{site_address}, {postcode}"
    elif site_address:
        location = site_address
    elif postcode:
        location = postcode
    else:
        # Use LPA/NCA as location
        location = f"{manual_lpa}, {manual_nca}"
    
    # Determine target LPA and NCA
    if manual_lpa and manual_nca:
        target_lpa = manual_lpa
        target_nca = manual_nca
    else:
        # Will be determined by geocoding later
        target_lpa = None
        target_nca = None
    
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
        
        # Extract all habitat types from metric
        area_df = demand_data['area']
        hedgerow_df = demand_data.get('hedgerows', pd.DataFrame())
        watercourse_df = demand_data.get('watercourses', pd.DataFrame())
        
        # Store surplus for SUO calculation (if available)
        metric_surplus = demand_data.get('surplus', pd.DataFrame())
        has_suo_surplus = False
        if not metric_surplus.empty:
            # Check if there's usable surplus (Medium+ distinctiveness)
            distinctiveness_order = {"Very Low": 0, "Low": 1, "Medium": 2, "High": 3, "Very High": 4}
            eligible_surplus = metric_surplus[
                metric_surplus["distinctiveness"].apply(
                    lambda d: distinctiveness_order.get(str(d), 0) >= 2
                )
            ]
            if not eligible_surplus.empty and eligible_surplus["units_surplus"].sum() > 0:
                has_suo_surplus = True
        
        # Rename columns to match optimizer expectations for area habitats
        if not area_df.empty:
            area_df = area_df.rename(columns={'habitat': 'habitat_name', 'units': 'units_required'})
        
        # Process hedgerow habitats and add to area_df
        if not hedgerow_df.empty:
            hedgerow_processed = hedgerow_df.rename(columns={'habitat': 'habitat_name', 'units': 'units_required'})
            # For hedgerows that don't match catalog, use Net Gain (Hedgerows) label
            # For now, append all hedgerow data to area_df for processing
            area_df = pd.concat([area_df, hedgerow_processed], ignore_index=True)
        
        # Process watercourse habitats and add to area_df
        if not watercourse_df.empty:
            watercourse_processed = watercourse_df.rename(columns={'habitat': 'habitat_name', 'units': 'units_required'})
            # For watercourses that don't match catalog, use Net Gain (Watercourses) label
            # For now, append all watercourse data to area_df for processing
            area_df = pd.concat([area_df, watercourse_processed], ignore_index=True)
        
        if area_df.empty:
            st.error("❌ No habitat requirements found in metric file")
            st.stop()
        
        # Check for Felled Woodland - not supported in promoter app
        FELLED_WOODLAND_NAME = "Woodland and forest - Felled/Replacement for felled woodland"
        felled_woodland_in_demand = area_df[area_df["habitat_name"] == FELLED_WOODLAND_NAME]
        if not felled_woodland_in_demand.empty:
            st.error(f"❌ '{FELLED_WOODLAND_NAME}' is not supported in automated quote generation.")
            st.info("This habitat requires manual pricing. Please use the main app (app.py) instead.")
            st.stop()
        
        # ===== STEP 3: Geocode Location =====
        show_loading_message(LOADING_MESSAGES[message_index % len(LOADING_MESSAGES)])
        message_index += 1
        progress_bar.progress(30)
        lat, lon = None, None
        
        # Only geocode if we don't have manual LPA/NCA
        if not target_lpa or not target_nca:
            if postcode:
                try:
                    lat, lon, _ = get_postcode_info(postcode)
                except Exception as e:
                    pass
        
        # ===== STEP 4: Get LPA/NCA =====
        show_loading_message(LOADING_MESSAGES[message_index % len(LOADING_MESSAGES)])
        message_index += 1
        progress_bar.progress(40)
        
        # Only query if we don't have manual LPA/NCA
        if not target_lpa or not target_nca:
            if lat and lon:
                try:
                    queried_lpa, queried_nca = get_lpa_nca_for_point(lat, lon)
                    if not target_lpa:
                        target_lpa = queried_lpa
                    if not target_nca:
                        target_nca = queried_nca
                except Exception as e:
                    pass
        
        # Ensure we have LPA/NCA values
        if not target_lpa:
            target_lpa = ""
        if not target_nca:
            target_nca = ""
        
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
        
        # ===== STEP 6.5: Compute SUO (Surplus Uplift Offset) Discount =====
        suo_discount_fraction = 0.0
        suo_applicable = False
        suo_results = None
        
        if has_suo_surplus and not allocation_df.empty:
            try:
                # Filter to Medium+ distinctiveness only
                distinctiveness_order = {"Very Low": 0, "Low": 1, "Medium": 2, "High": 3, "Very High": 4}
                eligible_surplus = metric_surplus[
                    metric_surplus["distinctiveness"].apply(
                        lambda d: distinctiveness_order.get(str(d), 0) >= 2
                    )
                ].copy()
                
                if not eligible_surplus.empty:
                    # Calculate total eligible surplus
                    total_eligible = eligible_surplus["units_surplus"].sum()
                    
                    # Apply 50% headroom
                    usable_surplus = total_eligible * 0.5
                    
                    # Calculate total units purchased
                    total_units = allocation_df["units_supplied"].sum()
                    
                    # Calculate discount fraction with 60% maximum cap
                    discount_fraction = min(usable_surplus / total_units, 0.60) if total_units > 0 else 0.0
                    
                    if discount_fraction > 0:
                        suo_applicable = True
                        suo_discount_fraction = discount_fraction
                        suo_results = {
                            "applicable": True,
                            "discount_fraction": discount_fraction,
                            "eligible_surplus": total_eligible,
                            "usable_surplus": usable_surplus,
                            "total_units_purchased": total_units
                        }
                        
                        # Apply discount to quote total
                        original_quote_total = quote_total
                        quote_total = quote_total * (1 - suo_discount_fraction)
            except Exception as e:
                # Continue without SUO if there's an error
                pass
        
        # ===== STEP 7: Generate full email content for review =====
        show_loading_message(LOADING_MESSAGES[message_index % len(LOADING_MESSAGES)])
        message_index += 1
        progress_bar.progress(80)
        
        pdf_content = None
        pdf_debug_message = ""
        email_html_content = None
        
        # Generate auto-incrementing reference number from database
        db_for_ref = SubmissionsDB()
        reference_number = db_for_ref.get_next_bng_reference("BNG-A-")
        
        # Calculate admin fee
        from optimizer_core import get_admin_fee_for_contract_size
        admin_fee = get_admin_fee_for_contract_size(contract_size)
        
        # For internal use, always generate full email for review (no PDF download)
        try:
            # Import the email generation function from optimizer_core
            from optimizer_core import generate_client_report_table_fixed
            
            # Generate the full client report table and email HTML
            report_df, email_html_content = generate_client_report_table_fixed(
                alloc_df=allocation_df,
                demand_df=area_df,
                total_cost=quote_total,
                admin_fee=admin_fee,
                client_name=client_name,
                ref_number=reference_number,  # Include auto-generated reference
                location=location,  # Use combined location
                backend=backend,
                promoter_name=promoter_name,
                promoter_discount_type=discount_type,
                promoter_discount_value=discount_value,
                suo_discount_fraction=suo_discount_fraction
            )
            pdf_debug_message = f"Internal quote - full email generated for reviewer"
        except Exception as e:
            import traceback
            pdf_debug_message = f"Email generation failed: {str(e)}\n{traceback.format_exc()}"
            email_html_content = None
        
        progress_bar.progress(90)
        
        # ===== STEP 7.5: Generate CSV Allocation Data =====
        show_loading_message("Generating allocation CSV...")
        csv_allocation_content = None
        csv_generation_error = None
        try:
            import sales_quotes_csv
            import json
            import numpy as np
            
            # Process allocation data exactly like app.py does
            # This splits paired habitats into separate rows for CSV
            if not allocation_df.empty:
                MULT = {"local": 1.0, "adjacent": 4/3, "far": 2.0}
                
                def sstr(x):
                    """Convert to string safely."""
                    return str(x) if x is not None else ""
                
                def split_paired_rows(df: pd.DataFrame) -> pd.DataFrame:
                    """Split paired allocations into separate rows - matches app.py logic."""
                    if df.empty: 
                        return df
                    rows = []
                    for _, r in df.iterrows():
                        if sstr(r.get("allocation_type")) != "paired":
                            rows.append(r.to_dict())
                            continue

                        # Extract paired parts (each has its own unit price and stock_use)
                        parts = []
                        try:
                            parts = json.loads(sstr(r.get("paired_parts")))
                        except Exception:
                            parts = []

                        sh = sstr(r.get("supply_habitat"))
                        name_parts = [p.strip() for p in sh.split("+")] if sh else []

                        units_total = float(r.get("units_supplied", 0.0) or 0.0)

                        if len(parts) == 2:
                            # For paired allocations, split units according to stock_use ratios
                            for idx, part in enumerate(parts):
                                rr = r.to_dict()
                                rr["supply_habitat"] = sstr(part.get("habitat") or (name_parts[idx] if idx < len(name_parts) else f"Part {idx+1}"))
                                
                                # Use stock_use ratio to determine units for this component
                                stock_use = float(part.get("stock_use", 0.5))
                                rr["units_supplied"] = units_total * stock_use
                                rr["unit_price"] = float(part.get("unit_price", rr.get("unit_price", 0.0)))
                                rr["cost"] = rr["units_supplied"] * rr["unit_price"]
                                rows.append(rr)
                        else:
                            # Fallback: split cost/units evenly (50/50)
                            units_each = 0.5 * units_total
                            if len(name_parts) == 2:
                                for part_name in name_parts:
                                    rr = r.to_dict()
                                    rr["supply_habitat"] = part_name
                                    rr["units_supplied"] = units_each
                                    rr["cost"] = float(r.get("cost", 0.0) or 0.0) * 0.5
                                    rows.append(rr)
                            else:
                                rows.append(r.to_dict())
                    return pd.DataFrame(rows)
                
                # Split paired rows - exactly like app.py
                expanded_alloc = split_paired_rows(allocation_df.copy())
                expanded_alloc["proximity"] = expanded_alloc.get("tier", "").map(sstr)
                expanded_alloc["effective_units"] = expanded_alloc.apply(
                    lambda r: float(r["units_supplied"]) * MULT.get(sstr(r.get("proximity", "")).lower(), 1.0), 
                    axis=1
                )
                
                # Create site_hab_totals - exactly like app.py
                site_hab_totals = (expanded_alloc.groupby(
                    ["BANK_KEY", "bank_name", "supply_habitat", "tier", "allocation_type"], 
                    as_index=False
                ).agg(
                    units_supplied=("units_supplied", "sum"),
                    effective_units=("effective_units", "sum"),
                    cost=("cost", "sum")
                ).sort_values(["bank_name", "supply_habitat", "tier"]))
                
                site_hab_totals["avg_unit_price"] = site_hab_totals["cost"] / site_hab_totals["units_supplied"].replace(0, np.nan)
                site_hab_totals["avg_effective_unit_price"] = site_hab_totals["cost"] / site_hab_totals["effective_units"].replace(0, np.nan)
                
                # Generate CSV using the processed data - exactly like app.py
                # For WC0323 (internal use), set introducer to "Direct" in CSV
                csv_introducer = "Direct" if promoter_name == "WC0323" else promoter_name
                csv_allocation_content = sales_quotes_csv.generate_sales_quotes_csv_from_optimizer_output(
                    quote_number=reference_number,
                    client_name=client_name,
                    development_address=location,  # Use combined location
                    base_ref=reference_number,
                    introducer=csv_introducer,
                    today_date=datetime.now(),
                    local_planning_authority=target_lpa,
                    national_character_area=target_nca,
                    alloc_df=site_hab_totals,  # Use processed data like app.py
                    contract_size=contract_size
                )
            else:
                csv_generation_error = "Allocation DataFrame is empty - no CSV generated"
        except Exception as e:
            # Log error but continue - CSV is optional
            import traceback
            csv_generation_error = f"CSV generation failed: {str(e)}\n{traceback.format_exc()}"
            # Don't fail the entire submission if CSV generation fails
            csv_allocation_content = None
        
        # ===== STEP 8: Save to Database =====
        show_loading_message("Saving to database...")
        try:
            db = SubmissionsDB()
            submission_id = db.store_submission(
                client_name=client_name,
                reference_number=reference_number,
                site_location=location,  # Use combined location
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
        email_sent = False
        email_status_message = ""
        email_debug_info = []  # Collect debug info to display in UI
        
        # Add CSV generation status to debug info
        if csv_allocation_content:
            email_debug_info.append(f"✓ CSV allocation generated successfully ({len(csv_allocation_content)} characters)")
        elif csv_generation_error:
            email_debug_info.append(f"✗ CSV generation failed: {csv_generation_error}")
        else:
            email_debug_info.append("⚠ CSV allocation content is None (no error reported)")
        
        try:
            # Get reviewer emails from secrets - try multiple access methods
            reviewer_emails = []
            reviewer_emails_raw = None
            
            # Debug: Show what keys are available in secrets
            try:
                available_keys = list(st.secrets.keys()) if hasattr(st.secrets, 'keys') else []
                email_debug_info.append(f"Available secret keys: {available_keys}")
            except Exception as e:
                email_debug_info.append(f"Could not list secret keys: {e}")
            
            # Try to access REVIEWER_EMAILS
            try:
                # Try direct key access first (works for TOML arrays)
                reviewer_emails_raw = st.secrets["REVIEWER_EMAILS"]
                email_debug_info.append("✓ Got REVIEWER_EMAILS via direct key access")
            except KeyError as e:
                email_debug_info.append(f"✗ KeyError accessing REVIEWER_EMAILS: {e}")
                # Fallback to .get() method
                try:
                    reviewer_emails_raw = st.secrets.get("REVIEWER_EMAILS", [])
                    email_debug_info.append("✓ Got REVIEWER_EMAILS via .get() method")
                except Exception as e2:
                    email_debug_info.append(f"✗ Error with .get() method: {e2}")
                    reviewer_emails_raw = []
            except Exception as e:
                email_debug_info.append(f"✗ Unexpected error accessing REVIEWER_EMAILS: {type(e).__name__}: {e}")
                reviewer_emails_raw = []
            
            email_debug_info.append(f"Raw value: {repr(reviewer_emails_raw)}")
            email_debug_info.append(f"Type: {type(reviewer_emails_raw)}")
            
            # Handle both array and string formats
            if isinstance(reviewer_emails_raw, list):
                reviewer_emails = [e.strip() for e in reviewer_emails_raw if e and e.strip()]
            elif isinstance(reviewer_emails_raw, str):
                reviewer_emails = [e.strip() for e in reviewer_emails_raw.split(",") if e.strip()]
            else:
                reviewer_emails = []
            
            email_debug_info.append(f"Processed emails: {reviewer_emails}")
            email_debug_info.append(f"Email count: {len(reviewer_emails)}")
            
            if reviewer_emails:
                # For internal use, always send full quote email for reviewer to forward
                email_sent, email_status_message = send_email_notification(
                    to_emails=reviewer_emails,
                    client_name=client_name,
                    quote_total=quote_total,
                    metric_file_content=metric_file.getvalue(),
                    metric_filename=f"{reference_number}_{metric_file.name}",
                    reference_number=reference_number,  # Auto-generated reference
                    site_location=location,  # Use combined location
                    promoter_name=promoter_name,
                    contact_email=contact_email if contact_email else promoter_name,
                    notes=notes,
                    email_type='full_quote',
                    email_html_body=email_html_content,
                    admin_fee=admin_fee,
                    csv_allocation_content=csv_allocation_content
                )
                email_debug_info.append(f"Full quote email sent for internal review: {email_sent}")
            else:
                email_status_message = "No reviewer emails configured in secrets (REVIEWER_EMAILS). Please add REVIEWER_EMAILS to .streamlit/secrets.toml as an array: REVIEWER_EMAILS = [\"email@example.com\"]"
                email_debug_info.append("✗ No reviewer emails found after processing")
        except Exception as e:
            email_status_message = f"Email notification error: {str(e)}"
            email_debug_info.append(f"✗ Exception in email block: {type(e).__name__}: {e}")
            import traceback
            email_debug_info.append(f"Traceback: {traceback.format_exc()}")
        
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
            'pdf_content': pdf_content,
            'pdf_debug_message': pdf_debug_message,
            'suo_applicable': suo_applicable,
            'suo_results': suo_results,
            'email_sent': email_sent,
            'email_status_message': email_status_message,
            'email_debug_info': email_debug_info
        }
        
        # Rerun to show confirmation screen
        st.rerun()
        
    except Exception as e:
        error_msg = str(e)
        st.error(f"❌ Error processing quote request: {error_msg}")
        
        import traceback
        with st.expander("Show error details"):
            st.code(traceback.format_exc())
        
        # Show catalog debug info if present in error message
        if "[DEBUG]" in error_msg:
            with st.expander("🔍 Catalog Debug Information", expanded=True):
                st.text(error_msg)
