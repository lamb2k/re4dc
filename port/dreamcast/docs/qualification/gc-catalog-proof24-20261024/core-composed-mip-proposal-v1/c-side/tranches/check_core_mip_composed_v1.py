#!/usr/bin/env python3
"""Bounded composed historical Core.dat + frozen PAL4 mip replay. Metadata only.
Each output directory is new. Matches are UNAPPROVED proposals, never a catalog.
"""
import argparse,ast,collections,hashlib,importlib.util,json,os,resource,signal,struct,sys,time,types,zlib
from pathlib import Path
sys.dont_write_bytecode=True
resource.setrlimit(resource.RLIMIT_AS,(268435456,268435456));resource.setrlimit(resource.RLIMIT_CORE,(0,0));signal.alarm(120)
BASE=Path('/mnt/c/Game Dev/Emulators/codex-lanes/gc-catalog-proof24')
SPEC=importlib.util.spec_from_file_location('approved_algorithm',BASE/'origin-discovery-v1/check_core_f7_v1.py')
A=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(A)
SELECTION='5f917f3521be886568e3880f63404def99a9cfaa1c0810321713f216c98d4484'
def bounds(data,start,n,end):
 assert 0<=start<=end<=len(data) and 0<n<=end-start
 return data[start:start+n]
def pictures(e,tid):
 h=struct.unpack_from('<12I',bounds(e,0,48,len(e)));assert h[0]==11
 o,t=h[1],h[6];n=struct.unpack('<I',bounds(e,o,4,len(e)))[0];assert 0<n<4096
 assert struct.unpack('<I',bounds(e,t,4,len(e)))[0]==n
 bounds(e,o+4,8*n,len(e));bounds(e,t+4,4*n,len(e))
 entries=[(struct.unpack_from('<H',e,o+4+8*i)[0],t+struct.unpack_from('<I',e,t+4+4*i)[0]) for i in range(n)]
 found=[(i,b) for i,(x,b) in enumerate(entries) if x==tid];assert len(found)==1
 slot,base=found[0];end=min([b for _,b in entries if b>base]+[len(e)])
 magic,count,start=struct.unpack('<III',bounds(e,base,12,end));assert magic==0x1000 and 0<count<=30
 bounds(e,base+start,48*count,end);out=[];meta=[]
 for k in range(count):
  d=base+start+48*k;w,h,depth,inter=struct.unpack_from('<4H',e,d);io,po=struct.unpack_from('<2I',e,d+32)
  assert 0<w<=256 and 0<h<=256 and w*h<=16384 and w*h%2==0 and depth==8 and inter in (0,1)
  raw=bounds(e,base+io,w*h//2,end);pal=bounds(e,base+po,96,end);colors=[]
  for c in range(16):
   q=(c if c<8 else c+8)*4;r,g,b,a=pal[q:q+4];colors.append((r,g,b,255 if a>=128 else a*255//128))
  px=[colors[v] for b in raw for v in (b&15,b>>4)]
  if inter: px=[px[x*w+y] for y in range(w) for x in range(h)];w,h=h,w
  out.append((w,h,px));meta.append({'frame':k,'descriptor_offset':d,'descriptor_sha256':A.sha(e[d:d+48]),'indices_offset':base+io,'indices_bytes':len(raw),'indices_sha256':A.sha(raw),'palette_span_offset':base+po,'palette_span_bytes':96,'palette_span_sha256':A.sha(pal),'width':w,'height':h,'depth':depth,'interlace':inter,'RGBA_sha256':A.sha(bytes(v for c in px for v in c))})
 return out,{'id':tid,'slot':slot,'TPL_offset':base,'TPL_bytes':end-base,'TPL_sha256':A.sha(e[base:end]),'pictures':meta}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--ids',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
 ids=[int(x,0) for x in a.ids.split(',')];assert 0<len(ids)<=12 and len(set(ids))==len(ids)
 out=Path(a.out);assert out.parent.resolve()==(BASE/'core-tranches-v1').resolve() and not out.exists()
 started=time.monotonic();xfile=A.REPO/'port/dreamcast/tools/ps2_room_extract.py';sp=importlib.util.spec_from_file_location('extract',xfile);X=importlib.util.module_from_spec(sp);sp.loader.exec_module(X)
 with A.ISO.open('rb') as fp:
  before=A.fingerprint(os.fstat(fp.fileno()));platform=A.platform_identity(fp);index,tablehash=X.afs_index(fp);member=index['core.dat'];assert member['index']==368 and member['size']==1524064
  core=A.read_at(fp,member['offset'],member['size']);assert A.sha(core)=='c48e2165a41cb20b124a11a96e9b00bcdcd051f435475004edcc23a47e920e33'
  assert before==A.fingerprint(os.fstat(fp.fileno()))==A.fingerprint(A.ISO.stat())
 assert A.sha(bytes([core[0]^1])+core[1:])!=A.sha(core)
 n=struct.unpack_from('<I',core)[0];assert 1<n<4096;offs=struct.unpack_from('<%dI'%n,core,16);assert core[16+4*n+4:16+4*n+8].rstrip(b'\0')==b'EFF'
 eff=core[offs[1]:offs[2]];assert A.sha(eff)=='e0a571bec16baa427c4267feb59ea6ec9aa64703b833d7ed42598115c62b0124'
 fx=A.source('port/dreamcast/tools/d367/test12fx/fx_ps2_pack.py');cs=A.source('port/dreamcast/tools/convert_tpl.py')
 assert A.sha(fx)=='41d9cafee8e82bd254bad6c02e202b0f398892b7a9ba894fd7fc3aa71c9ce3d5' and A.sha(cs)=='e306b31fb8a46d2fc993c75be22ee0064454fd0d91d32135b5c5bb08b4d232c2'
 ce={'struct':struct};wanted={'MAGIC','VERSION','FORMAT_PAL4_ARGB4444','FLAG_ALPHA','FLAG_BINARY_ALPHA','PAYLOAD_TWIDDLED','HEADER','TEXTURE'}
 nodes=[v for v in ast.parse(cs).body if isinstance(v,ast.Assign) and any(isinstance(t,ast.Name) and t.id in wanted for t in v.targets)];assert len(nodes)==len(wanted)
 exec(compile(ast.Module(body=nodes,type_ignores=[]),'<exact constants>','exec'),ce)
 cf=A.exact_functions(cs,['_pack_4444','_twiddle_table','twiddle_16bpp'],ce);env={'struct':struct,'zlib':zlib,'C':types.SimpleNamespace(**ce)}
 ff=A.exact_functions(fx,['premul','palette16','package'],env)
 # Exact public conversion modules at the last PAL4-mip implementation change.
 mip_commit='0425534d848973c1dae3ab960d0006ac9afcf363';mip_sources={};mip_pins=[]
 import subprocess
 for mod in ['convert_tpl','mipmap_vq','mipmap_pal4']:
  rel='port/dreamcast/tools/'+mod+'.py';raw=subprocess.check_output(['git','-C',str(A.REPO),'show',mip_commit+':'+rel],timeout=20)
  m=types.ModuleType(mod);m.__file__='<frozen public '+mip_commit+':'+rel+'>';sys.modules[mod]=m;exec(compile(raw,m.__file__,'exec'),m.__dict__)
  mip_sources[mod]=raw;mip_pins.append({'path':rel,'sha256':A.sha(raw),'commit':mip_commit})
 mip=sys.modules['mipmap_pal4']

 indexpath=A.LIB/'INDEX.tsv';lines=indexpath.read_text().splitlines();header=lines[0].split('\t');rows=[dict(zip(header,l.split('\t'))) for l in lines[1:]]
 keypath=A.LIB/'effects-tex/KEYS.tsv';keys=[l.split('\t') for l in keypath.read_text().splitlines() if l and not l.startswith('#')]
 catalogpath=A.PRIVATE/'private-current-v1/catalog.json';assert A.sha(catalogpath.read_bytes())=='8d29e181e545ff745685412b8a2f9edf00c2dd692bb3847150575394d820b364';cat=json.loads(catalogpath.read_bytes());catalog={r['id']:r for r in cat['entries'] if r['kind']=='texture'}
 recipe=json.loads((A.PRIVATE/'private-current-v1-inputs/selection.json').read_bytes());assert A.sha((A.PRIVATE/'private-current-v1-inputs/selection.json').read_bytes())==SELECTION
 results=[];targets=[];totalpx=0;negatives=[];needed={}
 for tid in ids:
  pics,meta=pictures(eff,tid);totalpx+=sum(len(p[2]) for p in pics);assert totalpx<=262144
  gid='etc/core.das:0#1:0x%02x'%tid
  rr=[r for r in rows if r['class']=='effects-tex' and r['room']=='common' and r['gc_id']==gid];assert len(rr)==1
  row=rr[0];assert row['ps2_source']=='Core.dat:1' and row['converter']=='fx_ps2_pack.py@5182665f'
  kr=sorted([k for k in keys if len(k)==6 and k[1]=='common' and k[2]==gid],key=lambda k:int(k[3]));assert kr and [int(k[3]) for k in kr]==list(range(len(kr)))
  weights=collections.Counter(c for _,_,px in pics for c in px);pal=env['palette16'](weights);aggregate=hashlib.sha256();bytesall=0;outputs=[];seen=set()
  for k in kr:
   key=k[0];w,h,px=pics[int(k[3])%len(pics)];blob,error=env['package'](w,h,px,pal,(w,h));assert key not in seen;seen.add(key)
   aggregate.update(key.encode()+blob);bytesall+=len(blob);expected=catalog.get(key);assert expected is not None
   lib=A.LIB/'effects-tex/common'/(key+'.re4tex');libmatch=blob==lib.read_bytes();base_sha=A.sha(blob);base_bytes=len(blob);blob,mip_evidence=mip.add_mipmaps(blob,enabled=True,engine='python');selectedmatch=A.sha(blob)==expected['sha256']
   sources=expected['sources'];assert len(sources)==1 and sources[0]['asset']=='dc/tex.pak';use=sources[0]
   needed.setdefault(use['path'],[]).append((use,blob));match=libmatch and selectedmatch
   rec={'kind':'texture','id':key,'sha256':A.sha(blob),'bytes':len(blob),'frame':int(k[3]),'PS2_frame':int(k[3])%len(pics),'width':w,'height':h,'quantizer_error':error,'historical_base_sha256':base_sha,'historical_base_bytes':base_bytes,'mip_composition':mip_evidence,'historical_base_equals_existing_library':libmatch,'equals_selected_full_SHA':selectedmatch,'selected_sha256':expected['sha256'],'selected_member_offset':use['offset'],'selected_member_bytes':use['bytes'],'selected_pack_sha256':use['sha256'],'status':'MATCH_UNAPPROVED' if match else 'MISMATCH_NO_PROPOSAL'};outputs.append(rec)
   if match:targets.append(rec)
  aggregateok=aggregate.hexdigest()==row['sha256'] and bytesall==int(row['bytes'])
  # A reused lookup key/first-writer exception must not silently produce origin proposals.
  if not aggregateok:
   badkeys={r['id'] for r in outputs};targets=[r for r in targets if r['id'] not in badkeys]
   for r in outputs:r['status']='AGGREGATE_MISMATCH_NO_PROPOSAL'
  results.append({'source':meta,'INDEX_row':row,'aggregate_replayed_sha256':aggregate.hexdigest(),'aggregate_bytes':bytesall,'aggregate_receipt_match':aggregateok,'outputs':outputs})
  # Each selected ID has real-output header/key and selected-span negatives.
  bad=bytearray(blob);bad[9]^=1;assert A.sha(bad)!=A.sha(blob)
  assert A.sha(b'wrong-key'+blob)!=A.sha(key.encode()+blob)
  assert A.sha(blob[:-1])!=A.sha(blob)
  malformed=bytearray(eff);struct.pack_into('<H',malformed,meta['pictures'][0]['descriptor_offset'],0)
  try:pictures(malformed,tid)
  except AssertionError:pass
  else:raise AssertionError('malformed descriptor accepted')
  negatives.append({'id':tid,'header_swap':True,'wrong_key':True,'truncated_full_output':True,'malformed_picture':True})
 for path,items in needed.items():
  pack=Path(path);before=A.fingerprint(pack.stat())
  with pack.open('rb') as fp:
   digest=hashlib.sha256()
   for b in iter(lambda:fp.read(1048576),b''):digest.update(b)
   assert all(digest.hexdigest()==u['sha256'] and pack.stat().st_size==u['size'] for u,_ in items)
   for u,blob in items:
    selected=A.read_at(fp,u['offset'],u['bytes']);assert A.sha(selected)==next(catalog[r['id']]['sha256'] for rr in results for r in rr['outputs'] if r['selected_member_offset']==u['offset'])
    # Mismatches are recorded, never asserted away or promoted.
    for rr in results:
     for r in rr['outputs']:
      if r['selected_member_offset']==u['offset']:r['actual_selected_fullbyte_equal']=selected==blob
   assert before==A.fingerprint(os.fstat(fp.fileno()))==A.fingerprint(pack.stat())
 assert all(r['actual_selected_fullbyte_equal'] for r in targets)
 check={'schema':1,'status':'COMPOSED_MECHANICAL_MATCHES_UNAPPROVED_ROOT_REVIEW_REQUIRED','selection_sha256':SELECTION,'authority':'Standing trusted user private PS2 disc source; same exact Core.dat/EFF as root-approved f7. No independent retail certificate.','platform':platform,'source_disc':{'path':str(A.ISO),'bytes':A.ISO.stat().st_size,'afs_table_sha256':tablehash,'member':dict(member,sha256=A.sha(core)),'EFF_entry':1,'EFF_offset':offs[1],'EFF_bytes':len(eff),'EFF_sha256':A.sha(eff)},'historical_converter':{'commit':A.CONVERTER,'fx_sha256':A.sha(fx),'convert_tpl_sha256':A.sha(cs),'fx_functions':ff,'C_functions':cf,'composed_mip_modules':mip_pins,'mip_engine':'python'},'inputs':{'helper_dependency':A.pin(BASE/'origin-discovery-v1/check_core_f7_v1.py'),'INDEX':A.pin(indexpath),'KEYS':A.pin(keypath),'catalog':A.pin(catalogpath),'root_one_approval':A.pin(BASE/'origin-root-review-v1/ROOT-APPROVED-ATTESTATION.json'),'tranche_helper':A.pin(Path(__file__))},'ids':ids,'total_decoded_pixels':totalpx,'matched_proposed_identities':len(targets),'results':results,'original_source_byte_mutation_rejected':True,'negative_controls':negatives,'RAM_only_asset_bytes':True,'filesystem_asset_outputs':0,'catalog_mutated':False,'allowances_added':0,'production_pin':0,'elapsed_seconds':time.monotonic()-started,'max_address_space_bytes':268435456,'timeout_seconds':120}
 payload=A.enc(check);proposal={'schema':1,'selection_sha256':SELECTION,'entries':[{'kind':'texture','id':r['id'],'sha256':r['sha256'],'provenance':'ps2','owner':'gc-catalog-proof24-root-batch-review-pending','reason':'Exact original Core.dat pictures through historical shared-palette conversion and frozen PAL4 mip composition equal full current selected member; historical base aggregate also exact. Root batch origin approval pending.','reviewed':False,'chain':[{'path':str(out/'CHECKS.json'),'sha256':A.sha(payload)},{'path':str(BASE/'origin-discovery-v1/historical-fx_ps2_pack-5182665f.py'),'sha256':A.sha(fx)},{'path':str(BASE/'origin-discovery-v1/historical-convert_tpl-5182665f.py'),'sha256':A.sha(cs)}]+[{'path':str(out/('historical-'+mod+'-0425534d.py')),'sha256':A.sha(raw)} for mod,raw in mip_sources.items()]} for r in targets]}
 out.mkdir();
 for mod,raw in mip_sources.items():(out/('historical-'+mod+'-0425534d.py')).write_bytes(raw)
 (out/'CHECKS.json').write_bytes(payload);(out/'attestation-proposal.json').write_bytes(A.enc(proposal))
 print(json.dumps({'status':check['status'],'ids':ids,'proposed':len(targets),'all_INDEX_aggregates_match':all(r['aggregate_receipt_match'] for r in results),'full_outputs':sum(len(r['outputs']) for r in results),'decoded_pixels':totalpx,'checks_sha256':A.sha(payload),'proposal_sha256':A.sha(A.enc(proposal)),'elapsed_seconds':check['elapsed_seconds'],'peak_KiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},indent=2))
if __name__=='__main__':main()
