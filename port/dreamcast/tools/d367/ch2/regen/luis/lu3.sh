set -euo pipefail
R=/root/probe/lanes-20261017r/ch2regen/luis; M=$R/models/luis-actor-v2; T=/root/probe/lanes-20261017r/ch2regen/t-luiso
mkdir -p $M/colour-vq-v2
/root/work/kos-re4dc-d336/utils/pvrtex/pvrtex -i $M/atlas.png -o $M/colour-vq-v2/atlas.dt -f RGB565 -c -p $M/colour-vq-v2/vq-preview.png > $M/colour-vq-v2/compress.log
python3 $T/port/dreamcast/tools/vq_export.py --pack-existing $M/colour-vq-v2/atlas.dt --package $M/colour-vq-v2/d9de79c8-a4fa0f80.re4tex --material ps2cast_luis_actor > $M/colour-vq-v2/package.log
python3 -c "import json;print(json.load(open('$M/validation.json'))['texture']['key'])" 2>&1 || ls $M
sha256sum $M/colour-vq-v2/*.re4tex $M/diffuse-alpha-v2/mask-runs.json
