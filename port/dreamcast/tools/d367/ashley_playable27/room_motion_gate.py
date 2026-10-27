#!/usr/bin/env python3
"""Prove prepared Ashley-room FCV/SEQ members match original PS2 bytes.

room_motion_gate.py PS2_DAT PREPARED_ARC OUTPUT_JSON --room 20d|20e
Read only. This neither stages room assets nor certifies chapter playability.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'motion'))
import ps2_motion_prepared as pm


def audit(ps2_dat,prepared_arc,room):
    ps2_bytes=ps2_dat.read_bytes();prepared_bytes=prepared_arc.read_bytes()
    ps2={i+4:(tag,data) for i,tag,data in pm.ps2_bin.dat_entries(ps2_bytes)}
    current=pm.Prepared(prepared_bytes,bare=True)
    required={0x20,0x21,0x22,0x26,0x34,*range(0x35,0x3d)} if room=='20d' else {0x24,0x25,0x26}
    rows=[];seen=set()
    for i,(tag,off) in enumerate(zip(current.tags,current.offs)):
        if not off or tag not in (b'FCV\0',b'SEQ\0'):continue
        arc=i+4;name=tag.decode().strip('\0');seen.add(arc)
        if arc not in ps2 or ps2[arc][0]!=name:
            raise ValueError(f'{room}/{arc:x}: missing or differently typed PS2 member')
        source=ps2[arc][1]
        expected=pm.ps2_fcv_host(source) if name=='FCV' else pm.ps2_seq_host(source)
        actual=current.member(off)
        if actual!=expected:
            raise ValueError(f'{room}/{arc:x}: prepared motion differs from original PS2')
        rows.append(dict(arc=arc,tag=name,bytes=len(actual),sha256=hashlib.sha256(actual).hexdigest(),
                         explicit_player_interaction=arc in required))
    if not required<=seen:
        raise ValueError(f'{room}: missing explicit Ashley interaction members {sorted(required-seen)}')
    extra=[dict(arc=arc,tag=tag,bytes=len(data)) for arc,(tag,data) in ps2.items()
           if tag in ('FCV','SEQ') and arc not in seen]
    return dict(room=room,ps2_dat=str(ps2_dat),ps2_dat_sha256=hashlib.sha256(ps2_bytes).hexdigest(),
        prepared_arc=str(prepared_arc),prepared_arc_sha256=hashlib.sha256(prepared_bytes).hexdigest(),
        all_live_room_motion_members_byte_equal_ps2=True,members=rows,
        ps2_only_members_not_selected=extra,replacements_needed=False,
        scope='Prepared historical room mirror only; not present in current release stage. No chapter/guest acceptance.')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('ps2_dat',type=Path);ap.add_argument('prepared_arc',type=Path)
    ap.add_argument('output',type=Path);ap.add_argument('--room',choices=['20d','20e'],required=True)
    a=ap.parse_args();result=audit(a.ps2_dat,a.prepared_arc,a.room)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2))
    print(json.dumps(dict(room=a.room,motion_members=len(result['members']),exact=True,replacements_needed=False)))


if __name__=='__main__':main()
