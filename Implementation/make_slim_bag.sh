#!/bin/bash
# Make a small copy of a bag for the team: dashboard topics only (bridge/topics.py + /ouster/imu,
# /dlio/odom_node/odom for the topic-rate table), zstd-compressed MCAP chunks.
# Message contents and counts are unchanged.
# Usage (macOS/Linux, or Windows inside WSL/Git Bash): ./make_slim_bag.sh ../Dataset/autonomy_demo ../Dataset/autonomy_demo_slim
set -euo pipefail
IN="$(cd "$1" && pwd)"; OUT_PARENT="$(cd "$(dirname "$2")" && pwd)"; OUT_NAME="$(basename "$2")"
IMAGE="${IMAGE:-ghcr.io/islamzee/hci_cavs_1/cavs-bag-bridge:latest}"
[ -e "$OUT_PARENT/$OUT_NAME" ] && { echo "$OUT_PARENT/$OUT_NAME exists"; exit 1; }
podman run --rm -v "$IN:/in:ro" -v "$OUT_PARENT:/out" "$IMAGE" bash -c "
{ echo 'output_bags:'
  echo '  - uri: /out/$OUT_NAME'
  echo '    storage_id: mcap'
  echo '    storage_preset_profile: zstd_small'
  echo '    topics:'
  for t in \$(python3 /bridge/topics.py) /ouster/imu /dlio/odom_node/odom; do echo \"      - \$t\"; done
} > /tmp/convert.yaml
ros2 bag convert -i /in -o /tmp/convert.yaml"
du -sh "$OUT_PARENT/$OUT_NAME"
