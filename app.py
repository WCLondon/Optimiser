"""
app.py — BNG Optimiser (Shiny for Python)

This is a Shiny for Python implementation of the BNG Optimiser.

MIGRATION STATUS:
This scaffold demonstrates the Shiny architecture and reactive patterns.
Full migration would require completing all TODOs marked below.

Key architectural changes from Streamlit:
1. Reactive programming model - computations only re-run when dependencies change
2. Explicit UI/server separation
3. Reactive.Calc for derived values (replaces st.session_state computed values)
4. UI components return immediate values (no widget keys needed)
"""

from shiny import App, ui, render, reactive, req
from shiny.types import ImgData
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime
import os

# Import business logic from core module
from optimiser import core

# Import supporting modules (unchanged from Streamlit version)
import database
import repo  
import metric_reader
import suo

# ================= Configuration =================
ADMIN_FEE_GBP = core.ADMIN_FEE_GBP

# Load environment variables
# In production, these would come from .env file
AUTH_USERNAME = os.getenv("AUTH_USERNAME", "WC0323")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "Wimborne")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "WCAdmin2024")


# ================= UI Definition =================

app_ui = ui.page_navbar(
    ui.nav_panel(
        "Optimiser",
        ui.layout_sidebar(
            ui.sidebar(
                ui.h3("BNG Optimiser"),
                
                # Authentication (simplified - in production use proper auth)
                ui.input_text("username", "Username", value=""),
                ui.input_password("password", "Password"),
                ui.input_action_button("login", "Login", class_="btn-primary"),
                ui.output_text("auth_status"),
                
                ui.hr(),
                
                # Backend loading section
                ui.input_checkbox("use_example_backend", "Use example backend", value=True),
                ui.input_file("backend_file", "Or upload backend Excel", accept=[".xlsx", ".xls"]),
                ui.input_action_button("load_backend", "Load Backend"),
                ui.output_text("backend_status"),
                
                ui.hr(),
                
                # Location input
                ui.h4("Site Location"),
                ui.input_text("postcode", "Postcode", placeholder="e.g., SW1A 1AA"),
                ui.input_text("address", "Or Address", placeholder="e.g., 10 Downing Street"),
                ui.input_action_button("find_location", "Find Location"),
                ui.output_text("location_status"),
                
                # LPA/NCA dropdown alternative
                ui.input_checkbox("use_lpa_nca_dropdown", "Or select LPA/NCA manually"),
                ui.panel_conditional(
                    "input.use_lpa_nca_dropdown",
                    ui.input_select("lpa_dropdown", "Select LPA", choices=[], selected=None),
                    ui.input_select("nca_dropdown", "Select NCA", choices=[], selected=None),
                    ui.input_action_button("apply_lpa_nca", "Apply LPA/NCA"),
                ),
                
                ui.hr(),
                
                # Promoter/Introducer selection
                ui.input_checkbox("use_promoter", "Add Promoter/Introducer"),
                ui.panel_conditional(
                    "input.use_promoter",
                    ui.output_ui("promoter_dropdown_ui"),
                ),
                
                width="300px"
            ),
            
            # Main content area
            ui.navset_tab(
                ui.nav_panel(
                    "Demand Entry",
                    ui.card(
                        ui.card_header("Habitat Demand"),
                        ui.output_ui("demand_rows_ui"),
                        ui.input_action_button("add_demand_row", "➕ Add Row"),
                        ui.input_action_button("clear_demand", "🧹 Clear All"),
                    ),
                    ui.card(
                        ui.card_header("BNG Metric Import"),
                        ui.input_file("metric_file", "Upload BNG Metric Excel", 
                                     accept=[".xlsx", ".xls", ".xlsb"]),
                        ui.input_action_button("import_metric", "Import from Metric"),
                        ui.output_text("metric_import_status"),
                    ),
                ),
                
                ui.nav_panel(
                    "Optimization",
                    ui.card(
                        ui.card_header("Run Optimization"),
                        ui.input_action_button("run_optimize", "🚀 Optimize", class_="btn-success btn-lg"),
                        ui.output_text("optimize_status"),
                    ),
                    ui.card(
                        ui.card_header("Results Summary"),
                        ui.output_text("results_summary"),
                        ui.output_table("allocation_summary"),
                    ),
                    ui.card(
                        ui.card_header("Allocation Details"),
                        ui.output_table("allocation_details"),
                    ),
                ),
                
                ui.nav_panel(
                    "Map & Geography",
                    ui.card(
                        ui.output_ui("map_display"),
                    ),
                ),
                
                ui.nav_panel(
                    "Manual Adjustments",
                    ui.card(
                        ui.card_header("Remove Allocation Rows"),
                        ui.output_ui("remove_rows_ui"),
                    ),
                    ui.card(
                        ui.card_header("Manual Area Habitat Entries"),
                        ui.output_ui("manual_area_ui"),
                        ui.input_action_button("add_manual_area", "➕ Add Area Entry"),
                    ),
                    ui.card(
                        ui.card_header("Manual Hedgerow Entries"),
                        ui.output_ui("manual_hedgerow_ui"),
                        ui.input_action_button("add_manual_hedgerow", "➕ Add Hedgerow Entry"),
                    ),
                    ui.card(
                        ui.card_header("Manual Watercourse Entries"),
                        ui.output_ui("manual_watercourse_ui"),
                        ui.input_action_button("add_manual_watercourse", "➕ Add Watercourse Entry"),
                    ),
                ),
                
                ui.nav_panel(
                    "Client Report",
                    ui.card(
                        ui.card_header("Email Report Generation"),
                        ui.input_text("client_name", "Client Name", value="INSERT NAME"),
                        ui.input_text("ref_number", "Reference Number", value="BNG00XXX"),
                        ui.input_text("site_location", "Site Location", value="INSERT LOCATION"),
                        ui.input_action_button("generate_report", "Generate Report"),
                        ui.download_button("download_email", "📧 Download Email (.eml)"),
                    ),
                    ui.card(
                        ui.card_header("Report Preview"),
                        ui.output_ui("report_preview"),
                    ),
                ),
            ),
        ),
    ),
    
    ui.nav_panel(
        "Quote Management",
        ui.card(
            ui.card_header("Search Quotes"),
            ui.input_text("search_client", "Client Name"),
            ui.input_text("search_ref", "Reference Number"),
            ui.input_action_button("search_quotes", "Search"),
            ui.output_table("quote_results"),
        ),
    ),
    
    ui.nav_panel(
        "Admin Dashboard",
        ui.card(
            ui.card_header("Admin Authentication"),
            ui.input_password("admin_password", "Admin Password"),
            ui.input_action_button("admin_login", "Access Dashboard"),
            ui.output_text("admin_auth_status"),
        ),
        ui.panel_conditional(
            "output.admin_authenticated",
            ui.card(
                ui.card_header("Submissions Database"),
                ui.output_table("admin_submissions"),
                ui.download_button("download_submissions", "📥 Download CSV"),
            ),
            ui.card(
                ui.card_header("Introducer Management"),
                ui.input_text("new_introducer_name", "Introducer Name"),
                ui.input_select("new_discount_type", "Discount Type", 
                              choices=["tier_up", "percentage", "no_discount"]),
                ui.input_numeric("new_discount_value", "Discount Value", value=0, min=0),
                ui.input_action_button("add_introducer", "Add Introducer"),
                ui.output_table("introducers_table"),
            ),
        ),
    ),
    
    title="BNG Optimiser",
    id="main_nav",
)


# ================= Server Logic =================

def server(input, output, session):
    """
    Server function implementing reactive logic.
    
    Key differences from Streamlit:
    - Use reactive.Value() instead of st.session_state for mutable state
    - Use @reactive.Calc for derived/computed values
    - Use req() to guard against invalid states
    - Reactivity is automatic based on dependencies
    """
    
    # ================= Reactive State =================
    # Replace st.session_state with reactive.Value for mutable state
    state = reactive.Value({
        "authenticated": False,
        "admin_authenticated": False,
        "backend": None,
        "backend_loaded": False,
        "target_lpa": None,
        "target_nca": None,
        "target_lat": None,
        "target_lon": None,
        "lpa_neighbors": [],
        "nca_neighbors": [],
        "lpa_geojson": None,
        "nca_geojson": None,
        "demand_rows": [{"id": 1, "habitat_name": "", "units": 0.0}],
        "next_row_id": 2,
        "allocation_result": None,
        "optimization_complete": False,
        "manual_area_rows": [],
        "manual_hedgerow_rows": [],
        "manual_watercourse_rows": [],
        "removed_allocation_ids": [],
        "selected_promoter": None,
        "promoter_discount_type": None,
        "promoter_discount_value": None,
        "suo_enabled": True,
        "suo_results": None,
    })
    
    # Initialize database connection
    try:
        db = database.SubmissionsDB()
    except Exception as e:
        db = None
        print(f"Database initialization failed: {e}")
    
    
    # ================= Authentication =================
    
    @reactive.Effect
    @reactive.event(input.login)
    def handle_login():
        """Handle login button click."""
        if input.username() == AUTH_USERNAME and input.password() == AUTH_PASSWORD:
            current = state()
            current["authenticated"] = True
            state.set(current)
    
    @output
    @render.text
    def auth_status():
        """Display authentication status."""
        if state()["authenticated"]:
            return "✅ Authenticated"
        return "🔐 Please log in"
    
    @reactive.Effect
    @reactive.event(input.admin_login)
    def handle_admin_login():
        """Handle admin login."""
        if input.admin_password() == ADMIN_PASSWORD:
            current = state()
            current["admin_authenticated"] = True
            state.set(current)
    
    @output
    @render.text
    def admin_auth_status():
        """Display admin authentication status."""
        if state()["admin_authenticated"]:
            return "✅ Admin Access Granted"
        return "🔐 Enter admin password"
    
    @output
    @render.text
    def admin_authenticated():
        """Helper for conditional panel."""
        return "true" if state()["admin_authenticated"] else "false"
    
    
    # ================= Backend Loading =================
    
    @reactive.Effect
    @reactive.event(input.load_backend)
    def load_backend():
        """Load backend data (from example or uploaded file)."""
        req(state()["authenticated"])
        
        try:
            # TODO: Implement actual backend loading
            # For now, use repo module to load from database
            current = state()
            
            # Check if backend tables are populated
            tables_status = repo.check_required_tables_not_empty()
            
            if all(tables_status.values()):
                # Load backend from database
                backend_data = {
                    "Banks": repo.fetch_banks(),
                    "Pricing": repo.fetch_pricing(),
                    "HabitatCatalog": repo.fetch_habitat_catalog(),
                    "Stock": repo.fetch_stock(),
                    "DistinctivenessLevels": repo.fetch_distinctiveness_levels(),
                    "SRM": repo.fetch_srm(),
                }
                current["backend"] = backend_data
                current["backend_loaded"] = True
                state.set(current)
            else:
                # Backend not complete in database
                raise ValueError("Backend tables not fully populated in database")
                
        except Exception as e:
            print(f"Backend loading error: {e}")
            # In production, show error to user
    
    @output
    @render.text
    def backend_status():
        """Display backend loading status."""
        if state()["backend_loaded"]:
            backend = state()["backend"]
            if backend:
                return f"✅ Backend loaded ({len(backend.get('Banks', pd.DataFrame()))} banks)"
        return "⚠️ No backend loaded"
    
    
    # ================= Location Finding =================
    
    @reactive.Effect
    @reactive.event(input.find_location)
    def find_location():
        """Find location from postcode or address."""
        req(state()["authenticated"])
        req(state()["backend_loaded"])
        
        postcode = input.postcode().strip()
        address = input.address().strip()
        
        try:
            if postcode:
                lat, lon, admin = core.get_postcode_info(postcode)
            elif address:
                lat, lon = core.geocode_address(address)
            else:
                return
            
            # Get LPA/NCA for point
            lpa_name, lpa_geojson, nca_name, nca_geojson = core.get_catchment_geo_for_point(lat, lon)
            
            # Get neighbors
            if lpa_geojson:
                lpa_neighbors = core.layer_intersect_names(core.LPA_URL, lpa_geojson, "LAD24NM")
                lpa_neighbors = [n for n in lpa_neighbors if n != lpa_name]
            else:
                lpa_neighbors = []
            
            if nca_geojson:
                nca_neighbors = core.layer_intersect_names(core.NCA_URL, nca_geojson, "NCA_Name")
                nca_neighbors = [n for n in nca_neighbors if n != nca_name]
            else:
                nca_neighbors = []
            
            # Update state
            current = state()
            current.update({
                "target_lat": lat,
                "target_lon": lon,
                "target_lpa": lpa_name,
                "target_nca": nca_name,
                "lpa_neighbors": lpa_neighbors,
                "nca_neighbors": nca_neighbors,
                "lpa_geojson": lpa_geojson,
                "nca_geojson": nca_geojson,
            })
            state.set(current)
            
        except Exception as e:
            print(f"Location finding error: {e}")
    
    @output
    @render.text
    def location_status():
        """Display location status."""
        if state()["target_lpa"] and state()["target_nca"]:
            return f"📍 Location: {state()['target_lpa']} (LPA), {state()['target_nca']} (NCA)"
        return "📍 No location set"
    
    
    # ================= Demand Entry =================
    
    @output
    @render.ui
    def demand_rows_ui():
        """Render dynamic demand entry rows."""
        req(state()["backend_loaded"])
        
        backend = state()["backend"]
        catalog = backend.get("HabitatCatalog", pd.DataFrame())
        habitat_choices = sorted(catalog["habitat_name"].dropna().unique().tolist()) if not catalog.empty else []
        
        demand_rows = state()["demand_rows"]
        
        rows_ui = []
        for row in demand_rows:
            row_id = row["id"]
            rows_ui.append(
                ui.layout_columns(
                    ui.input_select(
                        f"habitat_{row_id}",
                        "Habitat",
                        choices=[""] + habitat_choices,
                        selected=row.get("habitat_name", ""),
                    ),
                    ui.input_numeric(
                        f"units_{row_id}",
                        "Units",
                        value=row.get("units", 0.0),
                        min=0,
                        step=0.01,
                    ),
                    ui.input_action_button(
                        f"remove_{row_id}",
                        "❌",
                        class_="btn-sm btn-danger",
                    ),
                    col_widths=[6, 4, 2],
                )
            )
        
        return ui.TagList(*rows_ui)
    
    @reactive.Effect
    @reactive.event(input.add_demand_row)
    def add_demand_row():
        """Add a new demand row."""
        current = state()
        new_id = current["next_row_id"]
        current["demand_rows"].append({"id": new_id, "habitat_name": "", "units": 0.0})
        current["next_row_id"] = new_id + 1
        state.set(current)
    
    @reactive.Effect
    @reactive.event(input.clear_demand)
    def clear_demand():
        """Clear all demand rows."""
        current = state()
        current["demand_rows"] = [{"id": 1, "habitat_name": "", "units": 0.0}]
        current["next_row_id"] = 2
        state.set(current)
    
    # TODO: Add reactive effects to handle removal of individual rows
    # This requires dynamic event handling based on row IDs
    
    
    # ================= Metric Import =================
    
    @reactive.Effect
    @reactive.event(input.import_metric)
    def import_metric():
        """Import demand from BNG metric file."""
        req(input.metric_file())
        req(state()["backend_loaded"])
        
        try:
            # TODO: Implement metric import using metric_reader module
            # metric_file = input.metric_file()[0]
            # demand_data = metric_reader.read_metric_file(metric_file["datapath"])
            # Update state with imported demand
            pass
        except Exception as e:
            print(f"Metric import error: {e}")
    
    @output
    @render.text
    def metric_import_status():
        """Display metric import status."""
        return "Upload a BNG metric file to import demand"
    
    
    # ================= Optimization =================
    
    @reactive.Calc
    def demand_df():
        """
        Reactive calculation: Convert demand rows to DataFrame.
        
        This automatically recomputes whenever demand rows change.
        """
        req(state()["backend_loaded"])
        
        rows = []
        current_state = state()
        for row in current_state["demand_rows"]:
            # Read current values from inputs
            habitat_name = input[f"habitat_{row['id']}"]() if f"habitat_{row['id']}" in input else row.get("habitat_name", "")
            units = input[f"units_{row['id']}"]() if f"units_{row['id']}" in input else row.get("units", 0.0)
            
            if habitat_name and units > 0:
                rows.append({"habitat_name": habitat_name, "units_required": units})
        
        return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["habitat_name", "units_required"])
    
    @reactive.Effect
    @reactive.event(input.run_optimize)
    def run_optimization():
        """Run the optimization algorithm."""
        req(state()["authenticated"])
        req(state()["backend_loaded"])
        req(not demand_df().empty)
        
        try:
            # TODO: Implement full optimization logic
            # This would call the optimization functions from app_streamlit.py
            # For now, placeholder
            
            current = state()
            current["optimization_complete"] = True
            # current["allocation_result"] = allocation_df
            state.set(current)
            
        except Exception as e:
            print(f"Optimization error: {e}")
    
    @output
    @render.text
    def optimize_status():
        """Display optimization status."""
        if state()["optimization_complete"]:
            return "✅ Optimization complete"
        return "Click 'Optimize' to run allocation"
    
    @output
    @render.text
    def results_summary():
        """Display results summary."""
        if not state()["optimization_complete"]:
            return "No optimization results yet"
        
        # TODO: Calculate summary from allocation results
        return "Results summary placeholder"
    
    @output
    @render.table
    def allocation_summary():
        """Display allocation summary table."""
        if not state()["optimization_complete"]:
            return pd.DataFrame()
        
        # TODO: Generate summary table from results
        return pd.DataFrame()
    
    @output
    @render.table
    def allocation_details():
        """Display detailed allocation table."""
        if not state()["optimization_complete"]:
            return pd.DataFrame()
        
        # TODO: Return full allocation details
        return pd.DataFrame()
    
    
    # ================= Map Display =================
    
    @output
    @render.ui
    def map_display():
        """Display interactive map."""
        if not state()["target_lat"] or not state()["target_lon"]:
            return ui.div("Set a location to view map", class_="text-muted")
        
        # TODO: Implement map rendering
        # Options:
        # 1. Use Folium and embed HTML: ui.HTML(folium_map._repr_html_())
        # 2. Use Plotly for interactive maps
        # 3. Use leaflet via shinywidgets
        
        return ui.div("Map placeholder - implement with Folium or Plotly", class_="text-muted")
    
    
    # ================= Manual Adjustments =================
    
    @output
    @render.ui
    def remove_rows_ui():
        """UI for removing allocation rows."""
        if not state()["optimization_complete"]:
            return ui.div("Run optimization first", class_="text-muted")
        
        # TODO: Show allocation rows with remove buttons
        return ui.div("Allocation rows with remove buttons", class_="text-muted")
    
    @output
    @render.ui
    def manual_area_ui():
        """UI for manual area habitat entries."""
        if not state()["optimization_complete"]:
            return ui.div("Run optimization first", class_="text-muted")
        
        # TODO: Render manual area entry rows
        return ui.div("Manual area entries", class_="text-muted")
    
    @output
    @render.ui
    def manual_hedgerow_ui():
        """UI for manual hedgerow entries."""
        if not state()["optimization_complete"]:
            return ui.div("Run optimization first", class_="text-muted")
        
        # TODO: Render manual hedgerow rows
        return ui.div("Manual hedgerow entries", class_="text-muted")
    
    @output
    @render.ui
    def manual_watercourse_ui():
        """UI for manual watercourse entries."""
        if not state()["optimization_complete"]:
            return ui.div("Run optimization first", class_="text-muted")
        
        # TODO: Render manual watercourse rows
        return ui.div("Manual watercourse entries", class_="text-muted")
    
    
    # ================= Client Report =================
    
    @output
    @render.ui
    def report_preview():
        """Preview client report."""
        if not state()["optimization_complete"]:
            return ui.div("Complete optimization first", class_="text-muted")
        
        # TODO: Generate report preview
        return ui.div("Report preview", class_="text-muted")
    
    @session.download(filename="BNG_Quote.eml")
    def download_email():
        """Generate and download email file."""
        req(state()["optimization_complete"])
        
        # TODO: Generate email content
        yield "Email content placeholder"
    
    
    # ================= Quote Management =================
    
    @reactive.Effect
    @reactive.event(input.search_quotes)
    def search_quotes():
        """Search quotes in database."""
        req(state()["authenticated"])
        req(db is not None)
        
        # TODO: Implement quote search
        pass
    
    @output
    @render.table
    def quote_results():
        """Display quote search results."""
        # TODO: Show search results
        return pd.DataFrame()
    
    
    # ================= Admin Dashboard =================
    
    @output
    @render.table
    def admin_submissions():
        """Display submissions in admin dashboard."""
        req(state()["admin_authenticated"])
        req(db is not None)
        
        try:
            df = db.get_all_submissions(limit=100)
            return df
        except Exception as e:
            print(f"Error loading submissions: {e}")
            return pd.DataFrame()
    
    @session.download(filename=f"submissions_{datetime.now().strftime('%Y%m%d')}.csv")
    def download_submissions():
        """Download submissions as CSV."""
        req(state()["admin_authenticated"])
        req(db is not None)
        
        df = db.get_all_submissions(limit=1000)
        yield df.to_csv(index=False)
    
    @output
    @render.table
    def introducers_table():
        """Display introducers table."""
        req(state()["admin_authenticated"])
        req(db is not None)
        
        try:
            introducers = db.get_all_introducers()
            return pd.DataFrame(introducers) if introducers else pd.DataFrame()
        except Exception:
            return pd.DataFrame()
    
    @output
    @render.ui
    def promoter_dropdown_ui():
        """Render promoter dropdown dynamically."""
        req(state()["backend_loaded"])
        req(db is not None)
        
        try:
            introducers = db.get_all_introducers()
            choices = {intro["name"]: intro["name"] for intro in introducers}
            return ui.input_select("promoter", "Select Promoter", choices=choices)
        except Exception:
            return ui.div("No promoters available", class_="text-muted")


# ================= Create App =================

app = App(app_ui, server)


# ================= Development Note =================

"""
TODO LIST FOR COMPLETE MIGRATION:

1. Backend Loading:
   - [ ] Implement full backend loading from Excel files
   - [ ] Add caching for backend data
   - [ ] Handle backend validation

2. Location & Geography:
   - [ ] Complete LPA/NCA dropdown population
   - [ ] Implement map rendering (Folium HTML or Plotly)
   - [ ] Add bank location markers
   - [ ] Show catchment areas

3. Demand Entry:
   - [ ] Complete dynamic row addition/removal
   - [ ] Add validation for habitat names
   - [ ] Implement drag-and-drop reordering

4. Metric Import:
   - [ ] Integrate metric_reader module
   - [ ] Handle .xlsb files
   - [ ] Parse A1, B1, C1 sheets
   - [ ] Extract demand requirements

5. Optimization:
   - [ ] Port full optimization algorithm from app_streamlit.py
   - [ ] Implement PuLP solver integration
   - [ ] Add greedy fallback algorithm
   - [ ] Handle paired allocations (Orchard, etc.)
   - [ ] Apply trading rules
   - [ ] Calculate tiers (local/adjacent/far)
   - [ ] Apply SRM multipliers
   - [ ] Handle stock constraints

6. Results Display:
   - [ ] Show allocation table with sorting/filtering
   - [ ] Display summary metrics
   - [ ] Show by-bank breakdown
   - [ ] Show by-habitat breakdown
   - [ ] Highlight proxy pricing

7. Manual Adjustments:
   - [ ] Implement row removal from allocations
   - [ ] Add manual area habitat entries (simple and paired)
   - [ ] Add manual hedgerow entries
   - [ ] Add manual watercourse entries
   - [ ] Recalculate totals dynamically

8. SUO (Surplus Uplift Offset):
   - [ ] Integrate suo module
   - [ ] Calculate eligible surplus
   - [ ] Apply discount checkbox
   - [ ] Show before/after costs

9. Promoter Discounts:
   - [ ] Apply tier-up discounts
   - [ ] Apply percentage discounts
   - [ ] Show discount in final price

10. Client Report:
    - [ ] Generate email HTML with table
    - [ ] Format prices correctly
    - [ ] Include all manual entries
    - [ ] Create .eml file download
    - [ ] Add customer info form
    - [ ] Link to customer database

11. Quote Management:
    - [ ] Implement quote search
    - [ ] Show quote details
    - [ ] Load quote for editing
    - [ ] Handle requotes

12. Admin Dashboard:
    - [ ] Complete submissions table
    - [ ] Add filtering controls
    - [ ] Implement introducer CRUD
    - [ ] Add customer management
    - [ ] Export functionality

13. Database Integration:
    - [ ] Store submissions on report generation
    - [ ] Link customers
    - [ ] Track introducers
    - [ ] Save allocations

14. Performance:
    - [ ] Add @lru_cache to expensive pure functions
    - [ ] Implement reactive caching where appropriate
    - [ ] Optimize database queries
    - [ ] Add loading indicators

15. Testing:
    - [ ] Create tests/test_core.py
    - [ ] Add integration tests
    - [ ] Test reactive dependencies
    - [ ] Validate business logic

16. Documentation:
    - [ ] Update README with Shiny-specific instructions
    - [ ] Document reactive patterns
    - [ ] Add architecture diagrams
    - [ ] Create developer guide

ESTIMATED EFFORT:
- Core migration: 80-100 hours
- Testing: 20-30 hours
- Documentation: 10-15 hours
- Total: 110-145 hours (3-4 weeks full-time)

PRIORITY ORDER:
1. Authentication & backend loading
2. Location finding & demand entry
3. Optimization algorithm
4. Results display
5. Manual adjustments
6. Report generation
7. Database integration
8. Admin features
9. Quote management
10. Polish & optimization
"""
