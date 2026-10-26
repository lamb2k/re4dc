#!/bin/bash
set -e
REL=/root/work/lanes/gc-audit25-scratch/r2/rel/tree/dc/native
A="/mnt/c/Game Dev/Emulators/re4-assets-private"
W=/mnt/c/Flycast-Evidence/re4-dreamcast/vis-census26-20261026/pkg
mkdir -p "$W"
for r in $(ls $REL | grep '^r'); do
  [ -f $REL/$r/ps2-world.re4mesh ] || continue
  src=release
  mesh=$REL/$r/ps2-world.re4mesh
  for s in n256d26-x n256c26-20261026 n256b26-20261026 n256a26-20261026 n256w25-20261025 n256x25-20261025 n256y25-20261025 n256z25-20261025; do
    f="$A/$s/dc/native/$r/ps2-world.re4mesh"; [ -f "$f" ] && { mesh="$f"; src=$s; }
  done
  f=/root/work/lanes/world-n256all-scratch/sets/n256d26/dc/native/$r/ps2-world.re4mesh
  [ -f "$f" ] && { mesh="$f"; src=n256d26-wip; }
  mkdir -p "$W/$r"; cp "$mesh" "$W/$r/ps2-world.re4mesh"
  for x in ps2-world.r4pw ps2-world.ids append.json; do [ -f $REL/$r/$x ] && cp $REL/$r/$x "$W/$r/"; done
  echo "$r $src"
done > "$W/../sources.txt"
cat "$W/../sources.txt" | tr '\n' ';'
