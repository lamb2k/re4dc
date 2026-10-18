# reg113p-c.sh (Git Bash): regcast em17p + merge_cast -> regcast-ch2p, head mask runs, pool registry r113p (lane ch2regen)
set -euo pipefail
TREE=${TREE:-t-ecf2a44a}
L=//wsl.localhost/Ubuntu-24.04/root/probe/lanes-20261017r/ch2regen
LW=/root/probe/lanes-20261017r/ch2regen
T=$L/$TREE/port/dreamcast/tools; W=$L/ps2cast/conv-ch2
export PS2CAST_INPUTS=$L/ps2cast/inputs-ch2
export RE4_CAST_BUNDLE=$L/tools/cast_bundle.py
rm -rf "$W/regcast-em17p"
python "$T/ps2_cast.py" regcast $W/regcast-em17p ps2-overlay $W/ganado-em17-0cp 2>&1 | tail -1
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -- python3 "/mnt/c/Game Dev/Emulators/ps2cast-20261014/sh/conv/merge_cast.py" $LW/ps2cast/conv-ch2/regcast-ch2p $LW/ps2cast/conv-ch2/regcast-ch2 $LW/ps2cast/conv-ch2/regcast-em17p | tail -1
rm -rf "$W/e17p-mask-head"
python "$T/ps2_mask_runs.py" $W/ganado-em17-0cp $L/ps2cast/inputs-ch2/em17.drs 0x1cf 0x1ce 1 $W/e17p-mask-head > /dev/null
cat > ./gen-regp113.sh <<EOF
set -euo pipefail
T=$LW/$TREE; M=\$T/port/dreamcast/tools/d367/model-registry; W=$LW/ps2cast/conv-ch2
python3 - <<'P'
import json
s = json.load(open('$LW/$TREE/port/dreamcast/tools/d367/model-registry/ps2-ch2-r113p.json'))
s['cast_dir'] = '$LW/ps2cast/conv-ch2/regcast-ch2p'
for d in s['descriptors']:
    if 'mask_runs' in d:
        d['mask_runs'] = {k: v.replace('/root/probe/lanes-20261015/ps2cast/conv-ch2', '$LW/ps2cast/conv-ch2') for k, v in d['mask_runs'].items()}
json.dump(s, open('$LW/ps2cast/ps2-ch2-r113p.json', 'w', newline='\n'), indent=1)
P
cd \$T; o=\$W/reg-113p; rm -rf "\${o:?}"
python3 port/dreamcast/tools/d367/model_registry.py $LW/ps2cast/ps2-ch2-r113p.json \$o --tree \$T --package-room 113 --pack-bones 64 --wide-identity --pool > \$o.log 2>&1 || { tail -3 \$o.log; exit 1; }
sha256sum \$o/package/r113/registry.re4nmr; ls \$o/tex
echo "expect fa23cc54db60a695"
EOF
cp ./gen-regp113.sh "$L/tools/regp113.sh"
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -- bash -c "sed -i 's/\r$//' $LW/tools/regp113.sh && bash $LW/tools/regp113.sh"
