"""Room demand discovery (`assets.sh discover <room>`): what a room can load, and whether the
build and the prepared disc provide it. Static: the source game data plus the port's own source
tables, no emulator. `--log run-output.txt` compares one run against the prediction.

Sources, in the order the game uses them:
  * the enemy list (etc/emleonNN.esl) chosen by stage.cpp checkEmListNo for the room; every entry
    of the room is a possible spawn. Entries with the alive bit set in the file spawn at entry;
    entries without it spawn only after a room script or story state enables them (em2a in r100).
  * the room script (src/st<N>/r<room>.cpp): EmSetFromList2(<entry>) spawns, EmReadSearch /
    SearchEmModule(<id>) direct archive loads (event reservations, shared Ganado data).
  * enemy id -> read.cpp EmFileTbl[id] (Leon's table) -> dvd.cpp FileTbl names: the archive
    (em/emXX.das, prepared as .drs when the entry has a DLL) and the REL (rel/emXX.rel).
  * the prepared archive header: u32 LE at 0x24 is the heap-4 allocation readEmData makes
    (matches "DVD: Mem Alloc" in run logs).
Checks: the REL is linked (Makefile MODULES, platform/modules.cpp MODULE(id, name) with the
rel.json module_id, the ENEMY_DEMAND audit list), no missing-symbol stub names it, the prepared
archive exists, at most 4 enemy archives are live (read.cpp EmReadModule[4]), and the enemy
archives fit the room's measured heap-4 room for them (rooms.toml [room.X.demand]).
Round 2 (wiring.py): the porting-trap lint over each needed module and the room's stage module, and
`--wire`, which writes the module wiring (MODULES, modules.cpp, and the ENEMY_DEMAND audit list when
the lint is clean) into the checked tree; and the heap-4 options per enemy archive (enemy_heap.py)
with a plan that covers a shortfall; and the room's events (events.py: evd actors, route movie or
prepared + qualified evd); and Standard budgets + VRAM (standard.py).
"""
import json
import re
import struct
from pathlib import Path

from .util import write_json
from .wiring import fix_module, lint_module, wire as wire_module
from . import enemy_heap, events as event_files, standard
from .rooms import GcIso

ESL_REC = struct.Struct(">BBBBIHBB3h3hHh4x")   # include/em_set.h EmListData (big-endian source)
EM_SLOTS = 4                                     # read.cpp EmReadModule[4]
ESL_FILES = ["etc/emleon0%d.esl" % i for i in range(8)] + ["etc/omake0%d.esl" % i for i in range(3)]


def _num(s):
    return int(s, 0)


class Tables:
    """The port's source tables (read from the checkout, never copied)."""

    def __init__(self, repo):
        self.repo = Path(repo)
        s = (self.repo / "src/game/dvd.cpp").read_text()
        b = s[s.index("FileTblEntry FileTbl[] = {"):]
        self.files = re.findall(r'\{"([^"]*)",\s*0\}', b[:b.index("};")])
        r = (self.repo / "src/game/read.cpp").read_text()
        t = r[r.index("ReadFile EmFileTbl[64] = {"):]
        self.em = [tuple(int(x, 16) if i < 2 else int(x) for i, x in enumerate(m)) for m in re.findall(
            r"\{\s*0x([0-9A-Fa-f]+),\s*0x([0-9A-Fa-f]+),\s*(\d)\s*\}", t[:t.index("};")])]
        assert len(self.em) == 64, len(self.em)

    def enemy(self, eid):
        """{archive, rel, module} for enemy id, or None when the id has no file (objects, doors)."""
        if eid >= len(self.em) or self.em[eid][0] == 0:
            return None
        f, rel, dll = self.em[eid]
        arc = self.files[f]
        if dll:
            arc = arc.rsplit(".", 1)[0] + ".drs"
        out = {"archive": arc}
        if dll:
            out["rel"] = self.files[rel]
            out["module"] = Path(self.files[rel]).stem
        return out


def esl_list_numbers(room):
    """stage.cpp checkEmListNo for Leon's main game (System_flg bits 31 / 30, Assignment Ada and the Mercenaries,
    clear; stage 4 has no main-game list and uses its own omake lists): [(list, condition)]."""
    stage = room >> 8
    if stage == 1:
        if room == 0x120:
            return [(0, "always")]
        if room == 0x10E:
            return [(1, "System_flg & 0x2000"), (None, "else: keeps the current list")]
        return [(1 if room > 0x10B else 0, "always")]
    if stage == 2:
        if room in (0x22B, 0x22C, 0x22D):
            return [(None, "always: keeps the current list")]
        if room == 0x200:
            return [(1, "!(Scenario_flg[0] & 0x800000)"), (2, "else")]
        if room > 0x219:
            return [(4 if room == 0x222 else 5, "always")]
        if room > 0x210:
            return [(4, "always")]
        # emListVillage: rooms 200..204 / 207 / 208 use list 2 until the church bell (Scenario_flg[0] 0x40000)
        late = [(4, "Scenario_flg[0] & 0x10000000")]
        if room in (0x200, 0x201, 0x202, 0x203, 0x204, 0x207, 0x208):
            return late + [(2, "else, !(Scenario_flg[0] & 0x40000)"), (3, "else")]
        return late + [(3, "else")]
    if stage == 3:
        return [(6 if room <= 0x314 else 7, "always")]
    if stage == 4:
        if room > 0x404:
            return [(8, "always")]
        return [(10 if room in (0x403, 0x404) else 9, "always")]
    raise SystemExit("discover: stage %d list rules not mirrored yet (stage.cpp checkEmListNo)" % stage)


def esl_entries(path, room):
    data = Path(path).read_bytes()
    out = []
    for no in range(len(data) // 0x20):
        be, eid, typ, st, flag, hp, _, ch, px, py, pz, rx, ry, rz, rm, guard = ESL_REC.unpack_from(data, no * 0x20)
        if eid and rm == room:
            out.append({"no": no, "id": eid, "type": typ, "set": st, "flag": "%08x" % flag,
                        "alive": bool(be & 1), "pos_mm": [px * 10, py * 10, pz * 10]})
    return out


def script_refs(repo, room):
    p = Path(repo) / ("src/st%x/r%03x.cpp" % (room >> 8, room))
    if not p.exists():
        return {"file": None, "list_spawns": [], "loads": []}
    s = p.read_text()
    spawns = sorted({_num(m) for m in re.findall(r"EmSetFromList2\(\s*(0x[0-9a-fA-F]+|\d+)", s)})
    loads = sorted({_num(m) for m in re.findall(r"(?:EmReadSearch|SearchEmModule)\(\s*(0x[0-9a-fA-F]+|\d+)", s)})
    return {"file": str(p.relative_to(repo)), "list_spawns": spawns, "loads": loads}


def build_state(repo, obj=None):
    dc = Path(repo) / "port/dreamcast/game"
    mk = (dc / "Makefile").read_text()
    modules = re.search(r"^MODULES = (.*)$", mk, re.M).group(1).split()
    m = re.search(r"ifeq \(\$\(ENEMY_DEMAND\),1\)\s*\nifneq \(\$\(filter-out ([^,]*),\$\(MODULES\)\)", mk)
    audited = m.group(1).split() if m else []
    table = {name: int(i) for i, name in re.findall(r"MODULE\((\d+),\s*(\w+)\)", (dc / "platform/modules.cpp").read_text())}
    miss = Path(obj) / "missing.txt" if obj else dc / "obj/missing.txt"
    missing = miss.read_text().split() if miss.exists() else None
    return {"modules": modules, "audited": audited, "table": table, "missing": missing, "missing_file": str(miss)}


def rel_id(repo, module):
    p = Path(repo) / "config/G4BE08/modules" / module / "rel.json"
    return json.loads(p.read_text()).get("module_id") if p.exists() else None


def source_heap4_bytes(iso, archive):
    """Body size of the source (big-endian) archive on the GC disc: what an unprepared archive
    allocates (the LE conversion keeps the size; compaction is what shrinks it)."""
    if iso is None or iso.find(archive) is None:
        return None
    h = iso.read(archive)[:0x28]
    return struct.unpack_from(">I", h, 0x24)[0] if len(h) >= 0x28 else None


def room_container(prepared, iso, room):
    """The room's DVD container: prepared (.dar + .arc in the mirror) or only on the GC disc."""
    rel = "st%x/r%03x" % (room >> 8, room)
    dar, arc = Path(prepared) / (rel + ".dar"), Path(prepared) / (rel + ".arc")
    out = {"dar": dar.exists(), "arc": arc.exists(),
           "source": bool(iso and iso.find(rel + ".das"))}
    if out["arc"]:
        out["arc_bytes"] = arc.stat().st_size
    return out


def heap4_bytes(prepared_dir, archive):
    p = Path(prepared_dir) / archive
    if not p.exists():
        return None
    h = p.read_bytes()[:0x28]
    return struct.unpack_from("<I", h, 0x24)[0] if len(h) >= 0x28 else None


def stage_module(repo, room):
    """The stage REL whose units hold the room script (st1_0 for r100 ...)."""
    for d in sorted((Path(repo) / "config/G4BE08/modules").glob("st*")):
        sp = d / "splits.txt"
        if sp.exists() and re.search(r"^st\w*/r%03x\.cpp:" % room, sp.read_text(), re.M):
            return d.name
    return None


def lint_problems(mod, findings):
    return ["%s %s: lint %s %s:%d  %s" % ("error" if f["severity"] == "error" else "warning", mod, f["rule"],
                                         f["file"], f["line"], f["text"][:90]) for f in findings]


def discover(cfg, room_name, repo=None, obj=None, log=None, out_dir=None, wire=False, fix=False):
    repo = Path(repo or cfg.path("checkout") or Path(__file__).resolve().parents[4])
    room = int(room_name.lstrip("r"), 16)
    game = cfg.path("game_data")
    prepared = cfg.path("prepared_mirror")
    tab = Tables(repo)
    lists = esl_list_numbers(room)
    entries = []
    for no, cond in lists:
        if no is None:
            continue
        for e in esl_entries(game / ESL_FILES[no], room):
            e["list"] = ESL_FILES[no]
            e["list_condition"] = cond
            entries.append(e)
    sc = script_refs(repo, room)
    by_no = {e["no"]: e for e in entries}
    need = {}   # enemy id -> {reasons}
    iso = GcIso(cfg.path("gc_iso")) if cfg.path("gc_iso") and Path(cfg.path("gc_iso")).exists() else None

    def add(eid, why):
        need.setdefault(eid, set()).add(why)
    for e in entries:
        add(e["id"], "entry" if e["alive"] else "enabled-later")
    for no in sc["list_spawns"]:
        if no in by_no:
            add(by_no[no]["id"], "script-spawn")
    for eid in sc["loads"]:
        add(eid, "script-load")
    bs = build_state(repo, obj)
    rcfg = cfg.room(room_name).get("demand", {})
    rows, problems, warnings = [], [], []
    smod = stage_module(repo, room)
    fixed = []

    def fixes(mod):
        """--fix: rewrite the mechanical traps first; "review"/"manual" ones stay findings to read."""
        if not fix:
            return
        for f in fix_module(repo, mod):
            fixed.append(dict(f, module=mod))
            if f["fix"] != "fixed":
                warnings.append("%s: fix %s %s %s:%d  %s" % (mod, f["fix"], f["rule"], f["file"], f["line"], f["text"][:90]))
    if smod:
        fixes(smod)
    stage_lint = lint_module(repo, smod) if smod else []
    problems.extend(lint_problems(smod, [f for f in stage_lint if f["severity"] == "error"]))
    warnings.extend(lint_problems(smod, [f for f in stage_lint if f["severity"] != "error"]))
    for eid in sorted(need):
        info = tab.enemy(eid) or {}
        r = {"id": "0x%02x" % eid, "reasons": sorted(need[eid]),
             "entries": [e["no"] for e in entries if e["id"] == eid], **info}
        if "archive" in info:
            r["heap4_bytes"] = heap4_bytes(prepared, info["archive"])
            if r["heap4_bytes"] is None:
                src = source_heap4_bytes(iso, info["archive"].replace(".drs", ".drs"))
                r["heap4_bytes"] = src
                r["heap4_basis"] = "source (unprepared)" if src is not None else "unknown"
                problems.append("%s: prepared archive %s missing in %s%s" % (
                    r["id"], info["archive"], prepared,
                    "; counted at its source size %d" % src if src is not None else "; size unknown"))
        mod = info.get("module")
        if mod:
            rid = rel_id(repo, mod)
            r["module_id"] = rid
            fixes(mod)
            r["lint"] = lint_module(repo, mod)
            errors = [f for f in r["lint"] if f["severity"] == "error"]
            if wire and rid is not None:
                r["wired"] = wire_module(repo, mod, rid, "%s: %s" % (room_name, ",".join(sorted(need[eid]))), audit=not errors)
                bs = build_state(repo, obj)
            chk = {"makefile": mod in bs["modules"], "audit": mod in bs["audited"],
                   "table": bs["table"].get(mod) == rid and rid is not None}
            if bs["missing"] is not None:
                key = mod.lower()
                chk["stubs"] = [s for s in bs["missing"] if key in s.lower()]
            r["build"] = chk
            warnings.extend(lint_problems(mod, [f for f in r["lint"] if f["severity"] != "error"]))
            problems.extend(lint_problems(mod, errors))
            for k in ("makefile", "audit", "table"):
                if k == "audit" and not chk[k] and errors:
                    problems.append("%s %s: not in the ENEMY_DEMAND audit list (fix the lint errors first)" % (r["id"], mod))
                    continue
                if not chk[k]:
                    problems.append("%s %s: not in %s%s" % (r["id"], mod, {"makefile": "Makefile MODULES",
                                    "audit": "the ENEMY_DEMAND audit list", "table": "platform/modules.cpp MODULE(%s, %s)" % (rid, mod)}[k],
                                    "" if k != "table" else " (rel.json module_id %s)" % rid))
            if chk.get("stubs"):
                problems.append("%s %s: missing-symbol stubs %s" % (r["id"], mod, ", ".join(chk["stubs"])))
        rows.append(r)
    arcs = [r for r in rows if r.get("archive")]
    total = sum(r.get("heap4_bytes") or 0 for r in arcs)
    budget = rcfg.get("enemy_heap4_bytes")
    heap = {"enemy_archives": len(arcs), "slots": EM_SLOTS, "worst_case_bytes": total,
            "budget_bytes": budget, "budget_source": rcfg.get("enemy_heap4_source")}
    comp_path = cfg.path("enemy_compaction")
    summary = json.loads(Path(comp_path).read_text()) if comp_path and Path(comp_path).exists() else {}
    con = enemy_heap.contracts(repo)
    opts = []
    for r in arcs:
        ap = Path(prepared) / r["archive"]
        if not ap.exists():
            continue
        br = enemy_heap.breakdown(ap)
        r["body"] = br
        name = Path(r["archive"]).name
        kind = "GANADO" if name in con["GANADO"] else ("SMALL" if name in con["SMALL"] else None)
        applied = summary.get(name[:-4]) or summary.get(name[:-4] + "-control")
        applied = applied if applied and applied.get("resident_body_bytes") == r.get("heap4_bytes") else None
        opts += enemy_heap.options(r["archive"], br, kind, applied)
    heap["options"] = opts
    if len(arcs) > EM_SLOTS:
        problems.append("%d enemy archives can be live, read.cpp has %d slots" % (len(arcs), EM_SLOTS))
    if budget is None:
        heap["verdict"] = "no budget: measure one run (--log) and record [room.%s.demand]" % room_name
    elif total > budget:
        heap["verdict"] = "SHORT by %d bytes when every archive is live" % (total - budget)
        heap["plan"] = enemy_heap.plan(total - budget, opts)
        problems.append("heap 4: enemy archives %d > measured room %d (short %d)" % (total, budget, total - budget))
    else:
        heap["verdict"] = "fits (%d spare)" % (budget - total)
    rc = room_container(prepared, iso, room)
    if not (rc["dar"] and rc["arc"]):
        problems.append("room container st%x/r%03x: not prepared (%s)" % (
            room >> 8, room, "on the GC disc: convert it (le_mirror / prepare_native_ui)" if rc["source"] else "not on the disc either"))
    evs, ev_problems = event_files.events(repo, room, iso, prepared, cfg.path("route_movies"))
    problems.extend(ev_problems)
    std, std_problems = standard.budgets(standard.std_set(cfg.root, room_name), budget,
                                         cfg.room(room_name).get("standard", {}).get("budget_context", {}))
    problems.extend(std_problems)
    res = {"room": room_name, "container": rc, "fixed": fixed, "events": evs, "standard": std, "lists": [{"list": ESL_FILES[n] if n is not None else None, "condition": c} for n, c in lists],
           "script": sc, "entries": entries, "demand": rows, "heap4": heap, "problems": problems, "warnings": warnings,
           "stage_module": smod,
           "inputs": {"repo": str(repo), "game_data": str(game), "prepared": str(prepared), "missing": bs["missing_file"]}}
    if log:
        res["run"] = compare_log(log, rows)
        res["run"]["vram"], vp = standard.vram_log(Path(log).read_text(errors="replace"))
        res["run"]["problems"] += vp
        problems.extend(res["run"]["problems"])
    if out_dir:
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        write_json(Path(out_dir) / ("%s.json" % room_name), res)
    return res


def compare_log(path, rows):
    t = Path(path).read_text(errors="replace")
    loaded = re.findall(r"DVD: Read File: (em/em[0-9a-f]{2}\.drs)", t)
    failed = re.findall(r"readEmData\(\): error! (em/\S+)", t)
    shortfalls = [(int(a, 16), int(f, 16)) for a, f in re.findall(r"alloc\[([0-9a-f]+)\]:free\[([0-9a-f]+)\]", t)]
    linked = re.findall(r"module: id (\d+) -> (\w+)", t)
    halts = re.findall(r"HALT [^\n]*", t)
    predicted = {r["archive"] for r in rows if r.get("archive")}
    out = {"loaded": sorted(set(loaded)), "failed": sorted(set(failed)), "linked": sorted({m for _, m in linked}),
           "halts": halts[:5], "problems": []}
    extra = sorted(set(loaded) - predicted)
    if extra:
        out["problems"].append("run loaded archives the discovery did not predict: %s" % ", ".join(extra))
    for f in sorted(set(failed)):
        out["problems"].append("run: %s failed to load" % f)
    if shortfalls:
        a, f = shortfalls[0]
        out["shortfall"] = {"alloc": a, "free": f, "short": a - f}
    for h in halts[:2]:
        out["problems"].append("run: %s" % h)
    return out


def report(res):
    print("== %s: lists %s; script %s" % (res["room"], ", ".join("%s (%s)" % (l["list"], l["condition"]) for l in res["lists"]),
                                           res["script"]["file"]))
    for r in res["demand"]:
        b = r.get("build", {})
        print("  %s %-12s %-9s heap4 %8s  %s%s" % (
            r["id"], r.get("archive", "(no file)"), r.get("module", "-"),
            r.get("heap4_bytes", "-"), ",".join(r["reasons"]),
            ("  build " + " ".join("%s=%s" % (k, "ok" if v is True else ("NO" if v is False else (v or "none")))
                                   for k, v in b.items())) if b else ""))
    rc = res.get("container") or {}
    print("  room container: %s" % ("prepared (arc %d B)" % rc.get("arc_bytes", 0) if rc.get("dar") and rc.get("arc")
                                     else "NOT prepared" + (" (source on disc)" if rc.get("source") else "")))
    for f in res.get("fixed", []):
        print("  fix %-6s %-10s %s %s:%d" % (f["fix"], f["rule"], f["module"], f["file"], f["line"]))
    for e in res.get("events", []):
        if not e["on_disc"]:
            print("  event %s: not on the disc (named only)" % e["event"])
            continue
        print("  event %s %8d B %3d assets  %s  actors %s" % (
            e["event"], e["bytes"], e["assets"],
            "movie" if e["movie"] else ("evd qualified" if e["prepared"] and e["qualified"] else "EVD MISSING"),
            " ".join("%s x%d" % kv for kv in e["actor_groups"].items())))
    h = res["heap4"]
    print("  heap 4: %d enemy archives (slots %d), worst case %d bytes, budget %s: %s" % (
        h["enemy_archives"], h["slots"], h["worst_case_bytes"], h["budget_bytes"], h["verdict"]))
    for o in h.get("options", []):
        if o["status"] != "applied":
            print("    option %-13s %-14s %8d  %s (%s)" % (o["archive"], o["option"], o["bytes"], o["status"], o["basis"]))
    if h.get("plan"):
        pl = h["plan"]
        print("    plan for %d short: %s -> covers %d, remaining %d" % (
            pl["short"], " + ".join("%s %s (%s)" % (o["archive"].split("/")[-1][:-4], o["option"], o["status"]) for o in pl["chosen"]) or "-",
            pl["covered"], pl["remaining"]))
    h = res["heap4"]
    st = res.get("standard") or {}
    if "heap_delta" in st:
        print("  standard: packages %d vs Original %d (heap %+d)%s; adds %d textures %d B VRAM, drops %d" % (
            st["mesh_bytes"], st["orig_bytes"], st["heap_delta"],
            ("; enemy heap-4 room %d: %s" % (st["enemy_heap4_bytes"], ("fits (%d spare)" % (st["enemy_heap4_bytes"] - h["worst_case_bytes"]))
             if st["enemy_heap4_bytes"] >= h["worst_case_bytes"] else "SHORT by %d" % (h["worst_case_bytes"] - st["enemy_heap4_bytes"])))
            if "enemy_heap4_bytes" in st else "",
            st["tex"], st["tex_vram"], st["drops"]))
        if "vram" in st:
            v = st["vram"]
            print("  standard VRAM: pool %d, Original used %d + %d = %d at most (free >= %d; %s)" % (
                v["pool"], v["original_used"], st["tex_vram"], v["standard_used_max"], v["standard_free_min"], v["source"]))
    elif st:
        print("  standard: " + st.get("verdict", ""))
    if "run" in res and res["run"].get("vram"):
        v = res["run"]["vram"]
        print("  run VRAM: lowest free %s, peak used %s, rejects %d, missing texture packages %d" % (
            v["min_free"], v["max_used"], v["rejects"], len(v["missing_textures"])))
    if "run" in res:
        run = res["run"]
        print("  run: loaded %s; failed %s; linked %s%s" % (", ".join(run["loaded"]) or "-", ", ".join(run["failed"]) or "-",
                                                         ", ".join(run["linked"]),
                                                         ("; shortfall %s" % run["shortfall"]) if "shortfall" in run else ""))
    for r in res["demand"]:
        for w in r.get("wired") or []:
            print("  WIRED " + w)
    for w in res.get("warnings", []):
        print("  WARNING " + w)
    for p in res["problems"]:
        print("  PROBLEM " + p)
    if not res["problems"]:
        print("  ok")
