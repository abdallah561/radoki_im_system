/**
 * auto-logout.js — Inactivity-based automatic session logout
 *
 * Configuration (set via window.RADOKI_AUTO_LOGOUT before this script loads):
 *   csrfToken      — Django CSRF token for the AJAX POST request
 *   logoutUrl      — Server-side logout endpoint (POST, invalidates session)
 *   loginUrl       — Where to redirect after logout
 *   timeoutSeconds — Total inactivity timeout (default: 20)
 *   warningSeconds — How many seconds before timeout to show the warning modal (default: 10)
 */
(function () {
  'use strict';

  const cfg            = window.RADOKI_AUTO_LOGOUT || {};
  const TIMEOUT_MS     = (cfg.timeoutSeconds || 20) * 1000;
  const WARNING_MS     = (cfg.warningSeconds || 10) * 1000;
  const WARN_AFTER_MS  = TIMEOUT_MS - WARNING_MS;

  let idleTimer        = null;
  let warnTimer        = null;
  let countdownInterval = null;
  let secondsLeft      = 0;
  let modalVisible     = false;
  let logoutInProgress = false;

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

  /* ── Show warning modal ── */
  function showWarning() {
    if (logoutInProgress) return;
    
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
  }

  /* ── Perform server-side logout then redirect ── */
  function performLogout() {
    if (logoutInProgress) return;
    logoutInProgress = true;

    clearInterval(countdownInterval);
    clearTimeout(idleTimer);
    clearTimeout(warnTimer);

    hideModalElement();

    const done = function () {
      window.location.href = (cfg.loginUrl || '/accounts/login/') +
        '?next=' + encodeURIComponent(window.location.pathname) +
        '&reason=idle';
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
        timeout: 5000,
      }).then(done).catch(done);
      
      /* Failsafe: redirect anyway after 2 seconds */
      setTimeout(done, 2000);
    } catch (e) {
      done();
    }
  }

  /* ── Reset inactivity timers (only called when modal is NOT visible) ── */
  function resetTimer() {
    /* Do NOT reset while warning modal is showing */
    if (modalVisible) return;

    clearTimeout(idleTimer);
    clearTimeout(warnTimer);

    warnTimer = setTimeout(showWarning,     WARN_AFTER_MS);
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
      if (modal && modal.contains(e.target)) return;
      
      resetTimer();
    }, { passive: true, capture: true });
  });

  /* ── Handle visibility change (tab switching, phone lock screen) ── */
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'visible') {
      resetTimer();
    }
  });

  /* ── "Stay Logged In" button ── */
  document.addEventListener('DOMContentLoaded', function () {
    var stayBtn = document.getElementById('autoLogoutStayBtn');
    if (stayBtn) {
      stayBtn.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        hideWarning();
        resetTimer();
      });
    }
  });

  /* ── Kick off ── */
  resetTimer();

}());
