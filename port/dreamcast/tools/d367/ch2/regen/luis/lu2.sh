set -euo pipefail
L=/root/probe/lanes-20261017r/ch2regen; R=$L/luis
mkdir -p $R/host-model-check/host/dc; cp -n $L/tools/pvr.h $R/host-model-check/host/dc/pvr.h; cd $L/t-luisg
PS2CAST_HOST_WORKSPACE_KB=512 PS2CAST_HOSTCHECK=$R/host-model-check bash port/dreamcast/tools/ps2_cast_native.sh $R/models/luis-gun-v1 > $R/models/luis-gun-v1/native-stage.log 2>&1 || { tail -5 $R/models/luis-gun-v1/native-stage.log; exit 1; }
tail -2 $R/models/luis-gun-v1/native-stage.log
sha256sum $R/host-model-check/check-* 
HC=$(ls -d $R/host-model-check/check-* | head -1)
python3 $L/t-luiso/port/dreamcast/tools/ps2_luis_native.py $R/models/luis-actor-v2 $R/models/luis-actor-v2/native-proof-v2 --host-check $HC --private "/mnt/c/Game Dev/Emulators/re4-assets-private" | tail -3
sha256sum $R/models/luis-actor-v2/native-proof-v2/runtime/castmodel_runtime.h
grep -n -c -E "75c2655ee619|6fc181444d83" $L/t-luiso/port/dreamcast/tools/ps2_luis_mask.py || true
