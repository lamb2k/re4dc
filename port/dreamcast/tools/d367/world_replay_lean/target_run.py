#!/usr/bin/env python3
"""Execute actual SH4 replay setup, selector and matrix-memo code with traffic.

The replay geometry edge observes active inputs and writes representative bound
state; its geometry/TA work is excluded. Screen-matrix loads capture all 64 bytes
but exclude the unchanged hardware transfer. The pipeline model assumes perfect
D-cache, no bus/SQ/IRQ/DMA events. Cache-line touches are observed address sets,
never measured cache misses. This is no recorded game frame or hardware result.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
from types import SimpleNamespace

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
import pipeline_cost
import target_machine
from memory_trace import summarize
from target_machine import Machine


FIELDS=("mvq","used","input","output","slots","sq","bound","submitted","cache","primed",
        "palette","ps2","vertex_alpha","c4444","alpha","streaming","direct","lean_part",
        "uv_bias","uv_scale","proj_bx","proj_by","clip","clip_bytes","part_index",
        "material","material_cull","material_uv","near","far")


class FixtureMachine(Machine):
    def attach(self,symbols,layout):
        self.symbols=symbols;self.layout=layout
        self.fields=dict(zip(FIELDS,layout[6:]))
        self.edge_records=[];self.result_records=[];self.end_records=[];self.matrix_records=[]
        self.streaming_calls=0;self.emit_instruction_boundaries=[]
        self.hooks={symbols["_"+name][0]:name for name in (
            "fixture_emit_control","re4dc_model_result","re4dc_model_direct_end",
            "re4dc_ps2_world_direct_end_batch","re4dc_model_packet_streaming","mat_load")
            if "_"+name in symbols}

    def word(self,address,size=4):
        return int.from_bytes(self.bytes_at(address,size),"little")

    def putword(self,address,value,size=4):
        self.map(address,int(value).to_bytes(size,"little"))

    def observe_geometry(self):
        at,pick=self.reg[4:6];f=self.fields
        def word(name,size=4):return self.word(at+f[name],size)
        zero={name:word(name,1 if name in ("bound","submitted") else 4)
              for name in ("used","input","output","slots","bound","submitted","cache","primed")}
        assert all(value==0 for value in zero.values()),("logical state not reset",zero)
        assert word("palette")==0
        clip=self.bytes_at(at+f["clip"],f["clip_bytes"])
        assert len(clip)==24 and self.word(at+f["clip"]+20)==at,"clip context must name this emitter"
        material=f["material"]
        row=dict(matrix=self.bytes_at(at+f["mvq"],48).hex(),
            key=self.bytes_at(word("ps2"),24).hex(),pick=self.bytes_at(pick,6).hex(),
            cull=self.word(material+f["material_cull"]),
            uv_offset=self.bytes_at(material+f["material_uv"],8).hex(),
            uv_bias=self.bytes_at(at+f["uv_bias"],8).hex(),uv_scale=self.bytes_at(at+f["uv_scale"],8).hex(),
            clip=clip[:16].hex(),projection_offsets=self.bytes_at(at+f["proj_bx"],8).hex(),
            near=word("near"),far=word("far"),part_index=word("part_index"),alpha=word("alpha"),
            vertex_alpha=word("vertex_alpha",1),c4444=word("c4444",1),
            streaming=word("streaming",1),direct=word("direct",1),lean_part=word("lean_part",1))
        assert row["alpha"]==0xff000000 and row["streaming"]==row["direct"]==row["lean_part"]==1
        self.edge_records.append(row)
        self.emit_instruction_boundaries.append(len(self.instruction_pcs))
        # Representative values written by the unchanged successful direct
        # emission path. Do not poison invariants that geometry never changes.
        for name,value in (("input",7),("output",7),("slots",7),("sq",0xe00000e0),
                           ("cache",0x12345678),("primed",113)):
            self.putword(at+f[name],value)
        for name in ("bound","submitted"):
            self.putword(at+f[name],1,1)

    def step(self,pc,delay=False):
        hook=self.hooks.get(pc) if hasattr(self,"hooks") else None
        if hook=="fixture_emit_control":self.observe_geometry()
        elif hook=="re4dc_model_result":self.result_records.append(self.reg[4:7])
        elif hook in ("re4dc_model_direct_end","re4dc_ps2_world_direct_end_batch"):
            self.end_records.append(self.reg[4])
        elif hook=="re4dc_model_packet_streaming":self.streaming_calls+=1
        elif hook=="mat_load":self.matrix_records.append(self.bytes_at(self.reg[4],64).hex())
        return super().step(pc,delay)


def load(path):
    program,symbols=target_machine.scalar.load_elf(path)
    machine=FixtureMachine()
    for address,data,_ in program:machine.map(address,data)
    layout=[machine.word(symbols["_fixture_layout"][0]+4*i) for i in range(22)]
    replay=[machine.word(symbols["_fixture_replay_layout"][0]+4*i) for i in range(36)]
    assert layout[:4]==[1,164,252,8] and replay[0]==1
    machine.attach(symbols,replay)
    return machine,symbols,layout


def prepare(machine,symbols,layout,data):
    magic,input_size,package_size,group_size,cone_size=struct.unpack_from("<5I",data)
    assert magic==0x31505357 and input_size==layout[1]
    assert package_size<=layout[8] and group_size<=layout[10] and cone_size<=layout[12]
    offset=20
    for address,size in ((layout[6],input_size),(layout[7],package_size),(layout[9],group_size),(layout[11],cone_size)):
        machine.map(address,data[offset:offset+size]);offset+=size
    assert offset==len(data)
    machine.execute(symbols["_fixture_adopt"][0],package_size)
    assert machine.reg[0]==1
    machine.execute(symbols["_fixture_configure"][0])
    machine.execute(symbols["_fixture_reset"][0])


def timed(machine,symbols,entry,argument=0x9000):
    machine.minimum_sp=machine.reg[15]
    machine.observe_start()
    machine.execute(symbols["_"+entry][0],argument)
    traffic=machine.observe_stop()
    pcs=list(machine.instruction_pcs)
    report=dict(instructions=machine.steps,traffic=traffic,
                peak_stack_bytes=machine.initial_regs[15]-machine.minimum_sp)
    trace=SimpleNamespace(instruction_pcs=pcs,steps=len(pcs),read=machine.read)
    report["symbol_instructions"]=pipeline_cost.symbol_costs(trace,symbols)
    return report,trace


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
    row["cold_icache"]=dict(model_cycles=int(totals["cycles"]),instruction_fills=float(totals["ifills_per_frame"]),
        scope="Initially cold 8KB I-cache, once per complete sequence; synthetic ELF layout",command=command)
    return row


def selection(machine,symbols,layout,kind):
    machine.execute(symbols["_fixture_reset"][0])
    row,trace=timed(machine,symbols,"fixture_select_"+kind)
    count=machine.reg[0];eligible=machine.word(layout[15]+4)
    raw=machine.bytes_at(layout[13],layout[14]);picks=[]
    for i in range(count):
        let,nr,mask,lo,hi=struct.unpack_from("<H4B",raw,i*8)
        picks.append([let,nr,0 if nr==255 else mask,0 if nr==255 else lo,0 if nr==255 else hi])
    machine.reg[5]=eligible
    machine.execute(symbols["_fixture_snapshot"][0],count)
    result=machine.bytes_at(layout[15],layout[2])
    row.update(count=count,eligible=eligible,picks=picks,
        statistics=list(struct.unpack("<63I",result)),result_sha256=hashlib.sha256(result).hexdigest())
    return row,trace,(picks,result,raw[count*8:])


def replay(machine,symbols,parts,shape):
    machine.putword(machine.layout[4],shape)
    machine.execute(symbols["_fixture_prepare_replay"][0],parts)
    machine.edge_records=[];machine.result_records=[];machine.end_records=[];machine.streaming_calls=0
    machine.emit_instruction_boundaries=[]
    row,trace=timed(machine,symbols,"fixture_replay")
    result=list(struct.unpack("<8I",machine.bytes_at(machine.layout[5],32)))
    expected=0 if shape==1 else parts-sum(j%3==1 for j in range(parts)) if shape==2 else parts
    assert len(machine.edge_records)==len(machine.end_records)==expected
    assert len(machine.result_records)==parts
    assert result[:6]==[1,parts,0,0,0,0],result
    assert all(value==7 for value in machine.end_records)
    assert sum(x[1] for x in machine.result_records)==sum(x[2] for x in machine.result_records)==7*expected
    boundaries=[0,*machine.emit_instruction_boundaries,len(trace.instruction_pcs)]
    per_segment=[]
    for start,end in zip(boundaries,boundaries[1:]):
        per_segment.append(summarize([e for e in machine.memory_events if start<=e[0]<end],
                                    [e for e in machine.prefetch_events if start<=e[0]<end]))
    row.update(parts=parts,shape=shape,drawn_parts=expected,streaming_calls=machine.streaming_calls,
        state=result,edge_records=machine.edge_records,result_records=machine.result_records,
        segment_data_line_touches=sum(x["cached"]["unique_data_lines"] for x in per_segment),
        segment_definition="Before first geometry edge, between geometry edges, and trailing exit; unique union is reported separately")
    semantic=(result,machine.edge_records,machine.result_records,machine.end_records)
    return row,trace,semantic


def screen(machine,symbols,kind):
    # Miss and hit start from an independently prepared matrix state; all
    # arithmetic results from the actual load_screen body are captured.
    if kind=="hit":machine.execute(symbols["_fixture_screen"][0])
    machine.matrix_records=[]
    row,trace=timed(machine,symbols,"fixture_screen")
    assert len(machine.matrix_records)==1
    row["matrix"]=machine.matrix_records[0]
    return row,trace,row["matrix"]


def run(args):
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=False)
    build=json.loads(args.build.read_text())
    cases_path=Path(build["cases"]);cases=json.loads(cases_path.read_text())
    paths={name:Path(row["elf"]) for name,row in build["arms"].items()}
    models={}
    for name,path in paths.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest()==build["arms"][name]["sha256"]
        if not args.no_model:models[name]=pipeline_cost.Model(output/("model-"+name),path,args.host_cc)
    cost_names={"whole-inside","whole-tested","partial-groups","many-meshlets","scalar-box-fallback","marked-uv-cull-1"}
    selected_cases=cases if not args.quick else [x for x in cases if x["name"] in cost_names]
    rows=[]
    for case in selected_cases:
        data=(cases_path.parent/case["file"]).read_bytes()
        assert hashlib.sha256(data).hexdigest()==case["sha256"]
        collected={};semantics={}
        for arm,path in paths.items():
            # Batching does not change selector code: both selector contexts
            # are measured in B0; B1 is still checked for exact output.
            machine,symbols,layout=load(path);prepare(machine,symbols,layout,data)
            for kind in ("full","light"):
                row,trace,semantic=selection(machine,symbols,layout,kind)
                if arm in models and arm.endswith("b0") and case["name"] in cost_names:
                    row.update(price(models[arm],"select-"+case["name"]+"-"+kind,trace))
                if case["expected"] is not None:assert row["picks"]==case["expected"]
                collected[arm+"-"+kind]=row;semantics[arm+"-"+kind]=semantic
        first=next(iter(semantics.values()))
        assert all(x==first for x in semantics.values()),(case["name"],"selector output")
        rows.append(dict(kind="selection",name=case["name"],arms=collected))
        print("PASS selection",case["name"],flush=True)
        (output/"progress.json").write_text(json.dumps(rows,indent=2)+"\n")
    case=next(x for x in cases if x["name"]=="whole-inside")
    data=(cases_path.parent/case["file"]).read_bytes()
    for shape in (0,1,2):
        for parts in (0,1,2,8,20,48):
            collected={};semantics={}
            for arm,path in paths.items():
                machine,symbols,layout=load(path);prepare(machine,symbols,layout,data)
                row,trace,semantic=replay(machine,symbols,parts,shape)
                if arm in models and shape==0:row.update(price(models[arm],f"replay-{parts}",trace))
                collected[arm]=row;semantics[arm]=semantic
            first=next(iter(semantics.values()))
            assert all(x==first for x in semantics.values()),("replay",parts,shape,"state/input output")
            rows.append(dict(kind="replay",name=f"shape{shape}-parts{parts}",arms=collected))
            print("PASS replay",parts,shape,flush=True)
            (output/"progress.json").write_text(json.dumps(rows,indent=2)+"\n")
    for kind in ("miss","hit"):
        collected={};semantics={}
        for arm,path in paths.items():
            machine,symbols,layout=load(path);prepare(machine,symbols,layout,data)
            row,trace,semantic=screen(machine,symbols,kind)
            if arm in models:row.update(price(models[arm],"screen-"+kind,trace))
            collected[arm]=row;semantics[arm]=semantic
        first=next(iter(semantics.values()))
        assert all(x==first for x in semantics.values()),("screen",kind,"matrix output")
        rows.append(dict(kind="screen",name=kind,arms=collected))
        print("PASS screen",kind,flush=True)
    report=dict(status="PASS",scope=__doc__,checks=len(rows),cases=rows,
        target_build_sha256=hashlib.sha256(args.build.read_bytes()).hexdigest(),
        memory_controls=target_machine.memory_controls(),
        model={name:model.metadata() for name,model in models.items()},
        source_sha256={str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in (
            Path(__file__),Path(target_machine.__file__),Path(target_machine.scalar.__file__),HERE/"memory_trace.py",Path(pipeline_cost.__file__))})
    (output/"target-controls.json").write_text(json.dumps(report,indent=2)+"\n")
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--build",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--host-cc",default="gcc")
    p.add_argument("--quick",action="store_true")
    p.add_argument("--no-model",action="store_true")
    result=run(p.parse_args());print(json.dumps(dict(status=result["status"],checks=result["checks"])))


if __name__=="__main__":main()
