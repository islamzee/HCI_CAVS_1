# Dashboard sketch — notes

Author: Zeenat Islam

Current version: Zeenat_Dashboard_Sketch_v1.pdf (in Sketches/Finalized_Sketches)

## 1 Oct 2026 — v1
- Purpose: client-facing sketches of the Dashboard page (Zeenat's assignment in Finalized-list-of-sketches.txt).
- Use case: post-run review of a completed autonomy run. Data source: offline replay of the recorded bag (no live ROS connection).
- Pages: cover, 1 run overview, 2 event review, 3 fault drill-down, 4 navigation to Path Planning (Nathan), Faults and Sensors (Caleb), Run Logs (Chuck).
- All values come from Dataset/autonomy_demo/autonomy_demo_0.mcap: 72.1 s run, 29.2 m driven, max 2.2 m/s, autonomy 8.2 to 64.7 s, operator STOP and software e-stop at 64.7 s, e-stop cleared at 67.5 s, goal (14.5, -12.3) not reached.
- Sensor rates: LiDAR 10.0 Hz, cameras 19.1 / 19.1 / 18.9 Hz, DLIO odometry 99.9 Hz, IMU 99.8 Hz. No GPS topic in this bag.
- Camera 2 has two frame gaps above 158 ms (265 ms at 17.9 s, 170 ms at 65.8 s). No LiDAR dropouts were found. The injected GPS / LiDAR dropout faults described in the course slide do not appear in this copy of the bag.
- data.json holds the odometry trace and final plan extracted from the bag; make_dashboard_sketch.py regenerates the HTML.

## Client notes (received 1 Oct 2026)
- C-001 No tablets. The interface is hosted on a CAVS server.
- C-002 No vehicle control from the interface. A person is always in the vehicle and takes control.
- C-003 Three cameras are the only sensors in scope.
- C-004 No 3D mapping. Streaming image data uses too much bandwidth.
- C-005 The team manages the switch from automated to manual driving: stop the vehicle when any listed trigger fires.
- C-006 Any approach is acceptable, but it has to be efficient.
- C-007 CAVS can host the interface for testing with 3 days' notice.

## 1 Oct 2026 — v2
- Reframed from a tablet post-run review to a server-hosted supervisory monitor (desktop browser) with automatic stop triggers, plus post-run review (C-001, C-005).
- No drive controls (C-002). Sensor health reduced to the 3 cameras plus localization for the 2D map (C-003). 2D route only, camera previews at 1 frame/s instead of video (C-004, C-006).
- Trigger list T1–T7. STOP triggers publish /mtx/estop = true once from a trigger monitor node beside the vehicle stack. ALERT triggers only flag.
- Replaying autonomy_demo_0 against the list: T1 fires at 17.9 s (Camera 2, 265 ms gap), T2 at 23.6 s (Camera 2 at 14 frames in 1 s), T1 again at 65.8 s. T3, T4, T5 never fire (max camera gap 265 ms, no odometry gaps, autonomy_cmd_fresh stays true during autonomy). The actual run was stopped by the operator at 64.7 s.
- Measured sizes: each camera frame 2048 x 1536 mono8 = 3.1 MB, each Ouster point cloud 6.3 MB. Raw data ≈ 179 MB/s cameras + 63 MB/s LiDAR. Planned browser feed ≈ 50 kB/s.
- Observation: every camera frame checked in this bag is saturated white (pixel values 247–255). A blank-image trigger would fire for the whole run; confirm with CAVS whether the camera images in the provided bag are usable.
- Pages: cover, 1 live normal, 2 live trigger fired, 3 run review, 4 trigger list, 5 data budget, 6 navigation.
- To test on the CAVS server, request hosting at least 3 days ahead (C-007).

## Client / team note (received 1 Oct 2026)
- C-008 The ROS bag is the backend, and the session should mock a live session: the UI shows the bag's own recording date and time as the current time.

## 1 Oct 2026 — v3
- Live clock in the top bar shows the bag's recorded wall-clock time, advancing with playback: Fri 11 Sep 2026, 11:45:48 to 11:47:00 CDT (bag start epoch 1789145148.16, UTC-5) (C-008).
- Event log, trigger states, trigger table, STOP banner, timeline axis and the review comparison all use clock time (STOP trigger at 11:46:06, operator STOP at 11:46:52).
- Top bar reads "source: bag playback". Data-budget page shows ROS 2 bag playback standing in for the vehicle.

## Client note (received 2 Oct 2026)
- C-009 Do not stream raw LiDAR data to the web interface (computational overhead). LiDAR may be shown as a processed image or lightweight representation, such as an occupancy grid or 2D image, if processing and display overhead stays low.

## 2 Oct 2026 — v4
- Live dashboard: new LiDAR panel showing the occupancy grid centred on the vehicle, with a Grid / Panorama switch (C-009).
- New page 4, LiDAR view: occupancy grid plus the 360° LiDAR reflectivity panorama, with how each view is produced.
- Occupancy grid = /local_costmap/costmap, already produced by Nav2 from the LiDAR: 150 x 150 cells, 0.2 m (30 x 30 m), 1.69 updates/s, max gap 0.61 s. 22.5 kB per message; PNG 0.3–1.3 kB; encode 0.17 ms.
- Panorama = /ouster/reflec_image, already produced by the Ouster driver: 1024 x 128 mono16, 9.9 Hz. JPEG ≈ 22–25 kB; encode 0.5 ms. Sent at 1 frame/s only while the panel is open.
- Raw /ouster/points (6.3 MB per scan, 10 Hz) is never sent to the browser.
- Feed health now lists LiDAR (/ouster/points 10.0 Hz, no dropouts) and the LiDAR grid (1.7 Hz).
- Data budget: ≈ 50–75 kB/s to the browser.
- The LiDAR panorama shows real scenery (trees, a building, ground), unlike the camera frames in this bag, which are saturated white.
- lidar_preview/ holds the grid and panorama images rendered from the bag and their measurements (info.json); the v4 script embeds them.

## 6 Oct 2026 — bag check
- Verified autonomy_demo_0 against the slide's "Data Available to You" list and the injected-fault list. Full results in Bag_Check_v1.md.
- Missing: GPS / map imagery reference, mission waypoints, usable camera images and calibration, GPS and LiDAR dropout faults. Partial: local path, system status. Camera lag is weak and on Camera 2 only.

## 6 Oct 2026 — inspection scripts
- All scripts used to inspect the bag are in bag_inspection/ (bag_reader.py plus 01–08), with README.md. All eight were rerun and reproduce the reported numbers. Output goes to bag_inspection/output/.
- 07_trigger_replay.py reports T1 at the moment the 158 ms limit is crossed: 18.11 s (11:46:06.3 CDT). The sketches show the gap start, 17.9 s (11:46:06.0).
- Moved bag_inspection/ to Dataset/bag_inspection/ (6 Oct 2026). bag_reader.py now finds the bag from the new location; scripts rerun and confirmed.

## 6 Oct 2026 — team sketch review
- Reviewed the team's dashboard sketch (Home page with Drive status, Front camera perception, Navigation/costmap, Systems health, LiDAR top view, Planned path, Upcoming waypoints) against the bag and latency. Full table in Team_Sketch_Review_v1.md.
- New useful topic found: /mtx/velocity_filter/status (SafetyStatus, 20 Hz) with ok flag, inhibit reasons and cmd/odom/tf/lidar data ages.

## 6 Oct 2026 — revised team sketch
- Team_Dashboard_Revised_v1.pdf: the team's Home layout kept, with every panel filled from autonomy_demo_0. Page 1 autonomy running (11:46:02), page 2 T1 stop fired (11:46:06.2), page 3 list of changes.
- Waypoint 1 inferred at about (27.6, 1.6) from the sharp turn in /plan (the plan runs start → WP 1 → goal). Team_Sketch_Review_v1.md updated.
- Panel data extracted to Zeenat_Dashboard_source/team_sketch/ (state.json, local and global costmap PNGs at 14.3 s and 18.1 s); generator make_team_dashboard_sketch_v1.py.

## 6 Oct 2026 — revised team sketch v2
- Instruction: keep nothing that needs to be calculated. Only fields recorded in the bag are shown.
- Header: Safety filter (/mtx/velocity_filter/status ok), Nav2 and Drive bridge (/diagnostics messages), E-stop (/mtx/estop). Localization and Comms removed.
- Removed as calculated: feed rates and gap labels, inferred waypoint 1, distances, driven-distance total, local path overlay (needs frame transform), automatic stop triggers T1–T7.
- Added from recorded fields: Stop state panel (/mtx/estop, arbiter e-stop and inhibit reasons, collision monitor), WARN/ERROR log panel (/rosout), vehicle footprint (/local_costmap/published_footprint), driven path (/dlio/odom_node/path).
- Page 2 now shows the recorded operator STOP and e-stop at 11:46:52.8.
- New extraction script Dataset/bag_inspection/09_direct_fields.py; data in Zeenat_Dashboard_source/direct/.

## 6 Oct 2026 — team menu sketches review
- Reviewed Map, Sensors, Faults, Past Logs and Log detail sketches. Suggested changes and navigation flow in Team_Menus_Review_v1.md.

## 6 Oct 2026 — LiDAR top view decision
- LiDAR top view uses only recorded grids: /local_costmap/costmap (or /local_costmap/voxel_layer) with /local_costmap/published_footprint. North-up, 30 × 30 m, 1.7 updates/s.
- Not considered: /ouster/scan (needs angle-to-position conversion) and /ouster/points (raw point cloud, ruled out by C-009).

## 6 Oct 2026 — revised team sketch v3
- LiDAR top view switched to the occupancy grid /local_costmap/voxel_layer (0 = free, 100 = occupied; only cells the LiDAR hit). /local_costmap/costmap is a cost map (adds 1–99 safety margin) in the same message format.
- 09_direct_fields.py now also exports the voxel layer. Navigation map still uses /global_costmap/costmap.

## 6 Oct 2026 — Sensors, Faults and Logs sketches
- Team_Pages_Sketch_v1.pdf, same style as Team_Dashboard_Revised_v3, recorded fields only.
- Sensors (11:46:02): 3 camera cards (image size, camera-clock image stamp, exposure, gain from /cam_N/meta); LiDAR occupancy grid (/local_costmap/voxel_layer) and reflectivity image (/ouster/reflec_image, full 16-bit range shown as 8-bit), LiDAR data age, Ouster thermal and shot-limiting flags.
- Faults (11:46:53): state changes (/mtx/estop, safety filter, collision monitor), then /rosout ERROR and WARN, newest first, with Map and Log links. No counts or "ago" times.
- Logs: past runs from metadata.yaml (one bag); run detail = /rosout lines with level, node, message and clock time, filters for level and node.
- Data from Dataset/bag_inspection/10_page_fields.py, copied to Zeenat_Dashboard_source/pages/.
- v2 (6 Oct 2026): Sensors LiDAR view is the occupancy grid only (/local_costmap/voxel_layer with footprint). Reflectivity image removed. LiDAR data age and Ouster thermal / shot-limiting flags kept beside the grid.
- v3 (6 Oct 2026): Sensors page in two columns: cameras stacked vertically on the left (image beside its fields), LiDAR occupancy grid on the right, same height.

## 13 Oct 2026 — ROS bag issues list for Dr. Hudson
- Dr. Hudson asked teams for a list of issues with the 2 ROS bags provided, to fix future bags. Team plans to submit Thursday afternoon before class.
- Draft: Dataset/ROS_Bag_Issues_v1.md. Bag 1 (autonomy_demo_0): 13 issues. Bag 2 section empty: only one bag is in Dataset/.
- v2 (13 Oct 2026): item 1 adds the full GPS check (no GPS message types, no GPS in topics or logs, Ouster NMEA/GPS input off); item 2 adds that odometry has no gap over 29 ms. Bag 2 section still empty (second bag not in Dataset/).
- v3 (13 Oct 2026): same list as Word file, Dataset/ROS_Bag_Issues_v3.docx (landscape, Times New Roman). v2 .md moved to Dataset/_Archive.
- v4 (13 Oct 2026): 'Evidence' column renamed 'Finding'; 'Request for future bags' column removed.
- v5 (13 Oct 2026): built from the edited v4 (title, single 'Bag: autonomy_demo_0' heading, no Prepared by / For / Bag 2). Finding column expanded with counts, rates, times and topic names for all 13 issues. Correction: 9 lifecycle transition_event topics (v4 said 11); 23 of 85 topics have 0 messages.
- v6 (13 Oct 2026): Finding column as bullet points (same content as v5).
- v7 (13 Oct 2026): removed issues 11 (short run with one manual stop) and 12 (large file); Empty topics renumbered 11.

## Client feedback from Checkpoint 1 (notes received 13 Oct 2026, Checkpoint-1/CAVS Notes.pdf)
- C-010 Would be helpful to have a log system and be able to clear it.
- C-011 Ability to configure Hz.
- C-012 Need to work on settings.
- C-013 Prefers buttons, default to camera 2.
- C-014 Keep lighter color scheme or toggle for light mode due to sun.
- C-015 Stick to visuals, vehicle too loud to hear anything from interface.
- C-016 They do have coregistered lidar and camera, render an occupancy grid instead of lidar because of computational intensity.
- C-017 Resolution changes, square meter.
- C-018 There aren't any faults in the current data, they're going to get us a bag with faults in it.
- C-019 Two types of problems, one that cascades or one that stays hidden.
- C-020 Define multiple points (A, B, C) and it calculates intermediate points, but generally just a goal point: starts at 0, 0, goal of about 100, 100.
- C-021 A lot of high level derived information, good but heavy workload; look at the data closer, mostly raw data.

## 20 Oct 2026 — dashboard changes
- Checkpoint-1/Dashboard_Changes_v1.md maps C-010 to C-021 to dashboard changes, what the revised sketches already cover, and what is still to add.
- 20 Oct 2026: Home sketch suggestions in Checkpoint-1/Home_Sketch_Suggestions_v1.md.
- 20 Oct 2026: Home_Sketch_v1 (.pdf, .png) redraws the team Home sketch with the Checkpoint 1 changes (C-010 to C-021): 6 panels, recorded values at 11:46:02, CAM 0/1/2 buttons with CAM 2 default, occupancy grid with cell size and area, event log with Clear, light/dark toggle, no GPS/COMMS/BATTERY. Generator make_home_sketch_v1.py (uses direct/ and pages/).
- v2 (20 Oct 2026): occupancy grid panel gets grid lines every 1 m and bold lines every 5 m; legend lists cell size, line spacing and area.
- v3 (20 Oct 2026): Systems Health keeps status dots only on recorded statuses (safety filter ok flag, Nav2 and drive bridge diagnostics level). Odometry, LiDAR and command ages shown as recorded values with no dot, one decimal (0.4, 5.8, 48.8 ms).
- v4 (20 Oct 2026): light/dark mode switch removed from the header; light theme only.
- 22 Oct 2026: Home_Sketch_v4.svg added for Figma (vector, 1640 × 1064, text outlined as shapes).
- 27 Oct 2026: Figma prototyping. Sensors_v1, Faults_v1, Logs_Past_Runs_v1 and Logs_Run_Detail_v1 exported as SVG (screens from Team_Pages_Sketch_v3, scaled to 1640 wide). Figma_Navigation_Guide_v1.md: frames, hotspots, bottom-bar component, link table, flow start. Map and Settings screens not drawn yet; Sensors/Faults/Logs still in the earlier style.

## 9 Nov 2026 — implementation: bag replay in Podman + websocket bridge
- New folder Implementation/ (README.md there). Podman pod "cavs": cavs-player runs `ros2 bag play --loop` on autonomy_demo_0 (dashboard topics only); cavs-bridge (rclpy) streams recorded fields as JSON on ws://localhost:8765/. Probe page at http://localhost:8765/.
- Custom message packages (mtx_nav2_msgs, flir_camera_msgs, ouster_sensor_msgs) rebuilt from the schemas embedded in the .mcap, so the player can publish them.
- Per-browser camera choice (default CAM 2, C-013) and camera Hz 0.2–10 (C-011). Grids sent as lossless PNG of cell values; colours set in the browser.
- Measured: player keeps real time; 42.8 kB/s to one browser (within the 50–75 kB/s budget); loop and camera switching work. Camera frames white, as recorded (bag issue 3).
- Next: dashboard UI (Home first) connecting to the websocket.

## 9 Nov 2026 — team setup (Windows + macOS)
- Bag removed from the unpushed commit "dataset exploration" (GitHub limit 100 MB/file); file kept on disk. .gitignore (*.mcap, .DS_Store) and .gitattributes (LF for scripts used in Linux containers) added.
- Implementation/cavs-pod.yaml: `podman kube play` pod, same on Windows and macOS; bag mounted from the named volume "cavs-bag".
- .github/workflows/container.yml: builds the image for amd64 + arm64 and publishes to ghcr.io/islamzee/hci_cavs_1/cavs-bag-bridge.
- Implementation/make_slim_bag.sh: Dataset/autonomy_demo_slim = dashboard topics + /ouster/imu + /dlio/odom_node/odom, zstd. 18 GB → 19 MB, message counts identical (saturated camera frames compress to almost nothing). Not in git.
- Repo stays public (decided 9 Nov 2026). Bags only on the team drive, never in the repo or a Release. ghcr.io package to be set public after the first build.
- 9 Nov 2026: Implementation/Frontend_Data_Guide_v1.md for the team (start the data, connect, topics per module, field reference, gaps). Browser helper client/cavs-client.js + client/example.html. Bridge now sends connect-time history (latest event-topic messages + last 200 /rosout lines, then history_end) and a playback restart notice when the bag loops.
- 9 Nov 2026: slim bag Dataset/autonomy_demo_slim committed to the public repo (user's decision; full bag stays ignored). Teammates get it with git pull; no team-drive step.
