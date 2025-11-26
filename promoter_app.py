"""
Promoter App - BNG Quote Request Interface for Promoters/Introducers

This app allows promoters to submit BNG quote requests on behalf of clients.
Includes login system, form for client details, and automated quote generation.
"""

import json
import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Optional, Tuple

import metric_reader
from optimizer_core import (
    get_postcode_info, get_lpa_nca_for_point, get_lpa_nca_overlap_point,
    arcgis_point_query, arcgis_name_query, layer_intersect_names, norm_name,
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

# Cache LPA and NCA lists in session state
if 'all_lpas_list' not in st.session_state:
    st.session_state.all_lpas_list = fetch_all_lpas_from_arcgis()
if 'all_ncas_list' not in st.session_state:
    st.session_state.all_ncas_list = fetch_all_ncas_from_arcgis()


def authenticate_promoter(username: str, password: str) -> Tuple[bool, Optional[dict]]:
    """
    Authenticate promoter using the database with proper password hashing.
    
    For child accounts (those with parent_introducer_id), also fetches parent info
    to determine the correct promoter name and discount settings.
    
    Returns:
        Tuple of (success: bool, promoter_info: dict or None)
        
    The promoter_info dict includes:
        - All fields from the introducer record
        - 'effective_promoter_name': The promoter name to use for submissions
        - 'submitted_by_name': The individual user's name
        - 'submitted_by_username': The individual user's username/email
    """
    try:
        db = SubmissionsDB()
        # Try to authenticate using username and password hash
        success, introducer = db.authenticate_introducer(username, password)
        if success:
            # Check if this is a child account
            parent_id = introducer.get('parent_introducer_id')
            if parent_id:
                # Get parent introducer info for discount settings
                parent = db.get_introducer_by_id(parent_id)
                if parent:
                    # Use parent's discount settings but keep track of who submitted
                    introducer['effective_promoter_name'] = parent.get('name', introducer.get('name'))
                    introducer['discount_type'] = parent.get('discount_type', 'no_discount')
                    introducer['discount_value'] = parent.get('discount_value', 0)
                else:
                    introducer['effective_promoter_name'] = introducer.get('name')
            else:
                introducer['effective_promoter_name'] = introducer.get('name')
            
            # Track the individual submitter
            introducer['submitted_by_name'] = introducer.get('name')
            introducer['submitted_by_username'] = introducer.get('username', username)
            
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
                    # Use effective_promoter_name for display (parent name for child accounts)
                    st.session_state.promoter_name = promoter_info.get('effective_promoter_name', 
                                                                        promoter_info.get('name', username))
                    st.session_state.promoter_info = promoter_info
                    # Store submitter info separately
                    st.session_state.submitted_by_name = promoter_info.get('submitted_by_name', 
                                                                           promoter_info.get('name'))
                    st.session_state.submitted_by_username = promoter_info.get('submitted_by_username', username)
                    st.success(f"✓ Logged in as {st.session_state.submitted_by_name}")
                    st.rerun()
                else:
                    st.error("Invalid credentials. Please try again.")
    
    st.markdown("---")
    st.info("💡 **Forgot your password?** Contact your administrator to reset it.")
    st.stop()


# ================= LOGGED IN - SHOW FORM =================
promoter_name = st.session_state.promoter_name
promoter_info = st.session_state.get('promoter_info', {})
submitted_by_name = st.session_state.get('submitted_by_name', promoter_name)
submitted_by_username = st.session_state.get('submitted_by_username', '')

st.title(f"{promoter_name} - BNG Quote Request")

# Show user info - distinguish between promoter and individual user if different
if submitted_by_name != promoter_name:
    st.markdown(f"**Promoter:** {promoter_name} | **User:** {submitted_by_name}")
else:
    st.markdown(f"**Logged in as:** {promoter_name}")

# Get discount info for sidebar and later use
discount_type = promoter_info.get('discount_type', 'no_discount')
discount_value = promoter_info.get('discount_value', 0)

# Initialize session state for password change and quote search
if 'show_password_change' not in st.session_state:
    st.session_state.show_password_change = False
if 'show_my_quotes' not in st.session_state:
    st.session_state.show_my_quotes = False
if 'selected_quote_id' not in st.session_state:
    st.session_state.selected_quote_id = None
if 'quote_search_results' not in st.session_state:
    st.session_state.quote_search_results = None
if 'acceptance_notes' not in st.session_state:
    st.session_state.acceptance_notes = ""

# Logout button in sidebar
with st.sidebar:
    # Show promoter name and user name if different
    if submitted_by_name != promoter_name:
        st.markdown(f"### {promoter_name}")
        st.markdown(f"*User: {submitted_by_name}*")
    else:
        st.markdown(f"### {promoter_name}")
    st.markdown("---")
    
    # My Quotes button
    if st.button("📋 My Quotes", type="primary" if st.session_state.show_my_quotes else "secondary"):
        st.session_state.show_my_quotes = not st.session_state.show_my_quotes
        st.session_state.show_password_change = False  # Close other panels
        st.session_state.selected_quote_id = None  # Clear selected quote
        st.rerun()
    
    # Change Password button
    if st.button("🔑 Change Password"):
        st.session_state.show_password_change = not st.session_state.show_password_change
        st.session_state.show_my_quotes = False  # Close other panels
    
    # Password change form
    if st.session_state.show_password_change:
        st.markdown("#### Change Password")
        with st.form("change_password_form"):
            current_password = st.text_input("Current Password", type="password", key="current_pwd")
            new_password = st.text_input("New Password", type="password", key="new_pwd")
            confirm_password = st.text_input("Confirm New Password", type="password", key="confirm_pwd")
            change_pwd_submit = st.form_submit_button("Update Password")
            
            if change_pwd_submit:
                if not current_password or not new_password or not confirm_password:
                    st.error("Please fill in all password fields")
                elif new_password != confirm_password:
                    st.error("New passwords do not match")
                elif len(new_password) < 8:
                    st.error("New password must be at least 8 characters")
                else:
                    # Verify current password using the individual's username
                    success, _ = authenticate_promoter(
                        promoter_info.get('username') or submitted_by_username, 
                        current_password
                    )
                    if success:
                        try:
                            db = SubmissionsDB()
                            db.update_introducer_password(promoter_info['id'], new_password)
                            st.success("✓ Password updated successfully!")
                            st.session_state.show_password_change = False
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error updating password: {e}")
                    else:
                        st.error("Current password is incorrect")
        st.markdown("---")
    
    if st.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.session_state.promoter_name = ""
        st.session_state.promoter_info = {}
        st.session_state.submitted_by_name = ""
        st.session_state.submitted_by_username = ""
        st.session_state.show_password_change = False
        st.session_state.show_my_quotes = False
        st.session_state.selected_quote_id = None
        st.session_state.quote_search_results = None
        st.rerun()

st.markdown("---")

# ================= MY QUOTES PANEL =================
if st.session_state.show_my_quotes:
    st.title("📋 My Quotes")
    st.markdown("Search and manage your submitted quotes.")
    
    # Search filters
    with st.expander("🔎 Search Filters", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            search_client = st.text_input("Client Name", key="quote_search_client", 
                                          help="Search by client name (partial match)")
            search_ref = st.text_input("Reference Number", key="quote_search_ref",
                                       help="Search by quote reference (partial match)")
        with col2:
            search_location = st.text_input("Address/Postcode", key="quote_search_location",
                                           help="Search by site address or postcode (partial match)")
            search_lpa = st.text_input("LPA", key="quote_search_lpa",
                                      help="Search by Local Planning Authority (partial match)")
        
        search_btn = st.button("🔍 Search Quotes", key="quote_search_btn", type="primary")
    
    # Perform search
    if search_btn:
        try:
            db = SubmissionsDB()
            engine = db._get_connection()
            
            query = "SELECT * FROM submissions WHERE promoter_name = %(promoter_name)s"
            params = {"promoter_name": promoter_name}
            
            if search_client:
                query += " AND client_name ILIKE %(client_name)s"
                params["client_name"] = f"%{search_client}%"
            if search_ref:
                query += " AND reference_number ILIKE %(reference_number)s"
                params["reference_number"] = f"%{search_ref}%"
            if search_location:
                query += " AND site_location ILIKE %(location)s"
                params["location"] = f"%{search_location}%"
            if search_lpa:
                query += " AND target_lpa ILIKE %(lpa)s"
                params["lpa"] = f"%{search_lpa}%"
            
            query += " ORDER BY submission_date DESC LIMIT 50"
            
            with engine.connect() as conn:
                results_df = pd.read_sql_query(query, conn, params=params)
            
            st.session_state.quote_search_results = results_df
            
        except Exception as e:
            st.error(f"Error searching quotes: {e}")
    
    # Show recent quotes if no search has been performed
    if st.session_state.quote_search_results is None:
        try:
            db = SubmissionsDB()
            engine = db._get_connection()
            
            query = "SELECT * FROM submissions WHERE promoter_name = %(promoter_name)s ORDER BY submission_date DESC LIMIT 20"
            params = {"promoter_name": promoter_name}
            
            with engine.connect() as conn:
                results_df = pd.read_sql_query(query, conn, params=params)
            
            st.session_state.quote_search_results = results_df
        except Exception as e:
            st.error(f"Error loading quotes: {e}")
            results_df = pd.DataFrame()
    
    # Display search results
    results_df = st.session_state.quote_search_results
    if results_df is not None and not results_df.empty:
        st.markdown(f"### 📄 Your Quotes ({len(results_df)} found)")
        
        # Display columns
        display_cols = ["id", "submission_date", "client_name", "reference_number", 
                       "site_location", "target_lpa", "contract_size", "total_with_admin"]
        display_cols = [c for c in display_cols if c in results_df.columns]
        
        df_display = results_df[display_cols].copy()
        if "submission_date" in df_display.columns:
            df_display["submission_date"] = pd.to_datetime(df_display["submission_date"]).dt.strftime("%Y-%m-%d")
        if "total_with_admin" in df_display.columns:
            df_display["total_with_admin"] = df_display["total_with_admin"].apply(
                lambda x: f"£{x:,.0f}" if pd.notna(x) else "Pending"
            )
        
        # Rename columns for display
        df_display = df_display.rename(columns={
            "id": "ID",
            "submission_date": "Date",
            "client_name": "Client",
            "reference_number": "Reference",
            "site_location": "Location",
            "target_lpa": "LPA",
            "contract_size": "Size",
            "total_with_admin": "Total"
        })
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        
        # Select quote to view
        st.markdown("---")
        st.markdown("### 👁️ View Quote Details")
        quote_ids = results_df["id"].tolist()
        quote_options = [f"{row['reference_number']} - {row['client_name']}" for _, row in results_df.iterrows()]
        
        selected_idx = st.selectbox("Select a quote to view:", 
                                   range(len(quote_options)),
                                   format_func=lambda x: quote_options[x],
                                   key="quote_select_view")
        
        if st.button("View Details", key="view_quote_btn"):
            st.session_state.selected_quote_id = quote_ids[selected_idx]
            st.rerun()
        
    elif results_df is not None:
        st.info("No quotes found. Submit a new quote or try different search criteria.")
    
    # Show selected quote details
    if st.session_state.selected_quote_id is not None:
        st.markdown("---")
        st.markdown("### 📑 Quote Details")
        
        try:
            db = SubmissionsDB()
            submission = db.get_submission_by_id(st.session_state.selected_quote_id)
            
            if submission:
                # Back button
                if st.button("← Back to Quote List", key="back_to_list"):
                    st.session_state.selected_quote_id = None
                    st.rerun()
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("##### Quote Information")
                    st.write(f"**Reference:** {submission['reference_number']}")
                    st.write(f"**Client:** {submission['client_name']}")
                    st.write(f"**Location:** {submission['site_location']}")
                    st.write(f"**Date:** {submission['submission_date']}")
                    st.write(f"**Contract Size:** {submission['contract_size'] or 'N/A'}")
                    
                    total_with_admin = submission.get('total_with_admin', 0) or 0
                    if total_with_admin > 0:
                        st.write(f"**Total (inc. Admin):** £{total_with_admin:,.0f}")
                    else:
                        st.write("**Total:** Pending manual review")
                
                with col2:
                    st.markdown("##### Location Details")
                    st.write(f"**LPA:** {submission['target_lpa'] or 'N/A'}")
                    st.write(f"**NCA:** {submission['target_nca'] or 'N/A'}")
                    
                    if submission.get('contact_email'):
                        st.write(f"**Contact Email:** {submission['contact_email']}")
                    if submission.get('contact_number'):
                        st.write(f"**Contact Number:** {submission['contact_number']}")
                
                # Show demand details
                if submission.get('demand_habitats'):
                    st.markdown("##### Habitat Requirements")
                    demand_data = submission['demand_habitats']
                    if isinstance(demand_data, str):
                        demand_data = json.loads(demand_data)
                    if demand_data:
                        demand_df = pd.DataFrame(demand_data)
                        # Select and rename columns for display
                        if 'habitat_name' in demand_df.columns:
                            if 'units_required' in demand_df.columns:
                                display_demand = demand_df[['habitat_name', 'units_required']].copy()
                            else:
                                display_demand = demand_df[['habitat_name']].copy()
                            display_demand = display_demand.rename(columns={'habitat_name': 'Habitat', 'units_required': 'Units Required'})
                            st.dataframe(display_demand, use_container_width=True, hide_index=True)
                
                # Show allocation details
                allocations = db.get_allocations_for_submission(st.session_state.selected_quote_id)
                if not allocations.empty:
                    st.markdown("##### Allocation Details")
                    alloc_display = allocations[['bank_name', 'supply_habitat', 'units_supplied', 'unit_price', 'cost']].copy()
                    alloc_display['unit_price'] = alloc_display['unit_price'].apply(lambda x: f"£{x:,.0f}" if pd.notna(x) else "")
                    alloc_display['cost'] = alloc_display['cost'].apply(lambda x: f"£{x:,.0f}" if pd.notna(x) else "")
                    alloc_display = alloc_display.rename(columns={
                        'bank_name': 'Bank',
                        'supply_habitat': 'Habitat',
                        'units_supplied': 'Units',
                        'unit_price': 'Unit Price',
                        'cost': 'Cost'
                    })
                    st.dataframe(alloc_display, use_container_width=True, hide_index=True)
                
                # Quote acceptance section
                st.markdown("---")
                st.markdown("### ✅ Accept Quote & Notify Team")
                st.info("If the client has accepted this quote, click the button below to notify our team. They will contact you to proceed with the Allocation Agreement.")
                
                acceptance_notes = st.text_area(
                    "Additional notes for our team (optional):",
                    key="acceptance_notes_input",
                    help="Add any additional information or instructions for our team"
                )
                
                if st.button("🎉 Mark Quote as Accepted & Notify Team", key="accept_quote_btn", type="primary"):
                    try:
                        # Get reviewer emails from secrets
                        reviewer_emails = []
                        try:
                            reviewer_emails_raw = st.secrets["REVIEWER_EMAILS"]
                            if isinstance(reviewer_emails_raw, list):
                                reviewer_emails = [e.strip() for e in reviewer_emails_raw if e and e.strip()]
                            elif isinstance(reviewer_emails_raw, str):
                                reviewer_emails = [e.strip() for e in reviewer_emails_raw.split(",") if e.strip()]
                        except KeyError:
                            pass
                        
                        if not reviewer_emails:
                            st.error("No team email addresses configured. Please contact support.")
                        else:
                            # Build allocation summary
                            allocation_summary = ""
                            if not allocations.empty:
                                for _, row in allocations.iterrows():
                                    allocation_summary += f"- {row['supply_habitat']}: {row['units_supplied']:.2f} units @ £{row['unit_price']:,.0f}/unit = £{row['cost']:,.0f}\n"
                            
                            # Send acceptance notification email
                            email_sent, email_message = send_email_notification(
                                to_emails=reviewer_emails,
                                client_name=submission['client_name'],
                                quote_total=submission.get('total_with_admin', 0) or 0,
                                metric_file_content=None,  # No metric file needed for acceptance
                                email_type='quote_accepted',
                                reference_number=submission['reference_number'],
                                site_location=submission['site_location'],
                                promoter_name=promoter_name,
                                submitted_by_name=submitted_by_name,
                                contact_email=submission.get('contact_email', ''),
                                contact_number=submission.get('contact_number', ''),
                                notes=acceptance_notes,
                                allocation_summary=allocation_summary,
                                accepted_by=submitted_by_name
                            )
                            
                            if email_sent:
                                st.success("✅ Quote acceptance notification sent to our team! They will contact you shortly to proceed.")
                                st.balloons()
                            else:
                                st.error(f"Failed to send notification: {email_message}")
                                st.info("Please contact our team directly to inform them of the quote acceptance.")
                                
                    except Exception as e:
                        st.error(f"Error sending acceptance notification: {e}")
                        st.info("Please contact our team directly to inform them of the quote acceptance.")
                
            else:
                st.error("Quote not found.")
                st.session_state.selected_quote_id = None
                
        except Exception as e:
            st.error(f"Error loading quote details: {e}")
    
    # Back to new quote button
    st.markdown("---")
    if st.button("📝 Submit New Quote", key="back_to_new_quote", type="secondary"):
        st.session_state.show_my_quotes = False
        st.session_state.selected_quote_id = None
        st.rerun()
    
    st.stop()  # Don't show the quote form when viewing My Quotes

# ================= CHECK IF SHOWING CONFIRMATION SCREEN =================
if st.session_state.get('submission_complete', False):
    # Show confirmation screen
    st.balloons()
    
    submission_data = st.session_state.submission_data
    
    # Check if this is a manual review submission
    is_manual_review = submission_data.get('is_manual_review', False)
    
    if is_manual_review:
        # Manual review confirmation screen
        metric_type_display = submission_data.get('metric_type', 'Unknown')
        st.success(f"✅ **{metric_type_display} submitted for manual review!**")
        
        st.markdown("---")
        st.subheader("📋 Submission Summary")
        
        st.info(f"ℹ️ Your **{metric_type_display}** has been sent to our team for manual processing. You will be contacted with a quote once the review is complete.")
        
        # Show email notification status
        email_sent = submission_data.get('email_sent', False)
        email_status = submission_data.get('email_status_message', '')
        
        if email_sent:
            st.success(f"✅ **Notification Sent:** Our team has been notified of your request.")
        elif email_status:
            st.warning(f"⚠️ **Email Notification Issue:** {email_status}")
            st.info("💡 Your request was logged, but the email notification could not be sent. Please contact your administrator.")
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Client:** {submission_data['client_name']}")
            st.write(f"**Reference:** {submission_data['reference_number']}")
            st.write(f"**Location:** {submission_data['location']}")
        with col2:
            st.write(f"**Email:** {submission_data['contact_email']}")
            if submission_data.get('contact_number'):
                st.write(f"**Phone:** {submission_data['contact_number']}")
            st.write(f"**Metric Type:** {metric_type_display}")
            st.write(f"**Status:** Pending Manual Review")
    else:
        # Standard quote confirmation screen
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
            st.write(f"**Email:** {submission_data['contact_email']}")
            if submission_data.get('contact_number'):
                st.write(f"**Phone:** {submission_data['contact_number']}")
        with col2:
            # Only show quote total for quotes under £50,000
            quote_total_val = submission_data.get('quote_total', 0)
            if quote_total_val < 50000:
                st.write(f"**Total Cost:** £{round(submission_data['quote_total']):,.0f}")
                st.write(f"**Admin Fee:** £{submission_data['admin_fee']:,.0f}")
            else:
                st.write(f"**Status:** Under Review")
                st.info("This quote is £50,000 or over and is under review. You will be contacted with pricing details.")
            st.write(f"**Contract Size:** {submission_data['contract_size']}")
            st.write(f"**Habitats:** {submission_data['num_habitats']}")
    
        # Display SUO discount if applicable (only for standard quotes)
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
        
        # PDF download button - show prominently for quotes under £50,000
        quote_total_val = submission_data.get('quote_total', 0)
        if quote_total_val < 50000:
            st.markdown("---")
            
            pdf_data = submission_data.get('pdf_content')
            pdf_debug = submission_data.get('pdf_debug_message', '')
            
            if pdf_data:
                # Check if it's an actual PDF or an error/fallback message
                if isinstance(pdf_data, bytes) and len(pdf_data) > 0:
                    # Check if it's text content (error message) or actual PDF binary
                    try:
                        # Try to decode as text - if it works and contains error markers, it's not a real PDF
                        text_content = pdf_data.decode('utf-8')
                        # Only show error message if it's explicitly an error
                        if text_content.startswith('PDF generation error:'):
                            st.error("⚠️ There was an error generating the PDF. Our team has been notified and will email you a copy shortly.")
                            if pdf_debug:
                                st.code(pdf_debug, language="text")
                        else:
                            # It decoded as text but doesn't have error marker - might be fallback text
                            # Show as downloadable text file
                            st.download_button(
                                label="📄 Download Quote",
                                data=pdf_data,
                                file_name=f"BNG_Quote_{submission_data['client_name'].replace(' ', '_')}.txt",
                                mime="text/plain",
                                type="primary"
                            )
                            if pdf_debug:
                                with st.expander("Debug Information"):
                                    st.code(pdf_debug, language="text")
                    except UnicodeDecodeError:
                        # It's binary data (actual PDF) - this is what we want!
                        st.download_button(
                            label="📄 Download PDF Quote",
                            data=pdf_data,
                            file_name=f"BNG_Quote_{submission_data['client_name'].replace(' ', '_')}.pdf",
                            mime="application/pdf",
                            type="primary"
                        )
                else:
                    st.warning("⚠️ PDF generation encountered an issue. A copy will be emailed to you shortly.")
                    # Show debug information
                    if pdf_debug:
                        st.code(pdf_debug, language="text")
            else:
                # No PDF content at all - show informative message
                st.warning("⚠️ PDF could not be generated. Please contact support or check the logs. A copy will be emailed to you.")
                # Show debug information
                if pdf_debug:
                    st.code(pdf_debug, language="text")
                    st.code(submission_data['pdf_debug_message'], language=None)
    
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
    # Metric Type Selection at the top
    st.subheader("📊 Metric Type")
    metric_type = st.radio(
        "Select the type of BNG metric file you are uploading:",
        options=["Standard Metric", "Small Sites Metric", "Nutrient Neutrality Metric"],
        index=0,
        key="metric_type",
        help="Select 'Standard Metric' for automatic quote generation. Small Sites and Nutrient Neutrality metrics require manual processing."
    )
    
    # Show info message for manual processing types
    if metric_type in ["Small Sites Metric", "Nutrient Neutrality Metric"]:
        st.info(f"ℹ️ **{metric_type}** requires manual processing. Your request will be sent to our team for a manual quote.")
    
    st.markdown("---")
    
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
    
    contact_number = st.text_input("Contact Number", key="phone",
                                   help="Optional - client phone number for follow-up")
    
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
    
    # Validate phone number format if provided (basic validation - digits, spaces, +, -, parentheses)
    if contact_number:
        # Remove common formatting characters for validation
        cleaned_number = contact_number.replace(' ', '').replace('-', '').replace('(', '').replace(')', '').replace('+', '')
        if not cleaned_number.isdigit() or len(cleaned_number) < 7:
            st.error("❌ Please enter a valid contact number (at least 7 digits)")
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
    
    # ===== HANDLE MANUAL METRIC TYPES =====
    # For Small Sites Metric and Nutrient Neutrality Metric, skip processing and send for manual review
    if metric_type in ["Small Sites Metric", "Nutrient Neutrality Metric"]:
        st.markdown("---")
        st.markdown("### 📨 Submitting for Manual Review")
        
        loading_placeholder = st.empty()
        progress_bar = st.progress(0)
        
        try:
            loading_placeholder.info("⏳ Preparing your request for manual review...")
            progress_bar.progress(30)
            
            # Generate reference number for tracking
            db = SubmissionsDB()
            reference_number = db.get_next_bng_reference()
            
            progress_bar.progress(50)
            loading_placeholder.info("⏳ Sending notification to our team...")
            
            # Send manual review email
            email_sent = False
            email_status_message = ""
            email_debug_info = []
            
            try:
                # Get reviewer emails from secrets
                try:
                    reviewer_emails_raw = st.secrets["REVIEWER_EMAILS"]
                except KeyError:
                    reviewer_emails_raw = st.secrets.get("REVIEWER_EMAILS", [])
                
                # Handle both array and string formats
                if isinstance(reviewer_emails_raw, list):
                    reviewer_emails = [e.strip() for e in reviewer_emails_raw if e and e.strip()]
                elif isinstance(reviewer_emails_raw, str):
                    reviewer_emails = [e.strip() for e in reviewer_emails_raw.split(",") if e.strip()]
                else:
                    reviewer_emails = []
                
                if reviewer_emails:
                    email_sent, email_status_message = send_email_notification(
                        to_emails=reviewer_emails,
                        client_name=client_name,
                        quote_total=0,  # No quote generated for manual review
                        metric_file_content=metric_file.getvalue(),
                        metric_filename=f"{reference_number}_{metric_file.name}",
                        reference_number=reference_number,
                        site_location=location,
                        promoter_name=promoter_name,
                        submitted_by_name=submitted_by_name,
                        contact_email=contact_email if contact_email else promoter_name,
                        contact_number=contact_number,
                        notes=notes,
                        email_type='manual_review',
                        metric_type=metric_type
                    )
                else:
                    email_status_message = "No reviewer emails configured"
            except Exception as e:
                email_status_message = f"Email error: {str(e)}"
            
            progress_bar.progress(100)
            loading_placeholder.success("✓ Request submitted for manual review!")
            
            # Save to session state and show confirmation
            st.session_state.submission_complete = True
            st.session_state.submission_data = {
                'client_name': client_name,
                'reference_number': reference_number,
                'location': location,
                'contact_email': contact_email,
                'contact_number': contact_number,
                'quote_total': None,  # No quote for manual review
                'admin_fee': None,
                'contract_size': None,
                'num_habitats': None,
                'allocation_df': pd.DataFrame(),
                'promoter_name': promoter_name,
                'discount_type': discount_type,
                'discount_value': discount_value,
                'email_sent': email_sent,
                'email_status_message': email_status_message,
                'email_debug_info': email_debug_info,
                'pdf_content': None,
                'pdf_debug_message': None,
                'is_manual_review': True,
                'metric_type': metric_type
            }
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Error submitting request: {str(e)}")
            st.stop()
    
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
        
        # Try to get neighbors from lat/lon if available
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
        
        # If we don't have neighbors yet and we have manual LPA/NCA, use name-based lookup
        # This also populates lat/lon from the LPA centroid
        if (not lpa_neighbors or not nca_neighbors) and target_lpa and target_nca:
            try:
                overlap_lat, overlap_lon, lpa_neigh_from_name, nca_neigh_from_name = get_lpa_nca_overlap_point(target_lpa, target_nca)
                
                # Use the overlap point as coordinates if we don't have any yet
                if not lat and not lon and overlap_lat and overlap_lon:
                    lat = overlap_lat
                    lon = overlap_lon
                
                # Use neighbors from name query if we don't have them yet
                if not lpa_neighbors and lpa_neigh_from_name:
                    lpa_neighbors = lpa_neigh_from_name
                if not nca_neighbors and nca_neigh_from_name:
                    nca_neighbors = nca_neigh_from_name
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
        
        # ===== STEP 7: Generate PDF and email content (threshold £50k) =====
        show_loading_message(LOADING_MESSAGES[message_index % len(LOADING_MESSAGES)])
        message_index += 1
        progress_bar.progress(80)
        
        pdf_content = None
        pdf_debug_message = ""
        email_html_content = None  # For £50k+ quotes
        
        # Generate auto-incrementing reference number from database
        db_for_ref = SubmissionsDB()
        reference_number = db_for_ref.get_next_bng_reference("BNG-A-")
        
        # Calculate admin fee
        from optimizer_core import get_admin_fee_for_contract_size
        admin_fee = get_admin_fee_for_contract_size(contract_size)
        
        # Generate PDF for quotes under £50,000
        if quote_total < 50000:
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
                    promoter_discount_value=discount_value,
                    suo_discount_fraction=suo_discount_fraction
                )
                
                pdf_content, pdf_debug_message = generate_quote_pdf(
                    client_name=client_name,
                    reference_number=reference_number,
                    site_location=location,  # Use combined location
                    quote_total=quote_total,
                    report_df=report_df,
                    admin_fee=admin_fee
                )
                
            except Exception as e:
                # Log the error for debugging but continue with submission
                import traceback
                pdf_debug_message = f"PDF generation failed: {str(e)}\n{traceback.format_exc()}"
                pdf_content = None
        else:
            # For £50k+ quotes, generate full email HTML using app.py logic
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
                pdf_debug_message = f"Quote total (£{quote_total:.2f}) is >= £50,000 - full email generated for reviewer"
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
                csv_allocation_content = sales_quotes_csv.generate_sales_quotes_csv_from_optimizer_output(
                    quote_number=reference_number,
                    client_name=client_name,
                    development_address=location,  # Use combined location
                    base_ref=reference_number,
                    introducer=promoter_name,
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
                promoter_discount_value=discount_value,
                submitted_by_username=submitted_by_username,  # Track individual submitter
                contact_email=contact_email,
                contact_number=contact_number
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
                # Choose email type based on quote total
                if quote_total < 50000:
                    # Send simple quote notification with metric and CSV attachments
                    email_sent, email_status_message = send_email_notification(
                        to_emails=reviewer_emails,
                        client_name=client_name,
                        quote_total=quote_total,
                        metric_file_content=metric_file.getvalue(),
                        metric_filename=f"{reference_number}_{metric_file.name}",
                        reference_number=reference_number,  # Auto-generated reference
                        site_location=location,  # Use combined location
                        promoter_name=promoter_name,
                        submitted_by_name=submitted_by_name,  # Individual submitter name
                        contact_email=contact_email if contact_email else promoter_name,
                        contact_number=contact_number,
                        notes=notes,
                        email_type='quote_notification',
                        csv_allocation_content=csv_allocation_content
                    )
                    email_debug_info.append(f"Quote notification email sent (< £50k): {email_sent}")
                else:
                    # Send full quote email for reviewer to forward with CSV attachment
                    email_sent, email_status_message = send_email_notification(
                        to_emails=reviewer_emails,
                        client_name=client_name,
                        quote_total=quote_total,
                        metric_file_content=metric_file.getvalue(),
                        metric_filename=f"{reference_number}_{metric_file.name}",
                        reference_number=reference_number,  # Auto-generated reference
                        site_location=location,  # Use combined location
                        promoter_name=promoter_name,
                        submitted_by_name=submitted_by_name,  # Individual submitter name
                        contact_email=contact_email if contact_email else promoter_name,
                        contact_number=contact_number,
                        notes=notes,
                        email_type='full_quote',
                        email_html_body=email_html_content,
                        admin_fee=admin_fee,
                        csv_allocation_content=csv_allocation_content
                    )
                    email_debug_info.append(f"Full quote email sent (>= £50k): {email_sent}")
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
            'contact_number': contact_number,
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
