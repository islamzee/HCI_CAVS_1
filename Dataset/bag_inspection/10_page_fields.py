"""Recorded fields for the Sensors, Faults and Logs page sketches (no derived values).
Writes output/pages/fields.json and the LiDAR panorama image.
Author: Zeenat Islam
"""
import os, json, yaml
import numpy as np
from PIL import Image
from bag_reader import Bag, OUT_DIR, REPO

T_LIVE = 14.3                 # s into the run, Sensors page
D = os.path.join(OUT_DIR, "pages"); os.makedirs(D, exist_ok=True)
bag = Bag(); out = {}

def last(tp, t):
    L = bag.times(tp); k = max([i for i, x in enumerate(L) if x <= t], default=None)
    return None if k is None else bag.decode(tp, k)

# Sensors
cams = []
for c in range(3):
    t, m = last(f"/cam_{c}/meta", T_LIVE)
    ts, st = bag.header_stamp(f"/cam_{c}/image_raw", max(i for i, x in enumerate(bag.times(f"/cam_{c}/image_raw")) if x <= T_LIVE))
    _, img = last(f"/cam_{c}/image_raw", T_LIVE)
    cams.append(dict(frame=m.header.frame_id, exposure_us=m.exposure_time, gain=m.gain, brightness=m.brightness,
                     image_stamp=st, width=img.width, height=img.height, encoding=img.encoding))
out["cams"] = cams
t, m = last("/ouster/reflec_image", T_LIVE)
a = np.frombuffer(bytes(m.data), dtype="<u2").reshape(m.height, m.width).astype(float)
WINDOW = 65535                                                   # full 16-bit range shown as 8-bit (no per-image scaling)
b = (np.clip(a / WINDOW, 0, 1) * 255).astype(np.uint8)
Image.fromarray(b).save(os.path.join(D, "reflec.png"))
out["reflec"] = dict(t=t, w=m.width, h=m.height, encoding=m.encoding, stamp=m.header.stamp.sec + m.header.stamp.nanosec / 1e9)
_, m = last("/ouster/telemetry", T_LIVE)
out["telemetry"] = dict(thermal_shutdown=m.thermal_shutdown, shot_limiting=m.shot_limiting, countdown_thermal_shutdown=m.countdown_thermal_shutdown, countdown_shot_limiting=m.countdown_shot_limiting)
_, m = last("/mtx/velocity_filter/status", T_LIVE); out["lidar_age_s"] = m.lidar_age_s

# Faults: recorded events
ev = []
for k in range(bag.count("/rosout")):
    t, m = bag.decode("/rosout", k)
    if m.level >= 30 and m.name not in ("cam_0", "cam_1", "cam_2"):
        ev.append(dict(t=t, src="/rosout", level=m.level, node=m.name, msg=m.msg))
prev = None
for k in range(bag.count("/mtx/velocity_filter/status")):
    t, m = bag.decode("/mtx/velocity_filter/status", k); cur = (m.ok, tuple(m.inhibit_reasons))
    if cur != prev and not m.ok:
        ev.append(dict(t=t, src="/mtx/velocity_filter/status", level=30, node="velocity_filter", msg="ok=false inhibit_reasons=" + ",".join(m.inhibit_reasons)))
    prev = cur
for k in range(bag.count("/mtx/estop")):
    t, m = bag.decode("/mtx/estop", k); ev.append(dict(t=t, src="/mtx/estop", level=40 if m.data else 20, node="estop", msg=f"data={str(m.data).lower()}"))
for k in range(bag.count("/mtx/nav/collision_monitor_state")):
    t, m = bag.decode("/mtx/nav/collision_monitor_state", k)
    ev.append(dict(t=t, src="/mtx/nav/collision_monitor_state", level=30 if m.action_type else 20, node="collision_monitor", msg=f"action_type={m.action_type} polygon={m.polygon_name or '(none)'}"))
out["events"] = sorted(ev, key=lambda e: e["t"])

# Logs
meta = yaml.safe_load(open(os.path.join(REPO, "Dataset", "autonomy_demo", "metadata.yaml")))["rosbag2_bagfile_information"]
out["bag"] = dict(name="autonomy_demo_0", start_ns=meta["starting_time"]["nanoseconds_since_epoch"], duration_ns=meta["duration"]["nanoseconds"],
                  messages=meta["message_count"], ros_distro=meta.get("ros_distro"), storage=meta["storage_identifier"])
out["rosout"] = []
for k in range(bag.count("/rosout")):
    t, m = bag.decode("/rosout", k); out["rosout"].append(dict(t=t, level=m.level, node=m.name, msg=m.msg))
json.dump(out, open(os.path.join(D, "fields.json"), "w"), indent=1)
print(json.dumps({k: v for k, v in out.items() if k not in ("events", "rosout")}, indent=1))
print(len(out["events"]), "events;", len(out["rosout"]), "rosout lines")
for e in out["events"]: print(round(e["t"], 1), e["level"], e["node"], e["msg"][:70])
