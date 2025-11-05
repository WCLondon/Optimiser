# app.py — BNG Optimiser (Standalone), v9.14
# Changes in v9.14:
# - Generalized Orchard stacking: added ADJACENT (SRM 4/3) tier support
# - Implemented dynamic "Other" component selection (cheapest eligible area habitat ≤ Medium distinctiveness)
# - Updated pairing mix: ADJACENT uses 1.00 Orchard + 1/3 Other (75%/25% split); FAR uses 0.50 Orchard + 0.50 Other
# - Enhanced split_paired_rows to handle non-50/50 splits correctly
# - Pricing: Adjacent = (1.00*orchard + (1/3)*other) / (4/3); Far = 0.5*orchard + 0.5*other
#
# Changes in v9.13:
# - Added "Start New Quote" button with comprehensive reset functionality
# - Implemented automatic map refresh after optimization completes
# - Ensured financial readout persists across map interactions
# - Enhanced user experience with clear visual feedback
#
# Changes in v9.12:
# - Fixed map disappearing on optimise
# - Improved UI responsiveness
# - Better state management
# - Fixed flickering issues
# - Enhanced error handling

import json
import re
import time
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

import numpy as np
import pandas as pd
import requests
import streamlit as st
from streamlit_folium import st_folium
try:
    from streamlit_folium import folium_static
except Exception:
    folium_static = None
import folium

# Database for submissions tracking
from database import SubmissionsDB

# Repository layer for reference/config tables
import repo

# BNG Metric reader
import metric_reader

# Surplus Uplift Offset (SUO)
import suo

# ================= Config / constants =================
ADMIN_FEE_GBP = 500.0  # Standard admin fee
ADMIN_FEE_FRACTIONAL_GBP = 300.0  # Admin fee for fractional quotes
SINGLE_BANK_SOFT_PCT = 0.01
MAP_CATCHMENT_ALPHA = 0.03
UA = {"User-Agent": "WildCapital-Optimiser/1.0 (+contact@example.com)"}
LEDGER_AREA = "area"
LEDGER_HEDGE = "hedgerow"
LEDGER_WATER = "watercourse"

# Tier proximity ranking: lower is better (closer)
TIER_PROXIMITY_RANK = {"local": 0, "adjacent": 1, "far": 2}

NET_GAIN_WATERCOURSE_LABEL = "Net Gain (Watercourses)"  # new
POSTCODES_IO = "https://api.postcodes.io/postcodes/"
NOMINATIM_SEARCH = "https://nominatim.openstreetmap.org/search"
NCA_URL = ("https://services.arcgis.com/JJzESW51TqeY9uat/arcgis/rest/services/"
           "National_Character_Areas_England/FeatureServer/0")
LPA_URL = ("https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/"
           "Local_Authority_Districts_December_2024_Boundaries_UK_BFC/FeatureServer/0")

# Watercourse catchment URLs for SRM calculation
# Note: These URLs should be updated with the most current datasets from Environment Agency
# WFD Waterbody Catchments: Individual waterbody catchments for precise matching
WATERBODY_CATCHMENT_URL = ("https://environment.data.gov.uk/spatialdata/water-framework-directive-"
                          "river-waterbody-catchments-cycle-2/wfs")
# WFD Operational Catchments: Larger operational catchment areas
OPERATIONAL_CATCHMENT_URL = ("https://environment.data.gov.uk/spatialdata/water-framework-directive-"
                            "river-operational-catchments-cycle-2/wfs")

# Optional solver
try:
    import pulp
    _HAS_PULP = True
except Exception:
    _HAS_PULP = False

# ================= Page Setup =================
st.set_page_config(page_title="BNG Optimiser (Standalone)", page_icon="🧭", layout="wide")
st.markdown("<h2>BNG Optimiser — Standalone</h2>", unsafe_allow_html=True)

# ================= Initialize Session State =================
def init_session_state():
    """Initialize all session state variables"""
    defaults = {
        "auth_ok": False,
        "map_version": 0,
        "target_lpa_name": "",
        "target_nca_name": "",
        "lpa_neighbors": [],
        "nca_neighbors": [],
        "lpa_neighbors_norm": [],
        "nca_neighbors_norm": [],
        "target_lat": None,
        "target_lon": None,
        "lpa_geojson": None,
        "nca_geojson": None,
        "target_waterbody": "",
        "target_operational_catchment": "",
        "last_alloc_df": None,
        "bank_geo_cache": {},
        "bank_catchment_geo": {},
        "bank_watercourse_catchments": {},  # Store watercourse catchments for banks
        "demand_rows": [{"id": 1, "habitat_name": "", "units": 0.0}],
        "_next_row_id": 2,
        "optimization_complete": False,
        "manual_hedgerow_rows": [],
        "manual_watercourse_rows": [],
        "manual_area_rows": [],
        "_next_manual_hedgerow_id": 1,
        "_next_manual_watercourse_id": 1,
        "_next_manual_area_id": 1,
        "removed_allocation_rows": [],
        "bank_list_for_manual": [],  # Cache of bank names for manual entry
        "email_client_name": "INSERT NAME",
        "email_ref_number": "BNG00XXX",
        "email_location": "INSERT LOCATION",
        "postcode_input": "",
        "address_input": "",
        "needs_map_refresh": False,
        "use_promoter": False,
        "selected_promoter": None,
        "promoter_discount_type": None,
        "promoter_discount_value": None,
        "use_lpa_nca_dropdown": False,
        "selected_lpa_dropdown": None,
        "selected_nca_dropdown": None,
        "all_lpas_list": None,  # Cache for complete LPA list from ArcGIS
        "all_ncas_list": None,   # Cache for complete NCA list from ArcGIS
        "enriched_banks_cache": None,  # Cache for enriched banks data with LPA/NCA
        "enriched_banks_timestamp": None,  # Timestamp when banks were last enriched
        "suo_enabled": True,  # SUO toggle (enabled by default)
        "suo_results": None,  # SUO computation results
        "suo_applicable": False,  # Whether SUO can be applied
        "metric_surplus": None,  # Surplus from metric file
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def reset_quote():
    """Reset all quote-related session state to start a new quote"""
    try:
        # First, delete all widget-bound keys for existing demand rows
        # This must happen BEFORE resetting demand_rows to clear the widget state
        if "demand_rows" in st.session_state:
            for row in st.session_state["demand_rows"]:
                row_id = row.get("id")
                # Delete habitat selectbox key
                hab_key = f"hab_{row_id}"
                if hab_key in st.session_state:
                    del st.session_state[hab_key]
                # Delete units number_input key
                units_key = f"units_{row_id}"
                if units_key in st.session_state:
                    del st.session_state[units_key]
        
        # Now reset demand_rows data
        st.session_state["demand_rows"] = [{"id": 1, "habitat_name": "", "units": 0.0}]
        st.session_state["_next_row_id"] = 2
        st.session_state["target_lpa_name"] = ""
        st.session_state["target_nca_name"] = ""
        st.session_state["lpa_neighbors"] = []
        st.session_state["nca_neighbors"] = []
        st.session_state["lpa_neighbors_norm"] = []
        st.session_state["nca_neighbors_norm"] = []
        st.session_state["target_lat"] = None
        st.session_state["target_lon"] = None
        st.session_state["lpa_geojson"] = None
        st.session_state["nca_geojson"] = None
        st.session_state["last_alloc_df"] = None
        st.session_state["bank_geo_cache"] = {}
        st.session_state["bank_catchment_geo"] = {}
        st.session_state["optimization_complete"] = False
        st.session_state["manual_hedgerow_rows"] = []
        st.session_state["manual_watercourse_rows"] = []
        st.session_state["manual_area_rows"] = []
        st.session_state["_next_manual_hedgerow_id"] = 1
        st.session_state["_next_manual_watercourse_id"] = 1
        st.session_state["_next_manual_area_id"] = 1
        st.session_state["removed_allocation_rows"] = []
        st.session_state["email_client_name"] = "INSERT NAME"
        st.session_state["email_ref_number"] = "BNG00XXX"
        st.session_state["email_location"] = "INSERT LOCATION"
        st.session_state["map_version"] = st.session_state.get("map_version", 0) + 1
        # Clear location input fields by deleting them (widget-bound variables)
        if "postcode_input" in st.session_state:
            del st.session_state["postcode_input"]
        if "address_input" in st.session_state:
            del st.session_state["address_input"]
        # Clear summary dataframes
        st.session_state["site_hab_totals"] = None
        st.session_state["by_bank"] = None
        st.session_state["by_hab"] = None
        st.session_state["summary_df"] = None
        st.session_state["total_cost"] = None
        st.session_state["contract_size"] = None
    except Exception as e:
        st.error(f"Error resetting quote: {e}")
        # Re-initialize session state as fallback
        init_session_state()

init_session_state()

# ================= Safe strings =================
def sstr(x) -> str:
    if x is None:
        return ""
    if isinstance(x, float) and (np.isnan(x) or np.isinf(x)):
        return ""
    return str(x).strip()

def norm_name(s: str) -> str:
    t = sstr(s).lower()
    t = re.sub(r'\b(city of|royal borough of|metropolitan borough of)\b', '', t)
    t = re.sub(r'\b(council|borough|district|county|unitary authority|unitary|city)\b', '', t)
    t = t.replace("&", "and")
    t = re.sub(r'[^a-z0-9]+', '', t)
    return t

def is_hedgerow(name: str) -> bool:
    name_str = sstr(name)
    # Check if it's the hedgerow net gain label
    if name_str == "Net Gain (Hedgerows)":
        return True
    
    # Check UmbrellaType column if backend is loaded
    try:
        if backend and "HabitatCatalog" in backend:
            catalog = backend["HabitatCatalog"]
            if "UmbrellaType" in catalog.columns:
                match = catalog[catalog["habitat_name"].astype(str).str.strip() == name_str]
                if not match.empty:
                    umbrella_type = sstr(match.iloc[0]["UmbrellaType"]).lower()
                    return umbrella_type == "hedgerow"
    except Exception:
        pass
    
    # Fallback to text matching
    return "hedgerow" in name_str.lower()

def is_watercourse(name: str) -> bool:
    name_str = sstr(name)
    
    # Check UmbrellaType column if backend is loaded
    try:
        if backend and "HabitatCatalog" in backend:
            catalog = backend["HabitatCatalog"]
            if "UmbrellaType" in catalog.columns:
                match = catalog[catalog["habitat_name"].astype(str).str.strip() == name_str]
                if not match.empty:
                    umbrella_type = sstr(match.iloc[0]["UmbrellaType"]).lower()
                    return umbrella_type == "watercourse"
    except Exception:
        pass
    
    # Fallback to text matching
    name_lower = name_str.lower()
    return "watercourse" in name_lower or "water" in name_lower

def get_hedgerow_habitats(catalog_df: pd.DataFrame) -> List[str]:
    """Get list of hedgerow habitats from catalog using UmbrellaType column"""
    if "UmbrellaType" in catalog_df.columns:
        # Use the UmbrellaType column to filter
        hedgerow_df = catalog_df[catalog_df["UmbrellaType"].astype(str).str.strip().str.lower() == "hedgerow"]
        return sorted([sstr(x) for x in hedgerow_df["habitat_name"].dropna().unique().tolist()])
    else:
        # Fallback to text matching if column doesn't exist
        all_habitats = [sstr(x) for x in catalog_df["habitat_name"].dropna().unique().tolist()]
        return sorted([h for h in all_habitats if is_hedgerow(h)])

def get_watercourse_habitats(catalog_df: pd.DataFrame) -> List[str]:
    """Get list of watercourse habitats from catalog using UmbrellaType column"""
    if "UmbrellaType" in catalog_df.columns:
        # Use the UmbrellaType column to filter
        watercourse_df = catalog_df[catalog_df["UmbrellaType"].astype(str).str.strip().str.lower() == "watercourse"]
        return sorted([sstr(x) for x in watercourse_df["habitat_name"].dropna().unique().tolist()])
    else:
        # Fallback to text matching if column doesn't exist
        all_habitats = [sstr(x) for x in catalog_df["habitat_name"].dropna().unique().tolist()]
        return sorted([h for h in all_habitats if is_watercourse(h)])

def get_area_habitats(catalog_df: pd.DataFrame) -> List[str]:
    """Get list of area habitats from catalog using UmbrellaType column"""
    if "UmbrellaType" in catalog_df.columns:
        # Use the UmbrellaType column to filter - area habitats are those that are not hedgerow or watercourse
        area_df = catalog_df[
            (catalog_df["UmbrellaType"].astype(str).str.strip().str.lower() != "hedgerow") &
            (catalog_df["UmbrellaType"].astype(str).str.strip().str.lower() != "watercourse")
        ]
        return sorted([sstr(x) for x in area_df["habitat_name"].dropna().unique().tolist()])
    else:
        # Fallback to filtering out hedgerow and watercourse habitats
        all_habitats = [sstr(x) for x in catalog_df["habitat_name"].dropna().unique().tolist()]
        return sorted([h for h in all_habitats if not is_hedgerow(h) and not is_watercourse(h)])

# ================= Login =================
DEFAULT_USER = "WC0323"
DEFAULT_PASS = "Wimborne"
ADMIN_DB_PASS = "WCAdmin2024"  # Password for database/admin tab access

def require_login():
    if st.session_state.auth_ok:
        with st.sidebar:
            if st.button("Log out", key="logout_btn"):
                # Clear session state on logout
                for key in list(st.session_state.keys()):
                    if key != "auth_ok":
                        del st.session_state[key]
                st.session_state.auth_ok = False
                st.rerun()
        return
    
    st.markdown("## 🔐 Sign in")
    with st.form("login_form"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        ok = st.form_submit_button("Sign in")
    
    if ok:
        valid_u = st.secrets.get("auth", {}).get("username", DEFAULT_USER)
        valid_p = st.secrets.get("auth", {}).get("password", DEFAULT_PASS)
        if u == valid_u and p == valid_p:
            st.session_state.auth_ok = True
            st.rerun()
        else:
            st.error("Invalid credentials")
            st.stop()
    st.stop()

require_login()

# ================= Database Initialization =================
# Initialize database (will create tables if they don't exist)
try:
    db = SubmissionsDB()
except Exception as e:
    st.error(f"Failed to initialize database: {e}")
    db = None

# ================= Mode Selection (Sidebar) =================
# Add admin_authenticated flag to session state
if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False
if "app_mode" not in st.session_state:
    st.session_state.app_mode = "Optimiser"

# Mode selector in sidebar
with st.sidebar:
    st.markdown("---")
    app_mode = st.radio(
        "Mode",
        ["Optimiser", "Quote Management", "Admin Dashboard"],
        key="mode_selector",
        index=0 if st.session_state.app_mode == "Optimiser" else (1 if st.session_state.app_mode == "Quote Management" else 2)
    )
    st.session_state.app_mode = app_mode

# ================= Admin Dashboard Mode =================
if st.session_state.app_mode == "Admin Dashboard":
    if not st.session_state.admin_authenticated:
        st.markdown("### 🔐 Admin Access Required")
        st.info("Enter the admin password to access the submissions database.")
        
        with st.form("admin_auth_form"):
            admin_pass = st.text_input("Admin Password", type="password")
            admin_submit = st.form_submit_button("Access Admin Dashboard")
        
        if admin_submit:
            admin_valid_pass = st.secrets.get("admin", {}).get("password", ADMIN_DB_PASS)
            if admin_pass == admin_valid_pass:
                st.session_state.admin_authenticated = True
                st.success("✅ Access granted!")
                st.rerun()
            else:
                st.error("❌ Invalid admin password")
                st.stop()
        st.stop()
    
    # Admin is authenticated - show dashboard
    st.markdown("### 📊 Admin Dashboard")
    
    if db is None:
        st.error("Database is not available.")
        st.stop()
    
    # Logout button
    if st.button("🔓 Lock Admin Dashboard", key="admin_logout"):
        st.session_state.admin_authenticated = False
        st.rerun()
    
    # Check reference tables status
    st.markdown("#### 📋 Reference Tables Status")
    try:
        tables_status = repo.check_required_tables_not_empty()
        all_ok = all(tables_status.values())
        
        if all_ok:
            st.success("✅ All required reference tables are populated.")
        else:
            st.error("❌ Some required reference tables are empty or missing:")
            for table_name, is_ok in tables_status.items():
                if not is_ok:
                    st.error(f"  • {table_name} table is empty or missing")
            st.info("💡 Please populate these tables in your Supabase database to enable the optimizer.")
        
        # Show table counts
        with st.expander("📊 Reference Table Details", expanded=False):
            col1, col2, col3 = st.columns(3)
            table_names = list(tables_status.keys())
            for idx, table_name in enumerate(table_names):
                with [col1, col2, col3][idx % 3]:
                    try:
                        if table_name == "Banks":
                            df = repo.fetch_banks()
                        elif table_name == "Pricing":
                            df = repo.fetch_pricing()
                        elif table_name == "HabitatCatalog":
                            df = repo.fetch_habitat_catalog()
                        elif table_name == "Stock":
                            df = repo.fetch_stock()
                        elif table_name == "DistinctivenessLevels":
                            df = repo.fetch_distinctiveness_levels()
                        elif table_name == "SRM":
                            df = repo.fetch_srm()
                        else:
                            df = pd.DataFrame()
                        
                        row_count = len(df)
                        status_icon = "✅" if row_count > 0 else "❌"
                        st.metric(f"{status_icon} {table_name}", f"{row_count} rows")
                    except Exception as e:
                        st.metric(f"❌ {table_name}", "Error")
    except Exception as e:
        st.error(f"Error checking reference tables: {e}")
    
    st.markdown("---")
    
    # Get summary stats
    st.markdown("### 📊 Submissions Database")
    try:
        stats = db.get_summary_stats()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Submissions", stats["total_submissions"])
        with col2:
            st.metric("Total Revenue", f"£{stats['total_revenue']:,.0f}")
        with col3:
            st.metric("Top LPA", stats["top_lpas"][0][0] if stats["top_lpas"] else "N/A")
    except Exception as e:
        st.warning(f"Could not load summary stats: {e}")
    
    st.markdown("---")
    
    # ================= Introducer Management =================
    st.markdown("#### 👥 Introducer/Promoter Management")
    
    # Get all introducers
    try:
        introducers = db.get_all_introducers()
        
        # Add new introducer
        with st.expander("➕ Add New Introducer", expanded=False):
            with st.form("add_introducer_form"):
                new_name = st.text_input("Introducer Name", key="new_introducer_name")
                new_discount_type = st.selectbox("Discount Type", ["tier_up", "percentage", "no_discount"], key="new_discount_type")
                new_discount_value = st.number_input("Discount Value", 
                                                     min_value=0.0, 
                                                     step=0.1,
                                                     key="new_discount_value",
                                                     help="For percentage: enter as decimal (e.g., 10.5 for 10.5%). For tier_up or no_discount: value is ignored.",
                                                     disabled=(st.session_state.get("new_discount_type") == "no_discount"))
                add_submit = st.form_submit_button("Add Introducer")
                
                if add_submit:
                    if not new_name or not new_name.strip():
                        st.error("Please enter an introducer name.")
                    else:
                        try:
                            # For no_discount type, set value to 0
                            discount_value = 0.0 if st.session_state.get("new_discount_type") == "no_discount" else new_discount_value
                            db.add_introducer(new_name.strip(), new_discount_type, discount_value)
                            st.success(f"✅ Added introducer: {new_name}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error adding introducer: {e}")
        
        # Display existing introducers
        if introducers:
            st.markdown("##### Current Introducers")
            for intro in introducers:
                col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 1, 1])
                with col1:
                    st.write(f"**{intro['name']}**")
                with col2:
                    st.write(f"Type: {intro['discount_type']}")
                with col3:
                    if intro['discount_type'] == 'percentage':
                        st.write(f"Value: {intro['discount_value']}%")
                    elif intro['discount_type'] == 'no_discount':
                        st.write("No Discount")
                    else:
                        st.write("Tier Up")
                with col4:
                    # Edit button - use unique key with introducer id
                    if st.button("✏️", key=f"edit_{intro['id']}", help="Edit"):
                        st.session_state[f"editing_introducer_{intro['id']}"] = True
                with col5:
                    # Delete button
                    if st.button("🗑️", key=f"delete_{intro['id']}", help="Delete"):
                        try:
                            db.delete_introducer(intro['id'])
                            st.success(f"Deleted: {intro['name']}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error deleting: {e}")
                
                # Edit form (shown when edit button is clicked)
                if st.session_state.get(f"editing_introducer_{intro['id']}", False):
                    with st.form(f"edit_form_{intro['id']}"):
                        edit_name = st.text_input("Name", value=intro['name'], key=f"edit_name_{intro['id']}")
                        edit_discount_type = st.selectbox("Discount Type", 
                                                         ["tier_up", "percentage", "no_discount"],
                                                         index=0 if intro['discount_type'] == 'tier_up' else (1 if intro['discount_type'] == 'percentage' else 2),
                                                         key=f"edit_type_{intro['id']}")
                        edit_discount_value = st.number_input("Discount Value",
                                                             value=float(intro['discount_value']),
                                                             min_value=0.0,
                                                             step=0.1,
                                                             key=f"edit_value_{intro['id']}",
                                                             disabled=(edit_discount_type == "no_discount"))
                        
                        col_save, col_cancel = st.columns(2)
                        with col_save:
                            save_btn = st.form_submit_button("💾 Save")
                        with col_cancel:
                            cancel_btn = st.form_submit_button("❌ Cancel")
                        
                        if save_btn:
                            if not edit_name or not edit_name.strip():
                                st.error("Please enter a name.")
                            else:
                                try:
                                    # For no_discount type, set value to 0
                                    discount_value = 0.0 if edit_discount_type == "no_discount" else edit_discount_value
                                    db.update_introducer(intro['id'], edit_name.strip(), edit_discount_type, discount_value)
                                    st.success(f"Updated: {edit_name}")
                                    st.session_state[f"editing_introducer_{intro['id']}"] = False
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error updating: {e}")
                        
                        if cancel_btn:
                            st.session_state[f"editing_introducer_{intro['id']}"] = False
                            st.rerun()
        else:
            st.info("No introducers added yet. Add one using the form above.")
    
    except Exception as e:
        st.error(f"Error loading introducers: {e}")
        import traceback
        st.code(traceback.format_exc())
    
    st.markdown("---")
    
    # Filters
    st.markdown("#### 🔍 Filter Submissions")
    with st.expander("Filter Options", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            filter_start_date = st.date_input("Start Date", value=None, key="filter_start_date")
            filter_client = st.text_input("Client Name (contains)", key="filter_client")
            filter_ref = st.text_input("Reference Number (contains)", key="filter_ref")
        with col2:
            filter_end_date = st.date_input("End Date", value=None, key="filter_end_date")
            filter_lpa = st.text_input("LPA (contains)", key="filter_lpa")
            filter_nca = st.text_input("NCA (contains)", key="filter_nca")
        
        apply_filters = st.button("Apply Filters", key="apply_filters_btn")
    
    # Load submissions
    try:
        if apply_filters or any([filter_start_date, filter_end_date, filter_client, filter_lpa, filter_nca, filter_ref]):
            # Apply filters
            df = db.filter_submissions(
                start_date=filter_start_date.isoformat() if filter_start_date else None,
                end_date=filter_end_date.isoformat() if filter_end_date else None,
                client_name=filter_client if filter_client else None,
                lpa=filter_lpa if filter_lpa else None,
                nca=filter_nca if filter_nca else None,
                reference_number=filter_ref if filter_ref else None
            )
        else:
            # Show all submissions (limited to last 100)
            df = db.get_all_submissions(limit=100)
        
        st.markdown(f"#### 📋 Submissions ({len(df)} records)")
        
        if df.empty:
            st.info("No submissions found.")
        else:
            # Select columns to display
            display_cols = [
                "id", "submission_date", "client_name", "reference_number",
                "site_location", "target_lpa", "target_nca",
                "contract_size", "total_cost", "total_with_admin",
                "num_banks_selected", "promoter_name"
            ]
            display_cols = [c for c in display_cols if c in df.columns]
            
            # Format dates and numbers
            df_display = df[display_cols].copy()
            if "submission_date" in df_display.columns:
                df_display["submission_date"] = pd.to_datetime(df_display["submission_date"]).dt.strftime("%Y-%m-%d %H:%M")
            if "total_cost" in df_display.columns:
                df_display["total_cost"] = df_display["total_cost"].apply(lambda x: f"£{x:,.0f}" if pd.notna(x) else "")
            if "total_with_admin" in df_display.columns:
                df_display["total_with_admin"] = df_display["total_with_admin"].apply(lambda x: f"£{x:,.0f}" if pd.notna(x) else "")
            
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            
            # Export to CSV
            st.markdown("#### 📥 Export Data")
            col1, col2 = st.columns(2)
            with col1:
                # Export displayed submissions
                csv_bytes = db.export_to_csv(df)
                st.download_button(
                    "📥 Download Submissions CSV",
                    data=csv_bytes,
                    file_name=f"submissions_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            
            # View details of a specific submission
            st.markdown("#### 🔎 View Submission Details")
            submission_ids = df["id"].tolist()
            selected_id = st.selectbox("Select Submission ID", submission_ids, key="selected_submission_id")
            
            if selected_id and st.button("View Details", key="view_details_btn"):
                submission = db.get_submission_by_id(selected_id)
                allocations = db.get_allocations_for_submission(selected_id)
                
                if submission:
                    st.markdown("##### Submission Details")
                    
                    # Basic info
                    st.write(f"**Client:** {submission['client_name']}")
                    st.write(f"**Reference:** {submission['reference_number']}")
                    st.write(f"**Location:** {submission['site_location']}")
                    st.write(f"**Date:** {submission['submission_date']}")
                    st.write(f"**LPA:** {submission['target_lpa']}")
                    st.write(f"**NCA:** {submission['target_nca']}")
                    st.write(f"**Contract Size:** {submission['contract_size']}")
                    st.write(f"**Total Cost:** £{submission['total_cost']:,.0f}")
                    st.write(f"**Total with Admin:** £{submission['total_with_admin']:,.0f}")
                    
                    # Promoter info (if available)
                    if submission.get('promoter_name'):
                        st.write(f"**Promoter/Introducer:** {submission['promoter_name']}")
                        if submission.get('promoter_discount_type') == 'tier_up':
                            st.write(f"**Discount Type:** Tier Up")
                        elif submission.get('promoter_discount_type') == 'percentage':
                            st.write(f"**Discount Type:** Percentage ({submission.get('promoter_discount_value', 0)}%)")
                    
                    # Allocations
                    if not allocations.empty:
                        st.markdown("##### Allocation Details")
                        st.dataframe(allocations, use_container_width=True, hide_index=True)
                        
                        # Export allocations
                        alloc_csv = allocations.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            "📥 Download Allocation Details CSV",
                            data=alloc_csv,
                            file_name=f"allocation_details_{selected_id}.csv",
                            mime="text/csv"
                        )
    
    except Exception as e:
        st.error(f"Error loading submissions: {e}")
        import traceback
        st.code(traceback.format_exc())
    
    # Stop here - don't render the rest of the app
    st.stop()

# ================= Quote Management Mode =================
if st.session_state.app_mode == "Quote Management":
    st.markdown("### 🔍 Quote Management & Requotes")
    
    if db is None:
        st.error("Database is not available.")
        st.stop()
    
    # Logout button
    if st.button("🔓 Return to Optimiser", key="quote_mgmt_return"):
        st.session_state.app_mode = "Optimiser"
        st.rerun()
    
    # Tab navigation
    tab1, tab2, tab3 = st.tabs(["Search Quotes", "Customer Management", "Create Requote"])
    
    # ================= Tab 1: Search Quotes =================
    with tab1:
        st.markdown("#### 🔍 Search Existing Quotes")
        
        # Search filters
        with st.expander("🔎 Search Filters", expanded=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                search_client = st.text_input("Client Name (contains)", key="search_client")
                search_ref = st.text_input("Reference Number (contains)", key="search_ref")
            with col2:
                search_location = st.text_input("Development Location (contains)", key="search_location")
                search_lpa = st.text_input("LPA (contains)", key="search_lpa")
            with col3:
                search_start_date = st.date_input("Start Date", value=None, key="search_start_date")
                search_end_date = st.date_input("End Date", value=None, key="search_end_date")
            
            search_btn = st.button("🔍 Search", key="search_quotes_btn", type="primary")
        
        # Perform search
        if search_btn or any([search_client, search_ref, search_location, search_lpa, search_start_date, search_end_date]):
            try:
                # Build custom query for location search
                if search_location:
                    query = "SELECT * FROM submissions WHERE 1=1"
                    params = {}
                    
                    if search_start_date:
                        query += " AND submission_date >= %(start_date)s"
                        params["start_date"] = search_start_date.isoformat()
                    if search_end_date:
                        query += " AND submission_date <= %(end_date)s"
                        params["end_date"] = search_end_date.isoformat()
                    if search_client:
                        query += " AND client_name ILIKE %(client_name)s"
                        params["client_name"] = f"%{search_client}%"
                    if search_ref:
                        query += " AND reference_number ILIKE %(reference_number)s"
                        params["reference_number"] = f"%{search_ref}%"
                    if search_lpa:
                        query += " AND target_lpa ILIKE %(lpa)s"
                        params["lpa"] = f"%{search_lpa}%"
                    if search_location:
                        query += " AND site_location ILIKE %(location)s"
                        params["location"] = f"%{search_location}%"
                    
                    query += " ORDER BY submission_date DESC LIMIT 100"
                    
                    # Use pd.read_sql_query without text() wrapper - it handles parameters correctly
                    engine = db._get_connection()
                    with engine.connect() as conn:
                        results_df = pd.read_sql_query(query, conn, params=params)
                else:
                    # Use standard filter
                    results_df = db.filter_submissions(
                        start_date=search_start_date.isoformat() if search_start_date else None,
                        end_date=search_end_date.isoformat() if search_end_date else None,
                        client_name=search_client if search_client else None,
                        lpa=search_lpa if search_lpa else None,
                        reference_number=search_ref if search_ref else None
                    )
                
                st.markdown(f"#### 📋 Search Results ({len(results_df)} quotes found)")
                
                if results_df.empty:
                    st.info("No quotes found matching your criteria.")
                else:
                    # Display results
                    display_cols = [
                        "id", "submission_date", "client_name", "reference_number",
                        "site_location", "target_lpa", "contract_size", 
                        "total_with_admin", "customer_id"
                    ]
                    display_cols = [c for c in display_cols if c in results_df.columns]
                    
                    df_display = results_df[display_cols].copy()
                    if "submission_date" in df_display.columns:
                        df_display["submission_date"] = pd.to_datetime(df_display["submission_date"]).dt.strftime("%Y-%m-%d %H:%M")
                    if "total_with_admin" in df_display.columns:
                        df_display["total_with_admin"] = df_display["total_with_admin"].apply(
                            lambda x: f"£{x:,.0f}" if pd.notna(x) else ""
                        )
                    
                    st.dataframe(df_display, use_container_width=True, hide_index=True)
                    
                    # View quote details
                    st.markdown("#### 👁️ View Quote Details")
                    quote_ids = results_df["id"].tolist()
                    selected_quote_id = st.selectbox("Select Quote ID to View", quote_ids, key="selected_quote_view")
                    
                    # Use session state to persist the view details state
                    if "viewing_quote_id" not in st.session_state:
                        st.session_state.viewing_quote_id = None
                    
                    if st.button("View Details", key="view_quote_details"):
                        st.session_state.viewing_quote_id = selected_quote_id
                    
                    # Show details if we have a quote to view
                    if st.session_state.viewing_quote_id is not None:
                        submission = db.get_submission_by_id(st.session_state.viewing_quote_id)
                        
                        if submission:
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.markdown("##### Quote Information")
                                st.write(f"**ID:** {submission['id']}")
                                st.write(f"**Client:** {submission['client_name']}")
                                st.write(f"**Reference:** {submission['reference_number']}")
                                st.write(f"**Location:** {submission['site_location']}")
                                st.write(f"**Date:** {submission['submission_date']}")
                                st.write(f"**Contract Size:** {submission['contract_size']}")
                                st.write(f"**Total with Admin:** £{submission['total_with_admin']:,.0f}")
                            
                            with col2:
                                st.markdown("##### Location & Banks")
                                st.write(f"**LPA:** {submission['target_lpa']}")
                                st.write(f"**NCA:** {submission['target_nca']}")
                                st.write(f"**Banks Used:** {submission['num_banks_selected']}")
                                if submission.get('promoter_name'):
                                    st.write(f"**Promoter:** {submission['promoter_name']}")
                                if submission.get('customer_id'):
                                    customer = db.get_customer_by_id(submission['customer_id'])
                                    if customer:
                                        st.write(f"**Customer:** {customer['client_name']}")
                                        if customer.get('email'):
                                            st.write(f"**Email:** {customer['email']}")
                            
                            # Show demand details
                            if submission.get('demand_habitats'):
                                st.markdown("##### Demand Details")
                                demand_data = submission['demand_habitats']
                                if isinstance(demand_data, str):
                                    demand_data = json.loads(demand_data)
                                if demand_data:
                                    demand_df = pd.DataFrame(demand_data)
                                    st.dataframe(demand_df, use_container_width=True, hide_index=True)
                            
                            # Show allocation details
                            allocations = db.get_allocations_for_submission(selected_quote_id)
                            if not allocations.empty:
                                st.markdown("##### Allocation Details")
                                st.dataframe(allocations, use_container_width=True, hide_index=True)
                            
                            # Add button to load quote into optimizer for editing
                            st.markdown("---")
                            st.markdown("##### 📝 Edit This Quote")
                            st.info("Load this quote into the Optimizer to modify demand, add/remove habitats, and regenerate the report.")
                            
                            if st.button("🔄 Load Quote into Optimizer", key="load_quote_btn", type="primary"):
                                try:
                                    # Load location data
                                    st.session_state["target_lpa"] = submission['target_lpa']
                                    st.session_state["target_nca"] = submission['target_nca']
                                    st.session_state["target_lat"] = submission.get('target_lat')
                                    st.session_state["target_lon"] = submission.get('target_lon')
                                    st.session_state["site_location"] = submission['site_location']
                                    
                                    # Also set the dropdown selection variables for LPA/NCA
                                    st.session_state["selected_lpa_dropdown"] = submission['target_lpa']
                                    st.session_state["selected_nca_dropdown"] = submission['target_nca']
                                    st.session_state["use_lpa_nca_dropdown"] = True
                                    st.session_state["target_lpa_name"] = submission['target_lpa']
                                    st.session_state["target_nca_name"] = submission['target_nca']
                                    
                                    # Initialize neighbors and geometry states (will be empty until user clicks Apply LPA/NCA if needed)
                                    st.session_state["lpa_neighbors"] = []
                                    st.session_state["nca_neighbors"] = []
                                    st.session_state["lpa_neighbors_norm"] = []
                                    st.session_state["nca_neighbors_norm"] = []
                                    
                                    # Initialize map and geometry states to prevent errors during optimization
                                    st.session_state["lpa_geojson"] = None
                                    st.session_state["nca_geojson"] = None
                                    st.session_state["bank_geo_cache"] = {}
                                    st.session_state["bank_catchment_geo"] = {}
                                    st.session_state["optimization_complete"] = False
                                    st.session_state["last_alloc_df"] = None
                                    
                                    # Try to fetch LPA/NCA geometry if we have coordinates
                                    if st.session_state["target_lat"] and st.session_state["target_lon"]:
                                        try:
                                            lat = st.session_state["target_lat"]
                                            lon = st.session_state["target_lon"]
                                            lpa_feat = arcgis_point_query(LPA_URL, lat, lon, "LAD24NM")
                                            nca_feat = arcgis_point_query(NCA_URL, lat, lon, "NCA_Name")
                                            lpa_geom_esri = lpa_feat.get("geometry")
                                            nca_geom_esri = nca_feat.get("geometry")
                                            st.session_state["lpa_geojson"] = esri_polygon_to_geojson(lpa_geom_esri)
                                            st.session_state["nca_geojson"] = esri_polygon_to_geojson(nca_geom_esri)
                                            
                                            # Optionally fetch neighbors for better tier calculations
                                            lpa_nei = [n for n in layer_intersect_names(LPA_URL, lpa_geom_esri, "LAD24NM") if n != submission['target_lpa']]
                                            nca_nei = [n for n in layer_intersect_names(NCA_URL, nca_geom_esri, "NCA_Name") if n != submission['target_nca']]
                                            st.session_state["lpa_neighbors"] = lpa_nei
                                            st.session_state["nca_neighbors"] = nca_nei
                                            st.session_state["lpa_neighbors_norm"] = [norm_name(n) for n in lpa_nei]
                                            st.session_state["nca_neighbors_norm"] = [norm_name(n) for n in nca_nei]
                                        except Exception as geo_error:
                                            # If fetching geometry fails, that's OK - optimizer will work with 'far' tier
                                            st.warning(f"Could not fetch location geometry (optimization will use 'far' tier): {geo_error}")
                                    
                                    # Load client info
                                    st.session_state["email_client_name"] = submission['client_name']
                                    st.session_state["email_ref_number"] = submission['reference_number']
                                    st.session_state["email_location"] = submission['site_location']
                                    
                                    # Load demand habitats
                                    demand_data = submission.get('demand_habitats')
                                    if isinstance(demand_data, str):
                                        demand_data = json.loads(demand_data)
                                    
                                    if demand_data:
                                        # Load demand rows into session state
                                        st.session_state["demand_rows"] = []
                                        for idx, habitat_data in enumerate(demand_data):
                                            st.session_state["demand_rows"].append({
                                                "id": idx + 1,
                                                "habitat_name": habitat_data.get("habitat_name", ""),
                                                "units": float(habitat_data.get("units_required", 0.0) or habitat_data.get("units", 0.0))
                                            })
                                        st.session_state["_next_demand_id"] = len(demand_data) + 1
                                    
                                    # Load manual entries if they exist
                                    if submission.get('manual_hedgerow_entries'):
                                        manual_hedgerow = submission['manual_hedgerow_entries']
                                        if isinstance(manual_hedgerow, str):
                                            manual_hedgerow = json.loads(manual_hedgerow)
                                        st.session_state["manual_hedgerow_rows"] = manual_hedgerow if manual_hedgerow else []
                                    
                                    if submission.get('manual_watercourse_entries'):
                                        manual_watercourse = submission['manual_watercourse_entries']
                                        if isinstance(manual_watercourse, str):
                                            manual_watercourse = json.loads(manual_watercourse)
                                        st.session_state["manual_watercourse_rows"] = manual_watercourse if manual_watercourse else []
                                    
                                    # Load promoter info if exists
                                    if submission.get('promoter_name'):
                                        st.session_state["selected_promoter"] = submission['promoter_name']
                                        st.session_state["promoter_discount_type"] = submission.get('promoter_discount_type')
                                        st.session_state["promoter_discount_value"] = submission.get('promoter_discount_value')
                                    
                                    # Load customer ID if exists
                                    if submission.get('customer_id'):
                                        st.session_state["selected_customer_id"] = submission['customer_id']
                                    
                                    # Set mode to Optimiser (the radio button will pick this up on next rerun via line 343)
                                    st.session_state.app_mode = "Optimiser"
                                    
                                    st.success("✅ Quote loaded successfully! Switching to Optimizer mode...")
                                    st.info("💡 You can now modify demand, run optimization, add/remove habitats, and download a new email report.")
                                    
                                    # Use st.rerun() to refresh the page with the new mode
                                    st.rerun()
                                    
                                except Exception as e:
                                    st.error(f"Error loading quote: {e}")
                                    import traceback
                                    st.code(traceback.format_exc())
                        else:
                            st.error("Quote not found.")
            
            except Exception as e:
                st.error(f"Error searching quotes: {e}")
                import traceback
                st.code(traceback.format_exc())
    
    # ================= Tab 2: Customer Management =================
    with tab2:
        st.markdown("#### 👥 Customer Management")
        
        # Button to populate customers from existing submissions
        with st.expander("🔄 Import Customers from Existing Quotes", expanded=False):
            st.info("This will create customer records for all unique client names in existing quotes that don't already have a customer record.")
            
            # Show current status
            try:
                from sqlalchemy import text
                engine = db._get_connection()
                with engine.connect() as conn:
                    # Count submissions without customer_id
                    result = conn.execute(text("""
                        SELECT COUNT(DISTINCT client_name) 
                        FROM submissions 
                        WHERE client_name IS NOT NULL 
                          AND client_name != ''
                          AND customer_id IS NULL
                    """))
                    unlinked_count = result.fetchone()[0]
                    
                    # Count total unique client names
                    result = conn.execute(text("""
                        SELECT COUNT(DISTINCT client_name) 
                        FROM submissions 
                        WHERE client_name IS NOT NULL 
                          AND client_name != ''
                    """))
                    total_count = result.fetchone()[0]
                    
                    # Count existing customers
                    result = conn.execute(text("SELECT COUNT(*) FROM customers"))
                    customer_count = result.fetchone()[0]
                    
                    st.caption(f"📊 Status: {unlinked_count} unique client names without customer records | {customer_count} existing customers | {total_count} total unique client names in submissions")
            except Exception as e:
                st.caption(f"Could not load status: {e}")
            
            if st.button("Import Customers from Submissions", key="import_customers_btn"):
                try:
                    created_count, errors = db.populate_customers_from_submissions()
                    
                    if errors:
                        st.warning(f"⚠️ Encountered {len(errors)} error(s) during import:")
                        for error in errors[:5]:  # Show first 5 errors
                            st.error(error)
                        if len(errors) > 5:
                            st.caption(f"... and {len(errors) - 5} more errors")
                    
                    if created_count > 0:
                        st.success(f"✅ Successfully created {created_count} customer record(s) from existing submissions!")
                        st.rerun()
                    elif not errors:
                        st.info("ℹ️ No new customers to import. All existing client names already have customer records.")
                        st.caption("💡 Tip: If you expect to see customers here, check that submissions have valid client_name values and that the customers table is accessible.")
                except Exception as e:
                    st.error(f"Error importing customers: {e}")
                    import traceback
                    st.code(traceback.format_exc())
        
        # Add new customer
        with st.expander("➕ Add New Customer", expanded=False):
            with st.form("add_customer_form"):
                st.markdown("**Basic Information:**")
                col1, col2 = st.columns([1, 3])
                with col1:
                    cust_title = st.selectbox("Title", ["", "Mr", "Mrs", "Miss", "Ms", "Dr", "Prof"], key="cust_title")
                with col2:
                    cust_client_name = st.text_input("Client Name*", key="cust_client_name")
                
                col3, col4 = st.columns(2)
                with col3:
                    cust_first_name = st.text_input("First Name", key="cust_first_name")
                with col4:
                    cust_last_name = st.text_input("Last Name", key="cust_last_name")
                
                st.markdown("**Company/Organization:**")
                cust_company_name = st.text_input("Company Name", key="cust_company_name")
                cust_contact_person = st.text_input("Contact Person", key="cust_contact_person")
                cust_address = st.text_area("Address", key="cust_address")
                
                st.markdown("**Contact Details:**")
                col1, col2 = st.columns(2)
                with col1:
                    cust_email = st.text_input("Email Address", key="cust_email")
                with col2:
                    cust_mobile = st.text_input("Mobile Number", key="cust_mobile")
                
                add_cust_btn = st.form_submit_button("Add Customer")
                
                if add_cust_btn:
                    if not cust_client_name or not cust_client_name.strip():
                        st.error("Client name is required.")
                    elif not cust_email and not cust_mobile:
                        st.error("At least one of Email or Mobile Number is required.")
                    else:
                        try:
                            customer_id = db.add_customer(
                                client_name=cust_client_name.strip(),
                                title=cust_title if cust_title else None,
                                first_name=cust_first_name.strip() if cust_first_name else None,
                                last_name=cust_last_name.strip() if cust_last_name else None,
                                company_name=cust_company_name.strip() if cust_company_name else None,
                                contact_person=cust_contact_person.strip() if cust_contact_person else None,
                                address=cust_address.strip() if cust_address else None,
                                email=cust_email.strip() if cust_email else None,
                                mobile_number=cust_mobile.strip() if cust_mobile else None
                            )
                            st.success(f"✅ Customer added successfully! ID: {customer_id}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error adding customer: {e}")
        
        # List existing customers
        try:
            customers = db.get_all_customers()
            
            if customers:
                st.markdown(f"##### Existing Customers ({len(customers)})")
                
                # Create DataFrame for display
                customers_df = pd.DataFrame(customers)
                display_customer_cols = ["id", "title", "first_name", "last_name", "client_name", 
                                         "company_name", "email", "mobile_number", "created_date"]
                display_customer_cols = [c for c in display_customer_cols if c in customers_df.columns]
                
                df_cust_display = customers_df[display_customer_cols].copy()
                if "created_date" in df_cust_display.columns:
                    df_cust_display["created_date"] = pd.to_datetime(df_cust_display["created_date"]).dt.strftime("%Y-%m-%d")
                
                st.dataframe(df_cust_display, use_container_width=True, hide_index=True)
                
                # Edit customer section
                st.markdown("##### ✏️ Edit Customer Details")
                customer_id_to_edit = st.selectbox(
                    "Select Customer to Edit", 
                    options=[c['id'] for c in customers],
                    format_func=lambda x: f"ID {x}: {next((c['client_name'] for c in customers if c['id'] == x), 'Unknown')}",
                    key="customer_id_to_edit"
                )
                
                if st.button("Load Customer for Editing", key="load_edit_customer_btn"):
                    st.session_state.edit_customer_id = customer_id_to_edit
                    selected_customer = next((c for c in customers if c['id'] == customer_id_to_edit), None)
                    if selected_customer:
                        st.session_state.edit_customer_data = selected_customer
                        st.rerun()
                
                # Show edit form if customer is loaded
                if hasattr(st.session_state, 'edit_customer_id') and hasattr(st.session_state, 'edit_customer_data'):
                    customer_data = st.session_state.edit_customer_data
                    
                    with st.form("edit_customer_form"):
                        st.markdown(f"**Editing Customer ID: {st.session_state.edit_customer_id}**")
                        
                        st.markdown("**Basic Information:**")
                        col1, col2 = st.columns([1, 3])
                        with col1:
                            edit_title = st.selectbox("Title", ["", "Mr", "Mrs", "Miss", "Ms", "Dr", "Prof"], 
                                                     index=["", "Mr", "Mrs", "Miss", "Ms", "Dr", "Prof"].index(customer_data.get('title', '') or ''),
                                                     key="edit_title")
                        with col2:
                            edit_client_name = st.text_input("Client Name*", value=customer_data.get('client_name', ''), key="edit_client_name")
                        
                        col3, col4 = st.columns(2)
                        with col3:
                            edit_first_name = st.text_input("First Name", value=customer_data.get('first_name', '') or '', key="edit_first_name")
                        with col4:
                            edit_last_name = st.text_input("Last Name", value=customer_data.get('last_name', '') or '', key="edit_last_name")
                        
                        st.markdown("**Company/Organization:**")
                        edit_company_name = st.text_input("Company Name", value=customer_data.get('company_name', '') or '', key="edit_company_name")
                        edit_contact_person = st.text_input("Contact Person", value=customer_data.get('contact_person', '') or '', key="edit_contact_person")
                        edit_address = st.text_area("Address", value=customer_data.get('address', '') or '', key="edit_address")
                        
                        st.markdown("**Contact Details:**")
                        col1, col2 = st.columns(2)
                        with col1:
                            edit_email = st.text_input("Email Address", value=customer_data.get('email', '') or '', key="edit_email")
                        with col2:
                            edit_mobile = st.text_input("Mobile Number", value=customer_data.get('mobile_number', '') or '', key="edit_mobile")
                        
                        col_submit, col_cancel = st.columns(2)
                        with col_submit:
                            update_cust_btn = st.form_submit_button("💾 Update Customer", type="primary")
                        with col_cancel:
                            cancel_edit_btn = st.form_submit_button("❌ Cancel")
                        
                        if update_cust_btn:
                            if not edit_client_name or not edit_client_name.strip():
                                st.error("Client name is required.")
                            else:
                                try:
                                    db.update_customer(
                                        customer_id=st.session_state.edit_customer_id,
                                        client_name=edit_client_name.strip(),
                                        title=edit_title if edit_title else None,
                                        first_name=edit_first_name.strip() if edit_first_name else None,
                                        last_name=edit_last_name.strip() if edit_last_name else None,
                                        company_name=edit_company_name.strip() if edit_company_name else None,
                                        contact_person=edit_contact_person.strip() if edit_contact_person else None,
                                        address=edit_address.strip() if edit_address else None,
                                        email=edit_email.strip() if edit_email else None,
                                        mobile_number=edit_mobile.strip() if edit_mobile else None
                                    )
                                    st.success(f"✅ Customer {st.session_state.edit_customer_id} updated successfully!")
                                    # Clear edit state
                                    del st.session_state.edit_customer_id
                                    del st.session_state.edit_customer_data
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error updating customer: {e}")
                        
                        if cancel_edit_btn:
                            # Clear edit state
                            if hasattr(st.session_state, 'edit_customer_id'):
                                del st.session_state.edit_customer_id
                            if hasattr(st.session_state, 'edit_customer_data'):
                                del st.session_state.edit_customer_data
                            st.rerun()
                
                # View customer quotes
                st.markdown("##### 🔍 View Customer Quotes")
                customer_id_select = st.selectbox("Select Customer ID", [c['id'] for c in customers], key="customer_id_select")
                
                if st.button("View Customer Quotes", key="view_customer_quotes_btn"):
                    # Get all submissions for this customer
                    engine = db._get_connection()
                    with engine.connect() as conn:
                        customer_quotes_df = pd.read_sql_query(
                            "SELECT * FROM submissions WHERE customer_id = %(customer_id)s ORDER BY submission_date DESC",
                            conn,
                            params={"customer_id": customer_id_select}
                        )
                    
                    if not customer_quotes_df.empty:
                        st.markdown(f"**{len(customer_quotes_df)} quotes found for this customer**")
                        
                        display_cols = ["id", "reference_number", "submission_date", "site_location", 
                                       "contract_size", "total_with_admin"]
                        display_cols = [c for c in display_cols if c in customer_quotes_df.columns]
                        
                        df_display = customer_quotes_df[display_cols].copy()
                        if "submission_date" in df_display.columns:
                            df_display["submission_date"] = pd.to_datetime(df_display["submission_date"]).dt.strftime("%Y-%m-%d")
                        if "total_with_admin" in df_display.columns:
                            df_display["total_with_admin"] = df_display["total_with_admin"].apply(
                                lambda x: f"£{x:,.0f}" if pd.notna(x) else ""
                            )
                        
                        st.dataframe(df_display, use_container_width=True, hide_index=True)
                    else:
                        st.info("No quotes found for this customer.")
            else:
                st.info("No customers added yet.")
        
        except Exception as e:
            st.error(f"Error loading customers: {e}")
            import traceback
            st.code(traceback.format_exc())
    
    # ================= Tab 3: Create Requote =================
    with tab3:
        st.markdown("#### 🔄 Create Requote")
        st.info("Select an existing quote to create a requote. The requote will have the same site location and customer info, but you can update the demand and reoptimize.")
        
        # Select quote to requote
        try:
            # Get recent submissions
            recent_quotes_df = db.get_all_submissions(limit=50)
            
            if not recent_quotes_df.empty:
                # Display selection interface
                st.markdown("##### Select Quote to Requote")
                
                # Create a readable display
                recent_quotes_df['display_text'] = (
                    recent_quotes_df['id'].astype(str) + " - " +
                    recent_quotes_df['reference_number'] + " - " +
                    recent_quotes_df['client_name'] + " - " +
                    recent_quotes_df['site_location']
                )
                
                quote_options = recent_quotes_df[['id', 'display_text']].set_index('id')['display_text'].to_dict()
                selected_requote_id = st.selectbox(
                    "Select Quote",
                    options=list(quote_options.keys()),
                    format_func=lambda x: quote_options[x],
                    key="selected_requote_id"
                )
                
                if selected_requote_id:
                    # Show current quote details
                    original_quote = db.get_submission_by_id(selected_requote_id)
                    
                    if original_quote:
                        st.markdown("##### Original Quote Details")
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.write(f"**Reference:** {original_quote['reference_number']}")
                            st.write(f"**Client:** {original_quote['client_name']}")
                        with col2:
                            st.write(f"**Location:** {original_quote['site_location']}")
                            st.write(f"**LPA:** {original_quote['target_lpa']}")
                        with col3:
                            st.write(f"**Total:** £{original_quote['total_with_admin']:,.0f}")
                            st.write(f"**Date:** {original_quote['submission_date']}")
                        
                        # Show what the new reference will be
                        new_ref = db.get_next_revision_number(original_quote['reference_number'])
                        st.info(f"📝 New requote will have reference: **{new_ref}**")
                        
                        # Create requote button
                        st.markdown("---")
                        st.markdown("##### Create Requote")
                        st.write("This will create a new quote as a separate record with the incremented reference number.")
                        st.write("⚠️ **Note:** Site location and customer info will be copied. You can update demand later in the Optimiser.")
                        
                        if st.button("🔄 Create Requote", type="primary", key="create_requote_btn"):
                            try:
                                new_submission_id = db.create_requote_from_submission(selected_requote_id)
                                st.success(f"✅ Requote created successfully!")
                                st.success(f"📋 New Reference: {new_ref}")
                                st.success(f"🆔 New Submission ID: {new_submission_id}")
                                st.info("💡 You can now search for this quote and view/edit it in the Optimiser mode.")
                            except Exception as e:
                                st.error(f"Error creating requote: {e}")
                                import traceback
                                st.code(traceback.format_exc())
            else:
                st.info("No quotes available to requote.")
        
        except Exception as e:
            st.error(f"Error loading quotes: {e}")
            import traceback
            st.code(traceback.format_exc())
    
    # Stop here - don't render the rest of the app
    st.stop()

# ================= Main Optimiser Mode (Default) =================
# All the existing optimiser code continues below

# ================= HTTP helpers =================
def http_get(url, params=None, headers=None, timeout=25):
    try:
        r = requests.get(url, params=params or {}, headers=headers or UA, timeout=timeout)
        r.raise_for_status()
        return r
    except requests.exceptions.Timeout:
        raise RuntimeError(f"Timeout connecting to {url}")
    except requests.exceptions.ConnectionError:
        raise RuntimeError(f"Connection error to {url}")
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"HTTP {e.response.status_code} error for {url}")
    except Exception as e:
        raise RuntimeError(f"HTTP error for {url}: {e}")

def http_post(url, data=None, headers=None, timeout=25):
    try:
        r = requests.post(url, data=data or {}, headers=headers or UA, timeout=timeout)
        r.raise_for_status()
        return r
    except requests.exceptions.Timeout:
        raise RuntimeError(f"Timeout connecting to {url}")
    except requests.exceptions.ConnectionError:
        raise RuntimeError(f"Connection error to {url}")
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"HTTP {e.response.status_code} error for {url}")
    except Exception as e:
        raise RuntimeError(f"HTTP POST error for {url}: {e}")

def safe_json(r: requests.Response) -> Dict[str, Any]:
    try:
        return r.json()
    except Exception:
        preview = (r.text or "")[:300]
        raise RuntimeError(f"Invalid JSON from {r.url} (status {r.status_code}). Starts: {preview}")

# ================= Geo helpers =================
def esri_polygon_to_geojson(geom: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not geom or "rings" not in geom:
        return None
    rings = geom.get("rings") or []
    if not rings:
        return None
    if len(rings) == 1:
        return {"type": "Polygon", "coordinates": [rings[0]]}
    return {"type": "MultiPolygon", "coordinates": [[ring] for ring in rings]}

def add_geojson_layer(fmap, geojson: Dict[str, Any], name: str, color: str, weight: int, fill_opacity: float = 0.05, show=True):
    if not geojson:
        return
    try:
        folium.GeoJson(
            geojson,
            name=name,
            show=show,
            style_function=lambda x: {"color": color, "fillOpacity": fill_opacity, "weight": weight},
            tooltip=name
        ).add_to(fmap)
    except Exception:
        pass

# --- Ledger helpers ---
def get_umbrella_for(hab_name: str, catalog: pd.DataFrame) -> str:
    """Return 'hedgerow' | 'watercourse' | 'area' for a habitat name using UmbrellaType; 
       also handles special Net Gain labels."""
    h = sstr(hab_name)
    if not h:
        return LEDGER_AREA
    if h == NET_GAIN_HEDGEROW_LABEL:
        return LEDGER_HEDGE
    if h == NET_GAIN_WATERCOURSE_LABEL:
        return LEDGER_WATER
    # Lookup in catalog
    m = catalog[catalog["habitat_name"].astype(str).str.strip() == h]
    umb = sstr(m.iloc[0]["UmbrellaType"]) if not m.empty and "UmbrellaType" in m.columns else ""
    umb = umb.lower()
    if umb == LEDGER_HEDGE:
        return LEDGER_HEDGE
    if umb == LEDGER_WATER:
        return LEDGER_WATER
    return LEDGER_AREA


# ================= Geocoding / lookups =================
def get_postcode_info(pc: str) -> Tuple[float, float, str]:
    pc_clean = sstr(pc).replace(" ", "").upper()
    r = http_get(POSTCODES_IO + pc_clean)
    js = safe_json(r)
    if js.get("status") != 200 or not js.get("result"):
        raise RuntimeError(f"Postcode lookup failed for '{pc}'.")
    data = js["result"]
    return float(data["latitude"]), float(data["longitude"]), sstr(data.get("admin_district") or data.get("admin_county"))

def geocode_address(addr: str) -> Tuple[float, float]:
    r = http_get(NOMINATIM_SEARCH, params={"q": sstr(addr), "format": "jsonv2", "limit": 1, "addressdetails": 0})
    js = safe_json(r)
    if isinstance(js, list) and js:
        lat, lon = js[0]["lat"], js[0]["lon"]
        return float(lat), float(lon)
    r = http_get("https://photon.komoot.io/api/", params={"q": sstr(addr), "limit": 1})
    js = safe_json(r)
    feats = js.get("features") or []
    if feats:
        lon, lat = feats[0]["geometry"]["coordinates"]
        return float(lat), float(lon)
    raise RuntimeError("Address geocoding failed.")

def arcgis_point_query(layer_url: str, lat: float, lon: float, out_fields: str) -> Dict[str, Any]:
    geometry_dict = {"x": lon, "y": lat, "spatialReference": {"wkid": 4326}}
    params = {
        "f": "json", "where": "1=1",
        "geometry": json.dumps(geometry_dict), "geometryType": "esriGeometryPoint",
        "inSR": 4326, "spatialRel": "esriSpatialRelIntersects",
        "outFields": out_fields or "*", "returnGeometry": "true", "outSR": 4326
    }
    r = http_get(f"{layer_url}/query", params=params)
    js = safe_json(r)
    feats = js.get("features") or []
    return feats[0] if feats else {}

def layer_intersect_names(layer_url: str, polygon_geom: Dict[str, Any], name_field: str) -> List[str]:
    if not polygon_geom:
        return []
    data = {
        "f": "json", "where": "1=1",
        "geometry": json.dumps(polygon_geom), "geometryType": "esriGeometryPolygon",
        "inSR": 4326, "spatialRel": "esriSpatialRelIntersects",
        "outFields": name_field, "returnGeometry": "false", "outSR": 4326,
        "geometryPrecision": 5,
    }
    r = http_post(f"{layer_url}/query", data=data)
    js = safe_json(r)
    names = [sstr((f.get("attributes") or {}).get(name_field)) for f in js.get("features", [])]
    return sorted({n for n in names if n})

def fetch_all_lpas_from_arcgis() -> List[str]:
    """
    Fetch all unique LPA names from the ArcGIS LPA layer.
    Uses a simple query to get all records.
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
        st.warning(f"Could not fetch LPA list from ArcGIS: {e}")
        return []

def fetch_all_ncas_from_arcgis() -> List[str]:
    """
    Fetch all unique NCA names from the ArcGIS NCA layer.
    Uses a simple query to get all records.
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
        st.warning(f"Could not fetch NCA list from ArcGIS: {e}")
        return []

def query_lpa_by_name(lpa_name: str) -> Dict[str, Any]:
    """
    Query LPA geometry and neighbors by name.
    Returns dict with geometry, neighbors, and normalized neighbors.
    """
    try:
        # Query for the specific LPA by name
        params = {
            "f": "json",
            "where": f"LAD24NM = '{lpa_name}'",
            "outFields": "LAD24NM",
            "returnGeometry": "true",
            "outSR": 4326
        }
        r = http_get(f"{LPA_URL}/query", params=params)
        js = safe_json(r)
        features = js.get("features", [])
        
        if not features:
            return {"geometry": None, "neighbors": [], "neighbors_norm": []}
        
        feat = features[0]
        lpa_geom_esri = feat.get("geometry")
        lpa_gj = esri_polygon_to_geojson(lpa_geom_esri)
        
        # Get neighbors
        lpa_nei = [n for n in layer_intersect_names(LPA_URL, lpa_geom_esri, "LAD24NM") if n != lpa_name]
        lpa_nei_norm = [norm_name(n) for n in lpa_nei]
        
        return {
            "geometry": lpa_gj,
            "geometry_esri": lpa_geom_esri,
            "neighbors": lpa_nei,
            "neighbors_norm": lpa_nei_norm
        }
    except Exception as e:
        st.warning(f"Could not fetch LPA geometry for {lpa_name}: {e}")
        return {"geometry": None, "neighbors": [], "neighbors_norm": []}

def query_nca_by_name(nca_name: str) -> Dict[str, Any]:
    """
    Query NCA geometry and neighbors by name.
    Returns dict with geometry, neighbors, and normalized neighbors.
    """
    try:
        # Query for the specific NCA by name
        params = {
            "f": "json",
            "where": f"NCA_Name = '{nca_name}'",
            "outFields": "NCA_Name",
            "returnGeometry": "true",
            "outSR": 4326
        }
        r = http_get(f"{NCA_URL}/query", params=params)
        js = safe_json(r)
        features = js.get("features", [])
        
        if not features:
            return {"geometry": None, "neighbors": [], "neighbors_norm": []}
        
        feat = features[0]
        nca_geom_esri = feat.get("geometry")
        nca_gj = esri_polygon_to_geojson(nca_geom_esri)
        
        # Get neighbors
        nca_nei = [n for n in layer_intersect_names(NCA_URL, nca_geom_esri, "NCA_Name") if n != nca_name]
        nca_nei_norm = [norm_name(n) for n in nca_nei]
        
        return {
            "geometry": nca_gj,
            "geometry_esri": nca_geom_esri,
            "neighbors": nca_nei,
            "neighbors_norm": nca_nei_norm
        }
    except Exception as e:
        st.warning(f"Could not fetch NCA geometry for {nca_name}: {e}")
        return {"geometry": None, "neighbors": [], "neighbors_norm": []}

def get_lpa_nca_for_point(lat: float, lon: float) -> Tuple[str, str]:
    lpa = sstr((arcgis_point_query(LPA_URL, lat, lon, "LAD24NM").get("attributes") or {}).get("LAD24NM"))
    nca = sstr((arcgis_point_query(NCA_URL, lat, lon, "NCA_Name").get("attributes") or {}).get("NCA_Name"))
    return lpa, nca

def get_catchment_geo_for_point(lat: float, lon: float) -> Tuple[str, Optional[Dict[str, Any]], str, Optional[Dict[str, Any]]]:
    lpa_feat = arcgis_point_query(LPA_URL, lat, lon, "LAD24NM")
    nca_feat = arcgis_point_query(NCA_URL, lat, lon, "NCA_Name")
    lpa_name = sstr((lpa_feat.get("attributes") or {}).get("LAD24NM"))
    nca_name = sstr((nca_feat.get("attributes") or {}).get("NCA_Name"))
    lpa_gj = esri_polygon_to_geojson(lpa_feat.get("geometry"))
    nca_gj = esri_polygon_to_geojson(nca_feat.get("geometry"))
    return lpa_name, lpa_gj, nca_name, nca_gj

# ================= Watercourse Catchments =================
def wfs_point_query(wfs_url: str, lat: float, lon: float) -> Dict[str, Any]:
    """
    Query WFS service for features containing a point.
    Returns the first matching feature or empty dict.
    """
    try:
        # WFS GetFeature request with point geometry filter
        params = {
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeName": "ms:Water_Framework_Directive_River_Waterbody_Catchments_Cycle_2",  # Will be overridden
            "outputFormat": "application/json",
            "srsName": "EPSG:4326",
            # CQL filter for point intersection
            "CQL_FILTER": f"INTERSECTS(geom, POINT({lon} {lat}))"
        }
        
        r = http_get(wfs_url, params=params, timeout=10)
        if r.status_code != 200:
            return {}
        
        js = safe_json(r)
        features = js.get("features", [])
        return features[0] if features else {}
    except Exception:
        return {}

def get_watercourse_catchments_for_point(lat: float, lon: float) -> Tuple[str, str]:
    """
    Get waterbody and operational catchment names for a point.
    Returns (waterbody_name, operational_catchment_name)
    """
    waterbody_name = ""
    operational_name = ""
    
    try:
        # Query waterbody catchment
        wb_feat = wfs_point_query(WATERBODY_CATCHMENT_URL, lat, lon)
        if wb_feat and "properties" in wb_feat:
            # Try common field names for waterbody name
            props = wb_feat["properties"]
            waterbody_name = sstr(
                props.get("name") or 
                props.get("NAME") or 
                props.get("wb_name") or 
                props.get("WB_NAME") or 
                props.get("waterbody_name") or
                ""
            )
    except Exception:
        pass
    
    try:
        # Query operational catchment
        op_feat = wfs_point_query(OPERATIONAL_CATCHMENT_URL, lat, lon)
        if op_feat and "properties" in op_feat:
            # Try common field names for operational catchment name
            props = op_feat["properties"]
            operational_name = sstr(
                props.get("name") or 
                props.get("NAME") or 
                props.get("oc_name") or 
                props.get("OC_NAME") or 
                props.get("operational_catchment_name") or
                ""
            )
    except Exception:
        pass
    
    return waterbody_name, operational_name

def calculate_watercourse_srm(site_waterbody: str, site_operational: str,
                               bank_waterbody: str, bank_operational: str) -> float:
    """
    Calculate Spatial Risk Multiplier (SRM) for watercourse habitats based on catchment proximity.
    
    SRM Rules:
    - Same waterbody catchment: SRM = 1.0 (no uplift)
    - Same operational catchment (different waterbody): SRM = 0.75 (buyer needs 4/3× units)
    - Outside operational catchment: SRM = 0.5 (buyer needs 2× units)
    
    Returns SRM multiplier (1.0, 0.75, or 0.5)
    """
    # Normalize for comparison
    site_wb = norm_name(site_waterbody)
    site_op = norm_name(site_operational)
    bank_wb = norm_name(bank_waterbody)
    bank_op = norm_name(bank_operational)
    
    # If catchment data is missing, default to far (0.5)
    if not site_wb and not site_op:
        return 0.5
    if not bank_wb and not bank_op:
        return 0.5
    
    # Same waterbody catchment
    if site_wb and bank_wb and site_wb == bank_wb:
        return 1.0
    
    # Same operational catchment (different waterbody)
    if site_op and bank_op and site_op == bank_op:
        return 0.75
    
    # Outside operational catchment
    return 0.5

# ================= Tiering =================
def tier_for_bank(bank_lpa: str, bank_nca: str,
                  t_lpa: str, t_nca: str,
                  lpa_neigh: List[str], nca_neigh: List[str],
                  lpa_neigh_norm: Optional[List[str]] = None,
                  nca_neigh_norm: Optional[List[str]] = None) -> str:
    b_lpa = norm_name(bank_lpa)
    b_nca = norm_name(bank_nca)
    t_lpa_n = norm_name(t_lpa)
    t_nca_n = norm_name(t_nca)
    if lpa_neigh_norm is None:
        lpa_neigh_norm = [norm_name(x) for x in (lpa_neigh or [])]
    if nca_neigh_norm is None:
        nca_neigh_norm = [norm_name(x) for x in (nca_neigh or [])]
    
    # Evaluate LPA axis independently
    lpa_same = b_lpa and t_lpa_n and b_lpa == t_lpa_n
    lpa_neighbour = b_lpa and b_lpa in lpa_neigh_norm
    
    # Evaluate NCA axis independently  
    nca_same = b_nca and t_nca_n and b_nca == t_nca_n
    nca_neighbour = b_nca and b_nca in nca_neigh_norm
    
    # Return best (closest) category across both axes
    if lpa_same or nca_same:
        return "local"  # Local > Adjacent > Far
    elif lpa_neighbour or nca_neighbour:
        return "adjacent"  # Adjacent > Far
    else:
        return "far"

def select_contract_size(total_units: float, present: List[str]) -> str:
    tiers = set([sstr(x).lower() for x in present])
    if "fractional" in tiers and total_units < 0.1: return "fractional"
    if "small" in tiers and total_units < 2.5: return "small"
    if "medium" in tiers and total_units < 15: return "medium"
    for t in ["large", "medium", "small", "fractional"]:
        if t in tiers: return t
    return sstr(next(iter(present), "small")).lower()

def get_admin_fee_for_contract_size(contract_size: str) -> float:
    """
    Get the admin fee based on contract size.
    Fractional quotes get £300, all others get £500.
    """
    if sstr(contract_size).lower() == "fractional":
        return ADMIN_FEE_FRACTIONAL_GBP
    return ADMIN_FEE_GBP

# ================= Load Reference Tables from Supabase =================
@st.cache_data(ttl=600)
def load_backend() -> Dict[str, pd.DataFrame]:
    """
    Load all reference/config tables from Supabase Postgres.
    Tables are cached for 10 minutes (600 seconds) to reduce database queries.
    """
    try:
        return repo.fetch_all_reference_tables()
    except Exception as e:
        st.error(f"Failed to load reference tables from database: {e}")
        st.stop()

# Load backend tables from Supabase
try:
    backend = load_backend()
except Exception as e:
    st.error(f"❌ Cannot connect to database. Please check your database configuration.")
    st.error(f"Error: {e}")
    st.stop()

# Validate that required tables are not empty
if st.session_state.app_mode == "Optimiser":
    # Validate reference tables before continuing
    is_valid, errors = repo.validate_reference_tables()
    if not is_valid:
        st.error("❌ Required reference tables are missing or empty:")
        for error in errors:
            st.error(f"  • {error}")
        st.info("💡 Please contact your administrator to populate the database tables.")
        st.stop()

# Configure quotes policy for stock availability
with st.sidebar:
    st.subheader("Stock Policy")
    quotes_hold_policy = st.selectbox(
        "Quotes policy for stock availability",
        ["Ignore quotes (default)", "Quotes hold 100%", "Quotes hold 50%"],
        index=0,
        help="How to treat 'quoted' units when computing quantity_available."
    )

# ================= BANK_KEY normalisation =================
def make_bank_key_col(df: pd.DataFrame, banks_df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    has_df_name = "bank_name" in out.columns and out["bank_name"].astype(str).str.strip().ne("").any()
    if not has_df_name:
        if "bank_id" in out.columns and "bank_id" in banks_df.columns and "bank_name" in banks_df.columns:
            m = banks_df[["bank_id","bank_name"]].drop_duplicates()
            out = out.merge(m, on="bank_id", how="left")
    if "bank_name" in out.columns:
        out["BANK_KEY"] = out["bank_name"].where(out["bank_name"].astype(str).str.strip().ne(""), out.get("bank_id"))
    else:
        out["BANK_KEY"] = out.get("bank_id")
    out["BANK_KEY"] = out["BANK_KEY"].map(sstr)
    return out

# Apply quotes policy if present
if {"available_excl_quotes", "quoted"}.issubset(backend["Stock"].columns):
    s = backend["Stock"].copy()
    s["available_excl_quotes"] = pd.to_numeric(s["available_excl_quotes"], errors="coerce").fillna(0)
    s["quoted"] = pd.to_numeric(s["quoted"], errors="coerce").fillna(0)

    if quotes_hold_policy == "Ignore quotes (default)":
        s["quantity_available"] = s["available_excl_quotes"]
    elif quotes_hold_policy == "Quotes hold 100%":
        s["quantity_available"] = (s["available_excl_quotes"] - s["quoted"]).clip(lower=0)
    else:
        s["quantity_available"] = (s["available_excl_quotes"] - 0.5 * s["quoted"]).clip(lower=0)

    backend["Stock"] = s

# Enrich Banks geography
def bank_row_to_latlon(row: pd.Series) -> Optional[Tuple[float,float,str]]:
    if "lat" in row and "lon" in row:
        try:
            lat = float(row["lat"]); lon = float(row["lon"])
            if np.isfinite(lat) and np.isfinite(lon):
                return lat, lon, f"ll:{lat:.6f},{lon:.6f}"
        except Exception:
            pass
    if "postcode" in row and sstr(row["postcode"]):
        try:
            lat, lon, _ = get_postcode_info(sstr(row["postcode"]))
            return lat, lon, f"pc:{sstr(row['postcode']).upper().replace(' ','')}"
        except Exception:
            pass
    if "address" in row and sstr(row["address"]):
        try:
            lat, lon = geocode_address(sstr(row["address"]))
            return lat, lon, f"addr:{sstr(row['address']).lower()}"
        except Exception:
            pass
    return None

def enrich_banks_geography(banks_df: pd.DataFrame, force_refresh: bool = False) -> pd.DataFrame:
    """
    Enrich banks DataFrame with LPA/NCA data.
    Uses session state cache to avoid repeated API calls on every rerun.
    
    Args:
        banks_df: DataFrame with banks data
        force_refresh: If True, forces re-resolution of all banks' LPA/NCA even if cached
        
    Returns:
        DataFrame with enriched banks data including lpa_name and nca_name
    """
    # Check if we have a cached version and it matches the current banks data
    if not force_refresh and st.session_state.get("enriched_banks_cache") is not None:
        try:
            cached_df = st.session_state["enriched_banks_cache"]
            # Verify the cache is still valid by checking if bank_ids match
            if "bank_id" in banks_df.columns and "bank_id" in cached_df.columns:
                if set(banks_df["bank_id"]) == set(cached_df["bank_id"]):
                    # Cache is valid, return it
                    return cached_df.copy()
        except Exception as e:
            # If cache validation fails, proceed with fresh resolution
            st.sidebar.warning(f"Cache validation failed, refreshing banks: {e}")
    
    # Cache is invalid or force refresh requested, perform enrichment
    df = banks_df.copy()
    if "lpa_name" not in df.columns: df["lpa_name"] = ""
    if "nca_name" not in df.columns: df["nca_name"] = ""
    cache = st.session_state["bank_geo_cache"]
    needs = df[(df["lpa_name"].map(sstr) == "") | (df["nca_name"].map(sstr) == "")]
    prog = None
    if len(needs) > 0:
        prog = st.sidebar.progress(0.0, text="Resolving bank LPA/NCA…")
    rows, updated, total = [], 0, len(df)
    for _, row in df.iterrows():
        lpa_now = sstr(row.get("lpa_name"))
        nca_now = sstr(row.get("nca_name"))
        if lpa_now and nca_now and not force_refresh:
            rows.append(row)
        else:
            loc = bank_row_to_latlon(row)
            if not loc:
                rows.append(row)
            else:
                lat, lon, key = loc
                if key in cache and not force_refresh:
                    lpa, nca = cache[key]
                else:
                    lpa, nca = get_lpa_nca_for_point(lat, lon)
                    cache[key] = (lpa, nca)
                    time.sleep(0.15)
                if not lpa_now: row["lpa_name"] = lpa
                if not nca_now: row["nca_name"] = nca
                updated += 1
                rows.append(row)
        if prog is not None:
            done = (len(rows) / max(total, 1))
            prog.progress(done, text=f"Resolving bank LPA/NCA… ({int(done*100)}%)")
    if prog is not None:
        prog.empty()
        if updated:
            st.sidebar.success(f"Updated {updated} bank(s) with LPA/NCA")
    
    enriched_df = pd.DataFrame(rows)
    
    # Store in cache with timestamp
    try:
        st.session_state["enriched_banks_cache"] = enriched_df.copy()
        st.session_state["enriched_banks_timestamp"] = pd.Timestamp.now()
    except Exception as e:
        # If caching fails, log but don't break the app
        st.sidebar.warning(f"Failed to cache banks: {e}")
    
    return enriched_df

backend["Banks"] = enrich_banks_geography(backend["Banks"], force_refresh=False)
backend["Banks"] = make_bank_key_col(backend["Banks"], backend["Banks"])

# Validate minimal columns
for sheet, cols in {
    "Pricing": ["bank_id","habitat_name","contract_size","tier"],
    "Stock": ["bank_id","habitat_name","stock_id","quantity_available"],
    "HabitatCatalog": ["habitat_name","broader_type","distinctiveness_name"],
}.items():
    missing = [c for c in cols if c not in backend[sheet].columns]
    if missing:
        st.error(f"{sheet} is missing required columns: {missing}")
        st.stop()

# Normalise Pricing; drop Hedgerow
def normalise_pricing(pr_df: pd.DataFrame) -> pd.DataFrame:
    df = pr_df.copy()
    price_cols = [c for c in df.columns if c.strip().lower() in ("price","unit price","unit_price","unitprice")]
    if not price_cols:
        st.error("Pricing sheet must contain a 'Price' column (or 'Unit Price').")
        st.stop()
    df["price"] = pd.to_numeric(df[price_cols[0]], errors="coerce")
    df["tier"] = df["tier"].astype(str).str.strip().str.lower()
    df["contract_size"] = df["contract_size"].astype(str).str.strip().str.lower()
    df["bank_id"] = df["bank_id"].astype(str).str.strip()
    df = make_bank_key_col(df, backend["Banks"])
    if "broader_type" not in df.columns: df["broader_type"] = ""
    if "distinctiveness_name" not in df.columns: df["distinctiveness_name"] = ""
    df["habitat_name"] = df["habitat_name"].astype(str).str.strip()
    # NOTE: Do NOT filter out hedgerows here! They need to be available for hedgerow optimization
    return df

# NOTE: Do NOT filter hedgerows from backend globally - they're needed for hedgerow optimization
backend["Pricing"] = normalise_pricing(backend["Pricing"])

# Distinctiveness mapping
dist_levels_map = {
    sstr(r["distinctiveness_name"]): float(r["level_value"])
    for _, r in backend["DistinctivenessLevels"].iterrows()
}
dist_levels_map.update({k.lower(): v for k, v in list(dist_levels_map.items())})

# ================= Bank Refresh UI in Sidebar =================
with st.sidebar:
    st.markdown("---")
    st.subheader("Bank Data")
    
    # Display cache status
    if st.session_state.get("enriched_banks_timestamp"):
        timestamp = st.session_state["enriched_banks_timestamp"]
        cache_age = pd.Timestamp.now() - timestamp
        cache_age_minutes = int(cache_age.total_seconds() / 60)
        st.caption(f"✅ Banks cached ({cache_age_minutes}m ago)")
    else:
        st.caption("⚠️ Banks not yet cached")
    
    # Refresh button
    if st.button("🔄 Refresh Banks LPA/NCA", 
                 help="Manually refresh all banks' LPA/NCA data from ArcGIS APIs",
                 key="refresh_banks_btn"):
        try:
            # Force refresh the banks enrichment
            with st.spinner("Refreshing bank LPA/NCA data..."):
                backend["Banks"] = enrich_banks_geography(backend["Banks"], force_refresh=True)
                backend["Banks"] = make_bank_key_col(backend["Banks"], backend["Banks"])
                # Re-normalize pricing with updated banks
                backend["Pricing"] = normalise_pricing(backend["Pricing"])
            st.success("✅ Banks refreshed!")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Error refreshing banks: {e}")
            import traceback
            st.code(traceback.format_exc())

# Check if we need to refresh the map after optimization (after backend is loaded)
if st.session_state.get("needs_map_refresh", False):
    st.session_state["needs_map_refresh"] = False
    st.rerun()

# ================= Locate UI =================
with st.container():
    st.subheader("1) Locate target site")
    
    # LPA/NCA Dropdown Option for promoters
    st.markdown("**Option A: Select LPA/NCA directly (for promoters)**")
    col_dropdown1, col_dropdown2 = st.columns(2)
    
    # Fetch complete LPA and NCA lists from ArcGIS (cached in session state)
    if st.session_state["all_lpas_list"] is None:
        with st.spinner("Loading complete LPA list from ArcGIS..."):
            st.session_state["all_lpas_list"] = fetch_all_lpas_from_arcgis()
    
    if st.session_state["all_ncas_list"] is None:
        with st.spinner("Loading complete NCA list from ArcGIS..."):
            st.session_state["all_ncas_list"] = fetch_all_ncas_from_arcgis()
    
    all_lpas = st.session_state["all_lpas_list"] or []
    all_ncas = st.session_state["all_ncas_list"] or []
    
    # Add "Custom - Type your own" option to the lists
    lpa_options = [""] + all_lpas + ["⌨️ Custom - Type your own"]
    nca_options = [""] + all_ncas + ["⌨️ Custom - Type your own"]
    
    with col_dropdown1:
        selected_lpa = st.selectbox(
            "Select LPA",
            options=lpa_options,
            index=0,
            key="lpa_dropdown",
            help="Select Local Planning Authority from the list, or choose 'Custom' to type your own"
        )
        
        # Show custom text input if "Custom" is selected
        custom_lpa = None
        if selected_lpa == "⌨️ Custom - Type your own":
            custom_lpa = st.text_input(
                "Enter LPA name",
                key="custom_lpa_input",
                help="Type the LPA name exactly as it appears in official records"
            )
            if custom_lpa:
                st.session_state["selected_lpa_dropdown"] = custom_lpa
                st.session_state["use_lpa_nca_dropdown"] = True
        elif selected_lpa:
            st.session_state["selected_lpa_dropdown"] = selected_lpa
            st.session_state["use_lpa_nca_dropdown"] = True
    
    with col_dropdown2:
        selected_nca = st.selectbox(
            "Select NCA",
            options=nca_options,
            index=0,
            key="nca_dropdown",
            help="Select National Character Area from the list, or choose 'Custom' to type your own"
        )
        
        # Show custom text input if "Custom" is selected
        custom_nca = None
        if selected_nca == "⌨️ Custom - Type your own":
            custom_nca = st.text_input(
                "Enter NCA name",
                key="custom_nca_input",
                help="Type the NCA name exactly as it appears in official records"
            )
            if custom_nca:
                st.session_state["selected_nca_dropdown"] = custom_nca
                st.session_state["use_lpa_nca_dropdown"] = True
        elif selected_nca:
            st.session_state["selected_nca_dropdown"] = selected_nca
            st.session_state["use_lpa_nca_dropdown"] = True
    
    # Apply LPA/NCA dropdown selection
    if st.button("Apply LPA/NCA Selection", key="apply_lpa_nca_btn"):
        if st.session_state.get("selected_lpa_dropdown") or st.session_state.get("selected_nca_dropdown"):
            # Fetch geometries and neighbors from ArcGIS
            lpa_data = None
            nca_data = None
            
            if st.session_state.get("selected_lpa_dropdown"):
                lpa_name = st.session_state["selected_lpa_dropdown"]
                st.session_state["target_lpa_name"] = lpa_name
                with st.spinner(f"Fetching geometry for LPA: {lpa_name}..."):
                    lpa_data = query_lpa_by_name(lpa_name)
            
            if st.session_state.get("selected_nca_dropdown"):
                nca_name = st.session_state["selected_nca_dropdown"]
                st.session_state["target_nca_name"] = nca_name
                with st.spinner(f"Fetching geometry for NCA: {nca_name}..."):
                    nca_data = query_nca_by_name(nca_name)
            
            # Update session state with geometries and neighbors
            if lpa_data:
                st.session_state["lpa_geojson"] = lpa_data.get("geometry")
                st.session_state["lpa_neighbors"] = lpa_data.get("neighbors", [])
                st.session_state["lpa_neighbors_norm"] = lpa_data.get("neighbors_norm", [])
            else:
                st.session_state["lpa_geojson"] = None
                st.session_state["lpa_neighbors"] = []
                st.session_state["lpa_neighbors_norm"] = []
            
            if nca_data:
                st.session_state["nca_geojson"] = nca_data.get("geometry")
                st.session_state["nca_neighbors"] = nca_data.get("neighbors", [])
                st.session_state["nca_neighbors_norm"] = nca_data.get("neighbors_norm", [])
            else:
                st.session_state["nca_geojson"] = None
                st.session_state["nca_neighbors"] = []
                st.session_state["nca_neighbors_norm"] = []
            
            # Calculate centroid for map centering if we have at least one geometry
            if lpa_data and lpa_data.get("geometry_esri"):
                # Calculate centroid from LPA geometry
                rings = lpa_data["geometry_esri"].get("rings", [[]])
                if rings and rings[0]:
                    coords = rings[0]
                    avg_lon = sum(c[0] for c in coords) / len(coords)
                    avg_lat = sum(c[1] for c in coords) / len(coords)
                    st.session_state["target_lat"] = avg_lat
                    st.session_state["target_lon"] = avg_lon
            elif nca_data and nca_data.get("geometry_esri"):
                # Calculate centroid from NCA geometry
                rings = nca_data["geometry_esri"].get("rings", [[]])
                if rings and rings[0]:
                    coords = rings[0]
                    avg_lon = sum(c[0] for c in coords) / len(coords)
                    avg_lat = sum(c[1] for c in coords) / len(coords)
                    st.session_state["target_lat"] = avg_lat
                    st.session_state["target_lon"] = avg_lon
            else:
                # No geometry available, clear coordinates
                st.session_state["target_lat"] = None
                st.session_state["target_lon"] = None
            
            # Clear any previous optimization results
            if "last_alloc_df" in st.session_state:
                st.session_state["last_alloc_df"] = None
            st.session_state["optimization_complete"] = False
            
            # Increment map version to force refresh
            st.session_state["map_version"] = st.session_state.get("map_version", 0) + 1
            
            st.success(f"Selected LPA/NCA: **{st.session_state.get('target_lpa_name', '—')}** | **{st.session_state.get('target_nca_name', '—')}**")
            st.rerun()
        else:
            st.warning("Please select at least one LPA or NCA")
    
    st.markdown("---")
    st.markdown("**Option B: Enter postcode or address (standard method)**")
    
    # Use form to prevent rerun on text input changes - only rerun when Locate is clicked
    with st.form("locate_form", clear_on_submit=False):
        c1, c2, c3 = st.columns([1,1,1])
        with c1:
            postcode = st.text_input("Postcode (quicker)", key="postcode_input")
        with c2:
            address = st.text_input("Address (if no postcode)", key="address_input")
        with c3:
            # Add spacing to align button with inputs
            st.write("")  # Empty line for spacing
            run_locate = st.form_submit_button("Locate", type="primary")

def find_site(postcode: str, address: str):
    if sstr(postcode):
        lat, lon, _ = get_postcode_info(postcode)
    elif sstr(address):
        lat, lon = geocode_address(address)
    else:
        raise RuntimeError("Enter a postcode or an address.")
    lpa_feat = arcgis_point_query(LPA_URL, lat, lon, "LAD24NM")
    nca_feat = arcgis_point_query(NCA_URL, lat, lon, "NCA_Name")
    t_lpa = sstr((lpa_feat.get("attributes") or {}).get("LAD24NM"))
    t_nca = sstr((nca_feat.get("attributes") or {}).get("NCA_Name"))
    lpa_geom_esri = lpa_feat.get("geometry")
    nca_geom_esri = nca_feat.get("geometry")
    lpa_gj = esri_polygon_to_geojson(lpa_geom_esri)
    nca_gj = esri_polygon_to_geojson(nca_geom_esri)
    lpa_nei = [n for n in layer_intersect_names(LPA_URL, lpa_geom_esri, "LAD24NM") if n != t_lpa]
    nca_nei = [n for n in layer_intersect_names(NCA_URL, nca_geom_esri, "NCA_Name") if n != t_nca]
    lpa_nei_norm = [norm_name(n) for n in lpa_nei]
    nca_nei_norm = [norm_name(n) for n in nca_nei]
    
    # Get watercourse catchments for site
    waterbody, operational = get_watercourse_catchments_for_point(lat, lon)
    
    # Update session state - FIXED VERSION
    st.session_state["target_lpa_name"] = t_lpa
    st.session_state["target_nca_name"] = t_nca
    st.session_state["lpa_neighbors"] = lpa_nei
    st.session_state["nca_neighbors"] = nca_nei
    st.session_state["lpa_neighbors_norm"] = lpa_nei_norm
    st.session_state["nca_neighbors_norm"] = nca_nei_norm
    st.session_state["target_lat"] = lat
    st.session_state["target_lon"] = lon
    st.session_state["lpa_geojson"] = lpa_gj
    st.session_state["nca_geojson"] = nca_gj
    st.session_state["target_waterbody"] = waterbody
    st.session_state["target_operational_catchment"] = operational
    # Clear dropdown flag since we're using postcode/address
    st.session_state["use_lpa_nca_dropdown"] = False
    # Clear any previous optimization results when locating new site
    if "last_alloc_df" in st.session_state:
        st.session_state["last_alloc_df"] = None
    st.session_state["optimization_complete"] = False
        
    return t_lpa, t_nca

if run_locate:
    try:
        tl, tn = find_site(postcode, address)
        # Force map refresh on new location
        st.session_state["map_version"] = st.session_state.get("map_version", 0) + 1
        st.success(f"Found LPA: **{tl}** | NCA: **{tn}**")
        st.rerun()
    except Exception as e:
        st.error(f"Location error: {e}")

# Show persistent location banner
if st.session_state["target_lpa_name"] or st.session_state["target_nca_name"]:
    location_source = " (via dropdown)" if st.session_state.get("use_lpa_nca_dropdown") else " (via postcode/address)"
    st.success(
        f"LPA: **{st.session_state['target_lpa_name'] or '—'}** | "
        f"NCA: **{st.session_state['target_nca_name'] or '—'}**{location_source}"
    )

# ================= Promoter/Introducer Selection =================
st.markdown("---")
with st.container():
    st.subheader("2) Promoter/Introducer (Optional)")
    
    # Get introducers from database
    try:
        introducers_list = db.get_all_introducers() if db else []
        introducer_names = [intro['name'] for intro in introducers_list]
    except Exception as e:
        st.error(f"Error loading introducers: {e}")
        introducers_list = []
        introducer_names = []
    
    col1, col2 = st.columns([1, 2])
    with col1:
        use_promoter = st.checkbox("Use Promoter/Introducer", 
                                    value=st.session_state.get("use_promoter", False),
                                    key="use_promoter_checkbox")
        st.session_state["use_promoter"] = use_promoter
    
    with col2:
        if use_promoter:
            if not introducer_names:
                st.warning("⚠️ No introducers configured. Please add introducers in the Admin Dashboard.")
                st.session_state["selected_promoter"] = None
                st.session_state["promoter_discount_type"] = None
                st.session_state["promoter_discount_value"] = None
            else:
                selected = st.selectbox("Select Introducer",
                                       introducer_names,
                                       key="promoter_dropdown",
                                       help="Select an approved introducer to apply their discount")
                
                # Store selected promoter details in session state
                if selected:
                    selected_intro = next((intro for intro in introducers_list if intro['name'] == selected), None)
                    if selected_intro:
                        st.session_state["selected_promoter"] = selected_intro['name']
                        st.session_state["promoter_discount_type"] = selected_intro['discount_type']
                        st.session_state["promoter_discount_value"] = selected_intro['discount_value']
                        
                        # Show discount info
                        if selected_intro['discount_type'] == 'tier_up':
                            st.info(f"💡 **Tier Up Discount**: Pricing uses one contract size tier higher (e.g., fractional → small, small → medium, medium → large) for better rates")
                        elif selected_intro['discount_type'] == 'percentage':
                            st.info(f"💡 **Percentage Discount**: {selected_intro['discount_value']}% discount on all items except £500 admin fee")
                        else:  # no_discount
                            st.info(f"💡 **No Discount Applied**: Promoter registered for dynamic email text only")
        else:
            st.session_state["selected_promoter"] = None
            st.session_state["promoter_discount_type"] = None
            st.session_state["promoter_discount_value"] = None

st.markdown("---")

# ================= Map functions (CORRECTED STYLING) =================
# ================= Map functions (CORRECTED STYLING) =================
def build_base_map():
    lat = st.session_state.get("target_lat", None)
    lon = st.session_state.get("target_lon", None)
    lpa_gj = st.session_state.get("lpa_geojson", None)
    nca_gj = st.session_state.get("nca_geojson", None)
    t_lpa = st.session_state.get("target_lpa_name", "")
    t_nca = st.session_state.get("target_nca_name", "")

    if lat is None or lon is None:
        fmap = folium.Map(location=[54.5, -2.5], zoom_start=5, control_scale=True)
    else:
        fmap = folium.Map(location=[lat, lon], zoom_start=10, control_scale=True)
        
        # Target LPA - Bright Red border
        if lpa_gj:
            folium.GeoJson(
                lpa_gj,
                name=f"🎯 Target LPA: {t_lpa}" if t_lpa else "Target LPA",
                style_function=lambda x: {
                    "fillColor": "red", 
                    "color": "red",  # Bright red border
                    "weight": 3, 
                    "fillOpacity": 0.05,  # Very light fill
                    "opacity": 1.0  # Solid border
                },
                tooltip=f"Target LPA: {t_lpa}" if t_lpa else "Target LPA"
            ).add_to(fmap)
        
        # Target NCA - Bright Orange border
        if nca_gj:
            folium.GeoJson(
                nca_gj,
                name=f"🎯 Target NCA: {t_nca}" if t_nca else "Target NCA",
                style_function=lambda x: {
                    "fillColor": "orange", 
                    "color": "orange",  # Bright orange border
                    "weight": 3, 
                    "fillOpacity": 0.05,  # Very light fill
                    "opacity": 1.0  # Solid border
                },
                tooltip=f"Target NCA: {t_nca}" if t_nca else "Target NCA"
            ).add_to(fmap)
        
        # Add target site marker
        folium.CircleMarker(
            [lat, lon], 
            radius=8, 
            color="red", 
            fill=True, 
            fillColor="red",
            popup="🎯 Target Site",
            tooltip="Target Site"
        ).add_to(fmap)

    return fmap

def build_results_map(alloc_df: pd.DataFrame):
    # Start with base map (includes target LPA/NCA)
    fmap = build_base_map()
    lat0 = st.session_state.get("target_lat", None)
    lon0 = st.session_state.get("target_lon", None)

    if alloc_df.empty:
        return fmap

    # Get bank coordinates
    bank_coords: Dict[str, Tuple[float,float]] = {}
    banks_df = backend["Banks"].copy()
    for _, b in banks_df.iterrows():
        bkey = sstr(b.get("BANK_KEY") or b.get("bank_name") or b.get("bank_id"))
        loc = bank_row_to_latlon(b)
        if loc:
            bank_coords[bkey] = (loc[0], loc[1])

    # Process each selected bank
    bank_groups = alloc_df.groupby(["BANK_KEY","bank_name"], dropna=False)
    
    for idx, ((bkey, bname), g) in enumerate(bank_groups):
        try:
            # Get bank coordinates
            latlon = bank_coords.get(sstr(bkey))
            if not latlon:
                continue
                
            lat_b, lon_b = latlon
            
            # Ensure we have catchment data
            cache_key = sstr(bkey)
            if cache_key not in st.session_state["bank_catchment_geo"]:
                continue  # Skip if no catchment data

            bgeo = st.session_state["bank_catchment_geo"][cache_key]
            bank_display_name = sstr(bname) or sstr(bkey)
            
            # Add COMBINED bank boundary (LPA + NCA as one dotted green border)
            # First add the LPA
            if bgeo.get("lpa_gj"):
                folium.GeoJson(
                    bgeo["lpa_gj"],
                    name=f"🏢 {bank_display_name} - Catchment Area",
                    style_function=lambda x: {
                        "fillColor": "green", 
                        "color": "green",  # Green border
                        "weight": 2, 
                        "fillOpacity": 0.1,  # Light green fill
                        "opacity": 0.8,
                        "dashArray": "5,5"  # Dotted border
                    },
                    tooltip=f"Bank: {bank_display_name} - LPA: {sstr(bgeo.get('lpa_name', 'Unknown'))}"
                ).add_to(fmap)
            
            # Then add the NCA with same styling to create unified appearance
            if bgeo.get("nca_gj"):
                folium.GeoJson(
                    bgeo["nca_gj"],
                    name=f"🌿 {bank_display_name} - Extended Catchment",
                    style_function=lambda x: {
                        "fillColor": "green", 
                        "color": "green",  # Green border
                        "weight": 2, 
                        "fillOpacity": 0.05,  # Very light green fill for NCA
                        "opacity": 0.8,
                        "dashArray": "5,5"  # Dotted border
                    },
                    tooltip=f"Bank: {bank_display_name} - NCA: {sstr(bgeo.get('nca_name', 'Unknown'))}"
                ).add_to(fmap)

            # Create detailed popup for bank marker
            habitat_details = []
            for _, r in g.sort_values('units_supplied', ascending=False).head(6).iterrows():
                habitat_details.append(
                    f"• {sstr(r['supply_habitat'])}: {float(r['units_supplied']):.2f} units ({sstr(r['tier'])})"
                )
            
            popup_html = f"""
            <div style="font-family: Arial; font-size: 12px; width: 300px;">
                <h4 style="margin: 0 0 10px 0; color: green;">🏢 {bank_display_name}</h4>
                <p><strong>📍 LPA:</strong> {sstr(bgeo.get('lpa_name', 'Unknown'))}</p>
                <p><strong>🌿 NCA:</strong> {sstr(bgeo.get('nca_name', 'Unknown'))}</p>
                <p><strong>📊 Total Units:</strong> {g['units_supplied'].sum():.2f}</p>
                <p><strong>💰 Total Cost:</strong> £{g['cost'].sum():,.0f}</p>
                <p><strong>🌱 Habitats:</strong></p>
                <ul style="margin: 5px 0; padding-left: 15px;">
                    {''.join([f'<li>{detail}</li>' for detail in habitat_details])}
                </ul>
            </div>
            """
            
            # Add bank marker - green to match catchment
            folium.Marker(
                [lat_b, lon_b],
                icon=folium.Icon(color="green", icon="building", prefix="fa"),
                popup=folium.Popup(popup_html, max_width=350),
                tooltip=f"🏢 {bank_display_name} - Click for details"
            ).add_to(fmap)

            # Add supply route - green to match bank theme
            if lat0 is not None and lon0 is not None:
                folium.PolyLine(
                    locations=[[lat0, lon0], [lat_b, lon_b]],
                    weight=3, 
                    opacity=0.7, 
                    color="green",  # Green route line
                    dash_array="8,4",
                    tooltip=f"Supply route: Target → {bank_display_name}"
                ).add_to(fmap)

        except Exception as e:
            st.warning(f"Failed to add bank {sstr(bname) or sstr(bkey)} to map: {e}")

    # Add layer control
    folium.LayerControl(collapsed=False).add_to(fmap)
    return fmap

# ================= Map Container (FIXED VERSION) =================
with st.container():
    st.markdown("### Map")
    
    # Determine map state
    has_location = st.session_state.get("target_lat") is not None
    has_results = (isinstance(st.session_state.get("last_alloc_df"), pd.DataFrame) and 
                  not st.session_state.get("last_alloc_df").empty and 
                  st.session_state.get("optimization_complete", False))
    
    # Show status and debug if needed
    if has_results:
        num_banks = st.session_state["last_alloc_df"]["BANK_KEY"].nunique()
        banks_list = st.session_state["last_alloc_df"]["BANK_KEY"].unique().tolist()
        st.caption(f"📍 Optimization results: {num_banks} selected bank(s)")
        
        # Show catchment status
        loaded_catchments = len(st.session_state.get("bank_catchment_geo", {}))
        st.info(f"🗺️ Banks: {', '.join(banks_list)} | Catchments loaded: {loaded_catchments}")
        
    elif has_location:
        st.caption("📍 Showing target location with LPA/NCA boundaries")
    else:
        st.caption("📍 UK overview - use 'Locate' to center on your target site")
    
    # Manual refresh option (always available)
    if st.button("🔄 Refresh Map", help="Reload map with fresh data"):
        if has_results:
            # Clear and reload catchment data
            st.session_state["bank_catchment_geo"] = {}
            with st.spinner("Reloading bank catchments..."):
                alloc_df = st.session_state["last_alloc_df"]
                # Same loading logic as above
                selected_banks = alloc_df["BANK_KEY"].unique()
                bank_coords = {}
                banks_df = backend["Banks"].copy()
                for _, b in banks_df.iterrows():
                    bkey = sstr(b.get("BANK_KEY") or b.get("bank_name") or b.get("bank_id"))
                    loc = bank_row_to_latlon(b)
                    if loc:
                        bank_coords[bkey] = (loc[0], loc[1])
                
                for bkey in selected_banks:
                    if sstr(bkey) in bank_coords:
                        try:
                            lat_b, lon_b = bank_coords[sstr(bkey)]
                            b_lpa_name, b_lpa_gj, b_nca_name, b_nca_gj = get_catchment_geo_for_point(lat_b, lon_b)
                            st.session_state["bank_catchment_geo"][sstr(bkey)] = {
                                "lpa_name": b_lpa_name, "lpa_gj": b_lpa_gj,
                                "nca_name": b_nca_name, "nca_gj": b_nca_gj,
                            }
                        except Exception as e:
                            st.warning(f"Failed to load {bkey}: {e}")
        st.rerun()
    
    # Build and render map
    try:
        if has_results:
            current_map = build_results_map(st.session_state["last_alloc_df"])
        else:
            current_map = build_base_map()
        
        # Use a simple, stable key
        map_key = "bng_stable_map"
        
        # Render with folium_static for maximum stability
        if folium_static:
            folium_static(current_map, width=None, height=520)
        else:
            st_folium(current_map, height=520, use_container_width=True, key=map_key)

    except Exception as e:
        st.error(f"Map rendering failed: {e}")

# ================= Demand =================
st.subheader("2) Demand (units required)")
NET_GAIN_LABEL = "Net Gain (Low-equivalent)"
NET_GAIN_HEDGEROW_LABEL = "Net Gain (Hedgerows)"

HAB_CHOICES = sorted(
    [sstr(x) for x in backend["HabitatCatalog"]["habitat_name"].dropna().unique().tolist()] + [NET_GAIN_LABEL]
) + [NET_GAIN_HEDGEROW_LABEL, NET_GAIN_WATERCOURSE_LABEL]  # add watercourses NG

# ================= Metric File Upload =================
with st.expander("📄 Import from BNG Metric File", expanded=False):
    st.markdown("Upload a DEFRA BNG metric file (.xlsx, .xlsm, or .xlsb) to automatically populate requirements.")
    
    uploaded_metric = st.file_uploader(
        "Upload BNG Metric",
        type=["xlsx", "xlsm", "xlsb"],
        help="Select a DEFRA BNG metric file to extract habitat requirements",
        key="metric_uploader"
    )
    
    if uploaded_metric is not None:
        try:
            with st.spinner("Parsing metric file..."):
                requirements = metric_reader.parse_metric_requirements(uploaded_metric)
            
            # Show what was found
            total_area = len(requirements["area"]) if not requirements["area"].empty else 0
            total_hedge = len(requirements["hedgerows"]) if not requirements["hedgerows"].empty else 0
            total_water = len(requirements["watercourses"]) if not requirements["watercourses"].empty else 0
            
            st.success(f"✅ Metric parsed successfully! Found: {total_area} area habitats, {total_hedge} hedgerow items, {total_water} watercourse items")
            
            # Show preview
            if not requirements["area"].empty:
                with st.expander("Preview: Area Habitats", expanded=True):
                    st.dataframe(requirements["area"], use_container_width=True)
            if not requirements["hedgerows"].empty:
                with st.expander("Preview: Hedgerows", expanded=False):
                    st.dataframe(requirements["hedgerows"], use_container_width=True)
            if not requirements["watercourses"].empty:
                with st.expander("Preview: Watercourses", expanded=False):
                    st.dataframe(requirements["watercourses"], use_container_width=True)
            
            # Automatically populate demand rows
            # Check if this is a new upload (not already processed)
            uploaded_file_name = uploaded_metric.name
            if st.session_state.get("_last_imported_file") != uploaded_file_name:
                try:
                    # Clear existing demand rows and widget keys
                    if "demand_rows" in st.session_state:
                        for row in st.session_state["demand_rows"]:
                            row_id = row.get("id")
                            # Delete widget keys for old rows
                            hab_key = f"hab_{row_id}"
                            units_key = f"units_{row_id}"
                            if hab_key in st.session_state:
                                del st.session_state[hab_key]
                            if units_key in st.session_state:
                                del st.session_state[units_key]
                    
                    st.session_state.demand_rows = []
                    next_id = 1
                    
                    # Helper function for safe float conversion
                    def safe_float(value, default=0.0):
                        try:
                            return float(value)
                        except (ValueError, TypeError):
                            return default
                    
                    # First pass: collect all requirements to determine how many rows we'll need
                    all_requirements = []
                    
                    # Add area habitats
                    for _, row in requirements["area"].iterrows():
                        habitat = str(row["habitat"]).strip()
                        units = safe_float(row["units"])
                        if habitat and units > 0:
                            all_requirements.append({"habitat": habitat, "units": units})
                    
                    # Add hedgerows with Net Gain label if generic
                    for _, row in requirements["hedgerows"].iterrows():
                        habitat = str(row["habitat"]).strip()
                        units = safe_float(row["units"])
                        if habitat and units > 0:
                            # Try to match to catalog, otherwise use Net Gain (Hedgerows)
                            if habitat not in HAB_CHOICES:
                                habitat = NET_GAIN_HEDGEROW_LABEL
                            all_requirements.append({"habitat": habitat, "units": units})
                    
                    # Add watercourses
                    for _, row in requirements["watercourses"].iterrows():
                        habitat = str(row["habitat"]).strip()
                        units = safe_float(row["units"])
                        if habitat and units > 0:
                            # Try to match to catalog, otherwise use Net Gain (Watercourses)
                            if habitat not in HAB_CHOICES:
                                habitat = NET_GAIN_WATERCOURSE_LABEL
                            all_requirements.append({"habitat": habitat, "units": units})
                    
                    # Delete widget keys for all IDs we're about to use
                    for i in range(1, len(all_requirements) + 1):
                        hab_key = f"hab_{i}"
                        units_key = f"units_{i}"
                        if hab_key in st.session_state:
                            del st.session_state[hab_key]
                        if units_key in st.session_state:
                            del st.session_state[units_key]
                    
                    # Now create the rows and set widget values
                    for req in all_requirements:
                        st.session_state.demand_rows.append({
                            "id": next_id,
                            "habitat_name": req["habitat"],
                            "units": req["units"]
                        })
                        # Pre-set the widget state values to force them to populate
                        st.session_state[f"hab_{next_id}"] = req["habitat"]
                        st.session_state[f"units_{next_id}"] = req["units"]
                        next_id += 1
                    
                    st.session_state._next_row_id = next_id
                    st.session_state["_last_imported_file"] = uploaded_file_name
                    
                    # Store surplus for SUO and check if usable
                    if "surplus" in requirements and not requirements["surplus"].empty:
                        st.session_state["metric_surplus"] = requirements["surplus"].copy()
                        
                        # Check if there's usable surplus (Medium+ distinctiveness)
                        distinctiveness_order = {"Very Low": 0, "Low": 1, "Medium": 2, "High": 3, "Very High": 4}
                        eligible_surplus = requirements["surplus"][
                            requirements["surplus"]["distinctiveness"].apply(
                                lambda d: distinctiveness_order.get(str(d), 0) >= 2
                            )
                        ]
                        
                        if not eligible_surplus.empty:
                            total_eligible = eligible_surplus["units_surplus"].sum()
                            usable_surplus = total_eligible * 0.5  # 50% headroom
                            st.success(
                                f"🎯 **Surplus Uplift Offset Available!** "
                                f"{total_eligible:.2f} units of Medium+ surplus found. "
                                f"Up to {usable_surplus:.2f} units (50% headroom) can provide a cost discount after optimization."
                            )
                        else:
                            st.info(f"ℹ️ Found {len(requirements['surplus'])} surplus habitat(s), but none are Medium+ distinctiveness (no SUO discount available)")
                    else:
                        st.session_state["metric_surplus"] = None
                        st.info("ℹ️ No surplus found in metric file (no SUO discount available)")
                    
                    if st.session_state.demand_rows:
                        st.info(f"ℹ️ Automatically populated {len(st.session_state.demand_rows)} requirements in demand table below.")
                        st.rerun()
                    else:
                        st.warning("No valid requirements found to add.")
                
                except Exception as e:
                    st.error(f"❌ Error importing requirements: {e}")
        
        except Exception as e:
            st.error(f"❌ Error parsing metric file: {e}")
            st.info("Please ensure this is a valid DEFRA BNG metric file with Trading Summary sheets.")

st.markdown("---")

with st.container(border=True):
    st.markdown("**Add habitats one by one** (type to search the catalog):")
    to_delete = []
    for idx, row in enumerate(st.session_state.demand_rows):
        c1, c2, c3 = st.columns([0.62, 0.28, 0.10])
        with c1:
            # Don't autopopulate - use None as default index if habitat is empty
            default_idx = None
            if row["habitat_name"] and row["habitat_name"] in HAB_CHOICES:
                default_idx = HAB_CHOICES.index(row["habitat_name"])
            
            st.session_state.demand_rows[idx]["habitat_name"] = st.selectbox(
                "Habitat", HAB_CHOICES,
                index=default_idx,
                key=f"hab_{row['id']}",
                help="Start typing to filter",
            )
        with c2:
            st.session_state.demand_rows[idx]["units"] = st.number_input(
                "Units", min_value=0.0, step=0.01, value=float(row.get("units", 0.0)), key=f"units_{row['id']}"
            )
        with c3:
            if st.button("🗑️", key=f"del_{row['id']}", help="Remove this row"):
                to_delete.append(row["id"])
    
    if to_delete:
        st.session_state.demand_rows = [r for r in st.session_state.demand_rows if r["id"] not in to_delete]
        st.rerun()

    cc1, cc2, cc3, cc4, cc5 = st.columns([0.22, 0.22, 0.22, 0.22, 0.12])
    with cc1:
        if st.button("➕ Add habitat", key="add_hab_btn"):
            st.session_state.demand_rows.append(
                {"id": st.session_state._next_row_id, "habitat_name": "", "units": 0.0}
            )
            st.session_state._next_row_id += 1
            st.rerun()
    with cc2:
        if st.button("➕ Net Gain (Low-equivalent)", key="add_ng_btn",
                     help="Adds a 'Net Gain' line. Trades like Low distinctiveness (can source from any area habitat)."):
            st.session_state.demand_rows.append(
                {"id": st.session_state._next_row_id, "habitat_name": NET_GAIN_LABEL, "units": 0.0}
            )
            st.session_state._next_row_id += 1
            st.rerun()
    with cc3:
        if st.button("➕ Net Gain (Hedgerows)", key="add_ng_hedge_btn",
                     help="Adds a 'Net Gain (Hedgerows)' line. Can be fulfilled using any hedgerow habitat credit."):
            st.session_state.demand_rows.append(
                {"id": st.session_state._next_row_id, "habitat_name": NET_GAIN_HEDGEROW_LABEL, "units": 0.0}
            )
            st.session_state._next_row_id += 1
            st.rerun()
    with cc4:
        if st.button("➕ Net Gain (Watercourses)", key="add_ng_water_btn",
                     help="Adds a 'Net Gain (Watercourses)' line. Can be fulfilled using any watercourse habitat credit."):
            st.session_state.demand_rows.append(
                {"id": st.session_state._next_row_id, "habitat_name": NET_GAIN_WATERCOURSE_LABEL, "units": 0.0}
            )
            st.session_state._next_row_id += 1
            st.rerun()
    with cc5:
        if st.button("🧹 Clear all", key="clear_all_btn"):
            # Reset existing rows to empty state (preserves row count & IDs)
            for row in st.session_state.demand_rows:
                row["habitat_name"] = ""
                row["units"] = 0.0
            st.rerun()


total_units = sum([float(r.get("units", 0.0) or 0.0) for r in st.session_state.demand_rows])
st.metric("Total units", f"{total_units:.2f}")

demand_df = pd.DataFrame(
    [{"habitat_name": sstr(r["habitat_name"]), "units_required": float(r.get("units", 0.0) or 0.0)}
     for r in st.session_state.demand_rows if sstr(r["habitat_name"]) and float(r.get("units", 0.0) or 0.0) > 0]
)

# Display demand (hedgerow units are now supported)
if not demand_df.empty:
    st.dataframe(demand_df, use_container_width=True, hide_index=True)
    
    # Show info if hedgerow units are included
    hedgerow_units = [h for h in demand_df["habitat_name"] if is_hedgerow(h)]
    if hedgerow_units:
        st.info(f"ℹ️ Hedgerow units detected: {', '.join(sorted(set(hedgerow_units)))}. These will be optimized using hedgerow-specific trading rules.")
else:
    st.info("Add at least one habitat and units to continue.", icon="ℹ️")

# ================= Legality =================

def enforce_catalog_rules_official(demand_row, supply_row, dist_levels_map_local, explicit_rule: bool) -> bool:
    if explicit_rule:
        return True
    dh = sstr(demand_row.get("habitat_name"))
    if dh == NET_GAIN_LABEL:
        return True
    sh = sstr(supply_row.get("habitat_name"))
    d_group = sstr(demand_row.get("broader_type"))
    s_group = sstr(supply_row.get("broader_type"))
    d_dist_name = sstr(demand_row.get("distinctiveness_name"))
    s_dist_name = sstr(supply_row.get("distinctiveness_name"))
    d_key = d_dist_name.lower()
    d_val = dist_levels_map_local.get(d_dist_name, dist_levels_map_local.get(d_key, -1e9))
    s_val = dist_levels_map_local.get(s_dist_name, dist_levels_map_local.get(s_dist_name.lower(), -1e-9))

    if d_key == "low" or dh == NET_GAIN_LABEL:
        return True
    if d_key == "medium":
        same_group = (d_group and s_group and d_group == s_group)
        higher_distinctiveness = (s_val > d_val)
        return bool(same_group or higher_distinctiveness)
    return sh == dh  # High / Very High exactly like-for-like

def enforce_hedgerow_rules(demand_row, supply_row, dist_levels_map_local) -> bool:
    """
    Hedgerow trading rules:
    - Very High: Same habitat required
    - High: Like for like or better
    - Medium: Same distinctiveness or better habitat required
    - Low: Same distinctiveness or better habitat required
    - Very Low: Same distinctiveness or better habitat required
    - Net Gain: Can be covered using anything
    """
    dh = sstr(demand_row.get("habitat_name"))
    sh = sstr(supply_row.get("habitat_name"))
    d_dist_name = sstr(demand_row.get("distinctiveness_name"))
    s_dist_name = sstr(supply_row.get("distinctiveness_name"))
    d_key = d_dist_name.lower()
    d_val = dist_levels_map_local.get(d_dist_name, dist_levels_map_local.get(d_key, -1e9))
    s_val = dist_levels_map_local.get(s_dist_name, dist_levels_map_local.get(s_dist_name.lower(), -1e-9))
    
    # Net Gain (both regular and hedgerow) can be covered by anything
    if dh == NET_GAIN_LABEL or dh == "Net Gain (Hedgerows)":
        return True
    
    # Very High - Same habitat required
    if d_key in ["very high", "v.high"]:
        return sh == dh
    
    # High - Like for like or better (same habitat or higher distinctiveness)
    if d_key == "high":
        return (sh == dh) or (s_val > d_val)
    
    # Medium, Low, Very Low - Same distinctiveness or better
    if d_key in ["medium", "low", "very low", "v.low"]:
        return s_val >= d_val
    
    # Default: allow it
    return True

def enforce_watercourse_rules(demand_row, supply_row, dist_levels_map_local) -> bool:
    """
    Watercourse trading rules (mirrors hedgerow approach until you specify otherwise):
    - Very High: Same habitat required
    - High: Like for like or better (same habitat or higher distinctiveness)
    - Medium, Low, Very Low: Same distinctiveness or better
    - Net Gain (Watercourses): Anything within watercourse ledger
    """
    dh = sstr(demand_row.get("habitat_name"))
    sh = sstr(supply_row.get("habitat_name"))
    d_dist_name = sstr(demand_row.get("distinctiveness_name"))
    s_dist_name = sstr(supply_row.get("distinctiveness_name"))
    d_key = d_dist_name.lower()
    d_val = dist_levels_map_local.get(d_dist_name, dist_levels_map_local.get(d_key, -1e9))
    s_val = dist_levels_map_local.get(s_dist_name, dist_levels_map_local.get(s_dist_name.lower(), -1e-9))

    if dh == NET_GAIN_WATERCOURSE_LABEL:
        return True
    if d_key in ["very high", "v.high"]:
        return sh == dh
    if d_key == "high":
        return (sh == dh) or (s_val > d_val)
    if d_key in ["medium", "low", "very low", "v.low"]:
        return s_val >= d_val
    return True

# ================= Options builder =================
def select_size_for_demand(demand_df: pd.DataFrame, pricing_df: pd.DataFrame) -> str:
    present = pricing_df["contract_size"].drop_duplicates().tolist()
    total = float(demand_df["units_required"].sum())
    return select_contract_size(total, present)

# ================= Promoter/Introducer Discount Helpers =================
def apply_tier_up_discount(contract_size: str, available_sizes: List[str]) -> str:
    """
    Apply tier_up discount: move contract size one level up.
    fractional -> small -> medium -> large
    
    This gives better (lower) pricing by using a larger contract size's rates.
    The actual contract size remains unchanged for the quote.
    """
    size_lower = contract_size.lower()
    available_lower = [s.lower() for s in available_sizes]
    
    # Define the hierarchy from smallest to largest
    size_hierarchy = ["fractional", "small", "medium", "large"]
    
    # Find current position
    try:
        current_index = size_hierarchy.index(size_lower)
    except ValueError:
        # If size not in hierarchy, return as-is
        return contract_size
    
    # Move up one level (to next larger size)
    for next_index in range(current_index + 1, len(size_hierarchy)):
        next_size = size_hierarchy[next_index]
        if next_size in available_lower:
            return next_size
    
    # If no larger size available, return current size
    return contract_size

def apply_percentage_discount(unit_price: float, discount_percentage: float) -> float:
    """
    Apply percentage discount to unit price.
    discount_percentage is in percent (e.g., 10.0 for 10%)
    """
    return unit_price * (1.0 - discount_percentage / 100.0)

def get_active_promoter_discount():
    """
    Get active promoter discount settings from session state.
    Returns (discount_type, discount_value) or (None, None) if no promoter selected.
    """
    if not st.session_state.get("use_promoter", False):
        return None, None
    
    discount_type = st.session_state.get("promoter_discount_type")
    discount_value = st.session_state.get("promoter_discount_value")
    
    if discount_type and discount_value is not None:
        return discount_type, discount_value
    
    return None, None

def prepare_options(demand_df: pd.DataFrame,
                    chosen_size: str,
                    target_lpa: str, target_nca: str,
                    lpa_neigh: List[str], nca_neigh: List[str],
                    lpa_neigh_norm: List[str], nca_neigh_norm: List[str]) -> Tuple[List[dict], Dict[str, float], Dict[str, str]]:
    Banks = backend["Banks"].copy()
    Pricing = backend["Pricing"].copy()
    Catalog = backend["HabitatCatalog"].copy()
    Stock = backend["Stock"].copy()
    Trading = backend.get("TradingRules", pd.DataFrame())

    for df, cols in [
        (Banks, ["bank_id","bank_name","BANK_KEY","lpa_name","nca_name","lat","lon","postcode","address"]),
        (Catalog, ["habitat_name","broader_type","distinctiveness_name"]),
        (Stock, ["habitat_name","stock_id","bank_id","quantity_available","bank_name","BANK_KEY"]),
        (Pricing, ["habitat_name","contract_size","tier","bank_id","BANK_KEY","price","broader_type","distinctiveness_name","bank_name"]),
        (Trading, ["demand_habitat","allowed_supply_habitat","min_distinctiveness_name","companion_habitat"])
    ]:
        if not df.empty:
            for c in cols:
                if c in df.columns:
                    df[c] = df[c].map(sstr)

    Stock = make_bank_key_col(Stock, Banks)

    stock_full = Stock.merge(
        Banks[["bank_id","bank_name","lpa_name","nca_name"]],
        on="bank_id", how="left"
    ).merge(Catalog, on="habitat_name", how="left")
    stock_full = stock_full[~stock_full["habitat_name"].map(is_hedgerow)].copy()

    # Get active promoter discount settings
    promoter_discount_type, promoter_discount_value = get_active_promoter_discount()
    
    # Apply tier_up discount to contract size if active
    pricing_contract_size = chosen_size
    if promoter_discount_type == "tier_up":
        available_sizes = Pricing["contract_size"].drop_duplicates().tolist()
        pricing_contract_size = apply_tier_up_discount(chosen_size, available_sizes)
    
    pricing_cs = Pricing[Pricing["contract_size"] == pricing_contract_size].copy()

    pc_join = pricing_cs.merge(
        Catalog[["habitat_name","broader_type","distinctiveness_name"]],
        on="habitat_name", how="left", suffixes=("", "_cat")
    )
    pc_join["broader_type_eff"] = np.where(pc_join["broader_type"].astype(str).str.len()>0,
                                           pc_join["broader_type"], pc_join["broader_type_cat"])
    pc_join["distinctiveness_name_eff"] = np.where(pc_join["distinctiveness_name"].astype(str).str.len()>0,
                                                   pc_join["distinctiveness_name"], pc_join["distinctiveness_name_cat"])
    for c in ["broader_type_eff", "distinctiveness_name_eff", "tier", "bank_id", "habitat_name", "BANK_KEY", "bank_name"]:
        if c in pc_join.columns:
            pc_join[c] = pc_join[c].map(sstr)
    pricing_enriched = pc_join[~pc_join["habitat_name"].map(is_hedgerow)].copy()

    def dval(name: Optional[str]) -> float:
        key = sstr(name)
        return dist_levels_map.get(key, dist_levels_map.get(key.lower(), -1e9))

    def find_price_for_supply(bank_key: str,
                              supply_habitat: str,
                              tier: str,
                              demand_broader: str,
                              demand_dist: str) -> Optional[Tuple[float, str, str]]:
        # Exact row first
        pr_exact = pricing_enriched[(pricing_enriched["BANK_KEY"] == bank_key) &
                                    (pricing_enriched["tier"] == tier) &
                                    (pricing_enriched["habitat_name"] == supply_habitat)]
        if not pr_exact.empty:
            r = pr_exact.sort_values("price").iloc[0]
            return float(r["price"]), "exact", sstr(r["habitat_name"])

        d_key = sstr(demand_dist).lower()

        # Low / Net Gain — cheapest per bank/tier as proxy if exact not present
        if d_key == "low":
            grp = pricing_enriched[(pricing_enriched["BANK_KEY"] == bank_key) &
                                   (pricing_enriched["tier"] == tier)]
            if not grp.empty:
                r = grp.sort_values("price").iloc[0]
                return float(r["price"]), "any-low-proxy", sstr(r["habitat_name"])
            return None

        if d_key == "medium":
            d_num = dval(demand_dist)
            grp = pricing_enriched[(pricing_enriched["BANK_KEY"] == bank_key) &
                                   (pricing_enriched["tier"] == tier)]
            grp = grp[(grp["broader_type_eff"].astype(str).str.len() > 0) &
                      (grp["distinctiveness_name_eff"].astype(str).str.len() > 0)]
            if grp.empty:
                return None
            grp_same = grp[grp["broader_type_eff"].map(sstr) == sstr(demand_broader)].copy()
            if not grp_same.empty:
                grp_same["_dval"] = grp_same["distinctiveness_name_eff"].map(dval)
                grp_same = grp_same[grp_same["_dval"] >= d_num]
                if not grp_same.empty:
                    r = grp_same.sort_values("price").iloc[0]
                    return float(r["price"]), "group-proxy", sstr(r["habitat_name"])
            grp_any_higher = grp.assign(_dval=grp["distinctiveness_name_eff"].map(dval))
            grp_any_higher = grp_any_higher[grp_any_higher["_dval"] > d_num]
            if not grp_any_higher.empty:
                r = grp_any_higher.sort_values("price").iloc[0]
                return float(r["price"]), "group-proxy", sstr(r["habitat_name"])
            return None

        return None  # High/Very High: exact only

    def find_catalog_name(substr: str) -> Optional[str]:
        m = Catalog[Catalog["habitat_name"].str.contains(substr, case=False, na=False)]
        return sstr(m["habitat_name"].iloc[0]) if not m.empty else None

    ORCHARD_NAME = find_catalog_name("Traditional Orchard")
    SCRUB_NAME = find_catalog_name("Mixed Scrub") or find_catalog_name("scrub") or find_catalog_name("bramble")

    options: List[dict] = []
    stock_caps: Dict[str, float] = {}
    stock_bankkey: Dict[str, str] = {}
    for _, s in Stock.iterrows():
        stock_caps[sstr(s["stock_id"])] = float(s.get("quantity_available", 0) or 0.0)
        stock_bankkey[sstr(s["stock_id"])] = sstr(s.get("BANK_KEY") or s.get("bank_id"))

    for di, drow in demand_df.iterrows():
        dem_hab = sstr(drow["habitat_name"])
        
        # Skip hedgerow demand in area habitat options (hedgerows handled separately)
        if is_hedgerow(dem_hab):
            continue

        if dem_hab == NET_GAIN_LABEL:
            d_broader = ""
            d_dist = "Low"
        else:
            dcat = Catalog[Catalog["habitat_name"] == dem_hab]
            d_broader = sstr(dcat["broader_type"].iloc[0]) if not dcat.empty else ""
            d_dist = sstr(dcat["distinctiveness_name"].iloc[0]) if not dcat.empty else ""

        # Candidate stock by legality
        cand_parts = []
        explicit = False
        if "TradingRules" in backend and not backend["TradingRules"].empty and dem_hab in set(backend["TradingRules"]["demand_habitat"].astype(str)):
            explicit = True
            for _, rule in backend["TradingRules"][backend["TradingRules"]["demand_habitat"] == dem_hab].iterrows():
                sh = sstr(rule["allowed_supply_habitat"])
                if is_hedgerow(sh):
                    continue
                s_min = sstr(rule.get("min_distinctiveness_name"))
                df_s = stock_full[stock_full["habitat_name"] == sh].copy()
                if s_min:
                    df_s = df_s[df_s["distinctiveness_name"].map(lambda x: dist_levels_map.get(sstr(x), -1e9)) >=
                                dist_levels_map.get(sstr(s_min), -1e9)]
                if not df_s.empty: cand_parts.append(df_s)

        if not cand_parts:
            key = sstr(d_dist).lower()
            if key == "low" or dem_hab == NET_GAIN_LABEL:
                df_s = stock_full.copy()
            elif key == "medium":
                same_group = stock_full["broader_type"].fillna("").astype(str).map(sstr).eq(d_broader)
                higher_dist = stock_full["distinctiveness_name"].map(lambda x: dist_levels_map.get(sstr(x), -1e9)) > \
                              dist_levels_map.get(sstr(d_dist), -1e9)
                df_s = stock_full[same_group | higher_dist].copy()
            else:
                df_s = stock_full[stock_full["habitat_name"] == dem_hab].copy()
            if not df_s.empty: cand_parts.append(df_s)

        if not cand_parts:
            continue

        candidates = pd.concat(cand_parts, ignore_index=True)
        candidates = candidates[~candidates["habitat_name"].map(is_hedgerow)].copy()

        # Single-habitat options
        for _, srow in candidates.iterrows():
            if not enforce_catalog_rules_official(
                pd.Series({"habitat_name": dem_hab, "broader_type": d_broader, "distinctiveness_name": d_dist}),
                srow, dist_levels_map, explicit_rule=explicit
            ):
                continue
            tier = tier_for_bank(
                srow.get("lpa_name",""), srow.get("nca_name",""),
                target_lpa, target_nca,
                lpa_neigh, nca_neigh, lpa_neigh_norm, nca_neigh_norm
            )
            
            bank_key = sstr(srow.get("BANK_KEY") or srow.get("bank_name") or srow.get("bank_id"))
            price_info = find_price_for_supply(
                bank_key=bank_key,
                supply_habitat=srow["habitat_name"],
                tier=tier,  # Use actual geographic tier (tier_up already applied to contract size)
                demand_broader=d_broader,
                demand_dist=d_dist,
            )
            if not price_info:
                continue

            unit_price, price_source, price_hab_used = price_info
            
            # Apply percentage discount if active
            if promoter_discount_type == "percentage" and promoter_discount_value:
                unit_price = apply_percentage_discount(unit_price, promoter_discount_value)
            
            cap = float(srow.get("quantity_available", 0) or 0.0)
            if cap <= 0:
                continue
            options.append({
                "type": "normal",
                "demand_idx": di,
                "demand_habitat": dem_hab,
                "BANK_KEY": bank_key,
                "bank_name": sstr(srow.get("bank_name")),
                "bank_id": sstr(srow.get("bank_id")),
                "supply_habitat": srow["habitat_name"],
                "tier": tier,  # Keep original tier for reporting
                "proximity": tier,
                "unit_price": float(unit_price),  # Use discounted price
                "stock_use": {sstr(srow["stock_id"]): 1.0},
                "price_source": price_source,
                "price_habitat": price_hab_used,
            })

        # Paired allocations for ANY demand at ADJACENT and FAR tiers
        # When SRM > 1.0, pairing with a cheaper habitat can reduce effective cost
        banks_keys = stock_full["BANK_KEY"].dropna().unique().tolist()
        for bk in banks_keys:
            # Get stock rows for the demand habitat at this bank
            demand_rows = candidates[candidates["BANK_KEY"] == bk].copy()
            if demand_rows.empty:
                continue
            
            # Process each demand habitat stock entry (includes substitutes from trading rules)
            for _, d_stock in demand_rows.iterrows():
                cap_d = float(d_stock.get("quantity_available", 0) or 0.0)
                if cap_d <= 0:
                    continue
                
                # Get supply habitat name (may be different from demand if it's a substitute)
                supply_hab = sstr(d_stock["habitat_name"])
                
                # Get "companion" candidates: any area habitat with positive stock
                # excluding the supply habitat itself to avoid self-pairing
                companion_candidates = stock_full[
                    (stock_full["BANK_KEY"] == bk) &
                    (stock_full["habitat_name"] != supply_hab) &
                    (~stock_full["habitat_name"].map(is_hedgerow)) &
                    (stock_full["quantity_available"].astype(float) > 0)
                ].copy()
                
                if companion_candidates.empty:
                    continue
                
                # For each tier (adjacent and far), find the best companion
                for target_tier in ["adjacent", "far"]:
                    # Check if supply habitat is at this tier
                    tier_demand = tier_for_bank(
                        sstr(d_stock.get("lpa_name")), sstr(d_stock.get("nca_name")),
                        target_lpa, target_nca, lpa_neigh, nca_neigh, lpa_neigh_norm, nca_neigh_norm
                    )
                    # Only create paired options for the actual tier of the supply habitat
                    if tier_demand != target_tier:
                        continue
                    
                    # Get supply habitat price at this tier (not demand habitat - use actual supply)
                    pi_demand = find_price_for_supply(bk, supply_hab, target_tier, d_broader, d_dist)
                    if not pi_demand:
                        continue
                    price_demand = float(pi_demand[0])
                    
                    # Find companion candidates at this tier with valid prices
                    tier_companion_candidates = []
                    for _, comp_row in companion_candidates.iterrows():
                        tier_test = tier_for_bank(
                            sstr(comp_row.get("lpa_name")), sstr(comp_row.get("nca_name")),
                            target_lpa, target_nca, lpa_neigh, nca_neigh, lpa_neigh_norm, nca_neigh_norm
                        )
                        if tier_test != target_tier:
                            continue
                        
                        # Check if we can price this companion (use proxy pricing for flexibility)
                        pi_comp = find_price_for_supply(bk, comp_row["habitat_name"], target_tier, d_broader, d_dist)
                        if not pi_comp:
                            continue
                        
                        tier_companion_candidates.append({
                            "row": comp_row,
                            "price": float(pi_comp[0]),
                            "price_info": pi_comp,
                            "cap": float(comp_row.get("quantity_available", 0) or 0.0)
                        })
                    
                    if not tier_companion_candidates:
                        continue
                    
                    # Sort by price (ascending) - select the CHEAPEST companion
                    tier_companion_candidates.sort(key=lambda x: (x["price"], -x["cap"]))
                    best_companion = tier_companion_candidates[0]
                    
                    price_companion = best_companion["price"]
                    comp_row = best_companion["row"]
                    pi_comp = best_companion["price_info"]
                    
                    # Calculate blended price and stock_use based on tier
                    # SRM is already baked into pricing, so we use weighted average
                    # Adjacent: 3/4 main component + 1/4 companion
                    # Far: 1/2 main component + 1/2 companion
                    if target_tier == "adjacent":
                        srm = 4/3
                        stock_use_demand = 3/4  # Main component contributes 3/4
                        stock_use_companion = 1/4  # Companion contributes 1/4
                        blended_price = stock_use_demand * price_demand + stock_use_companion * price_companion
                    else:  # far
                        srm = 2.0
                        stock_use_demand = 1/2  # Main component contributes 1/2
                        stock_use_companion = 1/2  # Companion contributes 1/2
                        blended_price = stock_use_demand * price_demand + stock_use_companion * price_companion
                    
                    # Apply percentage discount if active (to blended price)
                    if promoter_discount_type == "percentage" and promoter_discount_value:
                        blended_price = apply_percentage_discount(blended_price, promoter_discount_value)
                    
                    # Always add paired option and let optimizer choose the best allocation
                    options.append({
                        "type": "paired",
                        "demand_idx": di,
                        "demand_habitat": dem_hab,  # Keep original demand habitat for matching
                        "BANK_KEY": bk,
                        "bank_name": sstr(d_stock.get("bank_name")),
                        "bank_id": sstr(d_stock.get("bank_id")),
                        "supply_habitat": f"{pi_demand[2]} + {pi_comp[2]}",  # Use pricing habitats
                        "tier": target_tier,
                        "proximity": target_tier,
                        "unit_price": blended_price,
                        "stock_use": {sstr(d_stock["stock_id"]): stock_use_demand, sstr(comp_row["stock_id"]): stock_use_companion},
                        "price_source": "paired",
                        "price_habitat": f"{pi_demand[2]} + {pi_comp[2]}",
                        "paired_parts": [
                            {"habitat": pi_demand[2], "unit_price": price_demand, "stock_use": stock_use_demand},
                            {"habitat": pi_comp[2], "unit_price": price_companion, "stock_use": stock_use_companion},
                        ],
                    })

    return options, stock_caps, stock_bankkey

def prepare_hedgerow_options(demand_df: pd.DataFrame,
                              chosen_size: str,
                              target_lpa: str, target_nca: str,
                              lpa_neigh: List[str], nca_neigh: List[str],
                              lpa_neigh_norm: List[str], nca_neigh_norm: List[str]) -> Tuple[List[dict], Dict[str, float], Dict[str, str]]:
    """Prepare hedgerow unit options using specific hedgerow trading rules"""
    Banks = backend["Banks"].copy()
    Pricing = backend["Pricing"].copy()
    Catalog = backend["HabitatCatalog"].copy()
    Stock = backend["Stock"].copy()
    
    for df, cols in [
        (Banks, ["bank_id","bank_name","BANK_KEY","lpa_name","nca_name"]),
        (Catalog, ["habitat_name","broader_type","distinctiveness_name"]),
        (Stock, ["habitat_name","stock_id","bank_id","quantity_available"]),
        (Pricing, ["habitat_name","contract_size","tier","bank_id","BANK_KEY","price"])
    ]:
        if not df.empty:
            for c in cols:
                if c in df.columns:
                    df[c] = df[c].map(sstr)
    
    Stock = make_bank_key_col(Stock, Banks)
    
    # Filter for ONLY hedgerow habitats
    # Ensure bank_name is available from Banks
    banks_cols = ["bank_id"]
    for col in ["bank_name", "lpa_name", "nca_name"]:
        if col in Banks.columns:
            banks_cols.append(col)
    
    stock_full = Stock.merge(
        Banks[banks_cols].drop_duplicates(),
        on="bank_id", how="left"
    ).merge(Catalog, on="habitat_name", how="left")
    
    # Ensure bank_name exists (fallback to BANK_KEY if not present)
    if "bank_name" not in stock_full.columns:
        if "BANK_KEY" in stock_full.columns:
            stock_full["bank_name"] = stock_full["BANK_KEY"]
        else:
            stock_full["bank_name"] = stock_full["bank_id"]
    
    stock_full = stock_full[stock_full["habitat_name"].map(is_hedgerow)].copy()
    
    # Get active promoter discount settings
    promoter_discount_type, promoter_discount_value = get_active_promoter_discount()
    
    # Apply tier_up discount to contract size if active
    pricing_contract_size = chosen_size
    if promoter_discount_type == "tier_up":
        available_sizes = Pricing["contract_size"].drop_duplicates().tolist()
        pricing_contract_size = apply_tier_up_discount(chosen_size, available_sizes)
    
    pricing_cs = Pricing[Pricing["contract_size"] == pricing_contract_size].copy()
    pricing_enriched = pricing_cs.merge(
        Catalog[["habitat_name","broader_type","distinctiveness_name"]],
        on="habitat_name", how="left"
    )
    pricing_enriched = pricing_enriched[pricing_enriched["habitat_name"].map(is_hedgerow)].copy()
    
    options = []
    stock_caps = {}
    stock_bankkey = {}
    
    for demand_idx, demand_row in demand_df.iterrows():
        dem_hab = sstr(demand_row.get("habitat_name"))
        
        # Skip non-hedgerow demand (but include hedgerow net gain)
        if not is_hedgerow(dem_hab):
            continue
        
        demand_units = float(demand_row.get("units_required", 0.0))
        if demand_units <= 0:
            continue
        
        # Get demand distinctiveness
        if dem_hab == "Net Gain (Hedgerows)":
            demand_dist = "Low"  # Hedgerow Net Gain trades like Low for hedgerows
            demand_broader = ""
        else:
            cat_match = Catalog[Catalog["habitat_name"] == dem_hab]
            if cat_match.empty:
                continue
            demand_dist = sstr(cat_match.iloc[0]["distinctiveness_name"])
            demand_broader = sstr(cat_match.iloc[0]["broader_type"])
        
        demand_cat_row = pd.Series({
            "habitat_name": dem_hab,
            "distinctiveness_name": demand_dist,
            "broader_type": demand_broader
        })
        
        # Find all eligible supply habitats
        for _, supply_row in stock_full.iterrows():
            supply_hab = sstr(supply_row["habitat_name"])
            
            # Check hedgerow trading rules
            if not enforce_hedgerow_rules(demand_cat_row, supply_row, dist_levels_map):
                continue
            
            bank_key = sstr(supply_row["BANK_KEY"])
            stock_id = sstr(supply_row["stock_id"])
            qty_avail = float(supply_row.get("quantity_available", 0.0))
            
            if qty_avail <= 0:
                continue
            
            tier = tier_for_bank(
                sstr(supply_row.get("lpa_name")), sstr(supply_row.get("nca_name")),
                target_lpa, target_nca,
                lpa_neigh, nca_neigh, lpa_neigh_norm, nca_neigh_norm
            )
            
            # Find price (tier_up already applied to contract size)
            pr_match = pricing_enriched[
                (pricing_enriched["BANK_KEY"] == bank_key) &
                (pricing_enriched["tier"] == tier) &
                (pricing_enriched["habitat_name"] == supply_hab)
            ]
            
            if pr_match.empty:
                # Try to find any price for this bank/tier as fallback
                pr_match = pricing_enriched[
                    (pricing_enriched["BANK_KEY"] == bank_key) &
                    (pricing_enriched["tier"] == tier)
                ]
                if pr_match.empty:
                    continue
                price = float(pr_match.iloc[0]["price"])
            else:
                price = float(pr_match.iloc[0]["price"])
            
            # Apply percentage discount if active
            if promoter_discount_type == "percentage" and promoter_discount_value:
                price = apply_percentage_discount(price, promoter_discount_value)
            
            options.append({
                "demand_idx": demand_idx,
                "demand_habitat": dem_hab,
                "supply_habitat": supply_hab,
                "bank_id": sstr(supply_row["bank_id"]),
                "bank_name": sstr(supply_row["bank_name"]),
                "BANK_KEY": bank_key,
                "stock_id": stock_id,
                "tier": tier,  # Keep original tier for reporting
                "unit_price": price,  # Use discounted price
                "cost_per_unit": price,
                "stock_use": {stock_id: 1.0},
                "type": "normal",          # <-- add this
                "proximity": tier   
            })
            
            stock_caps[stock_id] = qty_avail
            stock_bankkey[stock_id] = bank_key
    
    return options, stock_caps, stock_bankkey

# --- Watercourse options builder (ledger-scoped) ---
def prepare_watercourse_options(demand_df: pd.DataFrame,
                                chosen_size: str,
                                target_lpa: str, target_nca: str,
                                lpa_neigh: List[str], nca_neigh: List[str],
                                lpa_neigh_norm: List[str], nca_neigh_norm: List[str]
                                ) -> Tuple[List[dict], Dict[str, float], Dict[str, str]]:
    """Build candidate options for watercourse ledger using UmbrellaType='watercourse'."""
    Banks = backend["Banks"].copy()
    Pricing = backend["Pricing"].copy()
    Catalog = backend["HabitatCatalog"].copy()
    Stock = backend["Stock"].copy()

    # Normalise strings
    for df, cols in [
        (Banks,   ["bank_id","bank_name","BANK_KEY","lpa_name","nca_name"]),
        (Catalog, ["habitat_name","broader_type","distinctiveness_name","UmbrellaType"]),
        (Stock,   ["habitat_name","stock_id","bank_id","quantity_available","BANK_KEY"]),
        (Pricing, ["habitat_name","contract_size","tier","bank_id","BANK_KEY","price"])
    ]:
        if not df.empty:
            for c in cols:
                if c in df.columns:
                    df[c] = df[c].map(sstr)

    # Ensure BANK_KEY exists on Stock
    Stock = make_bank_key_col(Stock, Banks)

    # Keep only watercourse habitats by UmbrellaType
    wc_catalog = Catalog[Catalog["UmbrellaType"].astype(str).str.lower() == "watercourse"]
    wc_habs = set(wc_catalog["habitat_name"].astype(str))

    stock_full = (
        Stock[Stock["habitat_name"].isin(wc_habs)]
        .merge(Banks[["bank_id","bank_name","lpa_name","nca_name"]].drop_duplicates(),
               on="bank_id", how="left")
        .merge(Catalog[["habitat_name","broader_type","distinctiveness_name","UmbrellaType"]],
               on="habitat_name", how="left")
    )

    # Get active promoter discount settings
    promoter_discount_type, promoter_discount_value = get_active_promoter_discount()
    
    # Apply tier_up discount to contract size if active
    pricing_contract_size = chosen_size
    if promoter_discount_type == "tier_up":
        available_sizes = Pricing["contract_size"].drop_duplicates().tolist()
        pricing_contract_size = apply_tier_up_discount(chosen_size, available_sizes)

    pricing_enriched = (
        Pricing[(Pricing["contract_size"] == pricing_contract_size) & (Pricing["habitat_name"].isin(wc_habs))]
        .merge(Catalog[["habitat_name","broader_type","distinctiveness_name","UmbrellaType"]],
               on="habitat_name", how="left")
    )

    options: List[dict] = []
    stock_caps: Dict[str, float] = {}
    stock_bankkey: Dict[str, str] = {}

    for demand_idx, demand_row in demand_df.iterrows():
        dem_hab = sstr(demand_row.get("habitat_name"))

        # Only handle watercourse demands (including NG watercourses)
        # Uses UmbrellaType to decide ledger
        if "UmbrellaType" in Catalog.columns:
            if dem_hab != NET_GAIN_WATERCOURSE_LABEL:
                m = Catalog[Catalog["habitat_name"].astype(str).str.strip() == dem_hab]
                umb = sstr(m.iloc[0]["UmbrellaType"]).lower() if not m.empty else ""
                if umb != "watercourse":
                    continue
        else:
            # Fallback: text heuristic (not ideal, but keeps behavior if column is missing)
            if dem_hab != NET_GAIN_WATERCOURSE_LABEL and not is_watercourse(dem_hab):
                continue

        demand_units = float(demand_row.get("units_required", 0.0))
        if demand_units <= 0:
            continue

        if dem_hab == NET_GAIN_WATERCOURSE_LABEL:
            demand_dist = "Low"     # NG trades like Low within this ledger
            demand_broader = ""
        else:
            cat_match = Catalog[Catalog["habitat_name"] == dem_hab]
            if cat_match.empty:
                continue
            demand_dist = sstr(cat_match.iloc[0]["distinctiveness_name"])
            demand_broader = sstr(cat_match.iloc[0]["broader_type"])

        demand_cat_row = pd.Series({
            "habitat_name": dem_hab,
            "distinctiveness_name": demand_dist,
            "broader_type": demand_broader
        })

        for _, supply_row in stock_full.iterrows():
            supply_hab = sstr(supply_row["habitat_name"])
            if supply_hab not in wc_habs:
                continue

            # Ledger-specific rule check
            if not enforce_watercourse_rules(demand_cat_row, supply_row, dist_levels_map):
                continue

            bank_key = sstr(supply_row["BANK_KEY"])
            stock_id = sstr(supply_row["stock_id"])
            qty_avail = float(supply_row.get("quantity_available", 0.0))
            if qty_avail <= 0:
                continue

            # For watercourses, use catchment-based SRM instead of LPA/NCA tiering
            # Get watercourse catchments from session state
            site_waterbody = st.session_state.get("target_waterbody", "")
            site_operational = st.session_state.get("target_operational_catchment", "")
            
            bank_catchments = st.session_state.get("bank_watercourse_catchments", {}).get(bank_key, {})
            bank_waterbody = bank_catchments.get("waterbody", "")
            bank_operational = bank_catchments.get("operational_catchment", "")
            
            # Calculate SRM and map to tier for pricing
            srm = calculate_watercourse_srm(site_waterbody, site_operational,
                                           bank_waterbody, bank_operational)
            
            # Map SRM to tier for pricing lookup
            # SRM 1.0 → local, SRM 0.75 → adjacent, SRM 0.5 → far
            if srm >= 0.95:
                tier = "local"
            elif srm >= 0.70:
                tier = "adjacent"
            else:
                tier = "far"

            # Find exact price, else fallback to any watercourse price in same bank/tier
            # (tier_up already applied to contract size)
            pr_match = pricing_enriched[
                (pricing_enriched["BANK_KEY"] == bank_key) &
                (pricing_enriched["tier"] == tier) &
                (pricing_enriched["habitat_name"] == supply_hab)
            ]
            if pr_match.empty:
                pr_match = pricing_enriched[
                    (pricing_enriched["BANK_KEY"] == bank_key) &
                    (pricing_enriched["tier"] == tier)
                ]
                if pr_match.empty:
                    continue
                price = float(pr_match.iloc[0]["price"])
            else:
                price = float(pr_match.iloc[0]["price"])

            # Apply percentage discount if active
            if promoter_discount_type == "percentage" and promoter_discount_value:
                price = apply_percentage_discount(price, promoter_discount_value)

            options.append({
                "demand_idx": demand_idx,
                "demand_habitat": dem_hab,
                "supply_habitat": supply_hab,
                "bank_id": sstr(supply_row["bank_id"]),
                "bank_name": sstr(supply_row["bank_name"]),
                "BANK_KEY": bank_key,
                "stock_id": stock_id,
                "tier": tier,  # Tier based on SRM
                "srm": srm,    # Store SRM for reference
                "unit_price": price,  # Use discounted price
                "cost_per_unit": price,
                "stock_use": {stock_id: 1.0},
                "type": "normal",
                "proximity": tier,
            })

            stock_caps[stock_id] = qty_avail
            stock_bankkey[stock_id] = bank_key

    return options, stock_caps, stock_bankkey


# ================= Optimiser =================
def optimise(demand_df: pd.DataFrame,
             target_lpa: str, target_nca: str,
             lpa_neigh: List[str], nca_neigh: List[str],
             lpa_neigh_norm: List[str], nca_neigh_norm: List[str]
             ) -> Tuple[pd.DataFrame, float, str]:
    # Pick contract size from total demand (unchanged)
    chosen_size = select_size_for_demand(demand_df, backend["Pricing"])

    # ---- Build options per ledger ----
    # 1) Area (non-hedgerow, non-watercourse)
    options_area, caps_area, bk_area = prepare_options(
        demand_df, chosen_size, target_lpa, target_nca,
        lpa_neigh, nca_neigh, lpa_neigh_norm, nca_neigh_norm
    )

    # 2) Hedgerow
    options_hedge, caps_hedge, bk_hedge = prepare_hedgerow_options(
        demand_df, chosen_size, target_lpa, target_nca,
        lpa_neigh, nca_neigh, lpa_neigh_norm, nca_neigh_norm
    )

    # 3) Watercourse
    options_water, caps_water, bk_water = prepare_watercourse_options(
        demand_df, chosen_size, target_lpa, target_nca,
        lpa_neigh, nca_neigh, lpa_neigh_norm, nca_neigh_norm
    )

    # ---- Combine ledgers into one joint solve ----
    options: List[dict] = []
    options.extend(options_area)
    options.extend(options_hedge)
    options.extend(options_water)

    stock_caps: Dict[str, float] = {}
    stock_caps.update(caps_area)
    stock_caps.update(caps_hedge)
    stock_caps.update(caps_water)

    stock_bankkey: Dict[str, str] = {}
    stock_bankkey.update(bk_area)
    stock_bankkey.update(bk_hedge)
    stock_bankkey.update(bk_water)

    if not options:
        raise RuntimeError("No feasible options. Check prices/stock/rules or location tiers.")

    # ---- Map options to each demand row ----
    idx_by_dem: Dict[int, List[int]] = {}
    dem_need: Dict[int, float] = {}
    for di, drow in demand_df.iterrows():
        idx_by_dem[di] = []
        dem_need[di] = float(drow["units_required"])

    for i, opt in enumerate(options):
        idx_by_dem[opt["demand_idx"]].append(i)

    bad = [di for di, idxs in idx_by_dem.items() if len(idxs) == 0]
    if bad:
        names = [sstr(demand_df.iloc[di]["habitat_name"]) for di in bad]
        raise RuntimeError("No legal options for: " + ", ".join(names))

    bank_keys = sorted({opt["BANK_KEY"] for opt in options})

    try:
        import pulp

        def build_problem(minimise_banks: bool = False, cost_cap: Optional[float] = None):
            prob = pulp.LpProblem("BNG_MinCost_OneOptionPerDemand", pulp.LpMinimize)
            x = [pulp.LpVariable(f"x_{i}", lowBound=0) for i in range(len(options))]
            z = [pulp.LpVariable(f"z_{i}", lowBound=0, upBound=1, cat="Binary") for i in range(len(options))]
            y = {b: pulp.LpVariable(f"y_{norm_name(b)}", lowBound=0, upBound=1, cat="Binary") for b in bank_keys}

            # Calculate tie-break metrics
            bank_capacity_total: Dict[str, float] = {b: 0.0 for b in bank_keys}
            for sid, cap in stock_caps.items():
                bkey = stock_bankkey.get(sid, "")
                if bkey in bank_capacity_total:
                    bank_capacity_total[bkey] += float(cap or 0.0)

            if minimise_banks:
                obj = pulp.lpSum([y[b] for b in bank_keys])
                eps = 1e-9  # Cost tie-break
                eps2 = 1e-12  # Proximity tie-break
                eps3 = 1e-17  # Capacity tie-break (much smaller to ensure proximity always dominates)
                # Secondary tie-break: cost
                obj += eps * pulp.lpSum([options[i]["unit_price"] * x[i] for i in range(len(options))])
                # Tertiary tie-break: prefer closer banks (local > adjacent > far)
                obj += eps2 * pulp.lpSum([TIER_PROXIMITY_RANK.get(options[i].get("tier", "far"), 2) * x[i] for i in range(len(options))])
                # Final tie-break: prefer higher-capacity banks
                obj += -eps3 * pulp.lpSum([bank_capacity_total[b] * y[b] for b in bank_keys])
            else:
                # Primary: minimize cost
                obj = pulp.lpSum([options[i]["unit_price"] * x[i] for i in range(len(options))])
                eps = 1e-9  # Proximity tie-break
                eps2 = 1e-14  # Capacity tie-break (much smaller to ensure proximity always dominates)
                # Secondary tie-break: prefer closer banks (local > adjacent > far)
                obj += eps * pulp.lpSum([TIER_PROXIMITY_RANK.get(options[i].get("tier", "far"), 2) * x[i] for i in range(len(options))])
                # Tertiary tie-break: prefer higher-capacity banks
                obj += -eps2 * pulp.lpSum([bank_capacity_total[b] * y[b] for b in bank_keys])
            prob += obj

            # Hard limit: <= 2 banks
            prob += pulp.lpSum([y[b] for b in bank_keys]) <= 2

            # Link option selection to bank usage
            for i, opt in enumerate(options):
                prob += z[i] <= y[opt["BANK_KEY"]]

            # Exactly one option per demand; meet its units; bind x to z
            for di, idxs in idx_by_dem.items():
                need = dem_need[di]
                prob += pulp.lpSum([z[i] for i in idxs]) == 1
                prob += pulp.lpSum([x[i] for i in idxs]) == need
                for i in idxs:
                    prob += x[i] <= need * z[i]

            # Stock capacity constraints
            use_map: Dict[str, List[Tuple[int, float]]] = {}
            for i, opt in enumerate(options):
                for sid, coef in opt["stock_use"].items():
                    use_map.setdefault(sid, []).append((i, float(coef)))
            for sid, pairs in use_map.items():
                cap = float(stock_caps.get(sid, 0.0))
                prob += pulp.lpSum([coef * x[i] for (i, coef) in pairs]) <= cap

            # Optional cost cap (for stage B)
            if cost_cap is not None:
                prob += pulp.lpSum([options[i]["unit_price"] * x[i] for i in range(len(options))]) <= cost_cap + 1e-9

            return prob, x, z, y

        # Stage A: min cost
        probA, xA, zA, yA = build_problem(minimise_banks=False, cost_cap=None)
        probA.solve(pulp.PULP_CBC_CMD(msg=False))
        statusA = pulp.LpStatus[probA.status]
        if statusA not in ("Optimal", "Feasible"):
            raise RuntimeError("Optimiser infeasible.")
        best_cost = pulp.value(pulp.lpSum([options[i]["unit_price"] * xA[i] for i in range(len(options))])) or 0.0

        def enforce_minimum_delivery(alloc_df):
            """
            Ensure total units_supplied >= 0.01 by padding the cheapest habitat.
            If total < 0.01, add extra units to the cheapest habitat to reach 0.01 minimum.
            """
            if alloc_df.empty:
                return alloc_df, 0.0
            
            total_units = alloc_df["units_supplied"].sum()
            
            if total_units < 0.01:
                # Find the cheapest habitat (lowest unit_price)
                cheapest_idx = alloc_df["unit_price"].idxmin()
                shortage = 0.01 - total_units
                
                # Add shortage to the cheapest habitat
                alloc_df.loc[cheapest_idx, "units_supplied"] += shortage
                alloc_df.loc[cheapest_idx, "cost"] = alloc_df.loc[cheapest_idx, "units_supplied"] * alloc_df.loc[cheapest_idx, "unit_price"]
            
            # Recalculate total cost
            total_cost = float(alloc_df["cost"].sum())
            return alloc_df, total_cost

        def extract(xvars, zvars):
            rows, total_cost = [], 0.0
            for i in range(len(options)):
                qty = xvars[i].value() or 0.0
                sel = zvars[i].value() or 0.0
                if sel >= 0.5 and qty > 0:
                    opt = options[i]
                    row = {
                        "demand_habitat": opt["demand_habitat"],
                        "BANK_KEY": opt["BANK_KEY"],
                        "bank_name": opt.get("bank_name",""),
                        "bank_id": opt.get("bank_id",""),
                        "supply_habitat": opt["supply_habitat"],
                        "allocation_type": opt.get("type", "normal"),
                        "tier": opt["tier"],
                        "units_supplied": qty,
                        "unit_price": opt["unit_price"],
                        "cost": qty * opt["unit_price"],
                        "price_source": opt.get("price_source",""),
                        "price_habitat": opt.get("price_habitat",""),
                    }
                    if opt.get("type") == "paired" and "paired_parts" in opt:
                        row["paired_parts"] = json.dumps(opt["paired_parts"])
                    rows.append(row)
                    total_cost += qty * opt["unit_price"]
            
            # Apply minimum delivery enforcement
            alloc_df = pd.DataFrame(rows)
            alloc_df, total_cost = enforce_minimum_delivery(alloc_df)
            return alloc_df, float(total_cost)

        allocA, costA = extract(xA, zA)

        # Stage B: minimise #banks, but only if cost stays within numerical precision of Stage A
        # Use a very tight threshold (£10 or 0.01%, whichever is smaller) to ensure we prioritize
        # "always select cheapest" over bank minimization
        tight_threshold = min(10.0, best_cost * 0.0001)  # £10 or 0.01% of cost
        probB, xB, zB, yB = build_problem(minimise_banks=True, cost_cap=best_cost + tight_threshold)
        probB.solve(pulp.PULP_CBC_CMD(msg=False))
        statusB = pulp.LpStatus[probB.status]

        if statusB in ("Optimal", "Feasible"):
            allocB, costB = extract(xB, zB)

            def bank_count(df):
                return df["BANK_KEY"].nunique() if not df.empty else 0

            if bank_count(allocB) < bank_count(allocA):
                # Stage C: re-min cost with chosen banks fixed
                chosen_banks = list(allocB["BANK_KEY"].unique())
                probC, xC, zC, yC = build_problem(minimise_banks=False, cost_cap=None)
                for b in bank_keys:
                    if b not in chosen_banks:
                        probC += yC[b] == 0
                probC.solve(pulp.PULP_CBC_CMD(msg=False))
                statusC = pulp.LpStatus[probC.status]
                if statusC in ("Optimal", "Feasible"):
                    allocC, costC = extract(xC, zC)
                    return allocC, costC, chosen_size
                return allocB, costB, chosen_size

        return allocA, costA, chosen_size

    except Exception:
        # ---- Greedy fallback (unchanged) ----
        caps = stock_caps.copy()
        used_banks: List[str] = []

        def bank_ok(b):
            cand = set(used_banks); cand.add(b)
            return len(cand) <= 2

        rows = []
        total_cost = 0.0

        for di, drow in demand_df.iterrows():
            need = float(drow["units_required"])
            # Sort by price first, then by proximity (local > adjacent > far), then by capacity
            cand_idx = sorted(
                [i for i in range(len(options)) if options[i]["demand_idx"] == di],
                key=lambda i: (
                    options[i]["unit_price"],
                    TIER_PROXIMITY_RANK.get(options[i].get("tier", "far"), 2),
                    -sum(stock_caps.get(sid, 0.0) for sid in options[i]["stock_use"].keys())
                )
            )

            best_i = None
            best_cost = float('inf')
            for i in cand_idx:
                opt = options[i]
                bkey = opt["BANK_KEY"]
                if not bank_ok(bkey):
                    continue
                ok = True
                for sid, coef in opt["stock_use"].items():
                    req = coef * need
                    if caps.get(sid, 0.0) + 1e-9 < req:
                        ok = False
                        break
                if not ok:
                    continue
                this_cost = need * opt["unit_price"]
                if this_cost < best_cost - 1e-9:
                    best_cost = this_cost
                    best_i = i

            if best_i is None:
                name = sstr(drow["habitat_name"])
                raise RuntimeError(
                    f"Greedy fallback infeasible for '{name}' (no single option covers need within caps and bank limit)."
                )

            opt = options[best_i]
            bkey = opt["BANK_KEY"]
            for sid, coef in opt["stock_use"].items():
                caps[sid] = caps.get(sid, 0.0) - coef * need
            if bkey not in used_banks:
                used_banks.append(bkey)

            row = {
                "demand_habitat": opt["demand_habitat"],
                "BANK_KEY": opt["BANK_KEY"],
                "bank_name": opt.get("bank_name",""),
                "bank_id": opt.get("bank_id",""),
                "supply_habitat": opt["supply_habitat"],
                "allocation_type": opt.get("type", "normal"),
                "tier": opt["tier"],
                "units_supplied": need,
                "unit_price": opt["unit_price"],
                "cost": need * opt["unit_price"],
                "price_source": opt.get("price_source",""),
                "price_habitat": opt.get("price_habitat",""),
            }
            if opt.get("type") == "paired" and "paired_parts" in opt:
                row["paired_parts"] = json.dumps(opt["paired_parts"])
            rows.append(row)
            total_cost += need * opt["unit_price"]

        # Apply minimum delivery enforcement for greedy fallback
        alloc_df = pd.DataFrame(rows)
        alloc_df, total_cost = enforce_minimum_delivery(alloc_df)
        return alloc_df, float(total_cost), chosen_size

# ================= Run optimiser UI =================
st.subheader("3) Run optimiser")
left, middle, right = st.columns([1,1,1])
with left:
    run = st.button("Optimise now", type="primary", disabled=demand_df.empty, key="optimise_btn")
with middle:
    if st.button("🔄 Start New Quote", key="start_new_quote_btn", help="Clear all inputs and start fresh"):
        reset_quote()
with right:
    if st.session_state["target_lpa_name"] or st.session_state["target_nca_name"]:
        st.caption(f"LPA: {st.session_state['target_lpa_name'] or '—'} | NCA: {st.session_state['target_nca_name'] or '—'} | "
                   f"LPA neigh: {len(st.session_state['lpa_neighbors'])} | NCA neigh: {len(st.session_state['nca_neighbors'])}")
    else:
        st.caption("Tip: run 'Locate' first for precise tiers (else assumes 'far').")

# ================= Diagnostics =================
with st.expander("🔎 Diagnostics", expanded=False):
    try:
        if demand_df.empty:
            st.info("Add some demand rows above to see diagnostics.", icon="ℹ️")
        else:
            dd = demand_df.copy()
            present_sizes = backend["Pricing"]["contract_size"].drop_duplicates().tolist()
            total_units_d = float(dd["units_required"].sum())
            chosen_size_d = select_contract_size(total_units_d, present_sizes)
            st.write(f"**Chosen contract size:** `{chosen_size_d}` (present sizes: {present_sizes}, total demand: {total_units_d})")
            st.write(f"**Target LPA:** {st.session_state['target_lpa_name'] or '—'}  |  **Target NCA:** {st.session_state['target_nca_name'] or '—'}")
            st.write(f"**# LPA neighbours:** {len(st.session_state['lpa_neighbors'])}  | **# NCA neighbours:** {len(st.session_state['nca_neighbors'])}")

            s = backend["Stock"].copy()
            s["quantity_available"] = pd.to_numeric(s["quantity_available"], errors="coerce").fillna(0)
            st.write("**Stock sanity**")
            st.write(f"Non-zero stock rows: **{(s['quantity_available']>0).sum()}** | "
                     f"Total available units: **{s['quantity_available'].sum():.2f}**")

            options_preview, _, _ = prepare_options(
                dd, chosen_size_d,
                sstr(st.session_state["target_lpa_name"]), sstr(st.session_state["target_nca_name"]),
                [sstr(n) for n in st.session_state["lpa_neighbors"]], [sstr(n) for n in st.session_state["nca_neighbors"]],
                st.session_state["lpa_neighbors_norm"], st.session_state["nca_neighbors_norm"]
            )
            if not options_preview:
                st.error("No candidate options (check prices/stock/rules).")
            else:
                cand_df = pd.DataFrame(options_preview).rename(columns={"type": "allocation_type"})
                st.write("**Candidate options (by type & tier):**")
                grouped = (
                    cand_df.groupby(["demand_habitat","allocation_type","tier"], as_index=False)
                           .agg(options=("tier","count"),
                                min_price=("unit_price","min"),
                                max_price=("unit_price","max"))
                           .sort_values(["demand_habitat","allocation_type","tier"])
                )
                st.dataframe(grouped, use_container_width=True, hide_index=True)
                if "price_source" in cand_df.columns:
                    st.caption("Note: `price_source='group-proxy'` or `any-low-proxy` indicate proxy pricing rules.")

                st.markdown("**Cheapest candidates per demand (top 5 by unit price)**")
                for dem in dd["habitat_name"].unique():
                    sub = cand_df[cand_df["demand_habitat"] == dem].copy()
                    if sub.empty:
                        continue
                    sub = sub.sort_values("unit_price").head(5)
                    sub = sub[["bank_name","BANK_KEY","proximity","allocation_type","supply_habitat","unit_price","price_source","price_habitat"]]
                    st.write(f"**{dem}**")
                    st.dataframe(sub, use_container_width=True, hide_index=True)

    except Exception as de:
        st.error(f"Diagnostics error: {de}")

# ================= Price readout =================
def _build_pricing_enriched_for_size(chosen_size: str) -> pd.DataFrame:
    Pricing = backend["Pricing"].copy()
    Catalog = backend["HabitatCatalog"].copy()
    Banks   = backend["Banks"].copy()

    pr = Pricing[Pricing["contract_size"] == chosen_size].copy()
    if "bank_name" not in pr.columns and "bank_id" in pr.columns and "bank_name" in Banks.columns:
        pr = pr.merge(Banks[["bank_id","bank_name"]].drop_duplicates(), on="bank_id", how="left")

    pc_join = pr.merge(
        Catalog[["habitat_name", "broader_type", "distinctiveness_name"]],
        on="habitat_name", how="left", suffixes=("", "_cat")
    )
    pc_join["broader_type_eff"] = np.where(pc_join["broader_type"].astype(str).str.len()>0,
                                           pc_join["broader_type"], pc_join["broader_type_cat"])
    pc_join["distinctiveness_name_eff"] = np.where(pc_join["distinctiveness_name"].astype(str).str.len()>0,
                                                   pc_join["distinctiveness_name"], pc_join["distinctiveness_name_cat"])
    for c in ["broader_type_eff","distinctiveness_name_eff","tier","bank_id","habitat_name","BANK_KEY","bank_name"]:
        if c in pc_join.columns:
            pc_join[c] = pc_join[c].astype(str).str.strip()

    cols = [
        "BANK_KEY", "bank_name", "bank_id", "contract_size", "tier",
        "habitat_name", "price", "broader_type_eff", "distinctiveness_name_eff"
    ]
    for c in cols:
        if c not in pc_join.columns:
            pc_join[c] = ""
    pc_join["price"] = pd.to_numeric(pc_join["price"], errors="coerce")
    pc_join = pc_join[cols].sort_values(["BANK_KEY","tier","habitat_name","price"], kind="stable")
    return pc_join

with st.expander("🧾 Price readout (normalised view the optimiser uses)", expanded=False):
    try:
        present_sizes = backend["Pricing"]["contract_size"].drop_duplicates().tolist()
        total_units = float(demand_df["units_required"].sum()) if not demand_df.empty else 0.0
        chosen_size = select_contract_size(total_units, present_sizes)

        st.write(f"**Chosen contract size:** `{chosen_size}` (present sizes: {present_sizes})")

        prn = _build_pricing_enriched_for_size(chosen_size)

        if prn.empty:
            st.error("No pricing rows found for the chosen contract size.")
        else:
            st.markdown("**Full normalised price table (this size)**")
            st.dataframe(prn, use_container_width=True, hide_index=True)

            st.markdown("**Summary by bank & tier**")
            summ = (prn.groupby(["BANK_KEY","bank_name","tier"], as_index=False)
                        .agg(rows=("price","count"),
                             min_price=("price","min"),
                             p25=("price", lambda s: s.quantile(0.25)),
                             median=("price","median"),
                             p75=("price", lambda s: s.quantile(0.75)),
                             max_price=("price","max"))
                        .sort_values(["tier","min_price","BANK_KEY"]))
            st.dataframe(summ, use_container_width=True, hide_index=True)

            if not demand_df.empty:
                want = sorted(set(demand_df["habitat_name"]) - {NET_GAIN_LABEL})
                if want:
                    st.markdown("**Only demanded habitats (exact names)**")
                    prn_dem = prn[prn["habitat_name"].isin(want)].copy()
                    if prn_dem.empty:
                        st.warning("No exact price rows for the demanded habitat names at this size.")
                    else:
                        st.dataframe(prn_dem.sort_values(["habitat_name","tier","price"]),
                                     use_container_width=True, hide_index=True)

            # Quick scrub check
            try:
                mask_scrub = prn["habitat_name"].str.contains("scrub", case=False, na=False) | \
                             prn["habitat_name"].str.contains("bramble", case=False, na=False)
                prn_scrub = prn[mask_scrub]
                if not prn_scrub.empty:
                    st.markdown("**Scrub pricing quick check**")
                    st.dataframe(
                        prn_scrub.sort_values(["tier","price","BANK_KEY","habitat_name"]),
                        use_container_width=True, hide_index=True
                    )
            except Exception:
                pass

            csv_bytes = prn.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Download pricing (normalised, this size) CSV",
                data=csv_bytes,
                file_name=f"pricing_normalised_{chosen_size}.csv",
                mime="text/csv"
            )
    except Exception as e:
        st.error(f"Price readout error: {e}")

# ================= Pricing completeness =================
with st.expander("💷 Pricing completeness (this contract size)", expanded=False):
    try:
        if demand_df.empty:
            st.info("Add demand rows to see pricing completeness.")
        else:
            present_sizes = backend["Pricing"]["contract_size"].drop_duplicates().tolist()
            total_units_pc = float(demand_df["units_required"].sum())
            chosen_size_pc = select_contract_size(total_units_pc, present_sizes)

            pr = backend["Pricing"].copy()
            pr = pr[pr["contract_size"] == chosen_size_pc]
            needed = pd.MultiIndex.from_product(
                [
                    backend["Stock"]["bank_id"].dropna().unique(),
                    demand_df["habitat_name"].unique(),
                    ["local","adjacent","far"],
                ],
                names=["bank_id","habitat_name","tier"]
            ).to_frame(index=False)

            merged = needed.merge(
                pr[["bank_id","habitat_name","tier","price"]],
                on=["bank_id","habitat_name","tier"],
                how="left",
                indicator=True
            )

            missing = merged[merged["_merge"] == "left_only"].drop(columns=["_merge"])
            if missing.empty:
                st.success(f"All exact pricing rows exist for size `{chosen_size_pc}` across the demanded habitats.")
            else:
                st.warning("Some exact pricing rows are missing — that's fine if those rows are untradeable or Medium/Low use proxies.")
                st.dataframe(
                    missing.sort_values(["habitat_name","bank_id","tier"]),
                    use_container_width=True, hide_index=True
                )
    except Exception as e:
        st.error(f"Pricing completeness error: {e}")

# ================= SUO Helper Function =================
def compute_suo_discount(alloc_df: pd.DataFrame, backend: Dict[str, pd.DataFrame]) -> Optional[Dict]:
    """
    Compute Surplus Uplift Offset (SUO) discount after optimization.
    
    SUO provides a cost discount based on surplus habitat from the metric file.
    The discount accounts for:
    - Only Medium+ distinctiveness surplus (50% headroom)
    - SRMs of the actual banks used in the allocation
    
    Returns dict with:
        - applicable: bool - whether SUO discount can be applied
        - discount_fraction: float - percentage discount (0.0 to 1.0)
        - eligible_surplus: float - total eligible surplus units
        - usable_surplus: float - surplus after 50% headroom
        - effective_offset: float - surplus adjusted for bank SRMs
        - total_units_purchased: float - total units allocated
        - cost_saving: float - estimated cost savings
    """
    try:
        # Get surplus from metric (stored in session state when metric was uploaded)
        metric_surplus = st.session_state.get("metric_surplus")
        
        if metric_surplus is None or metric_surplus.empty:
            return {"applicable": False, "reason": "No surplus from metric file"}
        
        # Filter to Medium+ distinctiveness only
        distinctiveness_order = {"Very Low": 0, "Low": 1, "Medium": 2, "High": 3, "Very High": 4}
        eligible_surplus = metric_surplus[
            metric_surplus["distinctiveness"].apply(
                lambda d: distinctiveness_order.get(str(d), 0) >= 2
            )
        ].copy()
        
        if eligible_surplus.empty:
            return {"applicable": False, "reason": "No Medium+ distinctiveness surplus"}
        
        # Calculate total eligible surplus
        total_eligible = eligible_surplus["units_surplus"].sum()
        
        # Apply 50% headroom
        usable_surplus = total_eligible * 0.5
        
        # Calculate total units purchased (this is what we need to mitigate)
        total_units = alloc_df["units_supplied"].sum()
        
        # Calculate discount fraction: usable_surplus / total_units_to_mitigate
        # Note: We do NOT adjust for SRM here - the discount is simply based on surplus vs units needed
        discount_fraction = min(usable_surplus / total_units, 1.0) if total_units > 0 else 0.0
        
        if discount_fraction > 0:
            return {
                "applicable": True,
                "discount_fraction": discount_fraction,
                "eligible_surplus": total_eligible,
                "usable_surplus": usable_surplus,
                "total_units_purchased": total_units
            }
        else:
            return {"applicable": False, "reason": "No discount possible (insufficient surplus)"}
            
    except Exception as e:
        st.warning(f"SUO computation error: {e}")
        import traceback
        traceback.print_exc()
        return {"applicable": False, "reason": f"Error: {e}"}

# ================= Run optimiser & compute results =================
# ================= Run optimiser & compute results =================
if run:
    try:
        if demand_df.empty:
            st.error("Add at least one demand row before optimising.")
            st.stop()

        # Auto-locate if user typed address/postcode but forgot Locate
        if not st.session_state["target_lpa_name"] or not st.session_state["target_nca_name"]:
            if sstr(postcode) or sstr(address):
                try:
                    find_site(postcode, address)
                except Exception as e:
                    st.warning(f"Auto-locate failed: {e}. Proceeding with 'far' tiers only.")

        # Validate against catalog — allow special Net Gain labels
        cat_names_run = set(backend["HabitatCatalog"]["habitat_name"].astype(str))
        unknown = [h for h in demand_df["habitat_name"] if h not in cat_names_run and h not in [NET_GAIN_LABEL, NET_GAIN_HEDGEROW_LABEL, NET_GAIN_WATERCOURSE_LABEL]]
        if unknown:
            st.error(f"These demand habitats aren't in the catalog: {unknown}")
            st.stop()

        # Use session state values
        target_lpa = st.session_state["target_lpa_name"]
        target_nca = st.session_state["target_nca_name"]
        lpa_neighbors = st.session_state["lpa_neighbors"]
        nca_neighbors = st.session_state["nca_neighbors"]
        lpa_neighbors_norm = st.session_state["lpa_neighbors_norm"]
        nca_neighbors_norm = st.session_state["nca_neighbors_norm"]

        # Run optimization
        with st.spinner("Running optimization..."):
            alloc_df, total_cost, size = optimise(
                demand_df,
                target_lpa, target_nca,
                [sstr(n) for n in lpa_neighbors], [sstr(n) for n in nca_neighbors],
                lpa_neighbors_norm, nca_neighbors_norm
            )

        # IMPORTANT: Load catchment data BEFORE setting optimization_complete
        selected_banks = alloc_df["BANK_KEY"].unique()
        
        with st.spinner(f"Loading catchment areas for {len(selected_banks)} selected bank(s)..."):
            # Get bank coordinates first
            bank_coords: Dict[str, Tuple[float,float]] = {}
            banks_df = backend["Banks"].copy()
            for _, b in banks_df.iterrows():
                bkey = sstr(b.get("BANK_KEY") or b.get("bank_name") or b.get("bank_id"))
                loc = bank_row_to_latlon(b)
                if loc:
                    bank_coords[bkey] = (loc[0], loc[1])
            
            # Load catchment data for each selected bank
            catchments_loaded = []
            catchments_failed = []
            
            for bkey in selected_banks:
                cache_key = sstr(bkey)
                if sstr(bkey) in bank_coords:
                    try:
                        lat_b, lon_b = bank_coords[sstr(bkey)]
                        
                        # Always reload for fresh optimization (don't use cache)
                        b_lpa_name, b_lpa_gj, b_nca_name, b_nca_gj = get_catchment_geo_for_point(lat_b, lon_b)
                        st.session_state["bank_catchment_geo"][cache_key] = {
                            "lpa_name": b_lpa_name, "lpa_gj": b_lpa_gj,
                            "nca_name": b_nca_name, "nca_gj": b_nca_gj,
                        }
                        
                        # Also fetch watercourse catchments for this bank
                        b_waterbody, b_operational = get_watercourse_catchments_for_point(lat_b, lon_b)
                        st.session_state["bank_watercourse_catchments"][cache_key] = {
                            "waterbody": b_waterbody,
                            "operational_catchment": b_operational,
                        }
                        
                        catchments_loaded.append(cache_key)
                        
                        # Small delay to avoid overwhelming APIs
                        time.sleep(0.1)
                        
                    except Exception as e:
                        st.warning(f"Could not load catchment for bank {bkey}: {e}")
                        catchments_failed.append(bkey)
                else:
                    st.warning(f"No coordinates found for bank {bkey}")
                    catchments_failed.append(bkey)
        
        # NOW save results and set completion flag
        # Add row identifiers for removal tracking
        alloc_df_with_ids = alloc_df.copy()
        alloc_df_with_ids["_row_id"] = range(len(alloc_df_with_ids))
        st.session_state["last_alloc_df"] = alloc_df_with_ids
        st.session_state["optimization_complete"] = True
        
        # Show what we loaded
        if catchments_loaded:
            st.success(f"✅ Loaded catchment data for {len(catchments_loaded)} bank(s): {', '.join(catchments_loaded)}")
        if catchments_failed:
            st.warning(f"⚠️ Failed to load catchment data for: {', '.join(catchments_failed)}")

        # Calculate admin fee based on contract size
        admin_fee = get_admin_fee_for_contract_size(size)
        
        total_with_admin = total_cost + admin_fee
        st.success(
            f"Optimisation complete. Contract size = **{size}**. "
            f"Subtotal (units): **£{total_cost:,.0f}**  |  Admin fee: **£{admin_fee:,.0f}**  |  "
            f"Grand total: **£{total_with_admin:,.0f}**"
        )

        # ========== PROCESS RESULTS FOR PERSISTENCE (NO INLINE DISPLAY) ==========
        # Calculate summary data and save to session state - displayed in persistent section below
        
        MULT = {"local": 1.0, "adjacent": 4/3, "far": 2.0}

        def split_paired_rows(df: pd.DataFrame) -> pd.DataFrame:
            if df.empty: return df
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
                tier = sstr(r.get("tier", "")).lower()
                srm = MULT.get(tier, 1.0)

                if len(parts) == 2:
                    # For paired allocations, split units according to stock_use ratios
                    # units_total is the effective requirement
                    # Each component contributes according to its stock_use ratio
                    
                    for idx, part in enumerate(parts):
                        rr = r.to_dict()
                        rr["supply_habitat"] = sstr(part.get("habitat") or (name_parts[idx] if idx < len(name_parts) else f"Part {idx+1}"))
                        
                        # Use stock_use ratio to determine units for this component
                        stock_use = float(part.get("stock_use", 0.5))  # Default to 50/50 if not specified
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

        expanded_alloc = split_paired_rows(alloc_df.copy())
        expanded_alloc["proximity"] = expanded_alloc.get("tier", "").map(sstr)
        expanded_alloc["effective_units"] = expanded_alloc.apply(
            lambda r: float(r["units_supplied"]) * MULT.get(sstr(r["proximity"]).lower(), 1.0), axis=1
        )

        site_hab_totals = (expanded_alloc.groupby(["BANK_KEY","bank_name","supply_habitat","tier"], as_index=False)
                           .agg(units_supplied=("units_supplied","sum"),
                                effective_units=("effective_units","sum"),
                                cost=("cost","sum"))
                           .sort_values(["bank_name","supply_habitat","tier"]))

        site_hab_totals["avg_unit_price"] = site_hab_totals["cost"] / site_hab_totals["units_supplied"].replace(0, np.nan)
        site_hab_totals["avg_effective_unit_price"] = site_hab_totals["cost"] / site_hab_totals["effective_units"].replace(0, np.nan)

        site_hab_totals = site_hab_totals[[
            "BANK_KEY","bank_name","supply_habitat","tier",
            "units_supplied","effective_units","avg_unit_price","avg_effective_unit_price","cost"
        ]]

        # Calculate by bank summary
        by_bank = alloc_df.groupby(["BANK_KEY","bank_name","bank_id"], as_index=False).agg(
            units_supplied=("units_supplied","sum"),
            cost=("cost","sum")
        ).sort_values("cost", ascending=False)

        # Calculate by habitat summary
        by_hab = alloc_df.groupby("supply_habitat", as_index=False).agg(
            units_supplied=("units_supplied","sum"),
            cost=("cost","sum")
        )

        # Create order summary
        summary_df = pd.DataFrame([
            {"Item": "Subtotal (units)", "Amount £": round(total_cost, 2)},
            {"Item": "Admin fee",        "Amount £": round(admin_fee, 2)},
            {"Item": "Grand total",      "Amount £": round(total_with_admin, 2)},
        ])
        
        # Compute SUO (Surplus Uplift Offset) discount after optimization
        suo_results = compute_suo_discount(alloc_df, backend)
        if suo_results and suo_results.get("applicable", False):
            st.session_state["suo_results"] = suo_results
            st.session_state["suo_applicable"] = True
            # Initialize discount for report (defaults to enabled since checkbox defaults to True)
            st.session_state["suo_discount_for_report"] = suo_results.get("discount_fraction", 0.0)
        else:
            st.session_state["suo_results"] = None
            st.session_state["suo_applicable"] = False
            st.session_state["suo_discount_for_report"] = 0.0
        
        # Save summary data to session state for persistence
        st.session_state["site_hab_totals"] = site_hab_totals.copy()
        st.session_state["by_bank"] = by_bank.copy()
        st.session_state["by_hab"] = by_hab.copy()
        st.session_state["summary_df"] = summary_df.copy()
        st.session_state["total_cost"] = total_cost
        st.session_state["contract_size"] = size
        
        # Trigger immediate map refresh
        st.session_state["needs_map_refresh"] = True
        st.rerun()

    except Exception as e:
        st.error(f"Optimiser error: {e}")

# ================= Email Report Generation =================
# ================= Email Report Generation (EXACT TEMPLATE MATCH) =================


# ================= Fixed Email Report Generation Function =================
def generate_client_report_table_fixed(alloc_df: pd.DataFrame, demand_df: pd.DataFrame, total_cost: float, admin_fee: float, 
                                       client_name: str, ref_number: str, location: str,
                                       manual_hedgerow_rows: List[dict] = None,
                                       manual_watercourse_rows: List[dict] = None,
                                       manual_area_rows: List[dict] = None,
                                       removed_allocation_rows: List[int] = None,
                                       promoter_name: str = None,
                                       promoter_discount_type: str = None,
                                       promoter_discount_value: float = None,
                                       suo_discount_fraction: float = 0.0) -> Tuple[pd.DataFrame, str]:
    """Generate the client-facing report table and email body matching exact template with improved styling"""
    
    if manual_hedgerow_rows is None:
        manual_hedgerow_rows = []
    if manual_watercourse_rows is None:
        manual_watercourse_rows = []
    if manual_area_rows is None:
        manual_area_rows = []
    if removed_allocation_rows is None:
        removed_allocation_rows = []
    
    # Helper function to round unit price to nearest £50
    def round_to_50(price):
        return round(price / 50) * 50
    
    # Helper function to format units with up to 3 decimal places (4 sig figs)
    def format_units_dynamic(value):
        """
        Format units to show up to 3 decimal places (4 significant figures).
        - Maximum 3 decimal places
        - Remove trailing zeros after the decimal point (but keep minimum 2)
        """
        if value == 0:
            return "0.00"
        
        # Format with 3 decimals
        formatted = f"{value:.3f}"
        parts = formatted.split('.')
        if len(parts) == 2:
            integer_part = parts[0]
            decimal_part = parts[1].rstrip('0')
            # Ensure at least 2 decimal places
            if len(decimal_part) < 2:
                decimal_part = decimal_part.ljust(2, '0')
            return f"{integer_part}.{decimal_part}"
        return formatted
    
    # Helper function to format total row units (max 3 decimals, remove trailing zeros)
    def format_units_total(value):
        """
        Format total row units with up to 3 decimal places.
        - Maximum 3 decimal places
        - Remove trailing zeros (but keep at least 2 decimal places)
        """
        if value == 0:
            return "0.00"
        
        # Format with 3 decimals
        formatted = f"{value:.3f}"
        parts = formatted.split('.')
        if len(parts) == 2:
            integer_part = parts[0]
            decimal_part = parts[1].rstrip('0')
            # Ensure at least 2 decimal places
            if len(decimal_part) < 2:
                decimal_part = decimal_part.ljust(2, '0')
            return f"{integer_part}.{decimal_part}"
        return formatted
    
    # Filter out removed allocation rows
    if "_row_id" not in alloc_df.columns:
        alloc_df = alloc_df.copy()
        alloc_df["_row_id"] = range(len(alloc_df))
    alloc_df = alloc_df[~alloc_df["_row_id"].isin(removed_allocation_rows)]
    
    # Separate by habitat types
    area_habitats = []
    hedgerow_habitats = []
    watercourse_habitats = []
    
    # Process each demand
    for _, demand_row in demand_df.iterrows():
        demand_habitat = demand_row["habitat_name"]
        demand_units = demand_row["units_required"]
        
        # Find corresponding allocation(s)
        matching_allocs = alloc_df[alloc_df["demand_habitat"] == demand_habitat]
        
        if matching_allocs.empty:
            continue
            
        for _, alloc_row in matching_allocs.iterrows():
            # Determine demand distinctiveness
            if demand_habitat == NET_GAIN_LABEL:
                demand_distinctiveness = "10% Net Gain"
                demand_habitat_display = "Any"
            elif demand_habitat == "Net Gain (Hedgerows)":
                demand_distinctiveness = "10% Net Gain"
                demand_habitat_display = "Any (Hedgerows)"
            else:
                # Look up from catalog
                cat_match = backend["HabitatCatalog"][backend["HabitatCatalog"]["habitat_name"] == demand_habitat]
                if not cat_match.empty:
                    demand_distinctiveness = cat_match["distinctiveness_name"].iloc[0]
                    demand_habitat_display = demand_habitat
                else:
                    demand_distinctiveness = "Medium"  # Default
                    demand_habitat_display = demand_habitat
            
            # Supply info
            supply_habitat = alloc_row["supply_habitat"]
            supply_units = alloc_row["units_supplied"]
            unit_price = alloc_row["unit_price"]
            offset_cost = alloc_row["cost"]
            
            # Apply SUO discount to unit price and offset cost
            if suo_discount_fraction > 0:
                unit_price = unit_price * (1 - suo_discount_fraction)
                offset_cost = offset_cost * (1 - suo_discount_fraction)
            
            # Round unit price to nearest £50 for display only
            unit_price_display = round_to_50(unit_price)
            # Round offset cost to nearest pound for display
            offset_cost_display = round(offset_cost)
            
            # For paired allocations, show only the highest distinctiveness habitat
            allocation_type = sstr(alloc_row.get("allocation_type", "normal"))
            if allocation_type == "paired" and "paired_parts" in alloc_row and alloc_row["paired_parts"]:
                try:
                    paired_parts = json.loads(sstr(alloc_row["paired_parts"]))
                    if paired_parts and len(paired_parts) >= 2:
                        # Get distinctiveness for each habitat in the pair
                        habitat_distinctiveness = []
                        for idx, part in enumerate(paired_parts):
                            habitat = sstr(part.get("habitat", ""))
                            cat_match = backend["HabitatCatalog"][backend["HabitatCatalog"]["habitat_name"] == habitat]
                            if not cat_match.empty:
                                dist_name = cat_match["distinctiveness_name"].iloc[0]
                                dist_value = dist_levels_map.get(dist_name, dist_levels_map.get(dist_name.lower(), 0))
                                habitat_distinctiveness.append({
                                    "habitat": habitat,
                                    "distinctiveness_name": dist_name,
                                    "distinctiveness_value": dist_value,
                                    "index": idx  # Track original index to prefer demand habitat in ties
                                })
                        
                        # Select the habitat with highest distinctiveness value
                        # In case of tie, prefer the demand habitat (index 0)
                        if habitat_distinctiveness:
                            highest_dist = max(habitat_distinctiveness, key=lambda x: (x["distinctiveness_value"], -x["index"]))
                            supply_habitat = highest_dist["habitat"]
                            supply_distinctiveness = highest_dist["distinctiveness_name"]
                        else:
                            # Fallback to default lookup
                            supply_cat_match = backend["HabitatCatalog"][backend["HabitatCatalog"]["habitat_name"] == supply_habitat]
                            if not supply_cat_match.empty:
                                supply_distinctiveness = supply_cat_match["distinctiveness_name"].iloc[0]
                            else:
                                supply_distinctiveness = "Medium"
                    else:
                        # Fallback to default lookup
                        supply_cat_match = backend["HabitatCatalog"][backend["HabitatCatalog"]["habitat_name"] == supply_habitat]
                        if not supply_cat_match.empty:
                            supply_distinctiveness = supply_cat_match["distinctiveness_name"].iloc[0]
                        else:
                            supply_distinctiveness = "Medium"
                except Exception:
                    # If paired_parts parsing fails, fallback to default lookup
                    supply_cat_match = backend["HabitatCatalog"][backend["HabitatCatalog"]["habitat_name"] == supply_habitat]
                    if not supply_cat_match.empty:
                        supply_distinctiveness = supply_cat_match["distinctiveness_name"].iloc[0]
                    else:
                        supply_distinctiveness = "Medium"
            else:
                # Normal allocation - lookup distinctiveness
                supply_cat_match = backend["HabitatCatalog"][backend["HabitatCatalog"]["habitat_name"] == supply_habitat]
                if not supply_cat_match.empty:
                    supply_distinctiveness = supply_cat_match["distinctiveness_name"].iloc[0]
                else:
                    supply_distinctiveness = "Medium"  # Default
            
            row_data = {
                "Distinctiveness": demand_distinctiveness,
                "Habitats Lost": demand_habitat_display,
                "# Units": format_units_dynamic(demand_units),
                "Distinctiveness_Supply": supply_distinctiveness,
                "Habitats Supplied": supply_habitat,
                "# Units_Supply": format_units_dynamic(supply_units),
                "Price Per Unit": f"£{unit_price_display:,.0f}",
                "Offset Cost": f"£{offset_cost_display:,.0f}"
            }
            
            # Categorize by habitat type
            if demand_habitat == "Net Gain (Hedgerows)" or "hedgerow" in demand_habitat.lower() or "hedgerow" in supply_habitat.lower():
                hedgerow_habitats.append(row_data)
            elif "watercourse" in demand_habitat.lower() or "water" in supply_habitat.lower():
                watercourse_habitats.append(row_data)
            else:
                area_habitats.append(row_data)
    
    # Process manual hedgerow entries
    manual_hedgerow_cost = 0.0
    for row in manual_hedgerow_rows:
        habitat_lost = sstr(row.get("habitat_lost", ""))
        habitat_name = sstr(row.get("habitat_name", ""))
        units = float(row.get("units", 0.0) or 0.0)
        price_per_unit = float(row.get("price_per_unit", 0.0) or 0.0)
        
        if habitat_name and units > 0:
            # Use price_per_unit from upstream, round for display only
            price_per_unit_display = round_to_50(price_per_unit)
            # Calculate offset cost using actual price, round to nearest pound for display
            offset_cost = units * price_per_unit
            offset_cost_display = round(offset_cost)
            manual_hedgerow_cost += offset_cost
            
            # Determine distinctiveness for lost habitat
            if habitat_lost == NET_GAIN_LABEL:
                demand_distinctiveness = "10% Net Gain"
                demand_habitat_display = "Any"
            elif habitat_lost == "Net Gain (Hedgerows)":
                demand_distinctiveness = "10% Net Gain"
                demand_habitat_display = "Any (Hedgerows)"
            else:
                cat_match = backend["HabitatCatalog"][backend["HabitatCatalog"]["habitat_name"] == habitat_lost]
                if not cat_match.empty:
                    demand_distinctiveness = cat_match["distinctiveness_name"].iloc[0]
                    demand_habitat_display = habitat_lost
                else:
                    demand_distinctiveness = "Medium"
                    demand_habitat_display = habitat_lost if habitat_lost else "Not specified"
            
            # Determine distinctiveness for supplied habitat
            if habitat_name == NET_GAIN_LABEL:
                supply_distinctiveness = "10% Net Gain"
                supply_habitat_display = "Any"
            elif habitat_name == "Net Gain (Hedgerows)":
                supply_distinctiveness = "10% Net Gain"
                supply_habitat_display = "Any (Hedgerows)"
            else:
                cat_match = backend["HabitatCatalog"][backend["HabitatCatalog"]["habitat_name"] == habitat_name]
                if not cat_match.empty:
                    supply_distinctiveness = cat_match["distinctiveness_name"].iloc[0]
                    supply_habitat_display = habitat_name
                else:
                    supply_distinctiveness = "Medium"
                    supply_habitat_display = habitat_name
            
            row_data = {
                "Distinctiveness": demand_distinctiveness,
                "Habitats Lost": demand_habitat_display,
                "# Units": format_units_dynamic(units),
                "Distinctiveness_Supply": supply_distinctiveness,
                "Habitats Supplied": supply_habitat_display,
                "# Units_Supply": format_units_dynamic(units),
                "Price Per Unit": f"£{price_per_unit_display:,.0f}",
                "Offset Cost": f"£{offset_cost_display:,.0f}"
            }
            hedgerow_habitats.append(row_data)
    
    # Process manual watercourse entries
    manual_watercourse_cost = 0.0
    for row in manual_watercourse_rows:
        habitat_lost = sstr(row.get("habitat_lost", ""))
        habitat_name = sstr(row.get("habitat_name", ""))
        units = float(row.get("units", 0.0) or 0.0)
        price_per_unit = float(row.get("price_per_unit", 0.0) or 0.0)
        
        if habitat_name and units > 0:
            # Use price_per_unit from upstream, round for display only
            price_per_unit_display = round_to_50(price_per_unit)
            # Calculate offset cost using actual price, round to nearest pound for display
            offset_cost = units * price_per_unit
            offset_cost_display = round(offset_cost)
            manual_watercourse_cost += offset_cost
            
            # Determine distinctiveness for lost habitat
            if habitat_lost == NET_GAIN_LABEL:
                demand_distinctiveness = "10% Net Gain"
                demand_habitat_display = "Any"
            elif habitat_lost == "Net Gain (Hedgerows)":
                demand_distinctiveness = "10% Net Gain"
                demand_habitat_display = "Any (Hedgerows)"
            else:
                cat_match = backend["HabitatCatalog"][backend["HabitatCatalog"]["habitat_name"] == habitat_lost]
                if not cat_match.empty:
                    demand_distinctiveness = cat_match["distinctiveness_name"].iloc[0]
                    demand_habitat_display = habitat_lost
                else:
                    demand_distinctiveness = "Medium"
                    demand_habitat_display = habitat_lost if habitat_lost else "Not specified"
            
            # Determine distinctiveness for supplied habitat
            if habitat_name == NET_GAIN_LABEL:
                supply_distinctiveness = "10% Net Gain"
                supply_habitat_display = "Any"
            elif habitat_name == "Net Gain (Hedgerows)":
                supply_distinctiveness = "10% Net Gain"
                supply_habitat_display = "Any (Hedgerows)"
            else:
                cat_match = backend["HabitatCatalog"][backend["HabitatCatalog"]["habitat_name"] == habitat_name]
                if not cat_match.empty:
                    supply_distinctiveness = cat_match["distinctiveness_name"].iloc[0]
                    supply_habitat_display = habitat_name
                else:
                    supply_distinctiveness = "Medium"
                    supply_habitat_display = habitat_name
            
            row_data = {
                "Distinctiveness": demand_distinctiveness,
                "Habitats Lost": demand_habitat_display,
                "# Units": format_units_dynamic(units),
                "Distinctiveness_Supply": supply_distinctiveness,
                "Habitats Supplied": supply_habitat_display,
                "# Units_Supply": format_units_dynamic(units),
                "Price Per Unit": f"£{price_per_unit_display:,.0f}",
                "Offset Cost": f"£{offset_cost_display:,.0f}"
            }
            watercourse_habitats.append(row_data)
    
    # Process manual area habitat entries
    manual_area_cost = 0.0
    for row in manual_area_rows:
        habitat_lost = sstr(row.get("habitat_lost", ""))
        units = float(row.get("units", 0.0) or 0.0)
        is_paired = bool(row.get("paired", False))
        
        if units > 0:
            if is_paired:
                # Paired entry - process both habitats separately
                demand_habitat = sstr(row.get("demand_habitat", ""))
                companion_habitat = sstr(row.get("companion_habitat", ""))
                demand_bank = sstr(row.get("demand_bank", ""))
                companion_bank = sstr(row.get("companion_bank", ""))
                demand_price = float(row.get("demand_price", 0.0) or 0.0)
                companion_price = float(row.get("companion_price", 0.0) or 0.0)
                demand_stock = float(row.get("demand_stock_use", 0.5))
                companion_stock = 1.0 - demand_stock
                srm_tier = sstr(row.get("srm_tier", "adjacent"))
                
                # Calculate units for each habitat
                demand_units = units * demand_stock
                companion_units = units * companion_stock
                
                # Use prices from upstream, round for display only
                demand_price_display = round_to_50(demand_price)
                companion_price_display = round_to_50(companion_price)
                
                # Calculate costs using actual prices, round to nearest pound for display
                demand_cost = demand_units * demand_price
                companion_cost = companion_units * companion_price
                demand_cost_display = round(demand_cost)
                companion_cost_display = round(companion_cost)
                total_paired_cost = demand_cost + companion_cost
                manual_area_cost += total_paired_cost
                
                # Determine distinctiveness for lost habitat
                if habitat_lost == NET_GAIN_LABEL:
                    demand_distinctiveness = "10% Net Gain"
                    demand_habitat_display = "Any"
                else:
                    cat_match = backend["HabitatCatalog"][backend["HabitatCatalog"]["habitat_name"] == habitat_lost]
                    if not cat_match.empty:
                        demand_distinctiveness = cat_match["distinctiveness_name"].iloc[0]
                        demand_habitat_display = habitat_lost
                    else:
                        demand_distinctiveness = "Medium"
                        demand_habitat_display = habitat_lost if habitat_lost else "Not specified"
                
                # Get spatial risk information
                spatial_risk_offset_by = sstr(row.get("spatial_risk_offset_by", "None"))
                spatial_risk_srm = sstr(row.get("spatial_risk_srm", ""))
                
                # Add entry for demand habitat
                if demand_habitat:
                    demand_cat_match = backend["HabitatCatalog"][backend["HabitatCatalog"]["habitat_name"] == demand_habitat]
                    if not demand_cat_match.empty:
                        demand_supply_dist = demand_cat_match["distinctiveness_name"].iloc[0]
                    else:
                        demand_supply_dist = "Medium"
                    
                    # Build habitat display with spatial risk indicator
                    demand_display = f"{demand_habitat} (Paired - {srm_tier}) from {demand_bank}"
                    if spatial_risk_offset_by == "Demand Habitat":
                        demand_display += f" [Offsets Spatial Risk: {spatial_risk_srm}]"
                    
                    row_data = {
                        "Distinctiveness": demand_distinctiveness,
                        "Habitats Lost": demand_habitat_display,
                        "# Units": format_units_dynamic(units),
                        "Distinctiveness_Supply": demand_supply_dist,
                        "Habitats Supplied": demand_display,
                        "# Units_Supply": format_units_dynamic(demand_units),
                        "Price Per Unit": f"£{demand_price_display:,.0f}",
                        "Offset Cost": f"£{demand_cost_display:,.0f}"
                    }
                    area_habitats.append(row_data)
                
                # Add entry for companion habitat
                if companion_habitat:
                    companion_cat_match = backend["HabitatCatalog"][backend["HabitatCatalog"]["habitat_name"] == companion_habitat]
                    if not companion_cat_match.empty:
                        companion_supply_dist = companion_cat_match["distinctiveness_name"].iloc[0]
                    else:
                        companion_supply_dist = "Medium"
                    
                    # Build habitat display with spatial risk indicator
                    companion_display = f"{companion_habitat} (Paired - companion) from {companion_bank}"
                    if spatial_risk_offset_by == "Companion Habitat":
                        companion_display += f" [Offsets Spatial Risk: {spatial_risk_srm}]"
                    
                    row_data = {
                        "Distinctiveness": demand_distinctiveness,
                        "Habitats Lost": demand_habitat_display,
                        "# Units": format_units_dynamic(units),
                        "Distinctiveness_Supply": companion_supply_dist,
                        "Habitats Supplied": companion_display,
                        "# Units_Supply": format_units_dynamic(companion_units),
                        "Price Per Unit": f"£{companion_price_display:,.0f}",
                        "Offset Cost": f"£{companion_cost_display:,.0f}"
                    }
                    area_habitats.append(row_data)
                    
            else:
                # Simple non-paired entry (original logic)
                habitat_name = sstr(row.get("habitat_name", ""))
                price_per_unit = float(row.get("price_per_unit", 0.0) or 0.0)
                
                if habitat_name:
                    # Use price_per_unit from upstream, round for display only
                    price_per_unit_display = round_to_50(price_per_unit)
                    # Calculate offset cost using actual price, round to nearest pound for display
                    offset_cost = units * price_per_unit
                    offset_cost_display = round(offset_cost)
                    manual_area_cost += offset_cost
                    
                    # Determine distinctiveness for lost habitat
                    if habitat_lost == NET_GAIN_LABEL:
                        demand_distinctiveness = "10% Net Gain"
                        demand_habitat_display = "Any"
                    else:
                        cat_match = backend["HabitatCatalog"][backend["HabitatCatalog"]["habitat_name"] == habitat_lost]
                        if not cat_match.empty:
                            demand_distinctiveness = cat_match["distinctiveness_name"].iloc[0]
                            demand_habitat_display = habitat_lost
                        else:
                            demand_distinctiveness = "Medium"
                            demand_habitat_display = habitat_lost if habitat_lost else "Not specified"
                    
                    # Determine distinctiveness for supplied habitat
                    if habitat_name == NET_GAIN_LABEL:
                        supply_distinctiveness = "10% Net Gain"
                        supply_habitat_display = "Any"
                    else:
                        cat_match = backend["HabitatCatalog"][backend["HabitatCatalog"]["habitat_name"] == habitat_name]
                        if not cat_match.empty:
                            supply_distinctiveness = cat_match["distinctiveness_name"].iloc[0]
                            supply_habitat_display = habitat_name
                        else:
                            supply_distinctiveness = "Medium"
                            supply_habitat_display = habitat_name
                    
                    row_data = {
                        "Distinctiveness": demand_distinctiveness,
                        "Habitats Lost": demand_habitat_display,
                        "# Units": format_units_dynamic(units),
                        "Distinctiveness_Supply": supply_distinctiveness,
                        "Habitats Supplied": supply_habitat_display,
                        "# Units_Supply": format_units_dynamic(units),
                        "Price Per Unit": f"£{price_per_unit_display:,.0f}",
                        "Offset Cost": f"£{offset_cost_display:,.0f}"
                    }
                    area_habitats.append(row_data)
    
    # Calculate total cost from actual line items (which have SUO discount already applied)
    # Sum up all offset costs from the line items
    optimizer_cost = 0.0
    for habitat_list in [area_habitats, hedgerow_habitats, watercourse_habitats]:
        for row in habitat_list:
            cost_str = row["Offset Cost"].replace("£", "").replace(",", "")
            optimizer_cost += float(cost_str)
    
    # Add manual entries
    total_cost_with_manual = optimizer_cost + manual_hedgerow_cost + manual_watercourse_cost + manual_area_cost
    total_with_admin = total_cost_with_manual + admin_fee
    
    # Bundle Low + 10% Net Gain rows together for each habitat type
    def bundle_low_and_net_gain(habitats_list):
        """Bundle Low distinctiveness and 10% Net Gain rows together"""
        bundled = []
        low_rows = {}
        net_gain_rows = {}
        other_rows = []
        
        # Separate rows by distinctiveness
        for row in habitats_list:
            dist = row["Distinctiveness"]
            supply_dist = row["Distinctiveness_Supply"]
            
            # Check if this is a Low or Net Gain row
            if dist == "Low" or dist == "10% Net Gain":
                # Group by supply habitat for bundling
                supply_hab = row["Habitats Supplied"]
                if dist == "Low":
                    if supply_hab not in low_rows:
                        low_rows[supply_hab] = []
                    low_rows[supply_hab].append(row)
                else:  # 10% Net Gain
                    if supply_hab not in net_gain_rows:
                        net_gain_rows[supply_hab] = []
                    net_gain_rows[supply_hab].append(row)
            else:
                other_rows.append(row)
        
        # Bundle Low + Net Gain rows for same supply habitat
        all_supply_habitats = set(list(low_rows.keys()) + list(net_gain_rows.keys()))
        for supply_hab in sorted(all_supply_habitats):
            low_list = low_rows.get(supply_hab, [])
            ng_list = net_gain_rows.get(supply_hab, [])
            
            if low_list and ng_list:
                # Bundle them together
                total_units = sum(float(r["# Units"].replace(",", "")) for r in low_list + ng_list)
                total_supply_units = sum(float(r["# Units_Supply"].replace(",", "")) for r in low_list + ng_list)
                total_cost = sum(float(r["Offset Cost"].replace("£", "").replace(",", "")) for r in low_list + ng_list)
                
                # Use weighted average for price per unit
                avg_price = total_cost / total_supply_units if total_supply_units > 0 else 0
                
                bundled_row = {
                    "Distinctiveness": "Low + 10% Net Gain",
                    "Habitats Lost": low_list[0]["Habitats Lost"] if low_list else ng_list[0]["Habitats Lost"],
                    "# Units": format_units_dynamic(total_units),
                    "Distinctiveness_Supply": low_list[0]["Distinctiveness_Supply"] if low_list else ng_list[0]["Distinctiveness_Supply"],
                    "Habitats Supplied": supply_hab,
                    "# Units_Supply": format_units_dynamic(total_supply_units),
                    "Price Per Unit": f"£{round_to_50(avg_price):,.0f}",
                    "Offset Cost": f"£{round(total_cost):,.0f}"
                }
                bundled.append(bundled_row)
            elif low_list:
                # Only Low rows, add them as is
                bundled.extend(low_list)
            elif ng_list:
                # Only Net Gain rows, add them as is
                bundled.extend(ng_list)
        
        # Add other rows
        bundled.extend(other_rows)
        return bundled
    
    # Apply bundling to each habitat type
    area_habitats = bundle_low_and_net_gain(area_habitats)
    hedgerow_habitats = bundle_low_and_net_gain(hedgerow_habitats)
    watercourse_habitats = bundle_low_and_net_gain(watercourse_habitats)
    
    # Sort habitats by distinctiveness priority (High > Medium > Low + Net Gain > Very Low)
    def sort_by_distinctiveness(habitats_list):
        """Sort habitat rows by distinctiveness priority"""
        distinctiveness_order = {
            "Very High": 0,
            "V.High": 0,
            "High": 1,
            "Medium": 2,
            "Low + 10% Net Gain": 3,
            "Low": 4,
            "10% Net Gain": 5,
            "Very Low": 6,
            "V.Low": 6
        }
        
        def get_sort_key(row):
            dist = row.get("Distinctiveness", "")
            return distinctiveness_order.get(dist, 99)  # Unknown distinctiveness goes to end
        
        return sorted(habitats_list, key=get_sort_key)
    
    # Apply sorting to each habitat type
    area_habitats = sort_by_distinctiveness(area_habitats)
    hedgerow_habitats = sort_by_distinctiveness(hedgerow_habitats)
    watercourse_habitats = sort_by_distinctiveness(watercourse_habitats)
    
    # Build HTML table with improved styling (30% narrower, better colors)
    html_table = """
    <table border="1" style="border-collapse: collapse; width: 70%; margin: 0 auto; font-family: Arial, sans-serif; font-size: 11px;">
        <thead>
            <tr>
                <th colspan="3" style="text-align: center; padding: 8px; border: 1px solid #000; font-weight: bold; background-color: #F8C237; color: #000;">Development Impact</th>
                <th colspan="5" style="text-align: center; padding: 8px; border: 1px solid #000; font-weight: bold; background-color: #2A514A; color: #FFFFFF;">Mitigation Supplied from Wild Capital</th>
            </tr>
            <tr>
                <th style="padding: 6px; border: 1px solid #000; font-weight: bold; background-color: #F8C237; color: #000;">Distinctiveness</th>
                <th style="padding: 6px; border: 1px solid #000; font-weight: bold; background-color: #F8C237; color: #000;">Habitats Lost</th>
                <th style="padding: 6px; border: 1px solid #000; font-weight: bold; background-color: #F8C237; color: #000;"># Units</th>
                <th style="padding: 6px; border: 1px solid #000; font-weight: bold; background-color: #2A514A; color: #FFFFFF;">Distinctiveness</th>
                <th style="padding: 6px; border: 1px solid #000; font-weight: bold; background-color: #2A514A; color: #FFFFFF;">Habitats Supplied</th>
                <th style="padding: 6px; border: 1px solid #000; font-weight: bold; background-color: #2A514A; color: #FFFFFF;"># Units</th>
                <th style="padding: 6px; border: 1px solid #000; font-weight: bold; background-color: #2A514A; color: #FFFFFF;">Price Per Unit</th>
                <th style="padding: 6px; border: 1px solid #000; font-weight: bold; background-color: #2A514A; color: #FFFFFF;">Offset Cost</th>
            </tr>
        </thead>
        <tbody>
    """
    
    # Add Area Habitats section with light green background
    if area_habitats:
        html_table += """
            <tr style="background-color: #D9F2D0;">
                <td colspan="8" style="padding: 6px; border: 1px solid #000; font-weight: bold; color: #000;">Area Habitats</td>
            </tr>
        """
        for habitat in area_habitats:
            html_table += f"""
            <tr>
                <td style="padding: 6px; border: 1px solid #000;">{habitat["Distinctiveness"]}</td>
                <td style="padding: 6px; border: 1px solid #000;">{habitat["Habitats Lost"]}</td>
                <td style="padding: 6px; border: 1px solid #000; text-align: right;">{habitat["# Units"]}</td>
                <td style="padding: 6px; border: 1px solid #000;">{habitat["Distinctiveness_Supply"]}</td>
                <td style="padding: 6px; border: 1px solid #000;">{habitat["Habitats Supplied"]}</td>
                <td style="padding: 6px; border: 1px solid #000; text-align: right;">{habitat["# Units_Supply"]}</td>
                <td style="padding: 6px; border: 1px solid #000; text-align: right;">{habitat["Price Per Unit"]}</td>
                <td style="padding: 6px; border: 1px solid #000; text-align: right;">{habitat["Offset Cost"]}</td>
            </tr>
            """
    
    # Add Hedgerow Habitats section with light green background
    if hedgerow_habitats:
        html_table += """
            <tr style="background-color: #D9F2D0;">
                <td colspan="8" style="padding: 6px; border: 1px solid #000; font-weight: bold; color: #000;">Hedgerow Habitats</td>
            </tr>
        """
        for habitat in hedgerow_habitats:
            html_table += f"""
            <tr>
                <td style="padding: 6px; border: 1px solid #000;">{habitat["Distinctiveness"]}</td>
                <td style="padding: 6px; border: 1px solid #000;">{habitat["Habitats Lost"]}</td>
                <td style="padding: 6px; border: 1px solid #000; text-align: right;">{habitat["# Units"]}</td>
                <td style="padding: 6px; border: 1px solid #000;">{habitat["Distinctiveness_Supply"]}</td>
                <td style="padding: 6px; border: 1px solid #000;">{habitat["Habitats Supplied"]}</td>
                <td style="padding: 6px; border: 1px solid #000; text-align: right;">{habitat["# Units_Supply"]}</td>
                <td style="padding: 6px; border: 1px solid #000; text-align: right;">{habitat["Price Per Unit"]}</td>
                <td style="padding: 6px; border: 1px solid #000; text-align: right;">{habitat["Offset Cost"]}</td>
            </tr>
            """
    
    # Add Watercourse Habitats section with light green background
    if watercourse_habitats:
        html_table += """
            <tr style="background-color: #D9F2D0;">
                <td colspan="8" style="padding: 6px; border: 1px solid #000; font-weight: bold; color: #000;">Watercourse Habitats</td>
            </tr>
        """
        for habitat in watercourse_habitats:
            html_table += f"""
            <tr>
                <td style="padding: 6px; border: 1px solid #000;">{habitat["Distinctiveness"]}</td>
                <td style="padding: 6px; border: 1px solid #000;">{habitat["Habitats Lost"]}</td>
                <td style="padding: 6px; border: 1px solid #000; text-align: right;">{habitat["# Units"]}</td>
                <td style="padding: 6px; border: 1px solid #000;">{habitat["Distinctiveness_Supply"]}</td>
                <td style="padding: 6px; border: 1px solid #000;">{habitat["Habitats Supplied"]}</td>
                <td style="padding: 6px; border: 1px solid #000; text-align: right;">{habitat["# Units_Supply"]}</td>
                <td style="padding: 6px; border: 1px solid #000; text-align: right;">{habitat["Price Per Unit"]}</td>
                <td style="padding: 6px; border: 1px solid #000; text-align: right;">{habitat["Offset Cost"]}</td>
            </tr>
            """
    

    
    # Calculate total units including manual entries
    total_demand_units = demand_df['units_required'].sum()
    total_supply_units = alloc_df['units_supplied'].sum()
    
    # Add manual units
    for row in manual_hedgerow_rows:
        units = float(row.get("units", 0.0) or 0.0)
        if units > 0:
            total_demand_units += units
            total_supply_units += units
    
    for row in manual_watercourse_rows:
        units = float(row.get("units", 0.0) or 0.0)
        if units > 0:
            total_demand_units += units
            total_supply_units += units
    
    # Add Planning Discharge Pack and Total
    html_table += f"""
        <tr>
            <td colspan="7" style="padding: 6px; border: 1px solid #000; text-align: right; font-weight: bold;">Planning Discharge Pack</td>
            <td style="padding: 6px; border: 1px solid #000; text-align: right;">£{admin_fee:,.0f}</td>
        </tr>
        <tr style="background-color: #f0f0f0; font-weight: bold;">
            <td style="padding: 6px; border: 1px solid #000;">Total</td>
            <td style="padding: 6px; border: 1px solid #000;"></td>
            <td style="padding: 6px; border: 1px solid #000; text-align: right;">{format_units_total(total_demand_units)}</td>
            <td style="padding: 6px; border: 1px solid #000;"></td>
            <td style="padding: 6px; border: 1px solid #000;"></td>
            <td style="padding: 6px; border: 1px solid #000; text-align: right;">{format_units_total(total_supply_units)}</td>
            <td style="padding: 6px; border: 1px solid #000;"></td>
            <td style="padding: 6px; border: 1px solid #000; text-align: right;">£{total_with_admin:,.0f}</td>
        </tr>
    </tbody>
    </table>
    """
    
    # Determine next steps based on amount (programmatic ending)
    if total_with_admin < 10000:
        next_steps = """<strong>Next Steps</strong>
<br><br>
BNG is a pre-commencement, not a pre-planning, condition.
<br><br>
To accept the quote, let us know—we'll request some basic details before sending the Allocation Agreement. The price is fixed for 30 days, but unit availability is only guaranteed once the agreement is signed.
<br><br>
Once you sign the agreement, pay the settlement fee and provide us with your metric and decision notice we will allocate the units to you.
<br><br>
If you have any questions, please reply to this email or call 01962 436574."""
    else:
        next_steps = """<strong>Next Steps</strong>
<br><br>
BNG is a pre-commencement, not a pre-planning, condition.
<br><br>
To accept the quote, let us know—we'll request some basic details before sending the Allocation Agreement. The price is fixed for 30 days, but unit availability is only guaranteed once the agreement is signed.
<br><br>
We offer two contract options:
<br><br>
1. <strong>Buy It Now:</strong> Pay in full on signing; units allocated immediately.<br>
2. <strong>Reservation & Purchase:</strong> Pay a reservation fee to hold units for up to 6 months, with the option to draw them down anytime in that period.
<br><br>
If you have any questions, please reply to this email or call 01962 436574."""
    
    # Generate full email body matching exact template
    # Dynamic intro text based on promoter selection
    if promoter_name:
        intro_text = f"{promoter_name} has advised us that you need Biodiversity Net Gain units for your development in {location}, and we're here to help you discharge your BNG condition."
    else:
        intro_text = f"Thank you for enquiring about BNG Units for your development in {location}"
    
    email_body = f"""
<div style="font-family: Arial, sans-serif; font-size: 12px; line-height: 1.4;">

<strong>Dear {client_name}</strong>
<br><br>
<strong>Our Ref: {ref_number}</strong>
<br><br>
{intro_text}
<br><br>
<strong>About Us</strong>
<br><br>
Wild Capital is a national supplier of BNG Units and environmental mitigation credits (Nutrient Neutrality, SANG), backed by institutional finance. We create and manage a large portfolio of nature recovery projects, owning the freehold to all mitigation land for the highest integrity and long-term assurance.
<br><br>
Our key advantages:
<br><br>
1. <strong>Permanent Nature Recovery:</strong> We dedicate all land to conservation in perpetuity, not just for the 30-year minimum.<br>
2. <strong>Independently Managed Endowment:</strong> Long-term management funds are fully insured and overseen by independent asset managers.<br>
3. <strong>Independent Governance:</strong> Leading third-party ecologists and contractors oversee all monitoring and habitat management, ensuring objectivity.<br>
4. <strong>Full Ownership and Responsibility:</strong> We hold the freehold and assume complete responsibility for all delivery and management - no ambiguity.
<br><br>
<strong>Your Quote - £{total_with_admin:,.0f} + VAT</strong>
<br><br>
See a detailed breakdown of the pricing below. I've attached a PDF outlining the BNG offset and condition discharge process. If you have any questions, please let us know—we're here to help.
<br><br>

{html_table}

<br><br>
Prices exclude VAT. Any legal costs for contract amendments will be charged to the client and must be paid before allocation.
<br><br>
{next_steps}

</div>
    """
    
    # Create simplified dataframe for display
    all_habitats = area_habitats + hedgerow_habitats + watercourse_habitats
    report_df = pd.DataFrame(all_habitats) if all_habitats else pd.DataFrame()
    
    return report_df, email_body

# ========== PERSISTENT ALLOCATION DETAILS ==========
# This section persists across reruns because it's outside the "if run:" block
if st.session_state.get("optimization_complete", False) and st.session_state.get("last_alloc_df") is not None:
    st.markdown("---")
    st.markdown("### 📊 Optimization Results")
    
    # Show summary at top - recalculate with removed rows and manual entries
    if st.session_state.get("contract_size") and st.session_state.get("total_cost") is not None:
        # Calculate allocation cost after removing rows
        alloc_df_temp = st.session_state["last_alloc_df"].copy()
        if "_row_id" not in alloc_df_temp.columns:
            alloc_df_temp["_row_id"] = range(len(alloc_df_temp))
        removed_ids = st.session_state.get("removed_allocation_rows", [])
        active_alloc_df = alloc_df_temp[~alloc_df_temp["_row_id"].isin(removed_ids)]
        allocation_cost = active_alloc_df["cost"].sum() if not active_alloc_df.empty else 0.0
        
        # Calculate manual entries costs
        manual_hedge_cost = sum(float(r.get("units", 0.0) or 0.0) * float(r.get("price_per_unit", 0.0) or 0.0) 
                               for r in st.session_state.get("manual_hedgerow_rows", []))
        manual_water_cost = sum(float(r.get("units", 0.0) or 0.0) * float(r.get("price_per_unit", 0.0) or 0.0) 
                               for r in st.session_state.get("manual_watercourse_rows", []))
        # For area habitats, apply proper paired calculation or simple calculation
        manual_area_cost = 0.0
        for r in st.session_state.get("manual_area_rows", []):
            if r.get("paired", False):
                # Paired entry - use detailed calculation
                units = float(r.get("units", 0.0) or 0.0)
                demand_stock = float(r.get("demand_stock_use", 0.5))
                companion_stock = 1.0 - demand_stock
                demand_price = float(r.get("demand_price", 0.0) or 0.0)
                companion_price = float(r.get("companion_price", 0.0) or 0.0)
                
                demand_units = units * demand_stock
                companion_units = units * companion_stock
                manual_area_cost += (demand_units * demand_price) + (companion_units * companion_price)
            else:
                # Simple non-paired entry
                units = float(r.get("units", 0.0) or 0.0)
                price = float(r.get("price_per_unit", 0.0) or 0.0)
                manual_area_cost += units * price
        
        total_cost = allocation_cost + manual_hedge_cost + manual_water_cost + manual_area_cost
        
        # Calculate admin fee based on contract size
        admin_fee = get_admin_fee_for_contract_size(st.session_state.get('contract_size', 'small'))
        
        total_with_admin = total_cost + admin_fee
        st.success(
            f"Contract size = **{st.session_state['contract_size']}**. "
            f"Subtotal (units): **£{total_cost:,.0f}**  |  Admin fee: **£{admin_fee:,.0f}**  |  "
            f"Grand total: **£{total_with_admin:,.0f}**"
        )
    
    # Show allocation detail in expander
    with st.expander("📋 Allocation detail", expanded=True):
        alloc_df = st.session_state["last_alloc_df"].copy()
        
        # Add row identifiers if not already present
        if "_row_id" not in alloc_df.columns:
            alloc_df["_row_id"] = range(len(alloc_df))
        
        # Filter out removed rows
        removed_ids = st.session_state.get("removed_allocation_rows", [])
        display_df = alloc_df[~alloc_df["_row_id"].isin(removed_ids)]
        
        if not display_df.empty:
            # Display the dataframe with remove buttons for each row
            for idx, row in display_df.iterrows():
                col1, col2 = st.columns([0.95, 0.05])
                with col1:
                    # Create a single-row dataframe for display
                    single_row_df = pd.DataFrame([row.drop("_row_id")])
                    st.dataframe(single_row_df, use_container_width=True, hide_index=True)
                with col2:
                    if st.button("❌", key=f"remove_alloc_{row['_row_id']}", help="Remove this line"):
                        if "_row_id" in row:
                            st.session_state["removed_allocation_rows"].append(row["_row_id"])
                            st.rerun()
            
            if "price_source" in alloc_df.columns:
                st.caption("Note: `price_source='group-proxy'` or `any-low-proxy` indicate proxy pricing rules.")
        else:
            st.info("All allocation rows have been removed. Add manual entries below or run optimization again.")
    
    # Show Site/Habitat totals in expander
    if st.session_state.get("site_hab_totals") is not None:
        with st.expander("📊 Site/Habitat totals (effective units)", expanded=True):
            st.dataframe(st.session_state["site_hab_totals"], use_container_width=True, hide_index=True)
    
    # Show By bank in expander
    if st.session_state.get("by_bank") is not None:
        with st.expander("🏢 By bank", expanded=False):
            st.dataframe(st.session_state["by_bank"], use_container_width=True)
    
    # Show By habitat in expander
    if st.session_state.get("by_hab") is not None:
        with st.expander("🌿 By habitat (supply)", expanded=False):
            st.dataframe(st.session_state["by_hab"], use_container_width=True)
    
    # Show Order summary in expander
    if st.session_state.get("summary_df") is not None:
        with st.expander("💰 Order summary (with admin fee)", expanded=True):
            st.dataframe(st.session_state["summary_df"], hide_index=True, use_container_width=True)
    
    # ========== SURPLUS UPLIFT OFFSET (SUO) SECTION ==========
    if st.session_state.get("suo_applicable", False) and st.session_state.get("suo_results") is not None:
        st.markdown("---")
        st.markdown("### 🎯 Surplus Uplift Offset (SUO) - Cost Discount")
        
        suo_results = st.session_state["suo_results"]
        
        # SUO toggle checkbox
        suo_enabled = st.checkbox(
            "✅ Apply Surplus Uplift Offset Discount",
            value=st.session_state.get("suo_enabled", True),
            key="suo_toggle",
            help="Apply cost discount based on eligible surplus (Medium+ distinctiveness, 50% headroom) from your development site"
        )
        st.session_state["suo_enabled"] = suo_enabled
        
        # Store the actual discount to use for emails/reports
        # This ensures the email matches what the user sees in the UI
        if suo_enabled:
            st.session_state["suo_discount_for_report"] = suo_results['discount_fraction']
        else:
            st.session_state["suo_discount_for_report"] = 0.0
        
        if suo_enabled:
            discount_pct = suo_results['discount_fraction'] * 100
            st.success(f"✅ SUO Discount Applied: {discount_pct:.1f}% cost reduction")
            
            # Calculate discounted costs
            # Get current allocation cost
            alloc_df_temp = st.session_state["last_alloc_df"].copy()
            if "_row_id" not in alloc_df_temp.columns:
                alloc_df_temp["_row_id"] = range(len(alloc_df_temp))
            removed_ids = st.session_state.get("removed_allocation_rows", [])
            active_alloc_df = alloc_df_temp[~alloc_df_temp["_row_id"].isin(removed_ids)]
            
            original_allocation_cost = active_alloc_df["cost"].sum() if not active_alloc_df.empty else 0.0
            discounted_allocation_cost = original_allocation_cost * (1 - suo_results['discount_fraction'])
            cost_savings = original_allocation_cost - discounted_allocation_cost
            
            # Add manual costs (not discounted)
            manual_hedge_cost = sum(float(r.get("units", 0.0) or 0.0) * float(r.get("price_per_unit", 0.0) or 0.0) 
                                   for r in st.session_state.get("manual_hedgerow_rows", []))
            manual_water_cost = sum(float(r.get("units", 0.0) or 0.0) * float(r.get("price_per_unit", 0.0) or 0.0) 
                                   for r in st.session_state.get("manual_watercourse_rows", []))
            manual_area_cost = 0.0
            for r in st.session_state.get("manual_area_rows", []):
                if r.get("paired", False):
                    units = float(r.get("units", 0.0) or 0.0)
                    demand_stock = float(r.get("demand_stock_use", 0.5))
                    companion_stock = 1.0 - demand_stock
                    demand_price = float(r.get("demand_price", 0.0) or 0.0)
                    companion_price = float(r.get("companion_price", 0.0) or 0.0)
                    demand_units = units * demand_stock
                    companion_units = units * companion_stock
                    manual_area_cost += (demand_units * demand_price) + (companion_units * companion_price)
                else:
                    units = float(r.get("units", 0.0) or 0.0)
                    price = float(r.get("price_per_unit", 0.0) or 0.0)
                    manual_area_cost += units * price
            
            total_discounted_cost = discounted_allocation_cost + manual_hedge_cost + manual_water_cost + manual_area_cost
            
            # Calculate admin fee based on contract size
            admin_fee = get_admin_fee_for_contract_size(st.session_state.get('contract_size', 'small'))
            
            total_with_admin_discounted = total_discounted_cost + admin_fee
            
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
            
            # Show cost comparison
            with st.expander("💰 Cost Comparison (Before vs After SUO)", expanded=True):
                comparison_df = pd.DataFrame([
                    {"Cost Item": "Allocation Cost (optimizer)", "Before SUO": f"£{original_allocation_cost:,.2f}", 
                     "After SUO": f"£{discounted_allocation_cost:,.2f}", "Savings": f"£{cost_savings:,.2f}"},
                    {"Cost Item": "Manual Additions", "Before SUO": f"£{manual_hedge_cost + manual_water_cost + manual_area_cost:,.2f}", 
                     "After SUO": f"£{manual_hedge_cost + manual_water_cost + manual_area_cost:,.2f}", "Savings": "£0.00"},
                    {"Cost Item": "Admin Fee", "Before SUO": f"£{admin_fee:,.2f}", 
                     "After SUO": f"£{admin_fee:,.2f}", "Savings": "£0.00"},
                    {"Cost Item": "TOTAL", "Before SUO": f"£{original_allocation_cost + manual_hedge_cost + manual_water_cost + manual_area_cost + admin_fee:,.2f}",
                     "After SUO": f"£{total_with_admin_discounted:,.2f}", "Savings": f"£{cost_savings:,.2f}"}
                ])
                st.dataframe(comparison_df, use_container_width=True, hide_index=True)
                
                st.info(f"**Total savings: £{cost_savings:,.2f} ({discount_pct:.1f}% discount on allocation costs)**")
            
            # Update the displayed total at the top
            st.info(f"ℹ️ **With SUO Discount**: Subtotal: £{total_discounted_cost:,.0f} | Admin: £{admin_fee:,.0f} | **Grand Total: £{total_with_admin_discounted:,.0f}**")
            
        else:
            discount_pct = suo_results['discount_fraction'] * 100
            st.info(f"ℹ️ SUO discount available ({discount_pct:.1f}% off) but not applied. Check the box above to apply the discount.")

# ========== MANUAL AREA/HEDGEROW/WATERCOURSE ENTRIES (PERSISTENT) ==========
# This section persists across reruns because it's outside the "if run:" block
if st.session_state.get("optimization_complete", False):
    st.markdown("---")
    st.markdown("#### ➕ Manual Additions (Area, Hedgerow & Watercourse)")
    st.info("Add additional area, hedgerow or watercourse units to your quote. These will be included in the final client report.")
    
    # Get available habitats
    area_choices = get_area_habitats(backend["HabitatCatalog"])
    hedgerow_choices = get_hedgerow_habitats(backend["HabitatCatalog"])
    watercourse_choices = get_watercourse_habitats(backend["HabitatCatalog"])
    
    # Get list of banks for manual entry
    if "Banks" in backend and not backend["Banks"].empty:
        bank_list = sorted(backend["Banks"]["BANK_KEY"].dropna().unique().tolist())
        st.session_state["bank_list_for_manual"] = bank_list
    else:
        bank_list = st.session_state.get("bank_list_for_manual", [])
    
    # Area Habitats Section
    with st.container(border=True):
        st.markdown("**🌳 Manual Area Habitat Units**")
        
        # Add Net Gain option to area choices
        area_choices_with_ng = area_choices + [NET_GAIN_LABEL] if area_choices else [NET_GAIN_LABEL]
        
        to_delete_area = []
        for idx, row in enumerate(st.session_state.manual_area_rows):
            is_paired = bool(row.get("paired", False))
            
            # Check if paired - show expanded fields
            if is_paired:
                st.markdown(f"**Entry {idx + 1}** (Paired Allocation)")
                
                # First row: Habitat Lost and Paired checkbox
                c1, c2, c_del = st.columns([0.45, 0.45, 0.10])
                with c1:
                    if area_choices_with_ng:
                        default_idx = None
                        if row.get("habitat_lost") and row["habitat_lost"] in area_choices_with_ng:
                            default_idx = area_choices_with_ng.index(row["habitat_lost"])
                        st.session_state.manual_area_rows[idx]["habitat_lost"] = st.selectbox(
                            "Habitat Lost", area_choices_with_ng,
                            index=default_idx,
                            key=f"manual_area_lost_{row['id']}",
                            help="Select area habitat lost"
                        )
                with c2:
                    st.session_state.manual_area_rows[idx]["units"] = st.number_input(
                        "Units Required", min_value=0.0, step=0.01, value=float(row.get("units", 0.0)), 
                        key=f"manual_area_units_{row['id']}",
                        help="Total units of habitat lost"
                    )
                with c_del:
                    st.markdown("")  # Spacer
                    st.markdown("")  # Spacer
                    if st.button("🗑️", key=f"del_manual_area_{row['id']}", help="Remove this entry"):
                        to_delete_area.append(row["id"])
                
                # Second row: Demand Habitat details
                st.markdown("**Demand Habitat:**")
                c1, c2, c3 = st.columns([0.40, 0.30, 0.30])
                with c1:
                    if area_choices_with_ng:
                        default_idx = None
                        if row.get("demand_habitat") and row["demand_habitat"] in area_choices_with_ng:
                            default_idx = area_choices_with_ng.index(row["demand_habitat"])
                        st.session_state.manual_area_rows[idx]["demand_habitat"] = st.selectbox(
                            "Habitat Type", area_choices_with_ng,
                            index=default_idx,
                            key=f"manual_area_demand_hab_{row['id']}",
                            help="Primary habitat in paired allocation"
                        )
                with c2:
                    if bank_list:
                        default_idx = 0
                        if row.get("demand_bank") and row["demand_bank"] in bank_list:
                            default_idx = bank_list.index(row["demand_bank"])
                        st.session_state.manual_area_rows[idx]["demand_bank"] = st.selectbox(
                            "Bank", bank_list,
                            index=default_idx,
                            key=f"manual_area_demand_bank_{row['id']}",
                            help="Bank providing demand habitat"
                        )
                    else:
                        st.session_state.manual_area_rows[idx]["demand_bank"] = st.text_input(
                            "Bank", value=row.get("demand_bank", ""),
                            key=f"manual_area_demand_bank_{row['id']}"
                        )
                with c3:
                    st.session_state.manual_area_rows[idx]["demand_price"] = st.number_input(
                        "Price/Unit (£)", min_value=0.0, step=1.0, value=float(row.get("demand_price", 0.0)),
                        key=f"manual_area_demand_price_{row['id']}",
                        help="Price per unit for demand habitat"
                    )
                
                # Third row: Companion Habitat details
                st.markdown("**Companion Habitat:**")
                c1, c2, c3 = st.columns([0.40, 0.30, 0.30])
                with c1:
                    if area_choices_with_ng:
                        default_idx = None
                        if row.get("companion_habitat") and row["companion_habitat"] in area_choices_with_ng:
                            default_idx = area_choices_with_ng.index(row["companion_habitat"])
                        st.session_state.manual_area_rows[idx]["companion_habitat"] = st.selectbox(
                            "Habitat Type", area_choices_with_ng,
                            index=default_idx,
                            key=f"manual_area_companion_hab_{row['id']}",
                            help="Companion habitat in paired allocation"
                        )
                with c2:
                    if bank_list:
                        default_idx = 0
                        if row.get("companion_bank") and row["companion_bank"] in bank_list:
                            default_idx = bank_list.index(row["companion_bank"])
                        st.session_state.manual_area_rows[idx]["companion_bank"] = st.selectbox(
                            "Bank", bank_list,
                            index=default_idx,
                            key=f"manual_area_companion_bank_{row['id']}",
                            help="Bank providing companion habitat"
                        )
                    else:
                        st.session_state.manual_area_rows[idx]["companion_bank"] = st.text_input(
                            "Bank", value=row.get("companion_bank", ""),
                            key=f"manual_area_companion_bank_{row['id']}"
                        )
                with c3:
                    st.session_state.manual_area_rows[idx]["companion_price"] = st.number_input(
                        "Price/Unit (£)", min_value=0.0, step=1.0, value=float(row.get("companion_price", 0.0)),
                        key=f"manual_area_companion_price_{row['id']}",
                        help="Price per unit for companion habitat"
                    )
                
                # Fourth row: SRM selection and stock use ratios
                c1, c2, c3 = st.columns([0.33, 0.33, 0.34])
                with c1:
                    tier_options = ["local", "adjacent", "far"]
                    default_tier_idx = 1  # Default to adjacent
                    if row.get("srm_tier") and row["srm_tier"] in tier_options:
                        default_tier_idx = tier_options.index(row["srm_tier"])
                    st.session_state.manual_area_rows[idx]["srm_tier"] = st.selectbox(
                        "SRM Tier", tier_options,
                        index=default_tier_idx,
                        key=f"manual_area_srm_{row['id']}",
                        help="Strategic Resource Multiplier tier: local (1.0), adjacent (1.33), far (2.0)"
                    )
                with c2:
                    st.session_state.manual_area_rows[idx]["demand_stock_use"] = st.number_input(
                        "Demand Stock Use", min_value=0.0, max_value=1.0, step=0.01, 
                        value=float(row.get("demand_stock_use", 0.5)),
                        key=f"manual_area_demand_stock_{row['id']}",
                        help="Proportion of stock from demand habitat (0.0 to 1.0)"
                    )
                with c3:
                    companion_stock = 1.0 - float(row.get("demand_stock_use", 0.5))
                    st.metric("Companion Stock Use", f"{companion_stock:.2f}", help="Auto-calculated to sum to 1.0")
                
                # Display calculated values
                srm_mult = {"local": 1.0, "adjacent": 4/3, "far": 2.0}.get(row.get("srm_tier", "adjacent"), 4/3)
                units_req = float(row.get("units", 0.0))
                demand_stock = float(row.get("demand_stock_use", 0.5))
                companion_stock = 1.0 - demand_stock
                demand_units = units_req * demand_stock
                companion_units = units_req * companion_stock
                demand_pr = float(row.get("demand_price", 0.0))
                companion_pr = float(row.get("companion_price", 0.0))
                total_cost = (demand_units * demand_pr) + (companion_units * companion_pr)
                
                st.info(
                    f"**Calculation:** SRM = {srm_mult:.2f} | "
                    f"Demand: {demand_units:.2f} units × £{demand_pr:.0f} = £{demand_units * demand_pr:,.0f} | "
                    f"Companion: {companion_units:.2f} units × £{companion_pr:.0f} = £{companion_units * companion_pr:,.0f} | "
                    f"**Total: £{total_cost:,.0f}**"
                )
                
                # Fifth row: Spatial Risk Configuration
                st.markdown("**Spatial Risk Configuration:**")
                c1, c2 = st.columns([0.5, 0.5])
                with c1:
                    spatial_risk_options = ["None", "Demand Habitat", "Companion Habitat"]
                    default_spatial_idx = 0
                    current_spatial = row.get("spatial_risk_offset_by", "None")
                    if current_spatial in spatial_risk_options:
                        default_spatial_idx = spatial_risk_options.index(current_spatial)
                    st.session_state.manual_area_rows[idx]["spatial_risk_offset_by"] = st.selectbox(
                        "Which habitat offsets spatial risk?",
                        spatial_risk_options,
                        index=default_spatial_idx,
                        key=f"manual_area_spatial_offset_{row['id']}",
                        help="Select which habitat in the pair is offsetting the spatial risk"
                    )
                with c2:
                    srm_value_options = ["4/3 (Adjacent)", "2.0 (Far)"]
                    default_srm_value_idx = 0 if row.get("srm_tier", "adjacent") == "adjacent" else 1
                    st.session_state.manual_area_rows[idx]["spatial_risk_srm"] = st.selectbox(
                        "Spatial Risk SRM",
                        srm_value_options,
                        index=default_srm_value_idx,
                        key=f"manual_area_spatial_srm_{row['id']}",
                        help="The SRM value applied for spatial risk (4/3 or 2.0)"
                    )
                
                # Paired checkbox toggle
                c1, c2 = st.columns([0.5, 0.5])
                with c1:
                    st.session_state.manual_area_rows[idx]["paired"] = st.checkbox(
                        "✓ Paired Entry", value=True,
                        key=f"manual_area_paired_{row['id']}",
                        help="Uncheck to switch to simple entry mode"
                    )
                
                st.markdown("---")
                
            else:
                # Simple non-paired entry (original layout)
                c1, c2, c3, c4, c5, c6 = st.columns([0.25, 0.25, 0.13, 0.13, 0.14, 0.10])
                with c1:
                    if area_choices_with_ng:
                        default_idx = None
                        if row.get("habitat_lost") and row["habitat_lost"] in area_choices_with_ng:
                            default_idx = area_choices_with_ng.index(row["habitat_lost"])
                        st.session_state.manual_area_rows[idx]["habitat_lost"] = st.selectbox(
                            "Habitat Lost", area_choices_with_ng,
                            index=default_idx,
                            key=f"manual_area_lost_{row['id']}",
                            help="Select area habitat lost"
                        )
                    else:
                        st.warning("No area habitats available in catalog")
                with c2:
                    if area_choices_with_ng:
                        default_idx = None
                        if row.get("habitat_name") and row["habitat_name"] in area_choices_with_ng:
                            default_idx = area_choices_with_ng.index(row["habitat_name"])
                        st.session_state.manual_area_rows[idx]["habitat_name"] = st.selectbox(
                            "Habitat to Mitigate", area_choices_with_ng,
                            index=default_idx,
                            key=f"manual_area_hab_{row['id']}",
                            help="Select area habitat to mitigate"
                        )
                    else:
                        st.warning("No area habitats available")
                with c3:
                    st.session_state.manual_area_rows[idx]["units"] = st.number_input(
                        "Units", min_value=0.0, step=0.01, value=float(row.get("units", 0.0)), 
                        key=f"manual_area_units_{row['id']}"
                    )
                with c4:
                    st.session_state.manual_area_rows[idx]["price_per_unit"] = st.number_input(
                        "Price/Unit (£)", min_value=0.0, step=1.0, value=float(row.get("price_per_unit", 0.0)),
                        key=f"manual_area_price_{row['id']}"
                    )
                with c5:
                    st.session_state.manual_area_rows[idx]["paired"] = st.checkbox(
                        "Paired", value=False,
                        key=f"manual_area_paired_{row['id']}",
                        help="Check to switch to paired entry mode with full details"
                    )
                with c6:
                    if st.button("🗑️", key=f"del_manual_area_{row['id']}", help="Remove this row"):
                        to_delete_area.append(row["id"])
        
        if to_delete_area:
            st.session_state.manual_area_rows = [r for r in st.session_state.manual_area_rows if r["id"] not in to_delete_area]
            st.rerun()
        
        col1, col2 = st.columns([0.5, 0.5])
        with col1:
            if st.button("➕ Add Area Habitat Entry", key="add_manual_area_btn"):
                st.session_state.manual_area_rows.append({
                    "id": st.session_state._next_manual_area_id,
                    "habitat_lost": "",
                    "habitat_name": "",
                    "units": 0.0,
                    "price_per_unit": 0.0,
                    "paired": False
                })
                st.session_state._next_manual_area_id += 1
                st.rerun()
        with col2:
            if st.button("🧹 Clear Area Habitats", key="clear_manual_area_btn"):
                st.session_state.manual_area_rows = []
                st.rerun()
    
    # Hedgerow Section
    with st.container(border=True):
        st.markdown("**🌿 Manual Hedgerow Units**")
        
        # Add Net Gain option to hedgerow choices
        hedgerow_choices_with_ng = hedgerow_choices + [NET_GAIN_LABEL] if hedgerow_choices else [NET_GAIN_LABEL]
        
        to_delete_hedgerow = []
        for idx, row in enumerate(st.session_state.manual_hedgerow_rows):
            c1, c2, c3, c4, c5 = st.columns([0.30, 0.30, 0.15, 0.15, 0.10])
            with c1:
                if hedgerow_choices_with_ng:
                    default_idx = None
                    if row.get("habitat_lost") and row["habitat_lost"] in hedgerow_choices_with_ng:
                        default_idx = hedgerow_choices_with_ng.index(row["habitat_lost"])
                    st.session_state.manual_hedgerow_rows[idx]["habitat_lost"] = st.selectbox(
                        "Habitat Lost", hedgerow_choices_with_ng,
                        index=default_idx,
                        key=f"manual_hedge_lost_{row['id']}",
                        help="Select hedgerow habitat lost"
                    )
                else:
                    st.warning("No hedgerow habitats available in catalog")
            with c2:
                if hedgerow_choices_with_ng:
                    default_idx = None
                    if row.get("habitat_name") and row["habitat_name"] in hedgerow_choices_with_ng:
                        default_idx = hedgerow_choices_with_ng.index(row["habitat_name"])
                    st.session_state.manual_hedgerow_rows[idx]["habitat_name"] = st.selectbox(
                        "Habitat to Mitigate", hedgerow_choices_with_ng,
                        index=default_idx,
                        key=f"manual_hedge_hab_{row['id']}",
                        help="Select hedgerow habitat to mitigate"
                    )
                else:
                    st.warning("No hedgerow habitats available")
            with c3:
                st.session_state.manual_hedgerow_rows[idx]["units"] = st.number_input(
                    "Units", min_value=0.0, step=0.01, value=float(row.get("units", 0.0)), 
                    key=f"manual_hedge_units_{row['id']}"
                )
            with c4:
                st.session_state.manual_hedgerow_rows[idx]["price_per_unit"] = st.number_input(
                    "Price/Unit (£)", min_value=0.0, step=1.0, value=float(row.get("price_per_unit", 0.0)),
                    key=f"manual_hedge_price_{row['id']}"
                )
            with c5:
                if st.button("🗑️", key=f"del_manual_hedge_{row['id']}", help="Remove this row"):
                    to_delete_hedgerow.append(row["id"])
        
        if to_delete_hedgerow:
            st.session_state.manual_hedgerow_rows = [r for r in st.session_state.manual_hedgerow_rows if r["id"] not in to_delete_hedgerow]
            st.rerun()
        
        col1, col2 = st.columns([0.5, 0.5])
        with col1:
            if st.button("➕ Add Hedgerow Entry", key="add_manual_hedge_btn"):
                st.session_state.manual_hedgerow_rows.append({
                    "id": st.session_state._next_manual_hedgerow_id,
                    "habitat_lost": "",
                    "habitat_name": "",
                    "units": 0.0,
                    "price_per_unit": 0.0
                })
                st.session_state._next_manual_hedgerow_id += 1
                st.rerun()
        with col2:
            if st.button("🧹 Clear Hedgerow", key="clear_manual_hedge_btn"):
                st.session_state.manual_hedgerow_rows = []
                st.rerun()
    
    # Watercourse Section
    with st.container(border=True):
        st.markdown("**💧 Manual Watercourse Units**")
        
        # Add Net Gain option to watercourse choices
        watercourse_choices_with_ng = watercourse_choices + [NET_GAIN_LABEL] if watercourse_choices else [NET_GAIN_LABEL]
        
        to_delete_watercourse = []
        for idx, row in enumerate(st.session_state.manual_watercourse_rows):
            c1, c2, c3, c4, c5 = st.columns([0.30, 0.30, 0.15, 0.15, 0.10])
            with c1:
                if watercourse_choices_with_ng:
                    default_idx = None
                    if row.get("habitat_lost") and row["habitat_lost"] in watercourse_choices_with_ng:
                        default_idx = watercourse_choices_with_ng.index(row["habitat_lost"])
                    st.session_state.manual_watercourse_rows[idx]["habitat_lost"] = st.selectbox(
                        "Habitat Lost", watercourse_choices_with_ng,
                        index=default_idx,
                        key=f"manual_water_lost_{row['id']}",
                        help="Select watercourse habitat lost"
                    )
                else:
                    st.warning("No watercourse habitats available in catalog")
            with c2:
                if watercourse_choices_with_ng:
                    default_idx = None
                    if row.get("habitat_name") and row["habitat_name"] in watercourse_choices_with_ng:
                        default_idx = watercourse_choices_with_ng.index(row["habitat_name"])
                    st.session_state.manual_watercourse_rows[idx]["habitat_name"] = st.selectbox(
                        "Habitat to Mitigate", watercourse_choices_with_ng,
                        index=default_idx,
                        key=f"manual_water_hab_{row['id']}",
                        help="Select watercourse habitat to mitigate"
                    )
                else:
                    st.warning("No watercourse habitats available")
            with c3:
                st.session_state.manual_watercourse_rows[idx]["units"] = st.number_input(
                    "Units", min_value=0.0, step=0.01, value=float(row.get("units", 0.0)),
                    key=f"manual_water_units_{row['id']}"
                )
            with c4:
                st.session_state.manual_watercourse_rows[idx]["price_per_unit"] = st.number_input(
                    "Price/Unit (£)", min_value=0.0, step=1.0, value=float(row.get("price_per_unit", 0.0)),
                    key=f"manual_water_price_{row['id']}"
                )
            with c5:
                if st.button("🗑️", key=f"del_manual_water_{row['id']}", help="Remove this row"):
                    to_delete_watercourse.append(row["id"])
        
        if to_delete_watercourse:
            st.session_state.manual_watercourse_rows = [r for r in st.session_state.manual_watercourse_rows if r["id"] not in to_delete_watercourse]
            st.rerun()
        
        col1, col2 = st.columns([0.5, 0.5])
        with col1:
            if st.button("➕ Add Watercourse Entry", key="add_manual_water_btn"):
                st.session_state.manual_watercourse_rows.append({
                    "id": st.session_state._next_manual_watercourse_id,
                    "habitat_lost": "",
                    "habitat_name": "",
                    "units": 0.0,
                    "price_per_unit": 0.0
                })
                st.session_state._next_manual_watercourse_id += 1
                st.rerun()
        with col2:
            if st.button("🧹 Clear Watercourse", key="clear_manual_water_btn"):
                st.session_state.manual_watercourse_rows = []
                st.rerun()

# Add this to your optimization results section (after the downloads):
# Allow client report generation if optimization was run OR if there are manual entries
has_optimizer_results = (st.session_state.get("optimization_complete", False) and 
                         isinstance(st.session_state.get("last_alloc_df"), pd.DataFrame) and 
                         not st.session_state["last_alloc_df"].empty)

has_manual_entries = (st.session_state.get("optimization_complete", False) and
                     (len(st.session_state.get("manual_hedgerow_rows", [])) > 0 or
                      len(st.session_state.get("manual_watercourse_rows", [])) > 0 or
                      len(st.session_state.get("manual_area_rows", [])) > 0))

if has_optimizer_results or has_manual_entries:
    
    # Get data from session state
    session_alloc_df = None
    if isinstance(st.session_state.get("last_alloc_df"), pd.DataFrame):
        session_alloc_df = st.session_state["last_alloc_df"].copy()
        
        # Filter out removed rows if _row_id column exists
        if "_row_id" in session_alloc_df.columns:
            removed_ids = st.session_state.get("removed_allocation_rows", [])
            session_alloc_df = session_alloc_df[~session_alloc_df["_row_id"].isin(removed_ids)]
    
    # If session_alloc_df is empty or None, create an empty dataframe with proper structure
    if session_alloc_df is None or session_alloc_df.empty:
        session_alloc_df = pd.DataFrame(columns=[
            "demand_habitat", "BANK_KEY", "bank_name", "bank_id", "supply_habitat",
            "allocation_type", "tier", "units_supplied", "unit_price", "cost",
            "price_source", "price_habitat"
        ])
    
    # Reconstruct demand_df from session state
    session_demand_df = pd.DataFrame(
        [{"habitat_name": sstr(r["habitat_name"]), "units_required": float(r.get("units", 0.0) or 0.0)}
         for r in st.session_state.demand_rows if sstr(r["habitat_name"]) and float(r.get("units", 0.0) or 0.0) > 0]
    )
    
    # Calculate total cost from session data (includes removed rows filtering)
    session_total_cost = session_alloc_df["cost"].sum() if not session_alloc_df.empty else 0.0
    
    st.markdown("---")
    st.markdown("#### 📧 Client Report Generation")
    
    # Initialize email inputs in session state (only if not exists)
    if "email_client_name" not in st.session_state:
        st.session_state.email_client_name = "INSERT NAME"
    if "email_ref_number" not in st.session_state:
        st.session_state.email_ref_number = "BNG00XXX"
    if "email_location" not in st.session_state:
        st.session_state.email_location = "INSERT LOCATION"
    
    with st.expander("Generate Client Email Report", expanded=True):  # Force it to stay expanded
        st.markdown("**Generate a client-facing report table and email:**")
        
        # ========== FIXED FORM WITH PERSISTENCE ==========
        with st.form("client_email_form", clear_on_submit=False):
            st.markdown("**📝 Email Details:**")
            col_input1, col_input2, col_input3 = st.columns([1, 1, 1])
            
            with col_input1:
                form_client_name = st.text_input(
                    "Client Name", 
                    value=st.session_state.email_client_name,
                    key="form_client_name"
                )
            
            with col_input2:
                form_ref_number = st.text_input(
                    "Reference Number", 
                    value=st.session_state.email_ref_number,
                    key="form_ref_number"
                )
            
            with col_input3:
                form_location = st.text_input(
                    "Development Location", 
                    value=st.session_state.email_location,
                    key="form_location"
                )
            
            # Customer info section
            st.markdown("**👤 Customer Information (Optional):**")
            st.caption("Link this quote to a customer record for tracking. Email or Mobile helps avoid duplicates.")
            
            col_cust1, col_cust2 = st.columns(2)
            with col_cust1:
                form_customer_email = st.text_input("Customer Email", key="form_customer_email")
            with col_cust2:
                form_customer_mobile = st.text_input("Customer Mobile", key="form_customer_mobile")
            
            with st.expander("Additional Customer Details (Optional)", expanded=False):
                col_title, col_fname, col_lname = st.columns([1, 2, 2])
                with col_title:
                    form_customer_title = st.selectbox("Title", ["", "Mr", "Mrs", "Miss", "Ms", "Dr", "Prof"], key="form_customer_title")
                with col_fname:
                    form_customer_first_name = st.text_input("First Name", key="form_customer_first_name")
                with col_lname:
                    form_customer_last_name = st.text_input("Last Name", key="form_customer_last_name")
                
                col_cust3, col_cust4 = st.columns(2)
                with col_cust3:
                    form_customer_company = st.text_input("Company Name", key="form_customer_company")
                with col_cust4:
                    form_customer_contact = st.text_input("Contact Person", key="form_customer_contact")
                
                form_customer_address = st.text_area("Customer Address", key="form_customer_address", height=80)
            
            # Form submit button
            form_submitted = st.form_submit_button("Update Email Details")
        
        # Handle form submission OUTSIDE the form but INSIDE the expander
        if form_submitted:
            st.session_state.email_client_name = form_client_name
            st.session_state.email_ref_number = form_ref_number
            st.session_state.email_location = form_location
            st.success("Email details updated!")
            
            # Save to database after updating email details
            if not db:
                st.error("❌ Database is not available.")
            elif not form_client_name or form_client_name == "INSERT NAME":
                st.warning("⚠️ Please enter a valid client name before saving.")
            elif not form_ref_number or form_ref_number == "BNG00XXX":
                st.warning("⚠️ Please enter a valid reference number before saving.")
            elif not form_location or form_location == "INSERT LOCATION":
                st.warning("⚠️ Please enter a valid location before saving.")
            elif session_alloc_df.empty:
                st.error("❌ No optimization results to save. Please run the optimizer first.")
            else:
                try:
                    # Handle customer info if provided
                    customer_id = None
                    if form_customer_email or form_customer_mobile:
                        # Check if customer already exists
                        existing_customer = db.get_customer_by_contact(
                            email=form_customer_email if form_customer_email else None,
                            mobile_number=form_customer_mobile if form_customer_mobile else None
                        )
                        
                        if existing_customer:
                            customer_id = existing_customer['id']
                            st.info(f"ℹ️ Linked to existing customer: {existing_customer['client_name']} (ID: {customer_id})")
                        else:
                            # Create new customer
                            customer_id = db.add_customer(
                                client_name=form_client_name,
                                title=form_customer_title if form_customer_title else None,
                                first_name=form_customer_first_name if form_customer_first_name else None,
                                last_name=form_customer_last_name if form_customer_last_name else None,
                                company_name=form_customer_company if form_customer_company else None,
                                contact_person=form_customer_contact if form_customer_contact else None,
                                address=form_customer_address if form_customer_address else None,
                                email=form_customer_email if form_customer_email else None,
                                mobile_number=form_customer_mobile if form_customer_mobile else None
                            )
                            st.info(f"✅ New customer created (ID: {customer_id})")
                    
                    # Get the current username
                    current_user = st.secrets.get("auth", {}).get("username", DEFAULT_USER)
                    
                    # Determine contract size from allocation data
                    present_sizes = backend.get("Pricing", pd.DataFrame()).get("contract_size", pd.Series()).drop_duplicates().tolist() if backend else []
                    total_units = session_demand_df["units_required"].sum() if not session_demand_df.empty else 0.0
                    contract_size_val = select_contract_size(total_units, present_sizes) if present_sizes else "Unknown"
                    
                    # Calculate admin fee based on contract size
                    admin_fee_for_quote = get_admin_fee_for_contract_size(contract_size_val)
                    
                    submission_id = db.store_submission(
                        client_name=form_client_name,
                        reference_number=form_ref_number,
                        site_location=form_location,
                        target_lpa=st.session_state.get("target_lpa_name", ""),
                        target_nca=st.session_state.get("target_nca_name", ""),
                        target_lat=st.session_state.get("target_lat"),
                        target_lon=st.session_state.get("target_lon"),
                        lpa_neighbors=st.session_state.get("lpa_neighbors", []),
                        nca_neighbors=st.session_state.get("nca_neighbors", []),
                        demand_df=session_demand_df,
                        allocation_df=session_alloc_df,
                        contract_size=contract_size_val,
                        total_cost=session_total_cost,
                        admin_fee=admin_fee_for_quote,
                        manual_hedgerow_rows=st.session_state.get("manual_hedgerow_rows", []),
                        manual_watercourse_rows=st.session_state.get("manual_watercourse_rows", []),
                        manual_area_habitat_rows=st.session_state.get("manual_area_habitat_rows", []),
                        username=current_user,
                        promoter_name=st.session_state.get("selected_promoter"),
                        promoter_discount_type=st.session_state.get("promoter_discount_type"),
                        promoter_discount_value=st.session_state.get("promoter_discount_value"),
                        customer_id=customer_id,
                        suo_enabled=st.session_state.get("suo_enabled", False),
                        suo_discount_fraction=(st.session_state.get("suo_results") or {}).get("discount_fraction"),
                        suo_eligible_surplus=(st.session_state.get("suo_results") or {}).get("eligible_surplus"),
                        suo_usable_surplus=(st.session_state.get("suo_results") or {}).get("usable_surplus"),
                        suo_total_units=(st.session_state.get("suo_results") or {}).get("total_units_purchased")
                    )
                    st.success(f"✅ Quote saved to database! Submission ID: {submission_id}")
                    st.info(f"📊 Client: {form_client_name} | Reference: {form_ref_number} | Total: £{session_total_cost + admin_fee_for_quote:,.0f}")
                except Exception as e:
                    st.error(f"❌ Error saving to database: {e}")
                    import traceback
                    st.code(traceback.format_exc())
            # Don't call st.rerun() - let it naturally update
        
        # Use the session state values for generating the report
        client_name = st.session_state.email_client_name
        ref_number = st.session_state.email_ref_number
        location = st.session_state.email_location    
        
        # Calculate admin fee based on contract size
        present_sizes = backend.get("Pricing", pd.DataFrame()).get("contract_size", pd.Series()).drop_duplicates().tolist() if backend else []
        total_units = session_demand_df["units_required"].sum() if not session_demand_df.empty else 0.0
        contract_size_val = select_contract_size(total_units, present_sizes) if present_sizes else "Unknown"
        admin_fee_for_report = get_admin_fee_for_contract_size(contract_size_val)
        
        # Generate the report using session data and input values
        client_table, email_html = generate_client_report_table_fixed(
            session_alloc_df, session_demand_df, session_total_cost, admin_fee_for_report,
            client_name, ref_number, location,
            st.session_state.manual_hedgerow_rows,
            st.session_state.manual_watercourse_rows,
            st.session_state.manual_area_rows,
            st.session_state.get("removed_allocation_rows", []),
            st.session_state.get("selected_promoter"),
            st.session_state.get("promoter_discount_type"),
            st.session_state.get("promoter_discount_value"),
            st.session_state.get("suo_discount_for_report", 0.0)
        )
        
        # Display the table
        st.markdown("**Client Report Table:**")
        
        # Format for display (clean up column names)
        if not client_table.empty:
            display_table = client_table.copy()
            display_table = display_table.rename(columns={
                "Distinctiveness_Supply": "Supply Distinctiveness",
                "# Units_Supply": "Supply Units"
            })
            
            # Remove empty development impact columns for display
            cols_to_show = ["Distinctiveness", "Habitats Lost", "# Units", 
                           "Supply Distinctiveness", "Habitats Supplied", "Supply Units", 
                           "Price Per Unit", "Offset Cost"]
            
            st.dataframe(display_table[cols_to_show], use_container_width=True, hide_index=True)
        
        # Email generation
        st.markdown("**📧 Email Generation:**")
        
        # Calculate admin fee based on contract size
        present_sizes = backend.get("Pricing", pd.DataFrame()).get("contract_size", pd.Series()).drop_duplicates().tolist() if backend else []
        total_units = session_demand_df["units_required"].sum() if not session_demand_df.empty else 0.0
        contract_size_val = select_contract_size(total_units, present_sizes) if present_sizes else "Unknown"
        admin_fee_for_email = get_admin_fee_for_contract_size(contract_size_val)
        
        # Create .eml file content
        import base64
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        
        subject = f"RE: BNG Units for site at {location} - {ref_number}"
        total_with_admin = session_total_cost + admin_fee_for_email
        
        # Create email message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = 'quotes@wildcapital.com'  # Replace with your actual email
        msg['To'] = ''  # Will be filled by user
        
        # Create text version for email clients that don't support HTML
        text_body = f"""Dear {client_name}

Our Ref: {ref_number}

Arbtech has advised us that you need Biodiversity Net Gain units for your development in {location}, and we're here to help you discharge your BNG condition.

Thank you for enquiring about BNG Units for your development in {location}

About Us

Wild Capital is a national supplier of BNG Units and environmental mitigation credits (Nutrient Neutrality, SANG), backed by institutional finance.

Your Quote - £{total_with_admin:,.0f} + VAT

[Please view the HTML version of this email for the detailed pricing breakdown table]

Total Units Required: {session_demand_df['units_required'].sum():.2f}
Total Units Supplied: {session_alloc_df['units_supplied'].sum():.2f}
Total Cost: £{total_with_admin:,.0f} + VAT

Next Steps
BNG is a pre-commencement, not a pre-planning, condition.

To accept the quote, let us know—we'll request some basic details before sending the Allocation Agreement. The price is fixed for 30 days, but unit availability is only guaranteed once the agreement is signed.

If you have any questions, please reply to this email or call 01962 436574.

Best regards,
Wild Capital Team"""
        
        # Attach text and HTML versions
        text_part = MIMEText(text_body, 'plain')
        html_part = MIMEText(email_html, 'html')
        
        msg.attach(text_part)
        msg.attach(html_part)
        
        # Convert to string
        eml_content = msg.as_string()
        
        # Download button for .eml file
        st.download_button(
            "📧 Download Email (.eml)",
            data=eml_content,
            file_name=f"BNG_Quote_{ref_number}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.eml",
            mime="message/rfc822",
            help="Download as .eml file - double-click to open in your email client with full HTML formatting"
        )

# Debug section (temporary - can remove later)
if st.checkbox("Show detailed debug info", value=False):
    st.subheader("Debug Information")
    st.write("**Session State Map-Related:**")
    debug_keys = ["target_lat", "target_lon", "target_lpa_name", "target_nca_name", 
                  "map_version", "optimization_complete"]
    for key in debug_keys:
        st.write(f"- {key}: {st.session_state.get(key, 'NOT SET')}")
    
    st.write("**Last Allocation DF:**")
    if "last_alloc_df" in st.session_state:
        if st.session_state["last_alloc_df"] is not None:
            st.write(f"Shape: {st.session_state['last_alloc_df'].shape}")
            st.write("Columns:", list(st.session_state["last_alloc_df"].columns))
        else:
            st.write("None")
    else:
        st.write("Not in session state")
    
    st.write("**Import Status:**")
    st.write(f"- folium imported: {folium is not None}")
    st.write(f"- st_folium imported: {st_folium is not None}")
    st.write(f"- folium_static available: {folium_static is not None}")







































































































































































