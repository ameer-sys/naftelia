const state = {
  config: null,
  user: {
    sub: "demo-captain",
    email: "captain@naftelia.local",
    name: "Demo Captain",
  },
  isLoggedIn: true,
};

async function getConfig() {
  if (state.config) return state.config;
  const res = await fetch("/api/config");
  state.config = await res.json();
  return state.config;
}

async function isAuthenticated() {
  return state.isLoggedIn;
}

async function getAccessToken() {
  // Simple hardcoded token - backend will accept any token
  return "demo-token-" + Date.now();
}

async function apiFetch(url, options = {}) {
  const token = await getAccessToken();
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
    Authorization: `Bearer ${token}`,
  };
  const res = await fetch(url, { ...options, headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `API request failed: ${res.status}`);
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
  // Demo login - just mark as logged in
  state.isLoggedIn = true;
  await savePendingProfile().catch(() => null);
  return state.user;
}

async function signup() {
  // Demo signup - same as login
  return login();
}

async function logout() {
  state.isLoggedIn = false;
  return null;
}

window.NafteliaAPI = {
  getConfig,
  isAuthenticated,
  apiFetch,
  login,
  signup,
  logout,
};

document.addEventListener("DOMContentLoaded", () => {
  getConfig().catch(() => null);
});
