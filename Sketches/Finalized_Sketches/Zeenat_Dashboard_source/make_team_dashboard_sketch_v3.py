# Revised team dashboard sketch v3 (Home page): only fields recorded in the bag, no derived values
# Author: Zeenat Islam
import json, base64, datetime as dt, os

DATA_DIR = "direct"               # from Dataset/bag_inspection/09_direct_fields.py
OUT_HTML = "team_dashboard_v3.html"
BAG_START = 1789145148.161676535  # first message, epoch s
TZ = dt.timezone(dt.timedelta(hours=-5))
MODE = {0: "MANUAL", 1: "AUTONOMY", 2: "E-STOP"}   # /mtx/arbiter_status mode values, as named in /rosout
S = json.load(open(os.path.join(DATA_DIR, "state.json")))
DIAG = [("Nav2", "Managed nodes are active"), ("Drive bridge", "LIVE (transmitting)")]   # /diagnostics, level 0 throughout

INK, MUTE, LINE, BG = "#1f2328", "#6b7280", "#d7dade", "#f4f5f7"
OK, WARN, BAD, OFF, ACC = "#2f9e44", "#e0a100", "#d64545", "#a0a4aa", "#2f6fdb"

def clk(t, ms=False):
    d = dt.datetime.fromtimestamp(BAG_START + t, TZ)
    return d.strftime("%H:%M:%S") + (f".{d.microsecond // 100000}" if ms else "")
def img(name): return "data:image/png;base64," + base64.b64encode(open(os.path.join(DATA_DIR, name), "rb").read()).decode()
def dot(c): return f'<span class="dot" style="background:{c}"></span>'

def header(o):
    d = dt.datetime.fromtimestamp(BAG_START + o["t"], TZ); s = o["safety"]
    hs = [("SAFETY FILTER", "OK" if s["ok"] else "INHIBIT", OK if s["ok"] else BAD),
          ("NAV2", "active", OK), ("DRIVE BRIDGE", "LIVE", OK),
          ("E-STOP", "LATCHED" if o["estop"] else "clear", BAD if o["estop"] else OK)]
    h = "".join(f'<div class="hs"><span>{a}</span><b style="color:{c}">{b}</b></div>' for a, b, c in hs)
    return f'''<div class="hdr"><div class="brand"><b>CAVS</b><span>Center for Advanced<br>Vehicular Systems</span></div>
<div class="title">Autonomous Vehicle Testing<small>{dot(BAD)} LIVE · bag playback · autonomy_demo_0</small></div>{h}
<div class="clock">{clk(o["t"])}<small>{d.strftime("%b %d, %Y")} CDT</small></div></div>'''

def drive(o):
    a = o["arbiter"]; mode = MODE.get(a["mode"], str(a["mode"]))
    if a["estop"]:
        box = f'<div class="mode" style="background:#fdecec;border-color:{BAD}"><b style="color:{BAD}">{mode}</b><span>SOFTWARE E-STOP LATCHED<br>STOP pressed by operator</span></div>'
    else:
        box = f'<div class="mode"><b>{mode}</b><span>Navigating through 2 poses<br>to (14.50, −12.29)</span></div>'
    rows = [("Speed", f'{o["odom_twist"]["linear_x"]:.2f} m/s'), ("Commanded speed", f'{o["cmd_vel_autonomy"]["linear_x"]:.2f} m/s' if not a["estop"] else "inactive"),
            ("Commanded turn", f'{o["cmd_vel_autonomy"]["angular_z"]:+.3f} rad/s' if not a["estop"] else "inactive"),
            ("Active source", a["active_source"] or "none"), ("Autonomy active", str(a["autonomy_active"]).lower())]
    return f'<div class="p drive"><h3>DRIVE STATUS</h3>{box}' + "".join(f'<div class="kv"><span>{x}</span><b>{y}</b></div>' for x, y in rows) + "</div>"

def cams():
    out = "".join(f'<div class="cam"><svg width="100%" height="100%"><line x1="0" y1="0" x2="100%" y2="100%" stroke="{LINE}"/><line x1="100%" y1="0" x2="0" y2="100%" stroke="{LINE}"/></svg><span class="cl">CAM {i}</span></div>' for i in range(3))
    return f'<div class="p camp"><h3>CAMERAS<span class="tabs"><b>Camera</b><span>LiDAR</span><span>Faults</span></span></h3><div class="camrow">{out}</div><div class="foot">Latest frame from /cam_0, /cam_1, /cam_2 image_raw · once per second</div></div>'

def poly(pts, P): return " ".join("%.1f,%.1f" % P(*p) for p in pts)

def nav(o, H):
    g = o["global"]; x0, x1, y0, y1 = -3, 32, -15, 5; W = 300
    s = min(W / (x1 - x0), H / (y1 - y0))
    P = lambda x, y: ((x - x0) * s, (y1 - y) * s)
    gx, gy = P(g["ox"], g["oy"] + g["h"] * g["res"])
    gname = "global_%s.png" % o["t"]
    svg = [f'<svg width="{W}" height="{H}" class="navsvg"><image href="{img(gname)}" x="{gx:.1f}" y="{gy:.1f}" width="{g["w"]*g["res"]*s:.1f}" height="{g["h"]*g["res"]*s:.1f}" preserveAspectRatio="none" style="image-rendering:pixelated"/>',
           f'<polyline points="{poly(o["plan"], P)}" fill="none" stroke="{ACC}" stroke-width="2.5" stroke-dasharray="6 5"/>',
           f'<polyline points="{poly(o["dlio_path"], P)}" fill="none" stroke="{INK}" stroke-width="3.5" stroke-linecap="round"/>',
           f'<polygon points="{poly(o["footprint"], P)}" fill="{ACC}" stroke="#fff" stroke-width="1.2"/>']
    gx2, gy2 = P(*o["plan"][-1])
    svg.append(f'<circle cx="{gx2:.1f}" cy="{gy2:.1f}" r="7" fill="#fff" stroke="{INK}" stroke-width="2"/><text x="{gx2-8:.1f}" y="{gy2-11:.1f}" class="lbl">GOAL</text>')
    sx, sy = P(*o["dlio_path"][0])
    svg.append(f'<rect x="{sx-5:.1f}" y="{sy-5:.1f}" width="10" height="10" fill="{MUTE}"/><text x="{sx-8:.1f}" y="{sy+18:.1f}" class="lbl">START</text>')
    svg.append(f'<line x1="10" y1="{H-10}" x2="{10+5*s:.1f}" y2="{H-10}" stroke="{INK}" stroke-width="2"/><text x="10" y="{H-15}" class="lbl">5 m</text></svg>')
    return f'<div class="p navp"><h3>NAVIGATION</h3>{"".join(svg)}<div class="foot"><span><i class="ln"></i>driven (/dlio path)</span><span><i class="ln dash"></i>/plan</span><span><i class="sq"></i>obstacle</span></div></div>'

def health(o):
    s = o["safety"]
    rows = [("Safety filter", OK if s["ok"] else BAD, "ok" if s["ok"] else ", ".join(s["inhibit_reasons"]))]
    rows += [(a, OK, b) for a, b in DIAG]
    rows += [("Odometry age", OK, f'{s["odom_age_s"]*1000:.0f} ms'), ("LiDAR age", OK, f'{s["lidar_age_s"]*1000:.0f} ms'),
             ("TF age", OK, f'{s["tf_age_s"]*1000:.0f} ms'), ("Command age", OK, f'{s["cmd_age_s"]*1000:.0f} ms')]
    return '<div class="p health"><h3>SYSTEMS HEALTH</h3>' + "".join(f'<div class="kv"><span>{a}</span><b>{dot(c)}<em>{n}</em></b></div>' for a, c, n in rows) + "</div>"

def lidar(o, W):
    g = o["voxel"]; k = W / (g["w"] * g["res"])
    P = lambda x, y: ((x - g["ox"]) * k, W - (y - g["oy"]) * k)
    lname = "voxel_%s.png" % o["t"]
    svg = f'''<svg width="{W}" height="{W}"><image href="{img(lname)}" x="0" y="0" width="{W}" height="{W}" preserveAspectRatio="none" style="image-rendering:pixelated"/>
<polygon points="{poly(o["footprint"], P)}" fill="{INK}"/><line x1="10" y1="{W-10}" x2="{10+5*k:.1f}" y2="{W-10}" stroke="{INK}" stroke-width="2"/><text x="10" y="{W-15}" class="lbl">5 m</text></svg>'''
    return f'''<div class="p lid"><h3>LiDAR TOP VIEW · OCCUPANCY GRID</h3><div class="lidb">{svg}<div class="leg">
<div><i style="background:{BAD}"></i>occupied</div><div><i style="background:#fafaf8;border:1px solid #cfd3d8"></i>free</div><div><i style="background:{INK}"></i>vehicle footprint</div>
<div class="sm">/local_costmap/voxel_layer<br>30 × 30 m, 0.2 m cells<br>/local_costmap/published_footprint</div></div></div></div>'''

def stopstate(o):
    a = o["arbiter"]; cm = o["collision_monitor"]
    rows = [("/mtx/estop", "true" if o["estop"] else "no message yet" if o["estop"] is None else "false", BAD if o["estop"] else OK),
            ("Arbiter e-stop", str(a["estop"]).lower(), BAD if a["estop"] else OK),
            ("Arbiter inhibit", ", ".join(a["inhibit_reasons"]) or "none", BAD if a["inhibit_reasons"] else OK),
            ("Collision monitor", "no message yet" if cm is None else (cm["polygon"] or "clear"), OK)]
    return '<div class="p stop"><h3>STOP STATE</h3>' + "".join(f'<div class="kv"><span>{x}</span><b>{dot(c)}<em>{y}</em></b></div>' for x, y, c in rows) + "</div>"

def logs(o, n):
    r = "".join(f'<div class="lg"><span class="lt">{clk(t)}</span><span class="ll" style="color:{BAD if lv >= 40 else WARN}">{"ERROR" if lv >= 40 else "WARN"}</span><span class="lm">{nm[:22]}: {msg[:46]}</span></div>' for t, lv, nm, msg in o["rosout"][-n:][::-1])
    return f'<div class="p logp"><h3>LOG · WARN / ERROR</h3>{r}</div>'

def bottom(o):
    tabs = "".join(f'<div class="bt{" on" if n=="Home" else ""}">{n}</div>' for n in ["Home", "Map", "Sensors", "Logs", "Faults"])
    errs = [l for l in o["rosout"] if l[1] >= 40]
    errs = [l for l in errs if "E-STOP" in l[3]] or errs
    al = f'{clk(errs[-1][0])} · {errs[-1][3].split(':')[0][:44]}' if errs and errs[-1][0] > o["t"] - 5 else "No active alerts"
    return f'<div class="bottom">{tabs}<div class="alert{" red" if al != "No active alerts" else ""}">{al}</div></div>'

def screen(key):
    o = S[key]; stopped = bool(o["estop"])
    ban = f'<div class="banner"><b>E-STOP LATCHED · {clk(64.7, True)}</b> web: STOP pressed by operator · command_arbiter: SOFTWARE E-STOP LATCHED</div>' if stopped else ""
    right = f'<div class="rightcol">{stopstate(o)}{logs(o, 3 if stopped else 4)}</div>'
    return f'''<div class="screen">{header(o)}{ban}<div class="grid">{drive(o)}{cams()}{nav(o, 246 if stopped else 268)}{health(o)}{lidar(o, 250 if stopped else 286)}{right}</div>{bottom(o)}</div>'''

REMOVED = [
 ("Header", "Localization and Comms removed (no recorded status). Now Safety filter, Nav2, Drive bridge and E-stop, each read directly from /mtx/velocity_filter/status, /diagnostics and /mtx/estop."),
 ("Drive status", "Speed is /mtx/odom twist.linear.x. Commanded speed and turn are /mtx/cmd_vel_autonomy. Goal text is the bt_navigator log line. Waypoint number removed (inferred)."),
 ("Cameras", "Frame rate and gap labels removed (calculated). Only the latest image of each camera."),
 ("Navigation", "Driven path is the recorded /dlio/odom_node/path. Vehicle drawn from /local_costmap/published_footprint. Inferred WP 1 removed; goal is the last pose of /plan."),
 ("Systems health", "Feed rates removed (calculated). Rows are recorded fields: safety filter ok and reasons, Nav2 health, drive bridge, and the odometry, LiDAR, TF and command ages from /mtx/velocity_filter/status."),
 ("LiDAR", "Occupancy grid from /local_costmap/voxel_layer: only cells the LiDAR hit (occupied / free), no safety margin. Vehicle from the recorded footprint. No local path overlay (needs a frame transform)."),
 ("Stop triggers", "Removed: every trigger is a calculation on message timing. Replaced by Stop state, read from /mtx/estop, /mtx/arbiter_status and the collision monitor."),
 ("Mission", "Distances removed (calculated). Replaced by the WARN / ERROR lines from /rosout."),
 ("Page 2", "Shows the recorded operator STOP and e-stop at 11:46:52, not a trigger stop."),
]

CSS = f'''
@page {{ size: 1300px 940px; margin: 0 }}
*{{box-sizing:border-box}} body{{margin:0;font-family:Inter,Helvetica,Arial,sans-serif;color:{INK};background:#e9ebee}}
.page{{width:1300px;height:940px;padding:22px 28px;page-break-after:always}} .page h1{{font-size:20px;margin:0 0 4px}} .page .sub{{color:{MUTE};font-size:13px;margin-bottom:12px}}
.screen{{width:1244px;height:838px;background:{BG};border:1px solid {LINE};border-radius:8px;padding:10px;display:flex;flex-direction:column;gap:10px}}
.hdr{{display:flex;align-items:center;gap:22px;background:#fff;border:1px solid {LINE};border-radius:8px;padding:8px 16px;height:62px}}
.brand{{display:flex;align-items:center;gap:8px;background:#5d1725;color:#fff;padding:6px 10px;border-radius:4px}} .brand b{{font-size:20px;letter-spacing:1px}} .brand span{{font-size:10px;line-height:1.15}}
.title{{flex:1;font-size:22px;font-weight:700}} .title small{{display:block;font-size:11.5px;color:{MUTE};font-weight:500;margin-top:2px}}
.hs{{display:flex;flex-direction:column;font-size:11px;color:{MUTE};gap:2px}} .hs b{{font-size:14px}}
.clock{{font-family:monospace;font-size:16px;font-weight:700;text-align:right}} .clock small{{display:block;font-family:Inter,Helvetica;font-size:11px;color:{MUTE};font-weight:500}}
.banner{{background:{BAD};color:#fff;border-radius:6px;padding:8px 14px;font-size:14px}} .banner b{{margin-right:10px}}
.grid{{flex:1;display:grid;grid-template-columns:250px 1fr 324px;grid-template-rows:1fr 1fr;gap:10px;min-height:0;grid-template-areas:"drive cam nav" "health lid right"}}
.p{{background:#fff;border:1px solid {LINE};border-radius:8px;padding:10px 12px;overflow:hidden;min-height:0}}
.p h3{{margin:0 0 6px;font-size:13.5px;letter-spacing:.3px;display:flex;justify-content:space-between;align-items:center}}
.drive{{grid-area:drive}} .camp{{grid-area:cam;display:flex;flex-direction:column}} .navp{{grid-area:nav}} .health{{grid-area:health}} .lid{{grid-area:lid}}
.rightcol{{grid-area:right;display:grid;grid-template-rows:auto 1fr;gap:10px;min-height:0}}
.mode{{border:1.5px solid {OK};background:#e9f6ec;border-radius:8px;padding:10px;text-align:center;margin-bottom:8px}} .mode b{{display:block;font-size:17px}} .mode span{{font-size:12.5px}}
.kv{{display:flex;justify-content:space-between;align-items:center;gap:8px;font-size:12.5px;padding:5px 0;white-space:nowrap;border-bottom:1px solid #eef0f2}} .kv span{{color:{MUTE}}} .kv em{{font-style:normal;font-weight:500;font-size:11.5px;color:{INK};margin-left:4px}}
.dot{{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:5px;vertical-align:middle}}
.tabs{{display:flex;font-size:11.5px;font-weight:600}} .tabs b,.tabs span{{padding:3px 10px;border:1px solid {LINE};margin-left:4px;border-radius:4px}} .tabs b{{border-color:{ACC};color:{ACC};background:#eef4fd}} .tabs span{{color:{MUTE}}}
.camrow{{display:flex;gap:8px;flex:1;min-height:0}} .cam{{flex:1;position:relative;background:#f7f7f6;border:1px solid {LINE};border-radius:6px}}
.cl{{position:absolute;bottom:5px;left:6px;font-size:11px;background:#fff;padding:1px 6px;border-radius:3px;font-weight:600}}
.foot{{font-size:11px;color:{MUTE};margin-top:6px;display:flex;gap:12px}} .foot i{{display:inline-block;width:16px;height:0;border-top:3px solid {INK};vertical-align:middle;margin-right:4px}} .foot i.dash{{border-top:2.5px dashed {ACC}}} .foot i.sq{{width:9px;height:9px;border:0;background:#c8463c}}
.navsvg{{display:block;border:1px solid #eef0f2;border-radius:4px;background:#fafaf8}} .lbl{{font-size:10.5px;font-weight:700;fill:{INK}}}
.lidb{{display:flex;gap:12px}} .lidb svg{{border:1px solid #eef0f2;border-radius:4px;flex:none}} .leg{{font-size:11.5px;display:flex;flex-direction:column;gap:6px}} .leg i{{display:inline-block;width:11px;height:11px;border-radius:2px;margin-right:6px;vertical-align:middle}} .leg .sm{{margin-top:auto;color:{MUTE};font-size:10.5px;line-height:1.45;font-family:monospace}}
.lg{{display:grid;grid-template-columns:58px 44px 1fr;gap:4px;font-size:11px;padding:4px 0;border-bottom:1px solid #eef0f2}} .lt{{font-family:monospace;color:{MUTE}}} .ll{{font-weight:800;font-size:10px}} .lm{{line-height:1.3}}
.bottom{{display:flex;align-items:center;background:#fff;border:1px solid {LINE};border-radius:8px;height:58px;padding:0 8px}}
.bt{{padding:10px 26px;font-weight:700;font-size:15px;border-radius:6px}} .bt.on{{background:#e7effc;color:{ACC}}}
.alert{{margin-left:auto;border-left:1px solid {LINE};padding-left:18px;font-size:13px;color:{MUTE};min-width:360px}} .alert.red{{color:{BAD};font-weight:700}}
.chg{{background:#fff;border:1px solid {LINE};border-radius:8px;padding:18px 24px}} .chg table{{width:100%;border-collapse:collapse;font-size:14px}} .chg td{{padding:10px 8px;border-bottom:1px solid #eef0f2;vertical-align:top}} .chg td:first-child{{font-weight:700;width:180px}}
'''

pages = [
 f'<section class="page"><h1>Home — autonomy running</h1><div class="sub">Bag playback, {clk(14.3)} CDT. Every value is a field recorded in autonomy_demo_0.</div>{screen("14.3")}</section>',
 f'<section class="page"><h1>Home — operator STOP, e-stop latched</h1><div class="sub">Bag playback, {clk(64.9)} CDT. Recorded STOP at {clk(64.7, True)}.</div>{screen("64.9")}</section>',
 '<section class="page"><h1>Changes from v1</h1><div class="sub">Only fields recorded in the bag are shown. Anything that had to be calculated has been removed.</div><div class="chg"><table>'
 + "".join(f"<tr><td>{a}</td><td>{b}</td></tr>" for a, b in REMOVED) + "</table></div></section>",
]
open(OUT_HTML, "w").write(f'<!doctype html><html><head><meta charset="utf-8"><title>CAVS Dashboard Revised Sketch v3</title><meta name="author" content="Zeenat Islam"><style>{CSS}</style></head><body>{"".join(pages)}</body></html>')
print("ok")
