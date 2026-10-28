#!/usr/bin/env python3
"""Reproduce the Build29 whole-source coverage manifest and reviewed split table.

Every tracked/unignored C/C++/assembly/include/definition source below src/ and
port/dreamcast/ is read. Candidate keyword/dispatch matches are discovery aids,
not proof that every semantic fallback is recognized or reachable. The reviewed
catalogue supplies classification, costs, counter gaps and chapter uncertainty.
"""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
sys.path.insert(0, str(HERE))
from source_catalog29 import ROWS

SUFFIXES = {".cpp", ".c", ".h", ".hpp", ".inc", ".S", ".s", ".def"}
PATTERNS = {
    "decline/recovery": re.compile(r"fallback|fall[ -]back|slow[ _-]?path|legacy|generic[ _-]?path|\bdeclin\w*|\bretr(?:y|ies)|\breload\w*|\bthrash\w*|\brefus\w*|no[ -](?:block|slot|contig)", re.I),
    "cache/admission": re.compile(r"\b(?:cache|memo|miss|evict|overflow|capacity|guard|rebuild)\w*", re.I),
    "dispatch": re.compile(r"\b(?:GXBegin|GXCallDisplayList|MeshDraw|CalcSk1_\w+|hermiteFast|re4dc_\w*(?:native|fast|submit|decode|materialize)\w*)\s*\("),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def disposition(path):
    if path.startswith("port/dreamcast/tools/"):
        return "tool-or-fixture-source; not game recipe"
    if path.startswith("port/dreamcast/tests/"):
        return "test-source; not game recipe"
    if path.startswith("port/dreamcast/game/public-assets/"):
        return "public-generated-placeholder; not private game data"
    if path.startswith("port/dreamcast/game/third_party/"):
        return "runtime-vendor; recipe-dependent"
    if path.startswith("src/lib/"):
        return "recovered-library; runtime selection recipe-dependent"
    if path.startswith("src/"):
        return "recovered-game-source; module selection recipe-dependent"
    if path.startswith("port/dreamcast/game/"):
        return "port-game-runtime; knob/recipe-dependent"
    if path.startswith("port/dreamcast/room/") and path != "port/dreamcast/room/main.cpp":
        return "shared-native-runtime; recipe-dependent"
    return "standalone-demo/probe/engine-source; not presumed game runtime"


def write_tsv(path, fields, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def display_sites(sites):
    """Keep the Markdown review table bounded; TSV retains every resolved site."""
    anchors = sites.split("; ")
    # Prefer one reference per owning file before extra references in that file.
    first_by_file = {}
    for anchor in anchors:
        first_by_file.setdefault(anchor.rsplit(":", 1)[0], anchor)
    selected = list(first_by_file.values())[:4]
    selected += [anchor for anchor in anchors if anchor not in selected][:4-len(selected)]
    omitted = len(anchors)-len(selected)
    return "; ".join(selected)+(f"; +{omitted} additional sites in source-splits.tsv" if omitted else "")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--recipe", type=Path, required=True, help="recipe_values29.py output JSON")
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--markdown", type=Path, help="optional generated reviewer table")
    args = ap.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    recipes = json.loads(args.recipe.read_text())
    assert recipes["status"] == "PASS"
    game = recipes["profiles"]["public-game"]["values"]
    qa = recipes["profiles"]["public-qa-audit29"]["values"]
    raw = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z", "--", "src", "port/dreamcast"], cwd=ROOT)
    paths = sorted({p.decode() for p in raw.split(b"\0") if p and Path(p.decode()).suffix in SUFFIXES})
    sources = {p: (ROOT/p).read_bytes() for p in paths}
    lines = {p: b.decode("utf-8", errors="replace").splitlines() for p, b in sources.items()}
    review_by_file = defaultdict(list)
    reviewed = []
    for spec in ROWS:
        anchors = []
        for path, needle in spec["anchors"]:
            assert path in lines, (spec["id"], "file absent", path)
            matches = [i for i, line in enumerate(lines[path], 1) if needle in line]
            assert matches, (spec["id"], "anchor changed", path, needle)
            anchors.extend(path+":"+str(i) for i in matches)
            review_by_file[path].append(spec["id"])
        anchors = list(dict.fromkeys(anchors))
        assert all(k in game and k in qa for k in spec["knobs"]), (spec["id"], "recipe key absent")
        reviewed.append({k: v for k, v in spec.items() if k not in ("anchors", "knobs")} | dict(
            sites="; ".join(anchors), public_game_values=" ".join(k+"="+game[k] for k in spec["knobs"]),
            public_qa_differences=" ".join(k+"="+qa[k] for k in spec["knobs"] if qa[k] != game[k]) or "same"))
    fields = ["id", "category", "kind", "sites", "public_game_values", "public_qa_differences", "trigger", "modelled_cost_per_item", "chapter_1_2_reachability", "counters", "offline_evidence"]
    write_tsv(out/"source-splits.tsv", fields, reviewed)
    candidates, manifest = [], []
    corpus = hashlib.sha256()
    for path in paths:
        count = 0
        for number, line in enumerate(lines[path], 1):
            kinds = [kind for kind, pattern in PATTERNS.items() if pattern.search(line)]
            if not kinds:
                continue
            candidates.append(dict(file=path, line=number, candidate=";".join(kinds), disposition=disposition(path),
                                   reviewed_groups=";".join(sorted(set(review_by_file[path]))), excerpt=line.strip()[:240]))
            count += 1
        digest = sha(sources[path])
        corpus.update(path.encode()+b"\0"+digest.encode()+b"\n")
        manifest.append(dict(file=path, sha256=digest, bytes=len(sources[path]), lines=len(lines[path]),
                             disposition=disposition(path), candidate_lines=count,
                             reviewed_groups=sorted(set(review_by_file[path]))))
    write_tsv(out/"source-candidates.tsv", ["file", "line", "candidate", "disposition", "reviewed_groups", "excerpt"], candidates)
    # Map every inherited DFA and new FA29 registry symbol to current source
    # references. A reference can be a macro argument/branch return/comment;
    # the catalogue and existing Build26 reports explain its semantics.
    reasons = []
    inc = "port/dreamcast/game/platform/include/"
    definitions = [("DFA26", inc+"draw_fallback_"+part+".def") for part in ("world", "model", "other")]
    definitions += [("FA29", inc+"fallback_audit29.def")]
    for family, path in definitions:
        for definition_line, line in enumerate(lines[path], 1):
            match = re.match(r"(?:DFA26|FA29)_REASON\((\w+),\s*\"([^\"]+)\",\s*\"([^\"]+)\"\)", line)
            if not match:
                continue
            symbol, label, unit = match.groups()
            reasons.append(dict(family=family, symbol=symbol, label=label, unit=unit,
                                definition=path+":"+str(definition_line), source_references=""))
    refs = defaultdict(list)
    tokens = re.compile(r"\b(?:"+"|".join(re.escape(row["symbol"]) for row in reasons)+r")\b")
    for path in paths:
        if "tools/" in path or "tests/" in path or Path(path).suffix==".def":
            continue
        for number, line in enumerate(lines[path], 1):
            for token in sorted(set(tokens.findall(line))):
                refs[token].append(path+":"+str(number))
    for row in reasons:
        row["source_references"]="; ".join(refs[row["symbol"]])
        row["reference_notes"]="direct symbol references; may include comments and macro arguments"
    # The seven ActorPlan counters are dispatched by contiguous enum offset;
    # their middle entries correctly have no literal name at the call site.
    plans = ("ActorPlanBind", "ActorPlanPre", "ActorPlanRoles", "ActorPlanRow", "ActorPlanHand", "ActorPlanSem", "ActorPlanMat")
    assert tuple(row["symbol"] for row in reasons if row["symbol"] in plans)==plans
    plan_path="port/dreamcast/game/platform/native_actor_fast.cpp"
    plan_refs=[plan_path+":"+str(i) for i,line in enumerate(lines[plan_path],1) if "ActorPlanBind + kind" in line]
    assert len(plan_refs)==1, "indexed ActorPlan dispatcher changed; review the mapping"
    for row in reasons:
        if row["symbol"] in plans:
            row["source_references"]="; ".join(sorted(set(refs[row["symbol"]]+plan_refs)))
            row["reference_notes"]="ActorPlanBind+kind indexed dispatch; contiguous seven-entry range asserted in production and generator"
    write_tsv(out/"draw-reason-sites.tsv", ["family", "symbol", "label", "unit", "definition", "source_references", "reference_notes"], reasons)
    report = dict(status="PASS", scope=__doc__, corpus_sha256=corpus.hexdigest(), files_walked=len(paths),
                  bytes_walked=sum(len(b) for b in sources.values()), lines_walked=sum(len(v) for v in lines.values()),
                  candidate_lines=len(candidates), candidate_files=sum(bool(m["candidate_lines"]) for m in manifest),
                  reviewed_split_groups=len(reviewed), reviewed_categories=dict(Counter(r["category"] for r in reviewed)),
                  reason_counts=dict(Counter(r["family"] for r in reasons)), dispositions=dict(Counter(m["disposition"] for m in manifest)),
                  patterns={k: v.pattern for k, v in PATTERNS.items()},
                  source_sha256={str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in (Path(__file__), HERE/"source_catalog29.py")},
                  recipe_scope="actual public-game and public-qa-audit29 Make values; 1088 queried knobs in recorded run; private staged package admission unobserved",
                  limitations=["A whole-source read/candidate manifest is not a proof of all dynamic or semantically unnamed fallback branches.",
                      "Reviewed groups are explicit classifications, not blanket validation of every candidate in their source file.",
                      "False-positive examples: em_sub.cpp random-item fallback changes gameplay outcomes, not fast-vs-slow implementation; source assert/abort is not successful fallback; src/lib MPEG lookahead is not proof the native movie path uses that decoder.",
                      "Source-level reachability is distinct from actual chapter 1-2 data, live visibility, input sequence, device errors and private provenance acceptance.",
                      "MODELLED structural work/bytes are not hardware cycles. Numeric Build29 observer/data-fixture receipts are separate."])
    (out/"coverage-summary.json").write_text(json.dumps(report, indent=2)+"\n")
    # One record per line keeps a reviewable, compact complete hash manifest.
    with (out/"coverage-manifest.jsonl").open("w") as stream:
        for record in manifest:
            stream.write(json.dumps(record, separators=(",", ":"))+"\n")
    if args.markdown:
        text = ["# Build29 reviewed whole-source fallback sweep", "",
                "Generated by `source_sweep29.py` from `source_catalog29.py` and the actual public Make recipe receipt. "
                "Physical `file:line` anchors name the source on this branch; compiler `#line` diagnostics may differ.", "",
                f"The coverage manifest reads **{len(paths):,} source files / {report['lines_walked']:,} lines**, records **{len(candidates):,} keyword/dispatch candidate lines**, "
                f"and reviews **{len(reviewed)} split groups**. This is a reproducible discovery/review boundary, not an assertion that every semantic branch or real-data trigger has been observed.", "",
                "## Reading the table", "",
                "`work fallback` performs alternative required work; `compile alternative` is selected by recipe and cannot be called a per-frame miss; "
                "`guard/drop/failure` has no successful slow image/audio result. Costs are **MODELLED structural work and traffic**, not console timings. "
                "B=payload bytes, V=vertices, W=matrices, N=visited records, K=keys, L=effective lights. A minimum `ceil(B/32)` line count assumes a contiguous aligned span; "
                "unaligned spans may touch another line, revisits can reload a line, and writes can allocate/evict lines. No D-cache miss rate is invented.", "",
                "Recipe values below are the actual public-game command, including public missing-data overrides (for example `NMR_POOL_LOD=0`, whereas tracked CH2 requests 1). "
                "QA changes are listed separately. The full recipe receipt includes all queried feature families. These values do not certify private package admission.", "",
                f"The refreshed public recipe resolves `ACTOR_LIGHT_FAST_ONLY={game['ACTOR_LIGHT_FAST_ONLY']}`. "
                "When this switch is 1, Build25 owns lighting, bypasses the old probe/exact dispatch and the Build29 bake adapter, and suppresses those scanner predictions. "
                "The queue's earlier barn exact-light counts belong to their original image recipe. Preserve that recipe when reproducing the observation; "
                "an explicit FAST_ONLY0 conversion comparison is a separate variant and is not an incremental gain claim over the current FAST_ONLY1 release.", "",
                "Chapter reachability is source-level possibility unless the row explicitly cites the queue's existing barn console observation. "
                "The scanner and F29P/F29L live context are needed to assign light failures to actual Ganado, pitchfork, hay or barn prop parts. "
                "No model name or top offender is invented from unavailable game data.", "",
                "Inherited Build26 individual reason references and units are preserved in `draw-reason-sites.tsv`; they complement the "
                "Build26 draw/model/world reports already in `docs/cloud/`. New FA29 bins are a bounded diagnostic subset; the table explicitly names uninstrumented paths.", "",
                "Each Markdown group shows at most four representative source anchors. The complete resolved anchors are retained in "
                "[source-splits.tsv](../../../tools/d367/fallback_scan/receipts/source-splits.tsv), including every site omitted from this table.", ""]
        for category in dict.fromkeys(r["category"] for r in reviewed):
            text += ["## "+category, "", "| ID / kind / source | Resolved recipe | Trigger and result | MODELLED per-item work/traffic | Chapter 1-2 / diagnostics / data |", "|---|---|---|---|---|"]
            for r in reviewed:
                if r["category"] != category:
                    continue
                cells = [r["id"]+"; "+r["kind"]+"; "+display_sites(r["sites"]), r["public_game_values"]+"; QA: "+r["public_qa_differences"],
                         r["trigger"], r["modelled_cost_per_item"], r["chapter_1_2_reachability"]+" Counters: "+r["counters"]+" Offline: "+r["offline_evidence"]]
                text.append("| "+" | ".join(cell.replace("|", "\\|").replace("\n", " ") for cell in cells)+" |")
            text.append("")
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text("\n".join(text))
    print(json.dumps({k: report[k] for k in ("status", "files_walked", "lines_walked", "candidate_lines", "reviewed_split_groups", "reason_counts", "corpus_sha256")}))


if __name__ == "__main__":
    main()
