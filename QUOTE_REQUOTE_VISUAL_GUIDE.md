# Quote Requote Feature - Visual Guide

## Mode Selection

The application now has three modes accessible from the sidebar:

```
┌─────────────────────────┐
│ Mode                    │
├─────────────────────────┤
│ ○ Optimiser            │
│ ○ Quote Management     │ ← New!
│ ○ Admin Dashboard      │
└─────────────────────────┘
```

## Quote Management Page Layout

### Tab Navigation

```
╔═══════════════════════════════════════════════════════════════════════╗
║  🔍 Quote Management & Requotes                                       ║
╠═══════════════════════════════════════════════════════════════════════╣
║                                                                       ║
║  [🔓 Return to Optimiser]                                            ║
║                                                                       ║
║  ┌────────────┬───────────────────┬──────────────┐                  ║
║  │ Search     │ Customer          │ Create       │                  ║
║  │ Quotes     │ Management        │ Requote      │                  ║
║  └────────────┴───────────────────┴──────────────┘                  ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝
```

## Tab 1: Search Quotes

```
┌─────────────────────────────────────────────────────────────────────┐
│ 🔎 Search Filters                                           [▼]     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Client Name (contains)    Dev Location (contains)   Start Date    │
│  ┌──────────────────┐     ┌──────────────────┐     ┌──────────┐   │
│  │                  │     │                  │     │          │   │
│  └──────────────────┘     └──────────────────┘     └──────────┘   │
│                                                                     │
│  Reference (contains)      LPA (contains)           End Date       │
│  ┌──────────────────┐     ┌──────────────────┐     ┌──────────┐   │
│  │                  │     │                  │     │          │   │
│  └──────────────────┘     └──────────────────┘     └──────────┘   │
│                                                                     │
│  [🔍 Search]                                                        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ 📋 Search Results (15 quotes found)                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ID  │ Date       │ Client    │ Reference │ Location │ Total      │
│ ────┼────────────┼───────────┼───────────┼──────────┼────────── │
│  123│ 2025-10-15 │ ABC Ltd   │ BNG01234  │ London   │ £45,000   │
│  124│ 2025-10-14 │ XYZ Corp  │ BNG01235  │ Bristol  │ £32,500   │
│  125│ 2025-10-13 │ ABC Ltd   │ BNG01234.1│ London   │ £47,200   │
│  ...│ ...        │ ...       │ ...       │ ...      │ ...       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ 👁️ View Quote Details                                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Select Quote ID to View: [123 ▼]     [View Details]              │
│                                                                     │
│  ┌────────────────────────┬──────────────────────────┐           │
│  │ Quote Information      │ Location & Banks         │           │
│  │                        │                          │           │
│  │ ID: 123                │ LPA: Westminster         │           │
│  │ Client: ABC Ltd        │ NCA: Thames Basin        │           │
│  │ Reference: BNG01234    │ Banks Used: 3            │           │
│  │ Location: London SW1   │ Promoter: John Smith     │           │
│  │ Date: 2025-10-15       │ Customer: ABC Ltd        │           │
│  │ Contract: Medium       │ Email: abc@example.com   │           │
│  │ Total: £45,000         │                          │           │
│  └────────────────────────┴──────────────────────────┘           │
│                                                                     │
│  Demand Details                                                    │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ Habitat               │ Units Required │ Type               │ │
│  │ ─────────────────────┼────────────────┼────────────────────│ │
│  │ Grassland - Medium    │ 10.5          │ area               │ │
│  │ Urban - Low           │ 5.2           │ area               │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Tab 2: Customer Management

```
┌─────────────────────────────────────────────────────────────────────┐
│ ➕ Add New Customer                                         [▼]     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Client Name*              Company Name        Contact Person      │
│  ┌──────────────────┐     ┌──────────────┐   ┌─────────────┐     │
│  │                  │     │              │   │             │     │
│  └──────────────────┘     └──────────────┘   └─────────────┘     │
│                                                                     │
│  Address                                                           │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │                                                          │     │
│  │                                                          │     │
│  └──────────────────────────────────────────────────────────┘     │
│                                                                     │
│  Email Address             Mobile Number                           │
│  ┌──────────────────┐     ┌──────────────┐                       │
│  │                  │     │              │                       │
│  └──────────────────┘     └──────────────┘                       │
│                                                                     │
│  [Add Customer]                                                    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ Existing Customers (25)                                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ID │ Client Name │ Company      │ Email              │ Created   │
│ ───┼─────────────┼──────────────┼────────────────────┼────────── │
│  1 │ ABC Ltd     │ ABC Dev Ltd  │ abc@example.com    │ 2025-10-15│
│  2 │ XYZ Corp    │ XYZ Holdings │ xyz@example.com    │ 2025-10-14│
│  3 │ DEF Co      │ -            │ def@example.com    │ 2025-10-13│
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ 🔍 View Customer Quotes                                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Select Customer ID: [1 ▼]     [View Customer Quotes]             │
│                                                                     │
│  3 quotes found for this customer                                  │
│                                                                     │
│  ID  │ Reference │ Date       │ Location │ Contract │ Total       │
│ ────┼───────────┼────────────┼──────────┼──────────┼─────────── │
│  123│ BNG01234  │ 2025-10-15 │ London   │ Medium   │ £45,000    │
│  125│ BNG01234.1│ 2025-10-13 │ London   │ Medium   │ £47,200    │
│  130│ BNG01245  │ 2025-10-10 │ Bristol  │ Large    │ £85,000    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Tab 3: Create Requote

```
┌─────────────────────────────────────────────────────────────────────┐
│ 🔄 Create Requote                                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ℹ️ Select an existing quote to create a requote. The requote     │
│     will have the same site location and customer info, but you    │
│     can update the demand and reoptimize.                          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ Select Quote to Requote                                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Select Quote: [123 - BNG01234 - ABC Ltd - London SW1  ▼]         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ Original Quote Details                                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Reference: BNG01234        Location: London SW1    Total: £45,000 │
│  Client: ABC Ltd            LPA: Westminster        Date: 2025-10-15│
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  ℹ️ 📝 New requote will have reference: BNG01234.1                 │
└─────────────────────────────────────────────────────────────────────┘

────────────────────────────────────────────────────────────────────

┌─────────────────────────────────────────────────────────────────────┐
│ Create Requote                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  This will create a new quote as a separate record with the        │
│  incremented reference number.                                     │
│                                                                     │
│  ⚠️  Note: Site location and customer info will be copied. You     │
│      can update demand later in the Optimiser.                     │
│                                                                     │
│  [🔄 Create Requote]                                               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

After clicking "Create Requote":
┌─────────────────────────────────────────────────────────────────────┐
│  ✅ Requote created successfully!                                  │
│  ✅ 📋 New Reference: BNG01234.1                                   │
│  ✅ 🆔 New Submission ID: 126                                      │
│  ℹ️  💡 You can now search for this quote and view/edit it in     │
│     the Optimiser mode.                                            │
└─────────────────────────────────────────────────────────────────────┘
```

## Optimiser Mode - Customer Info Section

When saving a quote in Optimiser mode:

```
┌─────────────────────────────────────────────────────────────────────┐
│ Generate Client Email Report                                [▲]    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  📝 Email Details:                                                 │
│                                                                     │
│  Client Name           Reference Number      Development Location  │
│  ┌──────────────┐     ┌──────────────┐      ┌─────────────────┐  │
│  │ ABC Ltd      │     │ BNG01234     │      │ London SW1      │  │
│  └──────────────┘     └──────────────┘      └─────────────────┘  │
│                                                                     │
│  👤 Customer Information (Optional):                               │
│  Link this quote to a customer record for tracking. Either Email  │
│  or Mobile is recommended.                                         │
│                                                                     │
│  Customer Email               Customer Mobile                      │
│  ┌─────────────────────┐     ┌─────────────────────┐             │
│  │ abc@example.com     │     │ +44 1234 567890     │             │
│  └─────────────────────┘     └─────────────────────┘             │
│                                                                     │
│  Company Name                 Contact Person                       │
│  ┌─────────────────────┐     ┌─────────────────────┐             │
│  │ ABC Development Ltd │     │ John Smith          │             │
│  └─────────────────────┘     └─────────────────────┘             │
│                                                                     │
│  Customer Address                                                  │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │ 123 High Street                                          │    │
│  │ London SW1 1AA                                           │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                     │
│  [Update Email Details]                                            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

After clicking "Update Email Details" with customer info:
┌─────────────────────────────────────────────────────────────────────┐
│  ✅ Email details updated!                                         │
│  ℹ️  Linked to existing customer: ABC Ltd (ID: 1)                 │
│     OR                                                             │
│  ℹ️  ✅ New customer created (ID: 5)                              │
│  ✅ Quote saved to database! Submission ID: 123                   │
│  ℹ️  📊 Client: ABC Ltd | Reference: BNG01234 | Total: £45,000   │
└─────────────────────────────────────────────────────────────────────┘
```

## Reference Number Evolution

Shows how reference numbers evolve with requotes:

```
Original Quote:     BNG01234
                       ↓
First Requote:      BNG01234.1
                       ↓
Second Requote:     BNG01234.2
                       ↓
Third Requote:      BNG01234.3
                       ↓
                     ...
```

All quotes with the same base reference (BNG01234) can be searched and viewed together, making it easy to track the history of quotes for a particular development.

## Key Visual Elements

### Icons Used
- 🔍 - Search functionality
- 👥 - Customer management
- 🔄 - Requote/revision
- ✅ - Success messages
- ℹ️ - Information messages
- ⚠️ - Warning messages
- 📋 - Quote/reference information
- 👁️ - View details
- ➕ - Add new item
- 🔓 - Navigation/return
- 💡 - Tips and suggestions
- 📊 - Statistics/summary
- 🆔 - Identifier

### Color Coding (Streamlit defaults)
- **Blue** - Primary actions and links
- **Green** - Success messages
- **Yellow** - Warning messages
- **Red** - Error messages
- **Grey** - Information messages

## User Journey Examples

### Journey 1: First Time Quote with Customer
```
1. User logs into Optimiser
2. Creates quote in Optimiser mode
3. Enters customer email in save form
4. System creates new customer automatically
5. Quote saved and linked to customer
```

### Journey 2: Creating a Requote
```
1. User navigates to Quote Management
2. Goes to "Create Requote" tab
3. Selects original quote (BNG01234)
4. Clicks "Create Requote"
5. New quote created as BNG01234.1
6. User returns to Optimiser to modify demand
7. Reoptimizes and saves updated quote
```

### Journey 3: Finding Customer History
```
1. User navigates to Quote Management
2. Goes to "Customer Management" tab
3. Selects customer from dropdown
4. Clicks "View Customer Quotes"
5. Sees all quotes for that customer
6. Can click to view details of any quote
```

## Tips for Best User Experience

1. **Keep customer emails consistent** - Always use the same format for email addresses
2. **Fill in reference numbers carefully** - Use base reference without dots
3. **Use the search filters** - Combine multiple criteria for precise results
4. **Review requotes before saving** - Check demand is correct before reoptimizing
5. **Link customers at save time** - Easier than retroactive linking
