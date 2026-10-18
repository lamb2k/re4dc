set -euo pipefail
W=/root/probe/lanes-20261018/ch5tex
C=/root/probe/lanes-20261018/ch5regen
T=$C/game-249effe5/port/dreamcast/tools
E=/mnt/c/Flycast-Evidence/re4-dreamcast/ch5found-20261016
ISO="/mnt/c/Game Dev/Emulators/Resident Evil 4 (USA) (Disc 2).iso"
export PYTHONDONTWRITEBYTECODE=1
cd /tmp
rm -rf "${W:?}/pairs-c5" "${W:?}/pairs-c5b" "${W:?}/evt5"; mkdir -p $W/pairs-c5 $W/pairs-c5b $W/evt5
LOGS=$(ls $E/h-cx5cmW/scenarios/*/capture/run-output.txt $E/h-cx5vmW/scenarios/*/capture/run-output.txt)
python3 $T/d367/pairs_from_log.py --iso "$ISO" --output $W/pairs-c5 $(for f in $LOGS; do echo --log $f; done) \
  --file st3/r311.das --file st3/r327.das --file em/em1d.drs --file em/em1e.drs --file em/em1f.drs --file etc/core.das 2>&1 | tail -3
LOGS=$(ls $E/h-cx65mW/scenarios/*/capture/run-output.txt $E/h-cx67mW/scenarios/*/capture/run-output.txt)
python3 $T/d367/pairs_from_log.py --iso "$ISO" --output $W/pairs-c5b $(for f in $LOGS; do echo --log $f; done) \
  --file evd/r310s00.evd --file st3/r310.das --file em/em36.drs --file st3/r307.das --file st3/r315.das --file st3/r327.das --file em/em1d.drs --file em/em1e.drs --file em/em1f.drs --file etc/core.das 2>&1 | tail -3
S=$C/deps/source
cd $W/evt5
ls $S/evd | grep -E '^r3([0-2][0-9a-f]|30)s' | sed 's#^#evd/#' > evd5.manifest; wc -l < evd5.manifest
python3 $T/prepare_native_ui.py $S evd5.manifest $W/evt5/tex > tex.log 2>&1 || echo "rc=$?"
ls $W/pairs-c5 $W/pairs-c5b; ls $W/evt5/tex | wc -l
sha256sum $W/pairs-c5/*.re4tex $W/pairs-c5b/*.re4tex $W/evt5/tex/{f852b5a0-fa89f2b3,dec22ae8-7b78418e,ded53fe4-b8cc6557}.re4tex | cut -c1-16,65-
