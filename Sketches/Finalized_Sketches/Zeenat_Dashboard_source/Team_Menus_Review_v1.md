# Team menu sketches — suggested changes and navigation

Author: Zeenat Islam
Pages reviewed: Map, Sensors, Faults, Past Logs, Log detail.
Basis: autonomy_demo_0 bag, client notes C-001 to C-009, and the rule that only recorded fields are shown (no calculated values).

## All pages
- Same header on every page (Sensors and Faults have none): Safety filter, Nav2, Drive bridge, E-stop, bag clock. Remove GPS, Comms, Battery (not recorded).
- One theme. Home, Map and Logs are light; Sensors and Faults are dark.
- A LIVE / REVIEW chip in the header. LIVE = bag playing as a mock live session. REVIEW = looking back at a finished run.
- Clock shows the bag's recorded time (Fri 11 Sep 2026, 11:45:48–11:47:00 CDT), not Sep 28.
- Bottom alert bar is clickable and opens Faults.

## Map
| Element | Change | Reason |
|---|---|---|
| Playback controls 00:01:25 | Move to REVIEW mode only. In LIVE mode the map follows the bag clock with no scrubbing | Client wants playback to look live |
| Vehicle / Path / Waypoint distances in km | Remove | Calculated; this run is 29 m long |
| Faded waypoints and second dashed route | Remove | Not in the bag. Recorded: /plan and its goal (14.5, −12.3) |
| Waypoint markers | Goal only (end of /plan) | /goal_pose is empty |
| Camera lag / GPS dropout / LiDAR dropout markers and counts | Replace with recorded events: /rosout WARN and ERROR, collision monitor zones (11:46:11), e-stop (11:46:52), each placed at the vehicle position recorded at that moment | No GPS data; no LiDAR dropout; camera lag needs calculation |
| Obstacles (2 squares) | Show the global costmap layer | Obstacles are recorded as grid cells, not counted objects |
| Faults / Logs buttons in the legend | Remove; clicking an event marker opens that entry in Faults or Logs instead | Duplicates the bottom bar |
| Base map | Recorded: global costmap, /dlio/odom_node/path, /plan, footprint | No satellite imagery without GPS |

## Sensors
| Element | Change | Reason |
|---|---|---|
| One Camera panel | Three camera panels (CAM 0–2), latest frame once per second | Client: 3 cameras (C-003) |
| LAG 700 ms badge | Remove the number. Show the image's recorded header stamp instead | Lag is calculated; this bag peaks at 265 ms gaps on Camera 2 |
| LiDAR black panel | /ouster/reflec_image panorama (recorded image) and the local costmap | Raw point cloud ruled out (C-009) |
| LiDAR DROPOUT badge | Show recorded lidar_age_s from /mtx/velocity_filter/status | Recorded freshness value; no dropout in this bag |
| Note | Camera frames in this bag are white | Bag check, Q to CAVS |

## Faults
| Element | Change | Reason |
|---|---|---|
| Critical / Warnings counts, Uptime | Replace with lists split by recorded severity: ERROR and WARN from /rosout | Counts and uptime are calculated |
| "3.1 s ago" | Show the recorded clock time (11:46:52) | Relative time is calculated |
| LiDAR dropout / Camera lag cards | Depend on the stop-trigger decision. Without triggers, cards come from: /rosout ERROR/WARN, safety-filter inhibit reasons (no_cmd, cmd_stale), arbiter inhibit (estop), collision monitor | Recorded sources only |
| Each card | Node name, message, clock time, and links "Show on map" and "Open in log" | Connects to Map and Log detail |
| "More room for faults" | Scrolling list, newest first | |

## Past Logs
| Element | Change | Reason |
|---|---|---|
| Rows 122–127 with invented dates | One row per bag file on the server. Now: autonomy_demo_0 | Only one run exists |
| Columns | Name, Date, Start time, Duration, Messages, ROS distro — all from metadata.yaml | Recorded |
| Errors column | Remove, or keep only if counting is accepted | Counting is a calculation |
| Values for this bag | autonomy_demo_0 · 09/11/2026 · 11:45:48 am · 00:01:12 · 124,845 messages · jazzy | |

## Log detail
| Element | Change | Reason |
|---|---|---|
| Invented messages (Checking systems…, Loading path…) | Real /rosout lines: clock time, level, node, message (233 lines, 92 from the recorder) | Recorded |
| Time stamp 0:00–10:06 | Bag clock time (11:45:56 …) | Elapsed time is calculated |
| Filters | Level (INFO / WARN / ERROR) and node | Long list; recorder lines are noise |
| Title | LOG autonomy_demo_0 · 09/11/2026 · 00:01:12 | |
| Each line | "Show on map" opens Map in REVIEW at that moment | |

## Navigation flow

```
                 ┌──────────── bottom bar (every page) ────────────┐
                 Home   Map   Sensors   Logs   Faults   [alert bar]
                                                           │ click
LIVE MODE                                                  ▼
Home ── panel links ──► Map / Sensors / Faults          Faults
  │                                                        │ card
  │ alert bar ─────────────────────────────────────────────┤
  │                                                        ├─► Map (event marker highlighted)
  │                                                        └─► Log detail (line highlighted)
REVIEW MODE
Logs (past runs) ──► Log detail ──► "Show on map" ──► Map with playback controls
                                     ▲                    │ marker click
                                     └────────────────────┘
```

- Home is the hub in LIVE mode; the alert bar is the shortcut to Faults.
- Faults, Map markers and Log lines all point at the same event, so the operator can move between them without losing the moment.
- REVIEW mode starts only from Logs. Playback controls exist only there and on the Map in REVIEW.
- Settings: no vehicle control is allowed (C-002). Keep only display options (theme, log level filter) or remove the tab.
