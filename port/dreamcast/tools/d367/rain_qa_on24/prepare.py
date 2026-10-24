"""Source export + static OFF authentication only; never invokes an SDK tool."""
import sys
if __name__=='__main__' and not(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):raise SystemExit('Requires -I -S -B')
from pathlib import Path
import argparse,hashlib,json,resource,signal,tempfile,time,types
HERE=Path(__file__).resolve().parent

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--controller-sha256',required=True);a=ap.parse_args();resource.setrlimit(resource.RLIMIT_AS,(268435456,268435456));signal.alarm(120);start=time.monotonic()
 if (HERE/'CONTRACT.json').exists():raise RuntimeError('Single preparation; preserve existing output')
 path=HERE/'controller.py';raw=path.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=a.controller_sha256:raise RuntimeError('Exact continuation source required')
 m=types.ModuleType('continuation_prepared');m.__file__=str(path);sys.modules[m.__name__]=m;exec(compile(raw,str(path),'exec',dont_inherit=True),m.__dict__);c,ctl,post=m.context();plan,old,off=m.authenticate_off(c,ctl,post)
 c.boundaries(c.resources(c.ROOT),plan['budget'],admission=True);old_manifest=m.manifest(c.ROOT,c);root=Path(tempfile.mkdtemp(prefix='rain8ce-qa-on-cont-v1-',dir='/dev/shm'))
 exporter=m.source_module('reviewed_exporter',m.PARENT/'prepare.py',m.PINS['prepare.py']);exporter.export(c.TREE,c.SOURCE,root/'on/source');sub=root/'on/source'/plan['submodule']['path'];c.contained(root,sub);sub.rmdir();exporter.export(exporter.SUBTREE,plan['submodule']['commit'],sub)
 c.require(m.manifest(root/'on/source',c)==plan['source_manifest'],'Fresh ON direct Git export differs');c.fresh_arm(root/'on');c.boundaries(m.resources(root,c),plan['budget'],time.monotonic()-start,admission=True)
 original_post=c.ROOT/'qa-pair-result-v1/off/postbuild.json';contract=dict(schema=1,scope='CONTINUATION_NEW_ON_ONLY_REUSED_OFF',source=c.SOURCE,root=str(root),old_root=str(c.ROOT),old_root_manifest=old_manifest,parent_seal_sha256=m.PARENT_SEAL,old_receipt_sha256=m.OLD_RECEIPT,off_postbuild_path=str(original_post),off_postbuild_sha256=m.OLD_POST,canonical_lock='/tmp/d367-build-7d1f56a1729c.lock',shared_slots=['/root/probe/d367-build.lock','/root/probe/d367-build2.lock'],budget=plan['budget'],fresh_source_files=len(plan['source_manifest']),fresh_source_bytes=sum(x['bytes'] for x in plan['source_manifest'].values()),OFF_rebuilt=False,old_ON_resumed=False)
 c.exclusive_json(HERE/'CONTRACT.json',contract);metadata=dict(classification='STATIC_AUTHENTICATED_OFF_REUSE_AND_FRESH_ON_SOURCE_ONLY',old_receipt=dict(path=str(c.ROOT/'qa-pair-result-v1/receipt.json'),sha256=m.OLD_RECEIPT),original_OFF_postbuild_sha256=m.OLD_POST,actual_fresh_static_OFF_equal_original=True,OFF_files=off['files'],OFF_addresses=off['ELF']['addresses'],OFF_sizes=off['ELF']['sizes'],OFF_original_seconds=old['arms']['off']['seconds'],OFF_new_SDK=False,compile_commands=off['graph']['compile_commands_matched'],link_objects=len(off['graph']['objects']),default_off_GC_helpers=len(off['default_off_helpers']),dependency_files=len(off['dependency_closure']['files']),old_root_files=len(old_manifest),old_root_bytes=sum(x['bytes'] for x in old_manifest.values()),new_root=str(root),source_files=contract['fresh_source_files'],source_bytes=contract['fresh_source_bytes'],seconds=time.monotonic()-start,resources=m.resources(root,c),SDK_commands=0,Make_queries=0,bootstrap=0,stage=0,guests=0)
 c.exclusive_json(HERE/'OFF-REUSE-PREPARATION.json',metadata);template=dict(approved=False,grant_id='ROOT_MUST_ASSIGN_UNIQUE_ID',authorization='SDK_QA_RAIN_CONTINUE_ON',source=c.SOURCE,root=str(root),contract_sha256=c.sha(HERE/'CONTRACT.json'),kit_seal_sha256='ROOT_MUST_PIN_FINAL_KIT_SEAL',budget=plan['budget'],old_receipt_sha256=m.OLD_RECEIPT,parent_seal_sha256=m.PARENT_SEAL);c.exclusive_json(HERE/'ROOT-GRANT-TEMPLATE.json',template)
 print(json.dumps(dict(status=metadata['classification'],root=str(root),source_files=contract['fresh_source_files'],OFF_static_equal=True,old_root_files=len(old_manifest),owned_bytes=metadata['resources']['owned_bytes'],seconds=metadata['seconds'],SDK=0)))
if __name__=='__main__':main()
