"""Write bounded MODELLED results, preserving partial world attribution as a limit."""
import csv
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import re

root = Path("/mnt/c/Flycast-Evidence/re4-dreamcast/world-rebuild27-20261027")
profile = Path("/root/re4data/private/world-rebuild27-20261027/model-profile-v1")
symbols = json.loads((profile / "symbols-world.json").read_text())["symbols"]
names = {r["symbol"]: r["name"] for r in symbols}
names[0] = "UNKNOWN"
explicit = {r["symbol"]:r["owner"] for r in symbols if r["owner"]}
bench_path = Path("/root/work/lanes/world-rebuild27-model/port/dreamcast/tools/d367/benchmark/bench-split.py")
spec = importlib.util.spec_from_file_location("bench", bench_path)
bench = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench)

def category(name):
    if name == "UNKNOWN": return "Unknown invocation context"
    if re.search(r"ScenerySelector|sg_select|box_class|world_out|inside|outside|visible", name): return "Selection and conservative rejection"
    if re.search(r"transform|concat|PSMTX|PSVEC|screen|constants|sqrtf", name): return "Vertex and placement transforms"
    if re.search(r"clip_strip|clip_tri|clip_polygon|clipper", name): return "Clipping"
    if re.search(r"begin_batch|header|material|texture|Texture|resolve|fog|Fog", name): return "Material, texture, fog and header setup"
    if re.search(r"walk_lean|emit|submit|chunk_strips|strip|sq_|pvr_", name): return "Strip preparation and submission"
    if re.search(r"ps2_pass|dyn::|ps2_dyn|ps2_mesh_draw|sobake", name): return "Pass dispatch, placement and owner work (mixed self time)"
    return "Other shared helpers under observed world roots"

result = dict(evidence="MODELLED nominal SH-4 CPU only", source_tick_window=[300,329], counted_ticks=30,
              traced_ticks=[300,329], timed_samples=2, observed_draws_per_timed_tick=1,
              status="Sparse proxy exceeds 2 ms even by validated world lower bound; complete total-world timing remains unqualified",
              denominator="Each timed source-tick interval contains one Render and three world mesh passes. Thirty counted ticks contain 30 Render and 90 mesh entries. Timing averages use two drawn worlds, not thirty.",
              cpu_work_estimator="Existing bench-split.py: sum exclusive function hw_ms after excluding main, re4dc_pace_end and re4dc_vi_retrace_count. It removes polling/wait rows wholesale; it is an estimate of CPU work, not observed frame latency or presentation cadence.",
              world_attribution="Existing charge-preserving logic18 contextual exporter against this exact current hwsim source. Owner 6 is explicitly rooted in re4dc_ps2_mesh_draw, ps2_pass and its split lambda. Disjoint node self charges are summed, never overlapping inclusive rows. Raw includes incomplete roots; validated charges cover only complete valid roots. Neither is certified complete world cost; validated cost is a lower bound on complete world CPU.",
              helper_sha256=hashlib.sha256(bench_path.read_bytes()).hexdigest(), arms=[])
for arm in ("A", "B1", "C4"):
    e = root / f"hwmodel-v1-{arm}-cross"
    log = (e / "trace/hwtrace.log").read_text()
    assert "counts written frames 300:329" in log and "hwtrace done: traced 2 frames; exiting" in log
    assert len(list((e / "trace").glob("trace-*.bin"))) == 2
    summary = json.loads((e / "profile-context/summary.json").read_text())
    world = next(r for r in summary["owners"] if r["owner"] == 6)
    entries = json.loads((e / "counted-entry-counts.json").read_text())
    assert entries["Render"]["executions"] == 30 and entries["re4dc_ps2_mesh_draw"]["executions"] == 90
    counts, _ = bench.split(e)
    functions = list(csv.DictReader((e / "proj/rep/functions.tsv").open(), delimiter="\t"))
    sums = dict(line.split(None,1) for line in (e / "proj/nominal.sum.txt").read_text().splitlines() if len(line.split())==2)
    raw, valid = Counter(), Counter()
    function_cost, valid_function_cost = Counter(), Counter()
    last = None
    for row in csv.DictReader((e / "profile-context/nominal.contexts.tsv").open(), delimiter="\t"):
        r = {k:int(v) for k,v in row.items()}
        if r["sample"] != last:
            nodes=[]; roots=[]; last=r["sample"]
        n, parent = r["node"], r["parent"]
        assert n==len(nodes)
        newroot = bool(r["owner"] and (n==0 or parent>=n or nodes[parent]["owner"]!=r["owner"] or explicit.get(r["symbol"])==r["owner"] or r["kind"]==2))
        rt = n if newroot else roots[parent] if parent<n else -1
        nodes.append(r); roots.append(rt)
        if r["owner"] == 6:
            name=names[r["symbol"]]; cost=r["self16"]/16/200000/2
            raw[category(name)] += cost; function_cost[name] += cost
            if rt>=0 and nodes[rt]["complete"] and not nodes[rt]["invalid"]:
                valid[category(name)] += cost; valid_function_cost[name] += cost
    assert abs(sum(raw.values())-world["raw_ms"])<1e-9
    assert abs(sum(valid.values())-world["validated_root_ms"])<1e-9
    phase_rows=[dict(category=k, raw_context_ms=v, validated_lower_bound_ms=valid[k]) for k,v in raw.most_common()]
    function_rows=[dict(function=k, raw_context_self_ms=v, validated_self_ms=valid_function_cost[k]) for k,v in function_cost.most_common()]
    (e / "profile-context/world-disjoint-breakdown.json").write_text(json.dumps(dict(categories=phase_rows, functions=function_rows,
       limitation="Disjoint contextual self costs; categories are function-name classifications, not phase instrumentation. Inlined work remains mixed in ps2_pass; raw root coverage is partial."),indent=2)+"\n")
    source_log=(e / "trace/run-output.txt").read_text(encoding="utf-16")
    scene=[line for line in source_log.splitlines() if line.startswith(("warp: start room", "warp: placed room", "warp: alert at"))]
    row=dict(arm=arm, evidence=str(e), elapsed_seconds=float((e/"trace/elapsed.txt").read_text().split()[1]),
             cpu_work_estimate_ms=sum(counts.values()), bench_world_exclusive_bucket_ms=counts["world submit"],
             world_raw_context_ms=world["raw_ms"], world_validated_lower_bound_ms=world["validated_root_ms"],
             validated_roots=world["validated_roots"], observed_roots=world["observed_roots"],
             complete_total_world_ms=None, raw_projection_with_polling_ms=float(sums["ms_per_frame"]),
             exact_model_output_parity=json.loads((e/"profile-context/parity.json").read_text())["status"],
             counted_function_entries=entries, scene_log=scene, disjoint_world_categories=phase_rows)
    result["arms"].append(row)
result["decision"]="B1 has at least 3.361 ms of validated world CPU per observed drawn world in this two-sample cross test, already above 2 ms. Investigate its remaining selection/rejection, mixed pass/owner traversal, transformation, clipping and submission before adding detail. B1 still retains 11,054 L0 triangles and exact dynamic-owner geometry, so these data do not isolate a geometry-independent traversal floor or certify a compiled candidate-list gain. Use the retained traces and actual-view asset census to choose a targeted ultra-sparse B2 control or a bounded candidate-list experiment."
functions=list(csv.DictReader((root/'hwmodel-v1-B1-cross/proj/rep/functions.tsv').open(),delimiter='\t'))
selected=[r for r in functions if r['area']=='scenery' or re.search(r'ScenerySelector|re4dc_ps2_world_direct|re4dc_chunk_strips',r['func'])]
result['B1_flat_source_self_rows']=[dict(function=r['func'],ms=float(r['hw_ms']),file=r['file']) for r in sorted(selected,key=lambda r:-float(r['hw_ms']))[:20]]
result['B1_flat_source_self_limits']='Disjoint exclusive function rows. These expose code left outside interrupted contextual ancestry; they are a second view of the same charges and must not be added to contextual totals. ps2_pass self time contains inlined traversal, setup and other work; a geometry-independent fixed floor is not isolated.'
result["limits"]=["Only two timed samples, at early alerted cross ticks 300 and 329; no p95/p99, route or steady-combat qualification.",
 "Full 30-tick PC counts validate denominator and representativeness; timing cache states come only from two traces.",
 "Complete total-world CPU is unqualified due partial contextual root coverage. The table must not rename raw or validated partial attribution as total world.",
 "No actual PVR timing, registration deadline, vertex-buffer budget or presentation cadence acceptance. Model-only LBA0 CD-R transport differs from strict-cache GDEMU and console transport.",
 "Matched fixture/programme/assets and placement/alert logs are verified. Only C4 has a full RAM camera snapshot at tick300; within-tick races are recorded.",
 "CPU-work estimates exclude all main self time, including any non-wait overhead there, and do not establish a 30 fps frame deadline."]
(root/"MODELLED-RESULTS-v1.json").write_text(json.dumps(result,indent=2)+"\n")
lines=["# r101 cross MODELLED result, 2026-10-27", "", result["status"]+".", "", "| Arm | CPU work estimate ms/draw | Validated world lower bound ms/draw | Raw partial world attribution ms/draw | Validated roots |", "|---|---:|---:|---:|---:|"]
for r in result["arms"]:
    lines.append(f"| {r['arm']} | {r['cpu_work_estimate_ms']:.3f} | {r['world_validated_lower_bound_ms']:.3f} | {r['world_raw_context_ms']:.3f} | {r['validated_roots']}/{r['observed_roots']} |")
lines += ["", result["denominator"], "", result["cpu_work_estimator"], "", result["world_attribution"], "", "## B1 disjoint contextual world costs", "", "These categories partition the partial contextual world self costs. They are function classifications, not instrumented phases; inlined pass work remains mixed.", "", "| Category | Validated lower bound ms/draw | Raw partial ms/draw |", "|---|---:|---:|"]
for r in result["arms"][1]["disjoint_world_categories"]:
    lines.append(f"| {r['category']} | {r['validated_lower_bound_ms']:.3f} | {r['raw_context_ms']:.3f} |")
lines += ['', 'B1 exclusive source rows give a second, disjoint view for source investigation: ps2_pass 0.810 ms; ScenerySelector::chunk_select 0.303 ms; world_out 0.271 ms; box_class 0.267 ms; sg_select_lean 0.071 ms; transforms 0.576 + 0.056 ms; clip_strip 0.199 ms; walk_lean 0.292 ms; chunk_emit 0.192 ms; direct_begin_batch 0.104 ms; dyn_source 0.119 ms. These rows overlap the contextual table above as an alternative attribution, so do not add the tables. Inlined pass work cannot be called fixed traversal without a further control. Full function names/files are in MODELLED-RESULTS-v1.json.']
lines += ["", "## Decision", "", result["decision"], "", "## Limits", ""]+["- "+s for s in result["limits"]]
lines += ["", "All three simulations have byte-identical frames/PCs/cache-lines/sum outputs against the contextual exporter and exact disjoint charge conservation. All guest runs completed in under 55 seconds. Full programme, input and emulator bindings are in MODELLED-MATCHED-INPUT-AUDIT.json. Per-arm directories retain logs, ELF, counts, traces, parity checks, draw entry counts, scene records and disjoint function rows. Owned staged ISO duplicates were hash-checked and deleted with manifests.", ""]
(root/"MODELLED-RESULTS-v1.md").write_text("\n".join(lines))
print(json.dumps([{k:r[k] for k in ('arm','cpu_work_estimate_ms','world_raw_context_ms','world_validated_lower_bound_ms','validated_roots','observed_roots')} for r in result["arms"]],indent=2))
