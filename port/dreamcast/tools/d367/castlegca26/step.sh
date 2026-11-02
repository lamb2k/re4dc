#!/bin/bash
# step.sh objects <room> <etm|-> <pairs|-> <outdir> <castle tree>   (WSL; gen-objects.sh step 1)
# step.sh store <store> <room> <outdir> <castle tree>                (WSL; gen-objects.sh step 3)
set -euo pipefail
H=$(cd "$(dirname "$0")" && pwd); TW=$(cd "$H/../.." && pwd)
REASON="no-GameCube-assets rule (user 10-23; Test 26 castle convert 11-01): the PS2 object replaces the GC one"
case "$1" in
  objects)
    r=$2; etm=$3; pairs=$4; O=${5:?}; CT=${6:?}
    rm -rf "${O:?}"; mkdir -p "$O/x/tex" "$O/../gcroom"
    cd "$TW"
    [ -s "$O/../gcroom/$r.arc" ] || python3 "$H/gcroom.py" "$O/../gcroom" "$r"
    a=(room --dar "$CT/st2/$r.dar" --room "$r" --uv-fold --keep-larger --keep-larger-reason "$REASON" --out "$O/$r.dar" --json "$O/$r.json")
    [ "$etm" = - ] || a+=(--etm "$etm")
    [ "$pairs" = - ] || a+=(--pairs "$pairs")
    python3 ps2_objects.py "${a[@]}" > "$O/objects.log" 2>&1 || { tail -5 "$O/objects.log"; exit 1; }
    tail -1 "$O/objects.log" ;;
  store)
    ST=$2; r=$3; O=${4:?}; CT=${5:?}
    python3 "$H/mkstore.py" "$ST" "$r" "$CT/st2/$r.dar" "$O/x/$r.dar"
    mkdir -p "$ST/tex" "$ST/reports"
    find "$O/x/tex" -name '*.re4tex' -exec cp {} "$ST/tex/" \;
    cp "$O/$r.json" "$ST/reports/$r-objects.json"; cp "$O/x/tex.json" "$ST/reports/$r-tex.json"
    cp "$O/objects.log" "$ST/reports/$r-objects.log" ;;
  clean)  # step.sh clean <store>...: the stores are regenerated whole (only /root/re4data/private/*cgca26-* paths)
    shift
    for s in "$@"; do
      case "$s" in /root/re4data/private/*cgca26-2*) rm -rf "${s:?}";; *) echo "refusing to clean $s"; exit 1;; esac
    done ;;
  snd)    # step.sh snd <pmcgca26 store> <sndcgca26 store> <base catalog.json>
    S2=$2; S3=$3; CAT=${4:?}
    CT=${D2_CASTLE_TREE:-/root/re4data/private/castle-d2-j-20261021}
    ISO=${PS2_ISO:-/mnt/c/Game Dev/Emulators/re4_helpers/Resident Evil 4 (USA)/Resident Evil 4 (USA).iso}
    SW=/root/work/lanes/castle-gca-26-scratch/snd; rm -rf "${SW:?}"; mkdir -p "$SW/tree/st2" "$SW/tree/em" "$SW/ps2"
    for r in r201 r202 r204 r208; do cp "$S2/st2/$r.dar" "$SW/tree/st2/"; done
    cp "$CT/em/em19.drs" "$SW/tree/em/"
    cd "$TW"
    python3 ps2_audio.py afs --iso "$ISO" --out "$SW/ps2" 'r20*.snd' 'em19.snd' | tail -1
    python3 ps2_audio.py banks --tree "$SW/tree" --ps2 "$SW/ps2" --out "$SW/ov" --files st2/r201.dar,st2/r202.dar,st2/r204.dar,st2/r208.dar,em/em19.drs \
      --json "$SW/banks-map.json" --jobs 4 > "$SW/banks.txt"; tail -1 "$SW/banks.txt"
    python3 d367/snd28_store.py "$SW/tree" "$SW/ov" "$SW/banks-map.json" "$CAT" "$S3" "$SW/ps2" | tail -1
    cp "$SW/banks.txt" "$S3/_map/" ;;
  seal)   # step.sh seal <store>...: RECIPE / README + SHA256SUMS.txt
    shift
    for s in "$@"; do
      n=$(basename "$s"); n=${n%-*}
      case "$n" in
        cgca26) cat > "$s/RECIPE.txt" <<EOF
cgca26 (lane castle-gca-26, $(date -u +%F)): Disc 2 castle objects and enemy models from the PS2 version (user 11-01
"Convert in Test 26"; DISC 2 ONLY, recipe.conf D2_DATA). PS2 source: Resident Evil 4 (USA) PS2 ISO, BIO4DAT.AFS r201.dat
r202.dat r204.dat r208.dat (ETM etc models, room BINs, TPL pictures) and em1b.dat / em14.dat (enemy BINs).
st2/rNNN.dar = ps2_objects.py room --etm all --pairs (r201 22:22; r202 1f:1f,2a:2a; r204 1f:1f,2d:2d; r208 28:28) --uv-fold
--keep-larger, then ps2_objects_tex.py (PS2 pictures, tex/ loose keys); graft.json = the changed members;
provenance.tsv = converted model -> PS2 source member; em/em1b.drs em/em14.drs = ps2cast/ps2_ganado_bins.py (+ pmcgca26's
PS2 motion in em1b). Commands: tools/d367/castlegca26/gen-all.sh. Reports: reports/.
EOF
        ;;
        pmcgca26) cat > "$s/RECIPE.txt" <<EOF
pmcgca26 (lane castle-gca-26, $(date -u +%F)): Disc 2 castle motion from the PS2 version (BIO4DAT.AFS em1b.dat em3b.dat
r201.dat r202.dat r204.dat r208.dat of the PS2 USA ISO), motion/ps2_motion_prepared.py rewrite + verify (VERIFY PASS each):
em/em1b.drs (135 of 178 FCV changed, 133 new dc/mot keys), em/em3b.drs (0 changed: proof copy), st2/rNNN.dar (room FCV /
SEQ; graft.json = changed entries: r202 0x35 FCV, r204 0x2b 0x2c FCV). Commands: tools/d367/castlegca26/gen-em.sh.
EOF
        ;;
        sndcgca26) cat > "$s/README-sndcgca26.txt" <<EOF
sndcgca26 (lane castle-gca-26, $(date -u +%F)): tools/ps2_audio.py banks (PS2 PCM in place, same sizes) on pmcgca26's
st2/r201 r202 r204 r208.dar and the castle em/em19.drs; store by d367/snd28_store.py (provenance.tsv per bank; no RECIPE
on purpose, see snd28_store.py). _map/banks-map.json lists every sample (kept GC samples: gc_port23/sound-kept-gc.tsv).
EOF
        ;;
      esac
      (cd "$s" && find . -type f ! -name SHA256SUMS.txt -printf '%P\n' | sort | xargs -d '\n' sha256sum > SHA256SUMS.txt)
      echo "sealed $s: $(wc -l < "$s/SHA256SUMS.txt") files"
    done ;;
esac
