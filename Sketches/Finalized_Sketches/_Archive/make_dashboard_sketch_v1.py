# Dashboard sketch generator — CAVS-1 post-run review
# Author: Zeenat Islam
import json, math

AUTHOR   = "Zeenat Islam"
TEAM     = "Team CAVS-1: Nathan Hester, Chuck, Caleb, Zeenat Islam"
RUN      = "autonomy_demo_0"
RUN_DATE = "11 Sep 2026, 11:45 CDT"
DUR      = 72.1
OUT_HTML = "sketches.html"   # render to PDF with any Chromium print-to-PDF at 1400 x 1060 px

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

def mapsvg(w, h, upto=DUR, pins=True, highlight=None):
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
    g.append(f'<polyline points="{pp}" fill="none" stroke="{MUTE}" stroke-width="2.5" stroke-dasharray="7 6"/>')
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

def mappanel(w, h, upto=DUR, highlight=None, title="Route overview"):
    legend = f'''<div class="leg"><span><i style="background:{OK}"></i>&gt;1 m/s</span><span><i style="background:{WARN}"></i>0.3–1 m/s</span><span><i style="background:#a39a92"></i>creeping</span><span><i class="dash"></i>planned, not driven</span></div>'''
    return f'<div class="panel map" style="width:{w}px;height:{h}px"><div class="ph">{title}<span class="link">Open in Path Planning ›</span></div>{mapsvg(w-24, h-74, upto, True, highlight)}{legend}</div>'

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

# ---------- pages ----------
P = []
P.append(f'''<section class="page cover"><div class="cv">
<div class="kicker">CAVS Off-Road Proving Ground · Autonomous Vehicle Testing</div>
<h1>Post-Run Review Interface</h1><div class="h1s">Dashboard sketches · v1</div>
<div class="cvmeta">
<div><b>Use case</b>Reviewing a completed autonomy run from a recorded ROS 2 bag</div>
<div><b>Target display</b>12″ tablet, landscape, browser UI driven by Raspberry Pi 5</div>
<div><b>Data in these sketches</b>Values taken from the provided bag {RUN} (72.1 s, 124,845 messages)</div>
<div><b>Pages in this set</b>1 Dashboard overview · 2 Event review · 3 Fault drill-down · 4 Navigation</div>
</div>
<div class="by">{AUTHOR}<br><span>{TEAM}</span></div></div></section>''')

body1 = f'''<div class="col l">{summary()}{evlist()}</div>
<div class="col c">{mappanel(560, 428)}</div>
<div class="col r">{health()}</div>
<div class="row">{timeline(1232)}</div>'''
P.append(page("1 · Dashboard — run overview", "Landing view after a run is loaded. Playhead parked at the end of the run.", frame(body1),
  ["Top bar names the run and states the outcome in one chip, so the reviewer knows how the run ended before reading anything else.",
   "Run summary answers “how far, how long, was the goal reached, did a person step in.”",
   "Route trace is coloured by speed; the dashed leg is the plan that was never driven after the STOP.",
   "Numbered event pins match across the event list, the map and the timeline.",
   "System health shows each sensor for the whole run, colour coded green / amber / red / grey.",
   "Timeline lanes stack mode, speed, events and sensor streams on one shared time axis."]))

sel = 2; t = EVENTS[sel - 1][0]; sp = speed_at(t)
detail = f'''<div class="panel det"><div class="ph">Event 2 of 8<span class="link">‹ prev · next ›</span></div>
<div class="dh" style="border-color:{WARN}"><span class="pinb" style="background:{WARN}">2</span>Controller patience exceeded<div class="dts">t = 15.5 s · controller_server · WARN/ERROR</div></div>
<div class="kv"><span>Mode</span><b style="color:{OK}">AUTONOMY</b></div>
<div class="kv"><span>Speed</span><b>{sp[3]:.2f} m/s</b></div>
<div class="kv"><span>Position</span><b>({sp[1]:.1f}, {sp[2]:.1f}) m</b></div>
<div class="kv"><span>Preceded by</span><b>11× “collision ahead” in 0.5 s</b></div>
<div class="kv"><span>Outcome</span><b>follow_path aborted</b></div>
<div class="kv"><span>Sensors</span><b style="color:{OK}">all nominal</b></div>
<div class="logx"><div class="lh">/rosout around this moment</div>
<div>15.0 WARN  collision ahead! (×11)</div>
<div>15.5 ERROR patience exceeded</div>
<div>15.5 WARN  follow_path aborted</div>
<div>15.6 WARN  loop 8.3 Hz (target 20)</div>
<div class="link" style="margin-top:6px">Open in Run Logs ›</div></div></div>'''
cams = "".join(f'<div class="cam"><svg width="100%" height="100%"><line x1="0" y1="0" x2="100%" y2="100%" stroke="{LINE}"/><line x1="100%" y1="0" x2="0" y2="100%" stroke="{LINE}"/></svg><span>Cam {i} · 15.5 s</span></div>' for i in range(3))
body2 = f'''<div class="col l">{detail}</div>
<div class="col c">{mappanel(560, 290, upto=t, highlight=2, title="Route up to 15.5 s")}<div class="panel cams"><div class="ph">Camera frames at playhead<span class="link">Sensors ›</span></div><div class="camrow">{cams}</div></div></div>
<div class="col r">{health()}</div>
<div class="row">{timeline(1232, play=t, sel=2)}</div>'''
P.append(page("2 · Dashboard — reviewing an event", "Reviewer taps pin 2 on the timeline. Every panel jumps to that moment.", frame(body2, state="Stopped by operator"),
  ["Left column swaps the summary for an event card: what happened, vehicle state at that instant, and the log lines around it.",
   "Map trims the route to the playhead so the reviewer sees where the vehicle was, not where it ended up.",
   "Camera frames from all three cameras at the same timestamp sit under the map.",
   "Prev / next steps through events in order, so a full review needs no scrubbing."]))

CAMCHART = camchart()
body3 = f'''<div class="col l">{summary()}{evlist(sel=3)}</div>
<div class="col c"><div class="panel fz"><div class="ph">Camera 2 · frame gaps<span class="link">Open in Faults ›</span></div>
<svg width="536" height="200" viewBox="0 0 536 200">{CAMCHART}</svg>
<div class="fzr"><div><b>2</b><span>gaps</span></div><div><b>265 ms</b><span>longest</span></div><div><b>18.9 Hz</b><span>mean rate</span></div><div><b>19.0 Hz</b><span>expected</span></div></div></div>
<div class="panel"><div class="ph">Other fault classes in this run</div>
<div class="fc"><span class="dot" style="background:{OK}"></span>LiDAR dropout<b>none</b></div><div class="fc"><span class="dot" style="background:{OFF}"></span>GPS dropout<b>no GPS stream in log</b></div><div class="fc"><span class="dot" style="background:{OK}"></span>Camera 0 / 1 lag<b>none</b></div></div></div>
<div class="col r">{health(focus="Camera 2")}</div>
<div class="row">{timeline(1232, play=17.9, sel=3)}</div>'''
P.append(page("3 · Dashboard — fault drill-down", "Reviewer taps the amber Camera 2 tile. The dashboard opens a short fault summary in place.", frame(body3),
  ["Tapping any amber or red health tile opens its fault summary in the centre panel and moves the playhead to the first occurrence.",
   "The same three fault classes the course bag injects (GPS dropout, LiDAR dropout, camera lag) always have a slot, even when a run has none.",
   "Detailed fault analysis lives on the Faults page; the dashboard only answers “did it happen, when, how bad.”"]))

nav = f'''<div class="navmap">
<div class="nb hub">Dashboard<small>run overview · events · health</small><small class="own">Zeenat</small></div>
<div class="nb n1">Path Planning<small>waypoints, distance, obstacles</small><small class="own">Nathan</small></div>
<div class="nb n2">Faults<small>colour-coded GPS / LiDAR / camera faults</small><small class="own">Caleb</small></div>
<div class="nb n3">Sensors<small>camera &amp; LiDAR preview</small><small class="own">Caleb</small></div>
<div class="nb n4">Run Logs<small>previous runs, status</small><small class="own">Chuck</small></div>
<svg class="lines" width="1232" height="560"><g stroke="{MUTE}" stroke-width="2" fill="none">
<path d="M616 250 L616 250"/><path d="M500 280 L250 140"/><path d="M732 280 L982 140"/><path d="M500 330 L250 440"/><path d="M732 330 L982 440"/></g></svg>
<div class="lab l1">route map → Path Planning</div><div class="lab l2">health tile / fault card → Faults</div>
<div class="lab l3">camera frames → Sensors</div><div class="lab l4">run selector, log lines → Run Logs</div>
<div class="shared">Shared across every page: run selector and outcome chip (top), timeline playhead time, bottom menu bar</div></div>'''
P.append(page("4 · Navigation", "Where the dashboard hands off to the other pages in the team’s design.", f'<div class="tablet"><div class="screen navs">{nav}</div></div>',
  ["The dashboard is the hub. Each panel links to the page that owns its detail.",
   "The selected run and playhead time carry over when moving between pages, so the reviewer never loses their place."]))

CSS = f'''
@page {{ size: 1400px 1060px; margin:0 }}
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
.evt{{font-family:monospace;color:{MUTE};width:42px}}
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
html = f'<!doctype html><html><head><meta charset="utf-8"><title>CAVS Post-Run Review — Dashboard Sketches</title><meta name="author" content="{AUTHOR}"><style>{CSS}</style></head><body>{"".join(P)}</body></html>'
open(OUT_HTML, "w").write(html)
print("ok")
