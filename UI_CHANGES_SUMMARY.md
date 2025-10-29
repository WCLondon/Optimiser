# UI Changes Summary - BNG Metric Import Feature

## Location in App
The new feature is located in **Section 2: Demand (units required)**, just before the manual habitat entry interface.

## Visual Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│ 2) Demand (units required)                                   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ 📄 Import from BNG Metric File              [Expand ▼]│   │
│ └───────────────────────────────────────────────────────┘   │
│                                                               │
│ When expanded:                                                │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ Upload a DEFRA BNG metric file (.xlsx, .xlsm, or      │   │
│ │ .xlsb) to automatically populate requirements.        │   │
│ │                                                        │   │
│ │ [Browse files]  Or drag and drop                      │   │
│ │                                                        │   │
│ │ ✅ Metric parsed successfully!                         │   │
│ │    Found: 2 area habitats, 1 hedgerow, 0 watercourse │   │
│ │                                                        │   │
│ │ ┌─ Preview: Area Habitats ─────────────────┐         │   │
│ │ │ habitat          │ units                  │         │   │
│ │ │ Grassland        │ 5.23                   │         │   │
│ │ │ Woodland         │ 3.45                   │         │   │
│ │ └────────────────────────────────────────────┘        │   │
│ │                                                        │   │
│ │ [➕ Add to Demand Rows]  [Clear & Import]             │   │
│ └───────────────────────────────────────────────────────┘   │
│                                                               │
│ ───────────────────────────────────────────────────────────  │
│                                                               │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ Add habitats one by one (type to search the catalog): │   │
│ │                                                        │   │
│ │ [Habitat dropdown ▼]  [Units: 0.00]  [🗑️]             │   │
│ │ [Habitat dropdown ▼]  [Units: 0.00]  [🗑️]             │   │
│ │                                                        │   │
│ │ [➕ Add habitat] [➕ Net Gain (Low)] ...               │   │
│ └───────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## User Flow

### Step 1: Expand Import Section
```
User clicks on "📄 Import from BNG Metric File"
↓
Section expands showing file uploader
```

### Step 2: Upload File
```
User uploads metric.xlsx file
↓
App parses file (spinner shown)
↓
Success message displays with counts
```

### Step 3: Preview Requirements
```
Preview tables shown for each category:
- Area Habitats (expanded by default if data exists)
- Hedgerows (collapsed)
- Watercourses (collapsed)
```

### Step 4: Import
```
User clicks "➕ Add to Demand Rows"
↓
If existing data: Warning shown + "Clear & Import" button appears
If no data: Import happens immediately
↓
User confirms with "Clear & Import" (if needed)
↓
Demand table populated
↓
Success message: "✅ Added X requirements to demand table!"
↓
Page refreshes showing populated demand rows
```

## Color Scheme & Icons
- 📄 File icon for the main expander
- ✅ Green checkmark for success messages
- ⚠️ Warning icon for confirmation dialogs
- ➕ Plus icon for add actions
- 🗑️ Trash icon for delete actions

## Responsive Design
- Uses Streamlit's native `st.expander()` for collapsible section
- Preview tables use `use_container_width=True` for responsiveness
- Two-column button layout for better visual balance
- Clear separation with `st.markdown("---")` divider

## Error States

### File Upload Error
```
❌ Error parsing metric file: [error message]
ℹ️ Please ensure this is a valid DEFRA BNG metric file 
   with Trading Summary sheets.
```

### No Requirements Found
```
⚠️ No valid requirements found to add.
```

### User Confirmation
```
⚠️ This will replace all existing demand rows. 
   Click 'Clear & Import' to proceed.
```

## Accessibility
- Clear, descriptive button labels
- Help text on hover for all interactive elements
- Success/error messages with appropriate icons
- Logical tab order for keyboard navigation

## Integration Points

### Before Manual Entry
The file uploader appears BEFORE the manual entry section, allowing users to:
1. Import from metric file first (if they have one)
2. Manually add/edit entries after import
3. Use manual entry exclusively (if no metric file)

### After Location Selection
The file uploader appears AFTER the location section, maintaining logical workflow:
1. Set target location (LPA/NCA)
2. Import or enter requirements
3. Optimize allocation

## Performance
- File parsing is async with loading spinner
- Preview tables use efficient DataFrame rendering
- Import operation triggers single page refresh
- No unnecessary re-renders

## Mobile Considerations
- Expander works well on mobile
- File uploader is touch-friendly
- Tables are scrollable horizontally on narrow screens
- Button layout adapts to screen width
