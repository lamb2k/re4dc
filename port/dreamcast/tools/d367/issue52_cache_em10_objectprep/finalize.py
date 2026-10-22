"""Add existing common04 compiler/host closure references; no queries or target tools."""
from pathlib import Path
import hashlib,json,lzma,stat
P=Path('/root/probe/codex-issue52-objects/port/dreamcast/tools/d367/issue52_cache_em10_objectprep');C=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/issue52-cache-em10-objectprep-20261022');Q=Path('/root/re4data/private/texture-consumers21-next792-runner04-20261022')
sha=lambda b:hashlib.sha256(b).hexdigest()
def row(p):p=Path(p);return {'path':str(p),'resolved_path':str(p.resolve()),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}
d=json.loads(lzma.decompress((Q/'runner-plan.json.xz').read_bytes()));snapshot=d['source_tool_snapshot']
for r in snapshot['pins']:
 p=Path(r['path']);assert p.is_file()and p.stat().st_size==r['bytes']and sha(p.read_bytes())==r['sha256']and str(p.resolve())==r['resolved']
 assert stat.S_IMODE(p.stat().st_mode)==r['mode']
 assert (str(p.readlink())if p.is_symlink()else None)==r['symlink_target']
for r in d['directory_manifests']:
 assert {str(p)for p in Path(r['path']).iterdir()}=={x['path']for x in r['members']}
for p in snapshot['loader_absence_invariants']:assert not Path(p).exists()
x={'framework':row('/root/probe/codex-mipmap21-alpha-reader/port/dreamcast/tools/d367/link_closure21/tool_closure.py'),'source_snapshot_container':row(Q/'runner-plan.json.xz'),'snapshot_json_pointer':'source_tool_snapshot','directory_manifests_pointer':'directory_manifests','pin_count':len(snapshot['pins']),'pin_membership_sha256':sha(json.dumps(snapshot['pins'],sort_keys=True,separators=(',',':')).encode()),'paths_hash_modes_symlinks_checked_here':True,'actual_query_exec_or_dynamic_loader_probe_runs':0,'future_use':'Use unchanged tool_closure.check(source_tool_snapshot) and named04 parser/bridge after separate allocation, under matched env and actual source/tool/header/controller pins. check invokes driver selection and host loader queries; it was not called in source preparation. Fresh pre/post/exec-open proof may not be replaced by source pin checks.','scope':'Current51 compiler/host/plugin/loader/alias pins inherited from root-reviewed04 source; includes cc1plus/as/driver/wrappers and source04 timezone/BFD additions. No fresh compiler or programme qualification.'}
b=(json.dumps(x,sort_keys=True,separators=(',',':'))+'\n').encode()
for r in[P,C]:(r/'compiler-host-tool-reuse.json').write_bytes(b)
print('Existing common04 compiler/host pins verified:',len(snapshot['pins']))
