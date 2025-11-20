# Excel File Corruption Fix

## Issue
When opening metric files from notification emails or review required emails from `promoter_app.py` or `quickopt_app.py`, users would sometimes encounter this error:

```
Excel cannot open the file 'BNG-A-02074_metric.xlsx' because the file format or file extension is not valid. 
Verify that the file has not been corrupted and that the file extension matches the format of the file.
```

## Root Cause
The issue was caused by a mismatch between the actual file type and the email attachment metadata:

1. **File Upload**: Users could upload Excel files in three formats:
   - `.xlsx` (standard Excel workbook)
   - `.xlsm` (macro-enabled Excel workbook)
   - `.xlsb` (binary Excel workbook)

2. **Email Attachment Problem**: The code always attached files with:
   - Hardcoded `.xlsx` extension (regardless of actual file type)
   - Generic `application/octet-stream` MIME type

3. **Result**: When a user uploaded a `.xlsm` file but it was attached as `.xlsx`, Excel would reject it as corrupted because the file extension didn't match the actual file format.

## Solution

### 1. Added MIME Type Detection (`email_notification.py`)
Created a new helper function `get_excel_mime_type()` that maps file extensions to proper MIME types:

```python
def get_excel_mime_type(filename: str) -> tuple[str, str]:
    """Determine the correct MIME type for an Excel file based on its extension."""
    filename_lower = filename.lower()
    
    if filename_lower.endswith('.xlsm'):
        return ('application', 'vnd.ms-excel.sheet.macroEnabled.12')
    elif filename_lower.endswith('.xlsb'):
        return ('application', 'vnd.ms-excel.sheet.binary.macroEnabled.12')
    elif filename_lower.endswith('.xlsx'):
        return ('application', 'vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    else:
        return ('application', 'octet-stream')
```

### 2. Preserved Original Filename
Modified `send_email_notification()` to accept an optional `metric_filename` parameter that preserves the original file extension.

### 3. Updated Email Attachment Logic
Changed the attachment code from:
```python
attachment = MIMEBase('application', 'octet-stream')
attachment.add_header('Content-Disposition', f'attachment; filename="{reference_number}_metric.xlsx"')
```

To:
```python
maintype, subtype = get_excel_mime_type(attachment_filename)
attachment = MIMEBase(maintype, subtype)
attachment.add_header('Content-Disposition', f'attachment; filename="{attachment_filename}"')
```

### 4. Updated Application Code
Modified both `promoter_app.py` and `quickopt_app.py` to pass the original filename:
```python
send_email_notification(
    ...
    metric_filename=f"{reference_number}_{metric_file.name}",
    ...
)
```

## MIME Type Mapping

| File Extension | MIME Type |
|----------------|-----------|
| `.xlsx` | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` |
| `.xlsm` | `application/vnd.ms-excel.sheet.macroEnabled.12` |
| `.xlsb` | `application/vnd.ms-excel.sheet.binary.macroEnabled.12` |
| Other | `application/octet-stream` (fallback) |

## Testing
Created comprehensive test suite (`test_excel_attachment_fix.py`) that verifies:
- ✅ Correct MIME type detection for all three Excel formats
- ✅ Case-insensitive extension handling
- ✅ Proper attachment filenames
- ✅ Backward compatibility (defaults to `.xlsx` if no filename provided)

## Impact
- **Excel files will no longer be corrupted** when sent via email
- The fix preserves the original file extension and uses the correct MIME type
- Backward compatible - existing code that doesn't provide a filename will still work (defaults to `.xlsx`)

## Files Modified
1. `email_notification.py` - Added MIME type detection and filename preservation
2. `promoter_app.py` - Updated to pass original filename (both email flows)
3. `quickopt_app.py` - Updated to pass original filename
4. `test_excel_attachment_fix.py` - New comprehensive test suite
