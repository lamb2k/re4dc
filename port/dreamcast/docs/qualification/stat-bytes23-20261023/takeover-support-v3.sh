#!/usr/bin/env bash
set -euo pipefail
T=/root/work/lanes/stat-bytes23-complete
W=/root/work/lanes/stat-bytes23-console-scratch/qa23-2a14662d
printf 'QA PRESETS\n'
find "$W/qa/qa" -maxdepth 1 -type f -printf '%f\n' | head -40
printf 'QA PROGRAMME\n'
/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy -R .stack -O binary /root/probe/lanes/route/out-rr2a14662qrW/re4dc-game.elf /dev/shm/stat23-qa.bin
sha256sum /dev/shm/stat23-qa.bin
printf 'SOURCE PATCH\n'
git -C "$T" diff --binary 933936ea7f45ba81c09277a780ed00111407aa23..2a14662d4b025031cd93f64eed6a5d8159d473b7 > '/mnt/c/Game Dev/Emulators/codex-lanes/stat-bytes23/stat-routine-audit-2a14662d.patch'
printf 'H2 RESTORATION RECEIPT\n'
python3 - <<'PY'
import pathlib,re,json
r=pathlib.Path('/mnt/c/Flycast-Evidence/re4-dreamcast/stat-bytes23/takeover-2a14662d')
p=r/'target-identity-and-h2.json';d=json.loads(p.read_text())
for a in ['off','on']:
 s=(r/('h2-'+a+'-r2')/'run-output.txt').read_text(errors='replace')
 start=s.index('route movie start: id=10030');end=s.index('route movie terminal=1 id=10030',start)
 lines=[x for x in s[start:end].splitlines() if x.startswith('MOVIEARENA return')]
 assert len(lines)==1 and 'restored=1' in lines[0],lines
 d['h2'][a]['source_heap_restored']=True;d['h2'][a]['restoration_log']=lines[0]
d['parser_correction']='Initial receipt used a nonexistent log prefix for restoration. Exact MOVIEARENA return is now required between s30 start and terminal; original receipt retained.'
(r/'target-identity-and-h2-v3.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d['h2']))
PY
