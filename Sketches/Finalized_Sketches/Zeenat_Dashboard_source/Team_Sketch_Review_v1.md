# Team dashboard sketch — feasibility review

Author: Zeenat Islam
Reviewed against: autonomy_demo_0 bag (checked with Dataset/bag_inspection) and the client notes C-001 to C-009.

Legend: Feasible = data exists and is cheap to show · Partial = needs a substitute or relabel · Not supported = no data in the bag, or too costly for latency/bandwidth

## Panel by panel

| Panel / element | Verdict | Why | Suggested change |
|---|---|---|---|
| Header: GPS OK | Not supported | No GPS topic in the bag | Replace with "Localization" from /mtx/odom age (median 2.6 ms, max 64 ms in /mtx/velocity_filter/status) |
| Header: COMMS OK | Feasible | Can be measured in the browser from websocket message age | Show "last message 0.1 s ago" |
| Header: BATTERY 78% | Not supported | No battery topic. /ouster/telemetry only reports LiDAR thermal state | Drop |
| Header: clock | Feasible | Bag time | Show bag date and time (Fri 11 Sep 2026, 11:45–11:47 CDT), per C-008 |
| Drive status: AUTONOMOUS | Feasible | /mtx/arbiter_status mode (MANUAL, AUTONOMY, ESTOP), 5 Hz | Add STOPPED / E-STOP and MANUAL states |
| Drive status: Navigating to Waypoint 3 | Partial | Waypoints are not recorded. The goal (14.5, −12.3) is the end of /plan, and waypoint 1 (≈ 27.6, 1.6) can be inferred from the sharp turn in /plan. Only 2 waypoints exist | "Navigating to Waypoint 1 of 2" with distances in metres |
| Speed 12 km/h | Feasible, value unrealistic | /mtx/odom, 100 Hz. Max speed in this run is 2.2 m/s (8 km/h), mostly 1–2 m/s | Show m/s, throttle display to 5 Hz |
| Steering 2.4 | Partial | No measured steering angle. Only the raw command /mtx/drive_command x (−292 to 409, units unknown) or turn rate from /mtx/cmd_vel_autonomy | Show commanded turn rate, or ask CAVS for units |
| Gear D (Auto) | Not supported | No gear data | Drop |
| Terrain mode Rock / Rough | Not supported | No terrain data | Drop |
| Front camera with obstacle boxes, distances and drivable corridor | Not supported | Camera frames are white; camera_info is empty (no calibration); cameras have no TF frames, so LiDAR or path cannot be projected into the image; no object-detection topic. Running detection on the server adds GPU load and hundreds of ms. Full-rate video is ~60 MB/s per camera (C-004) | 1 frame/s thumbnails of all 3 cameras with feed status. Obstacles shown on the LiDAR grid instead |
| Camera / LiDAR / Faults tabs | Feasible | | LiDAR tab = panorama image (/ouster/reflec_image), per C-009 |
| Navigation map: path, vehicle | Feasible | /plan (every ~3 s), /mtx/odom, global costmap | Keep |
| Navigation map: WP 1–4 | Not supported | Waypoints not recorded (/goal_pose empty) | Show start, vehicle, goal only until CAVS supplies waypoints |
| Navigation map: NO-GO zone | Not supported | No keep-out or zone data | Drop, or ask CAVS |
| Systems health: Localization | Feasible | odom age, /mtx/odom rate | |
| Systems health: Perception | Not supported | No perception/detection node in the bag | Replace with "Cameras" and "LiDAR" feed health (rates, gaps, lidar_age_s) |
| Systems health: Planning, Control | Feasible | /bond heartbeats from planner_server, controller_server; "patience exceeded" log lines | |
| Systems health: Safety | Feasible | /mtx/velocity_filter/status (ok flag, inhibit reasons, 20 Hz), collision monitor, arbiter | |
| Systems health: Sensors | Feasible | Message rates and gaps | |
| LiDAR top view with obstacle ellipses | Partial | Obstacles come from /local_costmap/costmap (30 × 30 m, 0.2 m, 1.7 Hz, up to 0.6 s old). It shows occupied cells, not classified objects | Draw the real grid, label its age |
| Planned path (local), perspective view | Partial | Perspective needs camera calibration (missing). Top-down is possible from /received_global_plan (base_link frame, 15.6 Hz) and /lookahead_point | Top-down local path over the LiDAR grid; merge with the LiDAR panel |
| Lookahead 5 m | Feasible | /lookahead_point | Show actual value (about 4 m at mid-run) |
| Upcoming waypoints with km and terrain features | Not supported | No waypoint list; whole run is 29 m; no terrain annotations | Replace with goal distance and remaining path length in metres |
| Bottom bar: No Active Alerts | Feasible | Fed by the trigger list | Link to stop triggers |

## Not in the sketch but needed
- The client's main function: stop the vehicle when a trigger fires (C-005). There is no trigger list, STOP banner or stop state.
- Data freshness: each panel should show how old its data is, since sources update at very different rates.

## Latency budget (from the bag)

| Source | Update rate | Typical age | Display plan |
|---|---|---|---|
| Arbiter mode, safety status | 5–20 Hz | < 0.2 s | Live |
| Vehicle pose / speed | 100 Hz | ~3 ms | Throttle to 5–10 Hz |
| Local path, lookahead | 15.6 Hz | < 0.1 s | Throttle to 5 Hz |
| LiDAR (scan) | 10 Hz | 55 ms median, 261 ms max (lidar_age_s) | Not sent raw |
| LiDAR occupancy grid | 1.7 Hz | up to 0.6 s | PNG, ~1 kB |
| Global plan | every ~3 s | up to 3 s | On change |
| Camera thumbnails | 1 frame/s | up to 1 s | JPEG, ~15 kB each |
| Autonomy command age | 20 Hz | 48 ms median, 6.3 s max (outside autonomy) | Feeds trigger T5 |
