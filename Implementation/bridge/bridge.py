"""CAVS-1 websocket bridge: ROS 2 topics (replayed bag) -> JSON over a websocket for the browser dashboard.
Author: Zeenat Islam

  ws://<host>:8765/      websocket (JSON messages, see README.md)
  http://<host>:8765/    probe page for checking the stream

ROS spins in a background thread and stores the latest messages; an asyncio loop sends them to
each connected browser at the rates set in topics.py. Each client has its own camera choice and
camera rate (C-011, C-013).
"""
import asyncio, base64, io, json, os, threading, time
from collections import deque
from http import HTTPStatus

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
from sensor_msgs.msg import Image as ImageMsg
from PIL import Image
import websockets

from topics import TOPICS, CAMERAS, DEFAULT_CAMERA, CAMERA_HZ, CAMERA_WIDTH, stamp

PORT = int(os.environ.get("BRIDGE_PORT", 8765))
TICK = 0.05                                     # s between send passes per client
HERE = os.path.dirname(os.path.abspath(__file__))


# ----------------------------------------------------------------------------- encoders
def grid_fields(m):
    """OccupancyGrid -> recorded info + cell values as lossless 8-bit PNG (value 0..100, unknown -1 -> 255).
    Row 0 of the PNG is grid row 0 (origin corner); the browser flips it for display."""
    a = np.frombuffer(bytes(m.data), dtype=np.int8).reshape(m.info.height, m.info.width).view(np.uint8)
    buf = io.BytesIO(); Image.fromarray(a, mode="L").save(buf, format="PNG", optimize=True)
    return {"stamp": stamp(m.header.stamp), "frame_id": m.header.frame_id,
            "width": m.info.width, "height": m.info.height, "resolution": m.info.resolution,
            "origin_x": m.info.origin.position.x, "origin_y": m.info.origin.position.y,
            "png": base64.b64encode(buf.getvalue()).decode()}


def image_fields(m, width=CAMERA_WIDTH):
    """sensor_msgs/Image -> recorded header/size/encoding + downscaled JPEG for display."""
    raw = np.frombuffer(bytes(m.data), dtype=np.uint8)
    enc = m.encoding.lower()
    if enc in ("rgb8", "bgr8"):
        a = raw.reshape(m.height, m.step)[:, :m.width * 3].reshape(m.height, m.width, 3)
        if enc == "bgr8": a = a[:, :, ::-1]
        img = Image.fromarray(a, "RGB")
    elif enc in ("mono16", "16uc1"):
        a = raw.view("<u2").reshape(m.height, m.step // 2)[:, :m.width]
        img = Image.fromarray((a >> 8).astype(np.uint8), "L")
    else:                                       # mono8 and raw bayer patterns shown as grey
        img = Image.fromarray(raw.reshape(m.height, m.step)[:, :m.width], "L")
    img = img.resize((width, round(m.height * width / m.width)), Image.BILINEAR)
    buf = io.BytesIO(); img.save(buf, format="JPEG", quality=70)
    return {"stamp": stamp(m.header.stamp), "frame_id": m.header.frame_id, "width": m.width,
            "height": m.height, "encoding": m.encoding, "jpeg": base64.b64encode(buf.getvalue()).decode()}


# ----------------------------------------------------------------------------- shared store
class Store:
    """Latest message per topic (throttled/grid topics + cameras) and an event log ("all" topics)."""
    def __init__(self):
        self.lock = threading.Lock()
        self.seq = 0
        self.latest = {}          # topic -> [seq, msg, key_seq, cached_json]
        self.events = deque(maxlen=2000)   # (seq, json)
        self.counts = {}          # topic -> messages received from ROS
        self.wanted_cams = {DEFAULT_CAMERA}

    def put(self, topic, msg):
        spec = TOPICS.get(topic, {})
        if "skip" in spec and spec["skip"](msg):
            return
        with self.lock:
            self.seq += 1
            self.counts[topic] = self.counts.get(topic, 0) + 1
            if spec.get("mode") == "all":
                self.events.append((self.seq, encode(topic, spec["fields"](msg))))
                return
            prev = self.latest.get(topic)
            key_seq = prev[2] if prev else self.seq
            if "key" in spec and prev is not None and spec["key"](msg) != spec["key"](prev[1]):
                key_seq = self.seq
            self.latest[topic] = [self.seq, msg, key_seq, None]

    def json_for(self, topic):
        """Encode the latest message once and share it between clients."""
        with self.lock:
            e = self.latest.get(topic)
            if e is None: return None, 0, 0
            seq, msg, key_seq, cached = e
        if cached is None:
            spec = TOPICS.get(topic, {})
            if topic in CAMERAS: data = image_fields(msg)
            elif spec.get("mode") == "grid": data = grid_fields(msg)
            else: data = spec["fields"](msg)
            cached = encode(topic, data)
            with self.lock:
                if self.latest.get(topic, [None])[0] == seq: self.latest[topic][3] = cached
        return cached, seq, key_seq


def encode(topic, data):
    return json.dumps({"type": "msg", "topic": topic, "data": data}, separators=(",", ":"))


STORE = Store()


# ----------------------------------------------------------------------------- ROS side
class BridgeNode(Node):
    def __init__(self):
        super().__init__("cavs_ws_bridge")
        qos = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=50,
                         reliability=ReliabilityPolicy.RELIABLE, durability=DurabilityPolicy.VOLATILE)
        for topic, spec in TOPICS.items():
            self.create_subscription(spec["type"], topic, lambda m, t=topic: STORE.put(t, m), qos)
        self.cam_subs = {}
        self.create_timer(0.2, self.update_cameras)

    def update_cameras(self):
        """Subscribe only to the cameras someone is viewing (each raw frame is 3.1 MB)."""
        with STORE.lock: wanted = set(STORE.wanted_cams)
        img_qos = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=1,
                             reliability=ReliabilityPolicy.RELIABLE, durability=DurabilityPolicy.VOLATILE)
        for c in wanted - set(self.cam_subs):
            t = CAMERAS[c]
            self.cam_subs[c] = self.create_subscription(ImageMsg, t, lambda m, t=t: STORE.put(t, m), img_qos)
            self.get_logger().info(f"subscribed {t}")
        for c in set(self.cam_subs) - wanted:
            self.destroy_subscription(self.cam_subs.pop(c))
            self.get_logger().info(f"unsubscribed {CAMERAS[c]}")


def ros_thread():
    rclpy.init()
    node = BridgeNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node(); rclpy.try_shutdown()


# ----------------------------------------------------------------------------- websocket side
CLIENTS = {}   # websocket -> Client


class Client:
    def __init__(self):
        self.camera = DEFAULT_CAMERA
        self.camera_hz = CAMERA_HZ["default"]
        self.sent_seq, self.sent_t = {}, {}
        with STORE.lock:
            self.ev_seq = STORE.events[-1][0] if STORE.events else 0


def update_wanted_cams():
    with STORE.lock:
        STORE.wanted_cams = {c.camera for c in CLIENTS.values()} or {DEFAULT_CAMERA}


async def sender(ws, cl: Client):
    loop = asyncio.get_running_loop()
    while True:
        now = time.monotonic()
        out = []
        with STORE.lock:
            evs = [e for e in STORE.events if e[0] > cl.ev_seq]
        if evs:
            cl.ev_seq = evs[-1][0]; out += [j for _, j in evs]
        topics = [t for t, s in TOPICS.items() if s["mode"] != "all"] + [CAMERAS[cl.camera]]
        for t in topics:
            with STORE.lock:
                e = STORE.latest.get(t)
            if e is None or e[0] <= cl.sent_seq.get(t, 0): continue
            hz = cl.camera_hz if t in CAMERAS else TOPICS[t].get("hz")
            due = hz is None or now - cl.sent_t.get(t, 0) >= 1.0 / hz or e[2] > cl.sent_seq.get(t, 0)
            if not due: continue
            if t in CAMERAS or TOPICS[t]["mode"] == "grid":       # image encoding off the event loop
                j, seq, _ = await loop.run_in_executor(None, STORE.json_for, t)
            else:
                j, seq, _ = STORE.json_for(t)
            if j is None: continue
            cl.sent_seq[t], cl.sent_t[t] = seq, now
            out.append(j)
        for j in out:
            await ws.send(j)
        await asyncio.sleep(TICK)


async def receiver(ws, cl: Client):
    async for raw in ws:
        try:
            m = json.loads(raw)
        except ValueError:
            continue
        if m.get("cmd") == "camera" and m.get("id") in (0, 1, 2):
            cl.camera = m["id"]; update_wanted_cams()
        elif m.get("cmd") == "camera_rate":
            cl.camera_hz = min(CAMERA_HZ["max"], max(CAMERA_HZ["min"], float(m.get("hz", CAMERA_HZ["default"]))))
        await ws.send(json.dumps({"type": "settings", "camera": cl.camera, "camera_hz": cl.camera_hz}))


async def handler(ws, path=None):
    cl = Client(); CLIENTS[ws] = cl; update_wanted_cams()
    await ws.send(json.dumps({"type": "hello", "topics": {t: {"mode": s["mode"], "hz": s.get("hz")} for t, s in TOPICS.items()},
                              "cameras": CAMERAS, "camera": cl.camera, "camera_hz": cl.camera_hz, "camera_hz_range": CAMERA_HZ}))
    tasks = [asyncio.create_task(sender(ws, cl)), asyncio.create_task(receiver(ws, cl))]
    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for t in tasks: t.cancel()
        CLIENTS.pop(ws, None); update_wanted_cams()


def process_request(path, headers):
    """Plain HTTP GET (no websocket upgrade) -> probe page or ROS receive counts."""
    if headers.get("Upgrade", "").lower() == "websocket":
        return None
    if path.startswith("/stats"):
        with STORE.lock: body = json.dumps({"received": STORE.counts, "clients": len(CLIENTS)}, indent=1).encode()
        return HTTPStatus.OK, [("Content-Type", "application/json")], body
    body = open(os.path.join(HERE, "probe.html"), "rb").read()
    return HTTPStatus.OK, [("Content-Type", "text/html; charset=utf-8")], body


async def main():
    threading.Thread(target=ros_thread, daemon=True).start()
    async with websockets.serve(handler, "0.0.0.0", PORT, process_request=process_request,
                                max_size=2 ** 20, compression=None):
        print(f"bridge listening on :{PORT} (websockets {websockets.__version__})", flush=True)
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
