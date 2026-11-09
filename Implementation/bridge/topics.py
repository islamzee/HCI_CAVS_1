"""Topics the dashboard uses, how each is sent to the browser, and which recorded fields are kept.
Author: Zeenat Islam

Single source of truth: the player replays only these topics (`python3 topics.py` prints them),
and the bridge subscribes to them.

Only recorded fields are copied (no derived or calculated values, C-021).
Images and occupancy grids are re-encoded (JPEG / lossless PNG) so they fit the browser data budget.

Send modes
  "all"       every message is forwarded (low-rate, event-like topics)
  "throttle"  latest message only, at most `hz` per second; if `key` is given, a message whose key
              differs from the last one sent goes out immediately (state changes are never lost)
"""
from builtin_interfaces.msg import Time
from diagnostic_msgs.msg import DiagnosticArray
from geometry_msgs.msg import PolygonStamped, TwistStamped
from nav_msgs.msg import Odometry, OccupancyGrid, Path
from nav2_msgs.msg import CollisionMonitorState
from rcl_interfaces.msg import Log
from std_msgs.msg import Bool
from flir_camera_msgs.msg import ImageMetaData
from mtx_nav2_msgs.msg import ArbiterStatus, DriveCommand, SafetyStatus
from ouster_sensor_msgs.msg import Telemetry


def stamp(t: Time):
    return t.sec + t.nanosec * 1e-9


def hdr(m):
    return {"stamp": stamp(m.header.stamp), "frame_id": m.header.frame_id}


def twist_stamped(m):
    return {**hdr(m), "linear_x": m.twist.linear.x, "linear_y": m.twist.linear.y, "angular_z": m.twist.angular.z}


def polygon(m):
    return {**hdr(m), "points": [[p.x, p.y] for p in m.polygon.points]}


def path(m):
    return {**hdr(m), "poses": [[p.pose.position.x, p.pose.position.y] for p in m.poses]}


def byte_val(b):
    """diagnostic_msgs 'byte' fields arrive as bytes of length 1."""
    return b[0] if isinstance(b, (bytes, bytearray)) else int(b)


# Nodes running in the pod itself; their /rosout lines are not recorded data
LIVE_NODES = ("cavs_ws_bridge", "rosbag2_player")

TOPICS = {
    # --- vehicle state / safety -------------------------------------------------------------
    "/mtx/arbiter_status": dict(type=ArbiterStatus, mode="all", fields=lambda m: {
        **hdr(m), "mode": m.mode, "autonomy_requested": m.autonomy_requested,
        "autonomy_active": m.autonomy_active, "estop": m.estop, "joy_fresh": m.joy_fresh,
        "autonomy_cmd_fresh": m.autonomy_cmd_fresh, "active_source": m.active_source,
        "inhibit_reasons": list(m.inhibit_reasons)}),
    "/mtx/velocity_filter/status": dict(type=SafetyStatus, mode="throttle", hz=5,
        key=lambda m: (m.ok, tuple(m.inhibit_reasons)), fields=lambda m: {
        **hdr(m), "ok": m.ok, "inhibit_reasons": list(m.inhibit_reasons), "cmd_age_s": m.cmd_age_s,
        "odom_age_s": m.odom_age_s, "tf_age_s": m.tf_age_s, "lidar_age_s": m.lidar_age_s,
        "clock_offset_s": m.clock_offset_s}),
    "/mtx/estop": dict(type=Bool, mode="all", fields=lambda m: {"data": m.data}),
    "/mtx/nav/collision_monitor_state": dict(type=CollisionMonitorState, mode="all", fields=lambda m: {
        "action_type": m.action_type, "polygon_name": m.polygon_name}),
    "/diagnostics": dict(type=DiagnosticArray, mode="all", fields=lambda m: {
        **hdr(m), "status": [{"name": s.name, "level": byte_val(s.level), "message": s.message,
                              "hardware_id": s.hardware_id,
                              "values": {kv.key: kv.value for kv in s.values}} for s in m.status]}),
    "/rosout": dict(type=Log, mode="all", skip=lambda m: m.name in LIVE_NODES, fields=lambda m: {
        "stamp": stamp(m.stamp), "level": byte_val(m.level), "name": m.name, "msg": m.msg}),

    # --- motion ------------------------------------------------------------------------------
    "/mtx/odom": dict(type=Odometry, mode="throttle", hz=10, fields=lambda m: {
        **hdr(m), "x": m.pose.pose.position.x, "y": m.pose.pose.position.y,
        "qz": m.pose.pose.orientation.z, "qw": m.pose.pose.orientation.w,
        "linear_x": m.twist.twist.linear.x, "angular_z": m.twist.twist.angular.z}),
    "/mtx/cmd_vel_autonomy": dict(type=TwistStamped, mode="throttle", hz=10, fields=twist_stamped),
    "/mtx/drive_command": dict(type=DriveCommand, mode="throttle", hz=10, key=lambda m: m.source,
        fields=lambda m: {**hdr(m), "x": m.x, "y": m.y, "z": m.z, "source": m.source}),

    # --- navigation / map --------------------------------------------------------------------
    "/plan": dict(type=Path, mode="all", fields=path),
    "/dlio/odom_node/path": dict(type=Path, mode="throttle", hz=0.5, fields=path),
    "/local_costmap/published_footprint": dict(type=PolygonStamped, mode="throttle", hz=2, fields=polygon),
    "/mtx/nav/stop_zone": dict(type=PolygonStamped, mode="throttle", hz=1, fields=polygon),
    "/mtx/nav/slowdown_zone": dict(type=PolygonStamped, mode="throttle", hz=1, fields=polygon),
    "/local_costmap/costmap": dict(type=OccupancyGrid, mode="grid"),
    "/local_costmap/voxel_layer": dict(type=OccupancyGrid, mode="grid"),
    "/global_costmap/costmap": dict(type=OccupancyGrid, mode="grid"),

    # --- sensors -----------------------------------------------------------------------------
    **{f"/cam_{c}/meta": dict(type=ImageMetaData, mode="throttle", hz=1, fields=lambda m: {
        **hdr(m), "camera_time": m.camera_time, "brightness": m.brightness,
        "exposure_time": m.exposure_time, "max_exposure_time": m.max_exposure_time, "gain": m.gain})
       for c in range(3)},
    "/ouster/telemetry": dict(type=Telemetry, mode="throttle", hz=1,
        key=lambda m: (m.thermal_shutdown, m.shot_limiting), fields=lambda m: {
        **hdr(m), "thermal_shutdown": m.thermal_shutdown, "shot_limiting": m.shot_limiting,
        "countdown_thermal_shutdown": m.countdown_thermal_shutdown,
        "countdown_shot_limiting": m.countdown_shot_limiting}),
}

CAMERAS = [f"/cam_{c}/image_raw" for c in range(3)]   # subscribed on demand (only cameras a client is viewing)
DEFAULT_CAMERA = 2                                    # C-013
CAMERA_HZ = dict(default=2.0, min=0.2, max=10.0)      # C-011: viewer can change it
CAMERA_WIDTH = 640                                    # px sent to the browser (recorded frames are 2048 x 1536)

PLAYER_TOPICS = list(TOPICS) + CAMERAS

if __name__ == "__main__":
    print(" ".join(PLAYER_TOPICS))
