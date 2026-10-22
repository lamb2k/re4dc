"""One explicitly invoked fixed-program guest. Source/mock development invokes no main.
Preflight is read-only. No automatic retry/chained guest/image writers/ELF copies.
"""
import argparse,datetime,hashlib,importlib.util,json,os,pathlib,re,shutil,subprocess,sys,time
P=pathlib.Path(__file__).parent;GiB=1024**3;MiB=1024**2;ADMISSION=18*GiB+128*MiB;RUNTIME=18*GiB+64*MiB;CAP=60000000
SOURCE='c57ff60f0f462fdd2c419883b0258963504d756a';PROGRAM='52190ed293d8e62238bcad40fd351d35a965b253ad5b59cda570d0de34187e45';ELF='248dd4aac7c4e22a7a18a0183fc6409401fddf610d98881c90dd9664e342640b';IMAGE='da10104f6d4e28c6e4509a9fb75182fc4612f89a411ed4c1efa85d8a6c8bde7f'
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def no_alias(path):
 path=pathlib.Path(path)
 if path.resolve()!=path.absolute():raise RuntimeError('ancestor/path alias refused BEFORE metadata: '+str(path))
 return path

def hash_file(path,guard=lambda:None):
 h=hashlib.sha256()
 with pathlib.Path(path).open('rb') as f:
  while True:
   guard();data=f.read(8*MiB)
   if not data:break
   h.update(data)
 return h.hexdigest()

def fixed_profile(profile):
 f=profile['fixed_runtime'];d=profile['disc'];limits=profile['limits']
 if (f['source'],f['program_sha256'],f['elf_sha256'],d['files']['track03.iso']['sha256'])!=(SOURCE,PROGRAM,ELF,IMAGE):raise RuntimeError('wrong exact fixed programme')
 if len(f['all14'])!=14:raise RuntimeError('overlay set incomplete')
 expected={'inner_seconds':41,'input_cutoff_seconds':40.75,'absolute_actual_seconds':47.5,'independent_conservative_private_job_seconds':47.0,'evidence_bytes':CAP,'disk_admission':ADMISSION,'disk_runtime':RUNTIME,'global_admission':'<16','global_runtime':'<=16','max_PNG':8,'periodic_capture':0}
 if limits!=expected:raise RuntimeError('resource/guest bounds changed')
 if pathlib.Path(profile['evidence_root'])!=pathlib.Path('C:/Flycast-Evidence/re4-dreamcast/qa21-ganado-reader-guests-20261021'):raise RuntimeError('unowned evidence root')
 return profile

def native_file_id(path):
 text=subprocess.check_output(['fsutil','file','queryfileid',str(path)],text=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=3);ids=re.findall(r'0x[0-9a-fA-F]+',text)
 if len(ids)!=1:raise RuntimeError('native source fileID unavailable')
 return int(ids[0],16)

def preflight(profile,guard,native_id=native_file_id):
 fixed_profile(profile);disc=no_alias(profile['disc']['path']);stage=disc.parents[1];records={}
 for name,row in profile['disc']['stage_receipts'].items():
  actual=hash_file(no_alias(stage/name),guard)
  if actual!=row:raise RuntimeError('sealed stage receipt changed: '+name)
 for name,row in profile['disc']['files'].items():
  f=no_alias(disc/name)
  if f.stat().st_size!=row['bytes'] or hash_file(f,guard)!=row['sha256']:raise RuntimeError('disc identity changed: '+name)
  records[name]={'sha256':row['sha256'],'bytes':row['bytes']}
 image=disc/'track03.iso';expected=int(profile['disc']['files']['track03.iso']['native_id'],16)
 if native_id(image)!=expected or image.stat().st_nlink!=1:raise RuntimeError('image replacement/shared handle lineage: fileID/linkcount')
 if hash_file(no_alias(profile['elf_path']),guard)!=ELF:raise RuntimeError('ELF changed; no copies permitted')
 if hash_file(no_alias(profile['observer']['layout']),guard)!=profile['observer']['layout_sha256']:raise RuntimeError('DWARF changed')
 for name,row in profile['retained_dependencies'].items():
  if hash_file(no_alias(row['path']),guard)!=row['sha256']:raise RuntimeError('dependency changed: '+name)
 root=no_alias(profile['template']['path']);expected_data={n for n in profile['template']['files'] if n.startswith('data/')};actual_data={'data/'+str(f.relative_to(root/'data')).replace('\\','/') for f in (root/'data').rglob('*') if f.is_file()}
 if actual_data!=expected_data:raise RuntimeError('unexpected template save/data; cold must not inherit a state')
 for name,row in profile['template']['files'].items():
  if hash_file(no_alias(root/name),guard)!=row['sha256']:raise RuntimeError('template changed: '+name)
 own=json.loads((P/'source-manifest.json').read_text())
 for name,row in own['files'].items():
  if hash_file(no_alias(P/name),guard)!=row['sha256']:raise RuntimeError('own reviewed source/metadata changed: '+name)
 return records

def validate_seed(profile,mode,seed,profile_sha):
 if mode=='cold-shoot01':
  if seed is not None:raise RuntimeError('cold forbids saved state')
  return
 parent='cold-shoot01' if mode=='return-door01' else 'return-door01'
 root=no_alias(profile['evidence_root']);expected=no_alias(root/parent)
 if seed is None or no_alias(seed)!=expected:raise RuntimeError('only exact owned new-program parent allowed')
 receipt=json.loads((root/(parent+'-control')/'qualification.json').read_text())
 if receipt.get('qualified') is not True or receipt.get('profile_sha256')!=profile_sha or receipt.get('program_sha256')!=PROGRAM:raise RuntimeError('parent not qualified with exact programme/profile')

def output_paths(profile,mode):
 root=no_alias(profile['evidence_root']);cap=no_alias(root/mode);control=no_alias(root/(mode+'-control'))
 if cap.exists() or control.exists():raise RuntimeError('preserve existing output; no retry/overwrite')
 marker=root/'OWNED-BY.json';identity={'lane':'qa21-combined-regression','programme':PROGRAM,'image':IMAGE}
 if root.exists():
  if not marker.is_file() or json.loads(marker.read_text())!=identity:raise RuntimeError('output root ownership marker differs')
 else:
  root.mkdir(parents=False);marker.write_text(json.dumps(identity,indent=2)+'\n')
 control.mkdir();return cap,control,marker

def postflight(profile,cap,control,backend,result):
 def guard():
  if backend.free()<RUNTIME:raise RuntimeError('postguest runtime floor')
  if backend.evidence_bytes()+MiB>=CAP:raise RuntimeError('postguest receipt/checkpoint headroom')
 guard();result['postflight_disc']=preflight(profile,guard)
 run=json.loads((cap/'run-result.json').read_text());state=json.loads((cap/'inner-control.json').read_text());result['inner']=state
 if run.get('status')!='RUN_COMPLETE' or run.get('checkpoint_close_timeout') or 'reader_exit' in run or 'early_emulator_exit' in run or run.get('errors') or state.get('errors'):raise RuntimeError('runner/control close not clean')
 if state['mode']=='cold-shoot01' and (len(state.get('discharges',[]))!=2 or not all(r.get('accepted') for r in state['discharges'])):raise RuntimeError('two actual ordinary discharges not established; partial preserved')
 if state['mode']=='return-door01' and (not state.get('original_manual_witness') or (state.get('last') or {}).get('global',{}).get('room')!=0x101):raise RuntimeError('ordinary door/manual witness missing')
 if state['mode']=='cinematic01':
  labels=[w.get('capture') for w in state.get('witnesses',[])]
  if not all(n in labels for n in ['reciprocal-catch','life-zero','death-demo-start']):raise RuntimeError('actual catch/death/native-demo witness missing; partial preserved')
 # Preserve any natural terminal state; seal entire data only after guest/job closed.
 (cap/'ownership-resource-guard.json').write_text(json.dumps(result,indent=2)+'\n');guard()
 checkpoint=load('checkpoint',profile['retained_dependencies']['checkpoint.py']['path']);disc_identity={'files':{n:r['sha256'] for n,r in profile['disc']['files'].items()},'program_sha256':PROGRAM,'elf_sha256':ELF}
 parent=state.get('checkpoint_parent');result['checkpoint']=checkpoint.seal(cap,profile['elf_path'],profile['observer']['binding'],profile['observer']['layout'],disc_identity,parent)
 guard()

def main():
 if os.name!='nt':raise RuntimeError('Windows runtime only')
 ap=argparse.ArgumentParser();ap.add_argument('--profile',type=pathlib.Path,required=True);ap.add_argument('--profile-sha256',required=True);ap.add_argument('--tools-sha256',required=True);ap.add_argument('--mode',choices=['cold-shoot01','return-door01','cinematic01'],required=True);ap.add_argument('--seed',type=pathlib.Path);a=ap.parse_args()
 if hash_file(no_alias(a.profile))!=a.profile_sha256:raise RuntimeError('reviewed profile hash changed')
 if hash_file(no_alias(P/'source-manifest.json'))!=a.tools_sha256:raise RuntimeError('reviewed source manifest hash changed')
 manifest=json.loads((P/'source-manifest.json').read_text())
 for name,row in manifest['files'].items():
  if hash_file(no_alias(P/name))!=row['sha256']:raise RuntimeError('reviewed source changed before imports: '+name)
 profile=fixed_profile(json.loads(a.profile.read_text()));adapter=load('adapter',P/'inner-adapter.py');adapter.validate_role(profile,a.mode,a.seed);validate_seed(profile,a.mode,a.seed,a.profile_sha256)
 core=load('core',P/'guest-supervisor-core.py');backend_type=load('backend',P/'windows-backend.py').WindowsBackend;footprint_row=profile['retained_dependencies']['evidence_footprint.py']
 if hash_file(no_alias(footprint_row['path']))!=footprint_row['sha256']:raise RuntimeError('footprint helper changed before import')
 footprint=load('footprint',footprint_row['path'])
 root=no_alias(profile['evidence_root']);provisionalcap=root/a.mode;provisionalcontrol=root/(a.mode+'-control');backend=backend_type(provisionalcap,provisionalcontrol,profile['disc']['path'],profile['template']['files']['flycast.exe']['sha256'],footprint)
 def guard():
  if backend.free()<RUNTIME:raise RuntimeError('read-only preflight floor')
 pre=preflight(profile,guard)
 # Fresh admission AFTER all hashes, BEFORE output metadata/release. Monitor repeats it.
 if backend.free()<ADMISSION or backend.global_count()>=16:raise RuntimeError('fresh resource admission before output')
 cap,control,marker=output_paths(profile,a.mode);backend.marker_bytes=max(marker.stat().st_size,4096)
 cmd=[sys.executable,str(P/'inner-adapter.py'),'--profile',str(a.profile),'--mode',a.mode,'--cap',str(cap)]
 if a.seed:cmd+=['--seed',str(no_alias(a.seed))]
 started=datetime.datetime.now(datetime.timezone.utc).isoformat();result=core.monitor(backend,cmd)
 result.update(scope='automatic source/runtime gates only; PNG visual review/Continue/ordinary gameplay remain separately observed acceptance',tools_sha256=a.tools_sha256,cinematic_visual_review=False,Continue_acceptance=False,started_utc=started,mode=a.mode,profile_sha256=a.profile_sha256,preflight_disc=pre,source=SOURCE,program_sha256=PROGRAM,elf_sha256=ELF,image_sha256=IMAGE,memory_writes=False,retry=False)
 try:
  if result['qualified']:postflight(profile,cap,control,backend,result)
 except BaseException as error:result.update(qualified=False,postflight_error=type(error).__name__+': '+str(error))
 finally:
  # Metadata failure never causes another guest/copy; partial evidence stays in place.
  (control/'qualification.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'qualified':result['qualified'],'control':str(control),'mode':a.mode}));raise SystemExit(0 if result['qualified'] else 1)
if __name__=='__main__':main()
