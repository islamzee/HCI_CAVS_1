# Front-end data guide: getting live data for your module

For: everyone building a dashboard module (Home, Map, Sensors, Faults, Logs, Settings).
Author: Zeenat Islam · v1 · 9 Nov 2026

You do not need ROS. A Podman pod on your laptop replays the recorded run (`autonomy_demo_0`, 72 s, looping)
and streams its data as JSON over a websocket. Your page connects to it like any other websocket.

```
 your laptop
 ┌──────────────── Podman pod ────────────────┐
 │ bag player ──► bridge  ws://localhost:8765/ │──► your front end (any framework, any port)
 └─────────────────────────────────────────────┘
```

---

## 1. Start the data (every work session)

One-time setup is in [README.md](README.md#windows-setup) (Podman Desktop + the slim bag from the team drive).

| | Windows | macOS |
|---|---|---|
| Start | double-click `Implementation\start-windows.bat` | `cd Implementation && BAG_DIR=../Dataset/autonomy_demo_slim ./pod.sh up` |
| Stop | double-click `Implementation\stop-windows.bat` | `./pod.sh down` |

Check it works: open **http://localhost:8765/**. This probe page lists every topic with its latest values.
If you see numbers changing, your front end can connect.

The run loops: every 72 s the data jumps back to the start (see section 5).

---

## 2. Connect from your front end

Use the helper [client/cavs-client.js](client/cavs-client.js). It's one file with no dependencies: copy it into your project.

```js
import { CavsClient, decodeGrid, cameraSrc, yawFromQuaternion } from "./cavs-client.js";

const cavs = new CavsClient("ws://localhost:8765/");   // create ONE per app and share it

cavs.onStatus((s) => console.log("bridge:", s));        // "connecting" | "open" | "closed" (reconnects by itself)
cavs.on("/mtx/odom", (d) => {
  vehicle.x = d.x; vehicle.y = d.y;                     // metres, frame "odom"
  vehicle.speed = d.linear_x;                           // m/s, as recorded
});
cavs.onRestart(() => clearMyTables());                  // the bag started again from 00:00
```

- `cavs.on(topic, fn)` returns an unsubscribe function. In React, call it inside `useEffect` and return it as the cleanup.
- `cavs.on("*", (data, topic) => ...)` receives every topic.
- `cavs.latest(topic)` returns the newest value received on a topic.

Working example: [client/example.html](client/example.html). To try it, run `python -m http.server 8000` inside `Implementation/client`,
then open `http://localhost:8000/example.html`. ES modules don't load from `file://`.

Your dev server (Vite, React, plain HTML) can use any port; the bridge accepts connections from any origin.

**Not using the helper?** Every websocket message is one JSON object:
```
{"type":"msg", "topic":"/mtx/odom", "data":{...}}                  data for a topic
{"type":"hello", "camera":2, "camera_hz":2.0, ...}                 first message after connecting
{"type":"history_end", "messages":205}                             see "When you connect" below
{"type":"playback", "event":"restart"}                             bag looped back to 00:00
{"type":"settings", "camera":0, "camera_hz":5.0}                   reply to a command
```
Commands you can send: `{"cmd":"camera","id":0|1|2}` and `{"cmd":"camera_rate","hz":0.2..10}`.

**When you connect**, the bridge first sends the latest message of each event topic (e-stop, arbiter, plan,
diagnostics, collision monitor) and the last 200 `/rosout` lines, then `history_end`. After that, everything is live.
So a page opened mid-run still shows the correct e-stop state and recent log lines.

---

## 3. Which topics your module needs

From `Sketches/Finalized-list-of-sketches.txt`. Full field list in section 4.

| Module | Owner | Topics |
|---|---|---|
| **Map** (waypoints, path, obstacles) | Nathan | `/mtx/odom` (vehicle position + heading), `/plan` (planned path), `/dlio/odom_node/path` (driven path), `/local_costmap/published_footprint` (vehicle outline), `/global_costmap/costmap` and `/local_costmap/costmap` (obstacles), `/mtx/nav/stop_zone`, `/mtx/nav/slowdown_zone`, `/mtx/nav/collision_monitor_state` |
| **Logs, Status** | Chuck | `/rosout` (log lines), `/mtx/arbiter_status` (mode), `/diagnostics` (Nav2 + drive bridge), `/mtx/estop`, `/mtx/velocity_filter/status` (safety filter) |
| **Sensors, Faults** | Caleb | `/cam_0/1/2/image_raw` + `/cam_N/meta`, `/local_costmap/voxel_layer` (occupancy grid view), `/ouster/telemetry`, `/mtx/velocity_filter/status` (`*_age_s` fields), `/mtx/nav/collision_monitor_state`, `/rosout` (level ≥ 30) |
| **Home / Dashboard** | Zeenat | header: `/mtx/velocity_filter/status`, `/diagnostics`, `/mtx/estop`; drive status: `/mtx/arbiter_status`, `/mtx/odom`, `/mtx/cmd_vel_autonomy`, `/mtx/drive_command`; plus camera, grid, map and log as above |

---

## 4. Field reference

Values are exactly as recorded in the bag: no field is calculated by the bridge.
`stamp` = recorded time in seconds since 1970 (UTC). The run is 11 Sep 2026 around 11:45–11:47 CDT, so show it in `America/Chicago`.
"Sent" = the maximum rate the bridge sends to your browser. Topics marked *every message* are never dropped.

### Vehicle state and safety
| Topic | Sent | Fields |
|---|---|---|
| `/mtx/arbiter_status` | every message (5 Hz) | `mode` (0 MANUAL, 1 AUTONOMY, 2 ESTOP), `autonomy_requested`, `autonomy_active`, `estop`, `joy_fresh`, `autonomy_cmd_fresh`, `active_source` (`"autonomy"`, `"manual"`, `"stop"`, `""`), `inhibit_reasons` (list of strings) |
| `/mtx/velocity_filter/status` | 5 Hz, plus at once whenever `ok`/`inhibit_reasons` changes | `ok`, `inhibit_reasons`, `cmd_age_s`, `odom_age_s`, `tf_age_s`, `lidar_age_s`, `clock_offset_s` (seconds) |
| `/mtx/estop` | every message (2 per run) | `data` (true = software e-stop latched) |
| `/mtx/nav/collision_monitor_state` | every message (2 per run) | `action_type` (0 none, 1 stop, 2 slowdown, 3 approach, 4 limit), `polygon_name` |
| `/diagnostics` | every message (2 Hz) | `status`: list of `{name, level (0 OK, 1 WARN, 2 ERROR, 3 STALE), message, hardware_id, values {key: text}}`. Names: `mtx_nav2/drive_bridge`, `lifecycle_manager_navigation: Nav2 Health` |
| `/rosout` | every message | `stamp`, `level` (10 DEBUG, 20 INFO, 30 WARN, 40 ERROR, 50 FATAL), `name` (node), `msg`. Nodes: controller_server, command_arbiter, velocity_filter, web_ui, collision_monitor, bt_navigator, cam_0/1/2, rosbag2_recorder, … |

### Motion
| Topic | Sent | Fields |
|---|---|---|
| `/mtx/odom` | 10 Hz (recorded 100 Hz) | `x`, `y` (m, frame `odom`), `qz`, `qw` (heading as quaternion; `yawFromQuaternion(qz, qw)` gives radians), `linear_x` (m/s), `angular_z` (rad/s) |
| `/mtx/cmd_vel_autonomy` | 10 Hz | `linear_x`, `linear_y` (m/s), `angular_z` (rad/s): what autonomy commanded |
| `/mtx/drive_command` | 10 Hz, plus at once when `source` changes | `x` steer, `y` throttle, `z` pivot (counts, −1000..1000), `source` |

### Map and navigation (all positions in metres)
| Topic | Sent | Fields |
|---|---|---|
| `/plan` | every message (19 per run) | `poses`: `[[x, y], …]` in `odom`. The last point is the end of the plan. |
| `/dlio/odom_node/path` | 0.5 Hz | `poses`: `[[x, y], …]` in `odom`, the driven path so far (grows to about 1050 points) |
| `/local_costmap/published_footprint` | 2 Hz | `points`: 4 corners `[[x, y], …]` in `odom` |
| `/mtx/nav/stop_zone`, `/mtx/nav/slowdown_zone` | 1 Hz | `points` in **`base_link`** (relative to the vehicle: x forward, y left). To draw them on the map, rotate by the vehicle heading and add the `/mtx/odom` position. |
| `/global_costmap/costmap` | every message (~0.6 Hz) | grid, 200 × 200 cells, 0.5 m per cell |
| `/local_costmap/costmap` | every message (~1.7 Hz) | grid, 150 × 150 cells, 0.2 m per cell, moves with the vehicle |
| `/local_costmap/voxel_layer` | every message (~1.7 Hz) | grid as above, obstacles from LiDAR only (0 or 100) |

**Grids:** `width`, `height`, `resolution` (m per cell), `origin_x`, `origin_y` (position of cell row 0, column 0 in `odom`), `png`.
`await decodeGrid(d)` gives `values[row * width + col]`: 0 free … 100 occupied, −1 unknown.
Row 0 is at `origin_y`, so flip vertically when drawing on a canvas (y up). Cell (col, row) is at
`x = origin_x + (col + 0.5) * resolution`, `y = origin_y + (row + 0.5) * resolution`.

### Sensors
| Topic | Sent | Fields |
|---|---|---|
| `/cam_N/image_raw` (N = 0, 1, 2) | only the camera you selected, 2 fps by default (`setCamera`, `setCameraRate` up to 10) | `jpeg` (use `cameraSrc(d)` as `<img src>`, 640 px wide), recorded `width` 2048, `height` 1536, `encoding` `mono8`, `frame_id`, `stamp` |
| `/cam_N/meta` | 1 Hz each | `exposure_time` (µs), `max_exposure_time`, `gain`, `brightness`, `camera_time` |
| `/ouster/telemetry` | 1 Hz, plus at once on status change | `thermal_shutdown` (0 normal, 1 imminent), `shot_limiting` (0 normal, 1 imminent, 2–9 reduction steps), `countdown_thermal_shutdown`, `countdown_shot_limiting` |

---

## 5. Things that will surprise you

- **The run loops every 72 s.** Stamps jump back to the start and you get `playback restart` (`cavs.onRestart`). Clear logs, paths and tables then.
- **Camera images are all white.** That's the recorded data (bag issue 3), not a bug. Camera `stamp` uses the camera's own clock (around 8150 s), so don't show it as a date.
- **No GPS, no waypoint list.** Positions are metres from the start, in frame `odom`. The goal is not recorded (`/goal_pose` is empty); the end of `/plan` is the nearest thing.
- **The data has no faults.** CAVS will send a bag with faults later (C-018). Fault rows in the Figma sketches are sample data.
- **Only one run.** A "past runs" list can only show `autonomy_demo_0` for now.

## 6. Team rules for what to show (from the client)

- **Show recorded values, not calculated ones (C-021).** Display fields as they come. Formatting is fine (units, rounding, clock time, colour by recorded status/level). Values the bag doesn't contain are not, unless the team agrees on them first. Examples: distance travelled, distance to goal, event counts, "2.9 s ago", measured Hz.
- **Default camera is 2 (C-013).** Keep the light theme (C-014). Visual alerts only, no sounds (C-015).
- **Occupancy grid instead of point clouds (C-016).** Point clouds are never sent to the browser.

## 7. Not in the stream yet (ask Zeenat)

| Needed by | What | Status |
|---|---|---|
| Sensors, Faults (topic rate table) | measured Hz, last-message age, stamp delay per topic, incl. `/ouster/points`, `/ouster/imu`, `/dlio/odom_node/odom` | planned in the bridge. Don't compute these from the stream: it is throttled, so the rates you see are the bridge's send rates. |
| Settings → fault thresholds | 500 ms / 200 ms / 80 % / safety false | planned, together with the rate table |
| Settings → camera rate | | works now: `setCameraRate(hz)`, 0.2–10 fps (the recording is ~19 fps) |
| Logs → past runs | list of bags | only one bag so far |

If you need another topic or field, ask Zeenat: it's one line in [bridge/topics.py](bridge/topics.py).
The topics recorded in the bag are listed in `Dataset/autonomy_demo/metadata.yaml`.
