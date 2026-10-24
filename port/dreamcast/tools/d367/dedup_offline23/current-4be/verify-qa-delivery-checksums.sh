set -euo pipefail
E=/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/current-4be08e01
for arm in Off On;do
 d="/mnt/c/Game Dev/Emulators/RE4DC-QA23-Dedup-$arm-4be08e01"
 (cd "$d" && sha256sum -c --quiet SHA256SUMS.txt)
 printf 'DELIVERY_CHECKSUM_READBACK_PASS %s\n' "$arm"
done

