// E-stop button in the header. Author: Zeenat Islam
//
// NOT CONNECTED TO THE VEHICLE. The dashboard is read-only: the bridge never sends anything to ROS, so the button
// is shown disabled. It is an extra way to stop, never a replacement for the vehicle's own e-stops.
//
// To connect it, CAVS must first say how software requests an e-stop on the MTX (topic or service, message type,
// how it is reset) and approve sending it from the dashboard. Then: a handler for {cmd: "estop"} in the bridge,
// a send method in the client, and CONNECTED = true here. Rules to keep when it is connected:
//   - stopping is one click, with no confirmation (a confirmation delays a stop)
//   - the E-STOP status next to it shows "Latched" only when the vehicle reports it (/mtx/estop or
//     arbiter_status.estop), never just because the button was clicked; until then the button says it was sent
//     and is waiting for the vehicle, and says so if the vehicle does not confirm
//   - no reset from the dashboard; the vehicle is reset with its own procedure

export const CONNECTED = false;

/** Set up the header button (index.html #estopBtn). */
export function mountEstop(btn) {
  if (!CONNECTED) {
    btn.disabled = true;
    btn.classList.add("off");
    btn.title = "Not connected to the vehicle yet. Use the vehicle's own e-stop.";
    btn.setAttribute("aria-label", "E-stop, not connected to the vehicle");
  }
}
