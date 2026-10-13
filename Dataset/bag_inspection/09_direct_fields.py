"""Extract only directly recorded fields (no derived values) at chosen playback times, for the dashboard sketch.
Writes output/direct/state.json and costmap PNGs.
Author: Zeenat Islam
"""
import os, json
import numpy as np
from PIL import Image
from bag_reader import Bag, OUT_DIR

TIMES = (14.3, 64.9)          # s into the run: autonomy running; recorded operator STOP / e-stop
D = os.path.join(OUT_DIR, "direct"); os.makedirs(D, exist_ok=True)
bag = Bag(); out = {}

def last(tp, t):
    """Latest message on a topic at or before t (what a live display would be showing)."""
    L = bag.times(tp); k = max([i for i, x in enumerate(L) if x <= t], default=None)
    return None if k is None else bag.decode(tp, k)

def grid_png(tp, t, name):
    tt, m = last(tp, t); a = np.array(m.data, dtype=np.int16).reshape(m.info.height, m.info.width)
    rgb = np.zeros(a.shape + (3,), np.uint8); rgb[:] = (250, 250, 248); rgb[a < 0] = (236, 236, 232)
    c = (a > 0) & (a < 99); v = a[c] / 99.0
    rgb[c] = np.stack([250 - 20 * v, 250 - 100 * v, 248 - 140 * v], -1).astype(np.uint8); rgb[a >= 99] = (200, 70, 60)
    Image.fromarray(rgb[::-1]).save(os.path.join(D, name + ".png"))
    return dict(t=tt, w=m.info.width, h=m.info.height, res=m.info.resolution, ox=m.info.origin.position.x, oy=m.info.origin.position.y)

for T in TIMES:
    o = {"t": T}
    _, m = last("/mtx/arbiter_status", T); o["arbiter"] = dict(mode=m.mode, autonomy_requested=m.autonomy_requested, autonomy_active=m.autonomy_active, estop=m.estop, joy_fresh=m.joy_fresh, autonomy_cmd_fresh=m.autonomy_cmd_fresh, active_source=m.active_source, inhibit_reasons=list(m.inhibit_reasons))
    _, m = last("/mtx/velocity_filter/status", T); o["safety"] = dict(ok=m.ok, inhibit_reasons=list(m.inhibit_reasons), cmd_age_s=m.cmd_age_s, odom_age_s=m.odom_age_s, tf_age_s=m.tf_age_s, lidar_age_s=m.lidar_age_s)
    r = last("/mtx/estop", T); o["estop"] = None if r is None else r[1].data
    _, m = last("/mtx/odom", T); o["odom_twist"] = dict(linear_x=m.twist.twist.linear.x, angular_z=m.twist.twist.angular.z)
    _, m = last("/mtx/cmd_vel_autonomy", T); o["cmd_vel_autonomy"] = dict(linear_x=m.twist.linear.x, angular_z=m.twist.angular.z)
    _, m = last("/diagnostics", T); o["diagnostics"] = [dict(name=s.name, level=s.level, message=s.message) for s in m.status]
    r = last("/mtx/nav/collision_monitor_state", T); o["collision_monitor"] = None if r is None else dict(action_type=r[1].action_type, polygon=r[1].polygon_name, t=r[0])
    _, m = last("/plan", T); o["plan"] = [[p.pose.position.x, p.pose.position.y] for p in m.poses]
    _, m = last("/dlio/odom_node/path", T); o["dlio_path"] = [[p.pose.position.x, p.pose.position.y] for p in m.poses]
    _, m = last("/local_costmap/published_footprint", T); o["footprint"] = [[p.x, p.y] for p in m.polygon.points]
    o["local"] = grid_png("/local_costmap/costmap", T, f"local_{T}")
    o["voxel"] = grid_png("/local_costmap/voxel_layer", T, f"voxel_{T}")
    o["global"] = grid_png("/global_costmap/costmap", T, f"global_{T}")
    logs = []
    for k in range(bag.count("/rosout")):
        tt, m = bag.decode("/rosout", k)
        if tt <= T and m.level >= 30 and m.name not in ("cam_0", "cam_1", "cam_2"):
            logs.append([tt, m.level, m.name, m.msg])
    o["rosout"] = logs[-8:]
    out[str(T)] = o
    print(T, {k: v for k, v in o.items() if k not in ("plan", "dlio_path", "rosout", "footprint")})
    for l in o["rosout"]: print("   ", [round(l[0], 1), l[1], l[2], l[3][:80]])
json.dump(out, open(os.path.join(D, "state.json"), "w"))
