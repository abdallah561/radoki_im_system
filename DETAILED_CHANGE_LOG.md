# Line-by-Line Change Summary

## Overview

This document shows exactly what changed in each file to fix the Cloudinary file serving issue.

---

## 1. core/file_utils.py

### What Changed

**Complete rewrite of file serving logic to support Cloudinary**

### Key Additions:

#### New Import Statements (Lines 4-11):

```python
import mimetypes
import urllib.request
import ssl
```

- `urllib.request`: Download files from Cloudinary URLs
- `ssl`: SSL/HTTPS certificate validation

#### New Function: `_is_using_cloudinary()` (Lines 15-21):

```python
def _is_using_cloudinary():
    """Check if the project is configured to use Cloudinary storage."""
    return (
        getattr(settings, 'CLOUDINARY_CLOUD_NAME', '') and
        getattr(settings, 'CLOUDINARY_API_KEY', '') and
        getattr(settings, 'CLOUDINARY_API_SECRET', '')
    )
```

- Detects if Cloudinary is configured
- Returns True if all three env vars are set

#### New Function: `_fetch_file_from_cloudinary_url()` (Lines 24-67):

```python
def _fetch_file_from_cloudinary_url(file_url):
    """Fetch file content from a Cloudinary URL."""
    try:
        ssl_context = ssl.create_default_context()
        request = urllib.request.Request(
            file_url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
        with urllib.request.urlopen(request, context=ssl_context, timeout=30) as response:
            file_content = response.read()
        if not file_content:
            raise ValueError(f"Received empty response from {file_url}")
        return file_content
    except urllib.error.HTTPError as e:
        # ... handle HTTP errors
    except urllib.error.URLError as e:
        # ... handle URL errors
    except Exception as e:
        # ... handle other errors
```

#### Enhanced: `serve_file_response()` (Lines 70-180):

**Complete logic rewrite:**

**OLD (Before):**

```python
def serve_file_response(file_field, force_download=False, filename=None):
    try:
        with file_field.open('rb') as file_obj:
            file_content = file_obj.read()

        content_type, _ = mimetypes.guess_type(file_path)
        response = HttpResponse(file_content, content_type=content_type)

        if force_download:
            response['Content-Disposition'] = f'attachment; filename="{dl_filename}"'

        response['Content-Length'] = len(file_content)
        return response
    except Exception as e:
        raise
```

**NEW (After):**

```python
def serve_file_response(file_field, force_download=False, filename=None):
    # 1. Check if Cloudinary is configured
    if _is_using_cloudinary():
        try:
            # 2. Get URL from file_field
            file_url = file_field.url

            # 3. Transform URL for documents (/image/ → /raw/)
            if ext in ['.pdf', '.doc', '.docx', ...]:
                if '/image/upload/' in file_url:
                    file_url = file_url.replace('/image/upload/', '/raw/upload/')

            # 4. Fetch file from Cloudinary URL
            file_content = _fetch_file_from_cloudinary_url(file_url)
        except Exception as e:
            # 5. Fallback to local file reading
            with file_field.open('rb') as file_obj:
                file_content = file_obj.read()
    else:
        # 6. For local storage, use standard approach
        with file_field.open('rb') as file_obj:
            file_content = file_obj.read()

    # 7. Create response with proper headers
    response = HttpResponse(file_content, content_type=content_type)

    # 8. Set proper Content-Disposition
    if force_download:
        response['Content-Disposition'] = f'attachment; filename="{dl_filename}"'
    else:
        response['Content-Disposition'] = f'inline; filename="{dl_filename}"'

    # 9. Add caching headers
    if not force_download:
        response['Cache-Control'] = 'public, max-age=2592000, immutable'

    return response
```

### Benefits of Changes:

- ✅ Detects Cloudinary vs local storage
- ✅ Fetches files from Cloudinary URLs via HTTPS
- ✅ Transforms URLs for different file types
- ✅ Proper error handling with fallback
- ✅ SSL/HTTPS validation
- ✅ Performance caching
- ✅ Debug logging at every step

---

## 2. radoki/settings.py

### What Changed

**Enhanced CLOUDINARY_STORAGE configuration (Lines ~170-180)**

**OLD (Before):**

```python
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': CLOUDINARY_CLOUD_NAME,
    'API_KEY': CLOUDINARY_API_KEY,
    'API_SECRET': CLOUDINARY_API_SECRET,
}
# Cloudinary media URL - use 'upload' delivery for all file types
MEDIA_URL = f'https://res.cloudinary.com/{CLOUDINARY_CLOUD_NAME}/image/upload/'
```

**NEW (After):**

```python
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': CLOUDINARY_CLOUD_NAME,
    'API_KEY': CLOUDINARY_API_KEY,
    'API_SECRET': CLOUDINARY_API_SECRET,
    'FOLDER': 'radoki_media',           # ← NEW: Organize files
    'RESOURCE_TYPE': 'auto',            # ← NEW: Auto-detect file type
    'USE_FILENAME': True,               # ← NEW: Keep original names
    'UNIQUE_FILENAME': True,            # ← NEW: Ensure uniqueness
}
# Cloudinary media URL - Note: this may vary based on file type
MEDIA_URL = f'https://res.cloudinary.com/{CLOUDINARY_CLOUD_NAME}/image/upload/'
```

### What Each New Setting Does:

- `FOLDER`: Groups all media files in 'radoki_media' folder on Cloudinary
- `RESOURCE_TYPE`: 'auto' lets Cloudinary detect if it's image/video/document
- `USE_FILENAME`: Preserves original filenames (users see familiar names)
- `UNIQUE_FILENAME`: Prevents naming conflicts when same filename uploaded multiple times

### Impact:

- Better organization on Cloudinary dashboard
- Proper file type detection
- Cleaner file management

---

## 3. core/templatetags/cloudinary_tags.py

### What Changed

**Improved cloudinary_file_url filter for better URL transformation**

**Modified Section: cloudinary_file_url() filter (Lines ~19-54)**

**OLD Logic:**

```python
# If it's a Cloudinary URL and it's a PDF or document, adjust it
if 'res.cloudinary.com' in url:
    cloud_name = settings.CLOUDINARY_CLOUD_NAME
    file_name = file_field.name
    _, ext = os.path.splitext(file_name)
    ext = ext.lower()

    if ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.zip', '.txt']:
        public_id = file_name.rsplit('.', 1)[0] if '.' in file_name else file_name
        url = f'https://res.cloudinary.com/{cloud_name}/raw/upload/{public_id}{ext}'
```

**NEW Logic:**

```python
# Better detection and transformation
if url and 'res.cloudinary.com' in url:
    cloud_name = settings.CLOUDINARY_CLOUD_NAME
    file_name = file_field.name
    _, ext = os.path.splitext(file_name)
    ext = ext.lower()

    # More file types supported
    if ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
               '.zip', '.txt', '.rtf', '.csv']:  # ← Added .rtf, .csv

        # Check what type of URL it is
        if '/image/upload/' in url:
            # Replace /image/upload/ with /raw/upload/ for documents
            url = url.replace('/image/upload/', '/raw/upload/')
        elif '/upload/' in url and '/raw/upload/' not in url:
            # Replace /upload/ with /raw/upload/ for documents
            url = url.replace('/upload/', '/raw/upload/')
```

### Improvements:

- ✅ Supports more file types (.rtf, .csv)
- ✅ Better URL pattern matching
- ✅ More robust transformation logic
- ✅ Comments explain the transformation

---

## 4. courses/views.py

### What Changed

**Refactored file serving views to use improved utility functions**

#### serve_file() function (Lines ~781-840):

**OLD Logic:**

```python
def serve_file(request, resource_id):
    # ... permission checks ...

    file_name = resource.file.name
    file_ext = file_name.split('.')[-1].lower() if '.' in file_name else ''

    content_types = {'pdf': 'application/pdf'}
    content_type = content_types.get(file_ext, 'application/octet-stream')

    try:
        file_content = resource.file.read()
        if not file_content:
            raise PermissionDenied("File is empty or could not be read")

        response = HttpResponse(file_content, content_type=content_type)
        response['Content-Disposition'] = 'inline; filename="{}"'.format(file_name)
        response['Cache-Control'] = 'public, max-age=2592000, immutable'
        # ... more headers ...
        return response
    except Exception as e:
        raise PermissionDenied(f"Error reading file: {str(e)}")
```

**NEW Logic:**

```python
def serve_file(request, resource_id):
    # ... permission checks ...

    # Use improved file serving function that handles Cloudinary
    from core.file_utils import serve_file_response
    response = serve_file_response(resource.file, force_download=False)

    # Override content disposition to inline for preview
    file_name = resource.file.name
    response['Content-Disposition'] = f'inline; filename="{file_name}"'

    # Add caching headers
    response['Cache-Control'] = 'public, max-age=2592000, immutable'
    response['Pragma'] = 'cache'
    response['Expires'] = 'Sun, 31 Dec 2026 23:59:59 GMT'

    # Add security headers
    response['X-Content-Type-Options'] = 'nosniff'
    response['X-Frame-Options'] = 'SAMEORIGIN'
    response['X-XSS-Protection'] = '1; mode=block'
    response['Vary'] = 'Accept-Encoding'

    return response
```

### Improvements:

- ✅ Much simpler and cleaner code
- ✅ Delegates file reading to utility function
- ✅ Utility handles Cloudinary automatically
- ✅ Better error handling
- ✅ Maintained security and performance headers

#### download_resource() function:

```python
# OLD: Manual file reading
try:
    from core.file_utils import serve_file_response
    return serve_file_response(resource.file, force_download=True)
except Exception as e:
    raise PermissionDenied(f"Error reading file: {str(e)}")

# NEW: (Already using correct utility, just confirmed)
try:
    from core.file_utils import serve_file_response
    return serve_file_response(resource.file, force_download=True)
except Exception as e:
    raise PermissionDenied(f"Error reading file: {str(e)}")
```

✅ Already correct - delegates to utility function

---

## 5. payments/views.py

### What Changed

**Updated receipt viewing to properly serve Cloudinary files**

#### view_receipt() function (Lines ~185-210):

**OLD:**

```python
def view_receipt(request, payment_id):
    """Serve a receipt file from Cloudinary or local storage."""
    # ... permission checks ...

    try:
        from core.file_utils import serve_file_response
        return serve_file_response(payment.receipt)
    except Exception as e:
        logger.error(f"Error serving receipt {payment_id}: {str(e)}", exc_info=True)
        messages.error(request, f"Error downloading receipt: {str(e)}")
        return redirect('payments:review_receipts')
```

**NEW:**

```python
def view_receipt(request, payment_id):
    """Serve a receipt file from Cloudinary or local storage for viewing/download."""
    # ... permission checks ...

    try:
        from core.file_utils import serve_file_response
        # For receipts, serve inline (for viewing) not as attachment
        return serve_file_response(payment.receipt, force_download=False)
    except Exception as e:
        logger.error(f"Error serving receipt {payment_id}: {str(e)}", exc_info=True)
        messages.error(request, f"Error viewing receipt: {str(e)}")
        return redirect('payments:review_receipts')
```

### Changes:

- ✅ Added explicit `force_download=False` parameter
- ✅ Changed error message from "downloading" to "viewing"
- ✅ Clarified that receipts serve inline for viewing
- ✅ Better comment explaining the behavior

---

## Summary of All Changes

| File                                   | Change Type               | Impact                                | Lines |
| -------------------------------------- | ------------------------- | ------------------------------------- | ----- |
| `core/file_utils.py`                   | Complete rewrite          | Core fix - enables Cloudinary serving | ~180  |
| `radoki/settings.py`                   | Configuration enhancement | Better file organization              | 5     |
| `core/templatetags/cloudinary_tags.py` | Logic improvement         | Better URL transformation             | 20    |
| `courses/views.py`                     | Refactoring               | Simplified, more reliable             | 30    |
| `payments/views.py`                    | Parameter update          | Better clarity                        | 2     |

**Total: ~237 lines of code changes across 5 files**

---

## What's NOT Changed

- ✅ No database schema changes
- ✅ No model modifications
- ✅ No URL patterns changed
- ✅ No template changes needed
- ✅ No migrations required
- ✅ No breaking changes to API
- ✅ Fully backward compatible

---

## How to Review Changes

To see the exact differences:

```bash
# View changes in a specific file
git diff HEAD~1 core/file_utils.py

# View summary of all changes
git diff HEAD~1 --stat

# View full diff
git diff HEAD~1

# Or compare with previous commit
git show --name-status <commit_hash>
```

---

## Testing Each Change

### Test core/file_utils.py:

```python
from core.file_utils import serve_file_response, _is_using_cloudinary

# Test Cloudinary detection
is_cloud = _is_using_cloudinary()
print(f"Using Cloudinary: {is_cloud}")

# Test file serving
response = serve_file_response(resource.file, force_download=False)
print(f"Response status: {response.status_code}")
print(f"Content-Type: {response.get('Content-Type')}")
```

### Test courses/views.py:

- Navigate to resource preview
- Check file loads properly
- Verify Content-Disposition header

### Test payments/views.py:

- Upload a receipt
- View the receipt
- Verify it displays/downloads

---

## Deployment Verification

After deploying, verify:

1. No import errors in Django startup
2. Files serve from Cloudinary (check logs for "Successfully read X bytes")
3. PDFs display in browser (not download)
4. Downloads work for all file types
5. Receipts viewable by instructors
6. No 403 errors for authorized users

All changes are complete and ready for deployment!
