"""Route, speed, plan, operator actions and log events. Writes output/run.json (used by the sketch script as data.json).
Author: Zeenat Islam
"""
import os, json, collections
from bag_reader import Bag, OUT_DIR

ODOM_STEP = 25          # keep every 25th odometry message (~4 Hz)
bag = Bag(); out = {}

out["odom"] = []
for k in range(0, bag.count("/mtx/odom"), ODOM_STEP):
    t, m = bag.decode("/mtx/odom", k); p = m.pose.pose.position; v = m.twist.twist.linear
    out["odom"].append([round(t, 2), round(p.x, 2), round(p.y, 2), round((v.x**2 + v.y**2) ** .5, 2)])

n = bag.count("/plan")
t, m = bag.decode("/plan", n - 1)
out["plan"] = [[round(q.pose.position.x, 2), round(q.pose.position.y, 2)] for q in m.poses[::5]]
for k in range(n):
    t, m = bag.decode("/plan", k); e = m.poses[-1].pose.position
    print(f"plan {t:5.1f}s  {len(m.poses):4d} poses  goal ({e.x:.1f}, {e.y:.1f})  frame {m.header.frame_id}")

out["rosout"] = []
for k in range(bag.count("/rosout")):
    t, m = bag.decode("/rosout", k); out["rosout"].append([round(t, 1), m.level, m.name, m.msg])
print(collections.Counter((r[1], r[2]) for r in out["rosout"]))
for r in out["rosout"]:
    if r[1] >= 40 or r[2] in ("web_ui", "command_arbiter", "bt_navigator"):
        print(r)

for tp in ["/mtx/estop", "/mtx/nav/collision_monitor_state"]:
    for k in range(bag.count(tp)):
        t, m = bag.decode(tp, k); print(tp, round(t, 1), m)

json.dump(out, open(os.path.join(OUT_DIR, "run.json"), "w"))
print("wrote", os.path.join(OUT_DIR, "run.json"))
