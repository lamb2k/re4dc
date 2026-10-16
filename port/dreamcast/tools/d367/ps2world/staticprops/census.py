#!/usr/bin/env python3
"""Read-only census of the exact T15 fixture's static-world packages."""
from pathlib import Path
import json, struct, hashlib, zlib, re, subprocess, sys, collections

T = Path('/root/probe/codex-cpu-t15-20261016/tree')
OUT = Path('/root/probe/codex-static-props-t15-20261016/audit')
FIX = Path('/root/probe/codex-actor-t15-20261016/logs/fix/kos-call-49152-0.json')
MAN = Path('/mnt/c/Flycast-Evidence/re4-dreamcast/codex-actor-t15-20261016/hwmodel-cxt16a0-cross/payload-manifest.json')
replacements = json.loads(FIX.read_text())['replace']
manifest = json.loads(MAN.read_text())
sys.path.insert(0,str(T/'port/dreamcast/tools'))
import room_smd
sha = lambda b: hashlib.sha256(b).hexdigest()
source = T / 'port/dreamcast/game/model_bridge.cpp'
src = source.read_text()
table = src.split('const Entry kTable[] = {',1)[-1].split('};',1)[0]
if table == src.split('};',1)[0]:
    table = src[src.index('const Entry kTable'):].split('};',1)[0]
bakes = []
for room,kind,obj,rest,placement in re.findall(r'\{0x([0-9a-fA-F]+),(\d+),0x([0-9a-fA-F]+),0x([0-9a-fA-F]+)U?,(\d+)\}',table):
    bakes.append(dict(room=f'r{int(room,16):03x}',kind=int(kind),object_id=int(obj,16),rest_hash=rest,placement=int(placement)))
assert len(bakes) == 14,bakes

etc_classes={}
for file in ('EtcModel.cpp','et00.cpp'):
    s=(T/'src/game'/file).read_text()
    for m in re.finditer(r'\bint (Et([0-9a-fA-F]{2})_init)\([^;{]*\)\s*\{',s):
        start=m.end()-1;depth=1;end=start+1
        while depth:
            depth+=(s[end]=='{')-(s[end]=='}');end+=1
        body=s[start:end]
        factories=sorted(set(re.findall(r'\b(Set[A-Z][a-zA-Z0-9_]*)\(',body)))
        if 'EtXX_init(' in body:factories.append('SetWindow')
        etc_classes[int(m.group(2),16)]=dict(factories=factories,source=f'src/game/{file}',line=s.count('\n',0,m.start())+1)

def read_ets(room):
    dest=f'st1/{room}.dar';p=Path(replacements[dest]);b=p.read_bytes()
    assert manifest[dest]['sha256']==sha(b)
    kind,size,destination,offset=struct.unpack_from('<4I',b,0x20)
    pay=b[offset:offset+size];entries=[]
    for i,(tag,start,end) in enumerate(room_smd.tagged_entries(pay,'<')):
        if tag.rstrip(b'\0')!=b'ETS':continue
        count=struct.unpack_from('<H',pay,start)[0]
        assert start+16+count*40<=end
        for j in range(count):
            off=start+16+j*40;ident,slot=struct.unpack_from('<2H',pay,off)
            mapping=etc_classes.get(ident,{'factories':[]})
            factories=mapping['factories']
            candidate=bool(set(factories)&{'SetDoor','SetBox','SetRack','SetWindow'})
            entries.append(dict(section=i,index=j,etc_id=f'{ident:02x}',slot=slot,source_factory=mapping,existing_bake_class_candidate=candidate))
    counts=collections.Counter(f for e in entries for f in e['source_factory']['factories'])
    return dict(source=str(p),sha256=sha(b),entries=entries,total_records=len(entries),factory_record_counts=dict(sorted(counts.items())),candidate_records=sum(e['existing_bake_class_candidate'] for e in entries),scope='Static ETS declarations only; not live instances, visible counts, immutable eligibility or room-code spawns.')

rows=[]
for dest,filename in sorted(replacements.items()):
    if not re.fullmatch(r'dc/native/r[0-9a-f]{3}/ps2-world\.r4pw',dest): continue
    room=dest.split('/')[2]
    p=Path(filename); b=p.read_bytes()
    magic,version,nplace,npart,nmesh,crc,res0,res1=struct.unpack_from('<4s7I',b)
    assert magic==b'R4PW' and version==1 and len(b)==32+16*npart+52*nplace
    assert zlib.crc32(b[32:])==crc
    places=[struct.unpack_from('<HH12f',b,32+16*npart+52*i) for i in range(nplace)]
    mdest=dest.replace('.r4pw','.re4mesh'); mp=Path(replacements[mdest]); mb=mp.read_bytes()
    h=struct.unpack_from('<4s19I',mb)
    assert h[0]==b'R4IM' and h[2]==len(mb) and zlib.crc32(mb[80:])==h[3]
    assert h[4]==nmesh and h[5]==npart
    mh=manifest[mdest]; ph=manifest[dest]
    def match(m,blob):
        if isinstance(m,dict): return m.get('sha256')==sha(blob) and m.get('bytes',m.get('size',len(blob)))==len(blob)
        return m==sha(blob)
    assert match(mh,mb),(mdest,mh)
    assert match(ph,b),(dest,ph)
    sideparts=[struct.unpack_from('<4I',b,32+16*i) for i in range(npart)]
    fields=[x[1] for x in places]
    rec=dict(room=room,scope='chapter_1_route' if int(room[1:],16)<=0x10b else 'chapter_2_1_route',
        r4pw_source=str(p),mesh_source=str(mp),r4pw_sha256=sha(b),mesh_sha256=sha(mb),
        r4pw_bytes=len(b),mesh_bytes=len(mb),combined_bytes=len(b)+len(mb),
        placements=nplace,min_placement=min(fields),max_placement=max(fields),
        placement_ids_unique=len(set(fields))==len(fields),mesh_count=nmesh,part_count=npart,
        meshlet_count=h[6],vertex_count=h[7],index_bytes=h[8],color_mode=h[16],
        baked_runtime_records=[x for x in bakes if x['room']==room],
        available_append_ids_under_existing_gate=max(0,511-max(fields)),
        staged_mesh_is_active_variant=room!='r101',
        texture_key_count=len(set((q[0],q[1]) for q in sideparts)),
        current_room_owned_prop_cost_ms=None,
        measured_static_bake_incremental_saving_ms=None)
    rec['etc_declarations']=read_ets(room)
    if room=='r101':
        variant=Path(replacements['dc/native/r101/ps2-wv5.re4mesh']); vb=variant.read_bytes()
        vh=struct.unpack_from('<4s19I',vb)
        assert match(manifest['dc/native/r101/ps2-wv5.re4mesh'],vb)
        rec['active_variant']=dict(path=str(variant),sha256=sha(vb),bytes=len(vb),meshes=vh[4],parts=vh[5],meshlets=vh[6],vertices=vh[7])
        rec['current_room_owned_prop_cost_ms']={'value':1.559094,'model':'nominal callgraph','scene':'r101 cross, frames 500:799 stride 10','meaning':'all remaining per-part setup, not immutable props or removable work','source':'codex-actor-t15-20261016/current-model-comparison.json'}
    rows.append(rec)
assert len(rows)==17
report=dict(status='READ_ONLY_CENSUS_PASS',head=subprocess.check_output(['git','-C',str(T),'rev-parse','HEAD'],text=True).strip(),fixture=str(FIX),fixture_sha256=sha(FIX.read_bytes()),manifest=str(MAN),manifest_sha256=sha(MAN.read_bytes()),source=str(source),source_sha256=sha(source.read_bytes()),rooms=rows,
    limits=['All package bytes verified against the current actor T15 cost fixture manifest.','The source registry supports more rooms than this 17-room staged fixture.','Chapter scope follows the fullplay route: lake ends 1-3 and r11b starts 2-1; stage-1 room IDs are not all chapter 1.','Baked runtime records prove configured gate coverage, not live visibility or immutable eligibility.','No new runtime code, baked geometry, capture, heap allocation or performance claim.'])
OUT.mkdir(parents=True,exist_ok=True)
(OUT/'room-package-census.json').write_text(json.dumps(report,indent=2)+'\n')
print('| Room | R4PW placements | Max ID | Existing bake records | R4IM bytes | R4PW bytes | Append IDs left |')
print('|---|---:|---:|---:|---:|---:|---:|')
for r in rows:print(f"| {r['room']} | {r['placements']} | {r['max_placement']} | {len(r['baked_runtime_records'])} | {r['mesh_bytes']} | {r['r4pw_bytes']} | {r['available_append_ids_under_existing_gate']} |")
print('ETS candidates (declarations, not live/immutable):')
for r in rows:print(r['room'],r['etc_declarations']['total_records'],r['etc_declarations']['candidate_records'],r['etc_declarations']['factory_record_counts'])
print('Saved',OUT/'room-package-census.json')
