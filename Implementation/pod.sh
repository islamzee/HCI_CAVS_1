#!/bin/bash
# CAVS-1: replay the ROS bag in a Podman pod and stream it to the browser.
# Usage: ./pod.sh build | up | down | restart | logs [player|bridge] | status | topics
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# Bag folder (metadata.yaml + .mcap). Default: the new bag if it is downloaded, else the slim bag in the repo.
# bag_files.txt in a bag folder lists each .mcap with its exact size; a wrong name or size stops here.
check_bag() {   # prints a problem, or nothing if the folder is complete
    local dir="$1" name size have other
    [ -f "$dir/bag_files.txt" ] || return 0
    while read -r name size _; do
        case "$name" in ''|\#*) continue ;; esac
        if [ -f "$dir/$name" ]; then
            have=$(stat -f%z "$dir/$name" 2>/dev/null || stat -c%s "$dir/$name")
            [ "$have" = "$size" ] || { echo "$name is $have bytes, expected $size: download incomplete or damaged"; return; }
        else
            other=$(ls "$dir" | grep -m1 '\.mcap' || true)
            if [ -n "$other" ]; then echo "found '$other', expected '$name': rename it"; else echo missing; fi
            return
        fi
    done < "$dir/bag_files.txt"
}
if [ -z "${BAG_DIR:-}" ]; then
    problem=$(check_bag "$HERE/../Dataset/HCI-bag-v2")
    case "$problem" in
        "") BAG_DIR="$HERE/../Dataset/HCI-bag-v2" ;;
        missing) BAG_DIR="$HERE/../Dataset/autonomy_demo_slim"
                 echo "HCI-bag-v2 not downloaded (see Dataset/HCI-bag-v2/README.md); using autonomy_demo_slim" >&2 ;;
        *) echo "Dataset/HCI-bag-v2: $problem" >&2; exit 1 ;;
    esac
fi
PORT="${PORT:-8765}"
RATE="${RATE:-1.0}"                                     # playback speed
IMAGE="${IMAGE:-cavs-bag-bridge}"                       # or IMAGE=ghcr.io/islamzee/hci_cavs_1/cavs-bag-bridge:latest (no build needed)
POD=cavs

case "${1:-}" in
  build)
    podman build -t "$IMAGE" -f "$HERE/Containerfile" "$HERE" ;;
  up)
    BAG_DIR="$(cd "$BAG_DIR" && pwd)"
    # Linux with SELinux enforcing (RHEL, Rocky, Fedora): label the mounts so the containers may read them
    MNT=ro
    if [ "$(uname)" = Linux ] && command -v selinuxenabled >/dev/null && selinuxenabled; then MNT=ro,z; fi
    podman pod create --name "$POD" -p "$PORT:8765"
    # bridge first, so it is subscribed before the player starts publishing.
    # --restart=always: on a server, "podman-restart.service" starts them again after a reboot (Server_Setup_v1.md)
    podman run -d --restart=always --pod "$POD" --name cavs-bridge -v "$HERE:/web:$MNT" -v "$BAG_DIR:/bag:$MNT" "$IMAGE" python3 /bridge/bridge.py
    podman run -d --restart=always --pod "$POD" --name cavs-player -v "$BAG_DIR:/bag:$MNT" "$IMAGE" \
      bash -c "sleep 3; exec ros2 bag play /bag --loop --rate $RATE --topics \$(python3 /bridge/topics.py)"
    echo "Bag: $BAG_DIR"
    echo "Dashboard: http://localhost:$PORT/dashboard/   Probe page: http://localhost:$PORT/   websocket: ws://localhost:$PORT/   receive counts: http://localhost:$PORT/stats" ;;
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
