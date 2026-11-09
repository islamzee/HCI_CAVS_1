# A classic CAN frame as carried inside the 36-byte Ethernet-gateway envelope.
# Published by the drive bridge for every frame it sends (or would have sent in dry-run),
# and for every frame received from the gateway when RX is enabled.

std_msgs/Header header

uint32 id        # 11-bit CAN arbitration ID (0x050 for MTX drive commands)
uint8 dlc        # data length, 0..8
uint8[8] data    # payload, zero padded
uint8 channel    # gateway channel byte (offset 20 of the envelope)

bool dry_run     # true if this frame was NOT actually transmitted
string hex       # the full 36-byte envelope as space-separated hex, for humans
