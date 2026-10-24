from pathlib import Path
import hashlib,json
tree=Path(r'\\wsl.localhost\Ubuntu-24.04\root\work\lanes\gc-port23')
own=Path(r'C:\Game Dev\Emulators\codex-lanes\gc-port23')
source=tree/'port/dreamcast/tools/d367/gc_port23/target_current_objects.py'
s=source.read_text()
assert "BASE = 'd5c1ceab9e06461462669b3ce1d28a379747a74a'" in s
s=s.replace("BASE = 'd5c1ceab9e06461462669b3ce1d28a379747a74a'", "BASE = 'fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2'")
s=s.replace("PROFILE = Path('/root/probe/lanes/route/out-au23on5e4drP')", "PROFILE = Path('/root/probe/lanes/route/out-rrfb254e8rP')")
s=s.replace("'../../../src/game/read.cpp', '../../../src/game/dvd.cpp']", "'../../../src/game/read.cpp', '../../../src/game/dvd.cpp', 'platform/native_static.cpp', 'platform/room_file.c']")
s=s.replace("if not source.startswith(expected) or git('status', '--porcelain'):", "if source != expected or git('status', '--porcelain'):")
s=s.replace("    source = git('rev-parse', 'HEAD')", "    source = git('rev-parse', 'HEAD')\n    if expected != '77d8a20b2e6c6a8f3eccb6119081c27a3dd4ea22':raise RuntimeError('Unreviewed source')\n    if os.environ.get('GCGATE_PRIOR_REPORT'):raise RuntimeError('Fresh baseline required; no prior-object reuse')\n    free=os.statvfs('/mnt/c');free=free.f_bavail*free.f_frsize\n    if free < 24*1024**3:raise RuntimeError('C below24GiB')")
s=s.replace("            if gate:\n                pin", "            if gate and not unit.endswith('.c') and not unit.startswith('../../../src/') and unit not in ('model_bridge.cpp','ui_bridge.cpp','coarse_actor.cpp'):\n                pin")
# Target-specific mirrored definitions still apply to the two actual platform C++ units.
s=s.replace("                if unit == 'platform/native_ui.cpp':args.append('-DRE4DC_GC_ASSET_COARSE_LEON=1')", "            if gate:\n                if unit == 'platform/native_ui.cpp':args.append('-DRE4DC_GC_ASSET_COARSE_LEON=1')")
s=s.replace("            print(size.strip(), flush=True)", "            print(size.strip(), flush=True)\n            used=sum(p.stat().st_size for p in scratch.rglob('*') if p.is_file())\n            if used>256*1024**2:raise RuntimeError('Owned RAM output exceeds256MiB; retained for review')\n            if os.statvfs('/mnt/c').f_bavail*os.statvfs('/mnt/c').f_frsize<24*1024**3:raise RuntimeError('C below24GiB')")
s=s.replace("note='Selected objects only; default catalog pin0.", "harness_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), scope_version='STATIC77_CURRENT_FB_NO_REUSE', note='Selected objects only; actual current fb254 commands/profile and baseline, default catalog pin0.")
assert "out-au23on5e4drP" not in s and "BASE = 'fb254" in s
compile(s,'static-target-current-20261024.py','exec')
(own/'static-target-current-20261024.py').write_text(s,newline='\n')
sh='''#!/usr/bin/env bash
set -euo pipefail
TREE=/root/work/lanes/gc-port23
OWN='/mnt/c/Game Dev/Emulators/codex-lanes/gc-port23'
SOURCE=77d8a20b2e6c6a8f3eccb6119081c27a3dd4ea22
if [ "${1:-}" = --slot ];then
 shift
 [ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 25769803776 ]
 exec "$@"
fi
[ "$(git -C "$TREE" rev-parse HEAD)" = "$SOURCE" ]
[ -z "$(git -C "$TREE" status --porcelain)" ]
[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 26843545600 ]
if pgrep -af '^(bash|/bin/bash|python|python3) [^ ]*rr-(cycle|qa|jobs)\\.(sh|py)( |$)' >/dev/null;then echo RELEASE_PRIORITY_HOLD;exit3;fi
exec 7>"/tmp/d367-build-$(printf %s "$TREE" | md5sum | cut -c1-12).lock"
flock -n 7 || exit 2
cd "$TREE"
unset GCGATE_PRIOR_REPORT
export GCGATE_SOURCE="$SOURCE" SOURCE_DATE_EPOCH=1760000000 PYTHONDONTWRITEBYTECODE=1
export RE4DC_KOS_BASE=/root/work/kos-re4dc-d367
source port/dreamcast/kos-env.sh
export PATH="$KOS_BASE/utils/build_wrappers:$KOS_CC_BASE/bin:$PATH"
exec /root/probe/d367-buildslot.sh bash "$OWN/static-target-current-20261024.sh" --slot python3 -B "$OWN/static-target-current-20261024.py"
'''.replace('exit3','exit 3')
(own/'static-target-current-20261024.sh').write_text(sh,newline='\n')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(own/'STATIC-TARGET-PREPARATION.json').write_text(json.dumps(dict(runtime_source='77d8a20b2e6c6a8f3eccb6119081c27a3dd4ea22',baseline='fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2',profile='out-rrfb254e8rP',old_harness_sha256=sha(source),new_harness_sha256=sha(own/'static-target-current-20261024.py'),wrapper_sha256=sha(own/'static-target-current-20261024.sh'),scope='Source-only prepared adaptation. No SDK run yet. Fresh14 existing objects absent/0/ON compared to current baseline; five new helpers OFF/ON; no old object reuse. C/game bridge units mirror actual make GATE-only, platform C++ additionally catalog define. OneSDK slot/tree lease;256MiB owned output cap.'),indent=2)+'\n')
print('Static target harness prepared; no SDK/guest run.')
