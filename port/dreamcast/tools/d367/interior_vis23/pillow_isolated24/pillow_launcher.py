"""Pinned PIL-only availability for unchanged bounded capture runner; no guest grant."""
from pathlib import Path
import hashlib, importlib.abc, importlib.machinery, importlib.util, io, json, runpy, sys, types
PINS_SHA256='e7027f68abb393a897c405c95465cc2a701a948f8ec4b990da460a18b9a492d4'

def checked(path,pin):
    path=Path(path)
    if path.is_symlink():raise RuntimeError('symlink refused: '+str(path))
    raw=path.read_bytes()
    if len(raw)!=pin['size'] or hashlib.sha256(raw).hexdigest()!=pin['sha256']:
        raise RuntimeError('pinned bytes changed: '+str(path))
    return raw

class Source(importlib.abc.Loader):
    def __init__(self,path,pin):self.path,self.pin=path,pin
    def create_module(self,spec):return None
    def exec_module(self,module):
        raw=checked(self.path,self.pin)
        module.__file__=str(self.path)
        exec(compile(raw,str(self.path),'exec',dont_inherit=True),module.__dict__)

class PillowOnly(importlib.abc.MetaPathFinder):
    def __init__(self,root,files):self.root,self.files=root,files
    def find_spec(self,fullname,path=None,target=None):
        if fullname!='PIL' and not fullname.startswith('PIL.'):return None
        rel='/'.join(fullname.split('.')[1:])
        candidates=[((rel+'/' if rel else '')+'__init__.py',True),(rel+'.py',False)]
        candidates += [(rel+s,False) for s in importlib.machinery.EXTENSION_SUFFIXES]
        for name,package in candidates:
            if name not in self.files:continue
            p=self.root/name; checked(p,self.files[name])
            if name.endswith('.py'):
                spec=importlib.util.spec_from_loader(fullname,Source(p,self.files[name]),is_package=package)
                spec.origin=str(p)
                if package:spec.submodule_search_locations=[str(p.parent)]
                return spec
            return importlib.util.spec_from_file_location(fullname,p)
        raise ModuleNotFoundError('Unpinned PIL module refused: '+fullname)

def install(pinpath):
    if not (sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):
        raise RuntimeError('Requires Python -I -S -B')
    if not sys.pycache_prefix or Path(sys.pycache_prefix).exists():
        raise RuntimeError('Requires absent fresh -X pycache_prefix=absolute-path')
    if not Path(sys.pycache_prefix).is_absolute():raise RuntimeError('cache prefix must be absolute')
    if 'site' in sys.modules or any(n=='PIL' or n.startswith('PIL.') for n in sys.modules):
        raise RuntimeError('site/PIL already imported')
    raw=Path(pinpath).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PINS_SHA256:raise RuntimeError('manifest identity')
    m=json.loads(raw);root=Path(m['package_root'])
    if root.is_symlink() or not root.is_absolute():raise RuntimeError('package root')
    seen=set()
    for p in root.rglob('*'):
        if '__pycache__' in p.relative_to(root).parts:continue
        if p.is_symlink():raise RuntimeError('package symlink')
        if p.is_file():seen.add(p.relative_to(root).as_posix())
    if seen!=set(m['package_files']):raise RuntimeError('package membership changed')
    for name,pin in m['package_files'].items():checked(root/name,pin)
    for name,pin in m['distribution'].items():checked(Path(m['distribution_root'])/name,pin)
    for pin in m['inputs'].values():checked(pin['path'],pin)
    if Path(sys.executable).resolve()!=Path(m['inputs']['python']['path']).resolve():raise RuntimeError('python path')
    sys.meta_path.insert(0,PillowOnly(root,m['package_files']))
    from PIL import Image
    from PIL import PngImagePlugin
    if Image.__file__!=str(root/'Image.py'):raise RuntimeError('Image origin')
    return m

def self_test(m):
    from PIL import Image
    import PIL
    rgb=bytes([255,0,0,0,255,0,0,0,255,19,37,53])
    image=Image.frombytes('RGB',(2,2),rgb);png=io.BytesIO();image.save(png,format='PNG')
    png.seek(0)
    with Image.open(png) as decoded:
        assert decoded.mode=='RGB' and decoded.size==(2,2) and decoded.tobytes()==rgb
    assert 'site' not in sys.modules
    assert not any('site-packages' in str(p).lower() for p in sys.path)
    return {'status':'HOST_RGB_PNG_PASS_NO_GUEST','pillow':PIL.__version__,'png_bytes':len(png.getvalue()),'rgb_sha256':hashlib.sha256(rgb).hexdigest(),'loaded_PIL':sorted(n for n in sys.modules if n=='PIL' or n.startswith('PIL.')),'site_imported':False,'cache_prefix_exists':Path(sys.pycache_prefix).exists()}

def main():
    pinpath=Path(__file__).with_name('PILLOW-PINS.json')
    m=install(pinpath)
    if sys.argv[1:]==['--self-test']:
        print(json.dumps(self_test(m),indent=2));return
    if len(sys.argv)<4 or sys.argv[1]!='--':raise SystemExit('Use -- bound.py fp_run.py [unchanged runner args] or --self-test')
    args=sys.argv[2:]
    for n,p in [('bound',args[0]),('harness',args[1])]:
        if Path(p).resolve()!=Path(m['inputs'][n]['path']).resolve():raise RuntimeError('runner path mismatch '+n)
        checked(p,m['inputs'][n])
    sys.argv=args
    runpy.run_path(args[0],run_name='__main__')

if __name__=='__main__':main()
