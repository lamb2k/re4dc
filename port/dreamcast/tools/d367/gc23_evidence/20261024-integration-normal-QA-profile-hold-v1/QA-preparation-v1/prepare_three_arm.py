"""Add fresh fb254 baseline to immutable prepared pair. Source/hash work only."""
from pathlib import Path
import importlib.util,json,subprocess,hashlib,shlex
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('q',HERE/'prepare_qa_pair.py');q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
b=q.base
def main():
 old=json.loads((HERE/'PREPARATION.json').read_text());root=Path(old['root']);q.verify(old['input_pins']);q.verify(old['original_normal_pair_manifest'])
 assert b.git(b.TREE,'rev-parse','HEAD').strip()==b.SOURCE and not b.git(b.TREE,'status','--porcelain').strip()
 for arm in ('off','on'):
  q.verify({str(root/arm/'source'/n):r for n,r in old['source_manifest'].items()});assert not (root/arm/'out').exists()
 baseline=b.git(b.TREE,'rev-parse','fb254').strip();assert baseline.startswith('fb254')
 target=root/'baseline/source';assert not target.exists();b.export(b.TREE,baseline,target)
 sub=target/'port/dreamcast/game/third_party/sh4zam';sub.rmdir();b.export(b.SUBMODULE,b.SUBCOMMIT,sub)
 manifest={str(p.relative_to(target)):dict(bytes=p.stat().st_size,sha256=b.sha(p)) for p in sorted(target.rglob('*')) if p.is_file()}
 plan=dict(old);plan['sources']={'baseline':baseline,'off':b.SOURCE,'on':b.SOURCE}
 plan['source_manifests']={'baseline':manifest,'off':old['source_manifest'],'on':old['source_manifest']};del plan['source_manifest']
 plan['commands']=dict(old['commands']);plan['environment']=dict(old['environment']);plan['resolved_expected']=dict(old['resolved_expected'])
 argv=old['commands']['off'].copy();argv[1]=str(target/'port/dreamcast/tools/d367/build-r21.sh');plan['commands']['baseline']=argv
 env=dict(old['environment']['off']);env.update(OUT=str(root/'baseline/out'),OBJDIR=str(root/'baseline/out/obj'));plan['environment']['baseline']=env
 plan['resolved_expected']['baseline']=dict(old['resolved_expected']['off'])
 plan['arm_order']=['baseline','off','on'];plan['source_export_bytes']={arm:b.used(root/arm/'source') for arm in plan['arm_order']}
 plan['expected_current_raw_object_counts']={'baseline':449,'off':449,'on':455}
 plan['object_graph']=dict(no_reuse=True,OFF_helper='One empty unflagged compilation allowed; excluded actual link',baseline_helper='Absent source; no fabricated parent helper',ON_helper='Exactly one compile Motion1 and one link between gc_asset_audio.o and SDK mtx.o',QA_additions='Only dbgwarp_bridge.o adds one to normal448/454 graph. W11_FIXTURE is generated subscreen.h code in already linked sscrn_bridge.o, NOT an invented w11_fixture.o.')
 plan['OFF_identity']=dict(status='FRESH_BASELINE_REQUIRED_DURING_RUN',baseline_source=baseline,compare='QA off raw+all14 exactly equal fresh baseline same profile. No production49a4 QA comparison',normal_identity_retained=True)
 plan['input_pins']=dict(old['input_pins'])
 for f in [Path(__file__),HERE/'PREPARATION.json',HERE/'prepare_qa_pair.py']:
  plan['input_pins'][str(f)]=dict(bytes=f.stat().st_size,sha256=b.sha(f))
 plan['budget']=dict(old['budget']);plan['budget'].update(expected_approx_owned_peak_bytes=1400*1024**2,additional_preserved_preparation_roots=[],existing_prepared_pair_in_active_root=True,three_source_bytes=sum(plan['source_export_bytes'].values()),estimate='3x~100MB sources+3x~150MB outputs+3x~50MB scratch+transients/metadata, conservatively1.4GiB; actual hardcap2GiB includes all active-root files. Original normalpair belongs to previous frozen qualification, hashed/retained, not new allocation.')
 plan['preparation_v1_sha256']=b.sha(HERE/'PREPARATION.json');plan['source_files_per_arm']={arm:len(m) for arm,m in plan['source_manifests'].items()}
 assert b.used(root)<plan['budget']['owned_bytes_cap'] and plan['budget']['expected_approx_owned_peak_bytes']<plan['budget']['owned_bytes_cap']
 (HERE/'PREPARATION-THREE.json').write_text(json.dumps(plan,indent=2)+'\n');(root/'PREPARATION-THREE.json').write_text(json.dumps(plan,indent=2)+'\n')
 print(json.dumps(dict(status='PREPARED_THREE_ARMS_NOT_RUN',root=str(root),sources=plan['sources'],source_bytes=plan['budget']['three_source_bytes'],owned_now=b.used(root),estimated_peak=plan['budget']['expected_approx_owned_peak_bytes'],cap=plan['budget']['owned_bytes_cap'],pins=len(plan['input_pins']),normal_preserved=len(plan['original_normal_pair_manifest']),SDK=0,plan_sha256=b.sha(HERE/'PREPARATION-THREE.json')),indent=2))
if __name__=='__main__':main()
