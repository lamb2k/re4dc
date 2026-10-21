#!/usr/bin/env python3
"""Read an own FLYSAVE1 checkpoint using target-compiled offsets and two ELF code anchors."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import zlib


def decode(path):
    blob=Path(path).read_bytes()
    if blob[:8]!=b'FLYSAVE1':raise ValueError('unsupported state header')
    png=struct.unpack_from('<I',blob,20)[0];at=24+png
    if blob[at:at+8]!=b'#RZIPv\x01#':raise ValueError('unsupported archive header')
    chunk,total=struct.unpack_from('<IQ',blob,at+8);at+=20;pieces=[];decoded=0
    if total>64*1024**2 or chunk>16*1024**2:raise ValueError('unexpected archive size')
    while decoded<total:
        size=struct.unpack_from('<I',blob,at)[0];at+=4
        if not size:continue
        piece=zlib.decompress(blob[at:at+size]);at+=size
        if len(piece)>chunk:raise ValueError('archive chunk exceeds source contract')
        pieces.append(piece);decoded+=len(piece)
    if decoded!=total or at!=len(blob):raise ValueError('archive extent mismatch')
    return b''.join(pieces)


def code_segment(elf):
    blob=Path(elf).read_bytes()
    if blob[:6]!=b'\x7fELF\x01\x01':raise ValueError('expected little-endian target ELF32')
    off=struct.unpack_from('<I',blob,28)[0];size,count=struct.unpack_from('<HH',blob,42)
    rows=[]
    for i in range(count):
        kind,fo,va,pa,fs,ms,flags,alignment=struct.unpack_from('<8I',blob,off+i*size)
        if kind==1 and 0x8c000000<=va<0x8d000000 and fs>0x110000:rows.append((va,blob[fo:fo+fs]))
    if len(rows)!=1:raise ValueError('ambiguous target code segment')
    return rows[0]


def inspect(state,elf,layout_path,nm):
    raw=decode(state);va,code=code_segment(elf);locations=[];pos=-1
    while True:
        pos=raw.find(code[0x4000:0x4100],pos+1)
        if pos<0:break
        base=pos-(va+0x4000-0x8c000000)
        if base>=0 and base+0x1000000<=len(raw) and raw[base+va+0x100000-0x8c000000:base+va+0x100100-0x8c000000]==code[0x100000:0x100100]:locations.append(base)
    if len(locations)!=1:raise ValueError('two exact ELF anchors did not identify one RAM extent')
    base=locations[0]
    def read(address,size):
        if not 0x8c000000<=address<=address+size<=0x8d000000:raise ValueError('guest read outside RAM')
        return raw[base+address-0x8c000000:base+address-0x8c000000+size]
    u32=lambda a:struct.unpack('<I',read(a,4))[0]
    values={p[2]:int(p[0],16) for line in nm.splitlines() if len(p:=line.split())==3 and p[2] in ['_pG','_pPL','_CamCtrl']}
    if len(values)!=3:raise ValueError('matching ELF symbols incomplete')
    layout=json.loads(Path(layout_path).read_text())['layout'];pg=u32(values['_pG']);pl=u32(values['_pPL']);cam=values['_CamCtrl']+layout['camera']
    floats=lambda address,count:struct.unpack('<'+'f'*count,read(address,4*count))
    player=floats(pl+layout['player_pos'],3);angles=floats(pl+layout['player_ang'],3);camera=floats(cam+layout['camera_param'],8)
    if not all(math.isfinite(n) for n in player+angles+camera):raise ValueError('nonfinite scene scalars')
    return {'room':hex(struct.unpack('<H',read(pg+layout['room'],2))[0]),'game_tick':u32(pg+layout['frame']),
            'player_position':player,'player_angles':angles,'camera_position':camera[:3],'camera_target':camera[3:6],
            'camera_roll':camera[6],'camera_fovy':camera[7],
            'camera_mat':floats(cam+layout['camera_mat'],12),'camera_view_mat':floats(cam+layout['camera_vmat'],12),
            'camera_projection':floats(cam+layout['camera_proj'],16),
            'camera_control_sha256':hashlib.sha256(read(values['_CamCtrl'],layout['CameraControl_size'])).hexdigest(),
            'RAM_serialization_offset':base,'decoded_state_bytes':len(raw),
            'symbols':{k:hex(v) for k,v in values.items()},
            'state_sha256':hashlib.sha256(Path(state).read_bytes()).hexdigest(),
            'elf_sha256':hashlib.sha256(Path(elf).read_bytes()).hexdigest(),
            'layout_receipt_sha256':hashlib.sha256(Path(layout_path).read_bytes()).hexdigest(),
            'scope':'read-only checkpoint pose/camera at the saved game tick; does not bind earlier host-time screenshots to exact ticks'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',required=True);p.add_argument('--elf',required=True)
    p.add_argument('--layout',required=True);p.add_argument('--out',required=True)
    p.add_argument('--nm',default='/opt/toolchains/dc/sh-elf/bin/sh-elf-nm')
    a=p.parse_args();nm=subprocess.check_output([a.nm,'-n',a.elf],text=True)
    result=inspect(a.state,a.elf,a.layout,nm)
    with Path(a.out).open('x') as out:json.dump(result,out,indent=2);out.write('\n')
    print(json.dumps({k:result[k] for k in ['room','game_tick','player_position','camera_position','state_sha256']}))

if __name__=='__main__':main()
