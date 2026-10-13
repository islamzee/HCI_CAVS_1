"""Build the message index from the .mcap and cross-check counts against metadata.yaml.
Author: Zeenat Islam
"""
import os, time, yaml
from bag_reader import Bag, REPO

t = time.time(); bag = Bag(); print(f"index ready in {time.time()-t:.1f} s")
meta = yaml.safe_load(open(os.path.join(REPO, "Dataset", "autonomy_demo", "metadata.yaml")))["rosbag2_bagfile_information"]
expected = {t["topic_metadata"]["name"]: t["message_count"] for t in meta["topics_with_message_count"]}
total = 0; mismatch = 0
for name, n_meta in sorted(expected.items()):
    n = bag.count(name) if name in bag.topic else 0
    total += n
    if n != n_meta:
        mismatch += 1; print("MISMATCH", name, "mcap", n, "yaml", n_meta)
print("messages in mcap:", total, "| yaml:", meta["message_count"], "| mismatched topics:", mismatch)
print("chunks:", len(bag.chunks), "| compression:", {c[2] for c in bag.chunks})
