# 10-Minute Inactivity Timeout Implementation

## Overview

This implementation provides a robust auto-logout feature based on user inactivity. The system monitors user interactions and automatically logs them out after 10 minutes of inactivity, with a 60-second warning modal displayed at the 9-minute mark.

## Technical Architecture

### 1. Server-Side Configuration (`radoki/settings.py`)

```python
# Session Configuration
SESSION_COOKIE_AGE = 600  # 10 minutes in seconds
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # Expire session when browser closes
SESSION_SAVE_EVERY_REQUEST = True  # Update session on every request to track inactivity
SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript from accessing session cookie
```

**Why these settings:**

- `SESSION_COOKIE_AGE`: Sets the maximum session lifetime to 10 minutes
- `SESSION_SAVE_EVERY_REQUEST`: Ensures the server-side session is updated on every request, which effectively resets the session expiration timer on the server when user is active
- `SESSION_EXPIRE_AT_BROWSER_CLOSE`: Provides additional security by expiring the session when the browser is closed
- `SESSION_COOKIE_HTTPONLY`: Prevents XSS attacks from accessing the session cookie

### 2. Client-Side Configuration (`templates/core/base.html`)

```javascript
window.RADOKI_AUTO_LOGOUT = {
  csrfToken: "{{ csrf_token }}", // CSRF token for secure AJAX requests
  logoutUrl: "{% url 'accounts:auto_logout' %}",
  keepAliveUrl: "{% url 'accounts:keep_alive' %}",
  loginUrl: "{% url 'accounts:login' %}",
  timeoutSeconds: 600, // 10 minutes of inactivity before logout
  warningSeconds: 60, // Show warning modal 60 seconds before logout (at 9-minute mark)
};
```

### 3. Backend Endpoints (`accounts/views.py`)

#### `keep_alive_view` (POST `/accounts/keep-alive/`)

- **Purpose**: Refresh the server-side session without disturbing the user
- **Called by**: JavaScript during user activity detection
- **Behavior**:
  - Requires authenticated user
  - Returns 401 for unauthenticated requests
  - Resets session expiration on server due to `SESSION_SAVE_EVERY_REQUEST = True`
  - Responds with JSON status

#### `auto_logout_view` (POST `/accounts/auto-logout/`)

- **Purpose**: Terminate the session when inactivity timeout occurs
- **Behavior**:
  - Requires authenticated user
  - Invalidates the session server-side using Django's `logout()` function
  - Clears all session data
  - Responds with JSON status

### 4. Frontend JavaScript (`static/js/auto-logout.js`)

#### Key Functions:

**`resetTimer()`**

- Called on user activity or tab visibility change
- Clears existing timeout/warning timers
- Calls `callKeepAlive()` to refresh server session
- Schedules warning modal at 9-minute mark
- Schedules logout at 10-minute mark

**`callKeepAlive()`**

- Makes POST request to `/accounts/keep-alive/` endpoint
- Refreshes server-side session
- Executed on every user interaction

**`showWarning()`**

- Displays modal at 9-minute mark
- Starts 60-second countdown display
- Updates SVG ring visualization
- Prevents further timer resets while modal is shown

**`performLogout()`**

- Calls `/accounts/auto-logout/` to invalidate session server-side
- Redirects to login page with `?reason=session_expired` parameter
- Includes 2-second failsafe redirect if AJAX fails

#### Activity Detection:

The system monitors these user interactions:

```javascript
("mousemove",
  "mousedown",
  "click",
  "keydown",
  "keypress",
  "touchstart",
  "touchmove",
  "scroll",
  "wheel",
  "focus");
```

**Exception**: Activity originating from the modal itself is ignored, allowing users to interact with the warning message without extending the session.

### 5. Warning Modal Component

**Location**: `templates/core/base.html`

**Features**:

- Centered modal with professional design
- SVG ring visualization showing remaining time
- Real-time countdown (60 seconds → 0)
- "Stay Logged In" button to dismiss modal and extend session
- "Logout Now" button for immediate logout
- Gradient header with shield icon
- Responsive design for mobile devices

**Styling**:

- Uses CSS variables for theming
- Smooth animations and transitions
- Accessible ARIA labels

### 6. Login Page Enhancement (`accounts/views.py`)

```python
def login_view(request):
    # Check for session expiration reason
    reason = request.GET.get('reason')
    if reason == 'session_expired':
        messages.warning(
            request,
            'Your session has expired due to inactivity. Please log in again to continue.'
        )
```

**Result**: Users see a clear warning message when redirected after timeout.

## User Experience Flow

### Scenario 1: Active User (No Logout)

1. User logs in ✓
2. JavaScript timer starts (10 minutes)
3. User moves mouse at 5 minutes → Timer resets
4. User types at 7 minutes → Timer resets
5. User continues working → Session remains active

### Scenario 2: Inactive User (With Warning)

1. User logs in ✓
2. JavaScript timer starts (10 minutes)
3. User is inactive for 9 minutes → Timer triggers
4. **Warning Modal appears** with 60-second countdown ⚠️
5. User has 60 seconds to:
   - Click "Stay Logged In" → Session extends for another 10 minutes
   - Move mouse/keyboard → Session extends (after dismissing modal)
   - Click "Logout Now" → Immediate logout
6. If user does nothing for 60 seconds → Automatic logout

### Scenario 3: Inactive User (No Warning Response)

1. Warning modal shows at 9:00
2. User ignores warning
3. Timer counts down from 60 to 0
4. At 10:00 mark → Automatic logout
5. Server-side session is invalidated
6. Client redirected to login page
7. Login page shows: "Your session has expired due to inactivity"

## Security Considerations

### Client-Side Protection

- ✓ CSRF token validation for all AJAX requests
- ✓ Credentials sent with `same-origin` policy
- ✓ HTTPOnly cookie prevents JavaScript access
- ✓ Secure headers in production (HTTPS only, HSTS)

### Server-Side Protection

- ✓ `SESSION_COOKIE_HTTPONLY = True` prevents XSS exploitation
- ✓ Session invalidation removes all authentication data
- ✓ `@login_required` decorators protect views
- ✓ CSRF middleware validates POST requests

### Edge Cases Handled

- ✓ Tab hidden (browser minimized/switched away) → Timers pause
- ✓ Modal open during activity → Timer only resets on "Stay Logged In" or outside modal interaction
- ✓ Network error during logout → Failsafe redirect after 2 seconds
- ✓ User disabled JavaScript → Session still expires server-side at 10 minutes

## Testing

Run the test suite:

```bash
python manage.py test test_inactivity_timeout
```

Test cases cover:

- Session configuration verification
- Keep-alive endpoint functionality
- Auto-logout endpoint functionality
- Session clearing on logout
- Login page message display
- JavaScript file accessibility
- Modal element presence

## Deployment Checklist

- [ ] Verify `SESSION_COOKIE_AGE = 600` in production settings
- [ ] Verify `SESSION_SAVE_EVERY_REQUEST = True` is enabled
- [ ] Test keep-alive endpoint: POST `/accounts/keep-alive/`
- [ ] Test auto-logout endpoint: POST `/accounts/auto-logout/`
- [ ] Test modal displays at 9-minute mark
- [ ] Test warning countdown works correctly
- [ ] Test "Stay Logged In" button extends session
- [ ] Test redirect to login with `?reason=session_expired`
- [ ] Verify message displays on login page
- [ ] Test on mobile devices for touch event detection
- [ ] Test with network throttling (simulating slow connection)
- [ ] Run load tests to verify session keep-alive performance

## Browser Compatibility

- ✓ Chrome/Edge 90+
- ✓ Firefox 88+
- ✓ Safari 14+
- ✓ Mobile Safari (iOS 14+)
- ✓ Android Chrome

**Fallback**: Browsers without JavaScript support still get server-side timeout after 10 minutes due to `SESSION_COOKIE_AGE`.

## Performance Considerations

### Keep-Alive Calls

- **Frequency**: On every user interaction (mouse move, click, key press, scroll, touch)
- **Load**: Minimal - simple POST request without response body processing
- **Throttling**: Not implemented by default, but can be added if needed

**Optional Optimization**: Add debounce to reduce keep-alive calls:

```javascript
// In auto-logout.js - add this after callKeepAlive function
let lastKeepAliveTime = 0;
const KEEP_ALIVE_THROTTLE_MS = 10000; // Call keep-alive max every 10 seconds

function callKeepAliveThrottled() {
  const now = Date.now();
  if (now - lastKeepAliveTime >= KEEP_ALIVE_THROTTLE_MS) {
    lastKeepAliveTime = now;
    callKeepAlive();
  }
}
```

### Modal Rendering

- SVG ring updates 60 times per second (countdown)
- CSS animations use GPU acceleration for smoothness
- No heavy DOM manipulations

## Debugging

Enable console logging in JavaScript:

```javascript
// In static/js/auto-logout.js, change:
const DEBUG = false; // Change to true
```

This will output:

```
[auto-logout] Activity detected - timer reset (10 minutes until timeout)
[auto-logout] Keep-alive call successful - session refreshed on server
[auto-logout] WARNING MODAL TRIGGERED - User has 60 seconds to respond
[auto-logout] User clicked "Stay Logged In" button
[auto-logout] LOGGING OUT - Session terminated due to inactivity
```

## Future Enhancements

1. **Configurable Timeout**: Add admin settings to customize timeout duration per user role
2. **Activity-Specific Exemptions**: Exclude certain pages (like video playback) from inactivity tracking
3. **Granular Session Renewal**: Implement sliding window sessions (extend on every request instead of waiting 10 minutes)
4. **Multi-Tab Coordination**: Prevent logout if user is active in another tab
5. **Notification Preferences**: Allow users to opt-out of auto-logout
6. **Session Expiry Warnings**: Show countdown before reaching the warning modal
7. **Recovery Option**: Allow re-login without full page reload using modal form

## Support

For issues or questions:

1. Check browser console for JavaScript errors
2. Enable DEBUG mode for detailed logs
3. Verify endpoints are accessible: `/accounts/keep-alive/`, `/accounts/auto-logout/`
4. Check Django logs for keep-alive request status
5. Review test results: `python manage.py test test_inactivity_timeout -v 2`
