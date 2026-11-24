// Home dashboard (Home_Sketch_v4 / Figma "Dashboard-V2"). Owner: Zeenat. Author: Zeenat Islam
// Six panels: drive status, camera, navigation/costmap, systems health, LiDAR occupancy grid, event log.
// Shows recorded values only (C-021).

import { cameraSrc, yawFromQuaternion } from "../../../client/cavs-client.js";
import { clock, num, ms, escapeHtml, diagTone } from "../lib/format.js";
import { onEvents, clearEvents } from "../state.js";
import { getSetting, onSettingChange } from "../settings.js";
import { COLORS, gridCanvas, occupancyRGB, fitView, bounds, fitCanvas, polyline, scaleBar, redrawer, distanceRings } from "../lib/draw.js";

const RING_STEP_M = 10;      // distance rings around the vehicle in the navigation view
const RING_MIN_PX = 14;      // closer than this on screen: rings every 5 × RING_STEP_M instead
const NAV_MIN_SPAN_M = 30;  // navigation view is at least this wide, so the vehicle stays small before a plan or path arrives
const VEHICLE_MARKER_PX = [24, 15];   // occupancy grid vehicle marker, length × width in pixels (not to scale; feedback 17 Nov 2026)

/** Vehicle marker outline, front pointing up, centred on 0,0 (canvas pixels, y down). */
function markerPath(L, B) {
  return [[0, -L / 2], [B / 2, -L / 6], [B / 2, L / 2], [-B / 2, L / 2], [-B / 2, -L / 6]];
}

const VEHICLE_COLOR = COLORS.acc;   // one vehicle marker (shape + colour) on every map and legend

/** Draw the vehicle marker centred at (x, y) on screen; `angle` = clockwise turn from pointing up (radians). */
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

/** Vehicle marker as a small SVG for the legend (same shape as on the grid). */
function vehicleIcon(heightPx, gapPx) {
  const [L, B] = VEHICLE_MARKER_PX, w = (heightPx * B / L).toFixed(1);
  const pts = markerPath(L, B).map((p) => p.join(",")).join(" ");
  return `<svg width="${w}" height="${heightPx}" viewBox="${-B / 2} ${-L / 2} ${B} ${L}" aria-hidden="true" ` +
    `style="vertical-align:middle;margin:0 ${(gapPx ?? 19 - w).toFixed(1)}px 0 0"><polygon points="${pts}" fill="${VEHICLE_COLOR}"/></svg>`;
}

/**
 * Vehicle centre, heading and size from the recorded footprint polygon (frame odom).
 * Heading = direction of the footprint's longest side, pointed the way /mtx/odom faces.
 */
function vehiclePose(fp, odom) {
  if (!fp || fp.length < 3) return null;
  const cx = fp.reduce((s, p) => s + p[0], 0) / fp.length, cy = fp.reduce((s, p) => s + p[1], 0) / fp.length;
  let best = 0, yaw = 0;
  fp.forEach((p, i) => {
    const q = fp[(i + 1) % fp.length], len = Math.hypot(q[0] - p[0], q[1] - p[1]);
    if (len > best) { best = len; yaw = Math.atan2(q[1] - p[1], q[0] - p[0]); }
  });
  if (odom) {
    const o = yawFromQuaternion(odom.qz, odom.qw);
    if (Math.cos(yaw - o) < 0) yaw += Math.PI;
  }
  let fMin = Infinity, fMax = -Infinity, lMin = Infinity, lMax = -Infinity;
  for (const [x, y] of fp) {
    const dx = x - cx, dy = y - cy, f = dx * Math.cos(yaw) + dy * Math.sin(yaw), l = -dx * Math.sin(yaw) + dy * Math.cos(yaw);
    fMin = Math.min(fMin, f); fMax = Math.max(fMax, f); lMin = Math.min(lMin, l); lMax = Math.max(lMax, l);
  }
  return { cx, cy, yaw, length: fMax - fMin, width: lMax - lMin };
}

const TEMPLATE = `
<div class="home">
  <div class="row1">
    <section class="panel"><h3>◉ DRIVE STATUS</h3>
      <div id="mode" class="mode"><b>WAITING FOR DATA</b><span>&nbsp;</span></div>
      <div class="kv"><span>Speed</span><b class="mono" id="speed">—</b></div>
      <div class="kv"><span>Commanded speed</span><b class="mono" id="cmdSpeed">—</b></div>
      <div class="kv"><span>Commanded turn</span><b class="mono" id="cmdTurn">—</b></div>
      <div class="kv"><span>Command source</span><b class="mono" id="cmdSource">—</b></div>
    </section>

    <section class="panel"><h3>▣ CAMERA<span class="actions" id="camBtns">
        <button class="btn" data-cam="0">CAM 0</button><button class="btn" data-cam="1">CAM 1</button><button class="btn" data-cam="2">CAM 2</button></span></h3>
      <div class="camimg">
        <div class="noimg" id="camX">
          <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="8.5" cy="9.5" r="1.8"/><path d="M3 17l5-5 4 4 3-3 6 6"/><path d="M2 2l20 20"/></svg>
          <span id="camXmsg">No image available</span>
        </div>
        <img id="camImg" alt="" hidden>
        <span class="tag l" id="camL">CAM 2 · /cam_2/image_raw</span><span class="tag r" id="camR">no image</span>
      </div>
    </section>

    <section class="panel"><h3>⌖ NAVIGATION</h3>
      <div class="mapbox"><canvas id="nav"></canvas></div>
      <div class="legend"><span><i></i>driven</span><span><i class="dash"></i>planned</span><span><i class="sq"></i>costmap obstacle</span><span><i class="ring"></i>distance from vehicle</span><span>${vehicleIcon(13, 5)}vehicle</span></div>
    </section>
  </div>

  <div class="row2">
    <section class="panel"><h3><span class="ttl"><svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12h4l2.5-6 4 13 3-9 2 2H22"/></svg>SYSTEMS HEALTH</span></h3>
      <div class="kv"><span>Safety filter</span><b id="hfSafety">—</b></div>
      <div class="kv"><span>Nav2</span><b id="hfNav2">—</b></div>
      <div class="kv"><span>Drive bridge</span><b id="hfBridge">—</b></div>
      <div class="kv"><span>Odometry age</span><b class="mono" id="ageOdom">—</b></div>
      <div class="kv"><span>LiDAR age</span><b class="mono" id="ageLidar">—</b></div>
      <div class="kv"><span>Command age</span><b class="mono" id="ageCmd">—</b></div>
    </section>

    <section class="panel"><h3>◎ LiDAR · OCCUPANCY GRID</h3>
      <div class="lidar">
        <div class="gridbox"><canvas id="grid"></canvas></div>
        <div class="lleg">
          <div><i style="background:${COLORS.bad}"></i>Occupied</div>
          <div><i style="background:#fafaf8;border:1px solid ${COLORS.line}"></i>Free</div>
          <div>${vehicleIcon(15)}Vehicle<div class="mute" style="font-size:12px;padding-left:19px">not to scale</div></div>
          <div class="meta" id="gridMeta">waiting for<br>/local_costmap/<wbr>voxel_layer</div>
        </div>
      </div>
    </section>

    <section class="panel"><h3>☰ EVENT LOG<span class="actions"><a class="link" href="#/logs">View full log ›</a><button class="btn" id="clear">Clear</button></span></h3>
      <div class="events" id="events"><div class="empty">No events yet.</div></div>
    </section>
  </div>
</div>`;

export default {
  title: "Home",
  mount(root, { cavs, state }) {
    root.innerHTML = TEMPLATE;
    const $ = (id) => root.querySelector("#" + id);
    const offs = [];
    const on = (topic, fn) => offs.push(cavs.on(topic, fn));
    const set = (id, text, cls) => { const el = $(id); el.textContent = text; if (cls !== undefined) el.className = cls; };

    // ------------------------------------------------------------ drive status
    function renderMode() {
      const a = cavs.latest("/mtx/arbiter_status");
      const el = $("mode");
      if (!a) return;
      const plan = cavs.latest("/plan")?.poses;
      const end = plan && plan.length ? plan[plan.length - 1] : null;
      let tone, title, sub;
      if (a.mode === 2 || a.estop) { tone = "bad"; title = "E-STOP"; sub = "Software e-stop latched"; }
      else if (a.mode === 1 && a.autonomy_active) {
        tone = "ok"; title = "AUTONOMOUS";
        sub = end ? `End of plan<br>(${end[0].toFixed(2)}, ${end[1].toFixed(2)})` : "Autonomy active";
      } else if (a.mode === 1) {
        tone = "warn"; title = "AUTONOMY REQUESTED";
        sub = "Not active: " + escapeHtml(a.inhibit_reasons.join(", ") || "—");
      } else { tone = ""; title = "MANUAL"; sub = a.joy_fresh ? "Joystick input" : "No joystick input"; }
      el.className = "mode " + tone;
      el.innerHTML = `<b>${title}</b><span>${sub}</span>`;
    }
    on("/mtx/arbiter_status", (a) => { renderMode(); set("cmdSource", a.active_source || "(none)"); });
    on("/plan", renderMode);
    on("/mtx/odom", (d) => set("speed", num(d.linear_x, 2, "m/s")));
    on("/mtx/cmd_vel_autonomy", (d) => { set("cmdSpeed", num(d.linear_x, 2, "m/s")); set("cmdTurn", num(d.angular_z, 3, "rad/s", true)); });

    // ------------------------------------------------------------ layout (feedback 17 Nov 2026)
    // Camera panel as wide as the image needs at the row's height (no grey bars); occupancy grid panel
    // as wide as a square grid + legend; Navigation and Event log take the remaining width.
    let camAspect = 4 / 3;                       // updated from the recorded width / height of each frame
    const SIDE_COL = 330, GAP = 14, NAV_MIN = 360, CAM_MIN = 420;
    const layout = () => {
      const home = root.querySelector(".home"), cam = root.querySelector(".camimg"), lidar = root.querySelector(".lidar");
      if (!home || !cam || !lidar) return;
      const camPanel = cam.closest(".panel"), avail = home.clientWidth - SIDE_COL - 2 * GAP;
      const camW = cam.clientHeight * camAspect + (camPanel.offsetWidth - cam.clientWidth);
      const camCol = Math.round(Math.max(CAM_MIN, Math.min(camW, avail - NAV_MIN)));
      home.querySelector(".row1").style.gridTemplateColumns = `${SIDE_COL}px ${camCol}px 1fr`;
      const occPanel = lidar.closest(".panel"), leg = root.querySelector(".lleg");
      const occW = lidar.clientHeight + 16 + leg.offsetWidth + (occPanel.offsetWidth - lidar.clientWidth);
      home.querySelector(".row2").style.gridTemplateColumns = `${SIDE_COL}px ${Math.round(occW)}px 1fr`;
    };

    // ------------------------------------------------------------ camera (default CAM 2, C-013)
    root.querySelectorAll("#camBtns .btn").forEach((b) => (b.onclick = () => cavs.setCamera(+b.dataset.cam)));
    let camId = 2, camHz = 2, camTimer = null;
    // Blank-image icon until a frame arrives, after switching camera, or when frames stop
    // (none for 3 frame intervals, at least 3 s).
    const noImage = (msg) => {
      $("camImg").hidden = true; $("camX").style.display = "";
      set("camXmsg", msg); set("camR", "no image");
    };
    const armStale = () => {
      clearTimeout(camTimer);
      camTimer = setTimeout(() => noImage(`No image from CAM ${camId}`), Math.max(3000, 3000 / camHz));
    };
    offs.push(() => clearTimeout(camTimer));
    const showCam = (s) => {
      if (s.camera_hz) camHz = s.camera_hz;
      if (s.camera != null && s.camera !== camId) { camId = s.camera; noImage(`Waiting for CAM ${camId}`); armStale(); }
      root.querySelectorAll("#camBtns .btn").forEach((b) => b.classList.toggle("on", +b.dataset.cam === camId));
      set("camL", `CAM ${camId} · /cam_${camId}/image_raw`);
    };
    offs.push(cavs.onSettings(showCam));
    for (const c of [0, 1, 2]) on(`/cam_${c}/image_raw`, (d) => {
      if (c !== camId) return;
      const img = $("camImg");
      img.src = cameraSrc(d); img.hidden = false; $("camX").style.display = "none"; armStale();
      set("camR", `${d.width} × ${d.height} · ${d.encoding}`);
      if (d.width && d.height && Math.abs(d.width / d.height - camAspect) > 0.01) { camAspect = d.width / d.height; layout(); }
    });

    // ------------------------------------------------------------ navigation / costmap
    let globalGrid = null;
    const drawNav = redrawer(() => {
      const cv = $("nav"); if (!cv) return;
      const { ctx, w, h } = fitCanvas(cv);
      ctx.clearRect(0, 0, w, h);
      const plan = cavs.latest("/plan")?.poses || [];
      const path = cavs.latest("/dlio/odom_node/path")?.poses || [];
      const fp = cavs.latest("/local_costmap/published_footprint")?.points || [];
      const b = bounds([plan, path, fp, [[0, 0]]], 3, NAV_MIN_SPAN_M);
      if (!b) return;
      const v = fitView(...b, w, h);
      if (globalGrid) {
        const g = globalGrid.grid;
        ctx.imageSmoothingEnabled = false;
        ctx.drawImage(globalGrid.canvas, v.x(g.origin_x), v.y(g.origin_y + g.height * g.resolution),
                      g.width * g.resolution * v.k, g.height * g.resolution * v.k);
      }
      // distance rings around the vehicle, every RING_STEP_M (fewer when they would sit too close together),
      // under the plan and path (lib/draw.js distanceRings, shared with the Map page)
      const pose = vehiclePose(fp, cavs.latest("/mtx/odom"));
      if (pose) distanceRings(ctx, v, v.x(pose.cx), v.y(pose.cy), w, h, RING_STEP_M, RING_MIN_PX);
      if (plan.length) {
        ctx.setLineDash([7, 6]); ctx.strokeStyle = COLORS.acc; ctx.lineWidth = 2.5;
        polyline(ctx, v, plan); ctx.stroke(); ctx.setLineDash([]);
      }
      if (path.length) {
        ctx.strokeStyle = COLORS.ink; ctx.lineWidth = 4; ctx.lineCap = "round"; ctx.lineJoin = "round";
        polyline(ctx, v, path); ctx.stroke();
      }
      // vehicle first (same marker as the occupancy grid, not to scale, pointing the way it faces),
      // so the START / PLAN END markers and labels stay readable on top
      if (pose) drawVehicle(ctx, v.x(pose.cx), v.y(pose.cy), Math.PI / 2 - pose.yaw);
      // start (odom origin) and end of plan; labels get a white outline so they read over anything
      const label = (t, x, y) => { ctx.lineWidth = 3.5; ctx.strokeStyle = "#fff"; ctx.lineJoin = "round"; ctx.strokeText(t, x, y); ctx.fillStyle = COLORS.ink; ctx.fillText(t, x, y); };
      const sx = v.x(0), sy = v.y(0);
      ctx.strokeStyle = COLORS.acc; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.rect(sx - 6, sy - 6, 12, 12);              // square: no direction implied
      ctx.fillStyle = "#fff"; ctx.fill(); ctx.stroke();
      ctx.font = "700 12px Inter, 'Segoe UI', Helvetica, Arial, sans-serif";
      label("START (0, 0)", sx - 14, sy + 21);
      if (plan.length) {
        const [gx, gy] = plan[plan.length - 1];
        ctx.beginPath(); ctx.arc(v.x(gx), v.y(gy), 9, 0, 2 * Math.PI);
        ctx.fillStyle = "#e9f6ec"; ctx.fill(); ctx.strokeStyle = COLORS.ok; ctx.lineWidth = 2.5; ctx.stroke();
        label("PLAN END", v.x(gx) + 14, v.y(gy) + 5);
      }
      scaleBar(ctx, v, h, 5);
    });
    on("/global_costmap/costmap", async (d) => { globalGrid = await gridCanvas(d); drawNav(); });
    on("/plan", drawNav); on("/dlio/odom_node/path", drawNav); on("/local_costmap/published_footprint", drawNav);

    // ------------------------------------------------------------ systems health (dots only on recorded statuses)
    const dotted = (id, tone, text) => { $(id).innerHTML = `<span class="dot ${tone}"></span>${escapeHtml(text)}`; };
    on("/mtx/velocity_filter/status", (d) => {
      dotted("hfSafety", d.ok ? "ok" : "warn", d.ok ? "ok" : "inhibit: " + (d.inhibit_reasons.join(", ") || "—"));
      set("ageOdom", ms(d.odom_age_s)); set("ageLidar", ms(d.lidar_age_s)); set("ageCmd", ms(d.cmd_age_s));
    });
    on("/diagnostics", () => {
      const nav2 = Object.values(state.diagnostics).find((s) => s.name.includes("Nav2"));
      if (nav2) dotted("hfNav2", diagTone(nav2.level), nav2.message);
      const br = state.diagnostics["mtx_nav2/drive_bridge"];
      if (br) dotted("hfBridge", diagTone(br.level), br.message);
    });

    // ------------------------------------------------------------ LiDAR occupancy grid (C-016, C-017)
    // Top view from the vehicle: vehicle at the centre, front at the top (feedback 17 Nov 2026).
    // Shows the recorded footprint + the "Occupancy grid view" setting on every side (default 1 m, feedback 10 Nov 2026).
    // Cells come from /local_costmap/voxel_layer unchanged; only the drawing is rotated.
    let voxel = null;
    const drawGrid = redrawer(() => {
      const cv = $("grid"); if (!cv || !voxel) return;
      const { ctx, w, h } = fitCanvas(cv);
      const g = voxel.grid, res = g.resolution, W = g.width * res, H = g.height * res;
      const fp = cavs.latest("/local_costmap/published_footprint")?.points;
      const pose = vehiclePose(fp, cavs.latest("/mtx/odom"));
      const { cx, cy, yaw } = pose || { cx: g.origin_x + W / 2, cy: g.origin_y + H / 2, yaw: Math.PI / 2 };
      const margin = getSetting("gridMarginM");
      const span = pose ? Math.max(pose.length, pose.width) + 2 * margin : Math.max(W, H);
      const k = Math.min(w, h) / span;                                  // pixels per metre

      ctx.fillStyle = `rgb(${COLORS.unknown})`; ctx.fillRect(0, 0, w, h);  // outside the recorded grid
      // world (odom, metres) -> screen: vehicle centre at the middle, heading pointing up
      const sn = Math.sin(yaw), cs = Math.cos(yaw);
      const a = k * sn, b = -k * cs, c = -k * cs, d = -k * sn;
      ctx.save();
      ctx.transform(a, b, c, d, w / 2 - a * cx - c * cy, h / 2 - b * cx - d * cy);
      ctx.save();
      ctx.translate(g.origin_x, g.origin_y + H); ctx.scale(res, -res);  // grid image row 0 is the top (highest y)
      ctx.imageSmoothingEnabled = false;
      ctx.drawImage(voxel.canvas, 0, 0);
      ctx.restore();
      ctx.restore();
      // Reference lines fixed to the panel (they don't move or turn), centred on the vehicle:
      // thin every cell (0.2 m) while cells are at least 4 px, bold every 1, 5 or 10 m (at least 20 px apart).
      // Only the recorded cells move as the vehicle drives.
      const boldM = [1, 5, 10, 20].find((m) => m * k >= 20) || 50;
      const thin = res * k >= 4, step = thin ? res * k : boldM * k;
      const perBold = Math.round(boldM / (thin ? res : boldM)), n = Math.ceil(Math.max(w, h) / 2 / step) + 1;
      for (let i = -n; i <= n; i++) {
        const bold = i % perBold === 0;
        ctx.strokeStyle = bold ? "#9aa1a9" : "#e3e6e9"; ctx.lineWidth = bold ? 1.2 : 0.6;
        const x = w / 2 + i * step, y = h / 2 + i * step;
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
      }

      if (pose) drawVehicle(ctx, w / 2, h / 2);                          // front up, not to scale
      scaleBar(ctx, { k }, h, boldM);
      $("gridMeta").textContent = "";                                    // legend says the rest; scale bar shows 1 m
    });
    on("/local_costmap/voxel_layer", async (d) => { voxel = await gridCanvas(d, occupancyRGB); drawGrid(); });
    offs.push(onSettingChange((key) => key === "gridMarginM" && drawGrid()));
    on("/local_costmap/published_footprint", drawGrid);
    on("/mtx/odom", drawGrid);

    // ------------------------------------------------------------ event log (shared, clearable: C-010)
    const renderEvents = redrawer(() => {
      const box = $("events"); if (!box) return;
      const ev = state.events;
      box.innerHTML = ev.length ? ev.map((e) =>
        `<div class="er"><span class="t">${clock(e.stamp)}</span><span class="lv ${e.tone}">${e.label}</span>` +
        `<span class="n">${escapeHtml(e.node)}</span><span class="m" title="${escapeHtml(e.msg)}">${escapeHtml(e.msg)}</span></div>`).join("")
        : `<div class="empty">No events since cleared.</div>`;
    });
    $("clear").onclick = clearEvents;
    offs.push(onEvents(renderEvents));
    renderEvents();
    offs.push(cavs.onRestart(() => { globalGrid = null; voxel = null; drawNav(); }));

    // redraw canvases when the window changes size
    const ro = new ResizeObserver(() => { layout(); drawNav(); drawGrid(); });
    ro.observe(root.querySelector(".home")); ro.observe($("nav")); ro.observe($("grid"));

    return () => { offs.forEach((off) => off()); ro.disconnect(); };
  },
};
