W=/mnt/c/Flycast-Evidence/re4-dreamcast/vis-census26-20261026/work/$1; mkdir -p $W/noocc; cd $W/noocc || exit 1
cp ../inst.tsv ../cams.txt .
python3 - <<'P'
import struct
b=bytearray(open('../tris.bin','rb').read()); n=struct.unpack_from('<I',b,0)[0]
for i in range(n):
    o=4+i*44+40; f=struct.unpack_from('<I',b,o)[0]; struct.pack_into('<I',b,o,(f&~1)&~4)
open('tris.bin','wb').write(b)
P
OMP_NUM_THREADS=14 /root/work/lanes/vis-census26/pvs_cast . 4000 64 ceil cams.txt 320 240 > ceil.log 2>&1; rm -f ceilz.bin ceilt.bin ceilpx.bin tris.bin
