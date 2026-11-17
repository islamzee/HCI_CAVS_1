# CAVS-1 dashboard (shared app)

Author: Zeenat Islam

Plain HTML/CSS/JavaScript: no build step and nothing to install. It runs in the browser and gets live data from the bag bridge.

**Open it:** start the pod (`start-windows.bat`, or `pod.sh up` on macOS), then go to **http://localhost:8765/dashboard/**.
The pod serves this folder straight from your copy of the repo, so after editing a file just reload the page.

| Page | Owner | File | Status |
|---|---|---|---|
| Home | Zeenat | `js/pages/home.js` | built (Home_Sketch_v4 / Figma Dashboard-V2) |
| Map | Nathan | `js/pages/map.js` | placeholder |
| Sensors | Caleb | `js/pages/sensors.js` | placeholder |
| Logs | Chuck | `js/pages/logs.js` | placeholder |
| Faults | Caleb | `js/pages/faults.js` | placeholder |
| Settings | (unassigned) | `js/pages/settings.js` | started: occupancy grid view (1–15 m). Add settings in `js/settings.js` |

Each placeholder page lists the topics that module needs, with live values, so you can see your data right away.

## Building your page

Replace your page file with a module of this shape (see `js/pages/home.js` for a full example):

```js
import { clock, num } from "../lib/format.js";
import { onEvents } from "../state.js";            // only if you use the shared event log

export default {
  title: "Map",
  mount(root, { cavs, state }) {
    root.innerHTML = `<section class="panel"><h3>MAP</h3><div class="kv"><span>Speed</span><b id="v">—</b></div></section>`;
    const off = cavs.on("/mtx/odom", (d) => (root.querySelector("#v").textContent = num(d.linear_x, 2, "m/s")));
    return () => off();                              // called when the user leaves the page
  },
};
```

Rules:
- **Use the shared connection** (`cavs` passed to `mount`). Don't create another `CavsClient`.
- **Unsubscribe in the cleanup function.** Every `cavs.on(...)` returns an "off" function.
- **Only edit your own page file**, plus new files you add (e.g. `js/pages/map/…`, `css/map.css`). For changes to the shell, `state.js` or the shared helpers, ask Zeenat.
- **Show recorded values only** (C-021). Formatting (units, rounding, clock time, colours by recorded level) is fine. Calculated values need team agreement first.
- **Light theme only** (C-014), visual alerts only (C-015).

## What's shared

| File | What you get |
|---|---|
| `js/state.js` | `cavs` (the connection) and `state`: `diagnostics` by name, `estop`, `bagTime` (bag clock), `bag` (name, start, duration), `events` (event log, newest first). `onEvents(fn)` and `clearEvents()` for the log. |
| `js/settings.js` | Shared settings, saved per browser: `getSetting(key)`, `setSetting(key, value)`, `onSettingChange(fn)`. Add a setting to `SETTINGS` and it appears on the Settings page. |
| `js/lib/format.js` | `clock(stamp)` → "11:46:02" (CDT), `dateLabel(stamp)`, `num(v, digits, unit)`, `ms(seconds)`, level names (`ROSOUT_LEVEL`, `DIAG_LEVEL`, `ARBITER_MODE`, `COLLISION_ACTION`), `escapeHtml` |
| `js/lib/draw.js` | `gridCanvas(msg)` (costmap → canvas), `fitView`, `bounds`, `fitCanvas`, `polyline`, `scaleBar`, `redrawer`, `COLORS`. The Home navigation and occupancy-grid panels use them. |
| `css/app.css` | `.panel` (with `h3` header and `.actions`), `.kv` rows, `.btn` / `.btn.on`, `.dot.ok/.warn/.bad`, `.ok/.warn/.bad/.mute` text colours, `.empty`, `.mono` |
| `../client/cavs-client.js` | `cameraSrc(d)`, `decodeGrid(d)`, `yawFromQuaternion(qz, qw)` |

Topics and fields: [../Frontend_Data_Guide_v1.md](../Frontend_Data_Guide_v1.md).

## Other ways to open it
- Data from a teammate's pod: `http://localhost:8765/dashboard/?ws=ws://<their-ip>:8765/`
- With VS Code Live Server or any other static server: open `Implementation/` as the site root and go to `/dashboard/`. The page connects to `ws://localhost:8765/` by default.

## Layout
- The screen is designed for a desktop monitor (min 1280 × 760, like the 1640 × 1064 sketches).
- Header and bottom nav come from `index.html` and `js/app.js`. Pages render into `<main id="page">`.
- The alert summary at the bottom right shows recorded flags only, worst first: e-stop latched, then safety filter inhibit, then any diagnostics level above OK.
