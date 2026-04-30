const API_BASE = "http://127.0.0.1:5000";

const state = {
  config: null,
  auth0: null,
};

async function getConfig() {
  if (state.config) return state.config;

  const res = await fetch(`${API_BASE}/api/config`);
  if (!res.ok) throw new Error(`Config request failed: ${res.status}`);

  state.config = await res.json();
  console.log("Loaded config:", state.config);
  return state.config;
}

async function initAuth0() {
  const config = await getConfig();

  const canInit =
    window.createAuth0Client &&
    config.auth0Domain &&
    config.auth0ClientId &&
    config.auth0Audience;

  if (!canInit || config.auth0Domain.includes("your-")) return null;

  if (!state.auth0) {
    state.auth0 = await window.createAuth0Client({
      domain: config.auth0Domain,
      clientId: config.auth0ClientId,
      authorizationParams: {
        audience: config.auth0Audience,
        redirect_uri: window.location.origin,
      },
      cacheLocation: "localstorage",
      useRefreshTokens: true,
    });
  }

  if (
    window.location.search.includes("code=") &&
    window.location.search.includes("state=")
  ) {
    await state.auth0.handleRedirectCallback();
    window.history.replaceState({}, document.title, "/");
    await savePendingProfile();
    window.showPage?.("app");
  }

  return state.auth0;
}

async function isAuthenticated() {
  const auth0 = await initAuth0();
  return auth0 ? auth0.isAuthenticated() : false;
}

async function getAccessToken() {
  const auth0 = await initAuth0();

  if (!auth0) throw new Error("Auth0 is not configured");

  const authed = await auth0.isAuthenticated();

  if (!authed) {
    await auth0.loginWithRedirect();
    throw new Error("Redirecting to Auth0");
  }

  return auth0.getTokenSilently();
}

async function apiFetch(url, options = {}) {
  const token = await getAccessToken();

  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
    Authorization: `Bearer ${token}`,
  };

  const fullUrl = url.startsWith("http") ? url : `${API_BASE}${url}`;

  const res = await fetch(fullUrl, {
    ...options,
    headers,
  });

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    throw new Error(data.error || `API request failed: ${res.status}`);
  }

  return data;
}

async function savePendingProfile() {
  const raw = sessionStorage.getItem("naftelia-pending-profile");
  if (!raw) return null;

  const profile = JSON.parse(raw);

  const saved = await apiFetch("/api/me", {
    method: "PUT",
    body: JSON.stringify(profile),
  });

  if (profile.vessel_type) {
    await apiFetch("/api/vessels", {
      method: "POST",
      body: JSON.stringify({
        name: `${profile.full_name || "Captain"} vessel`,
        vessel_type: profile.vessel_type,
        safety_margin: "conservative",
      }),
    }).catch(() => null);
  }

  sessionStorage.removeItem("naftelia-pending-profile");
  return saved;
}

async function login() {
  const auth0 = await initAuth0();

  if (!auth0) {
    alert(
      "Auth0 is not configured yet. Add AUTH0_DOMAIN, AUTH0_CLIENT_ID, and AUTH0_AUDIENCE in backend/.env."
    );
    return;
  }

  return auth0.loginWithRedirect();
}

async function signup() {
  const auth0 = await initAuth0();

  if (!auth0) {
    alert("Auth0 is not configured yet. Add AUTH0 settings in backend/.env before real signup.");
    return;
  }

  return auth0.loginWithRedirect({
    authorizationParams: {
      screen_hint: "signup",
    },
  });
}

async function logout() {
  const auth0 = await initAuth0();
  if (!auth0) return;

  return auth0.logout({
    logoutParams: {
      returnTo: window.location.origin,
    },
  });
}

window.NafteliaAPI = {
  getConfig,
  initAuth0,
  isAuthenticated,
  apiFetch,
  login,
  signup,
  logout,
};

document.addEventListener("DOMContentLoaded", () => {
  initAuth0().catch((err) => {
    console.error("Auth0 init failed:", err);
  });
});