// Shared connection and state for every page. Import this; do not create another CavsClient.
// Author: Zeenat Islam
//
//   import { cavs, state } from "../state.js";
//
// Websocket address:
//   - ?ws=... in the page URL always wins: http://localhost:8765/dashboard/?ws=ws://192.168.1.20:8765/
//   - page served by the bridge, directly (http://host:8765/dashboard/) or through a web server in front of it
//     (https://server/<prefix>/dashboard/): connect back to the same place, wss:// under https.
//     Checked by asking the page's own server for <prefix>/stats, which only the bridge answers.
//   - otherwise (VS Code Live Server, opened as a file): ws://localhost:8765/

import { CavsClient } from "../../client/cavs-client.js";
import { ROSOUT_LEVEL, rosoutTone, COLLISION_ACTION } from "./lib/format.js";

const params = new URLSearchParams(location.search);

async function defaultWsUrl() {
  if (location.protocol === "http:" || location.protocol === "https:") {
    const prefix = location.pathname.split("/dashboard/")[0];
    try {
      const ctl = new AbortController(), t = setTimeout(() => ctl.abort(), 1500);
      const r = await fetch(`${prefix}/stats`, { cache: "no-store", signal: ctl.signal });
      clearTimeout(t);
      if (r.ok && "received" in (await r.json())) return `${location.protocol === "https:" ? "wss:" : "ws:"}//${location.host}${prefix}/`;
    } catch { /* not the bridge */ }
  }
  return "ws://localhost:8765/";
}
const wsUrl = params.get("ws") || (await defaultWsUrl());

export const cavs = new CavsClient(wsUrl);

/** Values several pages need, kept up to date here (recorded values only). */
export const state = {
  diagnostics: {},   // status name -> { name, level, message, values, stamp } from /diagnostics
  estop: null,       // /mtx/estop data (true = latched), null until a message arrives
  bagTime: null,     // header stamp (s) of the latest /mtx/odom message: the bag's clock
  bag: null,         // { name, start_ns, duration_ns, ... } from the bag's metadata.yaml
  events: [],        // event log, newest first: { stamp, label, tone, node, msg }  (Home panel, Logs/Faults may reuse)
};

// ------------------------------------------------------------------ event log (recorded events, kept across pages)
const MAX_EVENTS = 500;
const eventListeners = new Set();
/** Call fn() whenever state.events changes. Returns an unsubscribe function. */
export function onEvents(fn) { eventListeners.add(fn); return () => eventListeners.delete(fn); }
/** Clear the event log (C-010). */
export function clearEvents() { state.events = []; eventListeners.forEach((f) => f()); }
function addEvent(e) {
  state.events.unshift(e);
  if (state.events.length > MAX_EVENTS) state.events.length = MAX_EVENTS;
  eventListeners.forEach((f) => f());
}
cavs.on("/rosout", (d) => {
  if (d.level < 30 || /^cam_\d$/.test(d.name)) return;            // WARN and above; camera rate lines stay in Logs
  addEvent({ stamp: d.stamp, label: ROSOUT_LEVEL[d.level] || String(d.level), tone: rosoutTone(d.level), node: d.name, msg: d.msg });
});
let lastSafety = null;
cavs.on("/mtx/velocity_filter/status", (d) => {
  const key = d.ok + "|" + d.inhibit_reasons.join(",");
  if (key !== lastSafety && !d.ok)
    addEvent({ stamp: d.stamp, label: "SAFETY", tone: "acc", node: "velocity_filter", msg: `ok=false inhibit_reasons=${d.inhibit_reasons.join(",")}` });
  lastSafety = key;
});
// e-stop / collision monitor: only live changes are events (the connect-time history just gives the current value)
cavs.on("/mtx/estop", (d) => cavs.historyDone && addEvent({ stamp: state.bagTime, label: d.data ? "ESTOP" : "INFO", tone: d.data ? "bad" : "mute", node: "estop", msg: `data=${d.data}` }));
cavs.on("/mtx/nav/collision_monitor_state", (d) => cavs.historyDone && addEvent({
  stamp: state.bagTime, label: d.action_type ? "WARN" : "INFO", tone: d.action_type ? "warn" : "mute", node: "collision_monitor",
  msg: `action_type=${d.action_type} (${COLLISION_ACTION[d.action_type] ?? "?"}) polygon=${d.polygon_name || "(none)"}` }));

cavs.on("/diagnostics", (d) => {
  for (const s of d.status) state.diagnostics[s.name] = { ...s, stamp: d.stamp };
});
cavs.on("/mtx/estop", (d) => (state.estop = d.data));
cavs.on("/mtx/odom", (d) => (state.bagTime = d.stamp));
cavs.onSettings((s) => (state.bag = s.bag || null));
cavs.onRestart(() => {
  state.diagnostics = {};
  state.estop = null;
  state.bagTime = null;
  lastSafety = null;
  clearEvents();
});
