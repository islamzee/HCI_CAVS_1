# CAVS-1 implementation: bag player + websocket bridge

Author: Zeenat Islam

The recorded bag (`Dataset/autonomy_demo/autonomy_demo_0.mcap`, ROS 2 Jazzy) is replayed inside a Podman pod and
streamed to the browser over a websocket. The browser dashboard connects to `ws://<host>:8765/`.

```
 Podman pod "cavs"  (port 8765 published to the host)
 ┌───────────────────────────────────────────────────────────────────────┐
 │ cavs-player   ros2 bag play --loop --topics <dashboard topics>         │
 │                  │  DDS (UDP, inside the pod only)                     │
 │ cavs-bridge   bridge.py  (rclpy subscriber → throttle → JSON)         │
 └──────────────────┬────────────────────────────────────────────────────┘
                    │ ws://localhost:8765/   (~43 kB/s)
               browser dashboard
```

## Windows setup

1. **Install [Podman Desktop](https://podman-desktop.io)** and open it once. Accept its offer to set up WSL and a Podman machine (a restart may be needed).
2. **Get the bag.** Download the `autonomy_demo_slim` folder from the team drive and put it in `Dataset` in your copy of this repo:
   ```
   HCI_CAVS_1\Dataset\autonomy_demo_slim\metadata.yaml
   HCI_CAVS_1\Dataset\autonomy_demo_slim\autonomy_demo_slim_0.mcap
   ```
3. **Double-click `Implementation\start-windows.bat`.** The first run downloads about 1 GB. Your browser then opens `http://localhost:8765/`, the probe page with live data.

To stop, double-click `Implementation\stop-windows.bat`. To get updates, `git pull` and run `start-windows.bat` again.

If something goes wrong, the window says what to do. To see the player's own messages: `podman logs cavs-player`.

Never put bags in this repo. It is public, and the bags are CAVS data.

**Building a module?** Read [Frontend_Data_Guide_v1.md](Frontend_Data_Guide_v1.md): how to connect, which topics your module needs, and every field.

## macOS setup
```
brew install podman
podman machine init --cpus 6 --memory 8192 --disk-size 40
podman machine start
cd Implementation
BAG_DIR=../Dataset/autonomy_demo_slim ./pod.sh build
BAG_DIR=../Dataset/autonomy_demo_slim ./pod.sh up
```

## Details: manual commands (any OS)
`start-windows.bat` does these steps:
```
podman pull ghcr.io/islamzee/hci_cavs_1/cavs-bag-bridge:latest
podman volume create --opt type=none --opt o=bind --opt device=<bag folder as seen by the Podman machine> cavs-bag
podman kube play Implementation/cavs-pod.yaml      # stop: podman kube down Implementation/cavs-pod.yaml
```
On Windows, the Podman machine sees `C:\Users\...` as `/mnt/c/Users/...`. To use another bag: `start-windows.bat -Bag D:\path\to\bag`.

The image is built by GitHub Actions (`.github/workflows/container.yml`) for Intel/AMD and Apple silicon on every push to `main` that changes `Implementation/`. The image is public, so no login is needed.

## Run with pod.sh (macOS/Linux, builds the image locally)
From this folder:
```
./pod.sh build      # image: ros:jazzy + MCAP plugin + custom msgs + bridge (first build ~2 min)
./pod.sh up         # start pod; bridge first, player 3 s later
./pod.sh status
./pod.sh logs player   # or: logs bridge
./pod.sh topics     # ros2 topic list + /mtx/odom rate, from inside the pod
./pod.sh down
```
Options: `RATE=0.5 ./pod.sh up` (playback speed), `PORT=9000 ./pod.sh up`, `BAG_DIR=/path/to/bag ./pod.sh up`
(folder holding `metadata.yaml` and the `.mcap`, for the second bag).

Check pages:
- `http://localhost:8765/` probe page: per-topic counts and latest values, camera buttons and Hz, voxel grid
- `http://localhost:8765/stats` messages the bridge has received from ROS, per topic

## Files
| File | What it does |
|---|---|
| Containerfile | ROS 2 Jazzy image with rosbag2 MCAP storage, nav2/map/visualization/bond messages, the custom messages and the bridge |
| msgs/ | `mtx_nav2_msgs`, `flir_camera_msgs`, `ouster_sensor_msgs`: definitions copied from the schemas embedded in the .mcap. Needed because `ros2 bag play` can only publish types it has installed |
| bridge/topics.py | The dashboard topics, send mode and rate, and the recorded fields kept for each. The player also takes its topic list from here |
| bridge/bridge.py | ROS subscriber + websocket server |
| bridge/probe.html | Test page served by the bridge |
| start-windows.bat, stop-windows.bat, start-windows.ps1 | One-click start/stop on Windows (Podman machine, image, bag volume, pod, browser) |
| Frontend_Data_Guide_v1.md | For module developers: connecting, topics per module, field reference |
| client/cavs-client.js, client/example.html | Browser helper (connect, reconnect, per-topic callbacks, grid decoding) and a working example |
| cavs-pod.yaml | Pod definition for `podman kube play` (Windows and macOS) |
| pod.sh | build / up / down / logs / status / topics (macOS/Linux) |
| make_slim_bag.sh | Small copy of a bag: dashboard topics only, zstd-compressed (autonomy_demo: 18 GB → 19 MB, same message counts; the saturated camera frames compress to almost nothing) |
| ../.github/workflows/container.yml | Builds and publishes the image to ghcr.io |
| entrypoint.sh | Sources ROS and the custom messages |

## Websocket protocol
Server → browser, one JSON object per websocket message:
```
{"type":"hello", "topics":{topic:{mode,hz}}, "cameras":[...], "camera":2, "camera_hz":2.0, "camera_hz_range":{...}}
{"type":"msg", "topic":"/mtx/odom", "data":{"stamp":..., "x":..., "linear_x":..., ...}}
{"type":"settings", "camera":0, "camera_hz":2.0}        (reply to a command)
{"type":"history_end", "messages":205}                  (after the connect-time history: latest message of each event topic + last 200 /rosout lines)
{"type":"playback", "event":"restart"}                  (the bag looped back to the start)
```
Browser → server:
```
{"cmd":"camera", "id":0|1|2}             camera shown to this browser (default 2, C-013)
{"cmd":"camera_rate", "hz":0.2..10}      camera frames per second for this browser (C-011)
```

Data rules:
- Only recorded fields are sent (C-021). Each topic's fields are listed in `bridge/topics.py`.
- `stamp` is the recorded `header.stamp` in seconds. Camera stamps use the camera's own clock, the same as in the bag.
- Event-like topics (`/rosout`, `/diagnostics`, `/mtx/arbiter_status`, `/mtx/estop`, `/mtx/nav/collision_monitor_state`, `/plan`) are sent in full.
- High-rate topics are sent as the latest value at a capped rate. A state change (for example `ok` / `inhibit_reasons` on `/mtx/velocity_filter/status`, telemetry status, or drive command `source`) is sent at once.
- Occupancy grids are sent as a lossless 8-bit PNG of the cell values (0–100; unknown −1 is stored as 255), plus `width`, `height`, `resolution` and `origin`. PNG row 0 is grid row 0, so the browser flips it vertically. Colours are chosen in the browser.
- Camera frames are sent as JPEG, 640 px wide, for display; `width`, `height` and `encoding` are the recorded values. The bridge subscribes only to cameras a browser is viewing (raw frames are 3.1 MB each).
- `/rosout` lines from nodes running in the pod (`cavs_ws_bridge`, `rosbag2_player`) are dropped, so the log shows recorded lines only.
- Not streamed: `/ouster/points` and other point clouds, `/tf`, the Ouster images.

## Measured (9 Nov 2026, MacBook arm64, Podman 6.1.4 VM 6 CPU / 8 GB)
- Player keeps real time: `/mtx/odom` about 95–100 Hz, `/cam_2/image_raw` about 18 Hz received by the bridge (recorded 100 / 18.8 Hz).
- Websocket to one browser: **42.8 kB/s** total. Largest: `/dlio/odom_node/path` 15.9 kB/s (0.5 Hz), camera 5.3 kB/s (2 Hz).
- Camera switching works mid-stream. `--loop` restarts cleanly; both `/mtx/estop` messages arrive.
- Camera frames are all white: the recorded frames are saturated (ROS_Bag_Issues item 3). The bridge is not the cause.

## Notes
- DDS runs over UDP only (`FASTDDS_BUILTIN_TRANSPORTS=UDPv4`), with `ROS_DOMAIN_ID=42` and discovery limited to localhost, so the pod does not talk to other ROS machines on the network.
- The custom message packages contain only the types recorded in this bag. If a later bag has other `mtx_nav2_msgs` types, add their `.msg` files (they are in the bag's embedded schemas).
