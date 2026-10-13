# Dashboard sketch generator — CAVS-1 supervisory monitor (v4)
# Author: Zeenat Islam
import json, math

AUTHOR   = "Zeenat Islam"
TEAM     = "Team CAVS-1: Nathan Hester, Chuck, Caleb, Zeenat Islam"
RUN      = "autonomy_demo_0"
RUN_DATE = "11 Sep 2026, 11:45 CDT"
DUR      = 72.1
OUT_HTML = "sketches_v4.html"   # print to PDF at 1400 x 1080 px

D = json.load(open("data.json"))
ODOM, PLAN = D["odom"], D["plan"]

# palette (warm, understated)
INK, MUTE, LINE, PAPER, CARD = "#2f2a26", "#8a817a", "#cfc6bd", "#fbf8f4", "#ffffff"
OK, WARN, BAD, OFF, ACC = "#5f8f5a", "#d39b32", "#c4553f", "#b9b1a9", "#3f6f8f"

EVENTS = [  # t, severity, short label, source text from /rosout
    (8.1,  "info", "Autonomy engaged",            "web: operator sent NavigateThroughPoses 2 wp"),
    (15.5, "warn", "Controller patience exceeded", "controller_server: collision ahead, follow_path aborted"),
    (17.9, "warn", "Cam 2 frame gap 265 ms",       "/cam_2/image_raw"),
    (23.2, "warn", "Slowdown zone",                "collision monitor: action 2 due to SlowdownZone"),
    (25.7, "warn", "Controller patience exceeded", "controller_server: collision ahead, follow_path aborted"),
    (64.7, "bad",  "STOP pressed, e-stop latched", "web_ui / command_arbiter: SOFTWARE E-STOP LATCHED"),
    (65.8, "warn", "Cam 2 frame gap 170 ms",       "/cam_2/image_raw"),
    (67.5, "info", "E-stop cleared",               "web: software e-stop CLEARED by operator"),
]
SEV = {"info": ACC, "warn": WARN, "bad": BAD}
MODES = [(0, 8.2, "MANUAL", OFF), (8.2, 64.7, "AUTONOMY", OK), (64.7, 67.5, "E-STOP", BAD), (67.5, DUR, "MANUAL", OFF)]
SENSORS = [  # name, topic, rate, state, note, gaps
    ("LiDAR",    "/ouster/points",   "10.0 Hz", OK,   "no dropouts", []),
    ("Camera 0", "/cam_0/image_raw", "19.1 Hz", OK,   "no gaps", []),
    ("Camera 1", "/cam_1/image_raw", "19.1 Hz", OK,   "no gaps", []),
    ("Camera 2", "/cam_2/image_raw", "18.9 Hz", WARN, "2 frame gaps", [17.9, 65.8]),
    ("Odometry", "/dlio/odom",       "99.9 Hz", OK,   "no gaps", []),
    ("IMU",      "/ouster/imu",      "99.8 Hz", OK,   "no gaps", []),
    ("GPS",      "no topic in log",  "",        OFF,  "no messages", []),
]

def speed_at(t):
    return min(ODOM, key=lambda p: abs(p[0] - t))

# ---------- components ----------
def topbar(state="Stopped by operator"):
    return f'''<div class="top">
  <div class="brand">CAVS · Run Review</div>
  <div class="runsel">{RUN} <span class="caret">▾</span></div>
  <div class="meta">{RUN_DATE} · NATURE / MTX stack · 3 cams · Ouster LiDAR</div>
  <div class="chip" style="background:{BAD}1a;color:{BAD};border-color:{BAD}">{state}</div>
</div>'''

def menubar(active="Dashboard"):
    tabs = ["Dashboard", "Path Planning", "Faults", "Sensors", "Run Logs"]
    return '<div class="menu">' + "".join(
        f'<div class="tab{" on" if t == active else ""}">{t}</div>' for t in tabs) + "</div>"

def stat(label, val, sub="", color=INK):
    return f'<div class="stat"><div class="sl">{label}</div><div class="sv" style="color:{color}">{val}</div><div class="ss">{sub}</div></div>'

def summary():
    return f'''<div class="panel sum"><div class="ph">Run summary</div>
  <div class="stats">
   {stat("Duration", "72.1 s", "11:45:48 → 11:47:00")}
   {stat("Distance", "29.2 m", "driven")}
   {stat("Autonomy", "56.5 s", "8.2 s → 64.7 s")}
   {stat("Max speed", "2.2 m/s", "at 15.8 s")}
   {stat("Interventions", "1", "operator STOP", BAD)}
   {stat("Goal", "Not reached", "2 waypoints sent", WARN)}
  </div></div>'''

def mapsvg(w, h, upto=DUR, pins=True, highlight=None, plan=True):
    xs = [p[1] for p in ODOM] + [p[0] for p in PLAN]; ys = [p[2] for p in ODOM] + [p[1] for p in PLAN]
    x0, x1, y0, y1 = min(xs) - 2, max(xs) + 2, min(ys) - 2, max(ys) + 2
    s = min((w - 30) / (x1 - x0), (h - 30) / (y1 - y0))
    ox = (w - s * (x1 - x0)) / 2; oy = (h - s * (y1 - y0)) / 2
    X = lambda x: ox + (x - x0) * s
    Y = lambda y: h - (oy + (y - y0) * s)
    g = [f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">']
    for gx in range(int(x0) // 5 * 5, int(x1) + 5, 5):
        g.append(f'<line x1="{X(gx):.1f}" y1="0" x2="{X(gx):.1f}" y2="{h}" stroke="#eee6dd"/>')
    for gy in range(int(y0) // 5 * 5, int(y1) + 5, 5):
        g.append(f'<line x1="0" y1="{Y(gy):.1f}" x2="{w}" y2="{Y(gy):.1f}" stroke="#eee6dd"/>')
    pp = " ".join(f"{X(a):.1f},{Y(b):.1f}" for a, b in PLAN)
    if plan: g.append(f'<polyline points="{pp}" fill="none" stroke="{MUTE}" stroke-width="2.5" stroke-dasharray="7 6"/>')
    for i in range(1, len(ODOM)):
        a, b = ODOM[i - 1], ODOM[i]
        if b[0] > upto: break
        v = b[3]; c = OK if v > 1.0 else (WARN if v > 0.3 else "#a39a92")
        g.append(f'<line x1="{X(a[1]):.1f}" y1="{Y(a[2]):.1f}" x2="{X(b[1]):.1f}" y2="{Y(b[2]):.1f}" stroke="{c}" stroke-width="5" stroke-linecap="round"/>')
    gx, gy = PLAN[-1]
    g.append(f'<circle cx="{X(gx):.1f}" cy="{Y(gy):.1f}" r="9" fill="none" stroke="{INK}" stroke-width="2"/><circle cx="{X(gx):.1f}" cy="{Y(gy):.1f}" r="3" fill="{INK}"/>')
    g.append(f'<text x="{X(gx)+14:.1f}" y="{Y(gy)+5:.1f}" class="mt">Goal (14.5, −12.3)</text>')
    g.append(f'<rect x="{X(0)-6:.1f}" y="{Y(0)-6:.1f}" width="12" height="12" fill="{INK}"/><text x="{X(0)-4:.1f}" y="{Y(0)-14:.1f}" class="mt">Start</text>')
    if pins:
        for n, (t, sv, lab, _) in enumerate(EVENTS, 1):
            if t > upto: continue
            p = speed_at(t); cx, cy = X(p[1]) + (-14 if n in (7,) else 0), Y(p[2]) - 18 - (n % 2) * 18
            hl = highlight == n
            g.append(f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{X(p[1]):.1f}" y2="{Y(p[2]):.1f}" stroke="{SEV[sv]}" stroke-width="1.5"/>')
            g.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{12 if hl else 9}" fill="{SEV[sv]}" stroke="{INK if hl else "#fff"}" stroke-width="{3 if hl else 1.5}"/><text x="{cx:.1f}" y="{cy+4:.1f}" class="pin">{n}</text>')
    cur = speed_at(upto)
    g.append(f'<circle cx="{X(cur[1]):.1f}" cy="{Y(cur[2]):.1f}" r="8" fill="{ACC}" stroke="#fff" stroke-width="3"/>')
    # scale bar
    g.append(f'<line x1="14" y1="{h-14}" x2="{14+5*s:.1f}" y2="{h-14}" stroke="{INK}" stroke-width="2"/><text x="14" y="{h-20}" class="mt">5 m</text>')
    g.append("</svg>")
    return "".join(g)

def mappanel(w, h, upto=DUR, highlight=None, title="Route overview", plan=True):
    legend = f'''<div class="leg"><span><i style="background:{OK}"></i>&gt;1 m/s</span><span><i style="background:{WARN}"></i>0.3–1 m/s</span><span><i style="background:#a39a92"></i>creeping</span>{"<span><i class=dash></i>planned, not driven</span>" if plan else ""}</div>'''
    return f'<div class="panel map" style="width:{w}px;height:{h}px"><div class="ph">{title}<span class="link">Open in Path Planning ›</span></div>{mapsvg(w-24, h-74, upto, True, highlight, plan)}{legend}</div>'

def health(focus=None):
    rows = []
    for name, topic, rate, col, note, _ in SENSORS:
        f = ' focus' if focus == name else ''
        rows.append(f'<div class="hrow{f}"><span class="dot" style="background:{col}"></span><div class="hn">{name}<div class="ht">{topic}</div></div><div class="hr">{rate}<div class="hnote" style="color:{col if col!=OK else MUTE}">{note}</div></div></div>')
    return f'<div class="panel health"><div class="ph">System health · whole run</div>{"".join(rows)}<div class="faultsum"><b style="color:{WARN}">2</b> camera gaps · <b style="color:{OK}">0</b> LiDAR dropouts · <b style="color:{OFF}">–</b> GPS<span class="link">Faults ›</span></div></div>'

def timeline(w, play=DUR, sel=None):
    L, R = 120, w - 24; tw = R - L
    T = lambda t: L + t / DUR * tw
    g = [f'<svg width="{w}" height="200" viewBox="0 0 {w} 200">']
    # axis
    for t in range(0, 75, 5):
        g.append(f'<line x1="{T(t):.1f}" y1="16" x2="{T(t):.1f}" y2="184" stroke="#efe8e0"/><text x="{T(t):.1f}" y="197" class="ax">{t}s</text>')
    lanes = [("Mode", 16), ("Speed", 40), ("Events", 86), ("LiDAR", 112), ("Cameras", 130), ("Odometry", 148), ("GPS", 166)]
    for lab, y in lanes:
        g.append(f'<text x="10" y="{y+12 if lab not in ("Speed",) else y+22}" class="ln">{lab}</text>')
    for a, b, lab, c in MODES:
        g.append(f'<rect x="{T(a):.1f}" y="16" width="{T(b)-T(a):.1f}" height="16" fill="{c}" opacity=".85" rx="3"/>')
        if b - a > 6: g.append(f'<text x="{(T(a)+T(b))/2:.1f}" y="28" class="lw">{lab}</text>')
    pts = " ".join(f"{T(p[0]):.1f},{80-p[3]/2.4*38:.1f}" for p in ODOM)
    g.append(f'<polyline points="{L},80 {pts} {R},80" fill="{ACC}22" stroke="{ACC}" stroke-width="1.6"/>')
    g.append(f'<text x="{L-6}" y="46" class="ax" style="text-anchor:end">2.4</text><text x="{L-6}" y="82" class="ax" style="text-anchor:end">0</text>')
    for n, (t, sv, lab, _) in enumerate(EVENTS, 1):
        r = 11 if sel == n else 8
        g.append(f'<line x1="{T(t):.1f}" y1="36" x2="{T(t):.1f}" y2="180" stroke="{SEV[sv]}" stroke-width="1" stroke-dasharray="2 3" opacity=".7"/>')
        g.append(f'<circle cx="{T(t):.1f}" cy="96" r="{r}" fill="{SEV[sv]}" stroke="{INK if sel==n else "#fff"}" stroke-width="{3 if sel==n else 1.5}"/><text x="{T(t):.1f}" y="100" class="pin">{n}</text>')
    def bar(y, col, gaps=(), gw=0.27):
        s = [f'<rect x="{L}" y="{y}" width="{tw}" height="12" fill="{col}" opacity=".55" rx="2"/>']
        for gt in gaps:
            s.append(f'<rect x="{T(gt)-3:.1f}" y="{y-3}" width="8" height="18" fill="{WARN}" rx="2"/>')
        return "".join(s)
    g.append(bar(112, OK)); g.append(bar(130, OK, [17.9, 65.8])); g.append(bar(148, OK))
    g.append(f'<rect x="{L}" y="166" width="{tw}" height="12" fill="none" stroke="{OFF}" stroke-dasharray="4 4" rx="2"/><text x="{L+8}" y="176" class="ax" style="text-anchor:start">no messages recorded</text>')
    px = T(play)
    g.append(f'<line x1="{px:.1f}" y1="10" x2="{px:.1f}" y2="184" stroke="{INK}" stroke-width="2.5"/><path d="M{px-8:.1f},4 L{px+8:.1f},4 L{px:.1f},14 Z" fill="{INK}"/>')
    g.append("</svg>")
    ctl = f'<div class="ctl"><span class="btn">⏮</span><span class="btn big">▶</span><span class="btn">⏭</span><span class="clock">{play:.1f} / 72.1 s</span><span class="speed">1× ▾</span><span class="hint">Tap an event or drag the playhead</span></div>'
    return f'<div class="panel tl">{ctl}{"".join(g)}</div>'

def frame(body, active="Dashboard", state="Stopped by operator"):
    return f'<div class="tablet"><div class="screen">{topbar(state)}<div class="body">{body}</div>{menubar(active)}</div></div>'

def notes(items):
    return '<div class="notes">' + "".join(f'<div class="note"><span class="nn">{chr(65+i)}</span>{t}</div>' for i, t in enumerate(items)) + "</div>"

def page(title, sub, fr, nts):
    return f'<section class="page"><div class="pt"><h2>{title}</h2><div class="psub">{sub}</div></div>{fr}{notes(nts)}</section>'

CAM2 = [0, 61, 63, 86, 63, 72, 61, 61, 75, 53, 73, 53, 62, 53, 63, 53, 72, 61, 63, 72, 106, 62, 72, 62, 53, 62, 53, 61, 62, 72, 61, 62, 61, 71, 53, 71, 265, 63, 54, 62, 53, 62, 56, 53, 62, 130, 154, 108, 54, 74, 61, 61, 61, 53, 75, 61, 62, 53, 62, 53, 62, 54, 61, 64, 61, 63, 63, 61, 53, 71, 61, 61, 53, 62, 53, 62, 53, 112, 54, 61, 62, 62, 62, 90, 57, 63, 60, 62, 60, 62, 62, 62, 60, 61, 63, 62, 75, 65, 73, 61, 62, 62, 62, 62, 64, 62, 63, 63, 62, 61, 62, 61, 61, 62, 61, 74, 62, 62, 54, 62, 54, 66, 54, 61, 62, 65, 63, 61, 62, 74, 54, 169, 66, 53, 63, 62, 64, 53, 63, 63, 64, 63, 53, 63, 52]
def camchart():
    W, H, L, B, top = 536, 200, 44, 172, 22
    Y = lambda ms: B - min(ms, 280) / 280 * (B - top)
    X = lambda i: L + i * (W - L - 8) / len(CAM2)
    g = [f'<text x="0" y="12" class="ln">Longest frame interval per 0.5 s (ms)</text>']
    for v in (0, 53, 158, 265):
        g.append(f'<line x1="{L}" y1="{Y(v):.1f}" x2="{W-8}" y2="{Y(v):.1f}" stroke="{WARN if v==158 else "#eee6dd"}" {'stroke-dasharray="5 4"' if v==158 else ''}/><text x="{L-6}" y="{Y(v)+4:.1f}" class="ax" style="text-anchor:end">{v}</text>')
    g.append(f'<text x="{X(40):.1f}" y="{Y(158)-5:.1f}" class="ax" style="text-anchor:start">gap threshold: 3 frame periods (158 ms)</text>')
    for i, v in enumerate(CAM2):
        c = WARN if v > 158 else OK
        g.append(f'<rect x="{X(i):.1f}" y="{Y(v):.1f}" width="2.4" height="{B-Y(v):.1f}" fill="{c}"/>')
    g.append(f'<text x="{X(36)+8:.1f}" y="{Y(265)+10:.1f}" class="mt">265 ms at 17.9 s</text>')
    g.append(f'<text x="{X(131)-6:.1f}" y="{Y(169)-6:.1f}" class="mt" style="text-anchor:end">170 ms at 65.8 s</text>')
    for t in range(0, 75, 10):
        g.append(f'<text x="{X(t*2):.1f}" y="{B+16}" class="ax">{t}s</text>')
    return "".join(g)

def evlist(sel=None):
    r = "".join(f'<div class="evr{" sel" if sel==n else ""}"><span class="pinb" style="background:{SEV[sv]}">{n}</span><span class="evt">{t:.1f}s</span>{lab}</div>' for n,(t,sv,lab,_) in enumerate(EVENTS,1))
    return f'<div class="panel ev"><div class="ph">Key events</div>{r}</div>'


# ================= v2: server-hosted supervisory monitor with automatic stop triggers =================
VERSION = "v4"
import base64 as _b64, os as _os
LIDAR_DIR = "lidar_preview"   # PNGs rendered from the bag: /local_costmap/costmap, /global_costmap/costmap, /ouster/reflec_image
LINFO = json.load(open(_os.path.join(LIDAR_DIR, "info.json")))
def _img(name):
    return "data:image/png;base64," + _b64.b64encode(open(_os.path.join(LIDAR_DIR, name + ".png"), "rb").read()).decode()
def _pose(t):
    i = min(range(len(ODOM)), key=lambda k: abs(ODOM[k][0] - t))
    a, b = ODOM[max(i - 4, 0)], ODOM[min(i + 4, len(ODOM) - 1)]
    hd = math.atan2(b[2] - a[2], b[1] - a[1]) if math.dist(a[1:3], b[1:3]) > 0.05 else 0.0
    return ODOM[i][1], ODOM[i][2], hd
def gridview(key, t, px=260, show_scale=True):
    g = LINFO[key]; x, y, hd = _pose(t)
    k = px / g["w"]
    cx = (x - g["ox"]) / g["res"] * k; cy = px - (y - g["oy"]) / g["res"] * k
    L = 16
    tip = (cx + L * math.cos(hd), cy - L * math.sin(hd))
    sv = f'<svg class="gov" width="{px}" height="{px}"><circle cx="{cx:.1f}" cy="{cy:.1f}" r="7" fill="{ACC}" stroke="#fff" stroke-width="2.5"/><line x1="{cx:.1f}" y1="{cy:.1f}" x2="{tip[0]:.1f}" y2="{tip[1]:.1f}" stroke="{ACC}" stroke-width="3"/>'
    if show_scale:
        m5 = 5 / g["res"] * k
        sv += f'<line x1="10" y1="{px-12}" x2="{10+m5:.1f}" y2="{px-12}" stroke="{INK}" stroke-width="2"/><text x="10" y="{px-17}" class="mt">5 m</text>'
    sv += "</svg>"
    return f'<div class="gwrap" style="width:{px}px;height:{px}px"><img src="{_img(key)}" width="{px}" height="{px}">{sv}</div>'
def lidarpanel(t, key):
    g = LINFO[key]
    return f'''<div class="panel lidp"><div class="ph">LiDAR · occupancy grid<span class="tabs2"><b>Grid</b><span>Panorama</span></span></div>
<div class="lidbody">{gridview(key, t, 232)}<div class="lidleg"><div><i style="background:#2f2a26"></i>obstacle</div><div><i style="background:#d39b32"></i>near obstacle</div><div><i style="background:#fbf8f4;border:1px solid #cfc6bd"></i>free</div><div class="lidmeta">30 × 30 m around the vehicle<br>0.2 m cells · 1.7 updates/s<br>≈ {g["png_bytes"]/1000:.1f} kB per update</div></div></div></div>'''
import datetime as _dt
BAG_START = 1789145148.161676535          # first message time in the bag (epoch s)
TZ = _dt.timezone(_dt.timedelta(hours=-5)) # CDT
def clk(t, ms=False):
    d = _dt.datetime.fromtimestamp(BAG_START + t, TZ)
    return d.strftime("%H:%M:%S") + (f".{d.microsecond//100000}" if ms else "")
def day(t=0):
    return _dt.datetime.fromtimestamp(BAG_START + t, TZ).strftime("%a %d %b %Y")
URL = "cavs-server / hci-cavs1"

# Camera-only sensor set (client: 3 cameras are the only sensors in scope); localization kept for the 2D map
SENSORS = [  # name, source, rate, state, note
    ("Camera 0", "/cam_0/image_raw", "19.1 Hz", OK,   "no gaps"),
    ("Camera 1", "/cam_1/image_raw", "19.1 Hz", OK,   "no gaps"),
    ("Camera 2", "/cam_2/image_raw", "18.9 Hz", WARN, "2 frame gaps"),
    ("Localization", "/mtx/odom",    "99.9 Hz", OK,   "no gaps"),
    ("LiDAR", "/ouster/points",       "10.0 Hz", OK,   "no dropouts"),
    ("LiDAR grid", "/local_costmap/costmap", "1.7 Hz", OK, "no gaps"),
]

# Trigger set. action: STOP = publish /mtx/estop true (hand-over to safety driver), ALERT = flag only
TRIGGERS = [  # id, name, signal, threshold, action, first fire in autonomy_demo_0 (None = never)
    ("T1", "Camera frame gap",        "time between frames, any camera", "> 158 ms (3 frames)", "STOP",  17.9),
    ("T2", "Camera rate drop",        "frames per second, 1 s window",   "< 15 Hz",             "STOP",  23.6),
    ("T3", "Camera feed lost",        "no frame received",               "> 0.5 s",             "STOP",  None),
    ("T4", "Localization stale",      "time since last /mtx/odom",       "> 0.2 s",             "STOP",  None),
    ("T5", "Autonomy command stale",  "/mtx/arbiter_status",             "autonomy_cmd_fresh = false", "STOP", None),
    ("T6", "Path follower aborted",   "controller_server log",           "patience exceeded",   "ALERT", 15.5),
    ("T7", "Collision monitor zone",  "/mtx/nav/collision_monitor_state","slowdown or stop zone","ALERT", 23.2),
]
ACT = {"STOP": BAD, "ALERT": WARN}

def chrome(inner, live=True):
    dot = "".join(f'<i style="background:{c}"></i>' for c in ("#e2a59a", "#e8cf98", "#b7cfa8"))
    return f'''<div class="browser"><div class="bbar"><span class="dots">{dot}</span><span class="url">{URL}</span></div><div class="screen">{inner}</div></div>'''

def topbar2(mode, live=True, t=None, banner=None):
    mc = {"AUTONOMY": OK, "MANUAL": OFF, "STOPPED": BAD}[mode]
    lv = f'<span class="live"><i></i>LIVE</span><span class="wclock">{day(t)} · {clk(t)} CDT</span>' if live else f'<span class="live rev">REVIEW</span><span class="wclock">{day()} · {clk(0)}–{clk(DUR)} CDT</span>'
    return f'''<div class="top">
  <div class="brand">CAVS · Supervisory Monitor</div>
  <div class="runsel">{RUN} <span class="caret">▾</span></div>{lv}
  <div class="meta">source: bag playback</div>
  <div class="mode" style="background:{mc}">{mode}</div>
</div>'''

def menubar2(active="Dashboard"):
    tabs = ["Dashboard", "Path Planning", "Faults", "Cameras", "Run Logs", "Triggers"]
    return '<div class="menu">' + "".join(f'<div class="tab{" on" if t == active else ""}">{t}</div>' for t in tabs) + "</div>"

def trigpanel(t, fired=None):
    rows = []
    for tid, name, sig, thr, act, ft in TRIGGERS:
        if fired == tid:
            st, col, val = "FIRED", BAD, "265 ms"
        elif ft is not None and ft <= t:
            st, col, val = ("seen", WARN, f"at {clk(ft)}")
        else:
            st, col, val = ("armed", OK, "")
        cls = " fired" if fired == tid else ""
        rows.append(f'<div class="trow{cls}"><span class="dot" style="background:{col}"></span><div class="tn">{tid} {name}<div class="tt">{thr}</div></div><div class="ta"><span class="act" style="color:{ACT[act]};border-color:{ACT[act]}">{act}</span><div class="tv" style="color:{col if col!=OK else MUTE}">{val or st}</div></div></div>')
    return f'<div class="panel trig"><div class="ph">Stop triggers<span class="link">Edit list ›</span></div>{"".join(rows)}</div>'

def camrow(t, gapcam=None):
    out = []
    for i in range(3):
        bad = gapcam == i
        col = BAD if bad else OK
        lab = "frame gap 265 ms" if bad else "19 Hz"
        out.append(f'<div class="cam2{" bad" if bad else ""}"><svg width="100%" height="100%"><line x1="0" y1="0" x2="100%" y2="100%" stroke="{LINE}"/><line x1="100%" y1="0" x2="0" y2="100%" stroke="{LINE}"/></svg><span class="cl">Cam {i}</span><span class="cr" style="color:{col}">● {lab}</span></div>')
    return f'<div class="panel camp"><div class="ph">Cameras · preview 1 frame/s<span class="link">Cameras ›</span></div><div class="camrow2">{"".join(out)}</div></div>'

def linkpanel():
    return f'''<div class="panel linkp"><div class="ph">Link to vehicle</div>
<div class="kv"><span>Data to browser</span><b>≈ 50 kB/s</b></div>
<div class="kv"><span>Last message</span><b style="color:{OK}">0.1 s ago</b></div></div>'''

def evlog(t, extra=None):
    ev = [(8.1, ACC, "Autonomy engaged, 2 waypoints"), (15.5, WARN, "T6 Path follower aborted"), (17.9, BAD, "T1 Camera 2 frame gap 265 ms"), (23.2, WARN, "T7 Slowdown zone"), (23.6, BAD, "T2 Camera 2 at 14 Hz")]
    rows = [e for e in ev if e[0] <= t]
    if extra: rows.append(extra)
    r = "".join(f'<div class="evr"><span class="dot" style="background:{c}"></span><span class="evt">{clk(tt)}</span>{lab}</div>' for tt, c, lab in reversed(rows))
    return f'<div class="panel ev2"><div class="ph">Event log<span class="link">Run Logs ›</span></div>{r}</div>'

def strip(w, t, stop_at=None):
    L, R = 110, w - 20; tw = R - L
    T = lambda x: L + x / DUR * tw
    g = [f'<svg width="{w}" height="74" viewBox="0 0 {w} 74">']
    g.append(f'<text x="8" y="22" class="ln">Mode</text><text x="8" y="52" class="ln">Speed</text>')
    end = min(t, DUR)
    segs = [(0, 8.2, OFF, "MANUAL"), (8.2, stop_at or end, OK, "AUTONOMY")]
    if stop_at: segs.append((stop_at, end, BAD, "STOPPED"))
    for a, b, c, lab in segs:
        if b <= a: continue
        g.append(f'<rect x="{T(a):.1f}" y="10" width="{T(b)-T(a):.1f}" height="16" fill="{c}" opacity=".85" rx="3"/>')
        if T(b) - T(a) > 70: g.append(f'<text x="{(T(a)+T(b))/2:.1f}" y="22" class="lw">{lab}</text>')
    g.append(f'<rect x="{T(end):.1f}" y="10" width="{R-T(end):.1f}" height="16" fill="none" stroke="{LINE}" stroke-dasharray="4 4" rx="3"/>')
    pts = " ".join(f"{T(p[0]):.1f},{64-p[3]/2.4*26:.1f}" for p in ODOM if p[0] <= end)
    g.append(f'<polyline points="{L},64 {pts} {T(end):.1f},64" fill="{ACC}22" stroke="{ACC}" stroke-width="1.6"/>')
    g.append(f'<line x1="{T(end):.1f}" y1="4" x2="{T(end):.1f}" y2="70" stroke="{INK}" stroke-width="2.5"/>')
    g.append("</svg>")
    return f'<div class="panel strip">{"".join(g)}</div>'

def livebody(t, fired=None):
    mapw = 560
    m = mappanel(mapw, 300 if fired else 336, upto=t, title="Route · 2D", plan=False)
    return f'''<div class="col l">{trigpanel(t, fired)}</div>
<div class="col c">{camrow(t, 2 if fired else None)}{m}</div>
<div class="col r">{lidarpanel(t, "local_17" if fired else "local_12")}{evlog(t, (17.9, BAD, "STOP sent on /mtx/estop · safety driver in control") if fired else None)}</div>
<div class="row">{strip(1232, t, 17.9 if fired else None)}</div>'''

def frame2(body, mode, live=True, t=None, banner=None, active="Dashboard", cls=""):
    ban = f'<div class="banner">{banner}</div>' if banner else ""
    return chrome(f'{topbar2(mode, live, t)}{ban}<div class="body b2 {cls}">{body}</div>{menubar2(active)}')

# event pins on map: only trigger events in v2
EVENTS = [
    (8.1,  "info", "Autonomy engaged", ""),
    (15.5, "warn", "T6 Path follower aborted", ""),
    (17.9, "bad",  "T1 Cam 2 gap 265 ms", ""),
    (23.2, "warn", "T7 Slowdown zone", ""),
    (23.6, "bad",  "T2 Cam 2 at 14 Hz", ""),
    (25.7, "warn", "T6 Path follower aborted", ""),
    (64.7, "info", "Operator STOP (actual)", ""),
    (65.8, "bad",  "T1 Cam 2 gap 170 ms", ""),
]

def timeline2(w, play=DUR, sel=None):
    L, R = 120, w - 24; tw = R - L
    T = lambda t: L + t / DUR * tw
    g = [f'<svg width="{w}" height="200" viewBox="0 0 {w} 200">']
    off = 5 - (BAG_START % 5)
    for k in range(15):
        t = off + 5 * k
        if t > DUR: break
        g.append(f'<line x1="{T(t):.1f}" y1="16" x2="{T(t):.1f}" y2="184" stroke="#efe8e0"/><text x="{T(t):.1f}" y="197" class="ax">{clk(t)}</text>')
    for lab, y in [("Mode", 28), ("Speed", 62), ("Triggers", 100), ("Camera 0", 124), ("Camera 1", 142), ("Camera 2", 160), ("Localization", 178)]:
        g.append(f'<text x="10" y="{y}" class="ln">{lab}</text>')
    for a, b, lab, c in [(0, 8.2, "MANUAL", OFF), (8.2, 64.7, "AUTONOMY", OK), (64.7, 67.5, "E-STOP", BAD), (67.5, DUR, "MANUAL", OFF)]:
        g.append(f'<rect x="{T(a):.1f}" y="16" width="{T(b)-T(a):.1f}" height="16" fill="{c}" opacity=".85" rx="3"/>')
        if b - a > 6: g.append(f'<text x="{(T(a)+T(b))/2:.1f}" y="28" class="lw">{lab}</text>')
    pts = " ".join(f"{T(p[0]):.1f},{78-p[3]/2.4*36:.1f}" for p in ODOM)
    g.append(f'<polyline points="{L},78 {pts} {R},78" fill="{ACC}22" stroke="{ACC}" stroke-width="1.6"/>')
    # would-have-stopped marker
    g.append(f'<line x1="{T(17.9):.1f}" y1="12" x2="{T(17.9):.1f}" y2="184" stroke="{BAD}" stroke-width="2"/>')
    g.append(f'<rect x="{T(17.9)+4:.1f}" y="36" width="168" height="16" rx="3" fill="{BAD}"/><text x="{T(17.9)+10:.1f}" y="48" class="lw" style="text-anchor:start">trigger stop at {clk(17.9)}</text>')
    for n, (t, sv, lab, _) in enumerate(EVENTS, 1):
        r = 11 if sel == n else 8
        g.append(f'<circle cx="{T(t):.1f}" cy="96" r="{r}" fill="{SEV[sv]}" stroke="{INK if sel==n else "#fff"}" stroke-width="{3 if sel==n else 1.5}"/><text x="{T(t):.1f}" y="100" class="pin">{n}</text>')
    for y, gaps in [(114, []), (132, []), (150, [17.9, 65.8]), (168, [])]:
        g.append(f'<rect x="{L}" y="{y}" width="{tw}" height="12" fill="{OK}" opacity=".55" rx="2"/>')
        for gt in gaps:
            g.append(f'<rect x="{T(gt)-3:.1f}" y="{y-3}" width="8" height="18" fill="{BAD}" rx="2"/>')
    px = T(play)
    g.append(f'<line x1="{px:.1f}" y1="10" x2="{px:.1f}" y2="184" stroke="{INK}" stroke-width="2.5"/><path d="M{px-8:.1f},4 L{px+8:.1f},4 L{px:.1f},14 Z" fill="{INK}"/>')
    g.append("</svg>")
    ctl = f'<div class="ctl"><span class="btn">⏮</span><span class="btn big">▶</span><span class="btn">⏭</span><span class="clock">{clk(play, True)}</span><span class="ax2">{play:.1f} s of 72.1 s</span><span class="speed">1× ▾</span><span class="hint">Click an event or drag the playhead</span></div>'
    return f'<div class="panel tl">{ctl}{"".join(g)}</div>'

def health2():
    rows = "".join(f'<div class="hrow"><span class="dot" style="background:{col if col!=WARN else BAD}"></span><div class="hn">{n}<div class="ht">{src}</div></div><div class="hr">{rate}<div class="hnote" style="color:{BAD if col==WARN else MUTE}">{note}</div></div></div>' for n, src, rate, col, note in SENSORS)
    return f'<div class="panel health"><div class="ph">Feed health · whole run</div>{rows}</div>'

def compare():
    return f'''<div class="panel cmp"><div class="ph">Replayed against the trigger list</div>
<div class="cmpg"><div><span>Actual stop</span><b>{clk(64.7)}</b><em>operator STOP</em></div><div class="hl"><span>With triggers</span><b style="color:{BAD}">{clk(17.9)}</b><em>T1 Camera 2 frame gap</em></div></div>
<div class="kv"><span>Autonomy that would not have run</span><b>46.8 s</b></div>
<div class="kv"><span>STOP conditions met</span><b>3 (T1 ×2, T2 ×1)</b></div>
<div class="kv"><span>Alerts</span><b>3 (T6 ×2, T7 ×1)</b></div></div>'''

def evlist2(sel=None):
    r = "".join(f'<div class="evr{" sel" if sel==n else ""}"><span class="pinb" style="background:{SEV[sv]}">{n}</span><span class="evt">{clk(t)}</span>{lab}</div>' for n,(t,sv,lab,_) in enumerate(EVENTS,1))
    return f'<div class="panel ev"><div class="ph">Events</div>{r}</div>'

def trigtable():
    head = "<tr><th>ID</th><th>Trigger</th><th>Signal watched</th><th>Threshold</th><th>Action</th><th>Fired in autonomy_demo_0</th></tr>"
    rows = "".join(f'<tr><td><b>{tid}</b></td><td>{n}</td><td class="mono">{sig}</td><td>{thr}</td><td><span class="act" style="color:{ACT[a]};border-color:{ACT[a]}">{a}</span></td><td>{"" if ft is None else f"first at {clk(ft)} ({ft:.1f} s"}</td></tr>' for tid, n, sig, thr, a, ft in TRIGGERS)
    return f'''<div class="tpage"><div class="ph" style="font-size:14px">Stop trigger list</div><table class="tt2">{head}{rows}</table>
<div class="tfoot"><div><b style="color:{BAD}">STOP</b> publishes <span class="mono">/mtx/estop = true</span> once, from a trigger monitor node running beside the vehicle stack, so a stop does not depend on the network link. The vehicle halts and the safety driver takes over. The interface has no Go or resume control.</div>
<div><b style="color:{WARN}">ALERT</b> flags the event on the dashboard and in the log. Driving continues.</div>
<div>Every trigger is computed from message timing and small status topics. No image or point-cloud payload is needed to evaluate them.</div></div></div>'''

def dataflow():
    raw = [("3 cameras, raw", "2048 × 1536 mono8 · 19 Hz each", "≈ 179 MB/s", BAD),
           ("Ouster LiDAR point cloud, raw", "6.3 MB per scan · 10 Hz", "≈ 63 MB/s", BAD),
           ("3D map / point cloud view", "", "not sent", OFF)]
    sent = [("Trigger states", "from the trigger monitor node", "< 1 kB/s", OK),
            ("Vehicle pose for 2D map", "/mtx/odom throttled to 5 Hz", "≈ 4 kB/s", OK),
            ("Status + log lines", "/mtx/arbiter_status, /rosout", "≈ 2 kB/s", OK),
            ("Camera previews", "3 × 320 × 240 JPEG · 1 frame/s", "≈ 45 kB/s", OK),
            ("LiDAR occupancy grid", "150 × 150 PNG · 1.7 updates/s", "≈ 2 kB/s", OK),
            ("LiDAR panorama (when opened)", "1024 × 128 JPEG · 1 frame/s", "≈ 22 kB/s", OK)]
    tr = lambda r: "".join(f'<tr><td><span class="dot" style="background:{c}"></span>{a}</td><td class="mono">{b}</td><td><b>{v}</b></td></tr>' for a, b, v, c in r)
    return f'''<div class="flow">
<div class="fbox">ROS 2 bag playback<small>stands in for the vehicle now<br>+ trigger monitor node</small></div><div class="farrow">rosbridge<br><small>filtered, throttled topics</small></div>
<div class="fbox">CAVS server<small>hosts the interface<br>keeps run history</small></div><div class="farrow">websocket<br><small>≈ 50–75 kB/s</small></div>
<div class="fbox">Browser<small>any desktop<br>no install</small></div></div>
<div class="ftables"><div><div class="ph">Stays on the vehicle side</div><table class="tt2">{tr(raw)}</table></div>
<div><div class="ph">Sent to the browser</div><table class="tt2">{tr(sent)}</table></div></div>
<div class="fsum"><b>≈ 50–75 kB/s</b> to the browser against <b>≈ 240 MB/s</b> of raw camera and LiDAR data on the vehicle.</div>'''


def lidarpage():
    g = LINFO["local_17"]; pr = LINFO["ouster_reflec"]
    rows = [("Occupancy grid", "/local_costmap/costmap", "already built by Nav2 from the LiDAR", "int8 grid → PNG, 0.2 ms", f"≈ {g['png_bytes']/1000:.1f} kB × 1.7/s", OK),
            ("Panorama image", "/ouster/reflec_image", "already built by the Ouster driver", "16-bit → 8-bit JPEG, 0.5 ms", f"≈ {pr['jpg_bytes']/1000:.0f} kB × 1/s, only while open", OK),
            ("Raw point cloud", "/ouster/points", "", "not sent", "6.3 MB × 10/s", OFF)]
    tr = "".join(f'<tr><td><span class="dot" style="background:{c}"></span><b>{a}</b></td><td class="mono">{b}</td><td>{d}</td><td>{e}</td><td><b>{v}</b></td></tr>' for a, b, d, e, v, c in rows)
    pano = f'<div class="pano"><img src="{_img("ouster_reflec")}" width="1180" height="148"><span>LiDAR panorama · reflectivity · {clk(pr["t"])} CDT · 1024 × 128</span></div>'
    return f'''<div class="lpg"><div class="lpg1">
<div class="panel"><div class="ph">Occupancy grid<span class="tabs2"><b>Grid</b><span>Panorama</span></span></div>{gridview("local_17", 17.9, 300)}<div class="lidmeta" style="margin-top:6px">{clk(g["t"])} CDT · 30 × 30 m · 0.2 m cells</div></div>
<div class="panel lpt"><div class="ph">How each LiDAR view is made</div><table class="tt2"><tr><th>View</th><th>Source topic</th><th>Origin</th><th>Server step</th><th>To browser</th></tr>{tr}</table>
<div class="lnote">Both views reuse images the vehicle software already produces. The server only compresses them, so no point-cloud processing is added.</div></div></div>
<div class="panel">{pano}</div></div>'''

# ---------- pages ----------
P = []
P.append(f'''<section class="page cover"><div class="cv">
<div class="kicker">CAVS Off-Road Proving Ground · Autonomous Vehicle Testing</div>
<h1>Supervisory Monitor</h1><div class="h1s">Dashboard sketches · {VERSION}</div>
<div class="cvmeta">
<div><b>Use case</b><span>Watch an autonomy run and stop the vehicle automatically when a listed trigger fires. The safety driver then takes over. Runs can be reviewed afterwards.</span></div>
<div><b>Where it runs</b><span>Web interface hosted on a CAVS server, opened in a desktop browser</span></div>
<div><b>Sensors in scope</b><span>The 3 vehicle cameras, plus LiDAR shown as a 2D occupancy grid or a 2D panorama image. No raw point cloud and no 3D view in the browser.</span></div>
<div><b>Backend</b><span>The provided ROS 2 bag {RUN}, played back as a mock live session. The interface shows the recording\'s own date and time ({day()}, {clk(0)}–{clk(DUR)} CDT), as if the run were happening now.</span></div>
<div><b>Pages</b><span>1 Live, normal · 2 Live, trigger fired · 3 Run review · 4 LiDAR view · 5 Trigger list · 6 Data budget · 7 Navigation</span></div>
</div>
<div class="by">{AUTHOR}<br><span>{TEAM}</span></div></div></section>''')

P.append(page("1 · Dashboard, live — normal driving", f"Mock live session from the bag, {day(12.0)} at {clk(12.0)} CDT. Autonomy active, every trigger armed.",
  frame2(livebody(12.0), "AUTONOMY", True, 12.0),
  ["The clock shows the date and time the bag was recorded, advancing with playback, so the session reads as live.",
   "Trigger list on the left shows each stop condition and its live state. Green means armed and not met.",
   "Camera previews refresh once per second. LiDAR is shown as a 2D occupancy grid centred on the vehicle, never as a point cloud.",
   "Route is drawn in 2D from the vehicle pose only.",
   "No drive controls. A person in the vehicle can always take over."]))

P.append(page("2 · Dashboard, live — trigger fired", f"Same session at {clk(17.9)} CDT. Camera 2 goes 265 ms without a frame, so T1 fires.",
  frame2(livebody(17.9, fired="T1"), "STOPPED", True, 17.9,
         banner=f'<b>STOP sent · {clk(17.9, True)}</b> T1 Camera frame gap: Camera 2, 265 ms (limit 158 ms). Vehicle halted, safety driver in control.'),
  ["A full-width banner states which trigger fired, the measured value against its limit, and that the stop was sent.",
   "The tripped trigger and camera are outlined in red. The other triggers keep their state.",
   "The stop is sent once and is not repeated. Resuming autonomy is done from the vehicle, not from this screen."]))

body3 = f'''<div class="col l">{compare()}{evlist2(sel=3)}</div>
<div class="col c">{mappanel(560, 428, title="Route · 2D")}</div>
<div class="col r">{health2()}</div>
<div class="row">{timeline2(1232, play=17.9, sel=3)}</div>'''
P.append(page("3 · Dashboard, review — after the run", "The full run on one time axis, with the trigger list applied to the recorded data.",
  frame2(body3, "MANUAL", False, cls="rev"),
  [f"Comparison card: the operator stopped this run at {clk(64.7)}. With the trigger list, the stop would have come at {clk(17.9)}, 46.8 s earlier.",
   "Timeline lanes are the mode, speed, trigger events and one lane per camera plus localization.",
   "Clicking an event moves the map, camera frames and log to that moment."]))

P.append(page("4 · LiDAR view", "LiDAR reaches the browser only as a 2D image: an occupancy grid by default, or a panorama when the panel is switched.",
  chrome(f'{topbar2("STOPPED", True, 17.9)}<div class="body b3">{lidarpage()}</div>{menubar2("Dashboard")}'),
  ["The grid is a top-down 30 × 30 m view centred on the vehicle. Dark cells are obstacles, amber cells are close to one.",
   "The panorama shows the full 360° LiDAR sweep as a flat image. It is sent only while someone has it open.",
   "Neither view needs the raw point cloud in the browser."]))

P.append(page("5 · Trigger list", "The conditions that stop the vehicle. Thresholds are first proposals and can be tuned with CAVS.",
  chrome(f'{topbar2("MANUAL", False)}<div class="body b3">{trigtable()}</div>{menubar2("Triggers")}'),
  ["T1–T3 cover the three cameras. T4–T5 cover localization and the autonomy command link.",
   "T6–T7 are alerts only, since the navigation stack already slows or replans for them.",
   "The last column comes from replaying the provided bag."]))

P.append(page("6 · Data budget", "Why the interface stays light: triggers are evaluated on the vehicle side, and only small summaries reach the browser.",
  chrome(f'{topbar2("MANUAL", False)}<div class="body b3">{dataflow()}</div>{menubar2("Dashboard")}'),
  ["Raw sizes are measured from the bag: each camera frame is 3.1 MB and each point cloud 6.3 MB.",
   "Previews and pose are throttled before they leave the server, so several people can watch at once.",
   "The same layout works with the recorded bag now and with the live vehicle later."]))

nav = f'''<div class="navmap">
<div class="nb hub">Dashboard<small>live monitor · review · triggers</small><small class="own">Zeenat</small></div>
<div class="nb n1">Path Planning<small>waypoints, distance, obstacles (2D)</small><small class="own">Nathan</small></div>
<div class="nb n2">Faults<small>colour-coded camera and system faults</small><small class="own">Caleb</small></div>
<div class="nb n3">Cameras<small>3 camera previews</small><small class="own">Caleb</small></div>
<div class="nb n4">Run Logs<small>previous runs, status</small><small class="own">Chuck</small></div>
<svg class="lines" width="1232" height="560"><g stroke="{MUTE}" stroke-width="2" fill="none">
<path d="M500 280 L250 140"/><path d="M732 280 L982 140"/><path d="M500 330 L250 440"/><path d="M732 330 L982 440"/></g></svg>
<div class="lab l1">route map → Path Planning</div><div class="lab l2">trigger / feed health → Faults</div>
<div class="lab l3">camera previews → Cameras</div><div class="lab l4">run selector, event log → Run Logs</div>
<div class="shared">Shared on every page: run selector, LIVE / REVIEW state and mode chip (top), playhead time, menu bar</div></div>'''
P.append(page("7 · Navigation", "Where the dashboard hands off to the other pages in the team’s design.", chrome(f'<div class="navs">{nav}</div>'),
  ["The dashboard is the hub. Each panel links to the page that owns its detail.",
   "The selected run and playhead time carry over between pages."]))

CSS = f'''
@page {{ size: 1400px 1080px; margin:0 }}
*{{box-sizing:border-box}} body{{margin:0;font-family:Inter,Helvetica,Arial,sans-serif;color:{INK};background:#efe9e2}}
.page{{width:1400px;height:1060px;padding:26px 60px;page-break-after:always;position:relative}}
.pt h2{{margin:0;font-size:24px;font-weight:650}} .psub{{color:{MUTE};font-size:15px;margin:4px 0 14px}}
.tablet{{width:1280px;height:820px;background:#2b2724;border-radius:28px;padding:10px;box-shadow:0 8px 24px #0002}}
.screen{{width:100%;height:100%;background:{PAPER};border-radius:18px;overflow:hidden;display:flex;flex-direction:column}}
.top{{height:52px;display:flex;align-items:center;gap:18px;padding:0 18px;border-bottom:1px solid {LINE};background:#fff}}
.brand{{font-weight:750;letter-spacing:.3px}} .runsel{{border:1px solid {LINE};border-radius:8px;padding:6px 12px;font-family:monospace;font-size:14px}}
.caret{{color:{MUTE}}} .meta{{color:{MUTE};font-size:13px;flex:1}}
.chip{{border:1.5px solid;border-radius:20px;padding:5px 14px;font-weight:650;font-size:13px}}
.body{{flex:1;min-height:0;display:grid;grid-template-columns:300px 560px 1fr;grid-template-rows:minmax(0,1fr) 236px;gap:10px;padding:10px 12px}}
.row{{grid-column:1/4}} .col{{display:flex;flex-direction:column;gap:10px;min-height:0}}
.menu{{height:54px;display:flex;border-top:1px solid {LINE};background:#fff}}
.tab{{flex:1;display:flex;align-items:center;justify-content:center;font-weight:600;color:{MUTE};font-size:15px}}
.tab.on{{color:{INK};box-shadow:inset 0 4px 0 {ACC};background:#f4efe9}}
.panel{{background:{CARD};border:1px solid {LINE};border-radius:12px;padding:10px 12px;overflow:hidden}}
.ph{{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;color:{MUTE};margin-bottom:8px;display:flex;justify-content:space-between}}
.link{{color:{ACC};text-transform:none;letter-spacing:0;font-weight:600;font-size:13px}}
.stats{{display:grid;grid-template-columns:1fr 1fr;gap:6px}} .stat{{background:{PAPER};border-radius:8px;padding:5px 9px}}
.sl{{font-size:11px;color:{MUTE}}} .sv{{font-size:17px;font-weight:700;line-height:1.2}} .ss{{font-size:10px;color:{MUTE};line-height:1.1}} .sl{{line-height:1.1}}
.ev{{flex:1;padding-bottom:4px}} .evr.sel{{background:{WARN}22;border-radius:6px}} .evr{{display:flex;align-items:center;gap:8px;font-size:12px;padding:1px 0;line-height:1.15;border-bottom:1px dashed #eee5dc}}
.pinb{{display:inline-flex;width:18px;height:18px;border-radius:50%;color:#fff;font-size:11px;font-weight:700;align-items:center;justify-content:center;flex:none}}
.evt{{font-family:monospace;color:{MUTE};width:64px;flex:none}}
.map svg{{display:block}} .mt{{font-size:12px;fill:{INK};font-weight:600}} .pin{{font-size:11px;fill:#fff;font-weight:700;text-anchor:middle}}
.leg{{display:flex;gap:14px;font-size:11.5px;color:{MUTE};margin-top:6px}} .leg i{{display:inline-block;width:16px;height:5px;margin-right:5px;vertical-align:middle;border-radius:2px}}
.leg i.dash{{border-top:2.5px dashed {MUTE};height:0}}
.health{{height:100%;display:flex;flex-direction:column}} .hrow{{display:flex;align-items:center;gap:10px;padding:7px 6px;border-bottom:1px solid #f1ebe4;border-radius:8px}}
.hrow.focus{{background:{WARN}22;outline:2px solid {WARN}}}
.dot{{width:13px;height:13px;border-radius:50%;flex:none}} .hn{{flex:1;font-weight:600;font-size:14px}} .ht{{font-family:monospace;font-size:10.5px;color:{MUTE};font-weight:400}}
.hr{{text-align:right;font-weight:700;font-size:14px}} .hnote{{font-size:11px;font-weight:600}}
.faultsum{{margin-top:auto;font-size:12.5px;color:{MUTE};display:flex;gap:4px;align-items:center;padding-top:8px}} .faultsum .link{{margin-left:auto}}
.tl{{padding:6px 12px;height:236px}} .ctl{{display:flex;align-items:center;gap:10px;font-size:13px}}
.btn{{width:30px;height:26px;border:1px solid {LINE};border-radius:6px;display:inline-flex;align-items:center;justify-content:center}} .btn.big{{background:{INK};color:#fff;width:40px}}
.clock{{font-family:monospace;font-weight:700}} .speed{{border:1px solid {LINE};border-radius:6px;padding:2px 8px}} .hint{{margin-left:auto;color:{MUTE};font-size:12px}}
.ax{{font-size:10px;fill:{MUTE};text-anchor:middle}} .ln{{font-size:11.5px;fill:{INK};font-weight:600}} .lw{{font-size:10.5px;fill:#fff;font-weight:700;text-anchor:middle}}
.det{{height:100%}} .dh{{border-left:5px solid;padding:6px 10px;font-weight:700;font-size:16px;margin-bottom:10px;display:flex;flex-wrap:wrap;gap:8px;align-items:center;background:{PAPER};border-radius:6px}}
.dts{{width:100%;font-size:11.5px;color:{MUTE};font-weight:500}} .kv{{display:flex;justify-content:space-between;font-size:13px;padding:4px 0;border-bottom:1px dashed #eee5dc}} .kv span{{color:{MUTE}}}
.logx{{margin-top:10px;background:#2b2724;color:#e9e1d8;border-radius:8px;padding:8px;font-family:monospace;font-size:10.5px;line-height:1.55}} .lh{{color:#a39a92;margin-bottom:3px}}
.cams{{flex:1}} .camrow{{display:flex;gap:8px;height:80px}} .cam{{flex:1;position:relative;background:{PAPER};border:1px solid {LINE};border-radius:6px}}
.cam span{{position:absolute;left:6px;bottom:4px;font-size:10.5px;color:{MUTE};background:#fff;padding:0 4px}}
.fz{{flex:1}} .fzr{{display:flex;gap:8px}} .fzr div{{flex:1;background:{PAPER};border-radius:8px;padding:6px 8px}} .fzr b{{display:block;font-size:17px}} .fzr span{{font-size:11px;color:{MUTE}}}
.fc{{display:flex;align-items:center;gap:8px;font-size:13px;padding:3px 0}} .fc b{{margin-left:auto;color:{MUTE};font-weight:600}}
.notes{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px 22px;margin-top:14px}}
.note{{font-size:12.5px;line-height:1.4;display:flex;gap:8px}} .nn{{flex:none;width:20px;height:20px;border-radius:50%;background:{INK};color:#fff;font-size:11px;font-weight:700;display:inline-flex;align-items:center;justify-content:center}}
.cover{{display:flex;align-items:center;background:{PAPER}}} .cv{{padding:0 60px}} .kicker{{color:{ACC};font-weight:700;letter-spacing:.5px;text-transform:uppercase;font-size:15px}}
h1{{font-size:62px;margin:12px 0 4px}} .h1s{{font-size:26px;color:{MUTE}}}
.cvmeta{{margin:48px 0;display:grid;gap:14px;font-size:18px;max-width:900px}} .cvmeta>div{{display:flex}} .cvmeta b{{flex:none;width:250px;color:{MUTE};font-weight:600}}
.by{{font-size:20px;font-weight:700}} .by span{{font-size:15px;color:{MUTE};font-weight:500}}
.navs{{position:relative}} .navmap{{position:relative;width:100%;height:100%;padding:20px}} .lines{{position:absolute;left:14px;top:120px}}
.nb{{position:absolute;width:300px;background:#fff;border:2px solid {LINE};border-radius:14px;padding:16px 18px;font-size:22px;font-weight:700;z-index:2}}
.nb small{{display:block;font-size:13px;color:{MUTE};font-weight:500;margin-top:4px}} .nb .own{{color:{ACC};font-weight:700}}
.hub{{left:466px;top:330px;border-color:{ACC};border-width:3px;box-shadow:0 0 0 6px {ACC}22}}
.n1{{left:60px;top:150px}} .n2{{right:60px;top:150px}} .n3{{left:60px;top:540px}} .n4{{right:60px;top:540px}}
.lab{{position:absolute;font-size:13px;color:{INK};background:{PAPER};padding:2px 6px;border-radius:4px;z-index:3}}
.l1{{left:300px;top:300px}} .l2{{left:770px;top:300px}} .l3{{left:300px;top:480px}} .l4{{left:770px;top:480px}}
.shared{{position:absolute;left:20px;right:20px;bottom:20px;text-align:center;font-size:14px;color:{MUTE};border-top:1px dashed {LINE};padding-top:12px}}
'''
CSS += f'''
.page{{height:1080px}}
.browser{{width:1280px;height:830px;background:#ddd5cc;border-radius:12px;padding:0 6px 6px;box-shadow:0 8px 24px #0002;display:flex;flex-direction:column}}
.bbar{{height:34px;display:flex;align-items:center;gap:14px;padding:0 10px}} .dots i{{display:inline-block;width:11px;height:11px;border-radius:50%;margin-right:6px}}
.url{{flex:1;background:#f6f1eb;border-radius:7px;padding:4px 12px;font-size:12.5px;color:{MUTE};max-width:520px}}
.browser .screen{{flex:1;border-radius:6px;min-height:0}}
.live{{display:flex;align-items:center;gap:6px;font-weight:700;font-size:13px;color:{BAD}}} .live i{{width:9px;height:9px;border-radius:50%;background:{BAD};display:inline-block}}
.live.rev{{color:{ACC}}} .wclock{{font-family:monospace;font-size:14px;font-weight:700;background:{PAPER};border:1px solid {LINE};border-radius:6px;padding:4px 10px}} .ax2{{font-size:11.5px;color:{MUTE}}}
.mode{{color:#fff;font-weight:800;letter-spacing:1px;border-radius:8px;padding:7px 18px;font-size:15px}}
.banner{{background:{BAD};color:#fff;padding:9px 18px;font-size:15px}} .banner b{{margin-right:10px}}
.b2{{grid-template-rows:minmax(0,1fr) 96px}} .b2.rev{{grid-template-rows:minmax(0,1fr) 236px}}
.b3{{display:block;padding:16px 22px;overflow:hidden}}
.trig{{height:100%}} .trow{{display:flex;align-items:center;gap:9px;padding:6px 6px;border-bottom:1px solid #f1ebe4;border-radius:8px}}
.trow.fired{{background:{BAD}18;outline:2px solid {BAD}}}
.tn{{flex:1;font-weight:600;font-size:13px}} .tt{{font-size:11px;color:{MUTE};font-weight:500}}
.ta{{text-align:right}} .act{{font-size:10px;font-weight:800;border:1.5px solid;border-radius:4px;padding:0 5px;letter-spacing:.5px}}
.tv{{font-size:11px;font-weight:600;margin-top:2px}}
.camp{{flex:none}} .camrow2{{display:flex;gap:8px;height:140px}} .cam2{{flex:1;position:relative;background:{PAPER};border:1px solid {LINE};border-radius:6px}}
.cam2.bad{{outline:3px solid {BAD}}} .cam2 .cl,.cam2 .cr{{position:absolute;bottom:4px;font-size:11px;background:#fff;padding:0 5px;border-radius:3px;font-weight:600}}
.cl{{left:6px}} .cr{{right:6px}}
.linkp{{flex:none}} .ev2{{flex:1}} .ev2 .evr{{font-size:12.5px;padding:5px 0}}
.strip{{padding:6px 12px}}
.cmp{{flex:none}} .cmpg{{display:flex;gap:8px;margin-bottom:6px}} .cmpg div{{flex:1;background:{PAPER};border-radius:8px;padding:6px 9px}}
.cmpg span{{display:block;font-size:11px;color:{MUTE}}} .cmpg b{{font-size:20px}} .cmpg em{{display:block;font-size:10.5px;color:{MUTE};font-style:normal}}
.cmpg .hl{{outline:2px solid {BAD}}}
.tt2{{width:100%;border-collapse:collapse;font-size:14px}} .tt2 th{{text-align:left;font-size:11.5px;color:{MUTE};text-transform:uppercase;letter-spacing:.5px;padding:8px;border-bottom:2px solid {LINE}}}
.tt2 td{{padding:10px 8px;border-bottom:1px solid #eee5dc;vertical-align:middle}} .mono{{font-family:monospace;font-size:12px;color:#5b534d}}
.tt2 .dot{{display:inline-block;margin-right:8px;vertical-align:middle}}
.tfoot{{margin-top:18px;display:grid;gap:8px;font-size:14px;line-height:1.45}}
.flow{{display:flex;align-items:center;gap:10px;margin:6px 0 22px}} .fbox{{flex:1;background:#fff;border:2px solid {ACC};border-radius:12px;padding:14px 16px;font-size:20px;font-weight:700}}
.fbox small{{display:block;font-size:12.5px;color:{MUTE};font-weight:500;margin-top:4px}} .farrow{{width:170px;text-align:center;font-weight:700;font-size:13px;position:relative;padding-bottom:12px;border-bottom:3px solid {MUTE}}}
.farrow small{{font-weight:500;color:{MUTE}}} .farrow:after{{content:"";position:absolute;right:-2px;bottom:-8px;border:7px solid transparent;border-left:11px solid {MUTE}}}
.ftables{{display:grid;grid-template-columns:1fr 1fr;gap:22px}} .ftables>div{{background:#fff;border:1px solid {LINE};border-radius:12px;padding:12px 14px}}
.fsum{{margin-top:18px;font-size:17px;text-align:center}}
.navs{{position:relative;height:100%}}
.gwrap{{position:relative;border:1px solid {LINE};border-radius:6px;overflow:hidden;flex:none}} .gwrap img{{display:block;image-rendering:pixelated}} .gov{{position:absolute;left:0;top:0}}
.lidp{{flex:none}} .lidbody{{display:flex;gap:10px}} .lidleg{{font-size:11.5px;display:flex;flex-direction:column;gap:5px;color:{MUTE}}} .lidleg i{{display:inline-block;width:11px;height:11px;margin-right:6px;vertical-align:middle;border-radius:2px}}
.lidmeta{{margin-top:auto;font-size:11px;line-height:1.45}}
.tabs2{{display:flex;gap:0;text-transform:none;letter-spacing:0;font-size:11.5px}} .tabs2 b,.tabs2 span{{padding:1px 8px;border:1px solid {LINE}}} .tabs2 b{{background:{INK};color:#fff;border-color:{INK};border-radius:5px 0 0 5px}} .tabs2 span{{border-radius:0 5px 5px 0;color:{MUTE};font-weight:600}}
.lpg{{display:flex;flex-direction:column;gap:12px}} .lpg1{{display:flex;gap:12px}} .lpt{{flex:1}} .lnote{{margin-top:12px;font-size:13.5px;line-height:1.45}}
.pano img{{display:block;width:100%;height:auto;border-radius:6px;image-rendering:auto}} .pano span{{display:block;font-size:12px;color:{MUTE};margin-top:6px}}

.cvmeta>div{{display:flex}}
'''

html = f'<!doctype html><html><head><meta charset="utf-8"><title>CAVS Supervisory Monitor — Dashboard Sketches {VERSION}</title><meta name="author" content="{AUTHOR}"><style>{CSS}</style></head><body>{"".join(P)}</body></html>'
open(OUT_HTML, "w").write(html)
print("ok")
