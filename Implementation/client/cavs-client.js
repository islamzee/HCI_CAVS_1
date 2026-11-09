// CAVS-1 browser client for the bag bridge (ws://localhost:8765/). No dependencies.
// Author: Zeenat Islam
//
//   import { CavsClient, decodeGrid, cameraSrc } from "./cavs-client.js";
//   const cavs = new CavsClient();                 // one shared instance per page/app
//   cavs.on("/mtx/odom", (d) => console.log(d.x, d.y, d.linear_x));
//   cavs.onStatus((s) => console.log(s));          // "connecting" | "open" | "closed"
//   cavs.onRestart(() => clearMyLog());            // bag started again from 00:00
//   cavs.setCamera(0); cavs.setCameraRate(5);
//
// Field names are listed in Implementation/Frontend_Data_Guide_v1.md.

export class CavsClient {
  constructor(url = "ws://localhost:8765/", { reconnectMs = 2000 } = {}) {
    this.url = url;
    this.reconnectMs = reconnectMs;
    this.handlers = new Map();      // topic or "*" -> Set of callbacks
    this.statusHandlers = new Set();
    this.restartHandlers = new Set();
    this.settingsHandlers = new Set();
    this.last = new Map();          // topic -> latest data
    this.settings = null;           // { camera, camera_hz, ... } from the bridge
    this.historyDone = false;       // true once the connect-time history has arrived
    this.status = "connecting";
    this._closedByUser = false;
    this._connect();
  }

  /** Call fn(data, topic) for every message on `topic` ("*" = all topics). Returns an unsubscribe function. */
  on(topic, fn) {
    if (!this.handlers.has(topic)) this.handlers.set(topic, new Set());
    this.handlers.get(topic).add(fn);
    if (topic !== "*" && this.last.has(topic)) fn(this.last.get(topic), topic);   // deliver current value at once
    return () => this.handlers.get(topic).delete(fn);
  }
  onStatus(fn) { this.statusHandlers.add(fn); fn(this.status); return () => this.statusHandlers.delete(fn); }
  onRestart(fn) { this.restartHandlers.add(fn); return () => this.restartHandlers.delete(fn); }
  onSettings(fn) { this.settingsHandlers.add(fn); if (this.settings) fn(this.settings); return () => this.settingsHandlers.delete(fn); }

  /** Latest data received on a topic, or undefined. */
  latest(topic) { return this.last.get(topic); }

  /** Camera shown to this browser: 0, 1 or 2 (default 2). */
  setCamera(id) { this._send({ cmd: "camera", id }); }
  /** Camera frames per second for this browser (0.2 to 10, default 2). */
  setCameraRate(hz) { this._send({ cmd: "camera_rate", hz }); }

  close() { this._closedByUser = true; if (this.ws) this.ws.close(); }

  // ------------------------------------------------------------------ internals
  _connect() {
    this._setStatus("connecting");
    this.historyDone = false;
    const ws = new WebSocket(this.url);
    this.ws = ws;
    ws.onopen = () => this._setStatus("open");
    ws.onclose = () => {
      this._setStatus("closed");
      if (!this._closedByUser) setTimeout(() => this._connect(), this.reconnectMs);
    };
    ws.onerror = () => ws.close();
    ws.onmessage = (ev) => this._handle(JSON.parse(ev.data));
  }

  _handle(m) {
    if (m.type === "msg") {
      this.last.set(m.topic, m.data);
      for (const key of [m.topic, "*"]) {
        const hs = this.handlers.get(key);
        if (hs) for (const fn of hs) fn(m.data, m.topic);
      }
    } else if (m.type === "hello" || m.type === "settings") {
      this.settings = { ...(this.settings || {}), ...m };
      for (const fn of this.settingsHandlers) fn(this.settings);
    } else if (m.type === "history_end") {
      this.historyDone = true;
    } else if (m.type === "playback" && m.event === "restart") {
      this.last.clear();
      for (const fn of this.restartHandlers) fn();
    }
  }

  _send(obj) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) this.ws.send(JSON.stringify(obj));
  }

  _setStatus(s) {
    this.status = s;
    for (const fn of this.statusHandlers) fn(s);
  }
}

/** `src` for an <img> from a camera message (/cam_N/image_raw). */
export function cameraSrc(d) {
  return "data:image/jpeg;base64," + d.jpeg;
}

/**
 * Decode an occupancy grid message (/local_costmap/costmap, /local_costmap/voxel_layer, /global_costmap/costmap).
 * Resolves to { width, height, resolution, origin_x, origin_y, frame_id, stamp, values }
 * where values[row * width + col] is the recorded cell value: 0..100, or -1 for unknown.
 * Row 0 is the row at origin_y (the bottom of the map when y points up).
 */
export async function decodeGrid(d) {
  const bytes = Uint8Array.from(atob(d.png), (c) => c.charCodeAt(0));
  const bmp = await createImageBitmap(new Blob([bytes], { type: "image/png" }),
                                      { colorSpaceConversion: "none", premultiplyAlpha: "none" });
  const canvas = new OffscreenCanvas(d.width, d.height);
  const ctx = canvas.getContext("2d");
  ctx.drawImage(bmp, 0, 0);
  const px = ctx.getImageData(0, 0, d.width, d.height).data;   // RGBA, grey value in R
  const values = new Int8Array(d.width * d.height);
  for (let i = 0; i < values.length; i++) {
    const v = px[i * 4];
    values[i] = v === 255 ? -1 : v;
  }
  const { png, ...info } = d;
  return { ...info, values };
}

/** Heading (yaw, radians) from the recorded quaternion of /mtx/odom (qz, qw), for rotating a vehicle icon. */
export function yawFromQuaternion(qz, qw) {
  return 2 * Math.atan2(qz, qw);
}
