set -uo pipefail
cd /root/work/re4-dreamcast
ls /root/probe/lanes-20261016/cast16 /root/probe/lanes-20261016/cast16/* 2>&1 | head -40
for c in 85a9e99e 04ef5558 0e87c009; do echo "== $c"; git show --stat --format='%h %cI %s' $c | head -30; done
git branch -a --contains 0e87c009 | head
git log --all --oneline --format='%h %cI %s' -8 -- port/dreamcast/tools/ps2_cast.py | head
