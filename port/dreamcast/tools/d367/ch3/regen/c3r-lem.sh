set -euo pipefail
# c3r-lem.sh: try every distinct le_mirror.py blob (all refs) as the compact MIRROR for r201; print compact arc sha
L=/root/probe/lanes-20261018/ch3regen
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch3regen
cd "$L/git"
f=port/dreamcast/tools/le_mirror.py
mkdir -p "$L/lem"
git for-each-ref --format='%(refname)' | while read -r r; do
  b=$(git rev-parse -q --verify "$r:$f" 2>/dev/null) || continue
  echo "$b $(git log -1 --format=%ct "$r") $r"
done | sort -k1,1 -u | sort -k2n > "$L/lem/blobs.txt"
wc -l < "$L/lem/blobs.txt"
T=$L/trees/origin/lane/castle-1015/port/dreamcast/tools
while read -r b ts r; do
  git cat-file -p "$b" > "$L/trees/90606dcf/port/dreamcast/tools/lem_$b.py"
  D=$L/lem/out-$b; rm -rf "${D:?}"
  res=$( cd /tmp && python3 "$S/c3r_compact.py" "$T" "$L/trees/90606dcf/port/dreamcast/tools/lem_$b.py" "$L/src/st2/r201.das" "$L/tex1/origin/lane/castle-1015/r201/tex" "$D" 2>&1 | tail -2 | tr '\n' ' ' | cut -c1-120 || true)
  echo "$(date -d @$ts +%m%d-%H%M) ${b:0:10} $r :: $res"
  rm -rf "${D:?}"
done < "$L/lem/blobs.txt"
