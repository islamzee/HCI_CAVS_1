# Revised team dashboard sketch (Home page), filled with values from autonomy_demo_0
# Author: Zeenat Islam
import json, math, base64, datetime as dt, os

DATA_DIR = "team_sketch"          # state.json + costmap PNGs from Dataset/bag_inspection/output/team_sketch
OUT_HTML = "team_dashboard_v1.html"
BAG_START = 1789145148.161676535  # first message, epoch s
TZ = dt.timezone(dt.timedelta(hours=-5))
GOAL = (14.5, -12.3)              # end of /plan
WP1 = (27.62, 1.59)               # sharp turn in /plan = first waypoint (inferred)
ODOM = json.load(open("data.json"))["odom"]   # [t, x, y, speed]
S = json.load(open(os.path.join(DATA_DIR, "state.json")))

INK, MUTE, LINE, BG = "#1f2328", "#6b7280", "#d7dade", "#f4f5f7"
OK, WARN, BAD, OFF, ACC = "#2f9e44", "#e0a100", "#d64545", "#a0a4aa", "#2f6fdb"

def clk(t, ms=False):
    d = dt.datetime.fromtimestamp(BAG_START + t, TZ)
    return d.strftime("%H:%M:%S") + (f".{d.microsecond // 100000}" if ms else "")
def img(name):
    return "data:image/png;base64," + base64.b64encode(open(os.path.join(DATA_DIR, name), "rb").read()).decode()
def dot(c): return f'<span class="dot" style="background:{c}"></span>'

def header(t, safety_ok=True):
    d = dt.datetime.fromtimestamp(BAG_START + t, TZ)
    sc = OK if safety_ok else BAD
    return f'''<div class="hdr"><div class="brand"><b>CAVS</b><span>Center for Advanced<br>Vehicular Systems</span></div>
<div class="title">Autonomous Vehicle Testing<small>{dot(BAD)} LIVE · bag playback · autonomy_demo_0</small></div>
<div class="hs"><span>LOCALIZATION</span><b style="color:{OK}">OK</b></div>
<div class="hs"><span>COMMS</span><b style="color:{OK}">0.1 s</b></div>
<div class="hs"><span>SAFETY</span><b style="color:{sc}">{"OK" if safety_ok else "STOP"}</b></div>
<div class="clock">{clk(t)}<small>{d.strftime("%b %d, %Y")} CDT</small></div></div>'''

def drive(t, o, stopped):
    x, y, _ = o["pose"]
    if stopped:
        box = f'<div class="mode" style="background:#fdecec;border-color:{BAD}"><b style="color:{BAD}">STOPPED</b><span>T1 camera frame gap<br>Safety driver in control</span></div>'
    else:
        box = f'<div class="mode"><b>AUTONOMOUS</b><span>Navigating to Waypoint 1 of 2</span></div>'
    rows = [("Speed", f'{0 if stopped else o["speed"]:.1f} m/s'), ("Turn rate (cmd)", "0.0 °/s" if stopped else f'{math.degrees(o["cmd"][1]):+.1f} °/s'),
            ("Command source", "none" if stopped else o["arb"][1]), ("Command age", "stop latched" if stopped else f'{o["safety"]["cmd"]*1000:.0f} ms')]
    r = "".join(f'<div class="kv"><span>{a}</span><b>{b}</b></div>' for a, b in rows)
    return f'<div class="p drive"><h3>DRIVE STATUS</h3>{box}{r}</div>'

def cams(stopped):
    out = []
    for i in range(3):
        bad = stopped and i == 2
        lab = f'{dot(BAD)} gap 265 ms' if bad else f'{dot(OK)} 19 Hz'
        out.append(f'<div class="cam{" bad" if bad else ""}"><svg width="100%" height="100%"><line x1="0" y1="0" x2="100%" y2="100%" stroke="{LINE}"/><line x1="100%" y1="0" x2="0" y2="100%" stroke="{LINE}"/></svg><span class="cl">CAM {i}</span><span class="cr">{lab}</span></div>')
    return f'''<div class="p camp"><h3>CAMERAS<span class="tabs"><b>Camera</b><span>LiDAR</span><span>Faults</span></span></h3>
<div class="camrow">{"".join(out)}</div><div class="foot">Previews refresh once per second · 320 × 240 JPEG</div></div>'''

def nav(t, o):
    g = o["global"]; x0, x1, y0, y1 = -3, 32, -15, 5
    W, H = 300, (246 if t > 18 else 268)
    sx = W / (x1 - x0); sy = H / (y1 - y0); s = min(sx, sy)
    def P(x, y): return ((x - x0) * s, (y1 - y) * s)
    gx, gy = P(g["ox"], g["oy"] + g["h"] * g["res"])
    svg = [f'<svg width="{W}" height="{H}" class="navsvg"><image href="{img("global_" + str(round(t,1)) + ".png")}" x="{gx:.1f}" y="{gy:.1f}" width="{g["w"]*g["res"]*s:.1f}" height="{g["h"]*g["res"]*s:.1f}" preserveAspectRatio="none" style="image-rendering:pixelated"/>']
    pl = " ".join("%.1f,%.1f" % P(*p) for p in o["plan"])
    svg.append(f'<polyline points="{pl}" fill="none" stroke="{ACC}" stroke-width="2.5" stroke-dasharray="6 5"/>')
    dr = " ".join("%.1f,%.1f" % P(p[1], p[2]) for p in ODOM if p[0] <= t)
    svg.append(f'<polyline points="{dr}" fill="none" stroke="{INK}" stroke-width="3.5" stroke-linecap="round"/>')
    for (wx, wy), lab, fill in [(WP1, "WP 1", "#fff"), (GOAL, "GOAL", "#fff")]:
        cx, cy = P(wx, wy)
        svg.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="7" fill="{fill}" stroke="{INK}" stroke-width="2"/><text x="{cx-6:.1f}" y="{cy-11:.1f}" class="lbl">{lab}</text>')
    sx_, sy_ = P(0, 0)
    svg.append(f'<rect x="{sx_-5:.1f}" y="{sy_-5:.1f}" width="10" height="10" fill="{MUTE}"/><text x="{sx_-8:.1f}" y="{sy_+18:.1f}" class="lbl">START</text>')
    vx, vy = P(o["pose"][0], o["pose"][1]); yaw = o["pose"][2]
    tip = (vx + 14 * math.cos(yaw), vy - 14 * math.sin(yaw))
    svg.append(f'<polygon points="{tip[0]:.1f},{tip[1]:.1f} {vx-7*math.sin(yaw)-5*math.cos(yaw):.1f},{vy-7*math.cos(yaw)+5*math.sin(yaw):.1f} {vx+7*math.sin(yaw)-5*math.cos(yaw):.1f},{vy+7*math.cos(yaw)+5*math.sin(yaw):.1f}" fill="{ACC}" stroke="#fff" stroke-width="1.5"/>')
    svg.append(f'<line x1="10" y1="{H-10}" x2="{10+5*s:.1f}" y2="{H-10}" stroke="{INK}" stroke-width="2"/><text x="10" y="{H-15}" class="lbl">5 m</text></svg>')
    return f'<div class="p navp"><h3>NAVIGATION</h3>{"".join(svg)}<div class="foot"><span><i class="ln"></i>driven</span><span><i class="ln dash"></i>planned</span><span><i class="sq"></i>obstacle (global costmap)</span></div></div>'

def health(t, o, stopped):
    rows = [("Localization", OK, "100 Hz · 0 ms"),
            ("Cameras", BAD if stopped else OK, "Cam 2 gap 265 ms" if stopped else "3 / 3 · 19 Hz"),
            ("LiDAR", OK, f'10 Hz · {o["safety"]["lidar"]*1000:.0f} ms'),
            ("Planning", OK, "planner alive"),
            ("Control", WARN if t > 15.5 else OK, "aborted 11:46:03" if t > 15.5 else "controller alive"),
            ("Safety", BAD if stopped else OK, "STOP sent" if stopped else "velocity filter OK")]
    r = "".join(f'<div class="kv"><span>{a}</span><b>{dot(c)}<em>{n}</em></b></div>' for a, c, n in rows)
    return f'<div class="p health"><h3>SYSTEMS HEALTH</h3>{r}</div>'

def lidar(t, o):
    g = o["local"]; W = 250 if t > 18 else 286
    k = W / (g["w"] * g["res"])
    def P(x, y): return ((x - g["ox"]) * k, W - (y - g["oy"]) * k)
    x, y, yaw = o["pose"]
    def B(px, py): return (x + px * math.cos(yaw) - py * math.sin(yaw), y + px * math.sin(yaw) + py * math.cos(yaw))
    lp = " ".join("%.1f,%.1f" % P(*B(*p)) for p in o["local_path"])
    lx, ly = P(*B(o["lookahead"][0], o["lookahead"][1]))
    vx, vy = P(x, y)
    corners = [B(1.0, 0.6), B(1.0, -0.6), B(-1.0, -0.6), B(-1.0, 0.6)]
    veh = " ".join("%.1f,%.1f" % P(*c) for c in corners)
    rings = "".join(f'<circle cx="{vx:.1f}" cy="{vy:.1f}" r="{r*k:.1f}" fill="none" stroke="#c9ccd1" stroke-dasharray="3 4"/>' for r in (5, 10))
    svg = f'''<svg width="{W}" height="{W}"><image href="{img("local_" + str(round(t,1)) + ".png")}" x="0" y="0" width="{W}" height="{W}" preserveAspectRatio="none" style="image-rendering:pixelated"/>{rings}
<polyline points="{lp}" fill="none" stroke="{OK}" stroke-width="6" stroke-opacity=".45" stroke-linecap="round"/>
<circle cx="{lx:.1f}" cy="{ly:.1f}" r="4.5" fill="{OK}" stroke="#fff" stroke-width="1.5"/>
<polygon points="{veh}" fill="{INK}"/></svg>'''
    return f'''<div class="p lid"><h3>LiDAR TOP VIEW + LOCAL PATH</h3><div class="lidb">{svg}<div class="leg">
<div><i style="background:{BAD}"></i>obstacle</div><div><i style="background:#f0c48a"></i>near obstacle</div><div><i style="background:{OK};opacity:.5"></i>local path</div><div>{dot(OK)}lookahead {math.hypot(*o["lookahead"][:2]):.1f} m</div>
<div class="sm">rings 5 m / 10 m<br>grid 30 × 30 m<br>updated 1.7×/s</div></div></div></div>'''

TRIG = [("T1", "Camera frame gap > 158 ms", "STOP"), ("T2", "Camera rate < 15 Hz", "STOP"), ("T3", "Camera feed lost > 0.5 s", "STOP"),
        ("T4", "Localization stale > 0.2 s", "STOP"), ("T5", "Autonomy command stale", "STOP"), ("T6", "Path follower aborted", "ALERT"),
        ("T7", "Collision monitor zone", "ALERT")]
def triggers(t, stopped):
    rows = []
    for tid, name, act in TRIG:
        c = OK; st = "armed"
        if tid == "T1" and stopped: c, st = BAD, "FIRED"
        if tid == "T6" and t > 15.5: c, st = WARN, clk(15.5)
        ac = BAD if act == "STOP" else WARN
        rows.append(f'<div class="tr{" fired" if st=="FIRED" else ""}">{dot(c)}<span class="tn"><b>{tid}</b> {name}</span><span class="act" style="color:{ac};border-color:{ac}">{act}</span><span class="ts">{st}</span></div>')
    return f'<div class="p trig"><h3>STOP TRIGGERS</h3>{"".join(rows)}</div>'

def mission(t, o):
    x, y, _ = o["pose"]
    rows = [("WP 1", f'{math.dist((x, y), WP1):.1f} m', True), ("GOAL (14.5, −12.3)", f'{o["plan_len"]:.1f} m', False)]
    r = "".join(f'<div class="wp{" cur" if c else ""}"><span>{a}</span><b>{b}</b></div>' for a, b, c in rows)
    return f'''<div class="p mis"><h3>MISSION</h3>{r}<div class="kv"><span>Driven so far</span><b>{sum(math.dist(ODOM[i][1:3], ODOM[i-1][1:3]) for i in range(1, len(ODOM)) if ODOM[i][0] <= t):.1f} m</b></div>
</div>'''

def bottom(alert=None):
    tabs = "".join(f'<div class="bt{" on" if n=="Home" else ""}">{n}</div>' for n in ["Home", "Map", "Sensors", "Logs", "Faults", "Triggers"])
    al = alert or "No active alerts"
    return f'<div class="bottom">{tabs}<div class="alert{" red" if alert else ""}">{al}</div></div>'

def screen(t, stopped=False):
    o = S[str(t)]
    ban = f'<div class="banner"><b>STOP SENT · {clk(18.1, True)}</b> T1 Camera frame gap: Camera 2, 265 ms (limit 158 ms). Vehicle halted, safety driver in control.</div>' if stopped else ""
    return f'''<div class="screen">{header(t, not stopped)}{ban}<div class="grid{" withban" if stopped else ""}">
{drive(t, o, stopped)}{cams(stopped)}{nav(t, o)}
{health(t, o, stopped)}{lidar(t, o)}{triggers(t, stopped)}{mission(t, o)}</div>
{bottom("STOP · T1 Camera 2 frame gap · " + clk(18.1) if stopped else None)}</div>'''

CHANGES = [
 ("Header", "GPS and Battery replaced by Localization and Safety (no GPS or battery data). Clock shows the bag's recorded time."),
 ("Drive status", "Gear and Terrain mode removed (no data). Steering shown as commanded turn rate. Speed in m/s; this run peaks at 2.2 m/s."),
 ("Front camera", "Obstacle boxes and drivable corridor removed (no calibration, no detection, latency). Replaced by 3 camera previews at 1 frame/s."),
 ("Navigation", "Real global costmap, driven path and planned path. WP 1 is inferred from the turn in the planned path; only 2 waypoints exist. NO-GO zone removed (no data)."),
 ("Systems health", "Perception replaced by Cameras and LiDAR feed health. Each row shows its live value, not only OK."),
 ("LiDAR + planned path", "Merged into one top-down panel: real occupancy grid with the controller's local path and lookahead point. Perspective path view removed (needs camera calibration)."),
 ("Upcoming waypoints", "Replaced by Mission: distance to WP 1 and to the goal in metres. km distances and terrain items removed."),
 ("New: Stop triggers", "The client's main requirement. Shows each trigger's state; a fired trigger turns the screen into the STOPPED state (page 2)."),
]

CSS = f'''
@page {{ size: 1300px 940px; margin: 0 }}
*{{box-sizing:border-box}} body{{margin:0;font-family:Inter,Helvetica,Arial,sans-serif;color:{INK};background:#e9ebee}}
.page{{width:1300px;height:940px;padding:22px 28px;page-break-after:always}}
.page h1{{font-size:20px;margin:0 0 4px}} .page .sub{{color:{MUTE};font-size:13px;margin-bottom:12px}}
.screen{{width:1244px;height:838px;background:{BG};border:1px solid {LINE};border-radius:8px;padding:10px;display:flex;flex-direction:column;gap:10px}}
.hdr{{display:flex;align-items:center;gap:26px;background:#fff;border:1px solid {LINE};border-radius:8px;padding:8px 16px;height:62px}}
.brand{{display:flex;align-items:center;gap:8px;background:#5d1725;color:#fff;padding:6px 10px;border-radius:4px}} .brand b{{font-size:20px;letter-spacing:1px}} .brand span{{font-size:10px;line-height:1.15}}
.title{{flex:1;font-size:22px;font-weight:700}} .title small{{display:block;font-size:11.5px;color:{MUTE};font-weight:500;margin-top:2px}}
.hs{{display:flex;flex-direction:column;font-size:11.5px;color:{MUTE};gap:2px}} .hs b{{font-size:14px}}
.clock{{font-family:monospace;font-size:16px;font-weight:700;text-align:right}} .clock small{{display:block;font-family:Inter,Helvetica;font-size:11px;color:{MUTE};font-weight:500}}
.banner{{background:{BAD};color:#fff;border-radius:6px;padding:8px 14px;font-size:14px}} .banner b{{margin-right:10px}}
.grid{{flex:1;display:grid;grid-template-columns:250px 1fr 324px;grid-template-rows:1fr 1fr;gap:10px;min-height:0}}
.grid{{grid-template-areas:"drive cam nav" "health lid right"}}
.p{{background:#fff;border:1px solid {LINE};border-radius:8px;padding:10px 12px;overflow:hidden;min-height:0}}
.p h3{{margin:0 0 6px;font-size:13.5px;letter-spacing:.3px;display:flex;justify-content:space-between;align-items:center}}
.drive{{grid-area:drive}} .camp{{grid-area:cam}} .navp{{grid-area:nav}} .health{{grid-area:health}}
.lid{{grid-area:lid}}
.trig,.mis{{}} .rightcol{{grid-area:right}}
.mode{{border:1.5px solid {OK};background:#e9f6ec;border-radius:8px;padding:12px;text-align:center;margin-bottom:10px}} .mode b{{display:block;font-size:17px}} .mode span{{font-size:13px}}
.kv{{display:flex;justify-content:space-between;align-items:center;font-size:12.5px;padding:6px 0;border-bottom:1px solid #eef0f2}} .kv span{{color:{MUTE}}} .kv em{{font-style:normal;font-weight:500;font-size:11.5px;color:{MUTE};margin-left:6px}}
.dot{{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:5px;vertical-align:middle}}
.tabs{{display:flex;font-size:11.5px;font-weight:600}} .tabs b,.tabs span{{padding:3px 10px;border:1px solid {LINE};margin-left:4px;border-radius:4px}} .tabs b{{border-color:{ACC};color:{ACC};background:#eef4fd}} .tabs span{{color:{MUTE}}}
.camp{{display:flex;flex-direction:column}} .camrow{{display:flex;gap:8px;flex:1;min-height:0}} .cam{{flex:1;position:relative;background:#f7f7f6;border:1px solid {LINE};border-radius:6px}} .cam.bad{{outline:3px solid {BAD}}}
.cl,.cr{{position:absolute;bottom:5px;font-size:11px;background:#fff;padding:1px 6px;border-radius:3px;font-weight:600}} .cl{{left:6px}} .cr{{right:6px}}
.foot{{font-size:11px;color:{MUTE};margin-top:6px;display:flex;gap:12px}} .foot i{{display:inline-block;width:16px;height:0;border-top:3px solid {INK};vertical-align:middle;margin-right:4px}} .foot i.dash{{border-top:2.5px dashed {ACC}}} .foot i.sq{{width:9px;height:9px;border:0;background:#c8463c}}
.navsvg{{display:block;border:1px solid #eef0f2;border-radius:4px;background:#fafaf8}} .lbl{{font-size:10.5px;font-weight:700;fill:{INK}}}
.lidb{{display:flex;gap:12px}} .lidb svg{{border:1px solid #eef0f2;border-radius:4px;flex:none}} .leg{{font-size:11.5px;display:flex;flex-direction:column;gap:6px}} .leg i{{display:inline-block;width:11px;height:11px;border-radius:2px;margin-right:6px;vertical-align:middle}} .leg .sm{{margin-top:auto;color:{MUTE};font-size:10.5px;line-height:1.4}}
.tr{{display:flex;align-items:center;gap:4px;font-size:11.5px;padding:3px 4px;border-bottom:1px solid #eef0f2}} .tr.fired{{background:#fdecec;outline:1.5px solid {BAD};border-radius:4px}}
.tn{{flex:1}} .act{{font-size:9px;font-weight:800;border:1.3px solid;border-radius:3px;padding:0 4px}} .ts{{width:58px;text-align:right;font-size:10.5px;color:{MUTE};font-weight:600}}
.wp{{display:flex;justify-content:space-between;font-size:12.5px;padding:5px 8px;border-radius:5px}} .wp.cur{{background:#e9f6ec}} .wp b{{font-family:monospace}}
.bottom{{display:flex;align-items:center;background:#fff;border:1px solid {LINE};border-radius:8px;height:58px;padding:0 8px}}
.bt{{padding:10px 26px;font-weight:700;font-size:15px;border-radius:6px}} .bt.on{{background:#e7effc;color:{ACC}}}
.alert{{margin-left:auto;border-left:1px solid {LINE};padding-left:18px;font-size:13.5px;color:{MUTE};min-width:300px}} .alert.red{{color:{BAD};font-weight:700}}
.chg{{background:#fff;border:1px solid {LINE};border-radius:8px;padding:18px 24px}} .chg table{{width:100%;border-collapse:collapse;font-size:14px}} .chg td{{padding:10px 8px;border-bottom:1px solid #eef0f2;vertical-align:top}} .chg td:first-child{{font-weight:700;width:200px}}
'''

def right(t, stopped):
    return f'<div class="rightcol" style="display:grid;grid-template-columns:1fr;grid-template-rows:auto 1fr;gap:10px;min-height:0">{triggers(t, stopped)}{mission(t, S[str(t)])}</div>'

def screen2(t, stopped=False):
    o = S[str(t)]
    ban = f'<div class="banner"><b>STOP SENT · {clk(18.1, True)}</b> T1 Camera frame gap: Camera 2, 265 ms (limit 158 ms). Vehicle halted, safety driver in control.</div>' if stopped else ""
    return f'''<div class="screen">{header(t, not stopped)}{ban}<div class="grid">
{drive(t, o, stopped)}{cams(stopped)}{nav(t, o)}{health(t, o, stopped)}{lidar(t, o)}{right(t, stopped)}</div>
{bottom("STOP · T1 Camera 2 frame gap · " + clk(18.1) if stopped else None)}</div>'''

pages = [
 f'<section class="page"><h1>Home — autonomy running</h1><div class="sub">Bag playback, {clk(14.3)} CDT. All values from autonomy_demo_0.</div>{screen2(14.3)}</section>',
 f'<section class="page"><h1>Home — stop trigger fired</h1><div class="sub">Same playback at {clk(18.1, True)} CDT. Camera 2 has gone 158 ms without a frame.</div>{screen2(18.1, True)}</section>',
 '<section class="page"><h1>Changes from the team sketch</h1><div class="sub">Same layout and panel positions. Each change follows from the data in the bag or from system latency.</div><div class="chg"><table>'
 + "".join(f"<tr><td>{a}</td><td>{b}</td></tr>" for a, b in CHANGES) + "</table></div></section>",
]
open(OUT_HTML, "w").write(f'<!doctype html><html><head><meta charset="utf-8"><title>CAVS Dashboard Revised Sketch</title><meta name="author" content="Zeenat Islam"><style>{CSS}</style></head><body>{"".join(pages)}</body></html>')
print("ok")
