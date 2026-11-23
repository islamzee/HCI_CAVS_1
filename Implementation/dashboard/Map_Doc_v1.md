# Map Page Documentation (`map.js`)

**Owner:** Nathan · v1 · 22 Nov 2026

**Module:** `Implementation/dashboard/js/pages/map.js`

**Reference Sketch:** `Map V2 (+ Route faults / Route log overlays)`

**Data Policy:** Recorded values only (`C-021`)

## 1. Overview & Screen Design

The Map page provides a spatial view of the autonomous vehicle's trajectory, costmap obstacles, safety boundaries, and location-stamped alerts in frame `odom` (metres relative to the start origin). It is built on the dashboard's shared infrastructure (`state.js`, `lib/draw.js`, `lib/format.js`, and `client/cavs-client.js`) and follows the standard page module contract (`{ title, mount(root, { cavs, state }) }` returning a teardown callback).

### Layout Structure

The page uses a two-column layout (`270px` left rail + fluid map stage):

* **Left Rail (Telemetry & Pin Filters)**

  * **Recorded Bag Time Header:** Displays the current recorded clock time (`state.bagTime`), active bag name (`state.bag.name`), and date (`dateLabel`).

  * **Interactive Metric & Filter Cards:**

    * **Vehicle:** Displays recorded linear speed (`/mtx/odom` `linear_x` in `m/s`). Clicking switches the camera to **Follow** mode.

    * **Position:** Displays recorded `(x, y)` coordinates in `odom` (`/mtx/odom`). Clicking switches the camera to **Fit Route** mode.

    * **Plan End:** Displays the last recorded `(x, y)` point on `/plan` (or `waiting…` when `/plan` is empty). Clicking pans to the end of the plan.

    * **Safety:** Displays the live `/mtx/velocity_filter/status` state (`OK` / `INHIBIT`) and toggles Safety pins on the map.

    * **Warnings / Errors:** Displays filter visibility (`Shown` / `Hidden`) and toggles Warning or Critical/Error pins on the map.

  * **Pin View Filter (`Faults` | `Logs`):** Switches both the active pin pool on the map and which table format opens when clicking a pin.

* **Map Stage (Interactive Canvas & Toolbar)**

  * **Header Controls:** Independent visibility toggles for `Global Costmap`, `Local Costmap`, `Safety Zones`, and `Footprint`, plus `Fit Route` and `Follow` camera controls.

  * **Canvas Interactions:** Mouse-drag panning, scroll-wheel zooming, and click-to-inspect alert pins. Dragging or zooming out of `Fit Route` snapshots the current viewport into manual mode cleanly.

  * **Movable Pin Overlay:** Clicking a pin opens a floating, draggable window over the map showing the recorded faults or logs stamped at that location, with direct links out to `#/faults` and `#/logs`.

### Canvas Layering & Coordinate Handling

Layers render in painter's order (bottom to top) using `draw.js`'s `redrawer()` (\~30 fps timer throttle) and `fitCanvas()` (DPR scaling):

1. **Global & Local Costmaps** (`/global_costmap/costmap`, `/local_costmap/costmap`): Decoded asynchronously into offscreen canvases via `gridCanvas()` with generation counters to prevent out-of-order decode races. Local costmap blends at `0.65` alpha when layered over the global costmap.

2. **Planned Path** (`/plan`): Dashed blue line (`COLORS.acc`).

3. **Driven Path** (`/dlio/odom_node/path`): Solid dark ink line (`COLORS.ink`).

4. **Safety Zones** (`/mtx/nav/slowdown_zone`, `/mtx/nav/stop_zone`): Because these polygons publish in frame `base_link`, each vertex $(b_x, b_y)$ is transformed into `odom` using the vehicle's recorded pose $(o_x, o_y, \psi)$ from `/mtx/odom` (`yawFromQuaternion(qz, qw)`):

   $$
   x = o_x + b_x \cos\psi - b_y \sin\psi, \qquad y = o_y + b_x \sin\psi + b_y \cos\psi
   $$

   Polygons emphasize dynamically if `/mtx/nav/collision_monitor_state` reports an active slowdown or stop.

5. **Vehicle Footprint & Marker:** Draws the true-scale outline from `/local_costmap/published_footprint` beneath the standardized blue vehicle marker from `home.js` (`vehiclePose()`).

6. **Route Anchors:** `START (0, 0)` square marker and `PLAN END` circle marker.

7. **Spatial Alert Pins:** Inverted triangle markers sorted by severity (`Safety` under `Warnings` under `Errors`). Overlapping pins within a 14 px screen radius cluster visually with an offset shadow outline.

8. **Dynamic Scale Bar:** Automatically adjusts metre length (`1`–`100 m`) via `scaleBar()` as the user zooms.

### Background Alert & Coordinate Tracking

Because `app.js` imports `map.js` at startup, a lightweight module-scoped tracker runs even while the user is viewing other tabs (such as Home or Sensors):

* Tracks `/diagnostics` (`level > 0` transitions deduplicated per component name), `/mtx/velocity_filter/status` (`ok=false`), `/mtx/estop` (`data=true`), `/mtx/nav/collision_monitor_state` (`action_type > 0`), and `state.events` (`/rosout` `level >= 30`).

* Stamps every newly arriving alert with the vehicle's current `(x, y)` pose in a `WeakMap` (`eventPos`) so coordinates persist across tab switches without memory leaks. Startup alerts arriving before the first `/mtx/odom` message are queued and stamped as soon as the initial pose arrives.

* Resets cleanly on `cavs.onRestart()` whenever bag playback loops.

## 2. Changes Made from the Figma Prototype

Several adjustments were made when translating the static `Map V2` Figma prototype into the live WebSocket dashboard:

| Prototype Element | Live Implementation | Rationale | 
| ----- | ----- | ----- | 
| **Playback chapter-skip arrows & progress bar** | Replaced with a read-only **Recorded Bag Time** header. | The Podman bag player loops continuously as a live stream without client-side pausing or chapter skipping. | 
| **`Faults for Current Run` & `Logs for Current Run` full-run buttons** | Repurposed into a **`Pin View Filter`** (`Faults` | `Logs`) that controls map pins and pin-click pop-ups. | In the Figma prototype, full-run buttons stood in for navigating to a timestamp. In the live app, dedicated Faults and Logs tabs sit one click away in the bottom navigation bar. Scoping the Map overlay to clicked pins preserves spatial context without duplicating the full-page views. | 
| **`Info` card in left rail** | Replaced with a dedicated **`Safety`** card (`Info` stays inside the Log overlay). | `state.js` filters out routine `/rosout` info messages (`level < 30`), leaving only recovery transitions. Pinning `Safety` inhibits (`/mtx/velocity_filter/status`) on their own toggleable card surfaces safety interventions spatially without mixing them into ROS node warnings. | 
| **`Obstacles` card in left rail** | Removed from the left rail; obstacle layers are controlled by `Global Costmap` and `Local Costmap` header toggles. | Costmaps are occupancy grids rather than discrete object lists, so no object count exists in the bag. Removing the card avoids an empty or redundant control. | 
| **Prototype color palette** (purple vehicle, dashed blue traveled line, brown obstacles) | Harmonized with `home.js` (blue vehicle marker, solid ink driven path, dashed blue planned route, red costmap obstacles). | Ensures operators see identical vehicle, path, and obstacle symbology when switching between Home and Map. | 
| **Safety boundaries & footprint** (not in original sketch) | Added `/mtx/nav/stop_zone`, `/mtx/nav/slowdown_zone`, and `/local_costmap/published_footprint` layers with header toggles. | Surfaces live collision-monitor safety envelopes and true vehicle footprint directly on the map. | 
| **Log & fault label formatting** | Standardized Log badges to outlined `SAFETY`, `WARN`, `CRIT`, `INFO` | Matches the dashboard's log badge styling while keeping diagnostic entries visually consistent with topic-based fault rows. | 
| **Pre-planned waypoints & path** | Currently listens to `/plan`; mission waypoint integration deferred until bridge topics are updated. | In `hopefully_fixed`, the vehicle ran in `FollowPath` mode, leaving `/plan` empty. The 3 mission waypoints live on `/mtx/mission/waypoints` and `/mtx/mission/events`, none of which are forwarded by `bridge/topics.py` yet. | 

## 3. Discussion of Derived Calculations (`C-021`)

Section 6 of `Frontend_Data_Guide_v1.md` defines client rule **C-021**:

> *Show recorded values, not calculated ones (C-021). Display fields as they come. Formatting is fine (units, rounding, clock time, colour by recorded status/level). Values the bag doesn't contain are not, unless the team agrees on them first. Examples: distance travelled, distance to goal, event counts, "2.9 s ago", measured Hz.*

### Derived Metrics Prototyped vs. Reverted

During iterative development, a full derived-metrics version of `map.js` was built to match the Figma prototype, and then stripped back to a strict recorded-only implementation for `C-021` compliance:

| Feature | Derived Version (Prototyped) | Strict `C-021` Version (Current) | Reason for Reverting | 
| ----- | ----- | ----- | ----- | 
| **Run Progress** | Elapsed time (`bagTime - start_ns`), total duration, and percentage progress bar. | Recorded wall-clock time (`clock(state.bagTime)`), bag name, and date. | Elapsed offset and `%` progress are computed from bag metadata rather than recorded directly. | 
| **Traveled Distance** | Summed Euclidean segment lengths along `/dlio/odom_node/path` (`m`). | Recorded `(x, y)` vehicle position in `odom` from `/mtx/odom`. | Explicitly listed as an unapproved calculated value in `C-021`. | 
| **Waypoint / Remaining Distance** | Projected distance from current pose along `/plan` to the final pose (`m`). | Recorded `(x, y)` coordinate of the last point in `/plan` (matching `home.js`). | Explicitly listed as an unapproved calculated value ("distance to goal") in `C-021`. | 
| **Alert Card Counts & Pin Badges** | Live totals on `Safety`, `Warnings`, and `Errors` cards; numeric pills on clustered pins; summary counts in overlay headers. | Live recorded `OK` / `INHIBIT` status on `Safety`; `Shown` / `Hidden` toggle state on `Warnings` / `Errors`; stacked shadow triangle on overlapping pins. | Explicitly listed as an unapproved calculated value ("event counts") in `C-021`. | 
| **Fault `STARTED`, `DURATION`, `EXPECTED`, & `Hz`** | Bag-relative start time (`mm:ss.s`), live-ticking active duration (`s`), hardcoded expected states (`OK`, `ok=true`), and rate columns from Figma. | Recorded `STATUS`, wall-clock `TIME`, `TOPIC`, and `RECORDED STATE` only. | Durations and hardcoded thresholds are derived; computing topic `Hz` in the browser is also technically invalid because the WebSocket bridge throttles high-rate topics (e.g., `/mtx/odom` at 10 Hz, cameras at 2 fps). | 

### Technical Risk of Browser-Side Rate & Age Calculations

Even if the team approves certain UI-level derivations (such as distance traveled or event counts), **topic frequency (`Hz`), message staleness, and fault thresholds must not be computed in `map.js`**. Because `bridge/topics.py` throttles topics before forwarding them over WebSockets (and omits raw high-rate streams like `/ouster/points` and `/ouster/imu`), browser-side timers measure bridge send rates rather than actual vehicle sensor health. As noted in Section 7 of `Frontend_Data_Guide_v1.md`, accurate per-topic `Hz`, last-message age, and threshold checks need to come from the bridge itself.

## 4. Future Implementation

The following items are deferred pending cross-team module work and bridge updates:

### 4.1 Parity with Dedicated Faults & Logs Pages

The **Faults** (`Implementation/dashboard/js/pages/faults.js`, owner: Caleb) and **Logs** (`Implementation/dashboard/js/pages/logs.js`, owner: Chuck) modules are still being built. Once both pages, and any planned bridge-level fault rate/threshold fields, are finalized, the Map page's pin-click pop-up overlays should be updated to match:

* **Visual styling:** Align table layout, severity pills/badges (`CRIT`, `WARN`, `SAFETY`, `INFO`), and row highlighting with the final `faults.js` and `logs.js` implementations.

* **Column schema & data fields:** Match the exact columns and field formatting used by the full Faults and Logs views (including bridge-provided topic rates, staleness metrics, or threshold comparisons when available) so clicking a pin on the Map acts as a spatially filtered subset of those pages.

### 4.2 Bridge Topic Support for Pre-Planned Paths & Waypoints

In `hopefully_fixed`, autonomy was dispatched in `FollowPath` mode, which skips the global planner and leaves `/plan` empty. The full 3-waypoint mission (`(38.1, -1.4)`, `(38.0, 8.2)`, `(16.5, 8.3)` m in `odom`) is recorded in the bag, but not yet forwarded by the WebSocket bridge.

To support pre-planned paths and waypoint pins on the Map page, the following topics need to be added to `Implementation/bridge/topics.py` (with `String` imported from `std_msgs.msg`) and replayed by the Podman pod:

```
"/mtx/mission/waypoints": dict(type=Path, mode="all", fields=path),
"/mtx/mission/events": dict(type=String, mode="all", fields=lambda m: {"data": m.data}),


```

**Additional bridge & front-end integration considerations:**

* **Latched QoS & connect-time caching:** `/mtx/mission/waypoints` is published with latched (`TRANSIENT_LOCAL`) durability, so `bridge.py` should ensure its subscriber QoS receives latched messages and caches the latest mission waypoints/events in connect-time history for clients joining mid-run (after the 29.5 s dispatch mark).

* **Pre-planned path & waypoint rendering in `map.js`:** Once streamed, `map.js` can resolve the planned route from `/plan` (planner mode) with automatic fallback to `[missionStart, ...waypoints]` from `/mtx/mission/waypoints` and `goal_sent` on `/mtx/mission/events`, render numbered waypoint pins (`WP 1`, `WP 2`, `WP 3 (GOAL)`), and allow cycling focus across waypoints from the left rail.

### 4.3 Team Review of Selective Derived Metrics

During team review, confirm whether any lightweight spatial derivations, such as `Traveled` distance, remaining `Waypoint` distance, the `Run Progress` bar, or left-rail alert counts, should be approved as documented exceptions to `C-021`. The derived-metrics implementation has already been prototyped and can be selectively re-enabled if approved.