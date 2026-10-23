#!/usr/bin/env python3
"""Validate actual SH4 PREF addresses against independent package records.

This reuses the compiled replay/lookahead fixture. Geometry is an observed edge,
not rendered here. Assertions cover selected record IDs, indexed first offsets,
partial plain starts, straddled hot headers, zero-group payload suppression,
cross-part hints, lead ordering and in-allocation hint addresses.
"""
import argparse
import collections
import json
from pathlib import Path
import struct
import sys

sys.dont_write_bytecode=True
import target_cost as cost


def check(args):
    build=json.loads(args.build.read_text())
    arm=build["arms"]["q1"]
    path=Path(arm["elf"])
    assert cost.profile.sha(path)==arm["sha256"]
    machine,symbols,layout=cost.load(path)
    rows=[]
    for indexed in (False,True):
        for partial in (0,1,2):
            for parts,picks in ((1,1),(1,8),(8,1),(3,4)):
                data=cost.case_data(indexed)
                cost.old_run.prepare(machine,symbols,layout,data)
                machine.putword(symbols["_fixture_picks_per_part"][0],picks)
                machine.putword(symbols["_fixture_replay_partial"][0],partial)
                machine.execute(symbols["_fixture_prepare_replay"][0],parts)
                gathered=[machine.word(symbols["_fixture_gather_layout"][0]+4*i) for i in range(4)]
                pkbase=gathered[2];base=layout[7]
                lets=base+machine.word(base+48);verts=base+machine.word(base+52);strips=base+machine.word(base+56)
                pkg_end=base+machine.word(base+8)
                sg_begin,sg_end=layout[9],layout[9]+layout[10]
                expected=[];expected_leads={};straddled=0
                def span(address,count):
                    return [address]+([address+count-1] if (address&31)+count>32 else [])
                for i in range(1,parts*picks):
                    let,nr,mask,lo,hi=struct.unpack("<H4B",machine.bytes_at(pkbase+8*i,6))
                    header=lets+28*let
                    head_hints=span(header,16)
                    straddled+=len(head_hints)==2
                    expected.extend(head_hints)
                    for address in head_hints:expected_leads[address]=i
                    first_vertex,first_strip,strip_bytes,vertex_count,strip_count=struct.unpack("<3I2H",machine.bytes_at(header,16))
                    if not nr:continue
                    raw=strips+first_strip
                    start=verts+12*first_vertex
                    if strip_count&0x8000:
                        offset=machine.word(raw,2)
                        assert offset!=0,"fixture must distinguish actual first reference from pool base"
                        payload=[raw,*span(start+12*offset,12)]
                        raw+=2*vertex_count
                    else:
                        first=0 if nr==255 else lo
                        count=vertex_count if nr==255 else hi-lo+1
                        payload=span(start+12*first,12*min(3,count))
                    payload.append(raw if nr==255 else sg_begin+16*4*let)
                    expected.extend(payload)
                    for address in payload:expected_leads[address]=i
                machine.edge_records=[];machine.result_records=[];machine.end_records=[]
                machine.emit_instruction_boundaries=[];machine.streaming_calls=0
                row,trace=cost.old_run.timed(machine,symbols,"fixture_replay")
                addresses=[event[2] for event in machine.prefetch_events]
                assert collections.Counter(addresses)==collections.Counter(expected),(
                    indexed,partial,parts,picks,"unexpected/missing hint",addresses,expected)
                for ordinal,pc,address in machine.prefetch_events:
                    assert base<=address<pkg_end or sg_begin<=address<sg_end,(hex(address),"hint outside package/group allocation")
                    target=expected_leads[address]
                    assert ordinal<machine.emit_instruction_boundaries[target],(target,"hint after target geometry entry")
                rows.append(dict(indexed=indexed,partial=partial,parts=parts,picks_per_part=picks,
                    total_hints=len(addresses),straddled_hot_headers=straddled,
                    expected_payload_meshlets=0 if partial==2 else parts*picks-1,status="PASS"))
                print(json.dumps(rows[-1]),flush=True)
    result=dict(status="PASS",scope=__doc__,cases=rows,build=str(args.build.resolve()),
        build_sha256=cost.profile.sha(args.build),elf_sha256=arm["sha256"],
        source_sha256=cost.profile.sha(Path(__file__)))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+"\n")
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    result=check(args)
    print(json.dumps(dict(status=result["status"],cases=len(result["cases"]))))
