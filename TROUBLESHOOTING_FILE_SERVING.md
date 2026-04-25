# Quick Reference: File Serving Troubleshooting

## File Serving Flow Diagram

```
User Request (Preview/Download Resource)
        ↓
Permission Check (Login, Enrollment, Payment)
        ↓
Retrieve FileField from Database
        ↓
serve_file_response() called
        ↓
├─→ Is Cloudinary Configured?
│   ├─→ YES: Fetch from URL via urllib
│   │   ├─→ Get file_field.url
│   │   ├─→ Transform URL if document (/image/upload/ → /raw/upload/)
│   │   ├─→ Fetch content via HTTPS
│   │   └─→ Return HttpResponse
│   └─→ NO: Read from local storage
│       ├─→ Open file_field locally
│       ├─→ Read file content
│       └─→ Return HttpResponse
```

---

## Common Issues & Solutions

### Issue 1: "Permission Denied" Error

**Symptoms:**

- Users get 403 error when trying to view/download
- "You don't have permission to access this resource"

**Checklist:**

```
□ Is user logged in? Check request.user.is_authenticated
□ Is student enrolled in course? SELECT * FROM courses_enrollment WHERE student_id=X
□ Is payment approved? SELECT approved FROM payments_payment WHERE enrollment_id=X
□ Is user the instructor? Check course.instructor == request.user
□ Is resource download allowed? SELECT download_allowed FROM courses_resource WHERE id=X
```

**Solution:**

- For students: Check enrollment and payment status
- For instructors: Verify course ownership
- For downloads: Enable download permission on resource

---

### Issue 2: "File Not Found" or Empty Response

**Symptoms:**

- HTTP 200 but empty/blank response
- Browser can't display file
- "Received empty response from URL"

**Checklist:**

```
□ Does file exist in Cloudinary? Check Cloudinary dashboard
□ Is file_field.name correct? Check database: SELECT file FROM courses_resource WHERE id=X
□ Is Cloudinary configured? Check CLOUDINARY_CLOUD_NAME in settings
□ Is file size > 0? Check file isn't empty
□ Check logs: Look for "Successfully read X bytes" message
```

**Solution:**

1. Verify file exists in Cloudinary: `res.cloudinary.com/{cloud_name}/raw/upload/{file_path}`
2. Check file_field.name doesn't have extra spaces: `.strip()`
3. Ensure file wasn't recently deleted

---

### Issue 3: "Cannot Connect to Cloudinary" / Timeout

**Symptoms:**

- Timeout errors (30 second limit)
- SSL certificate errors
- "URLError: [SSL: CERTIFICATE_VERIFY_FAILED]"

**Checklist:**

```
□ Is internet working on server? Test curl/wget
□ Is Cloudinary API up? Check status.cloudinary.com
□ Is file size reasonable? Very large files may timeout
□ Are credentials correct? Verify in .env file
□ Is timeout sufficient? Default is 30 seconds
```

**Solution:**

1. Check Cloudinary status
2. Verify network connectivity on server
3. For large files, increase timeout:
   ```python
   # In serve_file_response
   urlopen(..., timeout=60)  # 60 seconds for large files
   ```
4. Split large files into smaller chunks

---

### Issue 4: Wrong File Type / Content-Type

**Symptoms:**

- PDF opens as download instead of preview
- Image shows as text/plain
- "application/octet-stream" instead of proper type

**Checklist:**

```
□ Is file extension correct? Check database: SELECT file FROM courses_resource
□ Is mimetypes.guess_type() detecting correctly?
□ Is URL being transformed correctly? Should be /raw/upload/ for documents
□ Are Cloudinary settings using resource_type='auto'?
```

**Solution:**

1. Add explicit Content-Type for known extensions:
   ```python
   content_types = {
       'pdf': 'application/pdf',
       'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
       'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
   }
   ```
2. Verify URL transformation in serve_file_response()
3. Check Cloudinary RESOURCE_TYPE setting

---

### Issue 5: "Downloaded File is Corrupted"

**Symptoms:**

- File downloads but can't open
- File size is wrong
- Content appears garbled

**Checklist:**

```
□ Is file_content complete? Check "read X bytes" in logs
□ Is encoding correct? Binary files need proper handling
□ Is Content-Length header correct?
□ Is urllib fetching complete file?
```

**Solution:**

1. Verify file opens correctly in Cloudinary directly
2. Check file size matches:
   ```python
   len(file_content) == expected_size
   ```
3. Test with smaller files first
4. Check internet connection during download

---

### Issue 6: Receipt Can't Be Viewed

**Symptoms:**

- Receipt upload works but viewing fails
- "Error viewing receipt"
- Instructor can't see uploaded receipts

**Checklist:**

```
□ Is payment record created? SELECT * FROM payments_payment WHERE enrollment_id=X
□ Is receipt file saved? Check payment.receipt.name
□ User permission: Is user student/instructor/superuser?
□ File exists in Cloudinary?
```

**Solution:**

1. Check payment record exists and has receipt
2. Verify user is student/instructor/superuser
3. Ensure file was actually uploaded to Cloudinary
4. Check Cloudinary folder structure

---

## Debug Logging

### Enable Detailed Logging

Add to `radoki/settings.py`:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'debug.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'core.file_utils': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}
```

### What to Look For

```
[DEBUG] Original file URL from cloudinary_storage: https://res.cloudinary.com/xxx/image/upload/...
[DEBUG] Transformed document URL to raw delivery: https://res.cloudinary.com/xxx/raw/upload/...
[DEBUG] Successfully read 12345 bytes from resources/file.pdf
[DEBUG] Content-Type determined as: application/pdf
```

---

## Testing with cURL

### Test Cloudinary File Direct

```bash
# Direct test - should return file content
curl -I https://res.cloudinary.com/{cloud_name}/raw/upload/{file_path}

# Check response headers
curl -H "User-Agent: Mozilla/5.0" https://res.cloudinary.com/{cloud_name}/raw/upload/{file_path} | head -c 100
```

### Test Django Endpoint

```bash
# Get download link (requires login session)
curl -b cookies.txt http://localhost:8000/courses/resource/1/serve/

# With authentication (development)
curl -H "Authorization: Bearer {token}" http://localhost:8000/courses/resource/1/serve/
```

---

## Quick Fixes Checklist

**File Not Serving:**

- [ ] Check Cloudinary dashboard - file exists?
- [ ] Check database - file_field.name correct?
- [ ] Check logs - any error messages?
- [ ] Verify permission checks passed
- [ ] Test with local file first

**Permission Issues:**

- [ ] Is user logged in?
- [ ] Is student enrolled?
- [ ] Is payment approved (for students)?
- [ ] Is user the instructor (for instructors)?
- [ ] Are they superuser (admins)?

**Content-Type Issues:**

- [ ] Check file extension
- [ ] Verify URL transformation (/image/ → /raw/)
- [ ] Test with known good file first
- [ ] Check Cloudinary RESOURCE_TYPE

**Performance Issues:**

- [ ] Check network latency
- [ ] Monitor Cloudinary API
- [ ] Check server resources
- [ ] Consider adding caching
- [ ] Monitor timeout settings

---

## Contact & Support

**For Issues:**

1. Check logs: `tail -f debug.log`
2. Review this troubleshooting guide
3. Check Cloudinary API status
4. Test manually with cURL
5. Review CLOUDINARY_FILE_SERVING_FIX.md for detailed info

**For Cloudinary Issues:**

- Dashboard: https://cloudinary.com/console/
- Documentation: https://cloudinary.com/documentation
- Support: https://support.cloudinary.com/

**For Django Issues:**

- Django Docs: https://docs.djangoproject.com/
- File Upload: https://docs.djangoproject.com/en/stable/ref/models/fields/#filefield
