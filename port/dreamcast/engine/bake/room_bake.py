"""One command per room: the engine's room bake, its visibility, its checks and its census row (lane eng-bake1).

    room_bake.py <room hex> [--out DIR]            bake one room (e.g. 10b)
    room_bake.py --chapter1 [--out DIR]            every chapter 1 room, then the census table (census.json, census.md)
    room_bake.py --inputs                          the chapter 1 room list with each bake input present or missing
    room_bake.py --control-seeds <room hex>        the seed check's failing input (seeds moved off the floor)
    room_bake.py --controls                        every check's failing input, after --chapter1 (controls.json)

Two kinds of pack, both in the NAT3 format of native_pack.py (no format change):
- game pack (<room>.pak): a recording of the old game in the room exists (RECORDINGS below). native_pack.build (the
  hill's hill_pack.build) bakes it whole, ending with the HUD fix; hud_fix.verify must pass.
- world pack (<room>.world.pak): no recording. Everything that can be had offline is baked the same way: the
  whole-room world, its materials and textures, the sky, the actor catalogue (Leon and the five Ganado appearances
  with their distance levels) and the catalogue tail. The logic streams carry only the room's entry points as
  cameras (one picture each), the seeds bake_vis grows the reachable floor from. It is not a game pack: it has no
  lights, environment, HUD, props or effects, and hud_fix.verify FAILS on it by design, so no pack writer or disc
  script takes it.
Offline inputs and where they come from:
- world, sky, textures: the old port's converted PS2 data (<disc>/native/rXXX, <disc>/tex.pak);
- the catalogue: <disc>/native/pl00, ganado, the private static tables, and Leon's cloth binds (leon-bind.bin: one
  file for chapter 1, identical in the village and farm recordings; it is Leon's model data, not the room's);
- entry points: every door of the stage whose destination is the room (dstPos of the AEV door records, read from the
  room archives by tools/d367/stage_route.py), plus r120's jump into r100 (src/st1/r120.cpp:99);
- lights and fog for the census: the room's LIT, cut 0 (include/light.h layout, tools/convert_lit.py), the data the
  old game's light manager loads and a recording records.
Visibility: bench/bake_vis.c over the pack (whole reachable room seeded from the pack's cameras). Census:
bake/census_world.c over the pack and its table, plus the pack's sections read here.
"""
import argparse, json, os, struct, subprocess, sys, time, zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENGINE = HERE.parent
TOOLS = ENGINE.parent / "tools"
sys.path.insert(0, str(HERE))

DISC = Path("/root/work/lanes/eng-bench/.m1/pristine/dc")
TABLES = Path("/root/work/lanes/eng-bench/.m1/native005/static.bin")
ISO = Path("/root/work/re4-dreamcast/orig/G4BE08/re4_debug_disc1.iso")
LEON_BIND_CH1 = Path("/mnt/e/RE4DC-Lanes/eng-e0b/runs/cap-cross/leon-bind.bin")
BIN = Path("/dev/shm/eng-bake1/bin")

# Chapter 1, the first room to the lake boss, in play order: the stage's chapter ends (src/st1/r106.cpp:419
# SceSetChapterEnd(0, 3) door 3 -> r104; r105.cpp:650 CHAPTER_1_2; r10b.cpp:359/390 CHAPTER_1_3 door 6 -> r11b) and
# the door graph of the room archives (tools/d367/stage_route.py --stage 1). r120 is the intro movie room: it has no
# world and jumps to r100 (r120.cpp:99).
CHAPTER1 = [("r120", "1-1", "intro movie, jump to r100"), ("r100", "1-1", ""), ("r101", "1-1", "village"),
            ("r103", "1-1", "farm"), ("r106", "1-1", "chapter 1-1 end"), ("r104", "1-2", ""),
            ("r107", "1-2", ""), ("r105", "1-2", "chapter 1-2 end"), ("r102", "1-3", ""),
            ("r108", "1-3", ""), ("r109", "1-3", ""), ("r10a", "1-3", ""), ("r10b", "1-3", "lake boss, chapter 1-3 end")]
# Comparison rooms outside chapter 1 that the engine already has a pack for.
COMPARE = [("r11d", "2-3", "hill (E1 hill scene)")]

# Recordings of the old game (bench/r3_capture.hpp, 300 pictures) that exist today, with what native_pack needs.
RECORDINGS = {
    0x101: dict(capture="/mnt/e/RE4DC-Lanes/eng-e0b/runs/cap-cross", prior="/mnt/e/RE4DC-Lanes/eng-bench/runs",
                ram="/mnt/e/RE4DC-Lanes/eng-bench/runs/eng-bench-cross-4/resource-ram-098.raw"),
    0x103: dict(capture="/mnt/e/RE4DC-Lanes/eng-e0b/runs/cap-hayfork", prior="/mnt/e/RE4DC-Lanes/eng-bench/runs",
                ram="/mnt/e/RE4DC-Lanes/eng-bench/runs/eng-bench-hayfork-4/resource-ram-072.raw"),
    0x11d: dict(capture="/mnt/e/RE4DC-Lanes/eng-e1d/runs/cap-hill", hill=True),
}
R120_JUMP = (-109450.0, -515.0, 820.0)   # src/st1/r120.cpp:99, SceAtExecRoomJump(0x100, &pos, ...)

# The visibility recipe of the village and farm tables (eng-e0b vis2c: 2 m camera cells, 27 eyes, margin 60 mm, the
# 256 KiB budget), used for every room so rooms compare. The hill's E1 table was baked with 1 m cells, 48 eyes,
# margin 150 and --erode (eng-e1d); its census row here is from this recipe, not that table.
VIS_ARGS = ["--cell", "2000"]

# The engine's proposed main-memory and video-memory map (docs/engine/SHELL_MAP.md:243-265), KiB.
PACK_RAM_KIB = 4096
VRAM_WORLD_KIB, VRAM_CHAR_KIB, VRAM_FX_KIB = 2048, 1280, 768


def log(*a):
    print(*a, flush=True)


# ---------------------------------------------------------------- room tables from the room archives (offline)
def stage_tables(iso=ISO):
    """{room: dict(doors=[...], entries=[(x, y, z, from)], lights=n, fog=(type, start, end))} for stage 1"""
    sys.path.insert(0, str(TOOLS)); sys.path.insert(0, str(TOOLS / "d367"))
    import room_smd
    from assetpipe.rooms import GcIso
    import stage_route
    g = GcIso(iso)
    rooms = stage_route.scan(g, 1)
    out = {r: dict(doors=d["doors"], entries=[], lights=None, fog=None) for r, d in rooms.items()}
    for a, d in rooms.items():
        for door in d["doors"]:
            if door["dst"] in out and door["dst"] != a:
                out[door["dst"]]["entries"].append((*door["pos"], a))
    out.setdefault("r100", dict(doors=[], entries=[], lights=None, fog=None))["entries"].append((*R120_JUMP, "r120"))
    for room, rel in g.rooms():
        if room not in out: continue
        data = room_smd.decode_das(g.read(rel))
        e = room_smd.archive_endian(data)
        # more seeds inside the room (one entry door can sit behind a step the walk test refuses: r106): the centre
        # of every area record (AEV doors, events, cameras; include/sce_at.h SceAtWork, include/area.h AreaData at
        # +0x04: XZ4 points at +0x14, a cylinder's or eye's x, z at +0x14, +0x18; its floor at +0x08) and every item
        # position (ITA, SceAtItem pos at +0x5C). Places the game puts the player or his pick-ups.
        areas = []
        for magic, ver in ((b"AEV", 0x104), (b"ITA", 0x105)):
            for w in stage_route.records(data, magic, ver):
                if magic == b"ITA":
                    areas.append((*struct.unpack_from(">3f", data, w + 0x5C), "item")); continue
                atype = data[w + 5]; floor = struct.unpack_from(">f", data, w + 8)[0]
                if atype == 1:
                    p = struct.unpack_from(">8f", data, w + 0x14); x, z = sum(p[0::2]) / 4, sum(p[1::2]) / 4
                elif atype in (2, 3):
                    x, z = struct.unpack_from(">2f", data, w + 0x14)
                else: continue
                areas.append((x, floor, z, "area%d" % data[w + 0x35]))
        out[room]["areas"] = [a for a in areas if all(abs(v) < 1e6 for v in a[:3])]
        lit = [data[s:t] for tag, s, t in room_smd.tagged_entries(data, e) if tag == b"LIT\0"]
        if not lit: continue
        L = lit[0]; cuts = struct.unpack_from(">H", L, 0)[0]; o = struct.unpack_from(">I", L, 4)[0]
        out[room]["lights"] = struct.unpack_from(">I", L, o + 4)[0]
        out[room]["fog"] = (struct.unpack_from(">i", L, o + 8)[0], *struct.unpack_from(">2f", L, o + 12))
        out[room]["lit_cuts"] = cuts
        # every cut's light count: the cut in force follows the player's light area at run time (light_area.cpp)
        out[room]["lights_per_cut"] = [struct.unpack_from(">I", L, struct.unpack_from(">I", L, 4 + 4 * c)[0] + 4)[0] for c in range(cuts)]
    return out


# ---------------------------------------------------------------- inputs
def inputs(room, disc=DISC, tables=None):
    """what the bake needs for the room, and whether each input exists"""
    rid = int(room[1:], 16); d = disc / "native" / room
    have = lambda p: Path(p).exists()
    row = dict(room=room,
               world=all(have(d / f) for f in ("ps2-world.re4mesh", "ps2-world.r4pw")),
               sky=have(d / "ps2-sky.r4sk"), groups=have(d / "ps2-world.r4sg"), tc=have(d / "ps2-world.r4tc"),
               cast=have(d / "registry.re4nmr"), cast_bytes=(d / "registry.re4nmr").stat().st_size if have(d / "registry.re4nmr") else 0,
               catalogue=all(have(disc / "native" / p) for p in ("pl00/leon_lod.re4lp", "ganado/ganado_lod.re4gl")) and have(TABLES),
               leon_bind=have(LEON_BIND_CH1), recording=rid in RECORDINGS)
    if row["world"]:
        tex = (disc / "tex.pak").read_bytes()
        count, idx = struct.unpack_from("<2I", tex, 12)
        keys = {(a, b) for a, b, _, _ in struct.iter_unpack("<4I", tex[idx:idx + 16 * count])}
        side = (d / "ps2-world.r4pw").read_bytes()
        parts = struct.unpack_from("<I", side, 12)[0]   # R4PW: version 4, placements 8, parts 12
        need = {struct.unpack_from("<2I", side, 32 + 16 * i) for i in range(parts)}
        row["world_keys"] = len(need); row["world_keys_missing"] = len(need - keys)
    if tables is not None:
        t = tables.get(room) or {}
        row["entries"] = len(t.get("entries", [])); row["lights_lit"] = t.get("lights")
    return row


# ---------------------------------------------------------------- the world pack (no recording)
def world_pack(room, entries, disc=DISC, tables=TABLES, leon_bind=LEON_BIND_CH1, cot=None):
    from pack_scene import Baker, Table, block, pack
    from native_world import whole_world
    from native_models import models, level_models, rigid
    from logic_delta import Changes
    rid = int(room[1:], 16)
    assets = Baker(disc, None, rid)
    world = whole_world(disc / "native" / room, lambda key, phase, cull: assets.header(key, (0, 2, 3)[phase], cull, world=True, fog=True))
    bind = leon_bind.read_bytes()
    mat = lambda key, phase: assets.header(key, phase, fog=True)
    actor_models = models(disc, tables, bind, mat)
    variants = []; levels = {}
    for base, level, blob in level_models(disc, tables, bind, mat):
        variants.append((base, level, len(actor_models))); actor_models.append(blob); levels[base, level] = blob
    for base in range(1, 6):
        src = levels.get((base, 3)); r = rigid(src) if src else None
        if r: variants.append((base, 4, len(actor_models))); actor_models.append(r)
    samples = [Table() for _ in range(9)]; changes = [Changes() for _ in samples]; frames = []
    for i, (x, y, z, _src) in enumerate(entries):
        cam = struct.pack("<12f", 1, 0, 0, -x, 0, 1, 0, -(y + 1600.0), 0, 0, 1, -z)   # eye 1.6 m over the entry
        cam += struct.pack("<14f", 0, cot / 1.33333333, 0, cot, 0, -100 / 18650.0, -18750 * 100 / 18650.0, 0, 0, 640, 480, 0, 1, 18750)
        groups = {1: cam}
        frames.append(pack("10I", i, *(t.add(changes[k].encode(groups.get(k + 1, b""))) for k, t in enumerate(samples))))
    sections = [block(t.rows) for t in (assets.textures, assets.headers)]
    sections += [world, block(frames), *(block(t.rows) for t in samples), block(actor_models)]
    sections.append(pack("2f", assets.top, assets.bottom) + pack("4sI", b"LODV", len(variants))
                    + b"".join(pack("4H", b, k, v, 0) for b, k, v in variants) + pack("4sI", b"CARD", 0))
    data = block(sections)
    world_textures = textures_of_world(world, assets)
    return pack("4s4I", b"NAT3", 4, rid, len(data), zlib.crc32(data)) + data, world_textures


def textures_of_world(world, assets):
    """texture rows the world materials and the sky use (row 0 is the sky)"""
    places, cells, ml, mt = struct.unpack_from("<4I", world, 4)
    meta = world[28 + ml:28 + ml + mt]
    tids = {0}
    for i in range(0, len(meta), 8):
        h = struct.unpack_from("<I", meta, i)[0]
        tids.add(struct.unpack_from("<I", assets.headers.rows[h])[0])
    return tids


def recorded_pack(rid):
    rec = RECORDINGS[rid]
    cap = Path(rec["capture"])
    if rec.get("hill"):
        import hill_pack
        data = hill_pack.build(DISC, cap, TABLES, {})
    else:
        import native_pack
        data = native_pack.build(DISC, cap, rid, TABLES, Path(rec["prior"]), Path(rec["ram"]))
    import hud_fix
    hud_fix.verify(data)
    return data


# ---------------------------------------------------------------- pack reading for the census
def blocks(b, at=0):
    n = struct.unpack_from("<I", b, at)[0]
    offs = struct.unpack_from(f"<{n + 1}I", b, at + 4)
    base = at + 4 + 4 * (n + 1)
    return [bytes(b[base + offs[i]:base + offs[i + 1]]) for i in range(n)]

FMT = ("RGB565", "ARGB1555", "ARGB4444", "PAL4", "PAL4", "PAL8")

def texture_rows(pack_bytes, world_tids=None):
    secs = blocks(pack_bytes, 20)
    texs, heads = blocks(secs[0]), blocks(secs[1])
    if world_tids is None:   # from the world section's materials
        world = secs[2]; places, cells, ml, mt = struct.unpack_from("<4I", world, 4)
        meta = world[28 + ml:28 + ml + mt]
        world_tids = {0} | {struct.unpack_from("<I", heads[struct.unpack_from("<I", meta, i)[0]])[0] for i in range(0, len(meta), 8)}
    rows = []
    for tid, pkg in enumerate(texs):
        at = struct.unpack_from("<I", pkg, 24)[0]
        name = pkg[at:at + 64].split(b"\0")[0].decode("latin-1")
        w, h, fmt, data_at, n, flags, payload, _ = struct.unpack_from("<8I", pkg, at + 64)
        kind = ("VQ " if payload == 2 else "") + FMT[fmt] + (" mip" if flags & 4 else "")
        rows.append(dict(tid=tid, name=name, w=w, h=h, kind=kind, bytes=n, world=tid in world_tids))
    return rows, secs


def light_count(rid):
    rec = RECORDINGS.get(rid)
    if not rec: return None
    b = (Path(rec["capture"]) / "picture-001.bin").read_bytes(); at = 16; n = 0
    while at < len(b):
        kind, size = struct.unpack_from("<2I", b, at); at += 8 + size; n += kind == 3
    return n


def template_cot():
    """cot(fovy / 2) of the village recording's first camera (the game's default view)"""
    b = (Path(RECORDINGS[0x101]["capture"]) / "picture-001.bin").read_bytes(); at = 16
    while at < len(b):
        kind, size = struct.unpack_from("<2I", b, at)
        if kind == 1: return struct.unpack_from("<f", b, at + 8 + 4 * 15)[0]
        at += 8 + size
    raise ValueError("no camera in the village recording")


# ---------------------------------------------------------------- host tools
def tools():
    BIN.mkdir(parents=True, exist_ok=True)
    render = ENGINE / "render"
    for name, src in (("bake_vis", ENGINE / "bench" / "bake_vis.c"), ("census_world", HERE / "census_world.c")):
        exe = BIN / name
        if not exe.exists() or exe.stat().st_mtime < max(src.stat().st_mtime, (render / "native_world.c").stat().st_mtime):
            subprocess.run(["cc", "-O2", "-march=native", "-w", f"-I{render}", str(src), str(render / "native_world.c"), "-lm", "-o", str(exe)], check=True)
    return BIN / "bake_vis", BIN / "census_world"


def keyvals(text):
    out = {}
    for line in text.splitlines():
        parts = line.split()
        if not parts or "=" in parts[0]: continue
        out[parts[0]] = {k: v for k, v in (p.split("=", 1) for p in parts[1:] if "=" in p)}
    return out


def run_vis(bake_vis, path, out, jobs):
    """bake_vis survey and bake -> (vis path or None, log or error, domain, (seeds in baked cells, seeds))"""
    import re
    vis = path.with_suffix(".vis")
    survey = subprocess.run([str(bake_vis), str(path), str(vis), "--survey", *VIS_ARGS], capture_output=True, text=True)
    r = subprocess.run([str(bake_vis), str(path), str(vis), "--jobs", str(jobs), *VIS_ARGS], capture_output=True, text=True)
    (out / f"{path.stem}.vis.log").write_text(survey.stderr + "\n----\n" + r.stderr)
    raw = Path(str(vis) + ".raw")
    if raw.exists(): raw.unlink()
    if r.returncode != 0 or not vis.exists():
        return None, f"bake_vis exit {r.returncode}: {r.stderr.strip().splitlines()[-1:]}", None, None
    m = re.search(r"(\d+) with a floor, (\d+) reachable on foot, (\d+) baked", r.stderr)
    dom = dict(floor_cells=int(m[1]), reachable=int(m[2]), baked=int(m[3])) if m else None
    m = re.search(r"route: (\d+) pictures, camera in a baked cell (\d+), inside its band (\d+)", survey.stderr)
    return vis, r.stderr, dom, (dict(pictures=int(m[1]), in_cell=int(m[2]), in_band=int(m[3])) if m else None)


def route_coverage(vis_path, capture):
    """recorded cameras (picture-NNN.bin, kind 1) that fall in a baked cell of the table and inside its band"""
    v = Path(vis_path).read_bytes(); h = struct.unpack_from("<16I", v); f = struct.unpack_from("<8f", v, 64)
    nplace, nx, nz, ncells = h[2], h[3], h[4], h[5]; at = 128 + 4 * (2 * nplace + 1)
    rows = struct.unpack_from(f"<{2 * nz}I", v, at); cells_at = at + 8 * nz
    n = inc = inb = 0
    for pic in sorted(Path(capture).glob("picture-*.bin")):
        b = pic.read_bytes(); o = 16
        while o < len(b):
            kind, size = struct.unpack_from("<2I", b, o)
            if kind == 1:
                c = struct.unpack_from("<12f", b, o + 8)
                x, y, z = (-(c[j] * c[3] + c[4 + j] * c[7] + c[8 + j] * c[11]) for j in range(3))
                n += 1; cx = int((x - f[0]) // f[2]); cz = int((z - f[1]) // f[2])
                if 0 <= cx < nx and 0 <= cz < nz:
                    x0, cnt = rows[2 * cz] & 0xffff, rows[2 * cz] >> 16
                    if x0 <= cx < x0 + cnt:
                        im, cm, ylo, yhi = struct.unpack_from("<2H2h", v, cells_at + 8 * (rows[2 * cz + 1] + cx - x0))
                        if im != 0xffff:
                            inc += 1; inb += ylo * f[7] <= y <= yhi * f[7]
                break
            o += 8 + size
    return dict(pictures=n, in_cell=inc, in_band=inb)


# ---------------------------------------------------------------- one room
def bake_room(room, out, tables, cot, jobs=4, control_seeds=False):
    rid = int(room[1:], 16); t0 = time.time()
    res = dict(room=room, checks={}, failures=[])
    row = inputs(room, tables=tables); res["inputs"] = row
    if not row["world"]:
        res["failures"].append("no PS2 world sidecars (native/%s/ps2-world.*)" % room); return res
    t = tables.get(room) or {}
    entries = [tuple(e) for e in t.get("entries", [])] + [tuple(a) for a in t.get("areas", [])]   # seeds: entry points, then the room's areas and items
    res["seeds"] = dict(entries=len(t.get("entries", [])), areas_and_items=len(t.get("areas", [])))
    if control_seeds:   # the seed check's control: every entry point lifted 50 m off the floor and moved 1 km away
        entries = [(x + 1e6, y + 5e4, z + 1e6, s) for x, y, z, s in entries]
    try:
        if rid in RECORDINGS and not control_seeds:
            data = recorded_pack(rid); kind = "game"; world_tids = None
            path = out / f"{room}.pak"
        else:
            data, world_tids = world_pack(room, entries, cot=cot); kind = "world"
            path = out / (f"{room}.world.pak" if not control_seeds else f"{room}.control.pak")
    except Exception as e:   # a bake failure is a row, not a stop
        res["failures"].append(f"bake: {type(e).__name__}: {e}"); return res
    path.write_bytes(data); res.update(kind=kind, pack=str(path), pack_bytes=len(data))
    # check 1: the HUD fix (game packs must pass; world packs must fail, so they can never reach a disc)
    import hud_fix
    try: hv = "PASS"; res["hud_digit_widgets_linked"] = hud_fix.verify(data)   # the HUD fix receipt (native_pack.build runs the fix)
    except ValueError as e: hv = "FAIL"
    res["checks"]["hud_verify"] = hv + (" (expected: world pack)" if kind == "world" else "")
    if (kind == "game") != (hv == "PASS"): res["failures"].append("hud_fix.verify gave %s on a %s pack" % (hv, kind))
    bake_vis, census_world = tools()
    vis, vlog, dom, seeds_in = run_vis(bake_vis, path, out, jobs)
    res["survey"] = seeds_in
    if vis is None:
        res["failures"].append(vlog); return res
    res["vis_domain"] = dom
    if kind == "game":
        # cross-check of the offline seeds: the same room as a world pack, its table grown from the entry points
        # alone, must cover the recorded cameras (the old method's seeds) in baked cells inside their bands
        try:
            wdata, _ = world_pack(room, entries, cot=cot); wpath = out / f"{room}.world.pak"; wpath.write_bytes(wdata)
            wvis, wlog, wdom, _ = run_vis(bake_vis, wpath, out, jobs)
            cov = route_coverage(wvis, Path(RECORDINGS[rid]["capture"])) if wvis else None
            res["offline_seed_check"] = dict(domain=wdom, recorded_cameras=cov)
            ok = cov and cov["in_band"] >= 0.95 * cov["pictures"]
            res["checks"]["offline_seeds_cover_recording"] = ("PASS" if ok else "FAIL") + (f" {cov['in_band']}/{cov['pictures']}" if cov else "")
        except Exception as e:
            res["checks"]["offline_seeds_cover_recording"] = f"FAIL {type(e).__name__}: {e}"
    # check 2: the reachable floor is seeded (an entry point that is not on a floor seeds nothing)
    reach = dom["reachable"] if dom else 0
    res["checks"]["seeded_floor"] = "PASS" if reach > 0 else "FAIL (no reachable cell: the seeds are not on the room's floor)"
    if reach == 0: res["failures"].append("visibility: no reachable cell from the seeds")
    c = subprocess.run([str(census_world), str(path), str(vis), "%.6f" % cot], capture_output=True, text=True)
    (out / f"{path.stem}.census.log").write_text(c.stdout + c.stderr)
    res["checks"]["census_world"] = "PASS" if c.returncode == 0 and "census ok" in c.stdout else f"FAIL exit {c.returncode}"
    if c.returncode != 0: res["failures"].append(f"census_world exit {c.returncode}"); return res
    res["world"] = keyvals(c.stdout)
    texrows, secs = texture_rows(data, world_tids)
    res["sections"] = [len(s) for s in secs]
    by = {}
    for t in texrows:
        k = ("world" if t["world"] else "other", t["kind"]); by[k] = by.get(k, 0) + t["bytes"]
    res["textures"] = dict(count=len(texrows), world=sum(t["world"] for t in texrows),
                           world_bytes=sum(t["bytes"] for t in texrows if t["world"]),
                           other_bytes=sum(t["bytes"] for t in texrows if not t["world"]),
                           by_kind={f"{a}:{b}": v for (a, b), v in sorted(by.items())},
                           names={n: sum(1 for t in texrows if t["name"] == n) for n in sorted({t["name"] for t in texrows})})
    res["materials"] = int(res["world"]["r4im"]["parts"])
    res["headers"] = len(blocks(secs[1]))
    rt = int(res["world"]["runtime"]["bytes"]); vb = vis.stat().st_size; dec = int(res["world"]["vis"]["decode_bytes"])
    res["ram_at_load"] = len(data) - len(secs[0]) + rt + vb + dec
    res["vis_bytes"] = vb
    res["lights_recorded"] = light_count(rid)
    from native_world import live_objects
    res["live_objects_left_out"] = sorted(live_objects(DISC / "native" / room).items())   # (placement, (kind, id))
    res["lights_lit"] = (tables.get(room) or {}).get("lights")
    res["lights_lit_max"] = max((tables.get(room) or {}).get("lights_per_cut") or [0]) or None
    res["lit_cuts"] = (tables.get(room) or {}).get("lit_cuts")
    res["seconds"] = round(time.time() - t0, 1)
    return res


PLACES = {"r100": "the first house", "r101": "village", "r103": "farm", "r107": "pool", "r108": "river", "r109": "the cabin",
          "r10b": "lake (lake boss)", "r11d": "hill"}


def table(results):
    """the census as Markdown rows (numbers only: no game data)"""
    kib = lambda b: "%.0f" % (b / 1024)
    A = ["| Room | Place | Ch | Pack | Triangles | Vertices | Strips | Meshlets | Materials | Textures | VRAM world KiB "
         "| VRAM catalogue, HUD, effects KiB | Pack KiB | RAM at load KiB | RAM at load, room content only KiB "
         "| Lights: LIT cut 0 / most in a cut / recorded | GameCube-sourced texture rows |", "|" + "---|" * 17]
    B = ["| Room | Place | Baked cells | Largest view: staged vertices / triangles | View p99 / p90 / p50 staged vertices "
         "| Mean view staged vertices | Largest view without the table | Largest PVS vertices / triangles | Mean PVS vertices / triangles "
         "| Recorded route: mean / largest staged vertices |", "|" + "---|" * 10]
    for r in results:
        place = PLACES.get(r["room"], "")
        if not r.get("world"):
            why = "; ".join(r.get("failures") or [r.get("note", "")])
            A.append(f"| {r['room']} | {place} | {r.get('chapter', '')} | none | " + " | ".join(["-"] * 11)
                     + f" | {(r.get('inputs') or {}).get('lights_lit', '-')} / - / - | - |" + (f" <!-- {why} -->" if why else ""))
            continue
        w = r["world"]; L0 = w["level0"]; v = w["view"]; p = w["pvs"]; t = r["textures"]; pc = w.get("viewpct", {}); rt = w.get("route", {})
        gc = sum(n for name, n in t["names"].items() if name in ("source", "source-pair"))
        s = r["sections"]; content = r["ram_at_load"] - sum(s[3:13])
        A.append("| %s | %s | %s | %s | %s | %s | %s | %s | %d | %d | %s | %s | %s | %s | %s | %s / %s / %s | %d |" % (
            r["room"], place, r.get("chapter", ""), r["kind"], L0["triangles"], L0["vertices"], L0["strips"], L0["meshlets"],
            r["materials"], t["count"], kib(t["world_bytes"]), kib(t["other_bytes"]), kib(r["pack_bytes"]), kib(r["ram_at_load"]),
            kib(content), r.get("lights_lit"), r.get("lights_lit_max"),
            r.get("lights_recorded") if r.get("lights_recorded") is not None else "-", gc))
        route = "%s / %s" % (rt["mean_staged_vertices"], rt["max_staged_vertices"]) if r["kind"] == "game" and rt else "-"
        B.append("| %s | %s | %s | %s / %s | %s / %s / %s | %s | %s | %s / %s | %s / %s | %s |" % (
            r["room"], place, p["cells"], v["max_staged_vertices"], v["max_triangles"], pc.get("p99_staged_vertices", "-"),
            pc.get("p90_staged_vertices", "-"), pc.get("p50_staged_vertices", "-"), v["mean_staged_vertices"],
            w["novis"]["max_staged_vertices"], p["max_vertices"], p["max_triangles"], p["mean_vertices"], p["mean_triangles"], route))
    return "\n".join(A) + "\n\n" + "\n".join(B)


def chapter1(out, jobs):
    st = out / "stage1-tables.json"
    if st.exists() and "\"areas\"" in st.read_text(): tables = json.loads(st.read_text())
    else: tables = stage_tables(); st.write_text(json.dumps(tables, indent=1))
    cot = template_cot()
    results = []
    for room, ch, note in CHAPTER1 + COMPARE:
        if room == "r120":
            results.append(dict(room=room, chapter=ch, note=note, kind="none", failures=[], checks={},
                                inputs=inputs(room, tables=tables))); continue
        done = out / f"{room}.census.json"   # one file per room as it finishes; a rerun resumes
        if done.exists():
            results.append(json.loads(done.read_text())); continue
        log(f"== {room}")
        r = bake_room(room, out, tables, cot, jobs); r.update(chapter=ch, note=note); results.append(r)
        done.write_text(json.dumps(r, indent=1))
        log(json.dumps({k: r.get(k) for k in ("room", "kind", "pack_bytes", "failures", "checks", "seconds")}))
    (out / "census.json").write_text(json.dumps(results, indent=1))
    (out / "census.md").write_text(table(results) + "\n")
    return results


def recensus(out):
    """re-run census_world over every baked room of census.json (after a change to the census tool)"""
    _, census_world = tools(); cot = template_cot()
    results = json.loads((out / "census.json").read_text())
    for r in results:
        if not r.get("pack") or not r.get("world"): continue
        pack = Path(r["pack"]); vis = pack.with_suffix(".vis")
        c = subprocess.run([str(census_world), str(pack), str(vis), "%.6f" % cot], capture_output=True, text=True)
        (out / f"{pack.stem}.census.log").write_text(c.stdout + c.stderr)
        if c.returncode == 0: r["world"] = keyvals(c.stdout)
        else: r["failures"].append(f"census_world exit {c.returncode}")
        (out / f"{r['room']}.census.json").write_text(json.dumps(r, indent=1)); log(r["room"], c.returncode)
    (out / "census.json").write_text(json.dumps(results, indent=1))
    (out / "census.md").write_text(table(results) + "\n")


def controls(out, jobs):
    """each check's failing input, run after --chapter1 (uses its packs); every row must say 'failed as it must'"""
    rows = []
    def row(name, failed, detail):
        rows.append(dict(check=name, result="failed as it must" if failed else "DID NOT FAIL", detail=detail)); log(rows[-1])
    tables = json.loads((out / "stage1-tables.json").read_text()); cot = template_cot()
    # 1. seeded floor: every entry point moved off the floor (r10a)
    r = bake_room("r10a", out, tables, cot, jobs, control_seeds=True)
    row("seeded_floor", any("reachable" in f or "bake_vis" in f for f in r["failures"]), r["failures"] or r.get("vis_domain"))
    # 2. census_world: the village pack against the farm's table
    _, census_world = tools()
    c = subprocess.run([str(census_world), str(out / "r101.pak"), str(out / "r103.vis"), "%.6f" % cot], capture_output=True, text=True)
    row("census_world table/pack match", c.returncode == 4, f"exit {c.returncode}")
    # 3. offline seed coverage: the village recording's cameras against the lake's world-pack table. (Not the farm's
    # or the hill's: those rooms share the village's world coordinates and their tables bake cells under the village
    # cameras, so they pass; the check tests that the cameras sit in baked cells, not which room baked them.)
    cov = route_coverage(out / "r10b.world.vis", Path(RECORDINGS[0x101]["capture"]))
    row("offline_seeds_cover_recording", cov["in_band"] < 0.95 * cov["pictures"], cov)
    # 4. HUD verify on a world pack (must refuse it)
    import hud_fix
    try: hud_fix.verify((out / "r10b.world.pak").read_bytes()); failed = False; d = "accepted"
    except ValueError as e: failed = True; d = str(e)[:120]
    row("hud_verify on a world pack", failed, d)
    # 5. receipt: a copy of receipt.json with the village pack's hash changed must mismatch
    if (out / "receipt.json").exists():
        doc = json.loads((out / "receipt.json").read_text()); o = doc["rooms"]["r101"]["outputs"]
        k = next(iter(o)); o[k] = "0" * 64
        (out / "receipt-control.json").write_text(json.dumps(doc))
        row("receipt check", not receipt(out, True, out / "receipt-control.json"), k)
        (out / "receipt-control.json").unlink()
    (out / "controls.json").write_text(json.dumps(rows, indent=1))
    return all(r["result"] == "failed as it must" for r in rows)


def sha(p):
    import hashlib
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""): h.update(chunk)
    return h.hexdigest()


def receipt(out, check=False, path=None):
    """receipt.json: per room the hashes of its inputs, of the bake scripts and of its outputs (pack, table).
    With check, re-hash and list every room whose receipt no longer matches (exit 1 on any). Its control:
    --controls compares against a copy with one pack hash changed (receipt-control.json), which must mismatch."""
    import hashlib
    results = json.loads((out / "census.json").read_text())
    path = path or out / "receipt.json"
    # the scripts are hashed as committed at the bake's commit (the packs record which: bake_commit), so a later
    # change to report-only code does not void a receipt and a change to the bake does
    commit = json.loads(path.read_text())["bake_commit"] if check else os.environ.get("BAKE_COMMIT", "HEAD")
    root = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=HERE, capture_output=True, text=True, check=True).stdout.strip())
    commit = subprocess.run(["git", "rev-parse", commit], cwd=root, capture_output=True, text=True, check=True).stdout.strip()
    rel = sorted(str(p.relative_to(root)) for p in [*HERE.glob("*.py"), HERE / "census_world.c", ENGINE / "bench" / "bake_vis.c",
                                                      ENGINE / "render" / "native_world.c", TOOLS / "d367" / "stage_route.py"])
    common = {}
    for r_ in rel:
        b = subprocess.run(["git", "show", f"{commit}:{r_}"], cwd=root, capture_output=True)
        if b.returncode == 0: common["git:" + r_] = hashlib.sha256(b.stdout).hexdigest()
    common.update({str(p): sha(p) for p in [DISC / "tex.pak", TABLES, LEON_BIND_CH1, ISO] if p.exists()})
    rooms = {}
    for r in results:
        room = r["room"]; rid = int(room[1:], 16); ins = {}
        d = DISC / "native" / room
        if d.exists():
            ins.update({str(p): sha(p) for p in sorted(d.iterdir()) if p.is_file()})
        rec = RECORDINGS.get(rid)
        if rec:
            for p in sorted(Path(rec["capture"]).glob("*")):
                if p.is_file() and (p.suffix in (".bin", ".raw", ".json")): ins[str(p)] = sha(p)
            if rec.get("ram"): ins[rec["ram"]] = sha(rec["ram"])
        outs = {}
        for name in ([r["pack"], str(Path(r["pack"]).with_suffix(".vis"))] if r.get("pack") else []) + \
                    ([str(out / f"{room}.world.pak"), str(out / f"{room}.world.vis")] if r.get("kind") == "game" else []):
            if Path(name).exists(): outs[name] = sha(name)
        rooms[room] = dict(inputs=ins, outputs=outs)
    doc = dict(bake_commit=commit, common=common, rooms=rooms)
    if not check:
        path.write_text(json.dumps(doc, indent=1)); log("wrote", path, len(rooms), "rooms"); return True
    old = json.loads(path.read_text()); bad = []
    for k, v in old["common"].items():
        if doc["common"].get(k) != v: bad.append(("common", k))
    for room, e in old["rooms"].items():
        now = rooms.get(room, {})
        for part in ("inputs", "outputs"):
            for k, v in e[part].items():
                if now.get(part, {}).get(k) != v: bad.append((room, k))
    for b in bad: log("receipt mismatch", *b)
    log("receipt", "OK" if not bad else "MISMATCH %d" % len(bad)); return not bad


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--receipt", action="store_true", help="write receipt.json (input, script and output hashes) after --chapter1")
    ap.add_argument("--check-receipt", action="store_true", help="re-hash and compare with receipt.json (exit 1 on a mismatch)")
    ap.add_argument("room", nargs="?"); ap.add_argument("--out", type=Path, default=Path("/mnt/e/RE4DC-Lanes/eng-bake1/packs"))
    ap.add_argument("--chapter1", action="store_true"); ap.add_argument("--inputs", action="store_true")
    ap.add_argument("--control-seeds", action="store_true"); ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--table", type=Path, help="census.json -> Markdown rows")
    ap.add_argument("--controls", action="store_true", help="run every check's failing input (after --chapter1)")
    ap.add_argument("--recensus", action="store_true", help="re-run the census tool over census.json's packs")
    a = ap.parse_args(); a.out.mkdir(parents=True, exist_ok=True)
    if a.controls:
        sys.exit(0 if controls(a.out, a.jobs) else 1)
    if a.receipt or a.check_receipt:
        sys.exit(0 if receipt(a.out, a.check_receipt) else 1)
    if a.recensus:
        recensus(a.out); return
    if a.table:
        print(table(json.loads(a.table.read_text()))); return
    if a.inputs:
        tables = stage_tables()
        rows = [inputs(r, tables=tables) | dict(chapter=c, note=n) for r, c, n in CHAPTER1 + COMPARE]
        print(json.dumps(rows, indent=1)); return
    if a.chapter1:
        chapter1(a.out, a.jobs); return
    room = "r" + a.room.lower().lstrip("r")
    r = bake_room(room, a.out, stage_tables(), template_cot(), a.jobs, a.control_seeds)
    print(json.dumps(r, indent=1))
    sys.exit(1 if r["failures"] else 0)


if __name__ == "__main__":
    main()
