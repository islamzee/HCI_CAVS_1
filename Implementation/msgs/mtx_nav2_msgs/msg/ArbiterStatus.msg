# State of the manual / autonomy command arbiter.

std_msgs/Header header

uint8 MODE_MANUAL=0      # joystick passthrough (silence when the joystick is idle or stale)
uint8 MODE_AUTONOMY=1    # autonomy requested; see autonomy_active for whether commands flow
uint8 MODE_ESTOP=2       # software e-stop latched; nothing is forwarded
uint8 mode

bool autonomy_requested  # operator asked for autonomy via the set_autonomy service
bool autonomy_active     # autonomy commands are currently being forwarded to the bridge
bool estop               # software e-stop latched
bool joy_fresh           # a /joy message arrived within joy_timeout
bool autonomy_cmd_fresh  # an autonomy velocity arrived within autonomy_cmd_timeout

string active_source     # DriveCommand.source currently being emitted, or "" for silence
string[] inhibit_reasons # why autonomy is not active, if requested
