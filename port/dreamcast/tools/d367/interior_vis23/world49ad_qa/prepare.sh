#!/usr/bin/env bash
set -euo pipefail
REPO=/root/work/lanes/interior-vis23
TREE=/root/work/lanes/interior-world49ad-qa
SOURCE=49ad20f9932d638ddb7becf5db6f86b92e0a76a2
WORK=/root/work/lanes/interior-world49ad-qa-scratch
[ ! -e "$TREE" ];[ ! -e "$WORK" ]
[ "$(git -C "$REPO" rev-parse HEAD)" = 63a8bd8c1$(git -C "$REPO" rev-parse HEAD | cut -c10-) ]
[ -z "$(git -C "$REPO" status --porcelain)" ]
python3 - <<'PY'
import pathlib,subprocess,json,fcntl,shutil
windows=subprocess.check_output(['/mnt/c/Users/lambd/AppData/Local/Programs/Python/Python312/python.exe','-c',"import shutil;print(shutil.disk_usage('C:/').free)"],text=True).strip()
win=int(windows);wsl=shutil.disk_usage('/mnt/c').free
assert min(win,wsl)>=24*(1<<30),(win,wsl)
rows=[]
for p in ['/root/probe/d367-build.lock','/root/probe/d367-build2.lock']:
 with open(p,'a') as f:
  try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);free=True
  except BlockingIOError:free=False
  rows.append(dict(path=p,free=free))
assert any(r['free'] for r in rows),rows
print(json.dumps(dict(windows_free=win,wsl_free=wsl,slots=rows)))
PY
git -C "$REPO" worktree add --no-checkout --detach "$TREE" "$SOURCE"
git -C "$TREE" config --worktree core.sparseCheckout true
git -C "$TREE" config --worktree core.sparseCheckoutCone false
git -C "$TREE" sparse-checkout set --no-cone --stdin <<'PAT'
/*
!/docs/
!/tests/
!/tools/
!/assets/
!/D349/
!/port/*
/port/dreamcast/
!/port/dreamcast/docs/
PAT
git -C "$TREE" read-tree -mu HEAD
mkdir -p "$WORK"
git -C "$TREE" submodule update --init --depth 1 port/dreamcast/game/third_party/sh4zam
export RE4DC_KOS_BASE=/root/work/kos-re4dc-d367
export PATH=$RE4DC_KOS_BASE/utils/build_wrappers:/opt/toolchains/dc/sh-elf/bin:/usr/bin:/bin
. "$TREE/port/dreamcast/kos-env.sh"
[ "$KOS_BASE" = /root/work/kos-re4dc-d367 ]
[ -z "$(git -C "$TREE" status --porcelain)" ]
{
 printf 'SOURCE=%s\nTREE=%s\nKOS_BASE=%s\n' "$SOURCE" "$TREE" "$KOS_BASE"
 sh-elf-g++ --version | head -1
 git -C "$TREE" submodule status port/dreamcast/game/third_party/sh4zam
 sha256sum "$KOS_BASE/lib/dreamcast/libkallisti.a"
} | tee "$WORK/SDK-PREPARED.txt"
