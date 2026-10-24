"""All recorded actual non-system MMD dependencies, explicit supplementary pins.
Historical asset receipts are supplementary evidence, never retroactive prehash.
"""
from pathlib import Path
import collections,hashlib,json,resource,shlex,time
HERE=Path(__file__).resolve().parent;QA=Path('/dev/shm/gc-motion24-qa-memory-v2-dbqczoc8');NORMAL=Path('/dev/shm/gc-motion24-full-pair-wrf50x14')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def row(p):return dict(bytes=Path(p).stat().st_size,sha256=sha(p))
def attest(path):
 path=Path(path);manifest=path.parent/'SHA256SUMS';report=None
 if manifest.exists():
  lines={name.strip().lstrip('*'):digest for digest,name in (line.split(None,1) for line in manifest.read_text().splitlines() if line.strip())};expected=lines.get(path.name)
 elif path.name=='ps2leon_pl08_pack_identity.inc':
  manifest=path.parent/'report-pl08-pack.json';expected=json.loads(manifest.read_text())['headers'][path.name]
 elif path.name=='ps2leon_hair_runs.h':
  manifest=path.parent/'report.json';expected=json.loads(manifest.read_text())['headers'][path.name]
 else:return dict(status='NO_HISTORICAL_ATTESTATION_FOUND')
 return dict(status='HISTORICAL_RECEIPT_MATCH' if expected==sha(path) else 'HISTORICAL_RECEIPT_MISMATCH_HOLD',receipt=dict(path=str(manifest),identity=row(manifest),mtime_ns=manifest.stat().st_mtime_ns),expected_sha256=expected,current_sha256=sha(path),scope='Existing filesystem asset receipt, not original QA build prehash')
def main():
 resource.setrlimit(resource.RLIMIT_AS,(268435456,268435456));start=time.monotonic();plan=json.loads((QA/'PREPARATION.json').read_text());pins=plan['input_pins'];allrows={};external={};total=0
 for group,root,names in [('QA',QA,['baseline','off','on']),('normal',NORMAL,['off','on'])]:
  for name in names:
   arm=root/name;cwd=arm/'source/port/dreamcast/game';deps=collections.defaultdict(list);depfiles=sorted((arm/'out').rglob('*.d'));commands={};log=(arm/'build.log').read_text().splitlines()
   for line in log:
    if ' -c ' not in line or ' -o ' not in line:continue
    argv=shlex.split(line)
    if '-o' in argv:commands[str(Path(argv[argv.index('-o')+1]).resolve())]=argv
   for dep in depfiles:
    logical=dep.read_text().replace(chr(92)+chr(10),' ').splitlines()[0];target,items=logical.split(':',1)
    for token in shlex.split(items):
     q=Path(token);q=(q if q.is_absolute() else cwd/q).resolve();deps[str(q)].append(str(dep))
   counts=collections.Counter();rows=[]
   for path,consumers in sorted(deps.items()):
    q=Path(path);pin=row(q) if q.is_file() else {'exists':False}
    if q.is_relative_to((arm/'source').resolve()):
     kind='frozen-Git-export';rel=str(q.relative_to(arm/'source'))
     expected=plan['source_manifests'][name].get(rel) if group=='QA' else plan['original_normal_pair_manifest'].get(path)
     if expected is None and rel.startswith('port/dreamcast/game/platform/sdk/gen/') and q.suffix=='.c' and not q.exists():
      kind='owned-generated-SDK-intermediate-not-retained';source=arm/'source/src/lib'/q.name;driver=arm/'source/port/dreamcast/game/platform/sdk/strip_cw_asm.py'
      assert source.is_file() and driver.is_file()
      pin=dict(exists=False,source=dict(path=str(source),identity=row(source)),driver=dict(path=str(driver),identity=row(driver)),source_make_recipe='python3 platform/sdk/strip_cw_asm.py $< $@',scope='Actual compile consumes an intermediate that Make removes; current output hash unavailable, exact retained source/driver bound')
     else:assert expected==pin,(path,expected,pin)
    elif q.is_relative_to((arm/'out').resolve()):kind='generated-owned-out'
    elif path in pins:kind='exact-original-input-pin';assert pins[path]==pin
    elif path.startswith(('/root/work/kos-re4dc-d367/','/opt/toolchains/')):kind='SDK-or-compiler-known-scope'
    else:
     kind='unrecorded-external';value=external.setdefault(path,dict(identity=pin,attestation=attest(q),consumers=[]));assert value['identity']==pin
     for dep in consumers:
      target=str(Path(dep).with_suffix('.o'));argv=commands.get(target);assert argv,(target,'no actual compile command')
      value['consumers'].append(dict(arm=group+'-'+name,dependency_file=dep,dependency_identity=row(dep),object=target,argv=argv,argv_sha256=hashlib.sha256(json.dumps(argv).encode()).hexdigest()))
    counts[kind]+=1;rows.append(dict(path=path,kind=kind,identity=pin,consumers=consumers))
   allrows[group+'-'+name]=dict(dependency_files=[dict(path=str(p),identity=row(p)) for p in depfiles],unique_dependencies=len(rows),class_counts=dict(counts),dependencies=rows);total+=len(depfiles)
 # Generator input is not a C/C++ MMD dependency: record it separately.
 pg=Path('/root/probe/lanes-20261010/ps2cast-all-assets/pg5/ganado_cast_runtime.h');derivatives={};derivation_commands={}
 for group,root,names in [('QA',QA,['baseline','off','on']),('normal',NORMAL,['off','on'])]:
  for name in names:
   arm=root/name;derivatives[group+'-'+name]={p.name:row(p) for p in (arm/'out/obj/ganado_lod').glob('*.h')};lines=[x for x in (arm/'build.log').read_text().splitlines() if 'glod_pack.py derive '+str(pg) in x];assert len(lines)==1;derivation_commands[group+'-'+name]=lines[0]
 assert all(x==derivatives['QA-baseline'] for x in derivatives.values())
 pending=[k for k,v in external.items() if v['attestation']['status']!='HISTORICAL_RECEIPT_MATCH']
 result=dict(status='SUPPLEMENTAL_DEPENDENCY_CENSUS_COMPLETE_HISTORICAL_HAIR_HEADER_MISMATCH_HOLD',original_preparation_sha256=sha(QA/'PREPARATION.json'),original_pins_not_rewritten=True,original_QA_readback_status=json.loads((HERE/'QA-READBACK.json').read_text())['status'],scope='Actual .d non-system dependencies only; MMD omits isystem headers, covered by prior separately pinned SDK/compiler scope; no claim of original complete prehash',total_dependency_files=total,arms=allrows,unrecorded_external_count=len(external),unrecorded_externals=external,generator_input=dict(path=str(pg),identity=row(pg),attestation=attest(pg),original_input_pin_present=str(pg) in pins,derived_headers_all5_equal=derivatives,actual_derivation_commands=derivation_commands),pending_historical_attestation=pending,effect_controls='Current normal OFF49a4 and fresh same-QA baseline/OFF raw+all14 identity are separate effect controls, not retroactive historical header hashes',review_tool_sha256=sha(__file__),seconds=time.monotonic()-start,no_SDK=True,no_stage=True,no_guest=True)
 with (HERE/'DEPENDENCY-CENSUS.json').open('x') as f:json.dump(result,f,indent=1);f.write('\n')
 print(json.dumps(dict(total_d_files=total,arms={k:dict(d_files=len(v['dependency_files']),unique=v['unique_dependencies'],classes=v['class_counts']) for k,v in allrows.items()},external=len(external),pending=pending)))
if __name__=='__main__':main()
