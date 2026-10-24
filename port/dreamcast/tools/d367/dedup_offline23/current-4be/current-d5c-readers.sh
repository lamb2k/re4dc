set -euo pipefail
ram=$(cat '/mnt/c/Game Dev/Emulators/codex-lanes/dedup-offline23/current-d5c-ram.txt')
tree=/root/work/lanes/dedup-offline23-current-d5c
d="$tree/port/dreamcast/tools/d367/dedup_offline23"
export TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1
: > "$ram/reader-results.log"
for mode in 0 3;do
 g++ -std=c++17 -O2 -DRE4DC_SCENERY_DEDUP=$mode -I"$tree/port/dreamcast/tools/d367/ps2world/hostinc" "$d/test_reader.cpp" -o "$ram/reader-$mode"
 for room in r100 r101 r103;do
  for variant in linear stripshare-v1;do
   sg=()
   if [ "$room" = r101 ];then sg+=("/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/$room-$variant/ps2-dd3.r4sg");fi
   printf 'mode=%s room=%s variant=%s ' "$mode" "$room" "$variant" >> "$ram/reader-results.log"
   "$ram/reader-$mode" "/root/re4payload/t164-20261018/tree/dc/native/$room/ps2-world.re4mesh" "/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/$room-$variant/ps2-dd3.re4mesh" "${sg[@]}" >> "$ram/reader-results.log"
  done
 done
done
git -C "$tree" show d5c1ceab9e06461462669b3ce1d28a379747a74a:port/dreamcast/room/instanced_mesh.hpp > "$ram/baseline-reader.hpp"
g++ -E -P -x c++ -DRE4DC_SCENERY_DEDUP=0 -I"$tree/port/dreamcast/tools/d367/ps2world/hostinc" -I"$tree/port/dreamcast/room" "$ram/baseline-reader.hpp" > "$ram/baseline-reader0.ii" 2>"$ram/preprocess-baseline.log"
g++ -E -P -x c++ -DRE4DC_SCENERY_DEDUP=0 -I"$tree/port/dreamcast/tools/d367/ps2world/hostinc" -I"$tree/port/dreamcast/room" "$tree/port/dreamcast/room/instanced_mesh.hpp" > "$ram/current-reader0.ii" 2>"$ram/preprocess-current.log"
cmp "$ram/baseline-reader0.ii" "$ram/current-reader0.ii"
cat "$ram/reader-results.log"
sha256sum "$ram/current-reader0.ii"
