/**
 * auth.js
 *
 * Implements the OAuth 2.0 Authorization Code flow with PKCE (RFC 7636).
 * This is the recommended approach for browser-based SPAs – no client secret
 * is ever stored in the browser.
 *
 * Public API
 * ----------
 *   AUTH.login()                   → redirects to Cognito Hosted UI
 *   AUTH.handleCallback(code,state) → exchanges code for tokens, stores them
 *   AUTH.logout()                  → clears session, redirects to Cognito logout
 *   AUTH.isAuthenticated()         → Boolean
 *   AUTH.getAccessToken()          → String | null
 *   AUTH.getUserEmail()            → String | null
 *   AUTH.api(path, options)        → fetch wrapper that injects Authorization header
 */

const AUTH = (() => {
  // ---- token storage keys ----
  const KEY_ACCESS  = "cfm_access_token";
  const KEY_ID      = "cfm_id_token";
  const KEY_REFRESH = "cfm_refresh_token";
  const KEY_EMAIL   = "cfm_user_email";
  // ---- PKCE transient keys ----
  const KEY_VERIFIER = "cfm_code_verifier";
  const KEY_STATE    = "cfm_oauth_state";

  // ------------------------------------------------------------------ #
  // PKCE helpers
  // ------------------------------------------------------------------ #

  function _randomBytes(length) {
    const arr = new Uint8Array(length);
    crypto.getRandomValues(arr);
    return arr;
  }

  function _base64urlEncode(buffer) {
    return btoa(String.fromCharCode(...new Uint8Array(buffer)))
      .replace(/\+/g, "-")
      .replace(/\//g, "_")
      .replace(/=+$/, "");
  }

  async function _generateCodeVerifier() {
    // 32 random bytes → 43-character base64url string (within RFC spec)
    return _base64urlEncode(_randomBytes(32));
  }

  async function _generateCodeChallenge(verifier) {
    const encoder = new TextEncoder();
    const data = encoder.encode(verifier);
    const digest = await crypto.subtle.digest("SHA-256", data);
    return _base64urlEncode(digest);
  }

  function _generateState() {
    return _base64urlEncode(_randomBytes(16));
  }

  // ------------------------------------------------------------------ #
  // Token storage (sessionStorage – cleared when tab closes)
  // ------------------------------------------------------------------ #

  function _saveTokens(tokens) {
    sessionStorage.setItem(KEY_ACCESS,  tokens.access_token  ?? "");
    sessionStorage.setItem(KEY_ID,      tokens.id_token      ?? "");
    sessionStorage.setItem(KEY_REFRESH, tokens.refresh_token ?? "");

    // Decode email from the ID token (base64 payload, no verification needed here)
    try {
      const payload = JSON.parse(atob(tokens.id_token.split(".")[1]));
      sessionStorage.setItem(KEY_EMAIL, payload.email ?? payload["cognito:username"] ?? "");
    } catch (_) { /* ignore */ }
  }

  function _clearSession() {
    [KEY_ACCESS, KEY_ID, KEY_REFRESH, KEY_EMAIL, KEY_VERIFIER, KEY_STATE]
      .forEach(k => sessionStorage.removeItem(k));
  }

  // ------------------------------------------------------------------ #
  // Public API
  // ------------------------------------------------------------------ #

  async function login() {
    const verifier   = await _generateCodeVerifier();
    const challenge  = await _generateCodeChallenge(verifier);
    const state      = _generateState();

    sessionStorage.setItem(KEY_VERIFIER, verifier);
    sessionStorage.setItem(KEY_STATE,    state);

    const params = new URLSearchParams({
      response_type:         "code",
      client_id:             CONFIG.COGNITO_CLIENT_ID,
      redirect_uri:          CONFIG.COGNITO_REDIRECT_URI,
      scope:                 CONFIG.COGNITO_SCOPE,
      state:                 state,
      code_challenge:        challenge,
      code_challenge_method: "S256",
    });

    window.location.href =
      `https://${CONFIG.COGNITO_DOMAIN}/oauth2/authorize?${params}`;
  }

  async function handleCallback(code, returnedState) {
    const savedState = sessionStorage.getItem(KEY_STATE);
    if (!savedState || returnedState !== savedState) {
      throw new Error("OAuth state mismatch – possible CSRF attack. Please log in again.");
    }

    const verifier = sessionStorage.getItem(KEY_VERIFIER);
    if (!verifier) {
      throw new Error("PKCE code verifier missing. Please log in again.");
    }

    const response = await fetch(
      `https://${CONFIG.COGNITO_DOMAIN}/oauth2/token`,
      {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({
          grant_type:    "authorization_code",
          client_id:     CONFIG.COGNITO_CLIENT_ID,
          redirect_uri:  CONFIG.COGNITO_REDIRECT_URI,
          code:          code,
          code_verifier: verifier,
        }),
      }
    );

    if (!response.ok) {
      const detail = await response.text();
      throw new Error(`Token exchange failed (${response.status}): ${detail}`);
    }

    const tokens = await response.json();
    _saveTokens(tokens);

    // Clean up PKCE transient values
    sessionStorage.removeItem(KEY_VERIFIER);
    sessionStorage.removeItem(KEY_STATE);

    return tokens;
  }

  function logout() {
    _clearSession();
    const params = new URLSearchParams({
      client_id:  CONFIG.COGNITO_CLIENT_ID,
      logout_uri: CONFIG.COGNITO_LOGOUT_URI,
    });
    window.location.href =
      `https://${CONFIG.COGNITO_DOMAIN}/logout?${params}`;
  }

  function isAuthenticated() {
    return !!sessionStorage.getItem(KEY_ACCESS);
  }

  function getAccessToken() {
    return sessionStorage.getItem(KEY_ACCESS);
  }

  function getUserEmail() {
    return sessionStorage.getItem(KEY_EMAIL) ?? "";
  }

  /**
   * Thin fetch wrapper that automatically:
   *   • Injects Authorization: Bearer <access_token>
   *   • Redirects to login on 401
   *
   * Usage:
   *   const res = await AUTH.api("/api/files/");
   *   const data = await res.json();
   */
  async function api(path, options = {}) {
    const token = getAccessToken();
    if (!token) {
      login();
      return;
    }

    const { headers: extraHeaders = {}, ...rest } = options;

    const response = await fetch(`${CONFIG.API_BASE_URL}${path}`, {
      ...rest,
      headers: {
        Authorization: `Bearer ${token}`,
        ...extraHeaders,
      },
    });

    if (response.status === 401) {
      _clearSession();
      login();
      return;
    }

    return response;
  }

  return { login, handleCallback, logout, isAuthenticated, getAccessToken, getUserEmail, api };
})();
