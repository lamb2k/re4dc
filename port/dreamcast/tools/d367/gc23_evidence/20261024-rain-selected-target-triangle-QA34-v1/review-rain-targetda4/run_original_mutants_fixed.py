"""Independent synthetic real-ELF controls, exact reviewer input. No SDK."""
from pathlib import Path
import argparse,importlib,sys,struct,json,tempfile
ap=argparse.ArgumentParser();ap.add_argument('--tools',required=True);a=ap.parse_args();sys.path.insert(0,a.tools)
import test_preparation as t,readback
with tempfile.TemporaryDirectory(prefix='rain-identity-review-',dir='/dev/shm') as d:
 r=Path(d);base=r/'base';t.elf(base,text=b'\x09\x00\x0b\x00'*2);original=base.read_bytes();h=struct.unpack_from('<HHIIIIIHHHHHH',original,16)
 results=[]
 def check(label,b,accepted):
  q=r/label;q.write_bytes(b)
  try:readback.require_identity(readback.Elf(base),readback.Elf(q));actual=True
  except ValueError:actual=False
  assert actual is False,(label,actual)
  results.append(dict(label=label,accepted_as_disabled_identity=actual))
 b=bytearray(original);struct.pack_into('<I',b,h[5]+40+12,0x1234);check('allocated-address',b,True)
 # Put the existing relocation on external symbol2; symbol1 is exported to outside consumers.
 b=bytearray(original);rela=struct.unpack_from('<IIIIIIIIII',b,h[5]+6*40);struct.pack_into('<I',b,rela[4]+4,(2<<8)|1);base.write_bytes(b);original=bytes(b)
 sym=struct.unpack_from('<IIIIIIIIII',b,h[5]+5*40)
 b=bytearray(original);struct.pack_into('<I',b,sym[4]+16+4,2);check('unreferenced-function-value',b,True)
 b=bytearray(original);b[sym[4]+16+12]=0x22;check('unreferenced-function-weak-binding',b,True)
 b=bytearray(original);b[sym[4]+16+13]=2;check('unreferenced-function-hidden-visibility',b,True)
 b=bytearray(original);text=struct.unpack_from('<IIIIIIIIII',b,h[5]+40);b[text[4]]=8;check('allocated-code-change',b,False)
 print(json.dumps(dict(scope='Exact da4 successor: original846 valid-extent mutations now rejected, no target evidence',results=results,SDK=0),indent=2))
