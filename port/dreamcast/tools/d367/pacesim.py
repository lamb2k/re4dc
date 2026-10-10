#!/usr/bin/env python3
"""tools/d367/pacesim.py (2026-10-09, PACE_CAP=2 measurement): replay pace.cpp's Fast-mode decision (PACE_CATCHUP=2, PACE_MODE=fast) on the hardware model's
per-tick costs, for PACE_CAP=1 and 2.

Model (pace.cpp re4dc_pace_begin / want_skip / re4dc_pace_end):
  - vblank every 16.683 ms; tick k is due at anchor + 2k vblanks; after a tick's work the loop spins until that due
    vblank (re4dc_pace_end), so a tick never starts early;
  - lag (vblanks) = now - due at the decision; skip the image when lag >= 2 and fewer than CAP consecutive skips;
    lag beyond 2*(CAP+1) vblanks is dropped (slow motion) keeping 2*CAP;
  - v2 decides the drop before Trans() of the previous tick; modelled here as a decision at iteration start using the
    lag predicted at that point (the rest_ema term), i.e. the same rule one iteration earlier. That matches the
    steady state; it can differ by one image at transitions.
  - a drawn tick costs D (per-tick sample), a skipped one S. A drawn image is on screen at the first vblank after its
    tick's work ends (TA double buffer; GPU assumed not limiting: GPU <= ~53 ms outdoors < the drawn interval here).
  - input: the pad is read at tick start; its latency = (vblank its effect is first shown) - (tick start).
Inputs: D and S lists (ms, console-scaled), cycled. Outputs speed %, drawn fps, latency, present intervals.
Usage: pacesim.py <views.json> <out.json>, views.json = {"view": {"D": [ms...], "S": [ms...], "k": 1.155}}, where D / S
are hw model compute ms (msbucket 'compute (nominal - pacing)'; not mode.tsv, which includes the pacing spin).
"""
import json, sys, math

VB = 16.683


def sim(D, S, cap, n=3000):
    t = 0.0
    anchor = 0.0
    ticks = 0
    run = 0
    pending = []          # tick start times whose effect is not shown yet
    presents = []
    lat = []
    di = si = 0
    drawn = 0
    vb = lambda x: math.floor(x / VB + 1e-9)
    for k in range(n):
        now_vb = vb(t)
        due_vb = int(round(anchor / VB)) + 2 * ticks
        lag = now_vb - due_vb
        if lag > 2 * (cap + 1):
            keep = 2 * cap
            anchor += (lag - keep) * VB
            due_vb = int(round(anchor / VB)) + 2 * ticks
            lag = keep
        skip = lag >= 2 and run < cap
        run = run + 1 if skip else 0
        pending.append(t)
        if skip:
            cost = S[si % len(S)]; si += 1
        else:
            cost = D[di % len(D)]; di += 1
        end = t + cost
        if not skip:
            shown = (vb(end) + 1) * VB
            presents.append(shown)
            for p in pending:
                lat.append(shown - p)
            pending = []
            drawn += 1
        ticks += 1
        due = (int(round(anchor / VB)) + 2 * ticks) * VB
        t = max(end, due)
    wall = t
    iv = [b - a for a, b in zip(presents, presents[1:])]
    iv.sort()
    pct = lambda a, q: a[min(len(a) - 1, int(q * len(a)))]
    lat.sort()
    return dict(cap=cap, speed=100.0 * n * 2 * VB / wall, fps=drawn * 1000.0 / wall,
                present_p50=pct(iv, .5), present_p99=pct(iv, .99), present_max=iv[-1],
                lat_mean=sum(lat) / len(lat), lat_p50=pct(lat, .5), lat_max=lat[-1],
                presents=[b - a for a, b in zip(presents, presents[1:])][:200])


if __name__ == '__main__':
    cfg = json.load(open(sys.argv[1]))     # {"view": {"D": [...], "S": [...], "k": 1.155}, ...}
    out = {}
    for v, c in cfg.items():
        D = [x * c['k'] for x in c['D']]; S = [x * c['k'] for x in c['S']]
        out[v] = [sim(D, S, 1), sim(D, S, 2)]
        for r in out[v]:
            print('%-8s CAP%d speed %5.1f%% fps %5.2f present p50 %.1f p99 %.1f max %.1f ms latency mean %.1f p50 %.1f max %.1f ms' % (
                v, r['cap'], r['speed'], r['fps'], r['present_p50'], r['present_p99'], r['present_max'], r['lat_mean'], r['lat_p50'], r['lat_max']))
    json.dump(out, open(sys.argv[2], 'w'), indent=1)
