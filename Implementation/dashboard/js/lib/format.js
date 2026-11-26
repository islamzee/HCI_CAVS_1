// Display formatting only (units, rounding, clock time). No values are calculated here.
// Author: Zeenat Islam

import { getSetting } from "../settings.js";

const TZ = "America/Chicago";   // the run was recorded at CAVS, Starkville MS

const timeFmt = {
  24: new Intl.DateTimeFormat("en-US", { timeZone: TZ, hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23" }),
  12: new Intl.DateTimeFormat("en-US", { timeZone: TZ, hour: "numeric", minute: "2-digit", second: "2-digit", hour12: true }),
};
const dateFmt = new Intl.DateTimeFormat("en-US", { timeZone: TZ, month: "short", day: "numeric", year: "numeric", timeZoneName: "short" });

/** Recorded stamp (seconds since 1970) as clock time in the "System time format" setting, e.g. "16:46:02" or
 *  "4:46:02 PM". `frac` (e.g. ".3") goes right after the seconds. */
export function clock(stamp, frac = "") {
  if (stamp == null || stamp < 1e9) return "--:--:--";
  const t = timeFmt[getSetting("timeFormat")] || timeFmt[24];
  return t.format(new Date(stamp * 1000)).replace(/(\d\d)(\D*)$/, `$1${frac}$2`);
}

/** Recorded stamp as date, e.g. "Sep 11, 2026 CDT". */
export function dateLabel(stamp) {
  if (stamp == null || stamp < 1e9) return "";
  const p = Object.fromEntries(dateFmt.formatToParts(new Date(stamp * 1000)).map((x) => [x.type, x.value]));
  return `${p.month} ${p.day}, ${p.year} ${p.timeZoneName}`;
}

/** Number with fixed decimals and a unit; "—" when missing. */
export function num(v, digits, unit = "", signed = false) {
  if (v == null || Number.isNaN(v)) return "—";
  const s = v.toFixed(digits);
  return (signed && v >= 0 ? "+" : "") + s + (unit ? " " + unit : "");
}

/** Seconds as milliseconds (unit change only), e.g. 0.0004 -> "0.4 ms". */
export function ms(seconds) {
  return seconds == null ? "—" : (seconds * 1000).toFixed(1) + " ms";
}

export const ROSOUT_LEVEL = { 10: "DEBUG", 20: "INFO", 30: "WARN", 40: "ERROR", 50: "FATAL" };
export const DIAG_LEVEL = { 0: "OK", 1: "WARN", 2: "ERROR", 3: "STALE" };
export const ARBITER_MODE = { 0: "MANUAL", 1: "AUTONOMY", 2: "ESTOP" };
export const COLLISION_ACTION = { 0: "none", 1: "stop", 2: "slowdown", 3: "approach", 4: "limit" };

/** CSS colour class for a level: ok | warn | bad | mute. */
export function diagTone(level) {
  return level == null ? "mute" : level === 0 ? "ok" : level === 1 ? "warn" : "bad";
}
export function rosoutTone(level) {
  return level >= 40 ? "bad" : level >= 30 ? "warn" : "mute";
}

export function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

// ---------------------------------------------------------------- alert wording
// Plain-language wording for the alert summary. Only rewords recorded text; nothing is calculated.

/** Component name for a /diagnostics status name, e.g. "cam_2: image" -> "Camera 2". */
export function componentName(name) {
  const cam = /^cam_(\d+)\b/.exec(name);
  if (cam) return `Camera ${cam[1]}`;
  if (name === "mtx_nav2/drive_bridge") return "Drive bridge";
  if (name === "mtx_nav2/web_ui") return "System check";
  if (/Nav2 Health/i.test(name)) return "Nav2";
  return name;
}

const PROBLEM_WORDS = { incompletes: "incomplete frames", drops: "dropped frames" };

/** Short problem text for a status, e.g. "incompletes is high!; drops too high!" -> "incomplete frames, dropped frames". */
export function problemText(status) {
  if (status.name === "mtx_nav2/web_ui") {               // list the parts it reports as not ok
    const bad = Object.entries(status.values || {})
      .filter(([k, v]) => !/^(goal|estop)$/i.test(k) && !/^ok\b/i.test(v))
      .map(([k, v]) => {
        const [state, ...rest] = String(v).split(":");
        const detail = rest.join(":").replace(/\(.*?\)/g, "").trim();
        return `${k.toLowerCase()} – ${detail || state.trim()}`;
      });
    if (bad.length) return bad.join(", ");
  }
  const parts = status.message.split(";").map((p) => p.trim().replace(/!+$/, "")).filter(Boolean)
    .map((p) => { const w = p.split(/\s+/)[0].toLowerCase(); return PROBLEM_WORDS[w] || p; });
  const text = [...new Set(parts)].join(", ");
  const lower = text && /^[A-Z][a-z]/.test(text) ? text[0].toLowerCase() + text.slice(1) : text;  // keep "STALE", "LIVE"
  return lower || DIAG_LEVEL[status.level]?.toLowerCase() || "problem";
}

const SAFETY_WORDS = { no_cmd: "no drive command" };
/** Safety filter inhibit reasons in words, e.g. ["no_cmd"] -> "no drive command". */
export function safetyReasons(reasons) {
  const list = Array.isArray(reasons) ? reasons : reasons ? [reasons] : [];
  return list.map((r) => SAFETY_WORDS[r] || String(r).replace(/_/g, " ")).join(", ");
}
