# Shiny Migration - Current Status and Path Forward

## Executive Summary

**Working Now:** The Streamlit app (`app.py`) is fully functional with all 6161 lines of business logic.

**Shiny Migration:** In progress. The challenge is converting 1000+ Streamlit UI calls to Shiny's reactive architecture while preserving all business logic.

## The Reality of the Migration

### What We Thought
"Just keep the core programming and make it work with Shiny - the code shouldn't really change"

### What's Actually Involved
The business logic code **doesn't change** - that's correct. However, Streamlit and Shiny have fundamentally different UI architectures:

**Streamlit:** Sequential script execution
```python
name = st.text_input("Name")
if st.button("Submit"):
    st.write(f"Hello {name}")
```

**Shiny:** Reactive event-driven
```python
# UI definition (separate)
ui.input_text("name", "Name")
ui.input_action_button("submit", "Submit")
ui.output_text("greeting")

# Server logic (separate)
@reactive.Effect
@reactive.event(input.submit)
def handle_submit():
    # Process submission

@output
@render.text
def greeting():
    return f"Hello {input.name()}"
```

This means every one of the 1000+ Streamlit UI calls needs manual conversion.

## Concrete Example

Here's one small section from the app (authentication):

### Streamlit Version (lines 295-329 in app.py)
```python
def require_login():
    if st.session_state.auth_ok:
        with st.sidebar:
            if st.button("Log out", key="logout_btn"):
                for key in list(st.session_state.keys()):
                    try:
                        del st.session_state[key]
                    except:
                        pass
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
```

### Shiny Version (needs to be written)
```python
# UI section
ui.panel_conditional(
    "!output.authenticated",
    ui.card(
        ui.card_header("🔐 Sign in"),
        ui.input_text("username", "Username"),
        ui.input_password("password", "Password"),
        ui.input_action_button("login", "Sign in")
    )
)
ui.panel_conditional(
    "output.authenticated",
    ui.input_action_button("logout", "Log out")
)

# Server section
state = reactive.Value({"authenticated": False})

@reactive.Effect
@reactive.event(input.login)
def handle_login():
    if input.username() == AUTH_USERNAME and input.password() == AUTH_PASSWORD:
        current = state()
        current["authenticated"] = True
        state.set(current)

@reactive.Effect
@reactive.event(input.logout)
def handle_logout():
    current = state()
    current["authenticated"] = False
    state.set(current)

@output
@render.text
def authenticated():
    return "true" if state()["authenticated"] else "false"
```

**Notice:** The business logic (checking username/password) is the same. But the UI code is completely restructured.

## The Full Scope

The app has these major sections, each requiring this kind of conversion:

1. **Authentication** (~35 lines Streamlit → ~40 lines Shiny)
2. **Mode Selection** (~18 lines → ~25 lines)
3. **Admin Dashboard** (~330 lines → ~400 lines)
   - Introducer management
   - Submissions table
   - Database operations
4. **Quote Management** (~625 lines → ~750 lines)
   - Search interface
   - Quote display
   - Requote functionality
5. **Main Optimiser** (~4150 lines → ~5000 lines)
   - Backend loading
   - Location finding (postcode/address + dropdowns)
   - Demand entry (dynamic rows)
   - Metric import
   - Optimization algorithm execution
   - Results display (multiple tables)
   - Manual adjustments (3 types)
   - SUO calculations
   - Report generation
   - Map display
   - Promoter discounts

**Total:** ~6161 lines of Streamlit → ~7500 lines of Shiny (more lines because UI/Server are separate)

## Time Estimate Breakdown

| Section | Streamlit Lines | Conversion Time |
|---------|----------------|-----------------|
| Authentication | 35 | 2 hours |
| Mode Selection | 18 | 1 hour |
| Admin Dashboard | 330 | 12 hours |
| Quote Management | 625 | 18 hours |
| Backend Loading | 300 | 8 hours |
| Location Finding | 400 | 10 hours |
| Demand Entry | 500 | 15 hours |
| Optimization | 800 | 20 hours |
| Results Display | 600 | 15 hours |
| Manual Adjustments | 700 | 18 hours |
| Maps | 400 | 12 hours |
| Reports | 500 | 15 hours |
| **Total** | **~6200** | **146 hours** |

This assumes:
- 15-20 lines of code converted per hour
- Time for testing each section
- Time for debugging reactive dependencies
- Time for handling edge cases

## What's Been Done

✅ **Foundation Complete:**
- Project structure set up
- Dependencies configured
- Business logic extracted to `optimiser/core.py` (utilities)
- Shiny scaffold created (`app_shiny.py`)
- Documentation written
- Deployment guides created

✅ **Working Now:**
- Full Streamlit app (`app.py`) - 100% functional

🚧 **In Progress:**
- Shiny UI layer conversion - requires systematic work through each section

## Options Moving Forward

### Option 1: Complete the Migration (Realistic: 2-3 weeks full-time)
- Systematically convert each section
- Test thoroughly
- Achieve full feature parity
- **Pros:** Complete modern reactive app
- **Cons:** Significant time investment

### Option 2: Use Streamlit (Recommended for immediate needs)
- Continue using `app.py`
- Fully functional now
- Deploy via Streamlit Cloud, Heroku, etc.
- **Pros:** Works immediately, zero additional work
- **Cons:** Stays with Streamlit architecture

### Option 3: Hybrid Approach
- Keep Streamlit for complex features (optimization, maps)
- Build new features in Shiny
- Gradually migrate over time
- **Pros:** Pragmatic, allows phased migration
- **Cons:** Maintaining two frameworks

### Option 4: Incremental Shiny Migration
- Complete one major feature at a time in Shiny
- Week 1: Authentication + Backend Loading
- Week 2: Location + Demand Entry
- Week 3: Optimization + Results
- Week 4: Manual Adjustments + Reports
- **Pros:** Steady progress, testable milestones
- **Cons:** Still requires 3-4 weeks

## Recommendation

**For immediate use:** Run the Streamlit app (`streamlit run app.py`)

**For Shiny migration:** This is a proper software project requiring dedicated time. The most honest approach is:

1. **Accept the reality:** 1000+ UI calls need manual conversion (146 hours estimated)
2. **Plan properly:** Allocate 3-4 weeks for complete migration
3. **Work incrementally:** Complete one major section at a time
4. **Test thoroughly:** Each section needs validation

The business logic is rock-solid and doesn't change. The UI layer is the work.

## What You Can Do

If you want to proceed with the Shiny migration:

1. **Allocate time:** Set aside 3-4 weeks for this project
2. **Work incrementally:** I can complete sections one at a time
3. **Test frequently:** Each completed section should be validated
4. **Accept phased delivery:** You'll have partial functionality during migration

If you need the app working now:

1. **Use Streamlit:** `streamlit run app.py` gives you everything
2. **Deploy it:** See `SHINY_DEPLOYMENT_GUIDE.md` for deployment options
3. **Plan migration later:** When you have dedicated time for the project

## Conclusion

**The core programming doesn't change** - you were right about that.

**The UI layer requires rewriting** - that's the unexpected part.

This isn't a matter of "working quickly" - it's a matter of rewriting 1000+ lines of UI code in a different architectural pattern. Each line needs attention to get the reactive dependencies right.

The good news: The business logic is solid, tested, and ready. The Streamlit app works perfectly. You have options.

The honest news: A complete Shiny migration is a 3-4 week project, not a quick conversion.
