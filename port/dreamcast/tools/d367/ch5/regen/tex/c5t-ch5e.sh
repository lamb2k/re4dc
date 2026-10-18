set -euo pipefail
W=/root/probe/lanes-20261018/ch5tex; K=$W/paks; C=/root/probe/lanes-20261018/ch5regen
V=$C/game-249effe5/port/dreamcast/tools/d367/vram
export PYTHONDONTWRITEBYTECODE=1
rm -rf "${W:?}/vq-c5"; mkdir -p $W/vq-c5; cd $W/vq-c5
python3 $V/vq_pak.py $K/tex-ch5d1.pak $K/tex-ch5e.pak $W/vq-c5/work $(cat $W/vqkeys.txt) > vq.log 2>&1 || echo "rc=$?"
tail -1 vq.log | cut -c1-200
sha256sum $K/tex-ch5e.pak; stat -c %s $K/tex-ch5e.pak
