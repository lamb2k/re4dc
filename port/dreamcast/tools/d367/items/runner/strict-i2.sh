cd /mnt/c/Flycast-Evidence/re4-dreamcast/items-20261014/_tools
for n in "$@"; do echo "== $n-i2"; bash i-strict.sh $n-c $n-i2 $n-i2 2>&1 | sed 's#/mnt/c/Flycast-Evidence/re4-dreamcast/items-20261014/##g' | cut -c1-200; done
