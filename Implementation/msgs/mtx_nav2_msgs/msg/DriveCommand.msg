# One drive command in the MTX drive-by-wire controller's native units.
#
# Produced ONLY by the command arbiter. Consumed ONLY by the drive bridge,
# which packs x/y/z as three little-endian int16 into CAN ID 0x050.
#
# Sign conventions are the vehicle's, not ROS's:
#   +x  = turn right while moving
#   +y  = forward
#   +z  = pivot right (only honoured by the vehicle when stationary)

std_msgs/Header header

int16 x          # steer counts,    -1000 .. 1000
int16 y          # throttle counts, -1000 .. 1000
int16 z          # pivot counts,     -800 ..  800 (manual passthrough may reach +-1000)

string source    # one of the SOURCE_* constants
string SOURCE_MANUAL=manual
string SOURCE_AUTONOMY=autonomy
string SOURCE_STOP=stop
