set -euo pipefail
# c3r-prepem.sh COMMIT EM...: castle prepem.sh/prepem19.sh replay (prepare_native_ui em textures + prepare_enemy_motions)
L=/root/probe/lanes-20261018/ch3regen
X=/root/re4data/private/cxfix-replay-20261018
C=${1:?}; shift
T=$L/trees/$C
[ -d "$T" ] || git -C "$L/git" worktree add -q --detach "$T" "$C"
TAG=$(echo "$C" | tr '/' '_')
W=$L/prepem/$TAG; mkdir -p "$W"
printf '{"source_complete": false, "profile": "diagnostic: no hot set (every streamed clip loads on first use)", "union": {"source_arc_indices": []}}\n' > "$W/empty-hot.json"
cd "$T/port/dreamcast/tools"
for e in "$@"; do
  [ -e "$L/src/em/$e.drs" ] || python3 /mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch3regen/c3r_gcx.py /root/work/re4-dreamcast/orig/G4BE08/re4_debug_disc1.iso "$L/src" "em/$e.drs" > /dev/null
  mkdir -p "$W/src-$e/em"; ln -sf "$L/src/em/$e.drs" "$W/src-$e/em/$e.drs"
  printf 'em/%s.drs\n' "$e" > "$W/$e-tex.manifest"
  rm -rf "${W:?}/tex-$e" "${W:?}/prep-$e"
  nice python3 prepare_native_ui.py "$W/src-$e" "$W/$e-tex.manifest" "$W/tex-$e" > "$W/tex-$e.log" 2>&1 || { tail -3 "$W/tex-$e.log"; continue; }
  nice python3 prepare_enemy_motions.py --source "$W/src-$e/em/$e.drs" --output "$W/prep-$e" --textures "$W/tex-$e" ${PEM_FLAGS:---hot-audit "$W/empty-hot.json" --diagnostic-incomplete-prefetch} > "$W/prep-$e.log" 2>&1 || { tail -3 "$W/prep-$e.log"; continue; }
  echo "$e $(sha256sum "$W/prep-$e/$e.drs" | cut -c1-12) tex $(ls "$W/tex-$e" | wc -l) mot $(find "$W/prep-$e" -name '*.fcv' | wc -l)"
done
