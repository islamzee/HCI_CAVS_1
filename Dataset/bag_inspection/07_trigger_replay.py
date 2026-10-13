"""Replay the proposed stop/alert triggers (T1-T7) over the recorded run and report first firing times.
Author: Zeenat Islam
"""
import numpy as np
from bag_reader import Bag

AUTONOMY = (8.2, 64.7)          # s, from /rosout and /mtx/estop
T1_GAP_S = 0.158                # 3 frame periods at 19 Hz
T2_MIN_FRAMES_PER_S = 15
T3_FEED_LOST_S = 0.5
T4_ODOM_STALE_S = 0.2
bag = Bag(); fired = {}

for cam in (0, 1, 2):
    L = np.array(bag.times(f"/cam_{cam}/image_raw")); d = np.diff(L)
    for j in np.where(d > T1_GAP_S)[0]:
        fired.setdefault("T1", []).append((round(L[j] + T1_GAP_S, 2), f"cam {cam} gap {d[j]*1000:.0f} ms"))
    for j in np.where(d > T3_FEED_LOST_S)[0]:
        fired.setdefault("T3", []).append((round(L[j] + T3_FEED_LOST_S, 2), f"cam {cam}"))
    for s in np.arange(AUTONOMY[0], AUTONOMY[1], 0.1):
        n = ((L >= s) & (L < s + 1)).sum()
        if n < T2_MIN_FRAMES_PER_S:
            fired.setdefault("T2", []).append((round(s + 1, 1), f"cam {cam} {n} frames/s")); break
L = np.array(bag.times("/mtx/odom")); d = np.diff(L)
for j in np.where(d > T4_ODOM_STALE_S)[0]:
    fired.setdefault("T4", []).append((round(L[j + 1], 1), f"odom gap {d[j]*1000:.0f} ms"))
for k in range(bag.count("/mtx/arbiter_status")):
    t, m = bag.decode("/mtx/arbiter_status", k)
    if AUTONOMY[0] + 0.1 < t < AUTONOMY[1] and not m.autonomy_cmd_fresh:
        fired.setdefault("T5", []).append((round(t, 1), "autonomy_cmd_fresh false")); break
for k in range(bag.count("/rosout")):
    t, m = bag.decode("/rosout", k)
    if "patience exceeded" in m.msg:
        fired.setdefault("T6", []).append((round(t, 1), m.msg))
for k in range(bag.count("/mtx/nav/collision_monitor_state")):
    t, m = bag.decode("/mtx/nav/collision_monitor_state", k)
    if m.action_type != 0:
        fired.setdefault("T7", []).append((round(t, 1), m.polygon_name))
for tid in ("T1", "T2", "T3", "T4", "T5", "T6", "T7"):
    print(tid, fired.get(tid, "never"))
