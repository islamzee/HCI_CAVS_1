# Sensors, Faults, Past Logs and Log detail page sketches v2, recorded fields only
# Author: Zeenat Islam
import json, os, contextlib, io, datetime as dt
with contextlib.redirect_stdout(io.StringIO()):
    import make_team_dashboard_sketch_v3 as H        # shared header, colours, CSS, helpers

PAGES_DIR = "pages"                                  # from Dataset/bag_inspection/10_page_fields.py
OUT_HTML = "team_pages_v2.html"
F = json.load(open(os.path.join(PAGES_DIR, "fields.json")))
T_SENS, T_FAULT = 14.3, 64.9
LEVEL = {10: "DEBUG", 20: "INFO", 30: "WARN", 40: "ERROR", 50: "FATAL"}
INK, MUTE, LINE, OK, WARN, BAD, ACC = H.INK, H.MUTE, H.LINE, H.OK, H.WARN, H.BAD, H.ACC
clk, dot = H.clk, H.dot

def pimg(name):
    import base64
    return "data:image/png;base64," + base64.b64encode(open(os.path.join(PAGES_DIR, name), "rb").read()).decode()

def review_header():
    b = F["bag"]; start = dt.datetime.fromtimestamp(b["start_ns"] / 1e9, H.TZ)
    return f'''<div class="hdr"><div class="brand"><b>CAVS</b><span>Center for Advanced<br>Vehicular Systems</span></div>
<div class="title">Autonomous Vehicle Testing<small><span class="rev">REVIEW</span> · recorded runs</small></div>
<div class="clock">{start.strftime("%H:%M:%S")}<small>{start.strftime("%b %d, %Y")} CDT · run start</small></div></div>'''

def bottom(active, alert=None):
    tabs = "".join(f'<div class="bt{" on" if n == active else ""}">{n}</div>' for n in ["Home", "Map", "Sensors", "Logs", "Faults"])
    return f'<div class="bottom">{tabs}<div class="alert{" red" if alert else ""}">{alert or "No active alerts"}</div></div>'

def lvl(l):
    c = BAD if l >= 40 else WARN if l >= 30 else MUTE
    return f'<span class="lv" style="color:{c};border-color:{c}">{LEVEL.get(l, l)}</span>'
def badge(e):
    if e["src"] == "/rosout": return lvl(e["level"])
    c = BAD if e["level"] >= 40 else WARN if e["level"] >= 30 else MUTE
    lab = {"/mtx/estop": "E-STOP", "/mtx/velocity_filter/status": "SAFETY", "/mtx/nav/collision_monitor_state": "ZONE"}[e["src"]]
    return f'<span class="lv" style="color:{c};border-color:{c}">{lab}</span>'

# ---------- Sensors ----------
def sensors():
    o = H.S[str(T_SENS)]
    cams = ""
    for c in F["cams"]:
        cams += f'''<div class="p scam"><h3>{c["frame"].upper().replace("_", " ")}<span class="mono">/{c["frame"]}/image_raw</span></h3>
<div class="simg"><svg width="100%" height="100%"><line x1="0" y1="0" x2="100%" y2="100%" stroke="{LINE}"/><line x1="100%" y1="0" x2="0" y2="100%" stroke="{LINE}"/></svg></div>
<div class="kv"><span>Image</span><b>{c["width"]} × {c["height"]} {c["encoding"]}</b></div>
<div class="kv"><span>Image stamp (camera clock)</span><b class="mono">{c["image_stamp"]:.3f} s</b></div>
<div class="kv"><span>Exposure / gain</span><b>{c["exposure_us"]} µs / {c["gain"]:.1f}</b></div></div>'''
    g = o["voxel"]; W = 330; k = W / (g["w"] * g["res"])
    P = lambda x, y: ((x - g["ox"]) * k, W - (y - g["oy"]) * k)
    grid = f'''<svg width="{W}" height="{W}" class="gsvg"><image href="{H.img("voxel_%s.png" % T_SENS)}" x="0" y="0" width="{W}" height="{W}" preserveAspectRatio="none" style="image-rendering:pixelated"/>
<polygon points="{H.poly(o["footprint"], P)}" fill="{INK}"/><line x1="10" y1="{W-10}" x2="{10+5*k:.1f}" y2="{W-10}" stroke="{INK}" stroke-width="2"/><text x="10" y="{W-15}" class="lbl">5 m</text></svg>'''
    r = F["reflec"]; t = F["telemetry"]
    lid = f'''<div class="p slid"><h3>LiDAR · OCCUPANCY GRID<span class="mono">/local_costmap/voxel_layer · /local_costmap/published_footprint</span></h3><div class="slb">
<div>{grid}<div class="cap">30 × 30 m around the vehicle · 0.2 m cells · north up</div></div>
<div class="sleg"><div><i style="background:{BAD}"></i>occupied</div><div><i style="background:#fafaf8;border:1px solid #cfd3d8"></i>free</div><div><i style="background:{INK}"></i>vehicle footprint</div>
<div class="kv"><span>LiDAR data age</span><b>{dot(OK)}{F["lidar_age_s"]*1000:.0f} ms</b></div>
<div class="kv"><span>Thermal shutdown</span><b>{dot(OK)}{t["thermal_shutdown"]}</b></div>
<div class="kv"><span>Shot limiting</span><b>{dot(OK)}{t["shot_limiting"]}</b></div></div></div></div>'''
    return f'<div class="screen">{H.header(o)}<div class="sgrid"><div class="camline">{cams}</div>{lid}</div>{bottom("Sensors")}</div>'

# ---------- Faults ----------
def faults():
    o = H.S[str(T_FAULT)]
    ev = [e for e in F["events"] if e["t"] <= T_FAULT][::-1]
    def row(e, sel=False):
        return f'''<div class="fr{" sel" if sel else ""}" style="border-left-color:{BAD if e["level"] >= 40 else WARN}"><span class="ft">{clk(e["t"], True)}</span>{badge(e)}
<span class="fn">{e["node"][:30]}</span><span class="fm">{e["msg"][:92]}</span><span class="fl">Map ›</span><span class="fl">Log ›</span></div>'''
    ros = [e for e in ev if e["src"] == "/rosout"]; other = [e for e in ev if e["src"] != "/rosout"]
    errs = [e for e in ros if e["level"] >= 40]; warns = [e for e in ros if e["level"] == 30]
    chips = '<div class="chips"><b>All</b><span>ERROR</span><span>WARN</span><i></i><b>/rosout</b><b>/mtx/estop</b><b>safety filter</b><b>collision monitor</b></div>'
    body = f'''<div class="p fpage"><h3>FAULTS<span class="mono">newest first · /rosout WARN/ERROR · /mtx/estop · /mtx/velocity_filter/status · collision monitor</span></h3>{chips}
<div class="fsec">STATE CHANGES · /mtx/estop · safety filter · collision monitor</div>{"".join(row(e, i == 0) for i, e in enumerate(other[:3]))}
<div class="fsec">ERROR · /rosout</div>{"".join(row(e) for e in errs[:6])}
<div class="fsec">WARN · /rosout</div>{"".join(row(e) for e in warns[:3])}<div class="more">scroll for earlier entries</div></div>'''
    ban = f'<div class="banner"><b>E-STOP LATCHED · {clk(64.7, True)}</b> web: STOP pressed by operator · command_arbiter: SOFTWARE E-STOP LATCHED</div>'
    return f'<div class="screen">{H.header(o)}{ban}<div class="fwrap">{body}</div>{bottom("Faults", "11:46:52 · SOFTWARE E-STOP LATCHED")}</div>'

# ---------- Past logs ----------
def past_logs():
    b = F["bag"]; s = dt.datetime.fromtimestamp(b["start_ns"] / 1e9, H.TZ); d = int(round(b["duration_ns"] / 1e9))
    row = f'''<tr class="sel"><td><b class="lnk">{b["name"]}</b></td><td>{s.strftime("%m/%d/%Y")}</td><td>{s.strftime("%I:%M:%S %p").lstrip("0").lower()}</td>
<td>{d//3600:02d}:{d%3600//60:02d}:{d%60:02d}</td><td>{b["messages"]:,}</td><td>{b["ros_distro"]}</td><td>{b["storage"]}</td></tr>'''
    body = f'''<div class="p lpage"><h3>PAST RUNS<span class="mono">one row per bag on the server · fields from metadata.yaml</span></h3>
<table class="lt"><tr><th>RUN</th><th>DATE</th><th>START</th><th>DURATION</th><th>MESSAGES</th><th>ROS</th><th>FORMAT</th></tr>{row}</table>
<div class="hint">Select a run to open its log and replay it on the map.</div></div>'''
    return f'<div class="screen">{review_header()}<div class="fwrap">{body}</div>{bottom("Logs")}</div>'

# ---------- Log detail ----------
def log_detail():
    b = F["bag"]; s = dt.datetime.fromtimestamp(b["start_ns"] / 1e9, H.TZ); d = int(round(b["duration_ns"] / 1e9))
    lines = [l for l in F["rosout"] if l["node"] not in ("rosbag2_recorder", "cam_0", "cam_1", "cam_2") and l["level"] >= 20]
    sel = next(i for i, l in enumerate(lines) if "patience exceeded" in l["msg"])
    rows = "".join(f'''<tr class="{"sel" if i == sel else ""}"><td class="mono">{clk(l["t"], True)}</td><td>{lvl(l["level"])}</td><td class="mono">{l["node"][:28]}</td><td>{l["msg"][:96]}</td>
<td class="fl">{"Show on map ›" if i == sel else ""}</td></tr>''' for i, l in enumerate(lines[sel - 12:sel + 6], start=sel - 12))
    chips = '<div class="chips"><span>DEBUG</span><b>INFO</b><b>WARN</b><b>ERROR</b><i></i><span>rosbag2_recorder</span><span>cam_0–2</span><b>all other nodes</b></div>'
    body = f'''<div class="p lpage"><h3>LOG · {b["name"]} · {s.strftime("%m/%d/%Y")} · {d//3600:02d}:{d%3600//60:02d}:{d%60:02d}<span class="mono">/rosout · {len(F["rosout"])} lines</span></h3>{chips}
<table class="lt dl"><tr><th>TIME (CDT)</th><th>LEVEL</th><th>NODE</th><th>MESSAGE</th><th></th></tr>{rows}</table></div>'''
    return f'<div class="screen">{review_header()}<div class="fwrap">{body}</div>{bottom("Logs")}</div>'

CSS = H.CSS + f'''
.rev{{color:{ACC};font-weight:800}} .mono{{font-family:monospace;font-size:11px;color:{MUTE};font-weight:500;letter-spacing:0}}
.sgrid{{flex:1;display:flex;flex-direction:column;gap:10px;min-height:0}} .camline{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px}}
.scam .simg{{height:120px;background:#f7f7f6;border:1px solid {LINE};border-radius:6px;margin-bottom:6px}}
.slid{{flex:1}} .slb{{display:flex;gap:16px}} .gsvg{{border:1px solid #eef0f2;border-radius:4px;display:block}} .cap{{font-size:11px;color:{MUTE};margin-top:5px}}
.sleg{{width:300px;display:flex;flex-direction:column;gap:7px;font-size:12px}} .sleg i{{display:inline-block;width:11px;height:11px;border-radius:2px;margin-right:6px;vertical-align:middle}} .spano{{flex:1}} .spano img{{width:100%;display:block;border-radius:4px}} .kvg{{display:grid;grid-template-columns:1fr 1fr;column-gap:24px;margin-top:10px}}
.fwrap{{flex:1;display:flex;min-height:0}} .fpage,.lpage{{flex:1}}
.chips{{display:flex;gap:6px;margin:4px 0 10px;font-size:11.5px;font-weight:600;align-items:center}} .chips b,.chips span{{padding:3px 10px;border-radius:12px;border:1px solid {LINE}}} .chips b{{background:#e7effc;border-color:{ACC};color:{ACC}}} .chips span{{color:{MUTE}}} .chips i{{width:14px}}
.fsec{{font-size:11.5px;font-weight:800;color:{MUTE};margin:8px 0 4px;letter-spacing:.5px}}
.fr{{display:grid;grid-template-columns:90px 56px 200px 1fr 50px 50px;gap:10px;align-items:center;font-size:12.5px;padding:7px 10px;border:1px solid #eef0f2;border-left:5px solid;border-radius:6px;margin-bottom:5px}}
.fr.sel{{background:#fdecec}} .ft{{font-family:monospace}} .fn{{font-family:monospace;font-size:11.5px;color:{MUTE}}} .fl{{color:{ACC};font-weight:700;font-size:12px}}
.lv{{font-size:9.5px;font-weight:800;border:1.3px solid;border-radius:3px;padding:0 5px;text-align:center}}
.more{{text-align:center;color:{MUTE};font-size:12px;margin-top:6px}}
.lt{{width:100%;border-collapse:collapse;font-size:13px}} .lt th{{text-align:left;font-size:11px;color:{MUTE};letter-spacing:.5px;padding:8px;border-bottom:2px solid {LINE}}}
.lt td{{padding:9px 8px;border-bottom:1px solid #eef0f2}} .lt tr.sel td{{background:#eef4fd}} .lnk{{color:{ACC}}} .dl td{{padding:6px 8px;font-size:12px}}
.hint{{color:{MUTE};font-size:12.5px;margin-top:14px}}
'''

pages = [
 ("Sensors", f"Bag playback, {clk(T_SENS)} CDT. Three cameras and the LiDAR occupancy grid, all recorded fields.", sensors()),
 ("Faults", f"Bag playback, {clk(T_FAULT)} CDT, just after the recorded e-stop. Entries come only from recorded topics.", faults()),
 ("Logs — past runs", "REVIEW mode. One bag exists today.", past_logs()),
 ("Logs — run detail", "REVIEW mode. /rosout lines with recorder and camera-driver lines filtered out. Selected line opens the map at that moment.", log_detail()),
]
html = "".join(f'<section class="page"><h1>{a}</h1><div class="sub">{b}</div>{c}</section>' for a, b, c in pages)
open(OUT_HTML, "w").write(f'<!doctype html><html><head><meta charset="utf-8"><title>CAVS Dashboard Pages Sketch</title><meta name="author" content="Zeenat Islam"><style>{CSS}</style></head><body>{html}</body></html>')
print("ok")
