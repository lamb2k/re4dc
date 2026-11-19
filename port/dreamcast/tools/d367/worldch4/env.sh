# env.sh (sourced; lane world-ch4, 2026-11-02): the chapter 4 (castle 4-1..4-4) Disc 2 data-set inputs for the
# castle-gca-26 pipeline (tools/d367/castlegca26) generalised in this directory. Disc 2 only (recipe.conf D2_DATA).
# Rooms: CASTLE-ROUTE-20261015.md "4-1..4-4" minus r201 (cgca26 already) and r206 (3-4 end room, chapter 3 lanes).
#   r221 (Verdugo) and r228 (Salazar) rooms are converted here; their boss bodies are lane boss-check's.
#   + r21a (optional 4-3 room off r225 / r21b; its PS2 wave code is not ported, ch4found16) and r22c (the castle hub
#   room: doors to r204 r211 r220 r305 r31d; reached in chapter 4 from r211 / r220).
# Room base archives (GameCube-prepared, little-endian native .dar/.arc): ch4found16 rel31 (SMD released, castle
#   release31.sh) where it exists, else the Codex cx fixture mirror (r221 r228 r22c).
# Specs room|ETM|PAIRS|ETM-FROM: pairs.py (same-index BIN entries in GC rNNN and PS2 rNNN.dat; no unpaired index);
#   ETM "-" where the room has no etc models (r222 r216 r215 r21d: empty ETM).
W4_ROOMS=${W4_ROOMS:-"r210 r222 r219 r211 r216 r212 r213 r214 r217 r218 r215 r229 r221 r22b r220 r223 r224 r21d r225 r21b r21a r226 r227 r228 r22a r22c"}
W4_SPECS=${W4_SPECS:-"r210|all|22:22|- r222|-|-|- r219|all|22:22|- r211|all|1f:1f,21:21|- r216|-|-|- r212|all|1f:1f|- r213|all|1f:1f|- r214|all|1f:1f|- r217|all|-|- r218|all|20:20|- r215|-|-|- r229|all|-|- r221|all|20:20|- r22b|all|-|- r220|all|-|- r223|all|1f:1f|- r224|all|21:21,2a:2a|- r21d|-|-|- r225|all|28:28,33:33,35:35|- r21b|all|1f:1f|- r226|all|1f:1f,4f:4f,5a:5a|- r227|all|20:20|- r228|all|-|- r22a|all|1f:1f|- r21a|all|-|- r22c|all|1f:1f|-"}
# Chapter 4 regular enemies (bosses em2c Verdugo, em38 Salazar, em2b El Gigante: lane boss-check). em14 / em1b / em1c
# are cgca26's already. em11 em18 em29 em2d also appear in chapter 3 rooms: same tool + same input = same bytes.
W4_CEM=${W4_CEM:-"em11 em13 em15 em16 em18 em24 em25 em29 em2d em3c"}
REL31=/root/probe/lanes-20261018/ch4regen/ch4found/rel31
CXMIR=/root/probe/codex-cx-fixtures-20261013/output
CT=${D2_CASTLE_TREE:-/root/re4data/private/castle-d2-j-20261021}
WK=${WK:-/root/work/lanes/world-ch4-scratch/work}
w4_base() {  # w4_base <room> <dar|arc> -> GameCube-prepared base archive path
  if [ -f "$REL31/rel-$1/st2/$1.$2" ]; then echo "$REL31/rel-$1/st2/$1.$2"
  else ls "$CXMIR/$1"/ancillary*/mirror/st2/"$1.$2" | head -1; fi
}
