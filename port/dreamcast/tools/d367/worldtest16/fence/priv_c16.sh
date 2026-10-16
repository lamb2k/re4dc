#!/bin/bash
# priv_c16.sh (WSL): the test 16 r101 world set C16 into re4-assets-private/world-r101-wt16c16-20261016 (6 files, recipe,
# job log, L2 report, SHA256SUMS); t11-fix.py WT16D points here.
set -e
P="/mnt/c/Game Dev/Emulators/re4-assets-private/world-r101-wt16c16-20261016"; R=/root/probe/worldtest16-20261016/rooms/r101-C16
mkdir -p "$P"
cp $R/out/ps2-world.re4mesh $R/out/ps2-world.r4pw $R/out/ps2-world.ids $R/out/ps2-world.r4sg $R/out/ps2-wv5.re4mesh $R/out/ps2-wv5.r4sg "$P/"
cp $R/job.log "$P/job.log"; cp $R/L2.json "$P/L2-report.json"
cat > "$P/RECIPE.txt" <<'R'
r101 world, test 16 (lane/worldtest16, 2026-10-16): version C16 = the test 16 C4 set (world-r101-wt16-20261016) plus
mesh bin 0x17 kept at level 0 (the house-front mesh whose thin fence rails the per-vertex reduction collapsed; found by
bisect: ladder output alone loses them, bin 0x17 alone restores them). World32 recipe (ps2_world_vert_ladder.py --px 96
--colour-guard 3 --colour-per-m 8 --uv-guard 0.03 --uv-per-m 0.05 --per-vertex --thin-frac 0.5 --thin-mm 2000
--max-error-mm 4000 --protect-last 14, ps2_world_batch.py --cell-mm 4000 --contiguous, ps2_strip_groups.py,
ps2_world_spatial_batch.py --cell-mm 32000, gate placements 209..222) from crowd12-bake-20261015/r101-t13, with
--protect-bins 0x2d,0x10,0x65,0xa4,0x7f,0x80,0x95,0xd,0x17 and the vertex box x -7000..1500, y -500..6500,
z -1500..7000 (stake crossbar + pyre planks; ladder_region.py WT_PROTECT_VBOX). Script: worldtest16/c16.sh.
Kept 0.652 of corners; MODELLED world p90 15.50 ms, worst view 20.49 (C4 15.11 / 20.41).
R
cd "$P" && rm -f SHA256SUMS && sha256sum * > /tmp/s && mv /tmp/s SHA256SUMS && cut -c1-16,65- SHA256SUMS
