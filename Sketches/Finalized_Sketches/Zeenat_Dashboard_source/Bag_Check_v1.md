# ROS bag check — autonomy_demo_0

Author: Zeenat Islam
Bag: Dataset/autonomy_demo/autonomy_demo_0.mcap · ROS 2 Jazzy · 1 file · 72.1 s · 124,845 messages (matches metadata.yaml)
Recorded: Fri 11 Sep 2026, 11:45:48–11:47:00 CDT
Reference: "Data Available to You" list in 0_CAVS-Slide.pdf

## Checked against the course slide

| Slide item | In the bag | Status |
|---|---|---|
| Google Earth / Maps imagery | No GPS (no NavSatFix topic), no `map` or `earth` frame. TF tree is only odom → base_link → sensors. Positions are metres from the start point. | Missing |
| Vehicle position | /mtx/odom and /dlio/odom_node/odom, 100 Hz, frame odom | Present |
| Mission waypoints | /goal_pose has 0 messages. The NavigateThroughPoses goal (2 waypoints) is not recorded; only the /rosout line and the final goal (14.5, −12.3) at the end of /plan. Waypoint 1 cannot be recovered. | Missing |
| Global path | /plan, 19 messages, every ~3 s, frame odom | Present |
| Local path | No /local_plan topic. Closest: /received_global_plan (controller's trimmed plan, frame base_link, 15.6 Hz), /lookahead_point, /lookahead_collision_arc | Partial |
| Occupancy grid | /local_costmap/costmap (150 × 150, 0.2 m, 1.7 Hz) and /global_costmap/costmap (200 × 200, 0.5 m). /map is a point cloud (DLIO keyframes), not a grid. | Present |
| Point cloud | /ouster/points 10 Hz, 6.3 MB per scan; /dlio/odom_node/pointcloud/deskewed | Present |
| Camera | 3 cameras, 2048 × 1536 mono8, ~19 Hz. Every frame sampled on all 3 cameras is saturated white (mean 255). camera_info is empty (0 × 0, no calibration). Cameras have no TF frames. Image time stamps use the camera's own clock, not system time. | Present but unusable |
| System status: topics publishing, rate | Can be computed from message timing only. No rate or statistics topic is recorded. | Partial |
| System status: processing nodes | /bond heartbeats for 6 Nav2 nodes (bt_navigator, controller_server, planner_server, behavior_server, velocity_smoother, collision_monitor). All lifecycle transition_event topics have 0 messages. /diagnostics covers only mtx_nav2/drive_bridge and one Nav2 Health status. No status for camera or LiDAR driver nodes. | Partial |
| Command and control | /mtx/estop, /mtx/arbiter_status, /mtx/drive_command present | Present |

## Injected faults (slide: GPS dropout, LiDAR dropout, camera lag)

| Fault | Finding | Status |
|---|---|---|
| GPS dropout | No GPS data at all, so a dropout cannot be shown | Missing |
| LiDAR dropout | /ouster/points longest gap 143 ms (one missed scan). /ouster/reflec_image longest gap 200 ms. No dropout. | Not found |
| Camera lag | Camera 2 only: frame gaps of 265 ms (11:46:06) and 170 ms (11:46:53), also seen in the camera's own stamps, so frames were lost at the camera. Camera 2 delivery delay rises in steps from ~0 to ~65 ms (about 20 s, 40 s and 65 s into the run). Cameras 0 and 1: no gaps, delay within ~10 ms. | Weak, Camera 2 only |

## Empty topics (0 messages)
/goal_pose, /initialpose, /clicked_point, /curvature_lookahead_point, /parameter_events, /events/write_split, all 11 lifecycle transition_event topics, all 8 costmap *_updates topics.

## Questions for CAVS
- Is there a newer bag with the injected GPS dropout, LiDAR dropout and camera lag?
- Can GPS (NavSatFix) be recorded, or the start point's latitude, longitude and heading supplied, so the route can sit on satellite imagery?
- Are the saturated camera images expected? Can a bag with usable images and camera_info be provided?
- Can the mission waypoints be recorded (for example /goal_pose or the NavigateThroughPoses goal)?
