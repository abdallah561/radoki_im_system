# Pre-Deployment Checklist

## Code Review Checklist

### File Changes Review:

- [x] `core/file_utils.py` - Complete rewrite
  - [x] `_is_using_cloudinary()` function added
  - [x] `_fetch_file_from_cloudinary_url()` function added
  - [x] `serve_file_response()` enhanced with Cloudinary support
  - [x] Error handling for HTTP, URL, and timeout errors
  - [x] Proper logging at DEBUG level
  - [x] Fallback mechanism to local storage

- [x] `radoki/settings.py` - Cloudinary configuration
  - [x] FOLDER setting added
  - [x] RESOURCE_TYPE set to 'auto'
  - [x] USE_FILENAME and UNIQUE_FILENAME settings

- [x] `core/templatetags/cloudinary_tags.py` - Template improvements
  - [x] Better document type detection
  - [x] Improved URL transformation logic
  - [x] Support for more file types

- [x] `courses/views.py` - Resource serving
  - [x] `preview_resource()` view
  - [x] `serve_file()` using new utility
  - [x] `download_resource()` using new utility
  - [x] `download_lesson_resource()` using new utility

- [x] `payments/views.py` - Receipt viewing
  - [x] `view_receipt()` updated to use new utility

---

## Environment Variables Check

Verify these are set in Render:

```
☐ CLOUDINARY_CLOUD_NAME=<your_cloud_name>
☐ CLOUDINARY_API_KEY=<your_api_key>
☐ CLOUDINARY_API_SECRET=<your_api_secret>
☐ DEBUG=False (Production)
☐ DATABASE_URL=<neon_postgres_url>
☐ SECRET_KEY=<your_secret_key>
```

**How to Check in Render:**

1. Go to Render Dashboard
2. Select your service
3. Settings → Environment
4. Verify all Cloudinary variables are present

---

## Syntax & Import Verification

### Imports Added:

- [x] `import ssl` - for SSL context
- [x] `import urllib.request` - for fetching files
- [x] `import mimetypes` - already existed, enhanced usage
- [x] No breaking imports removed

### All Modified Files Should Import Correctly:

```python
# Test imports in Django shell:
python manage.py shell

# Then test:
from core.file_utils import serve_file_response, _is_using_cloudinary
from courses.views import preview_resource, serve_file, download_resource
from payments.views import view_receipt

# If no errors, imports are working
```

---

## Git Commit Message Template

```
Fix: Implement proper Cloudinary file serving for resources and receipts

CHANGES:
- Refactor core/file_utils.py to fetch files from Cloudinary URLs
- Add _is_using_cloudinary() helper to detect storage backend
- Add _fetch_file_from_cloudinary_url() to download files via HTTPS
- Update serve_file_response() to handle both Cloudinary and local storage
- Transform document URLs from /image/upload/ to /raw/upload/
- Add SSL/HTTPS validation and error handling
- Add comprehensive logging for debugging
- Update courses/views.py to use improved file serving
- Update payments/views.py for receipt handling
- Enhance cloudinary_tags.py for better URL handling
- Update settings.py with better Cloudinary configuration

FIXES:
- Resources can now be previewed and downloaded from Cloudinary
- Receipts can now be viewed/downloaded without permission errors
- Proper Content-Disposition headers for inline/attachment serving
- Better performance with caching headers
- Fallback to local storage if Cloudinary fails

TESTING:
- Test resource preview (PDFs should display in browser)
- Test resource download (should download correctly)
- Test receipt viewing (should display/download)
- Test all user roles (student, instructor, admin)
- Monitor logs for any errors
```

---

## Pre-Deployment Testing (Local)

### 1. Start Development Server

```bash
python manage.py runserver
```

### 2. Test Resource Preview

- Create a test course (if not exists)
- Upload a PDF resource
- As enrolled student with approved payment:
  - Navigate to course
  - Click "Preview" on PDF
  - ✓ Should display in browser
  - ✓ View PDF source in browser

### 3. Test Resource Download

- Click "Download" on resource
- ✓ File should download to your computer
- ✓ File should be complete and uncorrupted

### 4. Test Receipt Viewing

- Upload a receipt payment
- As student:
  - Go to dashboard
  - View receipt
  - ✓ Should display or download
- As instructor:
  - Go to review receipts
  - Click on receipt
  - ✓ Should display or download

### 5. Test Logging

- Enable DEBUG logging in settings
- Tail the debug log: `tail -f debug.log`
- Download a file and verify:
  - ✓ "Original file URL from cloudinary_storage"
  - ✓ "Successfully read X bytes"
  - ✓ "Content-Type determined as"

### 6. Test Error Handling

- Try accessing non-existent file
- ✓ Should get proper error message
- ✓ No crashes or 500 errors

---

## Production Deployment Steps

### Step 1: Backup (Just in Case)

```bash
# If using Neon for database:
# Take backup via Neon dashboard
# Backup is automatic, but good to note it
```

### Step 2: Push to GitHub

```bash
git add -A
git commit -m "Fix: Implement proper Cloudinary file serving for resources and receipts

[Include template message from above]"

git push origin main
```

### Step 3: Monitor Render Build

1. Go to Render Dashboard
2. Click on your service (radoki-im-system)
3. Watch the "Latest Deploy" section
4. Wait for status to change to "Live" (green)
5. If fails, click on deploy to see error logs

### Step 4: Post-Deployment Validation (Critical!)

1. Go to https://radoki-im-system.onrender.com
2. Login as a student account
3. Navigate to a course with resources
4. Test preview resource (PDF) - MUST work
5. Test download resource - MUST work
6. Test receipt viewing (if payment made) - MUST work
7. Verify no 403/404/500 errors

### Step 5: Monitor Logs

```
In Render Dashboard:
Settings → Logs → View Logs

Look for:
✓ No 500 errors
✓ No permission denied for authorized users
✓ File serving completing successfully
✗ If errors appear, rollback or fix
```

---

## Rollback Plan (If Issues Occur)

If production deployment fails:

### Option 1: Quick Rollback

```bash
# Revert last commit
git revert HEAD
git push origin main

# Or go back to previous commit
git reset --hard <previous_commit_hash>
git push origin main --force
```

### Option 2: Check Logs

```
In Render Dashboard:
1. Settings → Logs
2. Search for ERROR or 500
3. Note the error message
4. Review TROUBLESHOOTING_FILE_SERVING.md
```

### Option 3: Fix & Redeploy

```bash
# Fix the issue locally
# Test locally with: python manage.py runserver
# Commit fix
# Push to GitHub
# Monitor new deployment
```

---

## Post-Deployment Monitoring

### Daily Check (First Week)

- [ ] Check Render logs for errors
- [ ] Test resource preview (1-2 resources)
- [ ] Test receipt viewing (if payments exist)
- [ ] Monitor Cloudinary API usage

### Weekly Check (After First Week)

- [ ] Review error logs
- [ ] Check Cloudinary API quota usage
- [ ] Verify no permission issues reported
- [ ] Monitor performance metrics

### Monthly Check

- [ ] Review comprehensive logs
- [ ] Check for any file serving issues
- [ ] Update any broken links
- [ ] Assess performance and caching effectiveness

---

## Success Criteria

Deployment is successful if:

✅ Resources can be previewed in browser (PDFs)
✅ Resources can be downloaded for all file types
✅ Receipts can be viewed/reviewed by instructors
✅ No 403 "Permission Denied" errors for authorized users
✅ Proper error messages for unauthorized access
✅ Files complete and uncorrupted
✅ No crashes or 500 errors
✅ Performance is acceptable
✅ All user roles (student, instructor, admin) work correctly

---

## Quick Reference: Critical URLs to Test

```
Resource Preview:
https://radoki-im-system.onrender.com/courses/resource/{resource_id}/serve/

Resource Download:
https://radoki-im-system.onrender.com/courses/resource/{resource_id}/download/

Lesson Resource Download:
https://radoki-im-system.onrender.com/courses/lesson/{lesson_id}/resource/download/

Receipt View:
https://radoki-im-system.onrender.com/payments/receipt/{payment_id}/view/
```

---

## Emergency Contact Points

If deployment fails and you need to check:

1. **Cloudinary Status**: https://status.cloudinary.com/
2. **Render Status**: https://status.render.com/
3. **Neon Status**: https://status.neon.tech/
4. **Django Docs**: https://docs.djangoproject.com/

---

## Notes

- This fix is backward compatible (works with both Cloudinary and local storage)
- No database migrations needed
- No changes to models
- Safe to deploy during any time
- Can be deployed with other pending changes (independent feature)

---

## Sign-Off

Before deploying:

- [ ] All code review items checked
- [ ] Tested locally
- [ ] Environment variables verified in Render
- [ ] Backup plan understood
- [ ] Success criteria understood
- [ ] Ready to deploy

**Date of Deployment:** ****\_\_\_****
**Deployed By:** ****\_\_\_****
**Result:** ****\_\_\_****
