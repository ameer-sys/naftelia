const state = {
  currentPage: "landing",
  appTab: "dashboard",
  miniMap: null,
  routeMap: null,
  activeVoyage: null,
  voyages: [],
};

const appTitles = {
  dashboard: "Dashboard",
  route: "Route",
  planner: "Plan Voyage",
  offline: "Offline Pack",
  settings: "Settings",
};

function qs(selector, root = document) {
  return root.querySelector(selector);
}

function qsa(selector, root = document) {
  return Array.from(root.querySelectorAll(selector));
}

function toast(message) {
  const el = qs("#toast");
  el.textContent = message;
  el.classList.add("show");
  window.clearTimeout(toast.timer);
  toast.timer = window.setTimeout(() => el.classList.remove("show"), 3200);
}

function refreshIcons() {
  if (window.lucide) window.lucide.createIcons();
}

function showPage(page) {
  state.currentPage = page;
  qsa(".page").forEach((el) => el.classList.toggle("active", el.id === `page-${page}`));
  qs(".site-header")?.classList.toggle("hidden", page !== "landing");
  qs("#mobileNav")?.classList.remove("open");
  window.scrollTo({ top: 0, behavior: "smooth" });

  if (page === "app") {
    showAppTab(state.appTab || "dashboard");
    window.setTimeout(initMaps, 150);
  }
  refreshIcons();
}

function scrollToSection(id) {
  showPage("landing");
  window.setTimeout(() => qs(`#${id}`)?.scrollIntoView({ behavior: "smooth", block: "start" }), 80);
}

function showSignupStep(step) {
  qsa(".signup-step").forEach((el) => el.classList.toggle("active", el.dataset.step === String(step)));
  qsa(".step-pill").forEach((el) => el.classList.toggle("active", el.dataset.signupStep === String(step)));
}

function showAppTab(tab) {
  state.appTab = tab;
  qsa(".app-tab").forEach((el) => el.classList.toggle("active", el.id === `tab-${tab}`));
  qsa("[data-app-tab]").forEach((el) => el.classList.toggle("active", el.dataset.appTab === tab));
  const title = qs("#appTitle");
  if (title) title.textContent = appTitles[tab] || "Dashboard";
  if (tab === "route" || tab === "dashboard") window.setTimeout(initMaps, 150);
  refreshIcons();
}

function routePoints() {
  const waypoints = state.activeVoyage?.waypoints || [];
  if (waypoints.length) return waypoints.map((point) => [point.latitude, point.longitude]);
  return [
    [48.1181, -123.4307],
    [48.31, -123.24],
    [48.5343, -123.0171],
  ];
}

function initOneMap(containerId, existingMap) {
  const container = qs(`#${containerId}`);
  if (!container || !window.L) return existingMap;
  if (existingMap) existingMap.remove();

  const points = routePoints();
  const map = window.L.map(containerId, { zoomControl: false, attributionControl: false }).setView(points[0], 9);
  window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 18 }).addTo(map);
  window.L.polyline(points, { color: "#0ea5a8", weight: 5, opacity: 0.92 }).addTo(map);
  points.forEach((point, index) => {
    const label = state.activeVoyage?.waypoints?.[index]?.label || (index === 0 ? "Origin" : index === points.length - 1 ? "Destination" : "Waypoint");
    window.L.marker(point).addTo(map).bindPopup(label);
  });
  window.L.circle(points[Math.floor(points.length / 2)], {
    radius: 1800,
    color: "#c9a35d",
    fillColor: "#c9a35d",
    fillOpacity: 0.12,
    weight: 2,
  }).addTo(map);
  map.fitBounds(points, { padding: [28, 28] });
  return map;
}

function initMaps() {
  state.miniMap = initOneMap("miniMap", state.miniMap);
  state.routeMap = initOneMap("routeMap", state.routeMap);
}

function setVoyage(voyage) {
  state.activeVoyage = voyage;
  if (!state.voyages.some((item) => item.id === voyage.id)) state.voyages.unshift(voyage);
  const plan = voyage.gemini_plan || {};
  const noaa = voyage.noaa_snapshot || {};
  const coops = noaa.coops?.observations || {};
  const wind = coops.wind?.s ? `${coops.wind.s} m/s` : "NOAA ready";
  const temp = coops.water_temperature?.v ? `${coops.water_temperature.v} C` : "NOAA ready";

  qs("#routeSummary").textContent = plan.summary || "Voyage plan created.";
  qs("#routeConfidence").textContent = `${plan.confidence || 70}%`;
  qs("#seaTemp").textContent = temp;
  qs("#windSpeed").textContent = wind;
  qs("#waveHeight").textContent = plan.safety_level || "normal";

  const briefing = plan.captain_briefing || [];
  const waypointInstructions = (voyage.waypoints || []).map((point) => point.instruction).filter(Boolean);
  const steps = waypointInstructions.length ? waypointInstructions : briefing;
  if (steps.length) qs("#routeSteps").innerHTML = steps.map((step) => `<li>${escapeHtml(step)}</li>`).join("");

  renderVoyages();
  initMaps();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function voyagePayload(form) {
  const data = new FormData(form);
  return {
    origin_label: data.get("origin_label"),
    origin: { lat: Number(data.get("origin_lat")), lon: Number(data.get("origin_lon")) },
    destination_label: data.get("destination_label"),
    destination: { lat: Number(data.get("destination_lat")), lon: Number(data.get("destination_lon")) },
    station_id: data.get("station_id"),
    departure_time: data.get("departure_time"),
    vessel: {
      vessel_type: qs("#settingVessel")?.value || "Sailboat",
      safety_margin: "conservative",
    },
  };
}

async function handleVoyage(event) {
  event.preventDefault();
  toast("Pulling NOAA data and asking Gemini for a route...");
  try {
    const voyage = await window.NafteliaAPI.apiFetch("/api/voyages/plan", {
      method: "POST",
      body: JSON.stringify(voyagePayload(event.currentTarget)),
    });
    setVoyage(voyage);
    showAppTab("route");
    toast("Voyage route created. Save the offline pack before departure.");
  } catch (error) {
    toast("Route planning failed. Check backend, Auth0, and API key configuration.");
  }
}

function renderVoyages() {
  const list = qs("#voyageHistory");
  if (!list) return;
  if (!state.voyages.length) {
    list.innerHTML = '<article class="voyage-item"><h3>No saved voyages yet</h3><p>Create your first route above.</p></article>';
    return;
  }
  list.innerHTML = state.voyages
    .map(
      (voyage) => `
        <article class="voyage-item">
          <h3>${escapeHtml(voyage.origin_label || "Origin")} to ${escapeHtml(voyage.destination_label || "Destination")}</h3>
          <p>${escapeHtml(voyage.gemini_plan?.safety_level || voyage.status || "planned")} safety level</p>
          <p>${escapeHtml(voyage.gemini_plan?.summary || "Route saved.")}</p>
        </article>
      `,
    )
    .join("");
}

async function startOfflineDownload() {
  const bar = qs("#offlineProgress");
  let progress = 0;
  if (!state.activeVoyage?.id) {
    toast("Create a voyage first, then download the 24-hour offline pack.");
    showAppTab("planner");
    return;
  }

  toast("Generating offline voyage pack...");
  if (bar) bar.style.width = "0";
  const timer = window.setInterval(() => {
    progress = Math.min(progress + 15, 90);
    if (bar) bar.style.width = `${progress}%`;
  }, 180);

  try {
    const pack = await window.NafteliaAPI.apiFetch(`/api/voyages/${state.activeVoyage.id}/offline-pack`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    localStorage.setItem("naftelia-offline-pack", JSON.stringify(pack));
    window.clearInterval(timer);
    if (bar) bar.style.width = "100%";
    toast("Offline pack saved locally for 24 hours.");
  } catch {
    window.clearInterval(timer);
    toast("Offline pack failed. Create a route and verify backend auth.");
  }
}

async function handleLogin(event) {
  event.preventDefault();
  if (window.NafteliaAPI?.login) await window.NafteliaAPI.login();
}

async function handleSignup(event) {
  event.preventDefault();
  const formData = new FormData(event.currentTarget);
  const profile = {
    full_name: formData.get("name"),
    email: formData.get("email"),
    home_port: formData.get("home_port"),
    vessel_type: formData.get("vessel_type"),
    plan: formData.get("plan"),
  };
  sessionStorage.setItem("naftelia-pending-profile", JSON.stringify(profile));
  if (window.NafteliaAPI?.signup) await window.NafteliaAPI.signup();
}

function bindInteractions() {
  document.addEventListener("click", async (event) => {
    const pageLink = event.target.closest("[data-page-link]");
    if (pageLink) {
      event.preventDefault();
      showPage(pageLink.dataset.pageLink);
      return;
    }

    const scrollLink = event.target.closest("[data-scroll-link]");
    if (scrollLink) {
      event.preventDefault();
      scrollToSection(scrollLink.dataset.scrollLink);
      return;
    }

    const tabLink = event.target.closest("[data-app-tab]");
    if (tabLink) {
      event.preventDefault();
      showPage("app");
      showAppTab(tabLink.dataset.appTab);
      return;
    }

    const nextStep = event.target.closest("[data-next-step]");
    if (nextStep) {
      event.preventDefault();
      showSignupStep(nextStep.dataset.nextStep);
      return;
    }

    const signupStep = event.target.closest("[data-signup-step]");
    if (signupStep) {
      event.preventDefault();
      showSignupStep(signupStep.dataset.signupStep);
      return;
    }

    const choice = event.target.closest(".choice");
    if (choice) {
      event.preventDefault();
      qsa(".choice").forEach((el) => el.classList.remove("active"));
      choice.classList.add("active");
      qs("input[name='vessel_type']").value = choice.dataset.value;
      return;
    }

    const plan = event.target.closest(".plan-choice");
    if (plan) {
      event.preventDefault();
      qsa(".plan-choice").forEach((el) => el.classList.remove("active"));
      plan.classList.add("active");
      qs("input[name='plan']").value = plan.dataset.plan;
      return;
    }

    const action = event.target.closest("[data-action]");
    if (action) {
      event.preventDefault();
      await handleAction(action.dataset.action, action);
    }
  });

  qs("#menuToggle")?.addEventListener("click", () => qs("#mobileNav")?.classList.toggle("open"));
  qs("#loginForm")?.addEventListener("submit", handleLogin);
  qs("#signupForm")?.addEventListener("submit", handleSignup);
  qs("#voyageForm")?.addEventListener("submit", handleVoyage);
}

async function handleAction(action) {
  if (action === "download-offline") {
    showPage("app");
    showAppTab("offline");
    await startOfflineDownload();
    return;
  }
  if (action === "refresh-route") {
    if (!state.activeVoyage) {
      toast("Create a voyage in Plan Voyage first.");
      showAppTab("planner");
      return;
    }
    toast("Refresh by generating a new NOAA + Gemini route from Plan Voyage.");
    return;
  }
  if (action === "payment-placeholder") {
    toast("Pro is coming soon. Payment collection is intentionally disabled.");
    return;
  }
  if (action === "social-demo" || action === "auth0-login") {
    if (window.NafteliaAPI?.login) await window.NafteliaAPI.login();
    return;
  }
  if (action === "save-settings") toast("Settings saved locally. Backend vessel sync is ready through /api/vessels.");
}

function initRevealAnimations() {
  const observer = new IntersectionObserver(
    (entries) => entries.forEach((entry) => entry.isIntersecting && entry.target.classList.add("visible")),
    { threshold: 0.12 },
  );
  qsa(".reveal").forEach((el) => observer.observe(el));
}

function initFromHash() {
  const hash = window.location.hash.replace("#", "");
  if (hash && qs(`#page-${hash}`)) showPage(hash);
}

window.showPage = showPage;
window.showAppTab = showAppTab;

document.addEventListener("DOMContentLoaded", () => {
  bindInteractions();
  renderVoyages();
  initRevealAnimations();
  initFromHash();
  refreshIcons();
});
