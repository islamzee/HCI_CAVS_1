"""Rate and longest gap of each sensor stream, from message log times only.
Author: Zeenat Islam
"""
import numpy as np
from bag_reader import Bag

TOPICS = ["/cam_0/image_raw", "/cam_1/image_raw", "/cam_2/image_raw", "/ouster/points", "/ouster/reflec_image",
          "/ouster/imu", "/mtx/odom", "/dlio/odom_node/odom", "/local_costmap/costmap", "/mtx/arbiter_status"]
GAP_FACTOR = 3          # a gap is an interval longer than 3 x the mean interval

bag = Bag()
for tp in TOPICS:
    L = np.array(bag.times(tp)); d = np.diff(L)
    gaps = [(round(L[j], 1), round(d[j] * 1000)) for j in np.where(d > GAP_FACTOR * d.mean())[0]]
    print(f"{tp:28s} {len(L)/(L[-1]-L[0]):7.2f} Hz  longest gap {d.max()*1000:6.1f} ms  gaps>{GAP_FACTOR}x mean (t s, ms): {gaps[:10]}")
