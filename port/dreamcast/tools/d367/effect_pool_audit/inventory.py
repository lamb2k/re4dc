#!/usr/bin/env python3
"""Reproducible lexical census of all public game-source effect request sites.

Comments/literals are removed before matching. Both preprocessor arms are kept.
This inventories named APIs, their effect-system wrappers, allocation factories,
and indirect query/owner APIs; it is not a claim of whole-program symbolic proof.
Every allocator/returned-handle consumer is reviewed separately in the report.
"""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

sys.dont_write_bytecode = True
from source_tools import mask_noncode

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
REQUESTS = {
    "PullEsp", "PullEspgen", "PullEspgenFront", "PullEspEspgen", "EspSeqSet",
    "EspEstSetSelect", "EspgenSeqSet", "EspgenDataSet", "EstSet", "Esp3f_Alloc",
    "EfmSeqSet", "SetEstTbl",
}
QUERIES = {
    "EspGetDmyPtr", "EspgenGetCallNo", "EspgenIncCallNo", "EspPullCoreKind",
    "EffGetToolState", "EffSetToolState", "EffClearToolState", "EffSetToolStateCallBack",
    "EffCallToolStateCallBack", "EffGetAreaState", "EffSetAreaState", "GetAreaState",
    "SetAreaState", "GetSstDispFlag", "SetSstDispFlag", "EspGenGetMoveLoop",
    "EspGenSetMoveLoop", "EffectEspDelete", "EffectEspgenDelete", "EffectEfmDelete",
    "EspDelete", "EspgenDelete", "EfmDelete", "r117_espEnd",
}
EXTRA_WRAPPERS = {"SstSet", "AreaSstSet", "EventCutEstSet", "EspSetWaterBomb",
                  "EspSetWaterHitmark", "EspSetEatEffect", "EstSetEm10WaterFall",
                  "EspDrawLaserLine", "EspDrawLaserLine2", "EspSetGatling", "EffEm2d_setTexRender"}
FUNCTION = re.compile(r"\b([A-Za-z_]\w*(?:::[~A-Za-z_]\w*)*)\s*\(")
CONTROL = {"if", "for", "while", "switch", "catch", "sizeof", "alignof", "decltype"}


def paired(text):
    pairs, stack = {}, []
    for index, char in enumerate(text):
        if char in "({[": stack.append((char, index))
        elif char in ")}]" and stack:
            opening, at = stack.pop()
            if (opening, char) in (("(", ")"), ("{", "}"), ("[", "]")):
                pairs[at] = index
    return pairs


def definitions(masked, pairs):
    result = []
    for match in FUNCTION.finditer(masked):
        name = match.group(1)
        if name in CONTROL: continue
        start = masked.index("(", match.start(), match.end())
        if start not in pairs: continue
        end = pairs[start] + 1
        tail = re.match(r"\s*(?:const\s*)?(?:noexcept\s*)?\{", masked[end:])
        if tail:
            body = end + tail.end() - 1
            if body in pairs:
                result.append(dict(name=name, start=match.start(), body=body, end=pairs[body] + 1))
    return result


def surrounding(defs, at):
    candidates = [row for row in defs if row["body"] < at < row["end"]]
    return max(candidates, key=lambda row: row["body"]) if candidates else None


def run(args):
    root, out = args.source.resolve(), args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    paths = subprocess.check_output(["rg", "--files", "src", "include", "port/dreamcast/game",
                                    "-g", "*.cpp", "-g", "*.c", "-g", "*.h", "-g", "*.hpp", "-g", "*.inc"],
                                   cwd=root, text=True).splitlines()
    sources = {}
    for path in sorted(paths):
        raw = (root / path).read_text(errors="replace")
        clean = mask_noncode(raw)
        pairs = paired(clean)
        sources[path] = raw, clean, pairs, definitions(clean, pairs)
    wrappers = set(EXTRA_WRAPPERS)
    # Follow named wrappers within the effect subsystem; room/enemy state
    # routines are consumers, not themselves labelled allocation APIs.
    changed = True
    while changed:
        changed = False
        pattern = re.compile(r"\b(?:" + "|".join(sorted(REQUESTS | wrappers)) + r")\s*\(")
        for path, (_, clean, _, defs) in sources.items():
            if not re.fullmatch(r"src/game/(?:esp\w*|Espgen\w*|est|eff_sys)\.cpp", path): continue
            for row in defs:
                name = row["name"]
                if name in REQUESTS | wrappers or name.endswith(("::move", "_Update")): continue
                if not (name.startswith(("Esp", "Est", "Eff", "AreaSst", "EventCut")) or name in {"SetWater", "SetSand", "SetEsp"}): continue
                if pattern.search(clean[row["body"] + 1:row["end"]]):
                    wrappers.add(name); changed = True
    rows, references, factories, handles = [], [], [], []
    api_names = REQUESTS | wrappers | QUERIES
    api = re.compile(r"\b(?:" + "|".join(sorted(api_names, key=len, reverse=True)) + r")\b")
    for path, (raw, clean, pairs, defs) in sources.items():
        for match in api.finditer(clean):
            name, at = match.group(), match.start()
            line = clean.count("\n", 0, at) + 1
            caller = surrounding(defs, at)
            rest = clean[match.end():]
            own = next((row for row in defs if row["start"] == at), None)
            if own: kind = "definition"
            elif not re.match(r"\s*\(", rest): kind = "reference"
            else:
                prefix = clean[clean.rfind("\n", 0, at) + 1:at]
                declaration = re.fullmatch(r"\s*(?:extern\s+)?(?:static\s+|inline\s+)*(?:void|int|u8|u16|u32|bool|cEsp\s*\*|cObj\s*\*|EspgenWork\s*\*)\s*", prefix)
                kind = "declaration" if declaration else "call"
            text = raw.splitlines()[line - 1].strip()
            row = dict(path=path, line=line, api=name, kind=kind,
                       caller=caller["name"] if caller else "<unresolved scope>" if kind == "call" else "",
                       family="request" if name in REQUESTS else "query_or_owner" if name in QUERIES else "wrapper",
                       source=text)
            references.append(row)
            if kind == "call": rows.append(row)
        for match in re.finditer(r"\bnew\s+cEsp[0-9a-fA-F]+\b|\bEspFuncTblSet\s*\(", clean):
            line = clean.count("\n", 0, match.start()) + 1
            factories.append(dict(path=path, line=line, source=raw.splitlines()[line - 1].strip()))
        for match in re.finditer(r"\b(?:cEsp\w*\s*\*|EspgenWork\s*\*|ActiveEspNum\b|pEspBuf\b|nEspgen\b|EspgenArray\b|Core_pEm\b|CoreKindTop\b|ToolState\b)", clean):
            # The full handle/pool scan is retained, including subsystems and
            # aliases, rather than assuming names containing 'esp' are pointers.
            line = clean.count("\n", 0, match.start()) + 1
            handles.append(dict(path=path, line=line, source=raw.splitlines()[line - 1].strip()))
    def write_csv(name, values):
        with (out / name).open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(values[0]) if values else [])
            writer.writeheader(); writer.writerows(values)
    write_csv("calls.csv", rows)
    write_csv("all-api-references.csv", references)
    write_csv("factory-sites.csv", factories)
    write_csv("handle-pool-sites.csv", handles)
    counts = Counter(row["api"] for row in rows)
    source_hashes = {path: hashlib.sha256(raw.encode()).hexdigest() for path, (raw, *_rest) in sources.items()
                     if any(row["path"] == path for row in references + factories + handles)}
    report = dict(scope=__doc__, files_scanned=len(sources), call_sites=len(rows),
                  request_calls=sum(counts[name] for name in REQUESTS),
                  request_calls_by_api={name: counts[name] for name in sorted(REQUESTS)},
                  calls_by_api=dict(sorted(counts.items())), wrappers=sorted(wrappers),
                  references_by_kind=dict(Counter(row["kind"] for row in references)),
                  unresolved_scope_calls=sum(row["caller"] == "<unresolved scope>" for row in rows),
                  factory_sites=len(factories), handle_pool_sites=len(handles), source_sha256=source_hashes,
                  source_head=subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip())
    (out / "inventory.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ("files_scanned", "call_sites", "request_calls", "request_calls_by_api", "wrappers")}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())
