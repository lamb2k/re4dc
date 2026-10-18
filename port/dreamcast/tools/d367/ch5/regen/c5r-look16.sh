set -uo pipefail
cd /root/work/re4-dreamcast
B=origin/wip/ch4regen-20261018:port/dreamcast/tools/d367/ch4found/regen/cast
for f in c16setup.sh c16real.sh c16conv.sh drv.py native.sh mask.py reg.sh c16pub.sh; do echo "=== $f"; git show $B/$f | head -60; done
echo === commits with ps2-ch5 specs
git log --all --oneline -5 -- port/dreamcast/tools/d367/model-registry/ps2-ch5-em1ep.json
git log --all --oneline -3 -- port/dreamcast/tools/d367/model-registry/ps2-ch5-em32.json port/dreamcast/tools/d367/model-registry/ps2-ch5-em3dp.json
git ls-tree --name-only $(git log --all -1 --format=%H -- port/dreamcast/tools/d367/model-registry/ps2-ch5-em1ep.json) port/dreamcast/tools/d367/model-registry/ | grep ch5
