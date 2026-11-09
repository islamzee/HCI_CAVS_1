#!/bin/bash
# CAVS-1: replay the ROS bag in a Podman pod and stream it to the browser.
# Usage: ./pod.sh build | up | down | restart | logs [player|bridge] | status | topics
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
BAG_DIR="${BAG_DIR:-$HERE/../Dataset/autonomy_demo}"   # folder with metadata.yaml + .mcap
PORT="${PORT:-8765}"
RATE="${RATE:-1.0}"                                     # playback speed
IMAGE=cavs-bag-bridge
POD=cavs

case "${1:-}" in
  build)
    podman build -t "$IMAGE" -f "$HERE/Containerfile" "$HERE" ;;
  up)
    BAG_DIR="$(cd "$BAG_DIR" && pwd)"
    podman pod create --name "$POD" -p "$PORT:8765"
    # bridge first, so it is subscribed before the player starts publishing
    podman run -d --pod "$POD" --name cavs-bridge "$IMAGE" python3 /bridge/bridge.py
    podman run -d --pod "$POD" --name cavs-player -v "$BAG_DIR:/bag:ro" "$IMAGE" \
      bash -c "sleep 3; exec ros2 bag play /bag --loop --rate $RATE --topics \$(python3 /bridge/topics.py)"
    echo "Probe page: http://localhost:$PORT/   websocket: ws://localhost:$PORT/   receive counts: http://localhost:$PORT/stats" ;;
  down)
    podman pod rm -f "$POD" ;;
  restart)
    "$0" down || true; "$0" up ;;
  logs)
    podman logs -f "cavs-${2:-bridge}" ;;
  status)
    podman pod ps; podman ps --pod --filter pod="$POD" ;;
  topics)   # check from inside the pod with the ROS CLI
    podman exec cavs-bridge bash -c "source /ws/install/setup.bash; ros2 topic list; echo; ros2 topic hz /mtx/odom --window 50 & sleep 4; kill %1" ;;
  *)
    sed -n '2,3p' "$0"; exit 1 ;;
esac
