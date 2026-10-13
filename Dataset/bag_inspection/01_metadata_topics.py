"""List topics, types and message counts from metadata.yaml, and the topics that recorded nothing.
Author: Zeenat Islam
"""
import os, yaml
from bag_reader import REPO

METADATA = os.path.join(REPO, "Dataset", "autonomy_demo", "metadata.yaml")

m = yaml.safe_load(open(METADATA))["rosbag2_bagfile_information"]
print("files:", m["relative_file_paths"], "| ros_distro:", m.get("ros_distro"))
print("duration s:", m["duration"]["nanoseconds"] / 1e9, "| messages:", m["message_count"])
rows = sorted((t["topic_metadata"]["name"], t["topic_metadata"]["type"], t["message_count"]) for t in m["topics_with_message_count"])
for name, typ, n in rows:
    print(f"{n:7d}  {name:55s} {typ}")
empty = [r for r in rows if r[2] == 0]
print(f"\n{len(rows)} topics, {len(empty)} with 0 messages:")
for name, typ, _ in empty:
    print("  ", name, typ)
