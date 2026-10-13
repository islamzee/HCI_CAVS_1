"""Render the LiDAR-derived 2D views and measure their size and encode time.
Writes PNGs and info.json to output/lidar_preview/.
Author: Zeenat Islam
"""
import os, io, json, time
import numpy as np
from PIL import Image
from bag_reader import Bag, OUT_DIR

GRID_TIMES = (12.0, 17.9, 40.0, 64.7)    # s into the run
PANO_TIME = 17.9
SCALE = 2                                # nearest-neighbour upscale for viewing
DEST = os.path.join(OUT_DIR, "lidar_preview"); os.makedirs(DEST, exist_ok=True)
bag = Bag(); info = {}

def grid(topic, t, name):
    k = bag.nearest(topic, t); tt, m = bag.decode(topic, k)
    a = np.array(m.data, dtype=np.int16).reshape(m.info.height, m.info.width)
    rgb = np.zeros(a.shape + (3,), np.uint8); rgb[:] = (251, 248, 244)
    rgb[a < 0] = (233, 226, 218)
    c = (a > 0) & (a < 99); v = a[c] / 99.0
    rgb[c] = np.stack([251 - 40 * v, 248 - 93 * v, 244 - 194 * v], -1).astype(np.uint8)
    rgb[a >= 99] = (47, 42, 38)
    im = Image.fromarray(rgb[::-1]); im.resize((im.width * SCALE, im.height * SCALE), Image.NEAREST).save(os.path.join(DEST, name + ".png"))
    buf = io.BytesIO(); Image.fromarray(np.where(a < 0, 255, a).astype(np.uint8)).save(buf, "PNG", optimize=True)
    info[name] = dict(t=round(tt, 2), w=m.info.width, h=m.info.height, res=m.info.resolution, ox=m.info.origin.position.x,
                      oy=m.info.origin.position.y, msg_bytes=len(m.data), png_bytes=len(buf.getvalue()), occ=int((a >= 99).sum()))

for t in GRID_TIMES:
    grid("/local_costmap/costmap", t, f"local_{int(t)}")
grid("/global_costmap/costmap", GRID_TIMES[-1], f"global_{int(GRID_TIMES[-1])}")

for nm in ("reflec", "range", "signal"):
    tp = f"/ouster/{nm}_image"; tt, m = bag.decode(tp, bag.nearest(tp, PANO_TIME))
    a = np.frombuffer(bytes(m.data), dtype="<u2").reshape(m.height, m.width).astype(float)
    lo, hi = np.percentile(a[a > 0], [2, 98]) if (a > 0).any() else (0, 1)
    b = (np.clip((a - lo) / (hi - lo + 1e-9), 0, 1) * 255).astype(np.uint8)
    Image.fromarray(b).save(os.path.join(DEST, f"ouster_{nm}.png"))
    buf = io.BytesIO(); Image.fromarray(b).save(buf, "JPEG", quality=70)
    info["ouster_" + nm] = dict(t=round(tt, 2), w=m.width, h=m.height, jpg_bytes=len(buf.getvalue()))

# encode cost
_, m = bag.decode("/local_costmap/costmap", 60); a = np.array(m.data, dtype=np.int16).reshape(m.info.height, m.info.width)
t0 = time.perf_counter()
for _ in range(200):
    buf = io.BytesIO(); Image.fromarray(np.where(a < 0, 255, a).astype(np.uint8)).save(buf, "PNG")
info["grid_png_encode_ms"] = (time.perf_counter() - t0) / 200 * 1000
_, m = bag.decode("/ouster/reflec_image", 300); r = np.frombuffer(bytes(m.data), dtype="<u2").reshape(m.height, m.width)
t0 = time.perf_counter()
for _ in range(100):
    x = np.clip(r / (np.percentile(r, 98) + 1) * 255, 0, 255).astype(np.uint8); buf = io.BytesIO(); Image.fromarray(x).save(buf, "JPEG", quality=70)
info["pano_jpeg_encode_ms"] = (time.perf_counter() - t0) / 100 * 1000
for tp in ("/local_costmap/costmap", "/ouster/reflec_image", "/ouster/points"):
    L = np.array(bag.times(tp)); info[tp] = dict(rate_hz=len(L) / (L[-1] - L[0]), max_gap_s=float(np.diff(L).max()), bytes=bag.size(tp, 10))
json.dump(info, open(os.path.join(DEST, "info.json"), "w"), indent=1)
print(json.dumps(info, indent=1))
