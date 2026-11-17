// App shell: header, bottom nav, page router, alert summary. Author: Zeenat Islam
//
// Each page is a module in js/pages/ exporting  { title, mount(root, ctx) }  where mount returns a cleanup
// function. ctx = { cavs, state }. See dashboard/README.md.

import { cavs, state } from "./state.js";
import { clock, dateLabel, componentName, problemText, safetyReasons } from "./lib/format.js";
import home from "./pages/home.js";
import map from "./pages/map.js";
import sensors from "./pages/sensors.js";
import logs from "./pages/logs.js";
import faults from "./pages/faults.js";
import settings from "./pages/settings.js";

const PAGES = { home, map, sensors, logs, faults, settings };
const $ = (id) => document.getElementById(id);

// ---------------------------------------------------------------- router
let cleanup = null;
function route() {
  const name = (location.hash.match(/^#\/(\w+)/) || [])[1] || "home";
  const page = PAGES[name] || home;
  if (cleanup) { try { cleanup(); } catch (e) { console.error(e); } }
  const root = $("page");
  root.replaceChildren();
  cleanup = page.mount(root, { cavs, state }) || null;
  document.querySelectorAll(".bottom a").forEach((a) => a.classList.toggle("on", a.dataset.page === name));
  document.title = `${page.title} · Autonomous Vehicle Testing`;
}
window.addEventListener("hashchange", route);
route();

// ---------------------------------------------------------------- header
function setStatus(el, text, tone) {
  el.textContent = text;
  el.className = tone;
}

cavs.onStatus((s) => {
  const el = $("conn");
  el.textContent = s === "open" ? "● LIVE" : s === "connecting" ? "● CONNECTING" : "○ NOT CONNECTED";
  el.className = "conn" + (s === "open" ? " live" : "");
});
cavs.onSettings(() => {
  $("bagName").textContent = state.bag ? `bag playback · ${state.bag.name}` : "bag playback";
});

cavs.on("/mtx/velocity_filter/status", (d) => setStatus($("hSafety"), d.ok ? "OK" : "INHIBIT", d.ok ? "ok" : "warn"));

function headerTick() {
  const nav2 = Object.values(state.diagnostics).find((s) => s.name.includes("Nav2"));
  if (nav2) setStatus($("hNav2"), nav2.level === 0 ? "Active" : ["OK", "WARN", "ERROR", "STALE"][nav2.level] || "?", nav2.level === 0 ? "ok" : nav2.level === 1 ? "warn" : "bad");
  const bridge = state.diagnostics["mtx_nav2/drive_bridge"];
  if (bridge) setStatus($("hBridge"), bridge.message.split(" ")[0] || "—", bridge.level === 0 ? "ok" : bridge.level === 1 ? "warn" : "bad");
  const estop = state.estop ?? cavs.latest("/mtx/arbiter_status")?.estop;
  if (estop != null) setStatus($("hEstop"), estop ? "Latched" : "Clear", estop ? "bad" : "ok");
  $("clock").textContent = clock(state.bagTime);
  $("date").textContent = dateLabel(state.bagTime);
  updateAlert();
}
setInterval(headerTick, 250);

// ---------------------------------------------------------------- alert summary (recorded flags only)
function updateAlert() {
  const el = $("alert");
  const show = (text, tone, all = text) => { el.textContent = text; el.className = "alert " + tone; el.title = all; };
  if (cavs.status !== "open") return show("○ Not connected to the bag bridge", "");
  // active alerts, worst first; worded for the operator (recorded flags only, nothing calculated)
  const alerts = [];
  const estop = state.estop ?? cavs.latest("/mtx/arbiter_status")?.estop;
  if (estop) alerts.push({ text: "E-stop latched", tone: "bad" });
  const sf = cavs.latest("/mtx/velocity_filter/status");
  if (sf && !sf.ok) alerts.push({ text: `Safety filter holding: ${safetyReasons(sf.inhibit_reasons) || "inhibit"}`, tone: "warn" });
  Object.values(state.diagnostics).filter((s) => s.level > 0)
    .sort((a, b) => b.level - a.level || (a.name === "mtx_nav2/web_ui") - (b.name === "mtx_nav2/web_ui"))
    .forEach((s) => alerts.push({ text: `${componentName(s.name)}: ${problemText(s)}`, tone: s.level >= 2 ? "bad" : "warn" }));
  if (!alerts.length) return show("◇ No Active Alerts", "");
  const more = alerts.length > 1 ? `  (+${alerts.length - 1} more)` : "";
  show(`⚠ ${alerts[0].text}${more}`, alerts[0].tone, alerts.map((a) => a.text).join("\n"));   // hover: every active alert
}
