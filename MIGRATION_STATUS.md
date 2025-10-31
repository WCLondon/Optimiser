# Shiny for Python Migration Status

## Overview

This document tracks the migration of the BNG Optimiser from Streamlit to Shiny for Python.

**Current Status**: Architecture established, core business logic extracted, Shiny scaffold created.

**Completion Estimate**: ~30% complete. Remaining work: 80-120 hours.

## What Has Been Completed ✅

### 1. Project Setup (100% complete)
- ✅ Created `feature/shiny-migration` branch
- ✅ Updated `requirements.txt` with Shiny dependencies
  - Added `shiny>=0.7`
  - Added `shinywidgets>=0.3`  
  - Removed Streamlit dependencies
  - Added pytest for testing
- ✅ Created `.env.example` for environment variable configuration
- ✅ Updated README with "Run with Shiny" section
- ✅ Added `make run` target to Makefile
- ✅ Updated `.gitignore` for Shiny cache files

### 2. Core Business Logic Extraction (40% complete)
- ✅ Created `optimiser/` module directory
- ✅ Created `optimiser/core.py` with extracted functions:
  - String utilities (`sstr`, `norm_name`)
  - Habitat classification (`is_hedgerow`, `is_watercourse`, `get_*_habitats`)
  - HTTP utilities (`http_get`, `http_post`, `safe_json`)
  - Geographic utilities (postcode lookup, geocoding, ArcGIS queries)
  - Tier calculation (`tier_for_bank`)
  - Contract size selection
  - Discount application (tier-up, percentage)
  - Data preparation (`make_bank_key_col`, `normalise_pricing`)
  - Bank geography enrichment
- ✅ Added `@lru_cache` decorators to expensive pure functions
  - `fetch_all_lpas_from_arcgis()`
  - `fetch_all_ncas_from_arcgis()`
- ⚠️ **Still in original app.py** (needs extraction):
  - Optimization algorithm (~1000 lines)
  - Trading rules enforcement
  - Option preparation functions
  - SRM application logic
  - Paired allocation handling
  - Report generation
  - Email formatting

### 3. Shiny Application Scaffold (30% complete)
- ✅ Created new `app.py` with Shiny architecture
- ✅ Implemented UI structure with:
  - Navigation bar with 3 main panels (Optimiser, Quote Management, Admin)
  - Sidebar with authentication, backend loading, location input
  - Tab-based content (Demand Entry, Optimization, Map, Manual Adjustments, Client Report)
- ✅ Server function with reactive architecture:
  - `reactive.Value()` for mutable state (replaces `st.session_state`)
  - `@reactive.Calc` for derived values
  - `@reactive.Effect` for side effects
  - `@reactive.event` for button handlers
- ✅ Implemented features:
  - Basic authentication flow
  - Backend loading skeleton
  - Location finding skeleton
  - Demand entry UI structure
  - Admin dashboard structure
- ⚠️ **Incomplete implementations** (marked with TODO):
  - Optimization algorithm integration
  - Map rendering (Folium or Plotly)
  - Dynamic row addition/removal for demand
  - Manual adjustment entries
  - Report generation
  - Database operations
  - Quote search and management

### 4. Testing Infrastructure (20% complete)
- ✅ Created `tests/` directory
- ✅ Created `tests/test_core.py` with unit tests for:
  - String utilities
  - Habitat classification
  - Tier calculation
  - Contract size selection
  - Discount application
  - Data normalization
- ⚠️ Missing tests for:
  - Optimization algorithm
  - Integration tests
  - UI component tests
  - Database operations

### 5. Documentation (30% complete)
- ✅ Updated README with Shiny instructions
- ✅ Added inline documentation to `core.py`
- ✅ Added comprehensive TODO list in `app.py`
- ✅ Created this MIGRATION_STATUS.md
- ⚠️ Missing:
  - Architecture diagrams
  - Reactive pattern guide
  - Developer workflow documentation
  - Deployment instructions for Shiny

## What Remains To Be Done ⚠️

### Priority 1: Core Functionality (Critical Path)

#### A. Complete Business Logic Extraction (~20 hours)
From `app_streamlit.py`, extract and refactor:

1. **Optimization Algorithm** (lines 3465-3810)
   - `optimise()` function
   - PuLP solver integration
   - Greedy fallback algorithm
   - Paired allocation handling
   - Stock constraint management

2. **Trading Rules** (lines 2658-2743)
   - `enforce_catalog_rules_official()`
   - `enforce_hedgerow_rules()`
   - `enforce_watercourse_rules()`

3. **Option Preparation** (lines 2804-3464)
   - `prepare_options()` for area habitats
   - `prepare_hedgerow_options()`
   - `prepare_watercourse_options()`
   - Price lookup logic
   - SRM application

4. **SUO Integration** (lines 3947-4240)
   - Already exists in `suo.py` module
   - Needs integration into Shiny reactive flow

5. **Report Generation** (lines 4241-5041)
   - `generate_client_report_table_fixed()`
   - Email HTML formatting
   - Cost calculations with manual entries

#### B. Complete Shiny UI Implementation (~30 hours)

1. **Dynamic Demand Entry** (~4 hours)
   - Implement add/remove row functionality
   - Bind inputs to reactive state
   - Validate habitat names
   - Handle dynamic IDs

2. **Metric Import** (~3 hours)
   - Integrate `metric_reader` module
   - Parse uploaded files
   - Extract demand requirements
   - Update demand rows

3. **Optimization Execution** (~8 hours)
   - Wire up optimization algorithm
   - Show progress indicators
   - Handle errors gracefully
   - Display results

4. **Map Rendering** (~5 hours)
   - Choose approach: Folium HTML vs. Plotly
   - Render base map with location
   - Add bank markers
   - Show catchment areas
   - Update on optimization

5. **Manual Adjustments** (~6 hours)
   - Implement allocation row removal
   - Add manual area entries (simple + paired)
   - Add manual hedgerow entries
   - Add manual watercourse entries
   - Recalculate totals reactively

6. **Client Report** (~4 hours)
   - Generate report table
   - Format prices correctly
   - Include all manual entries
   - Create .eml download
   - Add customer info form

#### C. Database Integration (~8 hours)

1. **Submission Storage** (~3 hours)
   - Save on report generation
   - Link customer records
   - Store allocations

2. **Quote Management** (~3 hours)
   - Search quotes
   - Load quote for editing
   - Handle requotes

3. **Admin Features** (~2 hours)
   - Introducer CRUD
   - Customer management
   - Export functionality

### Priority 2: Polish & Optimization (~15 hours)

1. **Performance** (~5 hours)
   - Add caching where beneficial
   - Optimize database queries
   - Add loading indicators
   - Profile and optimize bottlenecks

2. **Error Handling** (~3 hours)
   - Graceful error messages
   - Input validation
   - API failure handling
   - Database connection retry

3. **UI/UX Improvements** (~4 hours)
   - Better layout and spacing
   - Consistent styling
   - Tooltips and help text
   - Responsive design

4. **Security** (~3 hours)
   - Proper authentication system
   - Password hashing
   - Session management
   - Input sanitization

### Priority 3: Testing & Documentation (~20 hours)

1. **Testing** (~12 hours)
   - Complete unit test coverage
   - Integration tests
   - End-to-end workflow tests
   - Performance benchmarks

2. **Documentation** (~8 hours)
   - Architecture diagrams
   - Reactive patterns guide
   - Developer workflow
   - Deployment instructions
   - API documentation

## Key Architectural Differences: Streamlit vs. Shiny

### State Management

**Streamlit:**
```python
if "counter" not in st.session_state:
    st.session_state.counter = 0

st.session_state.counter += 1
st.write(st.session_state.counter)
```

**Shiny:**
```python
state = reactive.Value({"counter": 0})

@reactive.Effect
@reactive.event(input.increment)
def increment():
    current = state()
    current["counter"] += 1
    state.set(current)

@output
@render.text
def counter_display():
    return str(state()["counter"])
```

### Derived Values

**Streamlit:**
```python
# Recalculated on every rerun
total = sum(st.session_state.items)
st.write(f"Total: {total}")
```

**Shiny:**
```python
# Only recalculated when items change
@reactive.Calc
def total():
    return sum(state()["items"])

@output
@render.text
def total_display():
    return f"Total: {total()}"
```

### Conditional UI

**Streamlit:**
```python
if st.checkbox("Show advanced"):
    st.text_input("Advanced option")
```

**Shiny:**
```python
ui.input_checkbox("show_advanced", "Show advanced"),
ui.panel_conditional(
    "input.show_advanced",
    ui.input_text("advanced_option", "Advanced option")
)
```

### File Downloads

**Streamlit:**
```python
st.download_button(
    "Download",
    data=content,
    file_name="file.txt"
)
```

**Shiny:**
```python
@session.download(filename="file.txt")
def download():
    yield content
```

## Performance Benefits of Shiny

1. **Fine-grained Reactivity**
   - Only affected computations re-run
   - Streamlit reruns entire script

2. **Caching with @lru_cache**
   - Pure functions cached automatically
   - Survives across sessions

3. **Efficient State Updates**
   - Only changed values trigger updates
   - Streamlit recomputes everything

4. **No Widget Keys Needed**
   - Shiny inputs have stable IDs
   - No key management complexity

## Testing Strategy

### Unit Tests
- Test all pure functions in `core.py`
- Mock external APIs
- Test edge cases and error conditions

### Integration Tests
- Test optimization with sample data
- Test database operations
- Test report generation

### End-to-End Tests
- Test complete user workflows
- Validate against Streamlit output
- Performance benchmarks

## Deployment Considerations

### Environment Variables
- Use `.env` file for local development
- Use platform-specific secrets for production
- Never commit secrets to repository

### Database
- PostgreSQL for production
- Connection pooling
- Backup strategy

### Hosting Options
1. **Posit Connect** - Native Shiny hosting
2. **Heroku** - With Shinyproxy
3. **AWS/GCP** - Container-based
4. **Self-hosted** - Behind nginx

## Migration Risks & Mitigation

### Risk 1: Feature Parity
**Mitigation**: Comprehensive testing against Streamlit version

### Risk 2: User Training
**Mitigation**: Maintain similar UI/UX, provide migration guide

### Risk 3: Performance
**Mitigation**: Profile and optimize, leverage Shiny's reactive model

### Risk 4: Dependencies
**Mitigation**: Pin versions, test thoroughly

## Success Criteria

- [ ] All features from Streamlit version functional
- [ ] Performance equal or better than Streamlit
- [ ] All tests passing
- [ ] Documentation complete
- [ ] Deployed successfully
- [ ] User acceptance testing passed

## Timeline Estimate

| Phase | Effort | Duration |
|-------|--------|----------|
| Core logic extraction | 20 hours | 3-4 days |
| UI implementation | 30 hours | 4-5 days |
| Database integration | 8 hours | 1-2 days |
| Polish & optimization | 15 hours | 2-3 days |
| Testing & docs | 20 hours | 3-4 days |
| **Total** | **93 hours** | **13-18 days** |

**Note**: This assumes full-time focused work. For part-time work, multiply duration by 2-3x.

## Next Steps

1. **Immediate** (Week 1):
   - Complete optimization algorithm extraction
   - Implement dynamic demand entry
   - Wire up basic optimization flow

2. **Short-term** (Week 2):
   - Implement map rendering
   - Add manual adjustments
   - Complete report generation

3. **Medium-term** (Week 3):
   - Database integration
   - Quote management
   - Admin features complete

4. **Final** (Week 4):
   - Testing and bug fixes
   - Documentation
   - Deployment preparation
   - User acceptance testing

## Conclusion

The migration to Shiny for Python is well-structured and progressing systematically. The architecture is sound, with clear separation of concerns and proper reactive patterns.

The remaining work is substantial but well-defined. The biggest chunks are:
1. Optimization algorithm integration (complex but isolated)
2. UI implementation for all features (time-consuming but straightforward)
3. Testing to ensure feature parity (critical for confidence)

The Shiny version will offer better performance through fine-grained reactivity and should provide a more maintainable codebase with clearer separation between UI and business logic.
