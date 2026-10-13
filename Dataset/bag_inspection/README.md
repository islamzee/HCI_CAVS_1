# Bag inspection scripts

Author: Zeenat Islam

Scripts used to inspect `Dataset/autonomy_demo/autonomy_demo_0.mcap`. They read the .mcap directly (no ROS install) and write results to `output/`.

## Setup
```
pip3 install mcap mcap-ros2-support numpy pillow pyyaml
```
Paths are set at the top of `bag_reader.py` (`BAG_PATH`, `OUT_DIR`). By default the bag is found relative to the repository root.

## Scripts

| Script | What it does | Results used in |
|---|---|---|
| bag_reader.py | Shared helper. Reads the MCAP message index once (cached in output/index_cache.pkl), then decodes single messages on demand | all |
| 01_metadata_topics.py | Topic list, types, counts and empty topics from metadata.yaml | Sketches/Finalized_Sketches/Zeenat_Dashboard_source/Bag_Check_v1.md |
| 02_build_index_and_crosscheck.py | Builds the index and checks per-topic counts against metadata.yaml | Sketches/Finalized_Sketches/Zeenat_Dashboard_source/Bag_Check_v1.md |
| 03_rates_and_gaps.py | Rate and longest gap of each sensor stream | sketches v1–v4, Sketches/Finalized_Sketches/Zeenat_Dashboard_source/Bag_Check_v1.md |
| 04_run_events_and_route.py | Route, speed, plans, goal, operator actions, log events; writes output/run.json | sketches (data.json), events and timeline |
| 05_camera_checks.py | Camera size, pixel content, calibration, intervals, 1 s frame counts, delivery delay | trigger list, fault drill-down, Sketches/Finalized_Sketches/Zeenat_Dashboard_source/Bag_Check_v1.md |
| 06_lidar_views.py | Occupancy grid and LiDAR panorama images, sizes, encode times; writes output/lidar_preview/ | sketch v4 LiDAR panel and page 4 |
| 07_trigger_replay.py | Replays triggers T1–T7 over the run | sketches v2–v4 trigger list and review page |
| 09_direct_fields.py | Recorded fields only (no derived values) at chosen playback times; writes output/direct/ | Team_Dashboard_Revised_v2 |
| 10_page_fields.py | Recorded fields for the Sensors, Faults and Logs sketches; writes output/pages/ | Team_Dashboard_Revised (pages) |
| 08_check_against_brief.py | GPS, TF frames, waypoints, local path, /map, diagnostics, bond, LiDAR dropout | Sketches/Finalized_Sketches/Zeenat_Dashboard_source/Bag_Check_v1.md |

Run in order from this folder (Dataset/bag_inspection), for example `python3 02_build_index_and_crosscheck.py`. Building the index takes about a second.

Note: the reader handles uncompressed MCAP chunks only, which is how this bag is stored.
