// Settings page. Owner: Brody Pennington. Author: Zeenat Islam, Brody Pennington
// Each setting is defined in js/settings.js; this page lists them as button groups.
// Planned (sketch): camera rate, fault thresholds, time format.

import { SETTINGS, getSetting, setSetting, resetSettings, onSettingChange } from "../settings.js";
import { escapeHtml } from "../lib/format.js";

const TZ = "America/Chicago";
const DASH = "—";

// ================================================================ styles
const CSS = `
/* Scroll the page instead of squeezing the panels. Very wide screens: the two panels side by side. */
.st { flex: 1; min-height: 0; overflow-y: auto; display: grid; grid-template-columns: minmax(0, 1fr); gap: 14px; align-content: start; }
.st > .panel { min-width: 0; }
@media (min-width: 1700px) { .st { grid-template-columns: repeat(2, minmax(0, 1fr)); align-items: start; } }
.st h3 { flex-wrap: wrap; row-gap: 4px; }
.st-hint { font: 500 13px var(--font); color: var(--mute); margin-left: auto; letter-spacing: 0; text-transform: none; }

/* Row: label (with help under it) on the left, box + unit or choices on the right. */
.st-row { display: grid; grid-template-columns: minmax(0, 1fr) minmax(300px, 560px); grid-template-areas: "lbl ctl" "sub msg";
          gap: 6px 32px; align-items: center; padding: 16px 8px; border-bottom: 1.5px solid var(--rule); }
.st-row:last-child { border-bottom: 0; }
.st-lbl { grid-area: lbl; display: flex; align-items: center; gap: 12px; font-weight: 700; font-size: 16px; letter-spacing: .02em; text-transform: uppercase; color: var(--ink); }
.st-lbl .dot { width: 12px; height: 12px; flex: none; }
.st-sub { grid-area: sub; align-self: start; margin: 0; font-size: 13px; color: var(--mute); line-height: 1.4; }
.st-faults .st-sub { padding-left: 24px; }
.st-msg { grid-area: msg; align-self: start; margin: 0; font-size: 13px; color: var(--bad); }
.st-ctl { grid-area: ctl; display: flex; align-items: center; gap: 16px; min-width: 0; }
.st-in { flex: 1; min-width: 0; width: 100%; box-sizing: border-box; padding: 11px 14px; font: 600 17px var(--mono); color: var(--ink);
         border: 1.5px solid var(--line); border-radius: 4px; background: #fff; }
.st-in:focus { outline: none; border-color: var(--acc); box-shadow: 0 0 0 3px var(--acc-bg); }
.st-in[readonly] { background: var(--rule); color: var(--mute); cursor: default; box-shadow: none; border-color: var(--line); }
.st-in.bad { border-color: var(--bad); }
.st-unit { flex: none; width: 120px; font-weight: 700; font-size: 15px; color: var(--ink); }   /* fixed width keeps the boxes lined up */
.st-pair { flex: 1; min-width: 0; display: flex; gap: 12px; }
.st-pair .st-in { text-align: center; }
.st-choices { flex: 1; display: flex; flex-wrap: wrap; align-items: center; gap: 12px 36px; }
.st-radio { display: flex; align-items: center; gap: 12px; font: 700 15px var(--font); color: var(--ink);
            background: none; border: 0; padding: 0; cursor: pointer; white-space: nowrap; }
.st-radio i { width: 36px; height: 36px; flex: none; border-radius: 50%; background: var(--rule); border: 1.5px solid var(--line);
              display: grid; place-items: center; transition: background .15s; }
.st-radio:hover i { border-color: var(--mute); }
.st-radio[aria-checked="true"] i { background: var(--acc-bg); border-color: var(--acc); }
.st-radio[aria-checked="true"] i::after { content: ""; width: 18px; height: 18px; border-radius: 50%; background: var(--acc); }
.st-radio:focus-visible { outline: 2px solid var(--acc); outline-offset: 4px; border-radius: 4px; }
.st-note { margin: 10px 8px 0; font-size: 13px; }
.st .btn:disabled { opacity: .45; cursor: default; }

/* Medium screens: control goes under the label. */
@media (max-width: 1000px) {
  .st-row { grid-template-columns: minmax(0, 1fr); grid-template-areas: "lbl" "sub" "ctl" "msg"; gap: 8px; }
  .st-ctl { max-width: 620px; margin-top: 4px; }
  .st-faults .st-sub { padding-left: 24px; }
  .st-faults .st-ctl, .st-faults .st-msg { padding-left: 24px; }
}
`;


function ensureStyle() {
  if (document.getElementById("settings-css")) return;
  const s = document.createElement("style");
  s.id = "settings-css";
  s.textContent = CSS;
  document.head.append(s);
}

// rows
const dot = (s) => (s.tone ? `<span class="dot ${s.tone}"></span>` : "");
const title = (s) => escapeHtml(s.level ? `${s.level} · ${s.label}` : s.label);
const sub = (text) => (text ? `<p class="st-sub">${escapeHtml(text)}</p>` : "");
const optLabel = (s, o) => s.optionLabels?.[o] ?? `${o}${s.unit ? " " + s.unit : ""}`;

/** Editable row for one entry of js/settings.js. */
function settingRow(key, s) {
  if (s.options) {
    return `
  <div class="st-row" data-key="${escapeHtml(key)}">
    <div class="st-lbl">${dot(s)}${title(s)}</div>
    <div class="st-ctl"><div class="st-choices" role="radiogroup" aria-label="${title(s)}">${s.options.map((o, i) =>
      `<button class="st-radio" role="radio" data-i="${i}">${escapeHtml(optLabel(s, o))}<i></i></button>`).join("")}</div></div>
    ${sub(s.help)}
  </div>`;
  }
  return `
  <div class="st-row" data-key="${escapeHtml(key)}">
    <div class="st-lbl">${dot(s)}${title(s)}</div>
    <div class="st-ctl"><input class="st-in" type="number" inputmode="decimal" min="${s.min}" max="${s.max}" step="${s.step ?? "any"}" aria-label="${title(s)}">
      <span class="st-unit">${escapeHtml(s.unit ?? "")}</span></div>
    ${sub(s.help)}
    <p class="st-msg" hidden></p>
  </div>`;
}

// read-only row for one recorded value (camera rate, IMU rate, grid resolution, bag time).
const recordedRow = (id, label, unit, note) => `
  <div class="st-row">
    <div class="st-lbl">${escapeHtml(label)}</div>
    <div class="st-ctl"><input class="st-in" id="${id}" readonly value="${DASH}" aria-label="${escapeHtml(label)}">
      <span class="st-unit">${escapeHtml(unit)}</span></div>
    ${sub(note)}
  </div>`;

const rowsFor = (section) => Object.entries(SETTINGS).filter(([, s]) => s.section === section);

const TEMPLATE = () => `
<div class="st">
  <section class="panel"><h3>SETTINGS<span class="actions"><button class="btn" id="stReset">Reset to defaults</button></span></h3>
    ${recordedRow("stCamHz", "Camera frame rate", "FPS", "Rate the bridge sends camera frames. Set by the bridge · read-only.")}
    ${recordedRow("stImuHz", "IMU refresh rate", "Hz", "Recorded in the bag · read-only. The bridge doesn't send an IMU topic yet.")}
    ${recordedRow("stGridRes", "Resolution for occupancy grid", "m per cell", "Cell size recorded in /local_costmap/voxel_layer · read-only.")}
    ${rowsFor("settings").map(([k, s]) => settingRow(k, s)).join("")}
    <div class="st-row">
      <div class="st-lbl">Date and time</div>
      <div class="st-ctl"><div class="st-pair"><input class="st-in" id="stTime" readonly value="${DASH}" aria-label="Bag time"><input class="st-in" id="stDate" readonly value="${DASH}" aria-label="Bag date"></div>
        <span class="st-unit">CDT</span></div>
      ${sub("Bag time, from the recording · read-only.")}
    </div>
    <p class="mute st-note">Saved in this browser only. Another browser or computer keeps its own settings.</p>
  </section>

  <section class="panel st-faults"><h3>FAULT THRESHOLDS<span class="st-hint">Colours used in Faults and Sensors</span></h3>
    ${rowsFor("faults").map(([k, s]) => settingRow(k, s)).join("")}
  </section>
</div>`;

// page
export default {
  title: "Settings",
  mount(root, { cavs, state }) {
    ensureStyle();
    root.innerHTML = TEMPLATE();
    const $ = (id) => root.querySelector("#" + id);
    const offs = [];

    // editable rows (js/settings.js)
    const showSettings = () => {
      let changed = false;
      root.querySelectorAll(".st-row[data-key]").forEach((row) => {
        const key = row.dataset.key, s = SETTINGS[key], v = getSetting(key);
        if (v !== s.default) changed = true;
        row.querySelectorAll(".st-radio").forEach((b) => b.setAttribute("aria-checked", String(s.options[+b.dataset.i] === v)));
        const input = row.querySelector("input");
        if (input && document.activeElement !== input) { input.value = v; input.classList.remove("bad"); row.querySelector(".st-msg").hidden = true; }
      });
      $("stReset").disabled = !changed;
    };

    root.querySelectorAll(".st-row[data-key]").forEach((row) => {
      const key = row.dataset.key, s = SETTINGS[key];
      row.querySelectorAll(".st-radio").forEach((b) => (b.onclick = () => setSetting(key, s.options[+b.dataset.i])));
      const input = row.querySelector("input"), msg = row.querySelector(".st-msg");
      if (!input) return;
      // Saved when you leave the box or press Enter; Esc puts the saved value back.
      const commit = () => {
        const v = input.value.trim() === "" ? NaN : Number(input.value);
        if (setSetting(key, v)) { input.classList.remove("bad"); msg.hidden = true; input.value = getSetting(key); showSettings(); }
        else { input.classList.add("bad"); msg.hidden = false; msg.textContent = `Enter a number from ${s.min} to ${s.max}${s.unit ? " " + s.unit : ""}. Not saved.`; }
      };
      input.addEventListener("change", commit);
      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") input.blur();
        if (e.key === "Escape") { input.value = getSetting(key); input.classList.remove("bad"); msg.hidden = true; input.blur(); }
      });
    });
    $("stReset").onclick = resetSettings;

    // recorded rows (read-only)
    const showBridge = () => {
      const hz = cavs.settings?.camera_hz;
      $("stCamHz").value = hz != null ? String(hz) : DASH;
    };
    offs.push(cavs.on("/local_costmap/voxel_layer", (d) => {
      const r = d.resolution ?? d.info?.resolution;
      $("stGridRes").value = r != null ? String(r) : DASH;
    }));

    // Bag time in the chosen 12 / 24 hour format (this page already follows the time-format setting).
    const showTime = () => {
      const t = state?.bagTime;
      if (t == null) { $("stTime").value = DASH; $("stDate").value = DASH; return; }
      const d = new Date(t * 1000);
      $("stTime").value = new Intl.DateTimeFormat("en-US", { timeZone: TZ, hour: "numeric", minute: "2-digit", second: "2-digit", hour12: getSetting("timeFormat") === 12 }).format(d);
      $("stDate").value = new Intl.DateTimeFormat("en-US", { timeZone: TZ, month: "numeric", day: "numeric", year: "numeric" }).format(d);
    };
    offs.push(cavs.on("/mtx/odom", showTime));

    showSettings(); showBridge(); showTime();
    offs.push(
      onSettingChange((key) => { showSettings(); if (key === "timeFormat") showTime(); }),
      cavs.onSettings(showBridge),
      cavs.onRestart(() => { $("stGridRes").value = DASH; showTime(); }),
    );
    return () => offs.forEach((off) => off());
  },
};
