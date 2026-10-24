#!/usr/bin/env python3
"""One explicitly granted 8x8 historical PS2 converter proof, RAM-only asset bytes.
Writes new public source snapshots and metadata only; never outputs/replaces an asset.
"""
import ast,collections,hashlib,importlib.util,json,os,resource,signal,struct,subprocess,sys,time,types,zlib
from pathlib import Path
sys.dont_write_bytecode=True
resource.setrlimit(resource.RLIMIT_AS,(268435456,268435456));resource.setrlimit(resource.RLIMIT_CORE,(0,0));signal.alarm(120)
REPO=Path('/root/work/lanes/gc-catalog-proof24')
HERE=Path('/mnt/c/Game Dev/Emulators/codex-lanes/gc-catalog-proof24/origin-discovery-v1')
ISO=Path('/mnt/c/Users/Public/ps2/DVD/Resident Evil 4 (USA).iso')
LIB=Path('/mnt/c/Game Dev/Emulators/re4-assets-private/ps2lib')
PRIVATE=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/gc-catalog-proof24-20261024')
KEY='47a9bc5b-b0495b0f';OUTPUT_SHA='91ad12accc6fd1ad52b1f6289ef2ffebc1cbc31b91a964e6295498419e301900'
CONVERTER='5182665f6d6b62aee348e58266c015c891da5d85'
def sha(data):return hashlib.sha256(data).hexdigest()
def enc(obj):return (json.dumps(obj,indent=2,sort_keys=True)+'\n').encode()
def pin(path):
 b=path.read_bytes();return {'path':str(path),'bytes':len(b),'sha256':sha(b)}
def fingerprint(s):return s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns
def source(rel):return subprocess.check_output(['git','-C',str(REPO),'show',CONVERTER+':'+rel],timeout=20)
def read_at(fp,offset,size):
 fp.seek(offset);b=fp.read(size);assert len(b)==size;return b

def platform_identity(f):
 pvd=read_at(f,16*2048,2048);assert pvd[:7]==b'\x01CD001\x01'
 root=pvd[156:190];sector=struct.unpack_from('<I',root,2)[0];length=struct.unpack_from('<I',root,10)[0];assert 0<length<=1024*1024
 data=read_at(f,sector*2048,length);entries={};i=0
 while i<len(data):
  n=data[i]
  if not n:i=(i//2048+1)*2048;continue
  assert i+n<=len(data) and n>=34;q=data[i:i+n];namelen=q[32];name=q[33:33+namelen].decode('ascii','replace');entries[name]=(struct.unpack_from('<I',q,2)[0]*2048,struct.unpack_from('<I',q,10)[0]);i+=n
 cnf=entries['SYSTEM.CNF;1'];assert 0<cnf[1]<=4096;boot=read_at(f,*cnf);assert b'SLUS_211.34' in boot
 exe=entries['SLUS_211.34;1'];header=read_at(f,exe[0],64);assert header[:6]==b'\x7fELF\x01\x01' and struct.unpack_from('<H',header,18)[0]==8
 return {'volume_id':pvd[40:72].decode('ascii').strip(),'pvd_sha256':sha(pvd),'root_directory_sha256':sha(data),'SYSTEM_CNF':{'offset':cnf[0],'bytes':cnf[1],'sha256':sha(boot)},'boot_ELF':{'name':'SLUS_211.34;1','offset':exe[0],'bytes':exe[1],'header64_sha256':sha(header),'ELF_machine':'MIPS'},'full_ISO_hash_computed':False,'retail_authenticity_or_untampered_dump_independently_proved':False}

def selected_picture(e):
 h=struct.unpack_from('<12I',e);assert h[0]==11;o,t=h[1],h[6];n=struct.unpack_from('<I',e,o)[0];assert n<4096 and struct.unpack_from('<I',e,t)[0]==n
 entries=[(struct.unpack_from('<H',e,o+4+8*i)[0],t+struct.unpack_from('<I',e,t+4+4*i)[0]) for i in range(n)]
 found=[(i,v) for i,v in enumerate(entries) if v[0]==0xf7];assert len(found)==1;slot,(_,base)=found[0]
 magic,count,start=struct.unpack_from('<III',e,base);assert magic==0x1000 and count==1
 desc=base+start;w,h,depth,inter=struct.unpack_from('<4H',e,desc);io,po=struct.unpack_from('<2I',e,desc+32);assert (w,h,depth)==(8,8,8) and inter&~1==0
 end=min([v[1] for v in entries if v[1]>base]+[len(e)]);raw_start=base+io;raw=e[raw_start:raw_start+w*h//2];assert len(raw)==32 and raw_start+32<=end
 colors=[]
 for c in range(16):
  q=base+po+(c if c<8 else 16+c-8)*4;assert base<=q and q+4<=end;r,g,b,a=e[q:q+4];colors.append((r,g,b,255 if a>=128 else a*255//128))
 indices=[v for b in raw for v in (b&15,b>>4)];pixels=[colors[v] for v in indices]
 if inter&1:pixels=[pixels[x*w+y] for y in range(w) for x in range(h)];w,h=h,w
 return w,h,pixels,{'id':247,'slot':slot,'tpl_offset_in_EFF':base,'tpl_bytes':end-base,'tpl_sha256':sha(e[base:end]),'picture_descriptor_offset':desc,'picture_descriptor_sha256':sha(e[desc:desc+48]),'index_offset_in_EFF':raw_start,'index_bytes':32,'index_sha256':sha(raw),'palette_span_offset_in_EFF':base+po,'palette_span_bytes':96,'palette_span_sha256':sha(e[base+po:base+po+96]),'width':w,'height':h,'depth':depth,'interlace':inter,'decoded_pixel_RGBA_sha256':sha(bytes(v for c in pixels for v in c)),'unique_decoded_colors':len(set(pixels))}

def exact_functions(raw,names,globals):
 tree=ast.parse(raw);nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names];assert {n.name for n in nodes}==set(names)
 exec(compile(ast.Module(body=nodes,type_ignores=[]),'<exact historical public source>','exec'),globals)
 return {n.name:sha(ast.get_source_segment(raw.decode(),n).encode()) for n in nodes}

def main():
 start=time.monotonic();assert not (HERE/'CHECKS.json').exists()
 xfile=REPO/'port/dreamcast/tools/ps2_room_extract.py';spec=importlib.util.spec_from_file_location('extract',xfile);X=importlib.util.module_from_spec(spec);spec.loader.exec_module(X)
 with ISO.open('rb') as f:
  before=fingerprint(os.fstat(f.fileno()));platform=platform_identity(f);idx,indexsha=X.afs_index(f);member=idx['core.dat'];assert member['index']==368 and member['size']==1524064
  core=read_at(f,member['offset'],member['size']);assert sha(core)=='c48e2165a41cb20b124a11a96e9b00bcdcd051f435475004edcc23a47e920e33'
  assert before==fingerprint(os.fstat(f.fileno()))==fingerprint(ISO.stat())
 assert core==Path('/root/re4data/private/worldfx-20261018/ps2/Core.dat').read_bytes()
 n=struct.unpack_from('<I',core)[0];assert 1<n<4096;offs=list(struct.unpack_from('<%dI'%n,core,16));types=[core[16+4*n+4*i:20+4*n+4*i].rstrip(b'\0') for i in range(n)];assert types[1]==b'EFF';off,end=offs[1],offs[2];e=core[off:end]
 assert sha(e)=='e0a571bec16baa427c4267feb59ea6ec9aa64703b833d7ed42598115c62b0124'
 assert e==Path('/root/re4data/private/worldfx-20261018/cache/Core.ps2.eff1').read_bytes()
 w,h,pixels,picture=selected_picture(e)
 fxrel='port/dreamcast/tools/d367/test12fx/fx_ps2_pack.py';crel='port/dreamcast/tools/convert_tpl.py';fx=source(fxrel);csrc=source(crel);assert sha(fx)=='41d9cafee8e82bd254bad6c02e202b0f398892b7a9ba894fd7fc3aa71c9ce3d5'
 cenv={'struct':struct};wanted={'MAGIC','VERSION','FORMAT_PAL4_ARGB4444','FLAG_ALPHA','FLAG_BINARY_ALPHA','PAYLOAD_TWIDDLED','HEADER','TEXTURE'}
 ct=ast.parse(csrc);assigns=[v for v in ct.body if isinstance(v,ast.Assign) and any(isinstance(t,ast.Name) and t.id in wanted for t in v.targets)];assert len(assigns)==len(wanted);exec(compile(ast.Module(body=assigns,type_ignores=[]),'<historical constants>','exec'),cenv)
 cfunctions=exact_functions(csrc,['_pack_4444','_twiddle_table','twiddle_16bpp'],cenv);C=types_module.SimpleNamespace(**cenv)
 env={'struct':struct,'zlib':zlib,'C':C};ffunctions=exact_functions(fx,['premul','palette16','package'],env)
 palette=env['palette16'](collections.Counter(pixels));generated,error=env['package'](w,h,pixels,palette,(w,h));assert len(generated)==208 and sha(generated)==OUTPUT_SHA and error==0
 stored=LIB/'effects-tex/common'/f'{KEY}.re4tex';assert generated==stored.read_bytes()
 indexfile=LIB/'INDEX.tsv';fields=indexfile.read_text().splitlines();names=fields[0].split('\t');rows=[dict(zip(names,ln.split('\t'))) for ln in fields[1:] if ln.startswith('effects-tex\tcommon\tetc/core.das:0#1:0xf7\t')];assert len(rows)==1;row=rows[0]
 assert row['ps2_source']=='Core.dat:1' and row['converter']=='fx_ps2_pack.py@5182665f' and row['bytes']=='208' and row['gate']=='PASS:fx12-b-cand,fx12-h-cand,fx12b-candm-a'
 assert sha(KEY.encode()+generated)==row['sha256']=='7f7cb6a3ace45ffc051b0dcfbf071b054ac6be9ff9e7264e9543606489ad32f5'
 keysfile=LIB/'effects-tex/KEYS.tsv';keyrows=[ln for ln in keysfile.read_text().splitlines() if ln.startswith(KEY+'\t')];assert keyrows==[KEY+'\tcommon\tetc/core.das:0#1:0xf7\t0\t1\t1']
 catalog=PRIVATE/'private-current-v1/catalog.json';cat=json.loads(catalog.read_bytes());targets=[r for r in cat['entries'] if r['kind']=='texture' and r['id']==KEY];assert len(targets)==1;target=targets[0];assert target['sha256']==OUTPUT_SHA and target['provenance']=='unknown' and target['reviewed_proof'] is None
 use=target['sources'][0];pack=Path(use['path']);before=fingerprint(pack.stat())
 with pack.open('rb') as fp:
  hs=hashlib.sha256()
  for block in iter(lambda:fp.read(1024*1024),b''):hs.update(block)
  assert hs.hexdigest()==use['sha256']=='5bba464a1175d8ebe153d5aecb629ea9637807c2bf4fc438a32c17148d0729da'
  selected=read_at(fp,use['offset'],use['bytes']);assert selected==generated
  assert before==fingerprint(os.fstat(fp.fileno()))==fingerprint(pack.stat())
 # Negatives operate only on RAM values; they do not modify source or assets.
 mutated=pixels[:];mutated[0]=(0,0,0,255);badpal=env['palette16'](collections.Counter(mutated));bad,_=env['package'](w,h,mutated,badpal,(w,h));assert sha(bad)!=OUTPUT_SHA
 badheader=bytearray(generated);badheader[9]^=1;assert sha(badheader)!=OUTPUT_SHA
 assert sha(b'wrong-key'+generated)!=row['sha256']
 f7bad=bytearray(e);f7bad[picture['picture_descriptor_offset']:picture['picture_descriptor_offset']+2]=struct.pack('<H',16)
 rejected=False
 try:selected_picture(f7bad)
 except AssertionError:rejected=True
 assert rejected
 check={'schema':1,'status':'MECHANICAL_CHAIN_MATCH_ROOT_ORIGIN_REVIEW_PENDING','target':{'kind':'texture','id':KEY,'sha256':OUTPUT_SHA,'bytes':208},'origin_proposal':'ps2','reviewed':False,'source_authority':{'trusted_private_input':'User-selected existing PS2USA disc image; root must accept dump/source authority independently.','platform_checks':platform,'iso_path':str(ISO),'iso_size':ISO.stat().st_size,'afs_table_sha256':indexsha,'member':dict(member,sha256=sha(core)),'full_iso_hash_computed':False},'EFF':{'entry':1,'relative_offset_in_DAT':off,'absolute_offset_in_ISO':member['offset']+off,'bytes':len(e),'sha256':sha(e)},'picture':picture,'historical_converter':{'commit':CONVERTER,'fx_file':{'path':fxrel,'sha256':sha(fx)},'convert_tpl_file':{'path':crel,'sha256':sha(csrc)},'fx_function_sha256':ffunctions,'C_function_sha256':cfunctions,'execution':'Exact historical package/palette/twiddle functions from public Git source; one selected PS2picture decoded by bounded read-only checker matching historical linearPSMT4 path. No whole batch conversion.'},'existing_library_receipts':{'INDEX':pin(indexfile),'selected_row':row,'KEYS':pin(keysfile),'selected_key_row':keyrows[0],'gate_labels_are_historical_only':'Named original capture directories not independently rebound in this task; no new guest/look acceptance.'},'selected_current':{'selection_sha256':'5f917f3521be886568e3880f63404def99a9cfaa1c0810321713f216c98d4484','catalog_pin':pin(catalog),'pack_path':str(pack),'pack_size':use['size'],'pack_sha256':use['sha256'],'member_offset':use['offset'],'member_bytes':use['bytes'],'full_payload_sha256':sha(selected),'library_payload':pin(stored)},'replay':{'width':w,'height':h,'output_bytes':len(generated),'output_sha256':sha(generated),'full_output_equals_library_and_selected_member':True,'error':error,'RAM_only':True,'filesystem_asset_output':False},'negative_controls':['changed sourcepixel rejected by full outputSHA','changed outputheader rejected by full outputSHA','wrong lookupkey rejected by historical aggregate','wrong sourcepicture dimensions rejected'],'unproven_authority':['No full ISO/retail authenticity certificate; platform/source member checks and existing original-disc authority require root review.','Historical INDEX PASS strings are historical records; original guest/look captures not replayed or rebound here.','Root independent origin approval is not supplied; the existing allUnknown catalog remains unchanged.'],'elapsed_seconds':time.monotonic()-start,'max_address_space_bytes':268435456,'timeout_seconds':120,'production_pin_unchanged':0}
 # Public historical code snapshots and text/hash receipts only. Asset RAM values die here.
 for name,data in [('historical-fx_ps2_pack-5182665f.py',fx),('historical-convert_tpl-5182665f.py',csrc),('CHECKS.json',enc(check))]:
  path=HERE/name;assert not path.exists();path.write_bytes(data)
 proposal={'schema':1,'selection_sha256':'5f917f3521be886568e3880f63404def99a9cfaa1c0810321713f216c98d4484','entries':[{'kind':'texture','id':KEY,'sha256':OUTPUT_SHA,'provenance':'ps2','owner':'gc-catalog-proof24-root-review-pending','reason':'One exact PS2 Core.dat EFF1 f7 picture: original disc span, historical converter replay and selected full output match; root approval pending.','reviewed':False,'chain':[{'path':str(HERE/'CHECKS.json'),'sha256':sha(enc(check))},{'path':str(HERE/'historical-fx_ps2_pack-5182665f.py'),'sha256':sha(fx)},{'path':str(HERE/'historical-convert_tpl-5182665f.py'),'sha256':sha(csrc)}]}]}
 (HERE/'attestation-proposal.json').write_bytes(enc(proposal));print(json.dumps({'status':check['status'],'target':check['target'],'checks_sha256':sha(enc(check)),'proposal_sha256':sha(enc(proposal)),'elapsed_seconds':check['elapsed_seconds']},indent=2))

if __name__=='__main__':
 types_module=types
 main()