#!/usr/bin/env python3
"""Summarize measured target traces and an explicitly synthetic frame estimate.

The underlying fixture prices replay setup with a controlled geometry edge.
Data accesses are retired target loads/stores, not cache misses or bus traffic.
The frame projection assumes the requested piece count, replay batch occupancy,
one screen-memo call per piece, and a chosen memo hit fraction. It adds no new
selector saving: the base already avoids box/group selection when fully inside.
"""
import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract(row):
    traffic = row["traffic"]["cached"]
    return dict(warm_i_cycles=row["model_cycles"],
        cold_i_cycles=row["cold_icache"]["model_cycles"],
        instructions=row["instructions"],
        loads=traffic["load_instructions"], stores=traffic["store_instructions"],
        load_bytes=traffic["load_bytes"], store_bytes=traffic["store_bytes"],
        distinct_32b_lines=traffic["unique_data_lines"],
        distinct_read_32b_lines=traffic["unique_read_lines"],
        distinct_write_32b_lines=traffic["unique_write_lines"],
        segment_32b_line_touches=row.get("segment_data_line_touches"),
        pref_requests=row["traffic"]["prefetch"]["requests"],
        fixture_peak_stack_bytes=row["peak_stack_bytes"])


def summarize(args):
    evidence=json.loads(args.target_controls.read_text())
    assert evidence["status"]=="PASS"
    cases={(row["kind"], row["name"]):row for row in evidence["cases"]}
    complete,remainder=divmod(args.pieces,args.batch_size)
    occupancy=[args.batch_size]*complete+([remainder] if remainder else [])
    assert occupancy, "At least one drawn piece is required"
    per_run=[]
    screens=[]
    for (kind,name),case in cases.items():
        if kind=="replay" and name.startswith("shape0-"):
            parts=next(iter(case["arms"].values()))["parts"]
            arms={arm:extract(row) for arm,row in case["arms"].items()}
            if parts:
                for row in arms.values():
                    row["per_piece"]={key:row[key]/parts for key in (
                        "warm_i_cycles","cold_i_cycles","instructions","loads","stores",
                        "load_bytes","store_bytes","segment_32b_line_touches")}
            per_run.append(dict(parts=parts,arms=arms))
        elif kind=="screen":
            screens.append(dict(name=name,arms={arm:extract(row) for arm,row in case["arms"].items()}))
    runs={row["parts"]:row for row in per_run}
    screen={row["name"]:row for row in screens}
    assert all(count in runs for count in occupancy),"No trace for requested batch remainder"
    estimates=[]
    for batch in (0,1):
        arms={}
        for replay in (0,1):
            arm=f"r{replay}-b{batch}"
            totals={key:sum(runs[count]["arms"][arm][key] for count in occupancy)
                    for key in ("warm_i_cycles","loads","stores","load_bytes","store_bytes")}
            # This sum counts repeated line touches in each separate batch;
            # it is never a unique whole-frame working-set measurement.
            totals["sum_of_per_batch_distinct_lines"]=sum(
                runs[count]["arms"][arm]["distinct_32b_lines"] for count in occupancy)
            arms[arm]=totals
        off,on=arms[f"r0-b{batch}"],arms[f"r1-b{batch}"]
        replay_saving={key:off[key]-on[key] for key in off}
        scenarios=[]
        for hit_fraction in (0.0,0.5,1.0):
            memo_savings={}
            for key in ("warm_i_cycles","loads","stores","load_bytes","store_bytes"):
                memo_savings[key]=args.pieces*sum(weight*(
                    screen[kind]["arms"][f"r0-b{batch}"][key]-
                    screen[kind]["arms"][f"r1-b{batch}"][key])
                    for kind,weight in (("hit",hit_fraction),("miss",1-hit_fraction)))
            warm_saving=replay_saving["warm_i_cycles"]+memo_savings["warm_i_cycles"]
            milliseconds=warm_saving/(args.mhz*1000)
            scenarios.append(dict(memo_hit_fraction=hit_fraction,memo_savings=memo_savings,
                combined_warm_i_saving_cycles=warm_saving,
                combined_warm_i_saving_ms=milliseconds,
                assumed_baseline_frame_ms=args.frame_ms,
                projected_frame_ms=args.frame_ms-milliseconds,
                projected_fps=1000/(args.frame_ms-milliseconds)))
        estimates.append(dict(submit_batch=batch,replay_totals=arms,
            replay_savings=replay_saving,
            replay_warm_i_saving_ms=replay_saving["warm_i_cycles"]/(args.mhz*1000),
            scenarios=scenarios))
    return dict(status="PASS",scope=__doc__,
        target_controls_sha256=digest(args.target_controls),
        target_build_sha256=evidence["target_build_sha256"],
        controls=evidence["checks"],pieces=args.pieces,replay_batch_sizes=occupancy,
        assumed_mhz=args.mhz,per_run=per_run,screen=screens,frame_estimates=estimates,
        limitations=[
            "Perfect D-cache in both models; no SQ, DMA, interrupt or unrelated bus-contention cost. Cold I includes modeled instruction line-fill service.",
            "Warm I means ideal instruction residency; cold I begins with an empty 8 KB I-cache once per fixture run.",
            "Cold-I results are per-sequence sensitivity figures and are not added into a frame projection.",
            "Real geometry, matrix hardware transfer and UI submission work are excluded from these controlled traces.",
            "Loads/stores include stack, literals and helper library accesses; bytes are architectural accesses, not external transfers.",
            "Per-piece segment line touches apportion prologue/epilogue and count repeated lines between geometry edges.",
            "Distinct lines describe one batch address union; they must not be divided by occupancy and called per-piece working set.",
            "Production code and stack deltas come from the separate full translation-unit build receipt.",
            "Selector saving is zero; the experimental extra fast loop was rejected and the original selector retained.",
            "No measured hardware or Flycast speedup is claimed."])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-controls",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--pieces",type=int,default=500)
    parser.add_argument("--batch-size",type=int,default=48)
    parser.add_argument("--mhz",type=float,default=200)
    parser.add_argument("--frame-ms",type=float,default=49.3)
    args=parser.parse_args()
    assert args.pieces>0 and args.batch_size>0 and args.mhz>0 and args.frame_ms>0
    result=summarize(args)
    args.output.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(dict(status=result["status"],pieces=args.pieces,output=str(args.output))))


if __name__=="__main__":
    main()
