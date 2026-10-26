cd /mnt/c/Flycast-Evidence/re4-dreamcast/vis-census26-20261026/work/$1 || exit 1
OMP_NUM_THREADS=${2:-4} /usr/bin/time -f "%e s" /root/work/lanes/vis-census26/pvs_cast . 4000 64 ceil cams.txt 320 240 > ceil.log 2>&1; tail -1 ceil.log; rm -f ceilz.bin ceilt.bin ceilpx.bin
