"""Read-only frozen castle ELF/raw/master/all-overlay binding; metadata output only."""
from pathlib import Path
import ast, hashlib, json, struct, datetime, subprocess
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18')
R=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21')
D=R/'recovered-j-content-20261021'
T=Path(r'\\wsl.localhost\Ubuntu-24.04\root\probe\codex-castle18')
B=Path(r'\\wsl.localhost\Ubuntu-24.04\root\probe\codex-texture21-benchmark\port\dreamcast\tools\d367\texture21_benchmark')
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
h=lambda b:hashlib.sha256(b).hexdigest()
# Reuse reviewed pure ELF and overlay routines, without importing benchmark constants/main.
ns={'struct':struct}
for name,functions in [('elf_load_tail.py',{'inspect'}),('programme994_inspect.py',{'elf_tables','fnv'})]:
 tree=ast.parse((B/name).read_text()); nodes=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name in functions]
 exec(compile(ast.Module(body=nodes,type_ignores=[]),str(B/name),'exec'),ns)
elf=R/'builds/c21jmW/re4dc-game.elf'; raw=R/'builds/c21jmW/1ST_READ.raw.bin'; blob=elf.read_bytes()
# Only static-load fields are consumed; benchmark tail layout is deliberately not claimed.
static=ns['inspect'](blob,raw.stat().st_size,{'selected_paths':{'/1ST_READ.BIN':{'after_extent':45000}},'cooked_track_bytes':1018789888})
loads=static['PT_LOAD'];lo=min(r['vaddr'] for r in loads if r['file_bytes']);hi=max(r['virtual_file_end'] for r in loads)
flat=bytearray(hi-lo)
for row in loads:flat[row['vaddr']-lo:row['virtual_file_end']-lo]=blob[row['offset']:row['offset']+row['file_bytes']]
assert bytes(flat)==raw.read_bytes()
assert sha(elf)=='4d823b496b9a402baadabe7f679c089fa0fd55c7ffd175ec634915745a11487f'
assert h(flat)=='78fb06976cc394ec6e4cb7861046c24a15f82ddf7bcb2fcbfd452d3fcbf72e33'
sec,sym=ns['elf_tables'](blob);text=sec['.text'];tb=blob[text[4]:text[4]+(text[5]&~3)];identity=(ns['fnv'](tb),len(tb))
assert len(sym['_re4dc_image_id'])==1
v=sym['_re4dc_image_id'][0][0]; owners=[r for r in sec.values() if r[1]==1 and r[3]<=v and v+8<=r[3]+r[5]];assert len(owners)==1
s=owners[0]; assert struct.unpack_from('<2I',blob,s[4]+v-s[3])==identity
manifest=json.loads((D/'master/base-manifest.json').read_text())
records=json.loads((D/'iso-layout-and-directory-records.json').read_text()); rr={r['path'].lstrip('/'):r for r in records if r['namespace']=='RR' and not r['isdir']}
image=D/'master/track03.iso'; assert sha(image)=='b67ac21eff8d819ef9ca5f0997b4c16401cb98a3d304feb65aa4b90f7affbeb6'
names=sorted(n for n in manifest if n.startswith('dc/') and n.endswith('.ovl'))
proof=[]
with image.open('rb') as f:
 def read_disc(n):
  r=rr[n];f.seek((r['extent']-45000)*2048);data=f.read(r['size']);assert len(data)==r['size']
  assert h(data)==manifest[n]['sha256'] and len(data)==manifest[n]['size'];return data
 assert read_disc('1ST_READ.BIN')==flat
 for n in names:
  data=read_disc(n); header=struct.unpack_from('<16I',data); assert header[:2]==(0x4f344552,1)
  assert len(data)==64+header[2]+header[3]*4 and tuple(header[14:])==identity
  payload=data[64:64+header[2]];rel=data[64+header[2]:]; offsets=[r[0] for r in struct.iter_unpack('<I',rel)]
  assert ns['fnv'](payload)==header[12] and ns['fnv'](rel)==header[13]
  assert all(o<=header[2] for o in header[5:12]) and offsets==sorted(set(offsets))
  assert all(o%4==0 and o+4<=header[2] and header[4]<=struct.unpack_from('<I',payload,o)[0]<=header[4]+header[2] for o in offsets)
  nomination=R/'programs/candidate-routec21jmW'/Path(n).name; assert nomination.read_bytes()==data
  proof.append(dict(path=n,extent=rr[n]['extent'],bytes=len(data),sha256=h(data),header=list(header),relocations_checked=len(offsets),image_id_exact=True,nomination_overlay_exact=True,final_ELF_section_present=('.ovl_'+Path(n).stem in sec)))
# Reproduce KOS scramble in memory to resolve the distinct nomination bytes.
nomination=R/'programs/candidate-routec21jmW/1ST_READ.BIN'; seed=len(flat)&0xffff;remaining=len(flat);base=0;out=bytearray();chunk=2048*1024
while chunk>=32:
 while remaining>=chunk:
  idx=list(range(chunk//32))
  for i in range(len(idx)-1,-1,-1):
   seed=(seed*2109+9273)&0x7fff;x=(((seed+0xc000)&0xffff)*i)>>16;idx[i],idx[x]=idx[x],idx[i];o=base+32*idx[i];out.extend(flat[o:o+32])
  remaining-=chunk;base+=chunk
 chunk>>=1
out.extend(flat[base:base+remaining]);assert out==nomination.read_bytes()
stack=Path(r'\\wsl.localhost\Ubuntu-24.04\root\probe\lanes\route\out-c21jmW\stack.txt');source=stack.read_text().strip();assert source=='12a841d7cfe2c747266b0c330555557e651a4af0'
knobs=R/'builds/c21jmW/resolved-knobs.txt'; actual=dict(x.split('=',1) for x in knobs.read_text().splitlines() if '=' in x and not x.startswith('#'))
refs=[B/'elf_load_tail.py',B/'programme994_inspect.py',stack,knobs,R/'builds/c21jmW/candidate.txt',R/'skin-player-j-build-logs/logs-build.txt',R/'ashley-walk-J-build-proof.json',D/'master/base-manifest.json',D/'master-proof.json',D/'reconstruction-input-proof.json',D/'iso-layout-and-directory-records.json',L/'test21-build-skin-player-j.sh',L/'test21-skin-player-j-ram-master.sh',T/'port/dreamcast/tools/d367/castle18/build-test21-disc2.sh',T/'port/dreamcast/tools/d367/ch2/ch2-build.sh',T/'port/dreamcast/tools/d367/test15/t15-build.sh',T/'port/dreamcast/tools/d367/route/route-build.sh',T/'port/dreamcast/tools/d367/discsets/mkdisc2.py',T/'port/dreamcast/game/tools/link.sh',T/'port/dreamcast/game/tools/gen_overlay.py',T/'port/dreamcast/game/tools/ovl_id_patch.py',Path(r'\\wsl.localhost\Ubuntu-24.04\root\work\kos\utils\scramble\scramble.c')]
result=dict(schema='castle-frozen-master-programme-binding-v1',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='Read-only stored byte/ELF/overlay/source-build receipt binding. Not a new build, live Flycast, release or physical Dreamcast acceptance. No per-TU dependency-closure reconstruction is asserted.',source_commit_recorded_at_build=source,source_stack_clean_at_build=len(stack.read_text().splitlines())==1,ELF=dict(path=str(elf),sha256=sha(elf),entry=static['entry'],PT_LOAD=loads,end=static['_end'],static_span_end=static['mainRAM_static_span_end'],raw_load_base=lo,raw_exact_PT_LOAD_file_bytes_and_zero_holes=True),actual_master_program=dict(path='1ST_READ.BIN',bytes=len(flat),sha256=h(flat),extent=rr['1ST_READ.BIN']['extent'],raw_build_path=str(raw),direct_ELF_objcopy_no_scramble=True),master=dict(path=str(image),bytes=image.stat().st_size,sha256=sha(image)),nomination=dict(path=str(nomination),sha256=sha(nomination),exact_KOS_scramble_of_ELF_raw=True,consumed_by_base_harness=False),derivation=['route-build.sh objcopy -R .stack -O binary then KOS scramble produces nomination BIN; reproduced exactly in memory','mkdisc2.py separately objcopy -R .stack -O binary directly into disc tree1ST_READ.BIN; pure PT_LOAD reconstruction equals buildraw and actual masterextent','Recovered master keeps original manifest payload identities; newly mastered ISO metadata is separate and fullSHA b67 exact','All actual master dc/*.ovl enumerated from manifest, not benchmark list; each payload/relocationFNV/imageID validated against frozenELF text and retained nomination overlay bytes'],image_id=list(identity),overlay_count=len(proof),overlays=proof,resolved_flags_sha256=sha(knobs),resolved_flags=actual,input_refs={str(p):dict(bytes=p.stat().st_size,sha256=sha(p))for p in refs},preserved_erratum='Earlier nomination-directory identity alone did not establish consumed master programme; this additive receipt closes it with exact ELF/PT_LOAD/raw/master extents and scramble derivation. Old receipts unchanged.')
target=D/'frozen-master-programme-binding-20261021.json';assert not target.exists();target.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(report=str(target),report_sha256=sha(target),raw_sha256=h(flat),nomination_scramble_exact=True,overlay_count=len(proof),image_id=identity,PT_LOAD_count=len(loads),source=source)))
