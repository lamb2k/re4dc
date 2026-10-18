"""Apply recorded Codex PowerShell patches (here-string $old/$new + .Replace chains) to a file.
usage: c4r-psapply.py <in> <out> <patch.txt>...  (prints sha256 of out)"""
import hashlib, re, sys
sys.path.insert(0, __file__.rsplit('\\', 1)[0] if '\\' in __file__ else '.')
from importlib import util
spec = util.spec_from_file_location('cxb', __file__.replace('c4r-psapply.py', 'c4r-cxlib.py'))
L = util.module_from_spec(spec); spec.loader.exec_module(L)

src = open(sys.argv[1], encoding='utf-8', newline='').read()
for p in sys.argv[3:]:
    cmd = open(p, encoding='utf-8', newline='').read()
    # only the part that patches the first $p file (stop at the first WriteAllText)
    cut = cmd.find('WriteAllText')
    seg = cmd[:cut]
    src, n = L.apply(src, seg)
    print(p, 'replaces', n)
open(sys.argv[2], 'w', encoding='utf-8', newline='').write(src)
print(hashlib.sha256(src.encode('utf-8')).hexdigest())
