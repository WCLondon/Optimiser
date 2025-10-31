# Shiny Migration - Quick Reference

## Quick Start

```bash
# 1. Switch to migration branch
git checkout feature/shiny-migration

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env and set DATABASE_URL

# 4. Run the application
shiny run --reload app.py
# Or: make run

# 5. Access at http://localhost:8000
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific tests
pytest tests/test_core.py -v

# With coverage
pytest tests/ --cov=optimiser
```

## Current Status (30% Complete)

### ✅ What Works
- Project structure and dependencies
- Core business logic extraction (600 lines)
- Shiny app scaffold (1000 lines)
- Authentication flow
- Backend loading structure
- Database modules (no Streamlit dependencies)
- 14 unit tests (all passing)

### 🚧 What's In Progress (TODO)
- Optimization algorithm (needs extraction from app_streamlit.py)
- Dynamic demand entry
- Map rendering
- Manual adjustments
- Client report generation
- Quote management
- Admin features

### 📊 Estimated Remaining Effort
- **Core functionality:** 50 hours
- **Database & features:** 8 hours
- **Testing & polish:** 35 hours
- **Total:** ~90 hours (3-4 weeks)

## Architecture

### File Structure
```
optimiser/
├── __init__.py
└── core.py              # Business logic (600 lines)
app.py                   # Shiny UI (1000 lines)
app_streamlit.py         # Original app (reference)
db.py                    # Database (no Streamlit)
repo.py                  # Data access (no Streamlit)
tests/
├── __init__.py
└── test_core.py         # Unit tests (14 tests)
```

### Key Patterns

**Reactive State:**
```python
# Instead of st.session_state
state = reactive.Value({"counter": 0})

@reactive.Effect
def update():
    current = state()
    current["counter"] += 1
    state.set(current)
```

**Computed Values:**
```python
# Automatically recomputes when dependencies change
@reactive.Calc
def total():
    return sum(state()["items"])
```

**Renders:**
```python
@output
@render.table
def results_table():
    return my_dataframe()
```

## Documentation

- **Migration Status:** `MIGRATION_STATUS.md` (technical details)
- **Implementation Summary:** `IMPLEMENTATION_SUMMARY_SHINY_MIGRATION.md` (executive summary)
- **Original App:** `app_streamlit.py` (preserved for reference)

## Streamlit → Shiny Mapping

| Streamlit | Shiny |
|-----------|-------|
| `st.text_input()` | `ui.input_text()` |
| `st.number_input()` | `ui.input_numeric()` |
| `st.selectbox()` | `ui.input_select()` |
| `st.multiselect()` | `ui.input_select(multiple=True)` |
| `st.checkbox()` | `ui.input_checkbox()` |
| `st.button()` | `ui.input_action_button()` |
| `st.dataframe()` | `@render.table + ui.output_table()` |
| `st.session_state` | `reactive.Value()` |
| `@st.cache_data` | `@lru_cache` or `@reactive.Calc` |

## Common Tasks

### Add a New Feature

1. **Extract business logic to `core.py`:**
```python
def my_calculation(input_data):
    # Pure function, no UI dependencies
    return result
```

2. **Add UI in `app.py`:**
```python
# In app_ui:
ui.input_text("my_input", "Label"),

# In server:
@reactive.Calc
def my_result():
    return my_calculation(input.my_input())

@output
@render.text
def my_output():
    return str(my_result())
```

3. **Add test:**
```python
def test_my_calculation():
    assert my_calculation(test_data) == expected
```

### Debug Reactivity

```python
# Add print statements to track execution
@reactive.Calc
def my_calc():
    print(f"my_calc running with: {input.value()}")
    return compute()

# Check reactive dependencies
@reactive.Calc
def dependent():
    # This will rerun whenever my_calc() changes
    return my_calc() * 2
```

### Handle Errors

```python
@reactive.Calc
def safe_calc():
    try:
        return risky_operation()
    except Exception as e:
        print(f"Error: {e}")
        return None

@output
@render.text
def display():
    result = safe_calc()
    if result is None:
        return "Error occurred"
    return str(result)
```

## Performance Tips

1. **Use `@lru_cache` for expensive pure functions:**
```python
@lru_cache(maxsize=128)
def expensive_api_call(param):
    return fetch_from_api(param)
```

2. **Use `@reactive.Calc` for derived values:**
```python
# BAD: Recomputes every time
@output
@render.text
def total():
    return str(sum(get_data()))

# GOOD: Only recomputes when dependencies change
@reactive.Calc
def calculated_total():
    return sum(get_data())

@output
@render.text
def total():
    return str(calculated_total())
```

3. **Guard expensive operations with `req()`:**
```python
@reactive.Calc
def expensive_calc():
    req(input.ready())  # Don't run until ready
    return expensive_operation()
```

## Troubleshooting

### Import Error: No module named 'shiny'
```bash
pip install shiny>=0.7
```

### Database Connection Error
```bash
# Check .env file
cat .env
# Should have: DATABASE_URL=postgresql://...

# Test connection
python -c "from db import DatabaseConnection; print(DatabaseConnection.db_healthcheck())"
```

### Tests Failing
```bash
# Run with verbose output
pytest tests/ -v -s

# Run specific test
pytest tests/test_core.py::test_function_name -v
```

### Reactivity Not Working
- Check if `@reactive.Calc` depends on reactive inputs
- Ensure you're calling reactive values with `()`
- Use `print()` to trace execution

## Next Steps for Contributors

### High Priority (Essential for MVP)
1. Extract optimization algorithm from `app_streamlit.py`
2. Implement dynamic demand entry
3. Wire up optimization flow

### Medium Priority (Important Features)
1. Map rendering (Folium or Plotly)
2. Manual adjustments
3. Client report generation

### Low Priority (Nice to Have)
1. Advanced admin features
2. Performance optimizations
3. UI polish

## Getting Help

1. **Check documentation:**
   - `MIGRATION_STATUS.md` for technical details
   - `IMPLEMENTATION_SUMMARY_SHINY_MIGRATION.md` for overview
   
2. **Review TODOs:**
   - Search for `TODO` in `app.py`
   - Each marks an incomplete feature

3. **Ask the team:**
   - For architecture questions
   - For business logic clarification
   - For deployment planning

## Contributing

When adding features:

1. ✅ Extract business logic to `optimiser/core.py`
2. ✅ Keep functions pure and testable
3. ✅ Add unit tests to `tests/`
4. ✅ Update documentation
5. ✅ Mark TODOs when incomplete
6. ✅ Run tests before committing

## Resources

- **Shiny for Python Docs:** https://shiny.posit.co/py/
- **Shiny Gallery:** https://shiny.posit.co/py/gallery/
- **Original Streamlit App:** `app_streamlit.py`
