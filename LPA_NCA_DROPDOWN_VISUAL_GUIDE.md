# Visual Guide: LPA/NCA Dropdown and Dynamic Email Features

## Feature 1: LPA/NCA Dropdown Selection

### Before (Original UI)
```
┌─────────────────────────────────────────────────────────────┐
│ 1) Locate target site                                       │
│                                                              │
│ ┌──────────────┬──────────────────────┬─────────┐          │
│ │ Postcode     │ Address              │ Locate  │          │
│ │ (quicker)    │ (if no postcode)     │ [BTN]   │          │
│ │ [________]   │ [_________________]  │         │          │
│ └──────────────┴──────────────────────┴─────────┘          │
│                                                              │
│ ℹ️ LPA: Westminster | NCA: Thames Basin                     │
└─────────────────────────────────────────────────────────────┘
```

### After (With Dropdown Option)
```
┌─────────────────────────────────────────────────────────────┐
│ 1) Locate target site                                       │
│                                                              │
│ Option A: Select LPA/NCA directly (for promoters)          │
│                                                              │
│ ┌───────────────────────┬─────────────────────────┐        │
│ │ Select LPA            │ Select NCA              │        │
│ │ [Westminster      ▼]  │ [Thames Basin       ▼]  │        │
│ └───────────────────────┴─────────────────────────┘        │
│                                                              │
│              [ Apply LPA/NCA Selection ]                    │
│                                                              │
│ ───────────────────────────────────────────────────────     │
│                                                              │
│ Option B: Enter postcode or address (standard method)      │
│                                                              │
│ ┌──────────────┬──────────────────────┬─────────┐          │
│ │ Postcode     │ Address              │ Locate  │          │
│ │ (quicker)    │ (if no postcode)     │ [BTN]   │          │
│ │ [________]   │ [_________________]  │         │          │
│ └──────────────┴──────────────────────┴─────────┘          │
│                                                              │
│ ℹ️ LPA: Westminster | NCA: Thames Basin (via dropdown)      │
└─────────────────────────────────────────────────────────────┘
```

### Dropdown Behavior
```
When user types in LPA dropdown:
┌─────────────────────────┐
│ Select LPA              │
│ [west________      ▼]   │  ← User types "west"
│ ┌─────────────────────┐ │
│ │ Westminster         │ │
│ │ West Devon          │ │
│ │ West Lancashire     │ │  ← List filters as user types
│ │ West Lindsey        │ │
│ │ West Suffolk        │ │
│ └─────────────────────┘ │
└─────────────────────────┘
```

## Feature 2: Admin Dashboard - No Discount Option

### Add New Introducer Form

#### Before
```
┌──────────────────────────────────────────────────────┐
│ ➕ Add New Introducer                                │
│                                                       │
│ Introducer Name: [_____________________]             │
│                                                       │
│ Discount Type: [tier_up        ▼]                   │
│                 - tier_up                            │
│                 - percentage                         │
│                                                       │
│ Discount Value: [___10.5___]                        │
│                                                       │
│ ℹ️ For percentage: enter as decimal (e.g., 10.5     │
│    for 10.5%). For tier_up: value is ignored.       │
│                                                       │
│              [ Add Introducer ]                      │
└──────────────────────────────────────────────────────┘
```

#### After
```
┌──────────────────────────────────────────────────────┐
│ ➕ Add New Introducer                                │
│                                                       │
│ Introducer Name: [_____________________]             │
│                                                       │
│ Discount Type: [no_discount    ▼]                   │
│                 - tier_up                            │
│                 - percentage                         │
│                 - no_discount          ← NEW         │
│                                                       │
│ Discount Value: [____0.0___] (disabled)             │
│                                                       │
│ ℹ️ For percentage: enter as decimal (e.g., 10.5     │
│    for 10.5%). For tier_up or no_discount: value    │
│    is ignored.                                       │
│                                                       │
│              [ Add Introducer ]                      │
└──────────────────────────────────────────────────────┘
```

### Introducer List Display

#### Example with All Three Types
```
┌───────────────────────────────────────────────────────────────────┐
│ Current Introducers                                               │
│                                                                   │
│ ┌─────────────────┬──────────────────┬──────────────┬───┬───┐   │
│ │ Arbtech         │ Type: percentage │ Value: 10.0% │ ✏️ │🗑️ │   │
│ └─────────────────┴──────────────────┴──────────────┴───┴───┘   │
│                                                                   │
│ ┌─────────────────┬──────────────────┬──────────────┬───┬───┐   │
│ │ EcoConsult Ltd  │ Type: tier_up    │ Tier Up      │ ✏️ │🗑️ │   │
│ └─────────────────┴──────────────────┴──────────────┴───┴───┘   │
│                                                                   │
│ ┌─────────────────┬──────────────────┬──────────────┬───┬───┐   │
│ │ GreenPlanning   │ Type: no_discount│ No Discount  │ ✏️ │🗑️ │   │
│ └─────────────────┴──────────────────┴──────────────┴───┴───┘   │
│                                      ↑ NEW                        │
└───────────────────────────────────────────────────────────────────┘
```

## Feature 2: Promoter Selection in Main UI

### Discount Info Display

#### Tier Up Discount
```
┌───────────────────────────────────────────────────────────┐
│ 2) Promoter/Introducer (Optional)                        │
│                                                           │
│ ☑️ Use Promoter/Introducer                               │
│                                                           │
│ Select Introducer: [EcoConsult Ltd    ▼]                │
│                                                           │
│ ℹ️ Tier Up Discount: Pricing uses one contract size      │
│   tier higher (e.g., fractional → small, small →        │
│   medium, medium → large) for better rates               │
└───────────────────────────────────────────────────────────┘
```

#### Percentage Discount
```
┌───────────────────────────────────────────────────────────┐
│ 2) Promoter/Introducer (Optional)                        │
│                                                           │
│ ☑️ Use Promoter/Introducer                               │
│                                                           │
│ Select Introducer: [Arbtech            ▼]                │
│                                                           │
│ ℹ️ Percentage Discount: 10.0% discount on all items      │
│   except £500 admin fee                                  │
└───────────────────────────────────────────────────────────┘
```

#### No Discount (NEW)
```
┌───────────────────────────────────────────────────────────┐
│ 2) Promoter/Introducer (Optional)                        │
│                                                           │
│ ☑️ Use Promoter/Introducer                               │
│                                                           │
│ Select Introducer: [GreenPlanning      ▼]                │
│                                                           │
│ ℹ️ No Discount Applied: Promoter registered for dynamic  │
│   email text only                                        │
└───────────────────────────────────────────────────────────┘
```

## Feature 2: Dynamic Email Text

### Email Structure Comparison

#### Scenario 1: No Promoter Selected
```
┌──────────────────────────────────────────────────────────┐
│ Dear John Smith                                          │
│                                                          │
│ Our Ref: BNG00123                                        │
│                                                          │
│ Thank you for enquiring about BNG Units for your        │
│ development in Westminster                               │
│                                                          │
│ About Us                                                 │
│                                                          │
│ Wild Capital is a national supplier of BNG Units...     │
│                                                          │
│ Your Quote - £45,500 + VAT                              │
│                                                          │
│ See a detailed breakdown of the pricing below...        │
│                                                          │
│ [TABLE]                                                  │
└──────────────────────────────────────────────────────────┘
```

#### Scenario 2: Promoter with Percentage Discount
```
┌──────────────────────────────────────────────────────────┐
│ Dear John Smith                                          │
│                                                          │
│ Our Ref: BNG00123                                        │
│                                                          │
│ Arbtech has advised us that you need Biodiversity Net   │
│ Gain units for your development in Westminster, and     │
│ we're here to help you discharge your BNG condition.    │
│                                                          │
│ About Us                                                 │
│                                                          │
│ Wild Capital is a national supplier of BNG Units...     │
│                                                          │
│ Your Quote - £40,950 + VAT                              │
│                                                          │
│ Discount Applied: Introducer/Promoter: Arbtech          │
│ Discount Type: 10.0% percentage discount on all items   │
│ (excluding £500 admin fee)                              │
│                                                          │
│ See a detailed breakdown of the pricing below...        │
│                                                          │
│ [TABLE]                                                  │
└──────────────────────────────────────────────────────────┘
```

#### Scenario 3: Promoter with Tier Up Discount
```
┌──────────────────────────────────────────────────────────┐
│ Dear John Smith                                          │
│                                                          │
│ Our Ref: BNG00123                                        │
│                                                          │
│ EcoConsult Ltd has advised us that you need             │
│ Biodiversity Net Gain units for your development in     │
│ Westminster, and we're here to help you discharge your  │
│ BNG condition.                                           │
│                                                          │
│ About Us                                                 │
│                                                          │
│ Wild Capital is a national supplier of BNG Units...     │
│                                                          │
│ Your Quote - £42,000 + VAT                              │
│                                                          │
│ Discount Applied: Introducer/Promoter: EcoConsult Ltd   │
│ Discount Type: Tier Up (pricing uses one contract size  │
│ tier higher for better rates)                           │
│                                                          │
│ See a detailed breakdown of the pricing below...        │
│                                                          │
│ [TABLE]                                                  │
└──────────────────────────────────────────────────────────┘
```

#### Scenario 4: Promoter with No Discount (NEW)
```
┌──────────────────────────────────────────────────────────┐
│ Dear John Smith                                          │
│                                                          │
│ Our Ref: BNG00123                                        │
│                                                          │
│ GreenPlanning has advised us that you need              │
│ Biodiversity Net Gain units for your development in     │
│ Westminster, and we're here to help you discharge your  │
│ BNG condition.                                           │
│                                                          │
│ About Us                                                 │
│                                                          │
│ Wild Capital is a national supplier of BNG Units...     │
│                                                          │
│ Your Quote - £45,500 + VAT                              │
│          ↑ No discount applied                           │
│                                                          │
│ See a detailed breakdown of the pricing below...        │
│          ↑ No discount info shown                        │
│                                                          │
│ [TABLE]                                                  │
└──────────────────────────────────────────────────────────┘
```

## Key Visual Differences Summary

### LPA/NCA Dropdown
- ✅ Two new dropdown boxes above postcode/address
- ✅ "Apply LPA/NCA Selection" button
- ✅ Clear separation: "Option A" vs "Option B"
- ✅ Location banner shows "(via dropdown)" or "(via postcode/address)"

### No Discount Option
- ✅ Third option in discount type dropdown: "no_discount"
- ✅ Discount value field disabled when no_discount selected
- ✅ Display shows "No Discount" instead of percentage/tier up
- ✅ Info message: "Promoter registered for dynamic email text only"

### Dynamic Email Text
- ✅ Intro changes from generic to personalized when promoter selected
- ✅ Promoter name appears in first paragraph
- ✅ "Thank you for enquiring..." only appears without promoter
- ✅ Discount info section only appears for actual discounts
- ✅ No discount info shown for no_discount promoters

## User Flow Diagrams

### Flow 1: Using LPA/NCA Dropdown
```
┌─────────────────┐
│ Open Optimiser  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Upload Backend  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│ Select LPA from dropdown│
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ Select NCA from dropdown│
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ Click "Apply Selection" │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ Location banner shows   │
│ "(via dropdown)"        │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ Continue with demand    │
│ entry & optimization    │
└─────────────────────────┘
```

### Flow 2: Adding No-Discount Promoter
```
┌──────────────────────┐
│ Switch to Admin Mode │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Expand "Add New      │
│ Introducer"          │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Enter promoter name  │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Select "no_discount" │
│ from dropdown        │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Discount value auto  │
│ set to 0 (disabled)  │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Click "Add           │
│ Introducer"          │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Promoter appears in  │
│ list as "No Discount"│
└──────────────────────┘
```

### Flow 3: Email Generation with No-Discount Promoter
```
┌──────────────────────┐
│ Select no-discount   │
│ promoter from list   │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Info shows: "No      │
│ Discount Applied"    │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Complete demand &    │
│ run optimization     │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Generate client      │
│ report               │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Email shows:         │
│ - Promoter name in   │
│   intro text         │
│ - No discount info   │
│ - Full price         │
└──────────────────────┘
```

## Testing Checklist

### LPA/NCA Dropdown Testing
- [ ] Backend loads and populates LPA/NCA dropdowns
- [ ] Dropdowns filter as user types
- [ ] Apply button updates location banner
- [ ] Location banner shows "(via dropdown)"
- [ ] Optimization runs with dropdown-selected location
- [ ] Switching to postcode clears dropdown flag
- [ ] Location banner updates to "(via postcode/address)"

### No Discount Testing
- [ ] Can add introducer with no_discount type
- [ ] Discount value field disabled for no_discount
- [ ] Introducer list shows "No Discount"
- [ ] Can edit introducer to/from no_discount
- [ ] Main UI shows correct info message
- [ ] No discount applied to pricing
- [ ] Email shows promoter name in intro
- [ ] Email hides discount info section
- [ ] Email shows full price (no discount)

### Integration Testing
- [ ] LPA/NCA dropdown works with promoter selection
- [ ] Can use LPA/NCA dropdown + no_discount promoter
- [ ] Can use postcode + discount promoter
- [ ] All combinations generate correct email
- [ ] Database migration works on existing database
- [ ] Session state persists across page interactions
