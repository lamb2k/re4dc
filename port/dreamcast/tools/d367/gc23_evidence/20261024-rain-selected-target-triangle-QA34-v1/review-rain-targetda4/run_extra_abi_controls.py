"""Independent actual ELF parser schedules; no SDK."""
from pathlib import Path
import argparse,sys,struct,json,tempfile
ap=argparse.ArgumentParser();ap.add_argument('--tools',required=True);a=ap.parse_args();sys.path.insert(0,a.tools)
import test_preparation as t,readback
rows=[]
with tempfile.TemporaryDirectory(prefix='rain-da4-extra-',dir='/dev/shm') as d:
 r=Path(d)
 def variant(label,edit,ref=2,record=False):
  base=r/(label+'-base');t.elf(base,text=b'\x09\x00\x0b\x00'*2,reloc_symbol=ref,record=record)
  b=bytearray(base.read_bytes());h=struct.unpack_from('<HHIIIIIHHHHHH',b,16);sym=struct.unpack_from('<IIIIIIIIII',b,h[5]+5*40);edit(b,h,sym)
  new=r/(label+'-changed');new.write_bytes(b)
  try:readback.require_identity(readback.Elf(base),readback.Elf(new));rejected=False
  except ValueError:rejected=True
  assert rejected,label
  rows.append(dict(label=label,rejected=True))
 variant('full-st_other-high-bit',lambda b,h,s:b.__setitem__(s[4]+16+13,0x80))
 variant('external-definition-type',lambda b,h,s:b.__setitem__(s[4]+16+12,0x11))
 variant('external-definition-size',lambda b,h,s:struct.pack_into('<I',b,s[4]+16+8,2))
 variant('external-definition-section',lambda b,h,s:struct.pack_into('<H',b,s[4]+16+14,2),record=True)
 variant('unreferenced-import-visibility',lambda b,h,s:b.__setitem__(s[4]+32+13,2),ref=1)
 variant('unreferenced-import-binding',lambda b,h,s:b.__setitem__(s[4]+32+12,0x22),ref=1)
 variant('allocated-entry-size',lambda b,h,s:struct.pack_into('<I',b,h[5]+40+36,2))
 variant('ABI-e_flags',lambda b,h,s:struct.pack_into('<I',b,36,0x20))
 # Both fixtures retain a valid128-byte BSS. Extra row is initially local and
 # gains a duplicate externally visible alias; a dict-collapse checker misses it.
 base=r/'duplicate-base';t.elf(base,text=b'\x09\x00\x0b\x00'*2,reloc_symbol=2,record=True)
 b=bytearray(base.read_bytes());h=struct.unpack_from('<HHIIIIIHHHHHH',b,16);sym=struct.unpack_from('<IIIIIIIIII',b,h[5]+5*40)
 struct.pack_into('<IIIBBH',b,sym[4]+48,1,0,4,0x02,0,1);base.write_bytes(b)
 b[sym[4]+48+12]=0x12;new=r/'duplicate-new';new.write_bytes(b)
 try:readback.require_identity(readback.Elf(base),readback.Elf(new));raise AssertionError('duplicate extern escaped')
 except ValueError:rows.append(dict(label='duplicate-external-definition-multiset',rejected=True))
 base=r/'debug-base';new=r/'debug-new';t.elf(base,text=b'\x09\x00\x0b\x00'*2,reloc_symbol=2);t.elf(new,text=b'\x09\x00\x0b\x00'*2,reloc_symbol=2,debug=b'long unrelated debug path and source lines')
 assert base.read_bytes()!=new.read_bytes();readback.require_identity(readback.Elf(base),readback.Elf(new));rows.append(dict(label='debug-only-file-offset-difference',accepted=True))
 print(json.dumps(dict(scope='Frozen da4 strict selected disabled ELF tests only',controls=rows,SDK=0),indent=2))
