from pathlib import Path
import json,re,subprocess,hashlib
D=Path('/root/re4data/private/texture-world36-canonical-crc-20261021');H=Path('/root/probe/texture-world36-canonical-helper-20261021');P=Path('/root/probe/codex-texture-rect21/port/dreamcast/tools/d367/texture_rect21');assert not H.exists();H.mkdir();r=json.loads((D/'receipt.json').read_text())
for name in ['world_rect_bind.h','world_rect_provenance.h']:
 b=(P/name).read_text()
 if name=='world_rect_provenance.h':
  b,n=re.subn(r'static_assert\(sizeof\(certificates\)/sizeof\(certificates\[0\]\)==[0-9]+U\);','static_assert(sizeof(certificates)/sizeof(certificates[0])==3U);',b);assert n==1
 (H/name).write_text(b)
(H/'scoped_representations.inc').write_bytes((D/'proposed_representations.inc').read_bytes());(H/'provenance_certificates.inc').write_bytes((D/'proposed_provenance_certificates.inc').read_bytes())
code=Path('/root/probe/texture-world-next21-host-20261021-02/probe.cpp').read_text();assert code.count('std::cout<<checks')==1
extra=[]
for x in r['selected']:
 if not x['header_crc_only_changed']:continue
 a,b=map(lambda v:int(v,16),x['old_scoped_key'].split('-'));w,h=x['physical'];lw,lh=x['logical'];extra.append('{Descriptor d{%dU,%dU,0U,4U,2U,%dU,0x%08xU};float u=-7,v=-9;assert(!adapt(0x%08xU,0x%08xU,%dU,%dU,d,u,v,true));assert(u==-7&&v==-9);++checks;}'%(w,h,x['payload_bytes'],x['old_candidate_crc32'],a,b,lw,lh))
assert len(extra)==21;code=code.replace('std::cout<<checks','\n'.join(extra)+'\nstd::cout<<checks');(H/'probe.cpp').write_text(code)
command=['g++','-std=c++17','-O1','-g0','-fsanitize=undefined','-fno-sanitize-recover=all',str(H/'probe.cpp'),'-o',str(H/'probe')];run=subprocess.run(command,capture_output=True,text=True);assert run.returncode==0,run.stderr
paths=[D/'dc/native'/room/'ps2-world.r4pw' for room in ['r100','r101','r103']];run=subprocess.run([str(H/'probe'),*map(str,paths)],capture_output=True,text=True);assert run.returncode==0 and int(run.stdout)==573,run.stderr
result={'schema':1,'state':'CANONICAL_WORLD36_ACTUAL_HELPER_HOST_PASS','actual_adapter_provenance_checks':573,'representation_rows':36,'canonical_certificates':3,'stale_legacy_scoped_ID_rejections':21,'original_pixel_proofs_reused_exact_payload':True,'source_adapter_sha256':hashlib.sha256((P/'world_rect_bind.h').read_bytes()).hexdigest(),'source_provenance_sha256':hashlib.sha256((P/'world_rect_provenance.h').read_bytes()).hexdigest(),'host_count_assertion_explicit3':True,'command':command,'source_probe_sha256':hashlib.sha256(code.encode()).hexdigest(),'exe_sha256':hashlib.sha256((H/'probe').read_bytes()).hexdigest(),'stdout':run.stdout,'stderr':run.stderr,'limits':['Complete actual helper function bodies with proposedcanonical tables, not an integrated TU/SH4/full programme.','Active source tables/recipes/defaults untouched. All old inputs preserved.']};(H/'qualification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
