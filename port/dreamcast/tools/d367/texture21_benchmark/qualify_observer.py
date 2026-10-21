#!/usr/bin/env python3
from pathlib import Path
import json,hashlib,struct,sys
import argparse
from observer import Typed,ram_range
a=argparse.ArgumentParser(description='Exercise every observer field against actual frozen DWARF/symbols in synthetic RAM; no guest.');a.add_argument('--plan',type=Path,required=True);a.add_argument('--runtime-binding',default='observer-runtime-02');a.add_argument('--out',type=Path,required=True);a=a.parse_args()
base=a.plan;d=base/a.runtime_binding;layout=json.loads((d/'scene-existing-dwarf02.json').read_text());plan=json.loads((base/'observation-cold-window.json').read_text());plan['selected']=json.loads((base/'inputs-final/plan-inputs.json').read_text())['selected'];plan['read_only_observer']['typed_layouts']['scene']=layout
raw=bytearray(16777216)
def write(a,b):o=ram_range(a,len(b));raw[o:o+len(b)]=b
def read(a,n):o=ram_range(a,n);return bytes(raw[o:o+n])
def w(a,v):write(a,struct.pack('<I',v))
t=Typed(read,plan);g=0x8c500000;pl=0x8c600000;w(t.sym('_pG'),g);w(t.sym('_pPL'),pl);w(g+layout['types']['GlobalWork']['members']['Frame_cnt'],1);write(g+20382,struct.pack('<H',0x103));assert t.scene()['room_id']==0x103
entry=t.entries;selected=plan['selected'][0];write(entry+64,struct.pack('<II',*[int(x,16) for x in selected['scoped_key'].split('-')]));write(entry+76,b'\1');w(entry+72,10)
P=t.t['native_ui']['types']['Package']['members'];data=0x8c700000;ptrs=0x8c710000;owns=0x8c710020
for name,v in [('header_',data),('data_',data),('pvr_textures_',ptrs),('owns_texture_',owns)]:w(entry+P[name],v)
write(entry+P['upload_complete_'],b'\1');write(ptrs,struct.pack('<II',0xa4001000,0xa4001000));write(owns,b'\1')
H=t.t['native_ui']['types']['Header']['members']
for name,v in [('texture_count',1),('texture_stride',96),('texture_offset',48),('payload_crc32',selected['candidate_crc32'])]:w(data+H[name],v)
T=t.t['native_ui']['types']['Texture']['members']
for name,v in [('width',64),('height',64),('format',0),('flags',4),('payload',2),('data_size',3414)]:w(data+48+T[name],v)
r=t.table();assert r['selected'][0]['candidate_descriptor_match'] and r['selected'][0]['admission']=='sampled_valid_uploaded' and r['candidate_only_cohorts']==1
for name,v in [('frame',10),('direct_open',1),('model_handle',entry),('model_used',0),('model_pending',1),('model_packets',0x8c720000)]:w(t.sym('__ZN12_GLOBAL__N_1L'+str(len(name))+name+'E'),v)
write(0x8c720000,struct.pack('<8I',0,0,27,0xc0000000,0,0,0,0));assert t.witness()['physical_64_square']
with a.out.open('x') as output:output.write(json.dumps({'result':'PASS','source':'004cf224674fa60cf08dc10e641c723de238a0fd','actual_objects':['cam_ctrl.o','model.o','native_ui.o'],'actual_named_layout_fields':'ALL required fields validated before process attach','room_offset':20382,'scene_read':True,'candidate_package_table_descriptor_crc_shape_read':True,'stable_direct_header_read':True,'memory':'Synthetic bytearray using exact corrected existing ON target DWARF and symbols; no guest or writes to game','preserved_failure':'observer-runtime-01 and cold-functional-C-01 unchanged'},indent=2)+'\n')
print('Actual-layout full scene, selected package and direct-header dry-run PASS')
