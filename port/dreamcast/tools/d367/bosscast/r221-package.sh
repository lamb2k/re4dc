set -uo pipefail
cd /root/work/lanes/bossahead
T=port/dreamcast/tools/d367
python3 - <<'PY'
import json
s=json.load(open('/root/re4data/private/boss18-verdugo-g70-20261019/packages/r221-protected-min/inputs/spec.json'))
s['registry']='ps2-ch4-r221v'
s['about']='lane bossahead (2026-11-02): r221 Verdugo, boss18 PS2 casts: full body (em2c type 0, 201 source joints / 70 drawn) + independent tail (type 1) + verdugo-low-00, the g70 gameplay level (76.1% positions, lod_of the body; NATIVE_MODEL_REGISTRY_LOD). ot_type 5: NATIVE_MODEL_REGISTRY_OT5=1; grabs draw full: NATIVE_MODEL_REGISTRY_GRAB_FULL=1; death fade: NATIVE_MODEL_REGISTRY_DYING_BOSS=2 (bossmem26). Package: model_registry.py --wide-identity --pool --roles5 --pack-bones 80 --package-room 221. Frozen-ice blend stays on the source rule. Render only.'
s['room_packages']['221']['evidence']='boss18-verdugo-g70 (Codex) packfit; lane bossahead regeneration; census / grab / ice / fade / look after release done'
open('port/dreamcast/tools/d367/model-registry/ps2-ch4-r221v.json','w').write(json.dumps(s,indent=1)+'\n')
PY
L=/root/probe/lanes/bossahead; rm -rf "${L:?}/reg-r221"
python3 $T/model_registry.py $T/model-registry/ps2-ch4-r221v.json $L/reg-r221 --tree /root/work/lanes/bossahead --package-room 221 --wide-identity --pool --roles5 --pack-bones 80 --slots 2>&1 | tail -6
python3 -c "import json;d=json.load(open('$L/reg-r221/registry-manifest.json'));print(d['room_package']['bytes'],d['room_package']['arena'],d['capacities'])" 2>&1
