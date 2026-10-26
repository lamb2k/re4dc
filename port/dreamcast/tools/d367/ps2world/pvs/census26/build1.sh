cd /mnt/c/Flycast-Evidence/re4-dreamcast/vis-census26-20261026/work/$1 || exit 1
export PVS_EYE_H=1000,1700,2400 OMP_NUM_THREADS=${2:-8}
/usr/bin/time -f "%e s" /root/work/lanes/vis-census26/pvs_cast . 4000 4096 > build.log 2>&1
tail -3 build.log
