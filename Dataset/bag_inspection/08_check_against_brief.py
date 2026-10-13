"""Check the bag against the course brief: GPS, TF frames, waypoints, local path, map, system status, LiDAR dropout.
Author: Zeenat Islam
"""
import collections
import numpy as np
from bag_reader import Bag

bag = Bag()
print("GPS-like topics:", [t for t in bag.topic if any(k in t.lower() for k in ("gps", "fix", "navsat", "gnss"))])
print("NavSatFix topics:", [bag.channels[c].topic for c in bag.channels if "NavSatFix" in bag.summary.schemas[bag.channels[c].schema_id].name])

frames = collections.Counter()
for k in range(bag.count("/tf_static")):
    _, m = bag.decode("/tf_static", k)
    for tr in m.transforms: frames[("static", tr.header.frame_id, tr.child_frame_id)] += 1
for k in range(0, bag.count("/tf"), 20):
    _, m = bag.decode("/tf", k)
    for tr in m.transforms: frames[("dynamic", tr.header.frame_id, tr.child_frame_id)] += 1
print("TF edges:", sorted(frames))

for tp in ["/plan", "/received_global_plan", "/mtx/odom", "/ouster/points", "/map", "/global_costmap/costmap", "/dlio/odom_node/path"]:
    _, m = bag.decode(tp, 0); print(f"{tp:28s} frame {m.header.frame_id}")
print("waypoint / goal topics:", {t: bag.count(t) for t in ("/goal_pose", "/initialpose", "/clicked_point") if t in bag.topic})
print("local path topics:", [t for t in bag.topic if "local_plan" in t])
for k in (0, 300, 600, 900, 1100):
    t, m = bag.decode("/received_global_plan", k); p = m.poses
    print(f"received_global_plan {t:5.1f}s {len(p)} poses, frame {m.header.frame_id}")
_, m = bag.decode("/map", bag.count("/map") - 1)
print("/map is", type(m).__name__, m.width * m.height, "points, fields", [f.name for f in m.fields])

names = set()
for k in range(bag.count("/diagnostics")):
    _, m = bag.decode("/diagnostics", k); names |= {s.name for s in m.status}
print("diagnostics sources:", names)
ids = collections.Counter()
for k in range(0, bag.count("/bond"), 5):
    _, m = bag.decode("/bond", k); ids[m.id] += 1
print("bond heartbeats from:", dict(ids))

for tp in ("/ouster/points", "/ouster/reflec_image"):
    L = np.array(bag.times(tp)); print(f"{tp} longest gap {np.diff(L).max()*1000:.0f} ms, mean {np.diff(L).mean()*1000:.1f} ms")
    arr = np.array([bag.header_stamp(tp, k) for k in range(bag.count(tp))])
    print(f"   stamp longest gap {np.diff(np.sort(arr[:,1])).max()*1000:.0f} ms")
