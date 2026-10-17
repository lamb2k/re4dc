# pcsrun.sh <harness> <room> <tag> <suffix> <pcs-offset>: one run + the PC sampler ring streamed to /c/tmp/ch4/pcs
H=$1; R=$2; TAG=$3; SUF=$4; OFF=$5
C="/c/Flycast-Evidence/re4-dreamcast/ch4found-20261016/$H/scenarios/cx-$R-walk-$SUF/capture"
cd /c/tmp/ch4
(FLYMAX=6 bash runall.sh $H $TAG $SUF 1 $R > runs/$SUF.nohup 2>&1 &)
until [ -f "$C/flycast.pid" ]; do sleep 1; done
python pcs/read_pcs.py $OFF pcs/$H-$R-$SUF.pcs 75 --dir "$(cygpath -w "$C")" > pcs/$H-$R-$SUF.out 2>&1
echo pcs done
