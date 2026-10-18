set -euo pipefail
W=/root/probe/lanes-20261018/ch5tex; C=/root/probe/lanes-20261018/ch5regen
T=$C/game-249effe5/port/dreamcast/tools
P=/mnt/c/tmp/ch5
export PYTHONDONTWRITEBYTECODE=1
cd /root/work/re4-dreamcast
git cat-file -e 3f757369 2>/dev/null || git fetch -q origin wip/ch5found16-20261017
git show 3f757369:port/dreamcast/tools/d367/vram/vq16-c5.txt > $W/vq16-c5.txt
git show 3f757369:port/dreamcast/tools/d367/vram/vq_pak.py > $W/vq_pak.py
cmp $W/vq_pak.py $T/d367/vram/vq_pak.py && echo vq_pak-same || echo vq_pak-DIFF
grep -v '^#' $W/vq16-c5.txt | awk '{print $1}' | grep . > $W/vqkeys.txt; wc -l < $W/vqkeys.txt
K=$W/paks; mkdir -p $K; cd /tmp
python3 $P/pakunion.py $K/tex-ch5.pak $W/vq33/tex-st3vq4.pak /root/probe/lanes-20261018/ch3regen/extra/base/t15-15611245.pak
python3 $P/pakadd.py $K/tex-ch5b.pak $K/tex-ch5.pak $W/pairs-c5/*.re4tex
python3 $P/pakadd.py $K/tex-ch5c.pak $K/tex-ch5b.pak $C/prepem-game-249effe5/tex-em*/*.re4tex
E=$W/evt5/tex
python3 $P/pakbase.py $K/tex-ch5d.pak /root/probe/lanes-20261018/ch3regen/extra/base/p-51f1f7a4.pak $K/tex-ch5c.pak $E/f852b5a0-fa89f2b3.re4tex $E/dec22ae8-7b78418e.re4tex $E/ded53fe4-b8cc6557.re4tex $W/pairs-c5b/8273f9f1-17ca1557.re4tex $W/pairs-c5b/664b0f7e-013bedef.re4tex
python3 $P/pakbase.py $K/tex-ch5d1.pak $K/tex-ch5d.pak $K/tex-ch5d.pak $C/pairs-st3/all/196d7189-3e8f4f08.re4tex $C/fixtures/r327/ancillary-b47c37112cf4/tex/5430b7b8-d495a677.re4tex
rm -rf "${W:?}/vq-c5"; mkdir -p $W/vq-c5; cd $W/vq-c5
python3 $W/vq_pak.py $K/tex-ch5d1.pak $K/tex-ch5e.pak $W/vq-c5/work $(cat $W/vqkeys.txt) > vq.log 2>&1; echo rc=$?; tail -1 vq.log | cut -c1-200
sha256sum $K/*.pak | cut -c1-16,65-
echo want ch5e d5986c3e
