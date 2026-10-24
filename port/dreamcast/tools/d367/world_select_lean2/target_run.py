#!/usr/bin/env python3
"""Execute compiled selector controls and price their complete dynamic traces.

The complete MeshDraw/ScenerySelector setup and actual chunk_select/helper code
run on the retained scalar SH4 interpreter. No geometry or TA replay is run.
Warm/cold instruction-cache models assume perfect D-cache, no DMA/bus/SQ cost.
Observed architectural line touches are not cache misses or external traffic.
"""
import argparse
import bisect
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
from types import SimpleNamespace

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"world_replay_lean"))
import pipeline_cost
import target_machine
from memory_trace import summarize


def word(machine,address):return int.from_bytes(machine.bytes_at(address,4),"little")


class Machine(target_machine.Machine):
    def attach(self,symbols):
        self.helper_hooks={address:name for name,(address,size,info) in symbols.items()
            if any(x in name for x in ("9sg_selectE","14sg_select_leanE","7sg_pickE","12sg_pick_leanE"))
            and (info&15)==2}
        self.helper_entries=[]

    def step(self,pc,delay=False):
        if self.memory_tracking and pc in self.helper_hooks:
            self.helper_entries.append(dict(name=self.helper_hooks[pc],ordinal=len(self.instruction_pcs),
                groups=self.reg[5],mask=self.reg[7]))
        return super().step(pc,delay)


def load(path):
    program,symbols=target_machine.scalar.load_elf(path)
    machine=Machine()
    for address,data,_ in program:machine.map(address,data)
    layout=[word(machine,symbols["_fixture_layout"][0]+4*i) for i in range(22)]
    assert layout[:4]==[1,164,252,8],layout[:4]
    machine.attach(symbols)
    return machine,symbols,layout


def prepare(machine,symbols,layout,data,sg_mode):
    magic,input_size,package_size,group_size,cone_size=struct.unpack_from("<5I",data)
    assert magic==0x31505357 and input_size==layout[1]
    assert package_size<=layout[8] and group_size<=layout[10] and cone_size<=layout[12]
    offset=20
    for address,size in ((layout[6],input_size),(layout[7],package_size),(layout[9],group_size),(layout[11],cone_size)):
        machine.map(address,data[offset:offset+size]);offset+=size
    assert offset==len(data)
    machine.execute(symbols["_fixture_adopt"][0],package_size)
    assert machine.reg[0]==1,"production MeshPackage::adopt rejected fixture"
    machine.execute(symbols["_fixture_configure"][0])
    machine.execute(symbols["_fixture_sg_mode"][0],sg_mode)
    pkg=data[20+input_size:20+input_size+package_size]
    return dict(meshlets=(layout[7]+struct.unpack_from("<I",pkg,48)[0],
                         struct.unpack_from("<I",pkg,24)[0],28),
                clusters=(layout[7]+struct.unpack_from("<I",pkg,92)[0],
                         struct.unpack_from("<I",pkg,80)[0],20),
                groups=(layout[9],group_size,1))


def storage_traffic(machine,bounds):
    regions={name:(base,base+count*stride) for name,(base,count,stride) in bounds.items()}
    regions["stack"]=(machine.initial_regs[15]-65536,machine.initial_regs[15])
    buckets={name:[] for name in (*regions,"other")}
    for event in machine.memory_events:
        address,size=event[3:]
        matches=[name for name,(lo,hi) in regions.items() if lo<=address and address+size<=hi]
        assert len(matches)<=1,(address,size,matches)
        buckets[matches[0] if matches else "other"].append(event)
    return {name:summarize(events)["cached"] for name,events in buckets.items()}


def partitions(machine,bounds):
    """Partition by first demand read of each record; no trace instrumentation.

    Prefix entry and trailing exit stay charged. A line is counted again if
    adjacent meshlet/cluster intervals touch it; the full-run union is separate.
    Calls/branches/prefetches add no artificial measurement instructions.
    """
    base,count,stride=bounds;seen={}
    for ordinal,pc,kind,address,size in machine.memory_events:
        if kind=="read" and base<=address<base+count*stride:
            index=(address-base)//stride
            if index not in seen:seen[index]=ordinal
    cuts=sorted(set((0,*seen.values(),len(machine.instruction_pcs))))
    events=[[] for _ in range(len(cuts)-1)];prefetches=[[] for _ in events]
    for event in machine.memory_events:events[bisect.bisect_right(cuts,event[0])-1].append(event)
    for event in machine.prefetch_events:prefetches[bisect.bisect_right(cuts,event[0])-1].append(event)
    rows=[]
    for index,(begin,end) in enumerate(zip(cuts,cuts[1:])):
        traffic=summarize(events[index],prefetches[index])
        rows.append(dict(begin=begin,end=end,traffic=traffic))
    return dict(first_record_reads={str(k):v for k,v in seen.items()},intervals=len(rows),
        repeated_line_touches=sum(r["traffic"]["cached"]["unique_data_lines"] for r in rows),
        scope="Sum of per-interval unique32B unions split at first demand read of each record; includes entry/exit, not cache misses")


def selection(machine,symbols,layout,kind,bounds):
    machine.execute(symbols["_fixture_reset"][0])
    machine.minimum_sp=machine.reg[15]
    machine.helper_entries=[]
    machine.observe_start()
    machine.execute(symbols["_fixture_select_"+kind][0])
    traffic=machine.observe_stop()
    pcs=list(machine.instruction_pcs)
    trace=SimpleNamespace(instruction_pcs=pcs,steps=len(pcs),read=machine.read)
    count=machine.reg[0];eligible=word(machine,layout[15]+4)
    assert count<=320
    raw=machine.bytes_at(layout[13],layout[14]);picks=[]
    for i in range(count):
        let,nr,mask,lo,hi=struct.unpack_from("<H4B",raw,i*8)
        picks.append([let,nr,0 if nr==255 else mask,0 if nr==255 else lo,0 if nr==255 else hi])
    # The production selector can initialize the next Pick before rejecting it
    # through a cone. Compare that unused storage byte-for-byte below too;
    # requiring the whole tail to stay poison would reject the unchanged base.
    row=dict(count=count,eligible=eligible,picks=picks,instructions=machine.steps,
        raw_pick_bytes=len(raw),raw_picks_sha256=hashlib.sha256(raw).hexdigest(),
        traffic=traffic,peak_stack_bytes=machine.initial_regs[15]-machine.minimum_sp,
        symbol_instructions=pipeline_cost.symbol_costs(trace,symbols),
        helper_entries=list(machine.helper_entries),
        storage_traffic=storage_traffic(machine,bounds),
        meshlet_intervals=partitions(machine,bounds["meshlets"]),
        cluster_intervals=partitions(machine,bounds["clusters"]))
    machine.reg[5]=eligible
    machine.execute(symbols["_fixture_snapshot"][0],count)
    result=machine.bytes_at(layout[15],layout[2])
    row.update(statistics=list(struct.unpack("<63I",result)),result_sha256=hashlib.sha256(result).hexdigest())
    return row,trace,(picks,result,raw)


def price(model,name,trace):
    row=model.price(name,trace)
    output=model.output/(name+"-cold-icache")
    command=[str(model.binary),"--elf",str(model.view),"--out",str(output),
             "--perfect-dc","--no-dma","--sq-cost","0",str(model.output/(name+".bin"))]
    result=subprocess.run(command,capture_output=True,text=True)
    output.with_suffix(".log").write_text(result.stdout+result.stderr)
    assert result.returncode==0,result.stderr
    totals=dict(line.split() for line in output.with_suffix(".sum.txt").read_text().splitlines())
    assert int(totals["insns"])==trace.steps
    for key in ("dfills_per_frame","writebacks_per_frame","dma_bytes_per_frame","dma_starts_per_frame"):
        assert float(totals[key])==0
    row["cold_icache"]=dict(model_cycles=int(totals["cycles"]),
        instruction_fills=float(totals["ifills_per_frame"]),
        scope="Initially empty8KB I-cache once per complete part sequence; synthetic ELF layout",command=command)
    return row


def run(args):
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=False)
    observed_sources=[Path(__file__),HERE.parent/"world_replay_lean/target_machine.py",
        HERE.parent/"world_replay_lean/sh4_machine.py",HERE.parent/"world_replay_lean/memory_trace.py",
        HERE.parent/"world_replay_lean/pipeline_cost.py"]
    input_hashes={str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in observed_sources}
    build=json.loads(args.build.read_text())
    cases_path=Path(build["cases"]);cases=json.loads(cases_path.read_text())
    if args.case:cases=[c for c in cases if c["name"] in args.case]
    if args.quick:cases=[c for c in cases if c.get("cost") and c["clusters"]==1
        and c["meshlets_per_cluster"] in (1,8) and c["family"] in ("partial-groups","box-inside","box-outside")]
    assert cases,"no cases selected"
    paths={name:Path(row["elf"]) for name,row in build["arms"].items()}
    models={}
    for name,path in paths.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest()==build["arms"][name]["sha256"]
        if not args.no_model:models[name]=pipeline_cost.Model(output/("model-"+name),path,args.host_cc)
    rows=[dict(name=case["name"],metadata={k:v for k,v in case.items() if k not in ("sha256","file","config")},arms={}) for case in cases]
    semantics=[{} for _ in cases];comparisons=0
    for arm,path in paths.items():
        machine,symbols,layout=load(path)
        for index,case in enumerate(cases):
            data=(cases_path.parent/case["file"]).read_bytes()
            assert hashlib.sha256(data).hexdigest()==case["sha256"]
            for sg_mode in (args.sg_mode or (0,1)):
                bounds=prepare(machine,symbols,layout,data,sg_mode)
                for kind in (args.context or ("full","light")):
                    key=arm+f"-sg{sg_mode}-"+kind
                    row,trace,semantic=selection(machine,symbols,layout,kind,bounds)
                    if case["expected"] is not None:assert row["picks"]==case["expected"],(case["name"],key,"known selection differs")
                    if case.get("cost"):
                        expected_visited=case.get("expected_visited_meshlets",case["selected_level_meshlets"])
                        assert len(row["meshlet_intervals"]["first_record_reads"])==expected_visited,(key,case["name"],row["meshlet_intervals"])
                        assert len(row["cluster_intervals"]["first_record_reads"])==case["clusters"]
                    if arm in models and case.get("cost"):
                        row["pipeline"]=price(models[arm],case["name"]+f"-sg{sg_mode}-"+kind,trace)
                        n=case["selected_level_meshlets"];c=case["clusters"]
                        row["amortized"]=dict(meshlets=n,clusters=c,
                            warm_cycles_per_meshlet=row["pipeline"]["model_cycles"]/n,
                            cold_i_cycles_per_meshlet=row["pipeline"]["cold_icache"]["model_cycles"]/n,
                            warm_cycles_per_cluster=row["pipeline"]["model_cycles"]/c,
                            cold_i_cycles_per_cluster=row["pipeline"]["cold_icache"]["model_cycles"]/c,
                            scope="Whole measured part sequence divided by selected-level counts; includes all constructor/cluster/first-use/exit cost")
                    rows[index]["arms"][key]=row;semantics[index][key]=semantic
            print(json.dumps(dict(case=case["name"],arm=arm,status="EXECUTED")),flush=True)
    for case,semantic in zip(cases,semantics):
        for key,before in semantic.items():
            if "-q0-" in key:
                after=semantic[key.replace("-q0-","-q1-")]
                assert before==after,(case["name"],key,"target selection/statistics differ")
                comparisons+=1
    report=dict(status="PASS",scope=__doc__,build=str(args.build.resolve()),
        build_sha256=hashlib.sha256(args.build.read_bytes()).hexdigest(),
        runner_source_sha256=input_hashes,
        memory_controls=target_machine.memory_controls(),paired_comparisons=comparisons,
        models={name:model.metadata() for name,model in models.items()},cases=rows)
    for path,digest in input_hashes.items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,(path,"changed during target execution")
    for name,path in paths.items():assert hashlib.sha256(path.read_bytes()).hexdigest()==build["arms"][name]["sha256"],(name,"ELF changed during target execution")
    (output/"target-controls.json").write_text(json.dumps(report,indent=2)+"\n")
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--build",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--host-cc",default="gcc")
    p.add_argument("--no-model",action="store_true")
    p.add_argument("--quick",action="store_true")
    p.add_argument("--case",action="append",default=[])
    p.add_argument("--sg-mode",action="append",type=int,choices=(0,1),default=[])
    p.add_argument("--context",action="append",choices=("full","light"),default=[])
    result=run(p.parse_args())
    print(json.dumps(dict(status=result["status"],paired_comparisons=result["paired_comparisons"])))


if __name__=="__main__":main()
