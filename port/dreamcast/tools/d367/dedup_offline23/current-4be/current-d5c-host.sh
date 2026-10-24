set -euo pipefail
. '/mnt/c/Game Dev/Emulators/codex-lanes/dedup-offline23/current-d5c-pins.sh'
RAM=$(mktemp -d /dev/shm/dedup-current4be0-XXXXXX)
printf '%s\n' "$RAM" > '/mnt/c/Game Dev/Emulators/codex-lanes/dedup-offline23/current-d5c-ram.txt'
mkdir "$RAM/source"
git -C "$TREE" archive "$SOURCE" port/dreamcast/game/platform port/dreamcast/room port/dreamcast/tools/d367 | tar -xf - -C "$RAM/source"
python3 - "$RAM/source" "$SOURCE" <<'PY'
from pathlib import Path
import hashlib,json,sys
p=Path(sys.argv[1]);rows={str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest() for f in p.rglob('*') if f.is_file()}
(p/'source-pins.json').write_text(json.dumps(dict(source=sys.argv[2],files=rows),indent=2)+'\n')
PY
export TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1
D=$TREE/port/dreamcast/tools/d367/dedup_offline23
(cd "$D";python3 -m unittest test_offline_dedup test_strip_share test_prepare_qualification test_audit_evidence test_plan_private_qa_pair test_composition_source) > "$RAM/python-tests.log" 2>&1
python3 "$D/check_composition.py" --source-tree "$RAM/source" --expected-source "$SOURCE" --output "$RAM/composition"
mkdir "$RAM/compact"
for room in r100 r101 r103;do ln -s "$ASSETS/$room-stripshare-v1" "$RAM/compact/$room";done
python3 "$D/check_strip_binding.py" --source-tree "$TREE" --expected-source "$SOURCE" --baseline-native /root/re4payload/t164-20261018/tree/dc/native --legacy "$ASSETS" --compact "$RAM/compact" --output "$RAM/binding"
mkdir -p "$EVIDENCE"
python3 "$D/prepare_qualification.py" --tree "$TREE" --source "$SOURCE" --strip-share --alternates "$ASSETS" --work "$WORK" --off-label dd23cur${S8}offrP --on-label dd23cur${S8}onrP --output "$EVIDENCE/qualification-plan-prelink.json"
python3 "$D/plan_private_qa_pair.py" --plan "$EVIDENCE/qualification-plan-prelink.json" --expected-source "$SOURCE" --source-repo "$TREE" --tree /root/work/lanes/dedup-offline23-qa-4be08e01 --work "$WORK/qa" --output "$EVIDENCE/private-qa-plan-prelink.json"
cp "$RAM/composition/composition-controls.json" "$EVIDENCE/host-composition.json"
cp "$RAM/binding/strip-binding-controls.json" "$EVIDENCE/host-binding.json"
cp "$RAM/python-tests.log" "$EVIDENCE/host-tests.log"
cat "$RAM/python-tests.log" | tail -4
echo "CURRENT_HOST_READY source=$SOURCE RAM=$RAM"
