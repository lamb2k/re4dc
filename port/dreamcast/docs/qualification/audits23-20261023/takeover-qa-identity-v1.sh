#!/usr/bin/env bash
set -euo pipefail
E='/mnt/c/Flycast-Evidence/re4-dreamcast/audits23-takeover/5e4de9a0'
mkdir -p "$E/qa-identity"
O=/root/probe/lanes/route/out-rr5e4de9aqrW
/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy -R .stack -O binary "$O/re4dc-game.elf" /dev/shm/audits23-qa.bin
sha256sum /dev/shm/audits23-qa.bin > "$E/qa-identity/raw.sha256"
cp "$O/resolved-knobs.txt" "$O/stack.txt" "$O/syms.txt" "$E/qa-identity/"
sha256sum "$O/re4dc-game.elf" "$O"/*.ovl > "$E/qa-identity/programmes.sha256"
python3 - "$E" <<'PY'
import pathlib,json,re,sys
r=pathlib.Path(sys.argv[1]);out={}
for scene in ['boot','warp','h2']:
 p=r/f'qa-{scene}-r1';run=json.loads((p/'run-result.json').read_text());bound=json.loads((p/'bounded-launch.json').read_text());s=(p/'run-output.txt').read_text(errors='replace').replace('\0','')
 assert run['stopped']=='goal' and not run['errors'] and not bound['deadline_fired']
 assert not re.search(r'HALT|FAULT|MISSING|Out of memory',s)
 row={'elapsed_s':run['elapsed_s'],'goal':True,'deadline_fired':False,'errors':[]}
 if scene=='warp':assert 'phase=enter room=103' in s
 if scene=='h2':
  m=re.search(r'route movie terminal=1 id=10030 frames=340/340 uploaded=340 presented=340[^\n]*heap_before=(\d+)',s);assert m
  row['s30']={'frames':'340/340','heap_before':int(m[1])}
 out[scene]=row
(r/'qa-identity/own-qa-gates.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
PY
cat "$E/qa-identity/raw.sha256"