#!/usr/bin/env python3
"""Create portable Build 5 cost evidence and an explicit frame sensitivity.

The population is assumed: 500 one-pick pieces, 96 vertices each, replayed in
15 queues of 32 and one queue of 20. It is not an observed r101 census. Actual
compiled replay/lookahead code is priced on matching synthetic packages and
added to separately priced production gather entries. Leaf-wrapper integration
and cache-residency effects are not modelled. No D-cache gain is credited.
"""
import argparse
import json
from pathlib import Path
import struct
import sys

sys.dont_write_bytecode=True
import target_cost as cost


def scenario_data(indexed,count):
    let=cost.selection_cases.meshlet([[(i*300+k*2,100+(k&1)*5,100) for k in range(24)] for i in range(4)])
    pkg,groups,cones=cost.selection_cases.package([[[(0.,[let]*count)]]],indexed=indexed)
    if indexed:
        pkg=bytearray(pkg)
        lets=struct.unpack_from("<I",pkg,48)[0];strips=struct.unpack_from("<I",pkg,56)[0]
        for i in range(count):
            first=struct.unpack_from("<I",pkg,lets+28*i+4)[0]
            struct.pack_into("<96H",pkg,strips+first,*reversed(range(96)))
        pkg=bytes(pkg)
    config=cost.selection_cases.defaults();config["inside"]=1
    inp=cost.selection_cases.input_bytes(config)
    return struct.pack("<5I",0x31505357,len(inp),len(pkg),len(groups),len(cones))+inp+pkg+groups+cones


def compact(row):
    def cached(value):
        names=("load_instructions","store_instructions","load_bytes","store_bytes",
               "unique_read_lines","unique_write_lines","unique_data_lines")
        return {key:value[key] for key in names}
    def prefetch(value):
        return {key:value[key] for key in ("requests","unique_requested_lines","sq_flush_requests")}
    def regions(values):
        result={}
        for name,value in values.items():
            if "cached" in value:
                c=value["cached"];p=value["prefetch"]
                result[name]=dict(loads=c["load_instructions"],stores=c["store_instructions"],
                    read_bytes=c["load_bytes"],written_bytes=c["store_bytes"],lines32=c["unique_data_lines"],
                    prefetch_requests=p["requests"],prefetch_lines32=p["unique_requested_lines"])
            else:result[name]=value
        return {name:value for name,value in result.items() if any(value.values())}
    warm=row["pipeline"]["model_cycles"] if "pipeline" in row else row["warm_cycles"]
    cold=row["pipeline"]["cold_icache"]["model_cycles"] if "pipeline" in row else row["cold_i_cycles"]
    return dict(warm_cycles=warm,cold_i_cycles=cold,
        instructions=row["instructions"],traffic=dict(cached=cached(row["traffic"]["cached"]),
            prefetch=prefetch(row["traffic"]["prefetch"])),
        peak_stack_bytes=row["peak_stack_bytes"],
        storage_traffic=regions(row.get("storage_traffic",{})),
        **({"segment_data_line_touches":row["segment_data_line_touches"]}
           if "segment_data_line_touches" in row else {}))


def project(args):
    output=args.work.resolve();output.mkdir(parents=True,exist_ok=False)
    build=json.loads(args.build.read_text());raw=json.loads(args.costs.read_text())
    assert raw["build_sha256"]==cost.profile.sha(args.build)
    paths={arm:Path(value["elf"]) for arm,value in build["arms"].items()}
    machines={arm:cost.load(path) for arm,path in paths.items()}
    target_layouts={arm:machine.layout[:3] for arm,(machine,_,_) in machines.items()}
    assert target_layouts["q0"]==target_layouts["q1"]
    models={arm:cost.pipeline_cost.Model(output/("model-"+arm),path,args.host_cc) for arm,path in paths.items()}
    configurations=[(False,32,None),(False,20,None),(True,32,None),(True,20,None)]
    configurations += [(True,32,phase) for phase in (0,2,4,6,8)]+[(True,20,0)]
    replay_rows=[];lookup={}
    for indexed,parts,phase in configurations:
        name=f"{'indexed' if indexed else 'plain'}-parts{parts}-zero{phase if phase is not None else 'none'}"
        data=scenario_data(indexed,parts)
        (output/(name+".fixture")).write_bytes(data)
        arms={};semantics={}
        zeros=sum((phase+i)%10==0 for i in range(parts)) if phase is not None else 0
        for arm,path in paths.items():
            assert cost.profile.sha(path)==build["arms"][arm]["sha256"]
            machine,symbols,layout=machines[arm]
            cost.old_run.prepare(machine,symbols,layout,data)
            machine.putword(symbols["_fixture_picks_per_part"][0],1)
            machine.putword(symbols["_fixture_replay_partial"][0],0)
            machine.execute(symbols["_fixture_prepare_replay"][0],parts)
            gathered=[machine.word(symbols["_fixture_gather_layout"][0]+4*i) for i in range(4)]
            for i in range(parts):
                nr=0 if phase is not None and (phase+i)%10==0 else 255
                machine.map(gathered[2]+8*i,struct.pack("<H4B",parts-1-i,nr,0,0,0))
            machine.edge_records=[];machine.result_records=[];machine.end_records=[]
            machine.emit_instruction_boundaries=[];machine.streaming_calls=0
            row,trace=cost.old_run.timed(machine,symbols,"fixture_replay")
            row["pipeline"]=cost.old_run.price(models[arm],name,trace)
            row["storage_traffic"]=cost.storage_traffic(machine,layout,gathered)
            boundaries=[0,*machine.emit_instruction_boundaries,len(trace.instruction_pcs)]
            row["segment_data_line_touches"]=sum(cost.summarize(
                [e for e in machine.memory_events if start<=e[0]<end])["cached"]["unique_data_lines"]
                for start,end in zip(boundaries,boundaries[1:]))
            result=list(struct.unpack("<8I",machine.bytes_at(machine.layout[5],32)))
            assert result[:6]==[1,parts,0,0,0,0]
            assert len(machine.edge_records)==parts
            semantics[arm]=(result,machine.edge_records,machine.result_records,machine.end_records)
            arms[arm]=compact(row)
        assert semantics["q0"]==semantics["q1"]
        record=dict(name=name,indexed=indexed,parts=parts,zero_phase=phase,zero_picks=zeros,arms=arms)
        replay_rows.append(record);lookup[(indexed,parts,phase)]=record
        print(json.dumps(dict(name=name,status="PASS")),flush=True)
    gathers={r["name"]:r for r in raw["gather_rows"]}
    scenarios=[]
    for kind,indexed,empty in (("all plain",False,0),("all indexed",True,0),("indexed with every tenth pick empty",True,50)):
        components=[]
        if not empty:components=[(15,lookup[(indexed,32,None)]),(1,lookup[(indexed,20,None)])]
        else:components=[(3,lookup[(True,32,p)]) for p in (0,2,4,6,8)]+[(1,lookup[(True,20,0)])]
        totals={}
        full=gathers[f"gather-{'indexed' if indexed else 'plain'}-partial0"]
        zero=gathers[f"gather-{'indexed' if indexed else 'plain'}-partial2"]
        for arm in ("q0","q1"):
            replay=sum(n*r["arms"][arm]["warm_cycles"] for n,r in components)
            gather=(500-empty)*full["arms"][arm]["pipeline"]["model_cycles"]+empty*zero["arms"][arm]["pipeline"]["model_cycles"]
            totals[arm]=dict(replay_cycles=replay,gather_cycles=gather,component_cycles=replay+gather)
        delta=totals["q1"]["component_cycles"]-totals["q0"]["component_cycles"]
        scenarios.append(dict(name=kind,pieces=500,vertices_per_meshlet=96,indexed=indexed,empty_picks=empty,
            queues="15 x 32 + 1 x 20",arms=totals,replay_delta_cycles=totals["q1"]["replay_cycles"]-totals["q0"]["replay_cycles"],
            gather_delta_cycles=totals["q1"]["gather_cycles"]-totals["q0"]["gather_cycles"],delta_cycles=delta,
            delta_ms_at_200mhz=delta/200000,reference_frame_ms=47.8,modelled_frame_ms=47.8+delta/200000,
            label="MODELLED component sensitivity, not an r101 whole-frame measurement"))
    summary=dict(status="PASS",base=build["base"],scope=__doc__,
        receipts=dict(build_sha256=cost.profile.sha(args.build),raw_costs_sha256=cost.profile.sha(args.costs),
            prefetch_sha256=cost.profile.sha(args.prefetch),projection_source_sha256=cost.profile.sha(Path(__file__))),
        build_input_sha256=build["source_sha256"],
        target_elf_sha256={a:r["sha256"] for a,r in build["arms"].items()},
        target_layout=dict(MeshDraw_bytes=target_layouts["q0"][1],ChunkPart_bytes=target_layouts["q0"][2],
            scope="Both arms with all five prior knobs enabled"),
        models={arm:model.metadata() for arm,model in models.items()},
        prefetch_assertions=json.loads(args.prefetch.read_text()),
        gather=[dict(name=r["name"],selected_vertices=96 if r["partial"]==0 else 24 if r["partial"]==1 else 0,
            compared_gather_vertices=96 if r["partial"]!=2 else 0,
            arms={a:compact(v) for a,v in r["arms"].items()}) for r in raw["gather_rows"]],
        passed_checks=dict(replay_12_vertex=len(raw["rows"]),gather=len(raw["gather_rows"]),replay_96_vertex=len(replay_rows)),
        replay_12_vertex=[dict(name=r["name"],parts=r["parts"],picks_per_part=r["picks_per_part"],
            arms={a:compact(v) for a,v in r["arms"].items()}) for r in raw["rows"]
            if r["partial"]==0 and ((r["parts"]==32 and r["picks_per_part"] in (1,8))
                or (r["parts"]==1 and r["picks_per_part"]==1))],
        replay_96_vertex=replay_rows,modelled_frame_sensitivities=scenarios,
        receipt_notes=["Original raw receipt selected_vertices labels for partial gathers described the compared full gather span. Portable selected_vertices is corrected to24; compared_gather_vertices stays96. Instructions, memory events and output checks are unchanged."],
        limitations=["Leaf gather wrapper deltas are added to replay geometry-edge deltas, not measured inside a complete production emitter.",
            "The 500 pieces, vertex count, indexed proportion and empty rate are explicit assumptions, not an r101 census.",
            "Whole-frame sensitivity uses warm-I perfect-D-cache components at 200MHz; cold-I figures are per independent queue or gather invocation.",
            "PREF requests and architectural line touches are not cache misses or guaranteed bus transfers.",
            "Geometry, bind internals, FTRV/FSRRA, clipper, TA and hardware gameplay acceptance remain outside this target interpreter."])
    # Portable evidence: retain command/source hashes, not machine-local output paths.
    for model in summary["models"].values():
        model["source"]="port/dreamcast/tools/hwmodel/hwsim.c";model.pop("compile_command",None)
    summary["prefetch_assertions"].pop("build",None)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(summary,indent=2)+"\n")
    return summary


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build",type=Path,required=True)
    parser.add_argument("--costs",type=Path,required=True)
    parser.add_argument("--prefetch",type=Path,required=True)
    parser.add_argument("--work",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--host-cc",default="gcc")
    args=parser.parse_args();result=project(args)
    print(json.dumps(dict(status=result["status"],scenarios=result["modelled_frame_sensitivities"])))
