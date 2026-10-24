from pathlib import Path
import hashlib,json,shutil,subprocess,importlib.util,datetime
O=Path('/root/work/lanes/water-rain24-canary-bca44-20261024');E=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/water-rain24/rain-bca44-console55-20261024');T=Path('/root/work/lanes/water-rain24');D=T/'port/dreamcast/tools/d367';C=Path('/mnt/c/Game Dev/Emulators/codex-lanes/water-rain24')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ident(p):return {'bytes':p.stat().st_size,'sha256':sha(p)}
def values(path):return dict(line.split('=',1) for line in path.read_text().splitlines() if '=' in line and not line.startswith('#'))
def normalize(value,root):
 start=0
 while (at:=value.find(root,start))>=0:
  end=at+len(root);assert end==len(value) or value[end] in '/ \t\n\'"','non-boundary path prefix refused';start=end
 return value.replace(root,'<OWNED_ARM_OUT>')
def main():
 report=json.loads((O/'receipt.json').read_text());assert not report['complete'] and set(report['arms'])=={'off','on'}
 assert subprocess.check_output(['git','-C',str(T),'rev-parse','HEAD'],text=True).strip()==report['source'];assert not subprocess.check_output(['git','-C',str(T),'status','--porcelain'])
 refusal=E/'identities/original-preparation-refusal.json';assert not refusal.exists()
 shutil.copyfile(O/'receipt.json',E/'identities/preparation-before-path-normalization.json');shutil.copyfile(C/'prepare-canary-bca44-20261024.py',E/'identities/prepare-original-v1.py')
 roots={n:str(Path(report['arms'][n]['out'])) for n in ['off','on']};a,b=[values(Path(report['arms'][n]['out'])/'resolved-knobs.txt') for n in ['off','on']];assert set(a)==set(b)
 normalized=[];remaining={}
 for key in sorted(a):
  x,y=normalize(a[key],roots['off']),normalize(b[key],roots['on'])
  if a[key]!=b[key] and x==y:normalized.append({'field':key,'off_literal_count':a[key].count(roots['off']),'on_literal_count':b[key].count(roots['on']),'off_raw_sha256':hashlib.sha256(a[key].encode()).hexdigest(),'on_raw_sha256':hashlib.sha256(b[key].encode()).hexdigest(),'normalized_value_sha256':hashlib.sha256(x.encode()).hexdigest()})
  if x!=y:remaining[key]=[x,y]
 assert remaining=={'RAIN_R10C_DC':['0','1']},list(remaining)
 # Actual filter06 compile target macro propagation, with no arbitrary CXXFLAGS deletion.
 commands={}
 for n in ['off','on']:
  text=(O/'programmes'/(n+'-g/build.log')).read_text();lines=[line for line in text.splitlines() if ' -c ' in line and 'filter06.cpp' in line and ' -o ' in line];assert len(lines)==1
  import shlex
  commands[n]=[normalize(v,roots[n]) for v in shlex.split(lines[0])]
 token='-DRE4DC_RAIN_R10C_DC=1';assert commands['off'].count(token)==0 and commands['on'].count(token)==1
 assert [x for x in commands['on'] if x!=token]==commands['off']
 norm={'scope':'metadata-only correction; no build/stage rerun','allowed_literal_roots':roots,'replacement':'<OWNED_ARM_OUT>','boundary_checked':True,'raw_differing_field_count':len(normalized)+len(remaining),'path_only_field_count':len(normalized),'all_path_only_fields':normalized,'remaining_exact_option_difference':remaining,'derived_macro_normalization_fields':[],'actual_filter06_compile':{'off_tokens':commands['off'],'on_tokens':commands['on'],'sole_added_exact_token':token},'no_definitions_or_fields_dropped':True}
 refusal.write_text(json.dumps({'status':'PRESERVED_ORIGINAL_POST-STAGE_METADATA_REFUSAL','reason':'v1 compared literal full Make values including distinct owned OBJDIR paths; compiler/stage succeeded','original_source':ident(E/'identities/prepare-original-v1.py'),'original_receipt':ident(E/'identities/preparation-before-path-normalization.json'),'raw_differing_field_count':norm['raw_differing_field_count'],'path_only_field_count':len(normalized),'remaining_option_only':remaining},indent=2)+'\n');(E/'identities/profile-normalization.json').write_text(json.dumps(norm,indent=2)+'\n')
 source=D/'qa20/src/lake-scene5.txt';fixture=source.read_text().rstrip()+'\nfreeze 330\n';(E/'fixtures/r10c-view.txt').write_text(fixture);(E/'fixtures/neutral-pad.txt').write_text('')
 template=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/d367-harness-par');limited=Path('/mnt/c/Game Dev/Emulators/codex-lanes/world-emit23/current-stills/force_limited.py');spec=importlib.util.spec_from_file_location('limited',limited);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 for n in ['off','on']:
  capsule=E/'capsules'/n;capsule.mkdir();data=capsule/'data';data.mkdir()
  for name in ['T0000_vmu_save_A1.bin','vmu_save_A2.bin']:
   p=template/'data'/name;assert sha(p)=='b4c5a531493665876fc72c3fcdef8ebd05fe0f7d14fb2aa73dd87d3586670b20';shutil.copyfile(p,data/name)
  shutil.copyfile(template/'emu.cfg',capsule/'template-emu.cfg');(capsule/'limited-template-preview.cfg').write_text(mod.enforce_text((template/'emu.cfg').read_text()))
  base=Path(report['arms'][n]['base']);meta=json.loads((base/'base.json').read_text());t1=bytearray((base/'track01-template.iso').read_bytes())
  for key,src,lba in [('warp',E/'fixtures/r10c-view.txt',meta['warp_lba']),('pad',E/'fixtures/neutral-pad.txt',meta['pad_lba']),('w11',None,meta['w11_lba'])]:
   blob=src.read_bytes().replace(b'\r',b'') if src else b'';assert len(blob)<={'warp':2047,'pad':4095,'w11':511}[key];t1[lba*2048:lba*2048+meta['fixture_bytes']]=blob+bytes(meta['fixture_bytes']-len(blob))
  (capsule/'track01.iso').write_bytes(t1);(capsule/'disc.gdi').write_text(meta['gdi'])
  for name in ['track02.raw','track03.iso']:__import__('os').link(base/name,capsule/name)
  lint={}
  for profile in ['loader','standard']:
   p=subprocess.run(['python3',str(D/'disc_lint.py'),str(capsule/'disc.gdi'),'--profile',profile,'--json',str(capsule/('lint-'+profile+'.json'))],capture_output=True,text=True,timeout=60);(capsule/('lint-'+profile+'.log')).write_text(p.stdout+p.stderr);lint[profile]={'rc':p.returncode,'log':ident(capsule/('lint-'+profile+'.log'))}
  assert lint['loader']['rc']==0,'loader mapping refused'
  report['arms'][n]['capsule']={'path':str(capsule),'members':{str(p.relative_to(capsule)):ident(p) for p in capsule.rglob('*') if p.is_file()},'lint':lint,'config_preview_not_actual_guest_cfg':True}
 report['resolved_differences']=remaining;report['profile_normalization_receipt']=ident(E/'identities/profile-normalization.json');report['fixtures']={p.name:ident(p) for p in (E/'fixtures').iterdir()};report['guests_started']=0;report['complete']=True;report['stage_complete_guests_blocked_pending_root_preflight']=True;report['metadata_correction_no_rebuild']=True;report['free_after']=shutil.disk_usage('/mnt/c').free
 seen=set();owned=0
 for root in [O,E,T/'port/dreamcast/game/obj']:
  for p in root.rglob('*'):
   if p.is_file() and not p.is_symlink():
    s=p.stat();k=s.st_dev,s.st_ino
    if k not in seen:seen.add(k);owned+=s.st_size
 assert owned<=report['new_total_cap_bytes'] and report['free_after']>=report['floor_bytes'];report['final_unique_owned_bytes']=owned
 (O/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');(E/'identities/preparation-receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'complete':True,'guests':0,'raw_differing_fields':len(normalized)+1,'path_only_fields':len(normalized),'remaining':remaining,'unique_owned_bytes':owned,'free':report['free_after'],'receipt_sha256':sha(O/'receipt.json')}))
if __name__=='__main__':main()