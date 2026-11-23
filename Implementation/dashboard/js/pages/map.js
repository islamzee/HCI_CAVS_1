// Map page (Map V2 + Pin-scoped Route faults / Route log overlays).
// Owner: Nathan.
// Shows recorded values only (C-021): no calculated distances, counts, offsets, or durations.

import { yawFromQuaternion } from "../../../client/cavs-client.js";
import {
  clock, dateLabel, num, escapeHtml, COLLISION_ACTION, componentName, problemText, safetyReasons,
} from "../lib/format.js";
import { cavs, state, onEvents, clearEvents } from "../state.js";
import {
  COLORS, gridCanvas, fitView, bounds, fitCanvas, polyline, scaleBar, redrawer,
} from "../lib/draw.js";

const MIN_SPAN_M = 30;
const VEHICLE_MARKER_PX = [24, 15];
const VEHICLE_COLOR = COLORS.acc;
const MAX_FAULTS = 500;

const BUCKET_COLOR = {
  safety: COLORS.acc,
  warn: COLORS.warn,
  error: COLORS.bad,
};
const BUCKET_RANK = { safety: 1, warn: 2, error: 3 };

function eventBucket(ev) {
  if (ev.bucket) return ev.bucket;
  if (ev.tone === "bad") return "error";
  if (ev.label === "SAFETY" || ev.node === "collision_monitor") return "safety";
  if (ev.tone === "warn") return "warn";
  return "info";
}

function isDuplicateOfFaultRecord(ev) {
  return ev.label === "SAFETY" ||
    ev.label === "ESTOP" ||
    (ev.node === "collision_monitor" && ev.tone !== "mute");
}

/** Normalized badge text & tone for the Log overlay: SAFETY / WARN / CRIT / INFO. */
function logBadge(ev) {
  if (ev.tone === "bad") return { text: "CRIT", tone: "bad" };
  if (ev.label === "SAFETY") return { text: "SAFETY", tone: "acc" };
  if (ev.tone === "warn" || /^warn/i.test(ev.label || "")) return { text: "WARN", tone: "warn" };
  return { text: ev.label || "INFO", tone: ev.tone || "mute" };
}

/** Retain slash-prefixed ROS topic/filepath names for diagnostic statuses instead of friendly labels. */
function diagnosticTopicPath(s) {
  const vals = s.values || {};
  for (const [k, v] of Object.entries(vals)) {
    if (/topic/i.test(k) && typeof v === "string" && v.trim().startsWith("/")) {
      return v.trim();
    }
  }
  const raw = String(s.name || "").trim();
  if (!raw) return "/diagnostics";
  if (raw.startsWith("/")) return raw;
  if (raw.includes("/") && !raw.includes(":")) return `/${raw}`;
  const camMatch = raw.match(/(?:^|\b)cam(?:era)?[_\s-]*([0-2])(?:\b|$|:)/i);
  if (camMatch) return `/cam_${camMatch[1]}/image_raw`;
  if (raw.includes(":")) {
    const nodePart = raw.split(":")[0].trim().replace(/^\/+/, "");
    if (nodePart) return `/${nodePart}`;
  }
  return `/${raw.replace(/\s+/g, "_")}`;
}

/** Vehicle centre & heading in frame odom (matches home.js, with odom fallback). */
function vehiclePose(fp, odom) {
  if (fp && fp.length >= 3) {
    const cx = fp.reduce((s, p) => s + p[0], 0) / fp.length;
    const cy = fp.reduce((s, p) => s + p[1], 0) / fp.length;
    let best = 0, yaw = 0;
    fp.forEach((p, i) => {
      const q = fp[(i + 1) % fp.length], len = Math.hypot(q[0] - p[0], q[1] - p[1]);
      if (len > best) { best = len; yaw = Math.atan2(q[1] - p[1], q[0] - p[0]); }
    });
    if (odom) {
      const o = yawFromQuaternion(odom.qz, odom.qw);
      if (Math.cos(yaw - o) < 0) yaw += Math.PI;
    }
    return { cx, cy, yaw };
  }
  if (odom) return { cx: odom.x, cy: odom.y, yaw: yawFromQuaternion(odom.qz, odom.qw) };
  return null;
}

// ------------------------------------------------------------------ background route & fault tracker
const eventPos = new WeakMap();
const eventSeq = new WeakMap();
let seqCounter = 0;
let faultRecords = [];           // newest first: recorded status transitions
const activeFaults = new Map();  // key -> current active record (for deduplicating 2 Hz /diagnostics)
let pendingPos = [];             // startup alerts waiting for the first odom/footprint pose
let lastTopStateEvent = null;
const trackerListeners = new Set();
const notifyTracker = () => trackerListeners.forEach((fn) => fn());

function assignSeq(ev) {
  if (!eventSeq.has(ev)) eventSeq.set(ev, ++seqCounter);
}

function validStamp(stamp) {
  return (typeof stamp === "number" && stamp > 0) ? stamp : state.bagTime;
}

function currentPose() {
  return vehiclePose(
    cavs.latest("/local_costmap/published_footprint")?.points,
    cavs.latest("/mtx/odom"),
  );
}

function stampEvent(ev) {
  assignSeq(ev);
  if (eventPos.has(ev)) return;
  const pose = currentPose();
  if (pose) {
    eventPos.set(ev, { x: pose.cx, y: pose.cy });
  } else {
    pendingPos.push(ev);
  }
}

function flushPendingPos() {
  if (!pendingPos.length) return;
  const pose = currentPose();
  if (!pose) return;
  for (const ev of pendingPos) {
    if (!eventPos.has(ev)) eventPos.set(ev, { x: pose.cx, y: pose.cy });
  }
  pendingPos = [];
  notifyTracker();
}

function recordFaultTransition(key, spec, stamp) {
  const cur = activeFaults.get(key);
  if (cur && cur.bucket === spec.bucket && cur.detail === spec.detail) {
    return false;
  }
  const rec = {
    ...spec,
    key,
    source: "fault",
    stamp: validStamp(stamp),
  };
  stampEvent(rec);
  activeFaults.set(key, rec);
  faultRecords.unshift(rec);
  if (faultRecords.length > MAX_FAULTS) faultRecords.length = MAX_FAULTS;
  return true;
}

function clearActiveFault(key) {
  return activeFaults.delete(key);
}

function ingestDiagnosticStatus(s, stamp) {
  const key = `diag:${s.name}`;
  if (s.level <= 0) return clearActiveFault(key);
  const isCrit = s.level >= 2;
  const text = problemText(s);
  const topicPath = diagnosticTopicPath(s);
  const friendly = componentName(s.name);
  return recordFaultTransition(key, {
    bucket: isCrit ? "error" : "warn",
    label: s.level === 3 ? "STALE" : isCrit ? "CRITICAL" : "WARNING",
    tone: isCrit ? "bad" : "warn",
    topic: topicPath,
    topicHint: friendly !== topicPath ? `${friendly} (${s.name})` : s.name,
    node: topicPath,
    detail: text,
    msg: text,
  }, stamp);
}

function ingestVelocityFilter(d) {
  if (!d) return false;
  const key = "safety:velocity_filter";
  if (d.ok) return clearActiveFault(key);
  const reasons = safetyReasons(d.inhibit_reasons) || d.inhibit_reasons?.join(", ") || "inhibit";
  return recordFaultTransition(key, {
    bucket: "safety",
    label: "SAFETY",
    tone: "acc",
    topic: "/mtx/velocity_filter/status",
    topicHint: "Safety filter",
    node: "/mtx/velocity_filter/status",
    detail: `ok=false (${reasons})`,
    msg: `ok=false · ${reasons}`,
  }, d.stamp);
}

function ingestEstop(d) {
  if (!d) return false;
  const key = "fault:estop";
  if (!d.data) return clearActiveFault(key);
  return recordFaultTransition(key, {
    bucket: "error",
    label: "CRITICAL",
    tone: "bad",
    topic: "/mtx/estop",
    topicHint: "Software E-Stop",
    node: "/mtx/estop",
    detail: "data=true (latched)",
    msg: "Software e-stop latched",
  }, state.bagTime);
}

function ingestCollisionMonitor(d) {
  if (!d) return false;
  const key = "safety:collision_monitor";
  if (!d.action_type) return clearActiveFault(key);
  const action = COLLISION_ACTION[d.action_type] ?? `action ${d.action_type}`;
  const isStop = String(action).toLowerCase().includes("stop");
  const poly = d.polygon_name ? ` (${d.polygon_name})` : "";
  return recordFaultTransition(key, {
    bucket: isStop ? "error" : "safety",
    label: isStop ? "CRITICAL" : "SAFETY",
    tone: isStop ? "bad" : "warn",
    topic: "/mtx/nav/collision_monitor_state",
    topicHint: "Collision monitor",
    node: "/mtx/nav/collision_monitor_state",
    detail: `${action}${poly}`,
    msg: `${action}${poly}`,
  }, state.bagTime);
}

cavs.on("/mtx/odom", flushPendingPos);
cavs.on("/local_costmap/published_footprint", flushPendingPos);

cavs.on("/diagnostics", (d) => {
  let changed = false;
  for (const s of d.status || []) {
    if (ingestDiagnosticStatus(s, d.stamp)) changed = true;
  }
  if (changed) notifyTracker();
});
cavs.on("/mtx/velocity_filter/status", (d) => { if (ingestVelocityFilter(d)) notifyTracker(); });
cavs.on("/mtx/estop", (d) => { if (ingestEstop(d)) notifyTracker(); });
cavs.on("/mtx/nav/collision_monitor_state", (d) => { if (ingestCollisionMonitor(d)) notifyTracker(); });

onEvents(() => {
  const top = state.events[0] || null;
  if (top && top !== lastTopStateEvent) {
    const fresh = [];
    for (const ev of state.events) {
      if (ev === lastTopStateEvent) break;
      fresh.push(ev);
    }
    for (let i = fresh.length - 1; i >= 0; i--) stampEvent(fresh[i]);
  }
  if (!state.events.length) {
    faultRecords = [];
    pendingPos = [];
  }
  lastTopStateEvent = top;
  notifyTracker();
});

cavs.onRestart(() => {
  faultRecords = [];
  activeFaults.clear();
  pendingPos = [];
  lastTopStateEvent = null;
  notifyTracker();
});

// Hydrate any events/faults that already arrived before map.js initialized
for (let i = state.events.length - 1; i >= 0; i--) stampEvent(state.events[i]);
lastTopStateEvent = state.events[0] || null;
for (const s of Object.values(state.diagnostics)) ingestDiagnosticStatus(s, s.stamp);
ingestVelocityFilter(cavs.latest("/mtx/velocity_filter/status"));
ingestEstop(cavs.latest("/mtx/estop"));
ingestCollisionMonitor(cavs.latest("/mtx/nav/collision_monitor_state"));

function compareEntries(a, b, order = "desc") {
  const ta = a.stamp ?? 0, tb = b.stamp ?? 0;
  const diff = ta !== tb ? ta - tb : (eventSeq.get(a) ?? 0) - (eventSeq.get(b) ?? 0);
  return order === "asc" ? diff : -diff;
}

/** Unified log stream: all recorded fault transitions + /rosout + Info recovery entries. */
function allLogEntries(order = "asc") {
  const extra = state.events.filter((e) => !isDuplicateOfFaultRecord(e));
  return [...faultRecords, ...extra].sort((a, b) => compareEntries(a, b, order));
}

function clearAllRouteData() {
  faultRecords = [];
  pendingPos = [];
  clearEvents();
  notifyTracker();
}

// ------------------------------------------------------------------ drawing helpers
function markerPath(L, B) {
  return [[0, -L / 2], [B / 2, -L / 6], [B / 2, L / 2], [-B / 2, L / 2], [-B / 2, -L / 6]];
}

function drawVehicle(ctx, x, y, angle = 0) {
  const [L, B] = VEHICLE_MARKER_PX;
  ctx.save(); ctx.translate(x, y); ctx.rotate(angle);
  ctx.beginPath();
  markerPath(L, B).forEach(([px, py], i) => (i ? ctx.lineTo(px, py) : ctx.moveTo(px, py)));
  ctx.closePath();
  ctx.fillStyle = VEHICLE_COLOR; ctx.strokeStyle = "#fff"; ctx.lineWidth = 1.5; ctx.lineJoin = "round";
  ctx.fill(); ctx.stroke();
  ctx.restore();
}

function vehicleIcon(heightPx = 18) {
  const [L, B] = VEHICLE_MARKER_PX, w = (heightPx * B / L).toFixed(1);
  const pts = markerPath(L, B).map((p) => p.join(",")).join(" ");
  return `<svg width="${w}" height="${heightPx}" viewBox="${-B / 2} ${-L / 2} ${B} ${L}" aria-hidden="true"><polygon points="${pts}" fill="${VEHICLE_COLOR}"/></svg>`;
}

function triangleIcon(color, size = 16) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 16 16" aria-hidden="true"><polygon points="2,3 14,3 8,14" fill="${color}" stroke="${COLORS.ink}" stroke-width="1" stroke-linejoin="round"/></svg>`;
}

/** Pin marker; offset shadow indicates overlapping alerts at the same spot without displaying a count. */
function drawPin(ctx, x, y, r, fill, stacked = false, selected = false) {
  if (stacked) {
    ctx.beginPath();
    ctx.moveTo(x - r + 3, y - r * 0.75 - 3);
    ctx.lineTo(x + r + 3, y - r * 0.75 - 3);
    ctx.lineTo(x + 3, y + r * 1.05 - 3);
    ctx.closePath();
    ctx.fillStyle = "rgba(31, 35, 40, 0.25)";
    ctx.fill();
    ctx.strokeStyle = "#fff";
    ctx.lineWidth = 1.2;
    ctx.lineJoin = "round";
    ctx.stroke();
  }
  ctx.beginPath();
  ctx.moveTo(x - r, y - r * 0.75);
  ctx.lineTo(x + r, y - r * 0.75);
  ctx.lineTo(x, y + r * 1.05);
  ctx.closePath();
  ctx.fillStyle = fill;
  ctx.fill();
  ctx.strokeStyle = selected ? COLORS.ink : "#fff";
  ctx.lineWidth = selected ? 2.2 : 1.5;
  ctx.lineJoin = "round";
  ctx.stroke();
}

function baseToOdom(pts, odom) {
  const ox = odom.x, oy = odom.y, yaw = yawFromQuaternion(odom.qz, odom.qw);
  const c = Math.cos(yaw), s = Math.sin(yaw);
  return pts.map(([bx, by]) => [ox + bx * c - by * s, oy + bx * s + by * c]);
}

function drawGridLayer(ctx, v, layer, alpha = 1) {
  if (!layer) return;
  const g = layer.grid;
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(
    layer.canvas,
    v.x(g.origin_x),
    v.y(g.origin_y + g.height * g.resolution),
    g.width * g.resolution * v.k,
    g.height * g.resolution * v.k,
  );
  ctx.restore();
}

function clusterPins(events, v, radiusPx = 14) {
  const clusters = [];
  for (const ev of events) {
    const pos = eventPos.get(ev);
    if (!pos) continue;
    const px = v.x(pos.x), py = v.y(pos.y);
    const b = eventBucket(ev);
    let target = null;
    for (const c of clusters) {
      if (Math.hypot(c.px - px, c.py - py) <= radiusPx) { target = c; break; }
    }
    if (target) {
      target.events.push(ev);
      if (BUCKET_RANK[b] > BUCKET_RANK[target.bucket]) target.bucket = b;
    } else {
      clusters.push({ px, py, x: pos.x, y: pos.y, bucket: b, events: [ev] });
    }
  }
  clusters.sort((a, b) => BUCKET_RANK[a.bucket] - BUCKET_RANK[b.bucket]);
  return clusters;
}

const TEMPLATE = `
<style>
  .map-v2 { display: grid; grid-template-columns: 270px 1fr; gap: 14px; height: calc(100vh - 110px); min-height: 540px; }
  .map-v2 .rail { display: flex; flex-direction: column; gap: 8px; min-height: 0; }
  .map-v2 .clock-head { text-align: center; padding: 2px 0 8px; border-bottom: 1px solid ${COLORS.line}; }
  .map-v2 .clock-title { font-size: 11px; font-weight: 700; letter-spacing: .06em; color: ${COLORS.mute}; text-transform: uppercase; }
  .map-v2 .clock-val { font-size: 16px; font-weight: 700; margin-top: 2px; }
  .map-v2 .clock-sub { font-size: 11px; color: ${COLORS.mute}; margin-top: 1px; }
  .map-v2 .cards { display: flex; flex-direction: column; gap: 7px; flex: 1; min-height: 0; overflow: auto; }
  .map-v2 .mcard {
    display: flex; align-items: center; gap: 10px; width: 100%; text-align: left;
    padding: 8px 10px; border-radius: 7px; background: #fff; cursor: pointer;
    border: 1.5px solid var(--c, ${COLORS.line}); transition: opacity .15s, background .15s;
    font: inherit; color: ${COLORS.ink};
  }
  .map-v2 .mcard:hover { background: ${COLORS.bg}; }
  .map-v2 .mcard.off { opacity: .42; border-style: dashed; }
  .map-v2 .mcard .ico { width: 20px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
  .map-v2 .mcard .lbl { font-size: 13px; font-weight: 600; }
  .map-v2 .mcard .val { margin-left: auto; font-size: 12px; font-weight: 700; white-space: nowrap; }

  .map-v2 .pin-mode-box { padding-top: 6px; border-top: 1px solid ${COLORS.line}; }
  .map-v2 .pin-mode-lbl {
    font-size: 11px; font-weight: 700; letter-spacing: .06em; color: ${COLORS.mute};
    text-transform: uppercase; text-align: center; margin-bottom: 6px;
  }
  .map-v2 .rail-btns { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  .map-v2 .rail-btns .btn { padding: 8px 6px; font-size: 12px; font-weight: 600; text-align: center; }

  .map-v2 .stage-panel { display: flex; flex-direction: column; min-height: 0; }
  .map-v2 .stage-wrap { position: relative; flex: 1; min-height: 0; overflow: hidden; border-radius: 6px; }
  .map-v2 .stage-wrap canvas { width: 100%; height: 100%; display: block; cursor: grab; background: ${COLORS.bg}; }

  .map-v2 .map-overlay {
    position: absolute; top: 16px; left: 16px; z-index: 10; display: flex; flex-direction: column;
    width: min(780px, calc(100% - 32px)); max-height: calc(100% - 32px);
    background: rgba(255, 255, 255, .98); border: 1px solid ${COLORS.line}; border-radius: 10px;
    box-shadow: 0 12px 32px rgba(0, 0, 0, .18); padding: 12px 16px;
  }
  .map-v2 .map-overlay[hidden] { display: none; }
  .map-v2 .ov-head {
    display: flex; align-items: flex-start; gap: 10px; padding-bottom: 10px;
    border-bottom: 1px solid ${COLORS.line}; cursor: move; user-select: none;
  }
  .map-v2 .ov-head h4 { margin: 0; font-size: 15px; display: flex; align-items: center; gap: 6px; }
  .map-v2 .ov-grip { color: ${COLORS.mute}; font-size: 13px; letter-spacing: -1px; }
  .map-v2 .ov-sub { font-size: 12px; color: ${COLORS.mute}; margin-top: 2px; }
  .map-v2 .ov-actions { margin-left: auto; display: flex; align-items: center; gap: 8px; }
  .map-v2 .ov-actions button, .map-v2 .ov-actions a { cursor: pointer; }
  .map-v2 .ov-body { flex: 1; min-height: 0; overflow: auto; margin-top: 8px; }
  .map-v2 .ov-foot { margin-top: 8px; padding-top: 6px; border-top: 1px solid ${COLORS.line}; font-size: 11px; color: ${COLORS.mute}; }

  .map-v2 table.ov-tbl { width: 100%; border-collapse: collapse; font-size: 12px; }
  .map-v2 table.ov-tbl th {
    text-align: left; font-size: 11px; font-weight: 700; color: ${COLORS.mute}; letter-spacing: .04em;
    padding: 6px 8px; border-bottom: 1px solid ${COLORS.line}; position: sticky; top: 0; background: #fff;
  }
  .map-v2 table.ov-tbl td { padding: 6px 8px; border-bottom: 1px solid #eceef0; vertical-align: middle; }
  .map-v2 tr.flt-row.bad td:first-child { border-left: 3px solid ${COLORS.bad}; }
  .map-v2 tr.flt-row.warn td:first-child { border-left: 3px solid ${COLORS.warn}; }
  .map-v2 tr.flt-row.acc td:first-child { border-left: 3px solid ${COLORS.acc}; }
  .map-v2 tr.flt-row.bad { background: rgba(214, 69, 69, .05); }
  .map-v2 tr.flt-row.warn { background: rgba(212, 145, 0, .06); }
  .map-v2 tr.flt-row.acc { background: rgba(47, 111, 219, .05); }
  .map-v2 .pill {
    display: inline-block; padding: 2px 7px; border-radius: 4px; font-size: 11px; font-weight: 700;
    letter-spacing: .03em; color: #fff; white-space: nowrap;
  }
  .map-v2 .pill.bad { background: ${COLORS.bad}; }
  .map-v2 .pill.warn { background: ${COLORS.warn}; }
  .map-v2 .pill.acc { background: ${COLORS.acc}; }
  /* Match outlined SAFETY / WARN log badge style for CRIT logs */
  .map-v2 .ov-tbl .lv.bad {
    color: ${COLORS.bad};
    border: 1px solid ${COLORS.bad};
    background: rgb(255, 255, 255);
  }
  .map-v2 tr.pin-hit { cursor: pointer; }
  .map-v2 tr.pin-hit:hover { filter: brightness(.96); }
</style>

<div class="map-v2">
  <section class="panel rail">
    <div class="clock-head">
      <div class="clock-title">Recorded Bag Time</div>
      <div class="clock-val mono" id="mClock">—</div>
      <div class="clock-sub" id="mBagSub">waiting for bag…</div>
    </div>

    <div class="cards">
      <button class="mcard" id="cardVehicle" style="--c:${COLORS.acc}" title="Center and follow vehicle">
        <span class="ico">${vehicleIcon(18)}</span>
        <span class="lbl">Vehicle</span>
        <span class="val mono" id="mSpeed">—</span>
      </button>

      <button class="mcard" id="cardPos" style="--c:${COLORS.ink}" title="Fit driven route in view">
        <span class="ico"><svg width="16" height="16" viewBox="0 0 16 16"><line x1="8" y1="1" x2="8" y2="15" stroke="${COLORS.ink}" stroke-width="3" stroke-linecap="round"/></svg></span>
        <span class="lbl">Position</span>
        <span class="val mono" id="mPos">—</span>
      </button>

      <button class="mcard" id="cardWaypoint" style="--c:${COLORS.ok}" title="Pan to end of planned route">
        <span class="ico"><svg width="16" height="16" viewBox="0 0 16 16"><circle cx="8" cy="8" r="6" fill="#e9f6ec" stroke="${COLORS.ok}" stroke-width="2"/></svg></span>
        <span class="lbl">Plan End</span>
        <span class="val mono" id="mWaypoint">waiting…</span>
      </button>

      <button class="mcard" data-sev="safety" style="--c:${BUCKET_COLOR.safety}" title="Toggle Safety pins">
        <span class="ico">${triangleIcon(BUCKET_COLOR.safety)}</span>
        <span class="lbl">Safety</span>
        <span class="val" id="stSafety"><span class="dot mute"></span>waiting</span>
      </button>

      <button class="mcard" data-sev="warn" style="--c:${BUCKET_COLOR.warn}" title="Toggle Warning pins">
        <span class="ico">${triangleIcon(BUCKET_COLOR.warn)}</span>
        <span class="lbl">Warnings</span>
        <span class="val mute" id="stWarn">Shown</span>
      </button>

      <button class="mcard" data-sev="error" style="--c:${BUCKET_COLOR.error}" title="Toggle Critical / Error pins">
        <span class="ico">${triangleIcon(BUCKET_COLOR.error)}</span>
        <span class="lbl">Errors</span>
        <span class="val mute" id="stError">Shown</span>
      </button>
    </div>

    <div class="pin-mode-box">
      <div class="pin-mode-lbl">Pin View Filter</div>
      <div class="rail-btns">
        <button class="btn on" id="btnModeFaults" title="Show fault pins and open Faults table on pin click">Faults</button>
        <button class="btn" id="btnModeLogs" title="Show log pins and open Logs table on pin click">Logs</button>
      </div>
    </div>
  </section>

  <section class="panel stage-panel">
    <h3>
      ⌖ MAP
      <span class="actions" style="flex-wrap:wrap;gap:6px;">
        <button class="btn on" data-layer="global">Global Costmap</button>
        <button class="btn on" data-layer="local">Local Costmap</button>
        <button class="btn on" data-layer="zones">Safety Zones</button>
        <button class="btn on" data-layer="footprint">Footprint</button>
        <button class="btn on" data-mode="fit">Fit Route</button>
        <button class="btn" data-mode="follow">Follow</button>
      </span>
    </h3>

    <div class="stage-wrap" id="stageWrap">
      <canvas id="mapCv"></canvas>

      <div class="map-overlay" id="mapOverlay" hidden>
        <div class="ov-head" id="ovDragHandle" title="Drag to move window">
          <div>
            <h4><span class="ov-grip" aria-hidden="true">⋮⋮</span><span id="ovTitle">Faults · Selected point</span></h4>
            <div class="ov-sub" id="ovSub"></div>
          </div>
          <div class="ov-actions">
            <a class="link" id="ovFullLink" href="#/faults">Open full Faults ›</a>
            <button class="btn" id="ovSort" hidden title="Toggle chronological sort order">Oldest first</button>
            <button class="btn" id="ovClear">Clear Pins</button>
            <button class="btn" id="ovClose" title="Close (Esc)">✕</button>
          </div>
        </div>
        <div class="ov-body" id="ovBody"></div>
        <div class="ov-foot" id="ovFoot"></div>
      </div>
    </div>

    <div class="legend" style="flex-wrap:wrap;margin-top:8px;">
      <span><i></i>driven</span>
      <span><i class="dash"></i>planned</span>
      <span><i class="sq"></i>costmap obstacle</span>
      <span><i style="background:rgba(212,145,0,.22);border:1.5px solid ${COLORS.warn};height:10px;width:12px;"></i>slowdown</span>
      <span><i style="background:rgba(214,69,69,.24);border:1.5px solid ${COLORS.bad};height:10px;width:12px;"></i>stop zone</span>
      <span><i style="background:rgba(47, 111, 219, 0.12);border:1.5px solid ${COLORS.ink};height:10px;width:12px;"></i>footprint</span>
      <span class="mute" id="mapHint" style="margin-left:auto;">Click pins to view faults at that point · Drag to pan · Scroll to zoom</span>
    </div>
  </section>
</div>`;

export default {
  title: "Map",
  mount(root, { cavs: client, state: st }) {
    root.innerHTML = TEMPLATE;
    const $ = (id) => root.querySelector("#" + id);
    const offs = [];
    const on = (topic, fn) => offs.push(client.on(topic, fn));

    let alive = true;
    let globalGrid = null, localGrid = null;
    let globalGen = 0, localGen = 0;

    const layers = { global: true, local: true, zones: true, footprint: true };
    const sevFilter = { safety: true, warn: true, error: true };
    let pinMode = "faults";   // "faults" | "logs"
    let logOrder = "asc";

    const cam = { mode: "fit", cx: 0, cy: 0, span: MIN_SPAN_M };
    let lastView = null, lastBox = null, lastClusters = [];

    // null | { x, y, stamp, worldRadius, clickedEvents }
    let selectedSpot = null;
    let ovPos = null; // { left, top } once user drags the overlay

    function syncModeButtons() {
      root.querySelectorAll("[data-mode]").forEach((b) => b.classList.toggle("on", b.dataset.mode === cam.mode));
    }
    function syncLayerButtons() {
      root.querySelectorAll("[data-layer]").forEach((b) => b.classList.toggle("on", layers[b.dataset.layer]));
    }
    function syncPinModeButtons() {
      $("btnModeFaults").classList.toggle("on", pinMode === "faults");
      $("btnModeLogs").classList.toggle("on", pinMode === "logs");
      $("mapHint").textContent = pinMode === "faults"
        ? "Click pins to view faults at that point · Drag to pan · Scroll to zoom"
        : "Click pins to view logs at that point · Drag to pan · Scroll to zoom";
    }
    function syncSevLabels() {
      $("stWarn").textContent = sevFilter.warn ? "Shown" : "Hidden";
      $("stError").textContent = sevFilter.error ? "Shown" : "Hidden";
    }

    function clampOverlayPos(left, top) {
      const wrap = $("stageWrap"), box = $("mapOverlay");
      if (!wrap || !box || box.hidden) return { left, top };
      const pad = 8;
      const maxL = Math.max(pad, wrap.clientWidth - box.offsetWidth - pad);
      const maxT = Math.max(pad, wrap.clientHeight - box.offsetHeight - pad);
      return {
        left: Math.min(maxL, Math.max(pad, left)),
        top: Math.min(maxT, Math.max(pad, top)),
      };
    }

    function applyOverlayPos() {
      const wrap = $("stageWrap"), box = $("mapOverlay");
      if (!wrap || !box || box.hidden) return;
      const desired = ovPos ?? {
        left: Math.round((wrap.clientWidth - box.offsetWidth) / 2),
        top: 16,
      };
      const clamped = clampOverlayPos(desired.left, desired.top);
      box.style.left = `${clamped.left}px`;
      box.style.top = `${clamped.top}px`;
    }

    function snapshotToManual() {
      if (cam.mode === "manual") return;
      if (lastBox) {
        const [x0, x1, y0, y1] = lastBox;
        cam.cx = (x0 + x1) / 2;
        cam.cy = (y0 + y1) / 2;
        cam.span = Math.max(x1 - x0, y1 - y0);
      } else {
        const odom = client.latest("/mtx/odom");
        if (odom) { cam.cx = odom.x; cam.cy = odom.y; }
      }
      cam.mode = "manual";
      syncModeButtons();
    }

    function computeBox(plan, path, fp, odom) {
      if (cam.mode === "follow" && odom) {
        const r = cam.span / 2;
        return [odom.x - r, odom.x + r, odom.y - r, odom.y + r];
      }
      if (cam.mode === "fit") {
        const b = bounds([plan, path, fp, [[0, 0]]], 3, MIN_SPAN_M);
        if (b) return b;
      }
      const r = cam.span / 2;
      return [cam.cx - r, cam.cx + r, cam.cy - r, cam.cy + r];
    }

    function modeEvents() {
      if (pinMode === "faults") return faultRecords;
      return allLogEntries("desc").filter((e) => eventBucket(e) !== "info");
    }

    function activePinEvents() {
      return modeEvents().filter((e) => sevFilter[eventBucket(e)]);
    }

    function updateClock() {
      $("mClock").textContent = st.bagTime != null ? clock(st.bagTime) : "—";
      const parts = [];
      if (st.bag?.name) parts.push(st.bag.name);
      if (st.bagTime != null) parts.push(dateLabel(st.bagTime));
      $("mBagSub").textContent = parts.length ? parts.join(" · ") : "waiting for bag…";
    }

    function updateSafetyCard(sf) {
      const el = $("stSafety");
      if (!sf) {
        el.innerHTML = `<span class="dot mute"></span>waiting`;
        return;
      }
      el.innerHTML = `<span class="dot ${sf.ok ? "ok" : "warn"}"></span>${sf.ok ? "OK" : "INHIBIT"}`;
    }

    // ------------------------------------------------------------ pin-scoped movable overlay
    function getSpotList() {
      if (!selectedSpot) return [];
      const { x, y, stamp, worldRadius, clickedEvents } = selectedSpot;
      const matchesSpot = (ev) => {
        if (clickedEvents.has(ev)) return true;
        const pos = eventPos.get(ev);
        if (!pos) return false;
        const nearSpace = Math.hypot(pos.x - x, pos.y - y) <= worldRadius;
        const nearTime = stamp != null && ev.stamp != null && Math.abs(ev.stamp - stamp) <= 1.0;
        return nearSpace || (nearTime && Math.hypot(pos.x - x, pos.y - y) <= worldRadius * 2);
      };

      if (pinMode === "faults") {
        return faultRecords.filter((f) => sevFilter[f.bucket] && matchesSpot(f));
      }
      return allLogEntries(logOrder).filter((e) => {
        const b = eventBucket(e);
        return (b === "info" || sevFilter[b]) && matchesSpot(e);
      });
    }

    function renderOverlay() {
      if (!alive) return;
      const box = $("mapOverlay");
      if (!box) return;
      if (!selectedSpot) { box.hidden = true; return; }
      const wasHidden = box.hidden;
      box.hidden = false;

      const list = getSpotList();
      const bagName = st.bag?.name || "current run";
      const ts = selectedSpot.stamp != null ? clock(selectedSpot.stamp) : "—";
      const coordTxt = `odom (${num(selectedSpot.x, 2)}, ${num(selectedSpot.y, 2)}) m`;
      const link = $("ovFullLink");
      const sortBtn = $("ovSort");
      const body = $("ovBody");
      const foot = $("ovFoot");
      const prevScroll = body.scrollTop;

      if (pinMode === "faults") {
        $("ovTitle").textContent = "Faults · Selected point";
        $("ovSub").textContent = [bagName, ts, coordTxt].filter(Boolean).join(" · ");
        link.href = "#/faults";
        link.textContent = "Open full Faults ›";
        sortBtn.hidden = true;
        foot.textContent = "Recorded status flags at this spot. Drag header to move window.";

        if (!list.length) {
          body.innerHTML = `<div class="empty">No recorded faults at this point for the selected cards. Select <b>Logs</b> on the left to inspect log entries here.</div>`;
        } else {
          body.innerHTML = `
            <table class="ov-tbl">
              <thead><tr><th>STATUS</th><th>TIME</th><th>TOPIC</th><th>RECORDED STATE</th></tr></thead>
              <tbody>
                ${list.map((f, i) => {
                  const icon = f.tone === "bad" ? "▲" : "●";
                  const stateColor = f.tone === "bad" ? COLORS.bad : f.tone === "warn" ? COLORS.warn : COLORS.acc;
                  return `<tr class="flt-row ${f.tone} pin-hit" data-ov-idx="${i}">
                    <td><span class="pill ${f.tone}">${icon} ${escapeHtml(f.label)}</span></td>
                    <td class="mono">${clock(f.stamp)}</td>
                    <td class="mono" title="${escapeHtml(f.topicHint || f.topic)}">${escapeHtml(f.topic)}</td>
                    <td class="mono" style="color:${stateColor};">${escapeHtml(f.detail)}</td>
                  </tr>`;
                }).join("")}
              </tbody>
            </table>`;
        }
      } else {
        $("ovTitle").textContent = "Log · Selected point";
        $("ovSub").textContent = [bagName, ts, coordTxt].filter(Boolean).join(" · ");
        link.href = "#/logs";
        link.textContent = "Open full log ›";
        sortBtn.hidden = false;
        sortBtn.textContent = logOrder === "asc" ? "Oldest first" : "Newest first";
        foot.textContent = "Recorded log entries at this point. Drag header to move window.";

        if (!list.length) {
          body.innerHTML = `<div class="empty">No matching log entries at this point for the selected cards.</div>`;
        } else {
          body.innerHTML = `
            <table class="ov-tbl">
              <thead><tr><th>TIME</th><th>LEVEL</th><th>NODE / TOPIC</th><th>MESSAGE</th></tr></thead>
              <tbody>
                ${list.map((e, i) => {
                  const b = logBadge(e);
                  return `<tr class="pin-hit" data-ov-idx="${i}">
                    <td class="mono">${clock(e.stamp)}</td>
                    <td><span class="lv ${b.tone}">${escapeHtml(b.text)}</span></td>
                    <td class="mono" title="${escapeHtml(e.topicHint || e.node)}">${escapeHtml(e.node)}</td>
                    <td>${escapeHtml(e.msg)}</td>
                  </tr>`;
                }).join("")}
              </tbody>
            </table>`;
        }
      }

      if (prevScroll > 0) body.scrollTop = prevScroll;
      if (wasHidden || ovPos) applyOverlayPos();
    }

    const scheduleOverlay = redrawer(() => {
      if (selectedSpot) renderOverlay();
    }, 150);

    // Dragging the overlay window by its header bar
    let ovDrag = null;
    const onOvDown = (e) => {
      if (e.button !== 0 || e.target.closest("button, a")) return;
      const box = $("mapOverlay");
      ovDrag = {
        sx: e.clientX,
        sy: e.clientY,
        origLeft: box.offsetLeft,
        origTop: box.offsetTop,
      };
      e.preventDefault();
    };
    const onOvMove = (e) => {
      if (!ovDrag) return;
      const next = clampOverlayPos(
        ovDrag.origLeft + (e.clientX - ovDrag.sx),
        ovDrag.origTop + (e.clientY - ovDrag.sy),
      );
      ovPos = next;
      const box = $("mapOverlay");
      box.style.left = `${next.left}px`;
      box.style.top = `${next.top}px`;
    };
    const onOvUp = () => { ovDrag = null; };

    $("ovDragHandle").addEventListener("mousedown", onOvDown);
    window.addEventListener("mousemove", onOvMove);
    window.addEventListener("mouseup", onOvUp);

    $("ovBody").addEventListener("click", (e) => {
      const row = e.target.closest("[data-ov-idx]");
      if (!row) return;
      const ev = getSpotList()[Number(row.dataset.ovIdx)];
      if (!ev) return;
      const pos = eventPos.get(ev);
      if (!pos) return;
      cam.cx = pos.x; cam.cy = pos.y;
      cam.span = Math.min(cam.span, 18);
      cam.mode = "manual";
      selectedSpot = null;
      syncModeButtons();
      renderOverlay();
      drawMap();
    });

    $("ovSort").onclick = () => {
      logOrder = logOrder === "asc" ? "desc" : "asc";
      renderOverlay();
    };
    $("ovClose").onclick = () => { selectedSpot = null; ovPos = null; renderOverlay(); drawMap(); };
    $("ovClear").onclick = () => { clearAllRouteData(); selectedSpot = null; ovPos = null; renderOverlay(); drawMap(); };

    // ------------------------------------------------------------ map canvas
    const drawMap = redrawer(() => {
      if (!alive) return;
      const cv = $("mapCv"); if (!cv) return;
      const { ctx, w, h } = fitCanvas(cv);
      ctx.fillStyle = COLORS.bg;
      ctx.fillRect(0, 0, w, h);

      const odom = client.latest("/mtx/odom");
      const plan = client.latest("/plan")?.poses || [];
      const path = client.latest("/dlio/odom_node/path")?.poses || [];
      const fp = client.latest("/local_costmap/published_footprint")?.points || [];
      const stopZone = client.latest("/mtx/nav/stop_zone")?.points || [];
      const slowZone = client.latest("/mtx/nav/slowdown_zone")?.points || [];
      const col = client.latest("/mtx/nav/collision_monitor_state");

      const box = computeBox(plan, path, fp, odom);
      const v = fitView(...box, w, h);
      lastBox = box;
      lastView = v;

      // 1. Costmaps
      if (layers.global) drawGridLayer(ctx, v, globalGrid, 1.0);
      if (layers.local) drawGridLayer(ctx, v, localGrid, layers.global && globalGrid ? 0.65 : 1.0);

      // 2. Planned path (/plan)
      if (plan.length > 1) {
        ctx.setLineDash([7, 6]); ctx.strokeStyle = COLORS.acc; ctx.lineWidth = 2.5;
        polyline(ctx, v, plan); ctx.stroke(); ctx.setLineDash([]);
      }

      // 3. Driven path (/dlio/odom_node/path)
      if (path.length > 1) {
        ctx.strokeStyle = COLORS.ink; ctx.lineWidth = 4; ctx.lineCap = "round"; ctx.lineJoin = "round";
        polyline(ctx, v, path); ctx.stroke();
      }

      // 4. Safety zones (base_link -> odom)
      if (layers.zones && odom) {
        const activePoly = (col?.action_type && col?.polygon_name) ? col.polygon_name.toLowerCase() : "";
        if (slowZone.length > 2) {
          const hit = activePoly.includes("slow");
          polyline(ctx, v, baseToOdom(slowZone, odom), true);
          ctx.fillStyle = hit ? "rgba(212, 145, 0, 0.36)" : "rgba(212, 145, 0, 0.14)";
          ctx.fill();
          ctx.strokeStyle = COLORS.warn; ctx.lineWidth = hit ? 2.5 : 1.5; ctx.stroke();
        }
        if (stopZone.length > 2) {
          const hit = activePoly.includes("stop");
          polyline(ctx, v, baseToOdom(stopZone, odom), true);
          ctx.fillStyle = hit ? "rgba(214, 69, 69, 0.42)" : "rgba(214, 69, 69, 0.18)";
          ctx.fill();
          ctx.strokeStyle = COLORS.bad; ctx.lineWidth = hit ? 2.5 : 1.5; ctx.stroke();
        }
      }

      // 5. True-scale vehicle footprint outline
      if (layers.footprint && fp.length > 2) {
        polyline(ctx, v, fp, true);
        ctx.fillStyle = "rgba(47, 111, 219, 0.12)";
        ctx.fill();
        ctx.strokeStyle = COLORS.ink; ctx.lineWidth = 1.5; ctx.stroke();
      }

      // 6. Standard vehicle marker (matches home.js)
      const pose = vehiclePose(fp, odom);
      if (pose) drawVehicle(ctx, v.x(pose.cx), v.y(pose.cy), Math.PI / 2 - pose.yaw);

      // 7. START (0, 0) & PLAN END markers
      const label = (t, x, y) => {
        ctx.lineWidth = 3.5; ctx.strokeStyle = "#fff"; ctx.lineJoin = "round";
        ctx.strokeText(t, x, y); ctx.fillStyle = COLORS.ink; ctx.fillText(t, x, y);
      };
      ctx.font = "700 12px Inter, 'Segoe UI', Helvetica, Arial, sans-serif";
      const sx = v.x(0), sy = v.y(0);
      ctx.strokeStyle = COLORS.acc; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.rect(sx - 6, sy - 6, 12, 12);
      ctx.fillStyle = "#fff"; ctx.fill(); ctx.stroke();
      label("START (0, 0)", sx - 14, sy + 21);

      if (plan.length) {
        const [gx, gy] = plan[plan.length - 1];
        ctx.beginPath(); ctx.arc(v.x(gx), v.y(gy), 9, 0, 2 * Math.PI);
        ctx.fillStyle = "#e9f6ec"; ctx.fill(); ctx.strokeStyle = COLORS.ok; ctx.lineWidth = 2.5; ctx.stroke();
        label("PLAN END", v.x(gx) + 14, v.y(gy) + 5);
      }

      // 8. Alert pins for the active Pin View Filter (stacked shadow when overlapping, no numeric count)
      lastClusters = clusterPins(activePinEvents(), v, 14);
      for (const c of lastClusters) {
        const isSel = !!selectedSpot &&
          (c.events.some((e) => selectedSpot.clickedEvents.has(e)) ||
            Math.hypot(c.x - selectedSpot.x, c.y - selectedSpot.y) <= selectedSpot.worldRadius);
        drawPin(ctx, c.px, c.py, isSel ? 9 : 7, BUCKET_COLOR[c.bucket], c.events.length > 1, isSel);
      }

      const barM = [1, 2, 5, 10, 20, 50].find((m) => m * v.k >= 45) || 100;
      scaleBar(ctx, v, h, barM);
    });

    // ------------------------------------------------------------ controls
    root.querySelectorAll("[data-sev]").forEach((card) => {
      card.onclick = () => {
        const k = card.dataset.sev;
        sevFilter[k] = !sevFilter[k];
        card.classList.toggle("off", !sevFilter[k]);
        syncSevLabels();
        renderOverlay();
        drawMap();
      };
    });

    $("cardVehicle").onclick = () => { cam.mode = "follow"; syncModeButtons(); drawMap(); };
    $("cardPos").onclick = () => { cam.mode = "fit"; syncModeButtons(); drawMap(); };
    $("cardWaypoint").onclick = () => {
      const plan = client.latest("/plan")?.poses;
      if (!plan || !plan.length) return;
      const [gx, gy] = plan[plan.length - 1];
      cam.cx = gx; cam.cy = gy; cam.mode = "manual";
      syncModeButtons(); drawMap();
    };

    const setPinMode = (mode) => {
      if (pinMode === mode) return;
      pinMode = mode;
      syncPinModeButtons();
      renderOverlay();
      drawMap();
    };
    $("btnModeFaults").onclick = () => setPinMode("faults");
    $("btnModeLogs").onclick = () => setPinMode("logs");

    root.querySelectorAll("[data-layer]").forEach((b) => {
      b.onclick = () => {
        const k = b.dataset.layer;
        layers[k] = !layers[k];
        syncLayerButtons(); drawMap();
      };
    });
    root.querySelectorAll("[data-mode]").forEach((b) => {
      b.onclick = () => {
        cam.mode = b.dataset.mode;
        syncModeButtons(); drawMap();
      };
    });

    // ------------------------------------------------------------ pan, zoom & clickable pins
    const cv = $("mapCv");
    let drag = null;
    const onDown = (e) => {
      drag = { x: e.clientX, y: e.clientY, sx: e.clientX, sy: e.clientY, moved: false };
      cv.style.cursor = "grabbing";
    };
    const onMove = (e) => {
      if (!drag || !lastView) return;
      const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
      if (!drag.moved && Math.hypot(e.clientX - drag.sx, e.clientY - drag.sy) > 4) {
        drag.moved = true;
        snapshotToManual();
      }
      drag.x = e.clientX; drag.y = e.clientY;
      if (drag.moved) {
        cam.cx -= dx / lastView.k;
        cam.cy += dy / lastView.k;
        drawMap();
      }
    };
    const onUp = (e) => {
      if (drag && !drag.moved && lastClusters.length && lastView) {
        const rect = cv.getBoundingClientRect();
        const mx = e.clientX - rect.left, my = e.clientY - rect.top;
        let hit = null, best = 18;
        for (const c of lastClusters) {
          const d = Math.hypot(c.px - mx, c.py - my);
          if (d < best) { best = d; hit = c; }
        }
        if (hit) {
          selectedSpot = {
            x: hit.x,
            y: hit.y,
            stamp: hit.events[0]?.stamp ?? null,
            worldRadius: Math.max(1.5, 16 / lastView.k),
            clickedEvents: new Set(hit.events),
          };
          renderOverlay();
          drawMap();
        }
      }
      drag = null;
      cv.style.cursor = "grab";
    };
    const onWheel = (e) => {
      e.preventDefault();
      if (cam.mode === "fit") snapshotToManual();
      cam.span = Math.max(4, Math.min(400, cam.span * (e.deltaY > 0 ? 1.15 : 0.87)));
      drawMap();
    };
    const onKeyDown = (e) => {
      if (e.key === "Escape" && selectedSpot) { selectedSpot = null; ovPos = null; renderOverlay(); drawMap(); }
    };

    cv.addEventListener("mousedown", onDown);
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    cv.addEventListener("wheel", onWheel, { passive: false });
    window.addEventListener("keydown", onKeyDown);

    // ------------------------------------------------------------ ROS topic subscriptions
    function updateOdom(d) {
      if (!d) return;
      $("mSpeed").textContent = num(d.linear_x, 2, "m/s");
      $("mPos").textContent = `${num(d.x, 1)}, ${num(d.y, 1)} m`;
      updateClock();
      drawMap();
    }
    function updatePlan(d) {
      const pts = d?.poses || [];
      if (pts.length) {
        const [gx, gy] = pts[pts.length - 1];
        $("mWaypoint").textContent = `(${num(gx, 1)}, ${num(gy, 1)}) m`;
      } else {
        $("mWaypoint").textContent = "waiting…";
      }
      drawMap();
    }

    on("/mtx/odom", updateOdom);
    on("/dlio/odom_node/path", drawMap);
    on("/plan", updatePlan);
    on("/local_costmap/published_footprint", drawMap);
    on("/mtx/nav/stop_zone", drawMap);
    on("/mtx/nav/slowdown_zone", drawMap);
    on("/mtx/nav/collision_monitor_state", drawMap);
    on("/mtx/velocity_filter/status", updateSafetyCard);

    on("/global_costmap/costmap", async (d) => {
      const gen = ++globalGen;
      const decoded = await gridCanvas(d);
      if (alive && gen === globalGen) { globalGrid = decoded; drawMap(); }
    });
    on("/local_costmap/costmap", async (d) => {
      const gen = ++localGen;
      const decoded = await gridCanvas(d);
      if (alive && gen === localGen) { localGrid = decoded; drawMap(); }
    });

    offs.push(client.onSettings(updateClock));

    const onTrackerUpdate = () => {
      if (!alive) return;
      if (!allLogEntries().length) selectedSpot = null;
      scheduleOverlay();
      drawMap();
    };
    trackerListeners.add(onTrackerUpdate);
    offs.push(() => trackerListeners.delete(onTrackerUpdate));

    offs.push(client.onRestart(() => {
      globalGrid = null; localGrid = null;
      selectedSpot = null; ovPos = null;
      $("mSpeed").textContent = "—";
      $("mPos").textContent = "—";
      $("mWaypoint").textContent = "waiting…";
      $("stSafety").innerHTML = `<span class="dot mute"></span>waiting`;
      updateClock();
      renderOverlay();
      drawMap();
    }));

    // Hydrate from cached latest values on mount
    updateOdom(client.latest("/mtx/odom"));
    updatePlan(client.latest("/plan"));
    updateSafetyCard(client.latest("/mtx/velocity_filter/status"));
    updateClock();
    syncSevLabels();
    syncPinModeButtons();

    const ro = new ResizeObserver(() => {
      drawMap();
      if (selectedSpot) applyOverlayPos();
    });
    ro.observe(root.querySelector(".map-v2"));
    ro.observe(cv);

    drawMap();

    return () => {
      alive = false;
      offs.forEach((off) => off());
      ro.disconnect();
      cv.removeEventListener("mousedown", onDown);
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
      cv.removeEventListener("wheel", onWheel);
      window.removeEventListener("keydown", onKeyDown);
      $("ovDragHandle")?.removeEventListener("mousedown", onOvDown);
      window.removeEventListener("mousemove", onOvMove);
      window.removeEventListener("mouseup", onOvUp);
    };
  },
};