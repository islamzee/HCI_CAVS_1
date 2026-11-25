// Dashboard settings shared by all pages. Saved in this browser only (localStorage).
// Author: Zeenat Islam, Brody Pennington
//
//   import { getSetting, onSettingChange } from "../settings.js";
//   const m = getSetting("gridMarginM");
//   const off = onSettingChange((key, value) => { ... });   // call off() in your page cleanup

// Each setting has label, help, default, unit (optional), section ("settings" | "faults"), and EITHER
//   options: [...] + optionLabels (optional)   → round choice buttons on the Settings page
//   min, max, step                             → a number box on the Settings page
// Fault settings also have level ("CRITICAL" | "WARNING") and tone ("bad" | "warn") for the coloured dot.

const KEY = "cavs.settings.v1";

/** Every setting, its default and its allowed values. Add new settings here. */
export const SETTINGS = {
  gridMarginM: {
    section: "settings",
    label: "Occupancy grid view",
    help: "Metres shown around the vehicle on the Home occupancy grid. Default 1 m (client feedback, 10 Nov 2026).",
    default: 1,
    options: [1, 2, 5, 10, 15],
    unit: "m",
  },
  timeFormat: {
    section: "settings",
    label: "System time format",
    help: "12 or 24-hour clock.",
    options: [12, 24],
    optionLabels: { 12: "12 HR", 24: "24 HR" },
    default: 24,
  },

  // Fault thresholds (Faults and Sensors pages)
  faultNoMessageMs: {
    section: "faults",
    level: "CRITICAL",
    tone: "bad",
    label: "No messages from vehicle",
    unit: "ms",
    help: "Time since last message from vehicle. If this is exceeded, the vehicle is considered disconnected.",
    min: 100,
    max: 6000,
    step: 100,
    default: 500,
  },
  faultDelayMs: {
    section: "faults",
    level: "WARNING",
    tone: "warn",
    label: "Timestamp delay over",
    unit: "ms",
    help: "Time difference between the vehicle's timestamp and the dashboard's.",
    min: 100,
    max: 10000,
    step: 100,
    default: 200,
  },
  faultRatePct: {
    section: "faults",
    level: "WARNING",
    tone: "warn",
    label: "Message rate below",
    unit: "% of expected",
    help: "Percentage of expected messages received from the vehicle.",
    min: 1,
    max: 100,
    step: 1,
    default: 50,
  },
  faultSafetyFalse: {
    section: "faults",
    level: "WARNING",
    tone: "warn",
    label: "Safety false positive",
    help: "If the vehicle reports a safety fault when it is actually safe, this is a false positive.",
    options: [true, false],
    optionLabels: { true: "ON", false: "OFF" },
    default: true,
  },
};

/** True if value is allowed for this setting (one of its options, or a number from min to max). */
export function isValid(key, value) {
  const s = SETTINGS[key];
  if (!s) return false;
  if (s.options) return s.options.includes(value);
  return typeof value === "number" && Number.isFinite(value) && value >= s.min && value <= s.max;
}

// Only values that differ from the default are stored; anything unknown or not allowed is ignored.
function load() {
  try {
    const raw = JSON.parse(localStorage.getItem(KEY) || "{}");
    return Object.fromEntries(Object.entries(raw).filter(([k, v]) => isValid(k, v)));
  } catch { return {}; }   // storage blocked or corrupt: use defaults
}
function save() {
  try { localStorage.setItem(KEY, JSON.stringify(saved)); } catch { /* storage blocked: keep for this visit */ }
}

let saved = load();
const handlers = new Set();
const notify = (key) => handlers.forEach((fn) => fn(key, getSetting(key)));

export function getSetting(key) {
  return key in saved ? saved[key] : SETTINGS[key]?.default;
}

/** Save a value. Returns false (and changes nothing) if the value isn't allowed. */
export function setSetting(key, value) {
  if (!isValid(key, value)) return false;
  if (getSetting(key) === value) return true;
  if (value === SETTINGS[key].default) delete saved[key]; else saved[key] = value;
  save();
  notify(key);
  return true;
}

export function resetSettings() {
  const changed = Object.keys(saved);
  saved = {};
  save();
  changed.forEach(notify);
}

/** fn(key, value) on every change. Returns an "off" function. */
export function onSettingChange(fn) {
  handlers.add(fn);
  return () => handlers.delete(fn);
}

// keep several open tabs in step
window.addEventListener("storage", (e) => {
  if (e.key !== KEY) return;
  const before = Object.fromEntries(Object.keys(SETTINGS).map((k) => [k, getSetting(k)]));
  saved = load();
  for (const k of Object.keys(SETTINGS)) if (before[k] !== getSetting(k)) notify(k);
});

