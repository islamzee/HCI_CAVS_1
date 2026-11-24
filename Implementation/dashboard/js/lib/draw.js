// Canvas helpers shared by the map-like panels (Home navigation + occupancy grid, Map, Sensors).
// Author: Zeenat Islam
//
// World coordinates are metres in frame "odom" (x right, y up on screen).

import { decodeGrid } from "../../../client/cavs-client.js";

export const COLORS = {
  ink: "#1f2328", mute: "#5f6670", line: "#c9cdd2", bg: "#f3f4f6",
  ok: "#2f9e44", warn: "#d49100", bad: "#d64545", acc: "#2f6fdb",
  free: [250, 250, 248], unknown: [236, 236, 232], occupied: [200, 70, 60],
};

/** Costmap cell value (0..100, −1 unknown) -> RGB. Shades between free and occupied show inflation. */
export function costmapRGB(v) {
  if (v < 0) return COLORS.unknown;
  if (v >= 99) return COLORS.occupied;
  if (v === 0) return COLORS.free;
  const t = v / 99;
  return [250 - 20 * t, 250 - 100 * t, 248 - 140 * t];
}

/** Occupied / free only (voxel layer: values are 0 or 100). */
export function occupancyRGB(v) {
  if (v < 0) return COLORS.unknown;
  return v >= 50 ? [214, 69, 69] : COLORS.free;
}

/**
 * Decode a grid message into an offscreen canvas (one pixel per cell, y up: grid row 0 at the bottom).
 * Resolves to { canvas, grid } where grid has width, height, resolution, origin_x, origin_y, values.
 */
export async function gridCanvas(msg, rgb = costmapRGB) {
  const g = await decodeGrid(msg);
  const c = document.createElement("canvas");
  c.width = g.width; c.height = g.height;
  const ctx = c.getContext("2d");
  const img = ctx.createImageData(g.width, g.height);
  for (let row = 0; row < g.height; row++) {
    const y = g.height - 1 - row;
    for (let col = 0; col < g.width; col++) {
      const [r, gg, b] = rgb(g.values[row * g.width + col]);
      const i = (y * g.width + col) * 4;
      img.data[i] = r; img.data[i + 1] = gg; img.data[i + 2] = b; img.data[i + 3] = 255;
    }
  }
  ctx.putImageData(img, 0, 0);
  return { canvas: c, grid: g };
}

/** View that maps world metres to canvas pixels, fitting the box [x0..x1] × [y0..y1] into w × h. */
export function fitView(x0, x1, y0, y1, w, h) {
  const k = Math.min(w / (x1 - x0), h / (y1 - y0));
  const ox = (w - (x1 - x0) * k) / 2, oy = (h - (y1 - y0) * k) / 2;
  return {
    k,
    x: (wx) => ox + (wx - x0) * k,
    y: (wy) => oy + (y1 - wy) * k,
  };
}

/** Bounding box of point lists [[x, y], …], padded, with a minimum span. */
export function bounds(lists, pad = 3, minSpan = 10) {
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
  for (const pts of lists) for (const [x, y] of pts || []) {
    x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y);
  }
  if (!Number.isFinite(x0)) return null;
  const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
  const sx = Math.max(x1 - x0 + 2 * pad, minSpan) / 2, sy = Math.max(y1 - y0 + 2 * pad, minSpan) / 2;
  return [cx - sx, cx + sx, cy - sy, cy + sy];
}

/** Size a canvas to its CSS box at device pixel ratio; returns the 2D context in CSS pixels. */
export function fitCanvas(canvas) {
  const r = canvas.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
  const w = Math.max(1, Math.round(r.width * dpr)), h = Math.max(1, Math.round(r.height * dpr));
  if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { ctx, w: r.width, h: r.height };
}

export function polyline(ctx, view, pts, close = false) {
  ctx.beginPath();
  pts.forEach(([x, y], i) => (i ? ctx.lineTo(view.x(x), view.y(y)) : ctx.moveTo(view.x(x), view.y(y))));
  if (close) ctx.closePath();
}

/** Scale bar of `metres` length at the bottom-left corner. */
export function scaleBar(ctx, view, h, metres = 5) {
  const len = metres * view.k;
  ctx.strokeStyle = COLORS.ink; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(10, h - 12); ctx.lineTo(10 + len, h - 12); ctx.stroke();
  ctx.fillStyle = COLORS.ink; ctx.font = "700 12px Inter, 'Segoe UI', Helvetica, Arial, sans-serif";
  ctx.fillText(`${metres} m`, 10, h - 17);
}

/** Dashed distance rings around (cx, cy) in canvas px, every `step` m (5 × step when rings would sit closer than
 *  minPx on screen), each labelled ("10 m") at the first place on the ring that fits inside the canvas: diagonals
 *  (upper right first), then left, up, right, down; skipped if none fits. Used by Home and Map. */
export function distanceRings(ctx, view, cx, cy, w, h, step = 10, minPx = 14) {
  if (step * view.k < minPx) step *= 5;
  const far = Math.max(Math.hypot(cx, cy), Math.hypot(w - cx, cy), Math.hypot(cx, h - cy), Math.hypot(w - cx, h - cy)) / view.k;
  ctx.save();
  ctx.font = "600 11px Inter, 'Segoe UI', Helvetica, Arial, sans-serif";
  for (let r = step; r <= far; r += step) {
    const px = r * view.k;
    ctx.beginPath(); ctx.arc(cx, cy, px, 0, 2 * Math.PI);
    ctx.strokeStyle = "rgba(95, 102, 112, 0.45)"; ctx.lineWidth = 1; ctx.setLineDash([4, 4]); ctx.stroke(); ctx.setLineDash([]);
    const t = `${r} m`, tw = ctx.measureText(t).width, d = Math.SQRT1_2;
    const spot = [[d, -d], [-d, -d], [d, d], [-d, d], [-1, 0], [0, -1], [1, 0], [0, 1]].map(([ux, uy]) => [
      cx + ux * px + (ux > 0.1 ? 3 : ux < -0.1 ? -3 - tw : -tw / 2), cy + uy * px + (uy > 0.1 ? 13 : uy < -0.1 ? -3 : 4)])
      .find(([x, y]) => x >= 4 && x + tw <= w - 4 && y >= 14 && y <= h - 30);
    if (!spot) continue;
    const [lx, ly] = spot;
    ctx.lineWidth = 3; ctx.strokeStyle = "#fff"; ctx.lineJoin = "round"; ctx.strokeText(t, lx, ly);
    ctx.fillStyle = COLORS.mute; ctx.fillText(t, lx, ly);
  }
  ctx.restore();
}

/** Coalesce redraw requests: run fn at most every `minMs` (default ~30 fps). Uses a timer, not
 *  requestAnimationFrame, so panels also update in background tabs and embedded views. */
export function redrawer(fn, minMs = 33) {
  let timer = null, last = 0;
  return () => {
    if (timer) return;
    const wait = Math.max(0, last + minMs - performance.now());
    timer = setTimeout(() => {
      timer = null; last = performance.now();
      try { fn(); } catch (e) { console.error(e); }
    }, wait);
  };
}
