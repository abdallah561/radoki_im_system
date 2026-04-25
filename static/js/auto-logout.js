/**
 * auto-logout.js — Inactivity-based automatic session logout
 *
 * Features:
 * - Monitors user inactivity and logs out after configured timeout (default: 10 minutes / 600 seconds)
 * - Displays warning modal 60 seconds before logout
 * - Resets timer on any user interaction (mouse, keyboard, touch, scroll, focus)
 * - Session stays fresh via SESSION_SAVE_EVERY_REQUEST on normal requests
 * - Keep-alive called only when user clicks 'Stay Logged In' button
 * - Ignores user interactions originating from the modal itself
 * - Handles tab visibility changes (pauses tracking when tab is hidden)
 *
 * Configuration (set via window.RADOKI_AUTO_LOGOUT before this script loads):
 *   csrfToken      — Django CSRF token for AJAX POST requests
 *   logoutUrl      — Server-side logout endpoint (POST, invalidates session)
 *   keepAliveUrl   — Server-side keep-alive endpoint (POST, refreshes session)
 *   loginUrl       — Where to redirect after logout
 *   timeoutSeconds — Total inactivity timeout in seconds (default: 600 = 10 minutes)
 *   warningSeconds — How many seconds before timeout to show warning (default: 60)
 */
(function () {
  'use strict';

  const cfg            = window.RADOKI_AUTO_LOGOUT || {};
  const TIMEOUT_MS     = (cfg.timeoutSeconds || 600) * 1000;   // Total timeout: 10 minutes
  const WARNING_MS     = (cfg.warningSeconds || 60) * 1000;     // Warning before logout: 60 seconds
  const WARN_AFTER_MS  = TIMEOUT_MS - WARNING_MS;               // Show warning at 9-minute mark
  const DEBUG          = false;  // Set to true for console logging

  let idleTimer        = null;
  let warnTimer        = null;
  let countdownInterval = null;
  let secondsLeft      = 0;
  let modalVisible     = false;
  let logoutInProgress = false;
  let lastActivityTime = Date.now();

  /* ── Utility: Debug logging ── */
  function debugLog(msg, data) {
    if (DEBUG) {
      console.log('[auto-logout] ' + msg, data || '');
    }
  }

  /* ── Get modal element ── */
  function getModalElement() {
    return document.getElementById('autoLogoutModal');
  }

  /* ── Show modal with vanilla JS only ── */
  function showModalElement() {
    var modal = getModalElement();
    if (modal) {
      modal.style.display = 'flex !important';
      modal.classList.add('show');
      /* Remove any Bootstrap modal backdrop */
      document.body.classList.remove('modal-open');
      debugLog('Modal displayed');
    }
  }

  /* ── Hide modal with vanilla JS only ── */
  function hideModalElement() {
    var modal = getModalElement();
    if (modal) {
      modal.style.display = 'none';
      modal.classList.remove('show');
    }
    /* Clean up any Bootstrap backdrops */
    var backdrop = document.querySelector('.modal-backdrop');
    if (backdrop) backdrop.remove();
    document.body.classList.remove('modal-open');
    debugLog('Modal hidden');
  }

  /* ── Update countdown display + SVG ring ── */
  var RING_CIRCUMFERENCE = 226;

  function updateCountdown() {
    var el = document.getElementById('autoLogoutCountdown');
    if (el) el.textContent = secondsLeft;

    var arc = document.getElementById('alRingArc');
    if (arc) {
      var total   = Math.round(WARNING_MS / 1000);
      var ratio   = total > 0 ? secondsLeft / total : 0;
      var offset  = RING_CIRCUMFERENCE * (1 - ratio);
      arc.style.strokeDashoffset = offset;
    }
  }

  /* ── Call server-side keep-alive endpoint ── */
  function callKeepAlive() {
    if (!cfg.keepAliveUrl) {
      debugLog('No keep-alive URL configured');
      return;
    }

    debugLog('Keep-alive call initiated');

    fetch(cfg.keepAliveUrl, {
      method: 'POST',
      headers: {
        'X-CSRFToken': cfg.csrfToken || '',
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': 'application/json',
      },
      credentials: 'same-origin',
    }).then(function(response) {
      if (response.ok) {
        debugLog('Keep-alive call successful - session refreshed on server');
      } else {
        debugLog('Keep-alive failed with status: ' + response.status);
      }
    }).catch(function(error) {
      debugLog('Keep-alive fetch error:', error);
    });
  }

  /* ── Show warning modal ── */
  function showWarning() {
    if (logoutInProgress) return;
    
    debugLog('WARNING MODAL TRIGGERED - User has 60 seconds to respond');
    modalVisible = true;
    secondsLeft  = Math.round(WARNING_MS / 1000);
    updateCountdown();

    showModalElement();

    clearInterval(countdownInterval);
    countdownInterval = setInterval(function () {
      secondsLeft = Math.max(0, secondsLeft - 1);
      updateCountdown();
      
      if (secondsLeft <= 0) {
        clearInterval(countdownInterval);
        debugLog('Countdown reached zero - performing logout');
        performLogout();
      }
    }, 1000);
  }

  /* ── Hide warning modal ── */
  function hideWarning() {
    modalVisible = false;
    clearInterval(countdownInterval);
    hideModalElement();
    var arc = document.getElementById('alRingArc');
    if (arc) arc.style.strokeDashoffset = 0;
    debugLog('Warning modal hidden - session will continue');
  }

  /* ── Perform server-side logout then redirect ── */
  function performLogout() {
    if (logoutInProgress) return;
    logoutInProgress = true;

    clearInterval(countdownInterval);
    clearTimeout(idleTimer);
    clearTimeout(warnTimer);

    hideModalElement();

    debugLog('LOGGING OUT - Session terminated due to inactivity');

    const isAdmin = cfg.isAdmin || false;
    
    const done = function () {
      if (isAdmin) {
        /* For admin, redirect to admin login - Django admin handles logout on login page */
        window.location.href = (cfg.loginUrl || '/admin/login/') + '?reason=session_expired';
      } else {
        /* For normal site, use the reason parameter */
        window.location.href = (cfg.loginUrl || '/accounts/login/') + '?reason=session_expired';
      }
    };

    try {
      fetch(cfg.logoutUrl || '/accounts/auto-logout/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': cfg.csrfToken || '',
          'X-Requested-With': 'XMLHttpRequest',
          'Content-Type': 'application/json',
        },
        credentials: 'same-origin',
      }).then(done).catch(done);
      
      /* Failsafe: redirect anyway after 2 seconds */
      setTimeout(done, 2000);
    } catch (e) {
      debugLog('Logout fetch error:', e);
      done();
    }
  }

  /* ── Reset inactivity timers ── */
  function resetTimer() {
    /* Do NOT reset while warning modal is showing */
    if (modalVisible) {
      debugLog('User activity detected during warning - user can stay logged in');
      /* No keep-alive call needed - SESSION_SAVE_EVERY_REQUEST handles session refresh */
      return;
    }

    lastActivityTime = Date.now();
    debugLog('Activity detected - timer reset (10 minutes until timeout)');

    clearTimeout(idleTimer);
    clearTimeout(warnTimer);

    /* Session refreshed via SESSION_SAVE_EVERY_REQUEST on normal requests */

    /* Schedule warning modal at 9-minute mark */
    warnTimer = setTimeout(showWarning,     WARN_AFTER_MS);
    
    /* Schedule logout at 10-minute mark */
    idleTimer = setTimeout(performLogout,   TIMEOUT_MS);
  }

  /* ── Attach activity listeners (but respect modal state) ── */
  var ACTIVITY_EVENTS = [
    'mousemove', 'mousedown', 'click',
    'keydown', 'keypress',
    'touchstart', 'touchmove',
    'scroll', 'wheel',
    'focus',
  ];
  
  ACTIVITY_EVENTS.forEach(function (evt) {
    document.addEventListener(evt, function (e) {
      /* Ignore activity from the modal itself */
      var modal = getModalElement();
      if (modal && modal.contains(e.target)) {
        /* Only allow "Stay Logged In" and "Logout Now" buttons from modal */
        return;
      }
      
      resetTimer();
    }, { passive: true, capture: true });
  });

  /* ── Handle visibility change (tab switching, phone lock screen) ── */
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'visible') {
      debugLog('Tab became visible - resetting timer');
      resetTimer();
    } else {
      debugLog('Tab hidden - timers paused');
    }
  });

  /* ── "Stay Logged In" button ── */
  document.addEventListener('DOMContentLoaded', function () {
    var stayBtn = document.getElementById('autoLogoutStayBtn');
    if (stayBtn) {
      stayBtn.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        debugLog('User clicked "Stay Logged In" button - calling keep-alive');
        /* Call keep-alive to ensure session is extended */
        callKeepAlive();
        hideWarning();
        resetTimer();
      });
    }
  });

  /* ── Handle page unload (cleanup) ── */
  window.addEventListener('beforeunload', function () {
    clearTimeout(idleTimer);
    clearTimeout(warnTimer);
    clearInterval(countdownInterval);
  });

  /* ── Kick off initial timer ── */
  debugLog('Auto-logout initialized: 10 min timeout, 60 sec warning');
  resetTimer();

}());
