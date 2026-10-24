from pathlib import Path
import hashlib,json,shutil,subprocess,importlib.util,os,struct
O=Path('/root/work/lanes/water-rain24-canary-bca44-20261024');E=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/water-rain24/rain-bca44-console55-20261024');T=Path('/root/work/lanes/water-rain24');D=T/'port/dreamcast/tools/d367'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ident(p):return {'bytes':p.stat().st_size,'sha256':sha(p)}
def exact(p,b):
 if p.exists():assert p.read_bytes()==b,'existing bytes differ: '+str(p)
 else:p.write_bytes(b)
def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
iso=load(D/'fullplay/fp_iso.py','owned_iso')
def validate_mapping(cap,base,expected):
 meta=json.loads((base/'base.json').read_text());t3=iso.Track(cap/'track03.iso',45000);t1=iso.Track(cap/'track01.iso',0)
 want={'/dc/warp.txt':(400,8192,'warp'),'/dc/padscript.txt':(420,8192,'pad'),'/dc/w11.txt':(440,8192,'w11')};assert (meta['warp_lba'],meta['pad_lba'],meta['w11_lba'],meta['fixture_bytes'])==(400,420,440,8192)
 pv,sv=iso.volume_roots(t3);assert pv and sv;trees={}
 for root,joliet in [(pv,False),(sv,True)]:
  found={};outside=[]
  for path,lba,size,isdir,dlba,off in iso.walk(t3,root,joliet):
   if isdir:continue
   key=path.lower()
   if lba<45000:outside.append(key)
   if key in want:
    assert key not in found;want_lba,want_size,kind=want[key];assert (lba,size)==(want_lba,want_size)
    record=t3.read(dlba,(off+256+2047)//2048)[off:];assert struct.unpack_from('>I',record,6)[0]==lba and struct.unpack_from('>I',record,14)[0]==size
    data=t1.read_bytes(lba,size);assert data==expected[kind]+bytes(size-len(expected[kind]));found[key]={'lba':lba,'bytes':size,'backing_sha256':hashlib.sha256(data).hexdigest(),'directory_lba':dlba,'directory_offset':off}
  assert sorted(outside)==sorted(want) and set(found)==set(want);trees['joliet' if joliet else 'iso9660']=found
 # Hash EVERY actual virtual member using track1 only for the three bounded redirects.
 actual={}
 for path,lba,size in iso.files(t3):
  data=(t1 if lba<45000 else t3).read_bytes(lba,size) if size else b'';actual[path.lstrip('/')]={'size':size,'sha256':hashlib.sha256(data).hexdigest()}
 source=json.loads((base/'base-manifest.json').read_text());expectedman=dict(source)
 for key,(lba,size,kind) in want.items():expectedman[key.lstrip('/')]={'size':size,'sha256':hashlib.sha256(expected[kind]+bytes(size-len(expected[kind]))).hexdigest()}
 assert actual==expectedman,'additional virtual member drift';t1.f.close();t3.f.close()
 loader=json.loads((cap/'lint-loader.json').read_text());standard=json.loads((cap/'lint-standard.json').read_text());le=[x for x in loader['results'] if x[0]=='ERROR'];se=[x for x in standard['results'] if x[0]=='ERROR'];sd=[x for x in standard['results'] if x[0]=='STD']
 assert len(le)==len(se)==1 and le[0][1]==se[0][1]=='iso.extents'
 assert sorted(loader['facts']['hd_out_of_track'])==sorted(want) and loader['facts']['hd_overlaps']==[]
 assert sorted(standard['facts']['hd_out_of_track'])==sorted(want) and standard['facts']['hd_overlaps']==[]
 expectedstd={'std.raw2352','std.hdpad','std.toc1','std.bootlast','std.ip0000','std.ldtext'};assert {x[1] for x in sd}==expectedstd and len(sd)==len(expectedstd)
 return {'scope':'exact fp_run virtual fixture mapping only; GENERIC LINT REMAINS FAIL; not a standard/release disc pass','master_script':ident(D/'fullplay/fp_master.sh'),'fp_run_script':ident(D/'fullplay/fp_run.py'),'base_metadata':ident(base/'base.json'),'directory_trees':trees,'all_virtual_members_read_back':len(actual),'virtual_manifest_sha256':hashlib.sha256(json.dumps(actual,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'loader_errors_preserved':le,'standard_errors_preserved':se,'standard_deviations_preserved':sd,'root_review_required':True}
def main():
 report=json.loads((O/'receipt.json').read_text());assert not report['complete'] and set(report['arms'])=={'off','on'}
 assert not subprocess.check_output(['git','-C',str(T),'status','--porcelain'])
 norm=json.loads((E/'identities/profile-normalization.json').read_text());assert norm['remaining_exact_option_difference']=={'RAIN_R10C_DC':['0','1']} and norm['path_only_field_count']==75
 template=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/d367-harness-par');limited=load(Path('/mnt/c/Game Dev/Emulators/codex-lanes/world-emit23/current-stills/force_limited.py'),'limited')
 fixture=(D/'qa20/src/lake-scene5.txt').read_text().rstrip()+'\nfreeze 330\n';exact(E/'fixtures/r10c-view.txt',fixture.encode());exact(E/'fixtures/neutral-pad.txt',b'');expected={'warp':fixture.encode(),'pad':b'','w11':b''}
 for n in ['off','on']:
  cap=E/'capsules'/n;cap.mkdir(exist_ok=True);data=cap/'data';data.mkdir(exist_ok=True)
  for name in ['T0000_vmu_save_A1.bin','vmu_save_A2.bin']:
   p=template/'data'/name;assert sha(p)=='b4c5a531493665876fc72c3fcdef8ebd05fe0f7d14fb2aa73dd87d3586670b20';exact(data/name,p.read_bytes())
  exact(cap/'template-emu.cfg',(template/'emu.cfg').read_bytes());exact(cap/'limited-template-preview.cfg',limited.enforce_text((template/'emu.cfg').read_text()).encode())
  base=Path(report['arms'][n]['base']);meta=json.loads((base/'base.json').read_text());t1=bytearray((base/'track01-template.iso').read_bytes())
  for kind,lba in [('warp',400),('pad',420),('w11',440)]:t1[lba*2048:lba*2048+8192]=expected[kind]+bytes(8192-len(expected[kind]))
  exact(cap/'track01.iso',bytes(t1));exact(cap/'disc.gdi',meta['gdi'].encode())
  for name in ['track02.raw','track03.iso']:
   if not(cap/name).exists():os.link(base/name,cap/name)
   assert sha(cap/name)==sha(base/name)
  for profile in ['loader','standard']:
   log=cap/('lint-'+profile+'.log');result=cap/('lint-'+profile+'.json')
   if not log.exists():
    p=subprocess.run(['python3',str(D/'disc_lint.py'),str(cap/'disc.gdi'),'--profile',profile,'--json',str(result)],capture_output=True,text=True,timeout=60);log.write_text(p.stdout+p.stderr)
  mapping=validate_mapping(cap,base,expected);exact(cap/'virtual-mapping-validation.json',(json.dumps(mapping,indent=2)+'\n').encode())
  report['arms'][n]['capsule']={'path':str(cap),'members':{str(p.relative_to(cap)):ident(p) for p in cap.rglob('*') if p.is_file()},'mapping_validation':ident(cap/'virtual-mapping-validation.json'),'generic_lint_pass':False,'root_mapping_review_required':True,'config_preview_not_actual_guest_cfg':True}
 report.update(resolved_differences=norm['remaining_exact_option_difference'],profile_normalization_receipt=ident(E/'identities/profile-normalization.json'),fixtures={p.name:ident(p) for p in (E/'fixtures').iterdir()},guests_started=0,complete=True,stage_complete_guests_blocked_pending_root_preflight=True,metadata_correction_no_rebuild=True,free_after=shutil.disk_usage('/mnt/c').free)
 seen=set();owned=0
 for root in [O,E,T/'port/dreamcast/game/obj']:
  for p in root.rglob('*'):
   if p.is_file() and not p.is_symlink():
    s=p.stat();k=s.st_dev,s.st_ino
    if k not in seen:seen.add(k);owned+=s.st_size
 assert owned<=report['new_total_cap_bytes'] and report['free_after']>=report['floor_bytes'];report['final_unique_owned_bytes']=owned
 (O/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');(E/'identities/preparation-receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'complete':True,'guests':0,'profile_fields_path_only':75,'remaining':report['resolved_differences'],'unique_owned_bytes':owned,'free':report['free_after'],'receipt_sha256':sha(O/'receipt.json')}))
if __name__=='__main__':main()