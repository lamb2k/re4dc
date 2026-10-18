"""c3g_runs.py: per castle room, recorded scenario runs (newest first) with arm, tex.pak key, warp start line."""
import json, os, re, glob, collections
roots = [r"C:\Flycast-Evidence\re4-dreamcast\castle-20261015", r"C:\Flycast-Evidence\re4-dreamcast\ch3found-20261016"]
ROOMS = "r201 r202 r203 r204 r205 r206 r207 r208 r209 r20a r20b r20c r20d r20e r20f r216 r221 r228".split()
wre = re.compile(r"warp: start room=\w+ next_room=\w+ pos=\S+ ang=\S+")
out = collections.defaultdict(list)
for R in roots:
    for sj in glob.glob(R + r"\h-*\scenarios\cx-r2*\stage.json"):
        sc = os.path.dirname(sj); r = os.path.basename(sc).split("-")[1]
        if r not in ROOMS: continue
        try: d = json.load(open(sj, encoding="utf-8"))
        except Exception: continue
        fx = d.get("fixture") or {}
        rp = fx.get("replace", {}) if isinstance(fx, dict) else {}
        w = ""
        ro = os.path.join(sc, "capture", "run-output.txt")
        if os.path.exists(ro):
            m = wre.search(open(ro, encoding="latin1").read()); w = m.group(0) if m else "NOWARPLINE"
        res = ""
        rj = os.path.join(sc, "rfp-result.json")
        if os.path.exists(rj):
            try: res = json.dumps(json.load(open(rj)).get("verdict", ""))[:60]
            except Exception: pass
        out[r].append((os.path.getmtime(sj), os.path.relpath(sc, r"C:\Flycast-Evidence\re4-dreamcast"), d.get("arm"),
                       os.path.basename(str(rp.get("dc/tex.pak", "")))[:40], str(rp.get("dc/warp.txt", ""))[-60:], w, res))
for r in ROOMS:
    v = sorted(out[r], reverse=True)
    print("==", r, len(v))
    for x in v[:4]: print("   ", *x[1:])
