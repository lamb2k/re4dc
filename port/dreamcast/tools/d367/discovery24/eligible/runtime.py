"""Exact host provider pins/control state; not SH4 or historical-runtime proof."""
import hashlib,os,sys,ctypes,platform,struct
from pathlib import Path
ROOT=Path('/root/probe/lanes-20261018/codexreplay/pylib').resolve()
def identity(p):
    p=Path(p).resolve();h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return dict(path=str(p),bytes=p.stat().st_size,sha256=h.hexdigest())
def snapshot():
    import numpy as np
    if np.__version__!='1.26.4' or not Path(np.__file__).resolve().is_relative_to(ROOT):raise ValueError('Approved existing Linux NumPy provider required')
    keys=('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')
    if any(os.environ.get(k)!='1' for k in keys):raise ValueError('Single numeric thread caps')
    fe=ctypes.CDLL(None).fegetround()
    if fe!=0:raise ValueError('Host FE_TONEAREST required')
    if platform.machine()!='x86_64':raise ValueError('Pinned glibc x86_64 fenv layout required')
    env=ctypes.create_string_buffer(128)
    if ctypes.CDLL(None).fegetenv(env)!=0:raise ValueError('Host fenv read')
    x87=struct.unpack_from('<H',env.raw,0)[0];mxcsr=struct.unpack_from('<I',env.raw,28)[0]&~63
    if mxcsr!=0x1f80:raise ValueError('Expected SSE nearest/noFTZ/noDAZ control')
    paths={Path(np.__file__).resolve(),Path(np.core._multiarray_umath.__file__).resolve(),Path('/usr/include/x86_64-linux-gnu/bits/fenv.h')}
    for line in Path('/proc/self/maps').read_text().splitlines():
        words=line.split()
        if len(words)>=6 and (words[-1].startswith(str(ROOT)) or Path(words[-1]).name in ('libc.so.6','libm.so.6')) and '.so' in words[-1]:paths.add(Path(words[-1]))
    return dict(label='CURRENT_HOST_REPLAY',python=identity(sys.executable),python_version=sys.version,numpy_version=np.__version__,provider_files=[identity(p) for p in sorted(paths)],machine=platform.machine(),host_rounding=fe,x87_control_word=x87,mxcsr_control_ignoring_sticky_exception_flags=mxcsr,fenv_layout='glibc x86_64 fenv_t32; control@0 MXCSR@28',rounding_label='FE_TONEAREST',numpy_error_policy=np.geterr(),threads={k:os.environ[k] for k in keys},historical_runtime_identity=False,sh4_numeric_qualification=False)
