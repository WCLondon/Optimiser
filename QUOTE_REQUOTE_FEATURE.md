# Quote Requote Workflow and Customer Info Feature

## Overview

This feature adds comprehensive quote management capabilities to the BNG Optimiser application, including:

1. **Customer Information Management** - Store and track customer details
2. **Quote Search** - Search existing quotes by multiple criteria
3. **Requote Creation** - Create updated quotes with revision tracking
4. **Customer Linking** - Associate quotes with customer records

## Features

### 1. Customer Information Table

A new `customers` table stores standard customer details:

- **Client Name** (required)
- **Company Name** (optional)
- **Contact Person** (optional)
- **Address** (optional)
- **Email Address** (recommended)
- **Mobile/Phone Number** (recommended)
- **Created Date** (automatic)
- **Updated Date** (automatic)

#### Unique Identifiers

- Email or mobile number is used as a unique identifier
- Prevents duplicate customer records
- Automatically links quotes to existing customers when contact info matches

### 2. Quote Management Page

Access via the sidebar: **Mode → Quote Management**

The Quote Management page has three tabs:

#### Tab 1: Search Quotes

Search existing quotes using multiple filters:
- **Client Name** - Search by client name (partial match)
- **Reference Number** - Search by reference number (partial match)
- **Development Location** - Search by site location (partial match)
- **LPA** - Filter by Local Planning Authority
- **Start/End Date** - Filter by submission date range

**Features:**
- View search results in a table
- Select and view detailed information for any quote
- See customer information if linked
- View demand and allocation details

#### Tab 2: Customer Management

Manage customer records:
- **Add New Customer** - Create customer records with contact details
- **View All Customers** - See list of all customers
- **View Customer Quotes** - See all quotes associated with a customer

**GDPR Compliance:**
- Customer data should be handled according to your organization's GDPR policies
- Email and mobile numbers are used for unique identification
- Consider adding data retention and deletion policies

#### Tab 3: Create Requote

Create a new quote based on an existing one:
- **Select Existing Quote** - Choose from recent quotes
- **View Original Details** - Review the original quote information
- **Create Requote** - Generate a new quote with incremented revision suffix

**Requote Behavior:**
- Automatically appends revision suffix (e.g., BNG01234 → BNG01234.1 → BNG01234.2)
- Copies all site information (location, LPA, NCA)
- Copies customer association
- Copies demand and allocation as a starting point
- Creates a separate database record for tracking and auditing

### 3. Customer Linking in Optimiser Mode

When saving a quote in the Optimiser mode, you can now:

1. **Enter Customer Details** (optional):
   - Customer Email
   - Customer Mobile
   - Company Name
   - Contact Person
   - Customer Address

2. **Automatic Linking**:
   - If email or mobile matches an existing customer, the quote is linked to that customer
   - If no match is found, a new customer record is created
   - System notifies you whether an existing customer was linked or a new one created

3. **Benefits**:
   - Track all quotes for a specific customer
   - Maintain customer history
   - Streamline requote process

## Database Schema Changes

### New Tables

#### customers
```sql
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    client_name TEXT NOT NULL,
    company_name TEXT,
    contact_person TEXT,
    address TEXT,
    email TEXT,
    mobile_number TEXT,
    created_date TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_date TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT customers_unique_email_mobile UNIQUE NULLS NOT DISTINCT (email, mobile_number)
);
```

### Modified Tables

#### submissions
Added column:
- `customer_id INTEGER` - Foreign key to customers table

## API Methods

### SubmissionsDB Class - Customer Methods

#### `add_customer()`
```python
def add_customer(self, client_name: str, company_name: Optional[str] = None,
                 contact_person: Optional[str] = None, address: Optional[str] = None,
                 email: Optional[str] = None, mobile_number: Optional[str] = None) -> int
```
Add a new customer or return existing customer ID if email/mobile matches.

#### `get_customer_by_id()`
```python
def get_customer_by_id(self, customer_id: int) -> Optional[Dict[str, Any]]
```
Retrieve a customer record by ID.

#### `get_customer_by_contact()`
```python
def get_customer_by_contact(self, email: Optional[str] = None, 
                            mobile_number: Optional[str] = None) -> Optional[Dict[str, Any]]
```
Find a customer by email or mobile number.

#### `get_all_customers()`
```python
def get_all_customers(self) -> List[Dict[str, Any]]
```
Get all customer records.

#### `update_customer()`
```python
def update_customer(self, customer_id: int, client_name: Optional[str] = None,
                   company_name: Optional[str] = None, contact_person: Optional[str] = None,
                   address: Optional[str] = None, email: Optional[str] = None,
                   mobile_number: Optional[str] = None)
```
Update customer information.

### SubmissionsDB Class - Quote/Requote Methods

#### `get_next_revision_number()`
```python
def get_next_revision_number(self, base_reference: str) -> str
```
Get the next revision number for a reference (e.g., BNG01234 → BNG01234.1).

#### `get_quotes_by_reference_base()`
```python
def get_quotes_by_reference_base(self, base_reference: str) -> pd.DataFrame
```
Get all quotes with a given base reference (including all revisions).

#### `create_requote_from_submission()`
```python
def create_requote_from_submission(self, submission_id: int, 
                                   new_demand_df: Optional[pd.DataFrame] = None) -> int
```
Create a requote from an existing submission with incremented revision suffix.

### Modified Methods

#### `store_submission()`
Now accepts optional `customer_id` parameter:
```python
def store_submission(self, ..., customer_id: Optional[int] = None) -> int
```

## Usage Examples

### Example 1: Create a Customer and Link to Quote

```python
# In the Optimiser mode, fill in customer details when saving a quote:
# - Customer Email: john@example.com
# - Customer Mobile: +44 1234 567890
# - Company Name: ABC Development Ltd
# - Contact Person: John Smith

# System will automatically:
# - Create new customer record (or link to existing)
# - Associate the quote with the customer
# - Display confirmation message
```

### Example 2: Create a Requote

1. Go to **Quote Management** mode
2. Click **Create Requote** tab
3. Select the original quote from the dropdown
4. Review the original quote details
5. Click **Create Requote** button
6. New quote is created with reference like BNG01234.1
7. Update demand in Optimiser mode if needed
8. Reoptimize and save

### Example 3: Search for All Quotes for a Location

1. Go to **Quote Management** mode
2. Click **Search Quotes** tab
3. Enter "London" in Development Location field
4. Click **Search** button
5. Review results table
6. Select a quote to view details

### Example 4: View All Quotes for a Customer

1. Go to **Quote Management** mode
2. Click **Customer Management** tab
3. Select customer ID from dropdown
4. Click **View Customer Quotes** button
5. See all quotes associated with that customer

## Workflow Diagrams

### Standard Quote Creation Flow
```
User enters quote details in Optimiser
    ↓
User runs optimization
    ↓
User fills in customer details (optional)
    ↓
User saves quote
    ↓
System checks for existing customer (by email/mobile)
    ↓
├─ If exists: Link to existing customer
└─ If not: Create new customer
    ↓
Quote saved with customer association
```

### Requote Creation Flow
```
User searches for original quote
    ↓
User selects quote in "Create Requote" tab
    ↓
System shows original details
    ↓
User clicks "Create Requote"
    ↓
System generates new reference (e.g., .1, .2)
    ↓
System copies all site and customer info
    ↓
New quote created as separate record
    ↓
User can update demand and reoptimize in Optimiser mode
```

## Best Practices

1. **Always provide email or mobile** when saving quotes to enable customer tracking
2. **Use consistent reference numbering** - Base reference without dots (e.g., BNG01234)
3. **Review requotes before optimization** - Verify demand requirements are correct
4. **Keep customer information up to date** - Update customer records when details change
5. **Use search filters** - Combine multiple filters for precise quote searches

## Migration Notes

### Existing Quotes
- Existing quotes without customer associations will continue to work
- Customer linking is optional
- You can retroactively link quotes to customers by updating the `customer_id` field in the database

### Database Migration
The feature automatically creates the necessary tables and columns on first run. No manual migration is required.

## Security and Privacy

### GDPR Considerations
- Customer data includes personal information (email, mobile, address)
- Ensure compliance with GDPR requirements:
  - Obtain consent for data storage
  - Implement data access and deletion procedures
  - Secure database access
  - Regular data audits

### Access Control
- Quote Management page requires authentication
- All customer data operations are logged
- Database access follows existing security patterns

## Troubleshooting

### Issue: Customer not linking automatically
**Solution**: Ensure email or mobile number matches exactly (including formatting)

### Issue: Requote reference number not incrementing
**Solution**: Check that base reference number doesn't already contain a dot

### Issue: Cannot find quotes in search
**Solution**: Use partial matches and check date filters; search is case-insensitive

### Issue: Database error when creating customer
**Solution**: Check that at least one of email or mobile is provided

## Future Enhancements

Potential improvements for future versions:

1. **Email Integration** - Send quotes directly from the application
2. **Customer Dashboard** - Dedicated page for customer overview and history
3. **Bulk Operations** - Export/import customer data
4. **Advanced Search** - More filter options and saved searches
5. **Notification System** - Alert when requotes are created
6. **Customer Notes** - Add notes and tags to customer records
7. **Audit Trail** - Detailed tracking of all customer and quote changes

## Support

For issues or questions about this feature:
1. Review this documentation
2. Check the troubleshooting section
3. Examine application logs for error messages
4. Contact the development team

## Version History

- **v1.0** (2025-10-16) - Initial implementation
  - Customer information table
  - Quote search and management
  - Requote workflow
  - Customer linking in Optimiser mode
