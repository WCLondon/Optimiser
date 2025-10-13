# Promoter/Introducer Discount Feature - Visual Guide

## Feature Overview

This document provides a visual guide to the implemented promoter/introducer discount feature.

---

## 1. Admin Dashboard - Introducer Management

### Location
Admin Dashboard → Introducer/Promoter Management section (after summary stats)

### Features
```
┌─────────────────────────────────────────────────────────────┐
│ 👥 Introducer/Promoter Management                           │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ ➕ Add New Introducer [Expand ▼]                            │
│   ┌───────────────────────────────────────────────────┐    │
│   │ Introducer Name: [_________________]              │    │
│   │ Discount Type:   [tier_up ▼]                      │    │
│   │ Discount Value:  [0.0_____]                       │    │
│   │                  [Add Introducer]                  │    │
│   └───────────────────────────────────────────────────┘    │
│                                                               │
│ Current Introducers                                          │
│ ┌─────────────────────────────────────────────────────────┐│
│ │ John Smith    │ Type: percentage │ Value: 10.5% │✏️│🗑️││
│ │ Jane Doe      │ Type: tier_up    │ Tier Up      │✏️│🗑️││
│ │ ABC Company   │ Type: percentage │ Value: 15.0% │✏️│🗑️││
│ └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

**Actions Available:**
- ➕ Add: Opens form to create new introducer
- ✏️ Edit: Opens inline form to modify details
- 🗑️ Delete: Removes introducer (with confirmation)

---

## 2. Main UI - Promoter Selection

### Location
Main workflow → After "Locate target site", before demand entry

### UI Layout
```
───────────────────────────────────────────────────────────────
2) Promoter/Introducer (Optional)
───────────────────────────────────────────────────────────────

☐ Use Promoter/Introducer

[When checkbox is unchecked, no additional UI]

───────────────────────────────────────────────────────────────
```

**When Checkbox is Checked:**
```
───────────────────────────────────────────────────────────────
2) Promoter/Introducer (Optional)
───────────────────────────────────────────────────────────────

☑ Use Promoter/Introducer  |  [Select Introducer ▼]
                           |     John Smith
                           |     Jane Doe
                           |     ABC Company

💡 Percentage Discount: 10.5% discount on all items 
   except £500 admin fee

───────────────────────────────────────────────────────────────
```

**Or for Tier Up:**
```
───────────────────────────────────────────────────────────────
2) Promoter/Introducer (Optional)
───────────────────────────────────────────────────────────────

☑ Use Promoter/Introducer  |  [Jane Doe ▼]

💡 Tier Up Discount: Pricing uses one contract size tier higher 
   (e.g., fractional → small, small → medium, medium → large)

───────────────────────────────────────────────────────────────
```

---

## 3. Client Report - Promoter Display

### Email/Report Output

**Before Discount Applied:**
```
Your Quote - £25,000 + VAT

See a detailed breakdown of the pricing below...
```

**After Discount Applied (Percentage):**
```
Your Quote - £22,875 + VAT

Discount Applied: Introducer/Promoter: John Smith
Discount Type: 10.5% percentage discount on all items 
(excluding £500 admin fee)

See a detailed breakdown of the pricing below...
```

**After Discount Applied (Tier Up):**
```
Your Quote - £21,500 + VAT

Discount Applied: Introducer/Promoter: Jane Doe
Discount Type: Tier Up (pricing calculated at one tier higher)

See a detailed breakdown of the pricing below...
```

---

## 4. Admin Dashboard - Submission Details

### When Viewing a Submission

**Standard View (No Promoter):**
```
Submission Details
──────────────────
Client: ABC Development Ltd
Reference: BNG001234
Location: Site at Wimborne Road
Date: 2025-10-13 15:30
LPA: Dorset Council
NCA: Dorset Heaths
Contract Size: medium
Total Cost: £24,500
Total with Admin: £25,000
```

**With Promoter Information:**
```
Submission Details
──────────────────
Client: ABC Development Ltd
Reference: BNG001234
Location: Site at Wimborne Road
Date: 2025-10-13 15:30
LPA: Dorset Council
NCA: Dorset Heaths
Contract Size: medium
Total Cost: £24,500
Total with Admin: £25,000
Promoter/Introducer: John Smith
Discount Type: Percentage (10.5%)
```

---

## 5. Pricing Logic Flow

### How Discounts are Applied

**Tier Up Discount:**
```
Original Flow:
  Demand → Calculate Contract Size → Find Price
  (5 units)  (e.g., "small")         (£4,000/unit)

With Tier Up:
  Demand → Calculate Contract Size → Apply Tier Up → Find Price
  (5 units)  (e.g., "small")         ("medium")      (£3,000/unit)
                                                       ↓
                                                   25% savings
                                                   
Note: Actual contract size stays "small" for the quote record.
      Only pricing uses "medium" rates.
```

**Percentage Discount:**
```
Original Flow:
  Location → Calculate Tier → Find Price
  (Target)    (e.g., "local")  (£1,000/unit)

With Percentage (10%):
  Location → Calculate Tier → Find Price → Apply Discount
  (Target)    (e.g., "local")  (£1,000/unit)  (£900/unit)
                                                ↓
                                            10% savings
```

---

## 6. Database Schema

### Introducers Table
```
┌─────────────────────────────────────────────────────┐
│ introducers                                         │
├─────────────────────────────────────────────────────┤
│ id (PK)              │ INTEGER                      │
│ name                 │ TEXT (UNIQUE)                │
│ discount_type        │ TEXT ('tier_up'/'percentage')│
│ discount_value       │ REAL                         │
│ created_date         │ TEXT (ISO timestamp)         │
│ updated_date         │ TEXT (ISO timestamp)         │
└─────────────────────────────────────────────────────┘
```

### Submissions Table (Extended)
```
┌─────────────────────────────────────────────────────┐
│ submissions                                         │
├─────────────────────────────────────────────────────┤
│ ... [existing fields] ...                          │
│ promoter_name        │ TEXT (nullable)              │
│ promoter_discount_type│ TEXT (nullable)             │
│ promoter_discount_value│ REAL (nullable)            │
└─────────────────────────────────────────────────────┘
```

---

## User Workflows

### Admin Workflow: Adding an Introducer
1. Navigate to Admin Dashboard (sidebar)
2. Enter admin password
3. Scroll to "Introducer/Promoter Management"
4. Click "➕ Add New Introducer"
5. Enter name (e.g., "John Smith")
6. Select discount type (tier_up or percentage)
7. Enter discount value (for percentage type)
8. Click "Add Introducer"
9. ✅ Introducer appears in list

### User Workflow: Applying Discount
1. Enter postcode/address and locate site
2. Check "Use Promoter/Introducer" checkbox
3. Select introducer from dropdown
4. View discount information displayed
5. Continue with demand entry as normal
6. Run optimization
7. ✅ Discounted prices used automatically
8. Generate report - promoter info included

### Admin Workflow: Viewing Submissions with Promoters
1. Navigate to Admin Dashboard
2. View submissions list (promoter name column visible)
3. Select submission to view details
4. ✅ Promoter information displayed in detail view

---

## Error Handling

### No Introducers Configured
```
☑ Use Promoter/Introducer  |  [No Selection Available]

⚠️ No introducers configured. Please add introducers 
   in the Admin Dashboard.
```

### Invalid Discount Settings
The application validates:
- Discount type must be 'tier_up' or 'percentage'
- Name must be unique
- Name cannot be empty

---

## Integration Points

1. **Session State**: Promoter settings stored for entire workflow
2. **Optimization**: Discount applied before solver runs
3. **Reporting**: All reports include promoter details
4. **Database**: All quotes saved with promoter tracking
5. **Admin Dashboard**: Complete CRUD for introducer management

---

This feature is fully integrated and tested, ready for production use.
