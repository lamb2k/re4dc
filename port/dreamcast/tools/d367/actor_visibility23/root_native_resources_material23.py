"""Fresh named root census and one bounded guest admission; no cleanup."""
from pathlib import Path
import datetime,json,os,shutil
lane=Path('/mnt/c/Game Dev/Emulators/codex-lanes/pvs23')
old=json.loads((lane.parent/'arena23/root-resource-admission.json').read_text())
roots={r['path'] for r in old['roots']}
roots.update(str(p) for p in Path('/root/probe').iterdir() if p.is_dir() and p.name.startswith(('codex-pvs23','pvs23-package-','codex-actor-visibility23','codex-actor-coverage23','codex-actor-owner-witness23','codex-backface-walk23','codex-world-scratch23-integration')))
roots.update(('/mnt/c/Game Dev/Emulators/RE4DC-QA23-PVS-baf751e8','/mnt/c/Flycast-Evidence/re4-dreamcast/pvs23-20261022'))
if Path('/root/probe/lanes/actor-owner-witness23-target').exists():
    roots.add('/root/probe/lanes/actor-owner-witness23-target')
for extra in ('/root/probe/lanes/actor-visibility23-eligibility-witness-integration', '/root/probe/lanes/actor-visibility23-coverage-staging', '/root/probe/lanes/actor-visibility23-coverage-integration', '/root/probe/lanes/actor-visibility23-integration', '/root/probe/lanes/actor-visibility23-staging', '/root/probe/lanes/world-scratch23-integration', '/root/probe/lanes/world-scratch23-staging', '/root/probe/lanes/world-scratch23-memory-staging2158', '/mnt/c/Game Dev/Emulators/codex-lanes/world-scratch23/native'):
    if Path(extra).exists():roots.add(extra)
for parent in (Path('/mnt/c/Flycast-Evidence/re4-dreamcast'),Path('/mnt/c/Game Dev/Emulators/re4-assets-private'),Path('/root/re4data/private')):
    roots.update(str(p) for p in parent.iterdir() if p.is_dir() and p.name.startswith(('pvs23-','actor-visibility23-','backface-walk23-')))
kept=[]
for name in sorted(roots,key=lambda p:(len(p),p)):
    if not any(name==q or name.startswith(q+'/') for q in kept):kept.append(name)
package_roots=['/root/probe/pvs23-package-20261022-v1','/root/probe/codex-pvs23-build-3dd7dfe4','/mnt/c/Flycast-Evidence/re4-dreamcast/pvs23-20261022','/root/probe/lanes/world-scratch23-staging','/root/probe/lanes/world-scratch23-memory-staging2158','/root/probe/lanes/actor-visibility23-staging']
package_roots.extend(str(p) for p in Path('/mnt/c/Game Dev/Emulators').glob('RE4DC-QA23-PVS-*'))
rows=[];errors=[];seen=set();directory_allowance=0;package_seen=set();package_bytes=0
for name in kept:
    size=unique=0
    if not Path(name).exists():errors.append('missing '+name);continue
    for folder,dirs,files in os.walk(name,followlinks=False,onerror=lambda e:errors.append(str(e))):
        directory_allowance+=4096
        dirs[:]=[d for d in dirs if not os.path.islink(os.path.join(folder,d))]
        for fn in files:
            p=Path(folder)/fn
            try:
                if p.is_symlink():continue
                st=p.stat();charged=(st.st_size+4095)//4096*4096;size+=charged
                key=(st.st_dev,st.st_ino)
                if key not in seen:unique+=charged;seen.add(key)
                if any(str(p).startswith(q+'/') for q in package_roots) and key not in package_seen:
                    package_seen.add(key);package_bytes+=st.st_size
            except OSError as e:errors.append(str(e))
    rows.append(dict(path=name,charge4096=size,unique_charge4096=unique))
total=sum(r['charge4096'] for r in rows)
# Keep unused actor and C-walk source allocations reserved, not just current use.
reserve=0
for prefix in ('codex-actor-visibility23','codex-backface-walk23'):
    used=sum(r['charge4096'] for r in rows if Path(r['path']).name==prefix)
    reserve+=max(0,256*1024**2-used)
guest=60*1024**2
# New explicitly allocated independent source work: retain the full caps even
# when some current files are already counted, to avoid understating its peak.
# Includes a separate 320 MiB successor build allocation; historical 813 outputs remain preserved.
# Also reserves a separate 320 MiB actor integration build; no media is admitted by this reservation.
# Includes the separate 64 MiB console-limitfps23 two-object/relink reservation.
# Original emulator objects, libraries and programme remain in place.
# Separate 8 MiB, four-unit/two-arm witness target-object qualification.
independent_work_reserve=1364*1024**2
reserve+=independent_work_reserve
# New material/witness programme allocation: charge actual files above and
# reserve the remainder, without changing any historical source/build caps.
successor_roots=('/root/probe/codex-actor-visibility23-eligibility-witness-integration',
 '/root/probe/lanes/actor-visibility23-eligibility-witness-integration')
successor_used=sum(x['charge4096'] for x in rows if x['path'] in successor_roots)
for root in successor_roots:
    if Path(root).exists():
        for _,dirs,_files in os.walk(root,followlinks=False):
            successor_used+=4096
            dirs[:]=[d for d in dirs if not os.path.islink(os.path.join(_,d))]
successor_cap=736*1024**2
if successor_used>successor_cap:errors.append('material23 source/build allocation exceeds 736 MiB')
successor_unused=max(0,successor_cap-successor_used)
reserve+=successor_unused
r=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),roots=rows,errors=errors,charged_bytes=total,
    independent_work_reserve=independent_work_reserve,successor_cap=successor_cap,successor_used=successor_used,successor_unused=successor_unused,
    unique_charged_bytes=sum(x['unique_charge4096'] for x in rows),source_unused_reserve=reserve,guest_peak=guest,
    conservative_projected_peak=total+reserve+guest+directory_allowance,
    projected_peak=sum(x['unique_charge4096'] for x in rows)+reserve+guest+directory_allowance,
    directory_allowance=directory_allowance,root_cap=16*1024**3,c_free=shutil.disk_usage('/mnt/c').free,
    floor=19394461696+1073741824,scope='Actual file identity deduplication by filesystem device/inode with every file rounded up to 4 KiB, plus 4 KiB per walked directory. Conservative duplicate-link total retained separately. The failed native capture shares the exact immutable input ISO through retained hardlinks; it is not a second allocated ISO. One 60 MiB future guest, no new programme/media allocation.')
r['admitted']=not errors and r['projected_peak']<=r['root_cap'] and r['c_free']>=r['floor']+guest
r['package_current_bytes']=package_bytes;r['package_cap']=3758096384
r['package_one_guest_admitted']=package_bytes+guest<=r['package_cap']
out=lane/('root-native-resource-material23-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.json')
out.write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(dict(path=str(out),**{k:v for k,v in r.items() if k!='roots'}),indent=2))
assert r['admitted']
