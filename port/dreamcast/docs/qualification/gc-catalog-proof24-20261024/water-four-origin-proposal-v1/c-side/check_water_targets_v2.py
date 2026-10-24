#!/usr/bin/env python3
"""Four exact member+EFF+picture water origin candidates. RAM-only asset bytes.
Historical lookup mappings establish selected stored identities, NOT live Entry/use.
"""
import argparse,ast,collections,hashlib,importlib.util,json,os,resource,signal,struct,subprocess,sys,time,types,zlib
from pathlib import Path
sys.dont_write_bytecode=True
resource.setrlimit(resource.RLIMIT_AS,(268435456,268435456));resource.setrlimit(resource.RLIMIT_CORE,(0,0));signal.alarm(120)
BASE=Path('/mnt/c/Game Dev/Emulators/codex-lanes/gc-catalog-proof24');HERE=BASE/'water-target-origin-v1'
sp=importlib.util.spec_from_file_location('prior',BASE/'core-tranches-v1/check_core_tranche_v1.py');G=importlib.util.module_from_spec(sp);sp.loader.exec_module(G);A=G.A
RECEIPT=Path('/mnt/c/Game Dev/Emulators/codex-lanes/water-coverage24/R100-TARGET-SOURCE-INPUTS.json');RECEIPT_SHA='e701f9bad3af2d5790ca70edeb483ff37854a7cbeadba2c7dbd01034552fa8aa'
OLD='5182665f6d6b62aee348e58266c015c891da5d85';GSREV='952e8fbfce071e54ca251f09ed4d4793a23ac51e';MIPREV='0425534d848973c1dae3ab960d0006ac9afcf363'
CASES=[('Core.dat',1,0x56,'common','etc/core.das:0#1:0x56','13780699-289fc370',GSREV),('Core.dat',1,0x1d,'common','etc/core.das:0#1:0x1d','441a0cca-10da6929',GSREV),('Core.dat',1,0xfc,'common','etc/core.das:0#1:0xfc','4aaa2a61-69bd273d',GSREV),('r100.dat',6,0xca,'r100','st1/r100.arc#8:0xca','8b8bf3d6-0277ae15',OLD)]
def git_source(rev,rel):return subprocess.check_output(['git','-C',str(A.REPO),'show',rev+':'+rel],timeout=20)
def load_module(name,raw):
 m=types.ModuleType(name);m.__file__='<frozen public '+name+'>';sys.modules[name]=m;exec(compile(raw,m.__file__,'exec'),m.__dict__);return m
def selected(e,tid,GS):
 h=struct.unpack_from('<12I',G.bounds(e,0,48,len(e)));assert h[0]==11;o,t=h[1],h[6];n=struct.unpack('<I',G.bounds(e,o,4,len(e)))[0];assert 0<n<4096 and struct.unpack('<I',G.bounds(e,t,4,len(e)))[0]==n
 G.bounds(e,o+4,8*n,len(e));G.bounds(e,t+4,4*n,len(e));ents=[(struct.unpack_from('<H',e,o+4+8*i)[0],t+struct.unpack_from('<I',e,t+4+4*i)[0]) for i in range(n)]
 found=[(i,b) for i,(x,b) in enumerate(ents) if x==tid];assert len(found)==1;slot,b=found[0];end=min([v for _,v in ents if v>b]+[len(e)])
 magic,count,start=struct.unpack('<III',G.bounds(e,b,12,end));assert magic==4096 and count==1;d=b+start;descriptor=G.bounds(e,d,48,end);w,h,depth,inter=struct.unpack_from('<4H',descriptor);io,po=struct.unpack_from('<2I',descriptor,32)
 assert w in (128,256) and h==w and depth==8 and inter in (0,2);raw=G.bounds(e,b+io,w*h//2,end);pal=G.bounds(e,b+po,96,end)
 # Exact public GS address decoder; bounded selection corresponds to historical high-level decoder's PSMT4 branch.
 indices=list(GS.unswizzle_gs(raw,w,h,4)) if inter&2 else [v for v in raw for v in (v&15,v>>4)];assert len(indices)==w*h
 colors=[]
 for c in range(16):
  q=(c if c<8 else c+8)*4;r,g,bb,a=pal[q:q+4];colors.append((r,g,bb,255 if a>=128 else a*255//128))
 pixels=[colors[i] for i in indices]
 return (w,h,pixels),{'texture':tid,'slot':slot,'tpl_offset':b,'tpl_bytes':end-b,'tpl_sha256':A.sha(e[b:end]),'descriptor_offset':d,'descriptor_sha256':A.sha(descriptor),'pixels_offset':b+io,'pixels_bytes':len(raw),'pixels_sha256':A.sha(raw),'palette_offset':b+po,'palette_bytes':96,'palette_sha256':A.sha(pal),'width':w,'height':h,'depth':depth,'interlace':inter,'decoded_indices_sha256':A.sha(bytes(indices)),'decoded_RGBA_sha256':A.sha(bytes(v for c in pixels for v in c))}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);args=ap.parse_args();out=Path(args.out);assert out.parent.resolve()==HERE.resolve() and not out.exists();start=time.monotonic()
 assert A.sha(RECEIPT.read_bytes())==RECEIPT_SHA;input_receipt=json.loads(RECEIPT.read_bytes());source_pins={};frozen={}
 # Public source only, never a generated/private asset file.
 gsraw=git_source(GSREV,'port/dreamcast/tools/d367/test12fx/ps2_tpl_decode.py');GS=load_module('water_historical_GS',gsraw);frozen['ps2_tpl_decode-'+GSREV[:8]+'.py']=gsraw
 ce={};envs={};function_pins={}
 for rev in (OLD,GSREV):
  cs=git_source(rev,'port/dreamcast/tools/convert_tpl.py');fx=git_source(rev,'port/dreamcast/tools/d367/test12fx/fx_ps2_pack.py');cenv={'struct':struct};wanted={'MAGIC','VERSION','FORMAT_PAL4_ARGB4444','FLAG_ALPHA','FLAG_BINARY_ALPHA','PAYLOAD_TWIDDLED','HEADER','TEXTURE'}
  nodes=[n for n in ast.parse(cs).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in wanted for t in n.targets)];assert len(nodes)==len(wanted);exec(compile(ast.Module(body=nodes,type_ignores=[]),'<exact constants>','exec'),cenv)
  cfun=A.exact_functions(cs,['_pack_4444','_twiddle_table','twiddle_16bpp'],cenv);env={'struct':struct,'zlib':zlib,'C':types.SimpleNamespace(**cenv)};ffun=A.exact_functions(fx,['premul','palette16','package'],env);envs[rev]=env;function_pins[rev]={'fx_functions':ffun,'C_functions':cfun}
  frozen['fx_ps2_pack-'+rev[:8]+'.py']=fx;frozen['convert_tpl-'+rev[:8]+'.py']=cs
 for name in ['convert_tpl','mipmap_vq','mipmap_pal4','mipmap_twiddled','compact_native_vq']:
  raw=git_source(MIPREV,'port/dreamcast/tools/'+name+'.py');load_module(name,raw);frozen[name+'-'+MIPREV[:8]+'.py']=raw
 M=sys.modules['mipmap_pal4'];V=sys.modules['mipmap_vq'];Compact=sys.modules['compact_native_vq'];members={};platform=None
 xspec=importlib.util.spec_from_file_location('extract',A.REPO/'port/dreamcast/tools/ps2_room_extract.py');X=importlib.util.module_from_spec(xspec);xspec.loader.exec_module(X)
 with A.ISO.open('rb') as fp:
  before=A.fingerprint(os.fstat(fp.fileno()));assert A.ISO.stat().st_size==input_receipt['iso_bytes'];platform=A.platform_identity(fp);index,tablehash=X.afs_index(fp)
  for name,expected in input_receipt['members'].items():
   member=index[name.lower()];assert member['offset']==expected['offset'] and member['size']==expected['bytes'];raw=A.read_at(fp,member['offset'],member['size']);assert A.sha(raw)==expected['sha256']
   n=struct.unpack('<I',G.bounds(raw,0,4,len(raw)))[0];assert 1<n<4096;G.bounds(raw,16,8*n,len(raw));offs=struct.unpack_from('<%dI'%n,raw,16);entry=expected['eff_entry'];assert 0<=entry<n and raw[16+4*n+4*entry:20+4*n+4*entry].rstrip(b'\0')==b'EFF';end=offs[entry+1] if entry+1<n else len(raw);eff=G.bounds(raw,offs[entry],end-offs[entry],len(raw));assert len(eff)==expected['eff_bytes'] and A.sha(eff)==expected['eff_sha256'];members[(name,entry)]=eff
   source_pins[name]={'member':dict(member,sha256=A.sha(raw)),'eff_entry':entry,'eff_offset_in_DAT':offs[entry],'eff_offset_in_ISO':member['offset']+offs[entry],'eff_bytes':len(eff),'eff_sha256':A.sha(eff)}
  assert before==A.fingerprint(os.fstat(fp.fileno()))==A.fingerprint(A.ISO.stat())
 catalogpath=A.PRIVATE/'private-current-v1/catalog.json';assert A.sha(catalogpath.read_bytes())=='8d29e181e545ff745685412b8a2f9edf00c2dd692bb3847150575394d820b364';catalog={r['id']:r for r in json.loads(catalogpath.read_bytes())['entries'] if r['kind']=='texture'}
 indexpath=A.LIB/'INDEX.tsv';lines=indexpath.read_text().splitlines();head=lines[0].split('\t');rows=[dict(zip(head,l.split('\t'))) for l in lines[1:]];keypath=A.LIB/'effects-tex/KEYS.tsv';keys=[l.split('\t') for l in keypath.read_text().splitlines()]
 outputs=[];needed=[];negative=[]
 for member,entry,tid,room,ctx,key,rev in CASES:
  eff=members[(member,entry)];(w,h,pixels),picture=selected(eff,tid,GS);expected=[r for r in input_receipt['textures'] if (r['member'],r['eff_entry'],r['texture'])==(member,entry,tid)];assert len(expected)==1;assert len(expected[0]['pictures'])==1
  original=expected[0]['pictures'][0]
  for field in ['tpl_offset']:assert picture[field]==expected[0][field]
  for field in ['descriptor_offset','descriptor_sha256','pixels_offset','pixels_bytes','pixels_sha256','palette_offset','palette_bytes','palette_sha256','width','height','depth','interlace']:assert picture[field]==original[field]
  env=envs[rev];palette=env['palette16'](collections.Counter(pixels));base,error=env['package'](w,h,pixels,palette,(w,h));lib=A.LIB/'effects-tex'/room/(key+'.re4tex');libmatch=base==lib.read_bytes()
  rr=[r for r in rows if r['class']=='effects-tex' and r['room']==room and r['gc_id']==ctx];assert len(rr)==1;row=rr[0];assert row['ps2_source']==member+':'+str(entry);aggregate=A.sha(key.encode()+base);aggregateok=aggregate==row['sha256'] and len(base)==int(row['bytes'])
  kr=[r for r in keys if len(r)==6 and r[0]==key and r[1]==room and r[2]==ctx];assert len(kr)==1 and kr[0][3]=='0'
  selectedrow=catalog[key];assert len(selectedrow['sources'])==1;use=selectedrow['sources'][0];assert use['asset']=='dc/tex.pak';composed,mip_evidence=M.add_mipmaps(base,enabled=True,engine='python')
  compact,compact_evidence=Compact.compact(base,enabled=True);compact_mip,compact_mip_evidence=V.add_mipmaps(compact,enabled=True,engine='python') if compact_evidence['changed'] else (compact,None)
  candidates=[('direct',base),('composed_mip',composed),('lossless_vq',compact),('lossless_vq_mip',compact_mip)];found=[(label,blob) for label,blob in candidates if A.sha(blob)==selectedrow['sha256']];variant,final=found[0] if found else ('unmatched',composed);needed.append((use,final));matched=variant!='unmatched' and libmatch and aggregateok
  # A linear substitute for the actual GS-swizzled picture must fail its output hash.
  if picture['interlace']==2:
   altered=bytearray(eff);struct.pack_into('<H',altered,picture['descriptor_offset']+6,0);(_,_,badpixels),_=selected(altered,tid,GS);badpal=env['palette16'](collections.Counter(badpixels));bad,_=env['package'](w,h,badpixels,badpal,(w,h));assert bad!=base;negative.append({'member':member,'entry':entry,'texture':tid,'ignored_GS_swizzle_changes_full_output':True})
  bad=bytearray(final);bad[-1]^=1;assert A.sha(bad)!=A.sha(final)
  # Wrong EFF/member are not accepted by the exact tuple, even where an ID recurs.
  wrong_entry=entry+1;assert (member,wrong_entry,tid) not in {(r['member'],r['eff_entry'],r['texture']) for r in input_receipt['textures']}
  outputs.append({'member':member,'eff_entry':entry,'picture':picture,'historical_lookup_context':ctx,'lookup_key':key,'kind':'texture','id':key,'sha256':A.sha(final),'bytes':len(final),'base_bytes':len(base),'base_sha256':A.sha(base),'historical_converter_commit':rev,'historical_library_fullbyte_equal':libmatch,'historical_INDEX_row':row,'historical_aggregate_sha256':aggregate,'historical_aggregate_exact':aggregateok,'KEYS_row':kr[0],'selected':dict(use,full_payload_sha256=selectedrow['sha256']),'variant':variant,'mip_composition':mip_evidence if variant=='composed_mip' else None,'lossless_vq_composition':compact_evidence if variant.startswith('lossless_vq') else None,'lossless_vq_mip_composition':compact_mip_evidence if variant=='lossless_vq_mip' else None,'quantizer_error':error,'status':'MATCH_UNAPPROVED' if matched else 'UNMATCHED_NO_PROPOSAL','current_full_SHA_equal':A.sha(final)==selectedrow['sha256'],'runtime_resolved_Entry_or_recipe_correspondence_proved':False})
 assert len({u['path'] for u,_ in needed})==1;pack=Path(needed[0][0]['path']);before=A.fingerprint(pack.stat())
 with pack.open('rb') as fp:
  digest=hashlib.sha256()
  for block in iter(lambda:fp.read(1048576),b''):digest.update(block)
  assert digest.hexdigest()=='5bba464a1175d8ebe153d5aecb629ea9637807c2bf4fc438a32c17148d0729da'
  for result,(use,blob) in zip(outputs,needed):
   assert use['sha256']==digest.hexdigest() and use['size']==pack.stat().st_size;selectedbytes=A.read_at(fp,use['offset'],use['bytes']);assert A.sha(selectedbytes)==result['selected']['full_payload_sha256'];result['actual_selected_fullbyte_equal']=blob==selectedbytes
   assert result['status']!='MATCH_UNAPPROVED' or result['actual_selected_fullbyte_equal']
  assert before==A.fingerprint(os.fstat(fp.fileno()))==A.fingerprint(pack.stat())
 check={'schema':1,'status':'WATER_TARGET_STORED_IDENTITIES_ONLY_ROOT_REVIEW_PENDING','source_input_receipt':{'path':str(RECEIPT),'sha256':RECEIPT_SHA},'helper':A.pin(Path(__file__)),'dependencies':[A.pin(BASE/'origin-discovery-v1/check_core_f7_v1.py'),A.pin(BASE/'core-tranches-v1/check_core_tranche_v1.py')],'selection_sha256':'5f917f3521be886568e3880f63404def99a9cfaa1c0810321713f216c98d4484','platform':platform,'afs_table_sha256':tablehash,'source_members':source_pins,'historical_function_pins':function_pins,'frozen_public_sources':[{'path':name,'sha256':A.sha(raw),'bytes':len(raw)} for name,raw in frozen.items()],'lookup_receipts':{'INDEX':A.pin(indexpath),'KEYS':A.pin(keypath)},'results':outputs,'negative_controls':negative,'all_final_byte_mutations_rejected':True,'wrong_EFF_member_tuples_rejected':True,'matched_identities':sum(r['status']=='MATCH_UNAPPROVED' for r in outputs),'origin_authority':'Original exact user PS2 disc spans; root standing source authority accepted only f7 so far, these four proposals still require root review. No retail authenticity certificate.','limitations':['Stored selected pack identity is not actual active Entry key/payload, EST assignment or emission proof.','No GC recipe, animation/material/target/runtime lifetime equivalence proved.','Historical UNGATED records are locators only, not guest/look acceptance.'],'asset_bytes_RAM_only':True,'asset_files_written':0,'production_pin':0,'allowances_added':0,'elapsed_seconds':time.monotonic()-start,'peak_KiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'AS_limit':268435456,'timeout_seconds':120}
 payload=A.enc(check);proposal={'schema':1,'selection_sha256':check['selection_sha256'],'entries':[{'kind':'texture','id':r['id'],'sha256':r['sha256'],'provenance':'ps2','owner':'gc-catalog-proof24-water-root-review-pending','reason':'Exact original member+EFF+picture receipt, frozen historical GS/PSMT4 conversion and complete selected stored output match; no active Entry/recipe proof. Root origin review pending.','reviewed':False,'chain':[{'path':str(out/'CHECKS.json'),'sha256':A.sha(payload)}]+[{'path':str(out/name),'sha256':A.sha(raw)} for name,raw in frozen.items()]} for r in outputs if r['status']=='MATCH_UNAPPROVED']}
 out.mkdir()
 for name,raw in frozen.items():(out/name).write_bytes(raw)
 (out/'CHECKS.json').write_bytes(payload);(out/'ATTESTATION-PROPOSAL.json').write_bytes(A.enc(proposal));print(json.dumps({'matched':check['matched_identities'],'results':[{'source':r['member']+':'+str(r['eff_entry'])+':'+hex(r['picture']['texture']),'id':r['id'],'variant':r['variant'],'status':r['status'],'sha256':r['sha256']} for r in outputs],'checks_sha256':A.sha(payload),'proposal_sha256':A.sha(A.enc(proposal)),'elapsed_seconds':check['elapsed_seconds'],'peak_KiB':check['peak_KiB']},indent=2))
if __name__=='__main__':main()
