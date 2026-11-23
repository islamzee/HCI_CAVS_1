// Logs page (Team_Pages_Sketch_v3 / Figma "Logs", "IndividualLog") — Owner: Chuck.
//
//   #/logs               past runs: one row per bag
//   #/logs/<run name>    run detail: /rosout lines with level and node filters
//
// Recorded values only (C-021): every cell is a field from the bag's metadata.yaml or from a /rosout message.
// Light theme only (C-014), visual only (C-015).

import { cavs } from "../state.js";
import { ROSOUT_LEVEL, rosoutTone, escapeHtml, clock } from "../lib/format.js";
import { redrawer } from "../lib/draw.js";

// ================================================================ data
// The bridge sends the last 200 /rosout lines when a browser connects, then live lines only, and cavs.on() hands a
// page just the latest message when it mounts. So collect from page load: app.js imports this module at start-up,
// which means this code runs before you ever open the Logs tab.
// To get the WHOLE bag later, only this section changes (e.g. fetch the lines from a new bridge endpoint).

const MAX_LINES = 5000;
const keyOf = (l) => `${l.stamp}|${l.name}|${l.msg}`;
let lines = [];                      // oldest first: { stamp, level, name, msg }
const seen = new Set();              // the bridge re-sends its history after a reconnect: skip duplicates
const listeners = new Set();
const notify = () => listeners.forEach((f) => f());
/** Call fn() when the lines change. Returns an unsubscribe function. */
const onLines = (fn) => { listeners.add(fn); return () => listeners.delete(fn); };

cavs.on("/rosout", (d) => {
  const l = { stamp: d.stamp, level: d.level, name: d.name, msg: d.msg };
  if (seen.has(keyOf(l))) return;
  seen.add(keyOf(l));
  lines.push(l);
  if (lines.length > MAX_LINES) seen.delete(keyOf(lines.shift()));
  notify();
});
cavs.onRestart(() => { lines = []; seen.clear(); notify(); });     // bag looped back to 00:00 (see Frontend_Data_Guide §5)

// Deleting a log hides it in THIS browser (saved in localStorage, like js/settings.js). The bridge has no endpoint
// for removing a bag from the server, so the recording itself stays where it is; "Restore" brings the logs back.
// If the bridge ever gets a delete endpoint, call it inside deleteRuns().
const DELETED_KEY = "cavs.logs.deleted.v1";
let deleted = (() => { try { return new Set(JSON.parse(localStorage.getItem(DELETED_KEY) || "[]")); } catch { return new Set(); } })();
const saveDeleted = () => { try { localStorage.setItem(DELETED_KEY, JSON.stringify([...deleted])); } catch { /* storage blocked: lasts until reload */ } };
const bagInfo = () => cavs.settings?.bag || null;     // { name, start_ns, duration_ns, message_count, ros_distro } from the bridge
const allRuns = () => (bagInfo() ? [bagInfo()] : []); // one bag today; when the bridge lists several, only this changes
const visibleRuns = () => allRuns().filter((r) => !deleted.has(r.name));

const deletedListeners = new Set();
/** Call fn() after logs are deleted or restored. Returns an unsubscribe function. */
const onDeleted = (fn) => { deletedListeners.add(fn); return () => deletedListeners.delete(fn); };

function deleteRuns(names) {
  names.forEach((n) => deleted.add(n));
  saveDeleted();
  if (names.includes(bagInfo()?.name)) { lines = []; seen.clear(); notify(); }   // drop the collected lines of the deleted log
  deletedListeners.forEach((f) => f());
}
function restoreRuns() { deleted = new Set(); saveDeleted(); deletedListeners.forEach((f) => f()); }

// ================================================================ formatting (display only)
const TZ = "America/Chicago";
const dateFmt = new Intl.DateTimeFormat("en-US", { timeZone: TZ, month: "2-digit", day: "2-digit", year: "numeric" });
const timeFmt = new Intl.DateTimeFormat("en-US", { timeZone: TZ, hour: "numeric", minute: "2-digit", second: "2-digit", hour12: true });
const pad = (n) => String(n).padStart(2, "0");

const runDate = (ns) => dateFmt.format(new Date(ns / 1e6));                       // "09/11/2026"
const runStart = (ns) => timeFmt.format(new Date(ns / 1e6)).toLowerCase();        // "11:45:48 am"
const runLength = (ns) => { const s = Math.round(ns / 1e9); return `${pad(Math.floor(s / 3600))}:${pad(Math.floor(s / 60) % 60)}:${pad(s % 60)}`; };
const lineTime = (stamp) => {                                                     // "11:45:59.3"
  const tenths = Math.floor(stamp * 10 + 1e-4);
  return `${clock(Math.floor(tenths / 10))}.${tenths % 10}`;
};

// ================================================================ filters (kept while you switch pages)
const LEVEL_CHIPS = [[10, "DEBUG"], [20, "INFO"], [30, "WARN"], [40, "ERROR"]];   // ERROR chip also covers FATAL
const NODE_CHIPS = [["recorder", "rosbag2_recorder"], ["cameras", "cam_0–2"], ["other", "all other nodes"]];
const filters = { levels: new Set([20, 30, 40]), nodes: new Set(["other"]) };     // sketch defaults
const levelBucket = (lv) => Math.min(40, Math.max(10, Math.floor(lv / 10) * 10));
const nodeGroup = (n) => (n === "rosbag2_recorder" ? "recorder" : /^cam_\d$/.test(n) ? "cameras" : "other");
const visible = (l) => filters.levels.has(levelBucket(l.level)) && filters.nodes.has(nodeGroup(l.name));

// ================================================================ styles
const CSS = `
.lg { flex: 1; }
.lg-hint { font: 500 12.5px var(--mono); }
.lg-table { width: 100%; border-collapse: collapse; }
.lg-table th { text-align: left; font: 700 12px var(--mono); letter-spacing: .05em; color: var(--mute); padding: 8px; border-bottom: 1.5px solid var(--line); }
.lg-table td { padding: 12px 8px; font: 14.5px var(--mono); color: var(--mute); border-bottom: 1.5px solid var(--rule); }
.lg-table tbody tr { cursor: pointer; }
.lg-table tbody tr:hover { background: var(--acc-bg); }
.lg-table a { color: var(--acc); font-weight: 700; text-decoration: none; }
.lg-note { margin: 14px 8px 0; font-size: 14px; }
.lg-chips { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-bottom: 12px; flex: none; }
.lg-chip { font: 600 12.5px var(--font); padding: 3px 12px; border: 1.5px solid var(--line); border-radius: 999px; background: #fff; color: var(--mute); cursor: pointer; }
.lg-chip:hover { border-color: var(--mute); }
.lg-chip.on { border-color: var(--acc); background: var(--acc-bg); color: var(--acc); }
.lg-sep { width: 14px; flex: none; }
.lg-head, .lg-row { display: grid; grid-template-columns: 120px 76px 240px 1fr; gap: 10px; align-items: baseline; padding: 7px 8px; }
.lg-head { flex: none; font: 700 12px var(--mono); letter-spacing: .05em; color: var(--mute); border-bottom: 1.5px solid var(--line); padding-bottom: 8px; }
.lg-body { flex: 1; min-height: 0; overflow-y: auto; }
.lg-row { border-bottom: 1.5px solid var(--rule); font: 13px var(--mono); color: var(--mute); }
.lg-row:hover { background: var(--acc-bg); }
.lg-row .lv { justify-self: start; }
.lg-row .n { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.lg-row .m { overflow-wrap: anywhere; }
.btn.danger { border-color: var(--bad); color: var(--bad); background: #fff; }
.btn.danger:hover:not(:disabled) { background: var(--bad-bg); }
.btn:disabled { opacity: .45; cursor: default; }
.lg-table th.chk, .lg-table td.chk { width: 46px; padding-right: 0; }
.lg-table input[type=checkbox] { width: 17px; height: 17px; accent-color: var(--acc); cursor: pointer; vertical-align: middle; }
.lg-table tbody tr.sel { background: var(--acc-bg); }
.lg-linkbtn { font: 600 14px var(--font); color: var(--acc); background: none; border: 0; padding: 0; cursor: pointer; }
.lg-linkbtn:hover { text-decoration: underline; }
.lg-dialog { border: 1.5px solid var(--line); border-radius: 8px; padding: 22px 24px; width: 460px; max-width: 90vw; font-family: var(--font); color: var(--ink); }
.lg-dialog::backdrop { background: rgba(31, 35, 40, .45); }
.lg-dialog h4 { margin: 0 0 8px; font-size: 18px; }
.lg-dialog p { margin: 0 0 10px; font-size: 14.5px; line-height: 1.45; color: var(--mute); }
.lg-dialog ul { margin: 0; padding-left: 20px; font: 13.5px var(--mono); line-height: 1.7; }
.lg-dlg-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 18px; }
.lg-confirm { background: var(--bad); border-color: var(--bad); color: #fff; }
.lg-confirm:hover { background: #bd3a3a; border-color: #bd3a3a; }
`;
function ensureStyle() {
  if (document.getElementById("logs-css")) return;
  const s = document.createElement("style");
  s.id = "logs-css";
  s.textContent = CSS;
  document.head.append(s);
}

// ================================================================ views
// ---- confirmation (step two of every delete)
/** Modal "are you sure?" box. Resolves true only if the person presses the red button; Cancel, Esc and closing give false. */
function confirmDialog(root, { title, text, names = [], confirmLabel }) {
  return new Promise((resolve) => {
    const dlg = document.createElement("dialog");
    dlg.className = "lg-dialog";
    dlg.innerHTML = `<h4>${escapeHtml(title)}</h4><p>${escapeHtml(text)}</p>` +
      (names.length ? `<ul>${names.slice(0, 5).map((n) => `<li>${escapeHtml(n)}</li>`).join("")}${names.length > 5 ? `<li>…and ${names.length - 5} more</li>` : ""}</ul>` : "") +
      `<div class="lg-dlg-actions"><button class="btn" data-r="cancel" autofocus>Cancel</button>` +
      `<button class="btn lg-confirm" data-r="ok">${escapeHtml(confirmLabel)}</button></div>`;
    dlg.addEventListener("click", (e) => { const r = e.target.closest("[data-r]")?.dataset.r; if (r) dlg.close(r); });
    dlg.addEventListener("close", () => { dlg.remove(); resolve(dlg.returnValue === "ok"); });
    root.append(dlg);
    dlg.showModal();                                   // Cancel has focus, so Enter cannot delete by accident
  });
}
const deleteWording = (names) => {
  const one = names.length === 1;
  return {
    title: one ? "Are you sure you want to delete this log?" : `Are you sure you want to delete these ${names.length} logs?`,
    text: one ? "It will be removed from the Logs list. The recording itself stays on the server."
              : "They will be removed from the Logs list. The recordings themselves stay on the server.",
    names,
    confirmLabel: one ? "Yes, delete log" : `Yes, delete ${names.length} logs`,
  };
};

function mountList(root) {
  const selected = new Set();                           // run names ticked in the table
  root.innerHTML = `
<section class="panel lg">
  <h3>PAST RUNS<span class="actions"><span class="mute lg-hint">one row per bag on the server · fields from metadata.yaml</span>
    <button class="btn danger" id="lgDelSel" disabled>Delete selected</button></span></h3>
  <div id="lgRuns"></div>
  <p class="mute lg-note" id="lgNote"></p>
</section>`;
  const box = root.querySelector("#lgRuns"), note = root.querySelector("#lgNote"), delBtn = root.querySelector("#lgDelSel");

  const draw = () => {
    const runs = visibleRuns();
    for (const n of [...selected]) if (!runs.some((r) => r.name === n)) selected.delete(n);
    delBtn.disabled = !selected.size;
    delBtn.textContent = selected.size ? `Delete selected (${selected.size})` : "Delete selected";

    if (!runs.length) {
      box.innerHTML = `<div class="empty">${allRuns().length ? "No logs. All logs have been deleted." : cavs.status === "open" ? "The bridge did not send any run information." : "Not connected to the bag bridge."}</div>`;
    } else {
      box.innerHTML = `
<table class="lg-table">
  <thead><tr><th class="chk"><input type="checkbox" id="lgAll" aria-label="Select all logs"></th>
    <th>RUN</th><th>DATE</th><th>START</th><th>DURATION</th><th>MESSAGES</th><th>ROS</th></tr></thead>
  <tbody>${runs.map((b) => `
  <tr data-run="${escapeHtml(b.name)}" class="${selected.has(b.name) ? "sel" : ""}">
    <td class="chk"><input type="checkbox" aria-label="Select ${escapeHtml(b.name)}" ${selected.has(b.name) ? "checked" : ""}></td>
    <td><a href="#/logs/${encodeURIComponent(b.name)}">${escapeHtml(b.name)}</a></td>
    <td>${runDate(b.start_ns)}</td><td>${runStart(b.start_ns)}</td><td>${runLength(b.duration_ns)}</td>
    <td>${b.message_count.toLocaleString("en-US")}</td><td>${escapeHtml(b.ros_distro ?? "—")}</td>
  </tr>`).join("")}</tbody>
</table>`;
      const all = box.querySelector("#lgAll");
      all.checked = selected.size === runs.length;
      all.indeterminate = selected.size > 0 && selected.size < runs.length;
      all.onchange = () => { runs.forEach((r) => (all.checked ? selected.add(r.name) : selected.delete(r.name))); draw(); };
      box.querySelectorAll("tr[data-run]").forEach((tr) => {
        const name = tr.dataset.run;
        tr.querySelector("input").onchange = (e) => { e.target.checked ? selected.add(name) : selected.delete(name); draw(); };
        tr.onclick = (e) => { if (!e.target.closest("a, input")) location.hash = `#/logs/${encodeURIComponent(name)}`; };
      });
    }
    note.innerHTML = (runs.length ? "Select a run to open its log, or tick runs to delete them. " : "") +
      (deleted.size ? `<button class="lg-linkbtn" id="lgRestore">Restore deleted logs (${deleted.size})</button>` : "");
    note.querySelector("#lgRestore")?.addEventListener("click", restoreRuns);
  };

  delBtn.onclick = async () => {
    const names = [...selected];
    if (names.length && await confirmDialog(root, deleteWording(names))) { deleteRuns(names); selected.clear(); }
  };

  draw();
  const offs = [onDeleted(draw), cavs.onSettings(draw), cavs.onStatus(draw)];
  return () => offs.forEach((off) => off());
}

function mountDetail(root, run) {
  if (deleted.has(run)) { location.replace("#/logs"); return null; }     // e.g. the browser's back button after deleting
  root.innerHTML = `
<section class="panel lg">
  <h3><span id="lgTitle"></span><span class="actions"><span class="mute lg-hint" id="lgCount"></span><button class="btn danger" id="lgDelete">Delete log</button><a class="link" href="#/logs">‹ Past runs</a></span></h3>
  <div class="lg-chips">
    ${LEVEL_CHIPS.map(([v, label]) => `<button class="lg-chip" data-level="${v}">${label}</button>`).join("")}
    <span class="lg-sep"></span>
    ${NODE_CHIPS.map(([v, label]) => `<button class="lg-chip" data-node="${v}">${label}</button>`).join("")}
  </div>
  <div class="lg-head"><span>TIME (CDT)</span><span>LEVEL</span><span>NODE</span><span>MESSAGE</span></div>
  <div class="lg-body" id="lgBody"></div>
</section>`;
  const body = root.querySelector("#lgBody"), count = root.querySelector("#lgCount"), title = root.querySelector("#lgTitle");
  let first = true;

  const drawTitle = () => {
    const b = bagInfo();
    const known = b && b.name === run;
    title.textContent = `LOG · ${run}` + (known ? ` · ${runDate(b.start_ns)} · ${runLength(b.duration_ns)}` : "");
  };
  const drawChips = () => root.querySelectorAll(".lg-chip").forEach((c) => c.classList.toggle("on",
    c.dataset.level ? filters.levels.has(+c.dataset.level) : filters.nodes.has(c.dataset.node)));
  const drawLines = redrawer(() => {
    const follow = !first && body.scrollHeight - body.scrollTop - body.clientHeight < 40;   // stay at the newest line if you were there
    const shown = lines.filter(visible);
    body.innerHTML = shown.length ? shown.map((l) =>
      `<div class="lg-row"><span class="t">${lineTime(l.stamp)}</span><span class="lv ${rosoutTone(l.level)}">${ROSOUT_LEVEL[l.level] || l.level}</span>` +
      `<span class="n" title="${escapeHtml(l.name)}">${escapeHtml(l.name)}</span><span class="m">${escapeHtml(l.msg)}</span></div>`).join("")
      : `<div class="empty">${cavs.status !== "open" ? "Not connected to the bag bridge." : lines.length ? "No lines match the filters." : "No /rosout lines received yet."}</div>`;
    count.textContent = `/rosout · ${shown.length} lines`;
    if (follow) body.scrollTop = body.scrollHeight;
    first = false;
  }, 150);

  root.querySelectorAll(".lg-chip").forEach((c) => (c.onclick = () => {
    const set = c.dataset.level ? filters.levels : filters.nodes, v = c.dataset.level ? +c.dataset.level : c.dataset.node;
    set.has(v) ? set.delete(v) : set.add(v);
    drawChips(); drawLines();
  }));

  root.querySelector("#lgDelete").onclick = async () => {
    if (await confirmDialog(root, deleteWording([run]))) { deleteRuns([run]); location.replace("#/logs"); }   // back to the past-runs page
  };

  drawTitle(); drawChips(); drawLines();
  const offs = [onLines(drawLines), cavs.onSettings(drawTitle), cavs.onStatus(drawLines)];
  return () => offs.forEach((off) => off());
}

export default {
  title: "Logs",
  mount(root) {
    ensureStyle();
    const run = decodeURIComponent((location.hash.match(/^#\/logs\/([^?#]+)/) || [])[1] || "");
    return run ? mountDetail(root, run) : mountList(root);     // app.js remounts on every hash change
  },
};