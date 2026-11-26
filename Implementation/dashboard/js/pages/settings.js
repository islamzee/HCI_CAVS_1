// Settings page. Owner: Brody Pennington. Author: Zeenat Islam, Brody Pennington
// Each setting is defined in js/settings.js; this page lists them as button groups.
// Planned (sketch): camera rate, fault thresholds, time format.

import { SETTINGS, getSetting, setSetting, resetSettings, onSettingChange } from "../settings.js";
import { escapeHtml, clock, dateLabel } from "../lib/format.js";

const DASH = "—";

// ================================================================ styles
const CSS = `
/* Scroll the page instead of squeezing the panels. Very wide screens: the two panels side by side. */
.st { flex: 1; min-height: 0; overflow-y: auto; display: grid; grid-template-columns: minmax(0, 1fr); gap: 14px; align-content: start; }
.st > .panel { min-width: 0; min-height: auto; overflow: visible; }   /* .panel sets min-height: 0 and overflow: hidden, which let the grid squeeze the panels to the page height and cut rows off */
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
.st-below { grid-area: msg; align-self: start; margin: 0; font-size: 13px; color: var(--mute); }
.st-below b { font-family: var(--mono); color: var(--ink); }
.st-msg { grid-area: msg; align-self: start; margin: 0; font-size: 13px; color: var(--bad); }
.st-ctl { grid-area: ctl; display: flex; align-items: center; gap: 16px; min-width: 0; }
.st-in { flex: none; width: 130px; box-sizing: border-box; padding: 8px 12px;   /* sized for up to 5 digits */ text-align: center; font: 600 17px var(--mono); color: var(--ink);
         border: 1.5px solid var(--line); border-radius: 4px; background: #fff; }
.st-in:focus { outline: none; border-color: var(--acc); box-shadow: 0 0 0 3px var(--acc-bg); }
/* Read-only values (recorded, not settings) are plain text with no box, so only the things you can change look like controls. */
.st-ro { padding: 8px 0; font-weight: 700; font-size: 15px; color: var(--ink); }
.st-ro b { font: 700 17px var(--mono); margin-right: 4px; }
.st-in.bad { border-color: var(--bad); }
.st-unit { flex: none; min-width: 0; font-weight: 700; font-size: 15px; color: var(--ink); }   
.st-pair { flex: 1; min-width: 0; display: flex; gap: 12px; }
.st-pair .st-in { text-align: center; }
.st-choices.fit { flex: none; }
.st-now { display: flex; align-items: baseline; gap: 10px; margin-left: 8px; padding: 8px 0;
          color: var(--mute); font-size: 13px; white-space: nowrap; }
.st-now b { font: 700 16px var(--mono); color: var(--ink); }
.st-choices { flex: 1; display: flex; flex-wrap: wrap; align-items: center; gap: 12px 36px; }
.st-radio { display: flex; align-items: center; gap: 12px; font: 700 15px var(--font); color: var(--ink);
            background: none; border: 0; padding: 0; cursor: pointer; white-space: nowrap; }
.st-radio i { width: 36px; height: 36px; flex: none; border-radius: 50%; background: #fff; border: 1.5px solid var(--line);
              display: grid; place-items: center; transition: background .15s; }
.st-radio:hover i { border-color: var(--mute); }
.st-radio[aria-checked="true"] i { background: var(--acc-bg); border-color: var(--acc); }
.st-radio[aria-checked="true"] i::after { content: ""; width: 18px; height: 18px; border-radius: 50%; background: var(--acc); }
.st-radio:focus-visible { outline: 2px solid var(--acc); outline-offset: 4px; border-radius: 4px; }
.st-note { margin: 10px 8px 0; font-size: 13px; }
.st-grp { margin: 18px 8px 0; padding-bottom: 6px; font: 700 12.5px var(--font); letter-spacing: .08em; text-transform: uppercase; color: var(--acc);
          border-bottom: 1.5px solid var(--rule); }
.st-g > .st-grp { margin-top: 4px; }
.st-g + .st-g { margin-top: 14px; }

/* Landscape screens (the MTX: 1024 x 768 at 67 %, about 1530 px wide): each box in two columns, rows stacked
   (label, help, control), so Settings and Fault Thresholds fit without scrolling. */
.st-cols { display: grid; grid-template-columns: minmax(0, 1fr); }
@media (min-width: 1200px) {
  .st-cols { grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 48px; align-items: start; }
  .st-cols .st-row { grid-template-columns: minmax(0, 1fr); grid-template-areas: "lbl" "sub" "ctl" "msg"; gap: 8px; padding: 14px 8px; }
  .st-cols .st-ctl { max-width: 560px; }
  .st-faults .st-ctl, .st-faults .st-msg { padding-left: 24px; }
  .st-faults .st-row:nth-last-child(2) { border-bottom: 0; }   /* bottom row of both columns */
}
/* Reset: always looks like a button; blue when there is something to reset, muted (still outlined) when not. */
.st-reset { display: inline-flex; align-items: center; gap: 7px; background: #fff; border-color: var(--acc); color: var(--acc);
            box-shadow: 0 1px 2px rgba(31, 35, 40, .12); }
.st-reset svg { width: 15px; height: 15px; fill: none; stroke: currentColor; stroke-width: 2.2; stroke-linecap: round; stroke-linejoin: round; }
.st-reset:hover:not(:disabled) { background: var(--acc-bg); border-color: var(--acc); }
.st-reset:disabled { cursor: default; color: var(--mute); border-color: var(--line); box-shadow: none; }

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
function settingRow(key, s, extra = "") {
  const below = typeof extra === "object" ? extra.below : "";   // { below: html } goes under the choices
  if (below) extra = "";
  if (s.options) {
    return `
  <div class="st-row" data-key="${escapeHtml(key)}">
    <div class="st-lbl">${dot(s)}${title(s)}</div>
    <div class="st-ctl"><div class="st-choices${extra ? " fit" : ""}" role="radiogroup" aria-label="${title(s)}">${s.options.map((o, i) =>
      `<button class="st-radio" role="radio" data-i="${i}">${escapeHtml(optLabel(s, o))}<i></i></button>`).join("")}</div>${extra}</div>
    ${sub(s.help)}${below ? `<p class="st-below">${below}</p>` : ""}
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

// read-only row for one recorded value (none used at the moment; kept for later).
const recordedRow = (id, label, unit, note) => `
  <div class="st-row">
    <div class="st-lbl">${escapeHtml(label)}</div>
    <div class="st-ctl"><span class="st-ro"><b id="${id}">${DASH}</b> ${escapeHtml(unit)}</span></div>
    ${sub(note)}
  </div>`;

const rowsFor = (section) => Object.entries(SETTINGS).filter(([, s]) => s.section === section);

// Settings section, grouped under small headings: recorded (read-only) rows first, then the settings with that
// group in js/settings.js, then any extra rows. A setting without a group goes under "Other" (hidden when empty).
const group = (heading, recorded, key, after = "", extras = {}) => {
  const rows = rowsFor("settings").filter(([, s]) => s.group === key).map(([k, s]) => settingRow(k, s, extras[k])).join("");
  const body = recorded + rows + after;
  return body.trim() ? `<div class="st-g"><div class="st-grp">${escapeHtml(heading)}</div>${body}</div>` : "";
};

const TEMPLATE = () => `
<div class="st">
  <section class="panel"><h3>SETTINGS<span class="actions"><button class="btn st-reset" id="stReset" type="button"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 4v5h5"/></svg>Reset to defaults</button></span></h3>
    <div class="st-cols">
      <div>
      ${group("Time", "", "time", "", { timeFormat: `<span class="st-now" title="Bag time, from the recording · read-only"><b id="stTime">${DASH}</b><span id="stDate"></span></span>` })}
      ${group("Camera", "", "camera")}
      </div>
      <div>
      ${group("Occupancy grid", "", "grid", "", { gridCellM: { below: `Recorded: <b id="stGridRes">${DASH}</b> m per cell (/local_costmap/voxel_layer)` } })}
      ${group("Other", "", undefined)}
      </div>
    </div>
    <p class="mute st-note">Saved in this browser only. Another browser or computer keeps its own settings.</p>
  </section>

  <section class="panel st-faults"><h3>FAULT THRESHOLDS<span class="st-hint">Colours used in Faults and Sensors</span></h3>
    <div class="st-cols">${rowsFor("faults").map(([k, s]) => settingRow(k, s)).join("")}</div>
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
      $("stReset").title = changed ? "Put every setting back to its default" : "Nothing to reset: every setting is at its default";
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
    offs.push(cavs.on("/local_costmap/voxel_layer", (d) => {
      const r = d.resolution ?? d.info?.resolution;
      $("stGridRes").textContent = r != null ? String(+r.toFixed(3)) : DASH;   // recorded as float32 (0.20000000298…); shown rounded
    }));

    // Bag time in the chosen 12 / 24 hour format (this page already follows the time-format setting).
    // Bag time next to the time format choice, in the chosen format (same clock as the header).
    const showTime = () => {
      const t = state?.bagTime;
      $("stTime").textContent = t == null ? DASH : clock(t);
      $("stDate").textContent = t == null ? "" : dateLabel(t);
    };
    offs.push(cavs.on("/mtx/odom", showTime));

    showSettings(); showTime();
    offs.push(
      onSettingChange((key) => { showSettings(); if (key === "timeFormat") showTime(); }),
      cavs.onRestart(() => { $("stGridRes").textContent = DASH; showTime(); }),
    );
    return () => offs.forEach((off) => off());
  },
};
