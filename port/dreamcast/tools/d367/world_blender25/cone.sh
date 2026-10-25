#!/bin/bash
set -euo pipefail
X=/root/work/lanes/world-blender25-scratch
O=$X/sc21n; rm -rf "${O:?}"
cd /root/work/lanes/world-blender25/port/dreamcast/tools/d367/scenery21
python3 scn21_build.py $X/shipped $O --groups 4 --facing --sim r101:-7914,1700,2000 r101 2>&1 | tail -6
ls -la $O/r101
python3 -c "import struct;d=open(\"$O/r101/ps2-world.re4mesh\",\"rb\").read();h=struct.unpack_from(\"<4s19I\",d);print(\"crc %08x bytes %d\"%(h[3],h[2]))"
