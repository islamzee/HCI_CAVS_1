To: Daniel Carruth <DWC2@CAVS.MSSTATE.EDU>
Cc: Christopher Hudson <CHUDSON@CSE.MSSTATE.EDU>
Subject: CAVS-1 HCI project: questions about the autonomy_demo_0 bag

Dear Dr. Carruth,

Our team (CAVS-1) has started building the supervisory interface on the provided ROS 2 bag, autonomy_demo_0 (recorded 11 Sep 2026, 72 s). While checking it against the project brief, we found a few gaps that affect our design, and we would appreciate your guidance.

1. Injected faults. The brief mentions GPS dropout, LiDAR dropout and camera lag. In this bag we see no GPS topic, no LiDAR dropout (longest gap 143 ms), and only small frame gaps on Camera 2. Is there a newer version of the bag with the faults included?

2. GPS / map position. There is no GPS (NavSatFix) data, so positions are only relative to the start point. Could GPS be included, or could you share the start point's latitude, longitude and heading so we can show the route on satellite imagery?

3. Camera images. All frames from the three cameras are fully white, and camera_info is empty. Is this expected, and is a bag with usable images available?

4. Mission waypoints. /goal_pose is empty and the two waypoints sent at the start of the run are not recorded. Could the waypoints be recorded, or shared separately?

A one-page summary of what we checked is attached. We are happy to continue with the current bag in the meantime and swap in a new one when it is ready.

Thank you for your time.

Best regards,
Zeenat Islam
On behalf of Team CAVS-1 (Nathan Hester, Chuck, Caleb, Zeenat Islam)
Mississippi State University
