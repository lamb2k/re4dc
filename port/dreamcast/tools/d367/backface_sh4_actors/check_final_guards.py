"""Focused final census-tag delta qualification; prior full actor matrix is retained."""
from pathlib import Path
import os,json,subprocess,hashlib,shutil
T=Path(__file__).resolve().parents[5];G=T/'port/dreamcast/game';O=Path('/root/probe/codex-backface-sh4zam-actors-objects02');F=O/'final-tag'
assert os.environ.get('D367_SLOT_HELD')=='1';F.mkdir(exist_ok=True)
old=json.loads((O/'RECEIPT.json').read_text());src=G/'platform/native_actor_fast.cpp';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();rows=[]
for row in old['rows']:
 if row['arm']!='base' or row['cpu']not in [0,1]:continue
 flags=row['command'][:row['command'].index('-c')];out=F/f"cpu{row['cpu']}-movca{row['movca']}-skin{row['skin']}.ii"
 r=subprocess.run([*flags,'-E','-P',str(src),'-o',str(out)],cwd=G,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);assert r.returncode==0,r.stdout
 assert sha(out)==row['preprocessed_sha256'];rows.append(dict(cpu=row['cpu'],movca=row['movca'],skin=row['skin'],preprocessed_sha256=sha(out),matches_prior_compiled_identity_control=True))
row=next(r for r in old['rows']if r['cpu']==2 and r['movca']==1);flags=row['command'][:row['command'].index('-c')];flags=[x for x in flags if not x.startswith('-DRE4DC_TA_HASH=')]+['-DRE4DC_TA_HASH=1','-DRE4DC_BACKFACE_CENSUS=1'];obj=F/'actor-trace.o'
r=subprocess.run([*flags,'-c',str(src),'-o',str(obj)],cwd=G,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(F/'actor-trace.log').write_text(r.stdout);assert r.returncode==0,r.stdout[-2000:]
# The bridge delta is a single diagnostic-only function. Evaluate that exact
# original conditional with the real compiler; no include graph is changed.
bridge=(G/'model_bridge.cpp').read_text();base=subprocess.check_output(['git','show','20752045:model_bridge.cpp'],cwd=G,text=True)if False else subprocess.check_output(['git','show','20752045:port/dreamcast/game/model_bridge.cpp'],cwd=T,text=True)
a=bridge.index('#if defined(RE4DC_BACKFACE_CENSUS)');b=bridge.index('\n#endif',a)+len('\n#endif\n');assert bridge[:a]+bridge[b:]==base
assert 'm->kindid' in bridge[a:b]and 'm->id' in bridge[a:b]and 'for('not in bridge[a:b]and 'while('not in bridge[a:b]
total=sum(p.stat().st_size for p in O.rglob('*')if p.is_file())+sum(p.stat().st_size for p in Path('/root/probe/codex-backface-sh4zam-actors-objects').rglob('*')if p.is_file());assert total<32*1024**2
j=dict(scope=__doc__,actor_source=sha(src),model_bridge_source=sha(G/'model_bridge.cpp'),prior_matrix=sha(O/'RECEIPT.json'),final_CPU0_CPU1_preprocess=rows,final_CPU2_trace_object=sha(obj),bridge_diagnostic_guard_is_only_delta=True,bridge_typed_identity_no_actorwalk=True,total_object_test_output_bytes=total,not_full_program_or_target_acceptance=True)
(F/'RECEIPT.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(dict(receipt=sha(F/'RECEIPT.json'),total_output_bytes=total)))
