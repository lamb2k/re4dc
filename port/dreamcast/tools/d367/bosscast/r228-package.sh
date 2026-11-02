set -uo pipefail
T=/root/work/lanes/bossahead/port/dreamcast/tools/d367
L=/root/probe/lanes/bossahead
rm -rf "${L:?}/cast-r228" "${L:?}/reg-r228"
python3 $T/bosscast/mergecast.py $L/cast-r228 /root/probe/lanes-20261016/cast16/conv4/regcast-ch4:armor-em25-00 /root/re4data/private/boss18-salazar-role-contract-20261019/cast-full:queen-em38-00,tentacle-em38-01=tent-em38-01,salazar-em38-03,roots-em38-04
cd /root/work/lanes/bossahead
python3 $T/model_registry.py $T/model-registry/ps2-ch4-r228s.json $L/reg-r228 --tree /root/work/lanes/bossahead --package-room 228 --wide-identity --pool --roles5 --role-tex34 --shift0 --pack-bones 64 2>&1 | tail -15
