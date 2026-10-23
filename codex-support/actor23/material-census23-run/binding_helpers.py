from pathlib import Path
import hashlib,importlib,json,sys
from contain import sha
def native_path(value):
 if value.startswith('/mnt/c/'):return Path('C:/'+value[7:])
 if value.startswith('/root/'):return Path(r'\\wsl.localhost\Ubuntu-24.04')/Path(value[1:])
 p=Path(value)
 if not p.is_absolute():raise ValueError('absolute pinned path required: '+value)
 return p

def checked_json(path,pin,inputs):
 path=native_path(str(path))
 data=path.read_bytes()
 if hashlib.sha256(data).hexdigest()!=pin:raise ValueError('receipt pin differs: '+str(path))
 inputs[str(path)]=pin;return json.loads(data)

def pin(path,inputs,expected=None):
 path=native_path(str(path))
 if not path.is_file() or path.is_symlink():raise ValueError('ordinary input file required: '+str(path))
 digest=sha(path)
 if expected and digest!=expected:raise ValueError('input hash differs: '+str(path))
 inputs[str(path)]=digest;return path

def runtime_inputs(inputs):
 # These imports perform no emulator/process/window queries. Pin the modules
 # used by stock runner/reader/PIL plus the CPython DLL and extension modules.
 for name in ('argparse','ast','copy','csv','ctypes','ctypes.wintypes','datetime','hashlib',
              'importlib.util','json','locale','os','pathlib','re','shutil','socket',
              'struct','subprocess','threading','time','runpy','encodings.cp1252','encodings.utf_16'):
  importlib.import_module(name)
 from PIL import Image
 Image.init()
 pin(Path(sys.executable),inputs)
 for module in list(sys.modules.values()):
  value=getattr(module,'__file__',None)
  if value:
   path=Path(value)
   if path.is_file() and path.suffix.lower() in ('.py','.pyd','.dll','.zip'):pin(path,inputs)
 for folder in (Path(sys.base_prefix),Path(sys.base_prefix)/'DLLs'):
  for pattern in ('*.dll','*.pyd','python*.zip'):
   for path in folder.glob(pattern):pin(path,inputs)
 # Include lazily used PIL plugins without executing their image operations.
 import PIL
 for path in Path(PIL.__file__).parent.rglob('*'):
  if path.is_file() and path.suffix.lower() in ('.py','.pyd','.dll'):pin(path,inputs)


