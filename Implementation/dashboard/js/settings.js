// Dashboard settings shared by all pages. Saved in this browser only (localStorage).
// Author: Zeenat Islam
//
//   import { getSetting, onSettingChange } from "../settings.js";
//   const m = getSetting("gridMarginM");
//   const off = onSettingChange((key, value) => { ... });   // call off() in your page cleanup

const KEY = "cavs.settings.v1";

/** Every setting, its default and its allowed values. Add new settings here. */
export const SETTINGS = {
  gridMarginM: {
    label: "Occupancy grid view",
    help: "Metres shown around the vehicle on the Home occupancy grid. Default 1 m (client feedback, 10 Nov 2026).",
    default: 1,
    options: [1, 2, 5, 10, 15],
    unit: "m",
  },
};

let values = load();
const handlers = new Set();

function load() {
  const out = Object.fromEntries(Object.entries(SETTINGS).map(([k, s]) => [k, s.default]));
  try {
    const saved = JSON.parse(localStorage.getItem(KEY) || "{}");
    for (const [k, v] of Object.entries(saved)) if (k in SETTINGS && SETTINGS[k].options.includes(v)) out[k] = v;
  } catch { /* storage blocked or corrupt: use defaults */ }
  return out;
}

function save() {
  try { localStorage.setItem(KEY, JSON.stringify(values)); } catch { /* storage blocked: keep for this visit */ }
}

export function getSetting(key) {
  return values[key];
}

export function setSetting(key, value) {
  if (!(key in SETTINGS) || !SETTINGS[key].options.includes(value) || values[key] === value) return;
  values[key] = value;
  save();
  for (const fn of handlers) fn(key, value);
}

export function resetSettings() {
  for (const [k, s] of Object.entries(SETTINGS)) setSetting(k, s.default);
}

/** fn(key, value) on every change. Returns an "off" function. */
export function onSettingChange(fn) {
  handlers.add(fn);
  return () => handlers.delete(fn);
}

// keep several open tabs in step
window.addEventListener("storage", (e) => {
  if (e.key !== KEY) return;
  const before = values;
  values = load();
  for (const k of Object.keys(SETTINGS)) if (before[k] !== values[k]) for (const fn of handlers) fn(k, values[k]);
});
