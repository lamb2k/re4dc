"""Caller acquires its permitted build lease and supplies an owned output path.
Usage: build_host.py SDK_MATERIALIZED OWN_OUTPUT EXISTING_HEADER ...
"""
from pathlib import Path
import subprocess,sys
sdk=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(exist_ok=False)
test=Path(__file__).resolve().parent;game=test.parents[1]
base=['-O2','-fPIC','-fno-fast-math','-ffp-contract=off','-I'+str(sdk/'include'),'-I'+str(game/'platform/include')]
objects=[]
for source,name in [(sdk/'source/shz_bounds.c','sdk'),(game/'platform/room_occl.c','room'),(test/'host_room.c','stub')]:
 obj=out/(name+'.o');subprocess.run(['gcc',*base,'-c',str(source),'-o',str(obj)],check=True);objects.append(str(obj))
lib=out/'host.so';subprocess.run(['g++','-std=c++17',*base,'-shared','-DRE4DC_ACTOR_VISIBILITY23=1',str(game/'platform/actor_visibility23.cc'),str(test/'host_bridge.cpp'),*objects,'-o',str(lib)],check=True)
subprocess.run(['python3',str(test/'test_host.py'),str(lib),*sys.argv[3:]],check=True)
