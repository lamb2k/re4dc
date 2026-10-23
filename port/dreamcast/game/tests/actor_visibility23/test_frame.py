"""Fresh-process actual helper API: window admission/cancel/budget, no cModel/GX claim."""
import ctypes,sys
L=ctypes.CDLL(sys.argv[1]);F=L.re4dc_actor_visibility23_frame
F.argtypes=[ctypes.c_uint]*4
mode=ctypes.c_uint.in_dll(L,'re4dc_actor_visibility23_mode')
bits=int(sys.argv[2],0);expected={0:0,32:1,64:2}.get(bits,0)
assert mode.value==0
F(0,0,bits,10);assert mode.value==0
F(1,1,bits,20);assert mode.value==expected
for f in range(2,601):F(f,1,bits,f*10);assert mode.value==expected
F(601,1,bits,6010);assert mode.value==0
F(602,0,bits,6020);F(603,1,bits,6030);assert mode.value==0
print('actual helper frame window PASS',bits)
