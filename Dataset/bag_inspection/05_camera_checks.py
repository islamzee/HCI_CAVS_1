"""Camera checks: image size, pixel content, calibration, frame intervals, delivery delay.
Author: Zeenat Islam
"""
import numpy as np
from bag_reader import Bag

SAMPLE_EVERY = 90       # frames between pixel samples
BIN_S = 0.5             # bin for longest-interval series (used for the Camera 2 chart)
bag = Bag()

for cam in (0, 1, 2):
    img = f"/cam_{cam}/image_raw"
    t, m = bag.decode(img, 0)
    npx = m.height * m.step
    print(f"\nCamera {cam}: {m.width} x {m.height} {m.encoding}, {bag.size(img, 0)/1e6:.2f} MB per frame")
    stats = []
    for k in range(0, bag.count(img), SAMPLE_EVERY):
        _, b = bag.raw(img, k)
        a = np.frombuffer(b[-npx:], dtype=np.uint8); stats.append((a.min(), a.mean()))
    print(f"  {len(stats)} frames sampled: min pixel {min(s[0] for s in stats)}-{max(s[0] for s in stats)}, mean {min(s[1] for s in stats):.1f}-{max(s[1] for s in stats):.1f}")
    _, ci = bag.decode(f"/cam_{cam}/camera_info", 5)
    print(f"  camera_info: {ci.width} x {ci.height}, distortion '{ci.distortion_model}', fx {ci.k[0]}")
    _, me = bag.decode(f"/cam_{cam}/meta", 500)
    print(f"  meta: brightness {me.brightness}, exposure {me.exposure_time} us, gain {me.gain}")

    # intervals from log time and from the camera's own stamps
    arr = np.array([bag.header_stamp(img, k) for k in range(bag.count(img))]); arr = arr[np.argsort(arr[:, 0])]
    d_log, d_stamp = np.diff(arr[:, 0]), np.diff(arr[:, 1])
    print(f"  longest interval: log {d_log.max()*1000:.0f} ms, camera stamp {d_stamp.max()*1000:.0f} ms (stamps are epoch time: {arr[0,1] > 1e9})")
    win = [((arr[:, 0] >= s) & (arr[:, 0] < s + 1)).sum() for s in np.arange(8.2, 64.7, 0.1)]
    print(f"  lowest frame count in any 1 s window during autonomy: {min(win)}")
    lag = (arr[:, 0] - arr[:, 1]); ex = (lag - np.percentile(lag, 5)) * 1000
    print("  delivery delay vs. start, median per 5 s (ms):", [int(np.median(ex[(arr[:, 0] >= b) & (arr[:, 0] < b + 5)])) for b in range(0, 72, 5)])
    bins = {}
    for j in range(1, len(arr)):
        kk = int(arr[j, 0] / BIN_S); bins[kk] = max(bins.get(kk, 0), round(d_log[j - 1] * 1000))
    print(f"  longest interval per {BIN_S} s (ms):", [bins.get(k, 0) for k in range(int(72.2 / BIN_S))])
