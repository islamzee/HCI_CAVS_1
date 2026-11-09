# Output of the velocity filter: whether autonomous velocity is allowed through, and why not.

std_msgs/Header header

bool ok                  # true when the last command was forwarded
string[] inhibit_reasons # empty when ok

# Ages are measured against the node clock at evaluation time. Negative = not yet received.
float64 cmd_age_s
float64 odom_age_s
float64 tf_age_s
float64 lidar_age_s

# |now - odom.header.stamp| at the last odometry message. A large value means the sensor
# stack is stamping in a different clock domain (e.g. Ouster TIME_FROM_INTERNAL_OSC).
float64 clock_offset_s
