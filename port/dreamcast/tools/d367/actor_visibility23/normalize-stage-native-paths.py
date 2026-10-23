from pathlib import Path
import hashlib,json,copy
L=Path(__file__).resolve().parent
src=Path('C:/Flycast-Evidence/re4-dreamcast/pvs23-20261022/actor23-bea2d402-on-q01/stage-receipt.json')
pin='0dd7482f61af065e66edae065cd165b983eeaf5833503262a18ec3389ef58430'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sha(src)!=pin:raise ValueError('Original stage changed')
b=json.loads((L/'native-census-bea2r2/BINDINGS.json').read_bytes())
s=json.loads(src.read_bytes());d=copy.deepcopy(s);changes={}
for k in ('ownership_audit','kos_receipt','module_roster'):
 p,q=Path(s[k]['path']),Path(b[k]['path'])
 if any(x.is_symlink() or not x.is_file() for x in (p,q)) or p.resolve()!=q.resolve() or not p.samefile(q) or s[k]['sha256']!=b[k]['sha256'] or sha(p)!=b[k]['sha256']:raise ValueError(k)
 if s[k]['path']!=b[k]['path']:changes[k]=dict(before=s[k]['path'],after=b[k]['path'])
 d[k]['path']=b[k]['path']
d['native_path_provenance']=dict(original=dict(path=str(src),sha256=pin),changes=changes,scope='Receipt path spelling only; original staged programme, assets, members and fixture unchanged.')
out=src.with_name('stage-receipt-native-paths.json')
with out.open('x') as f:f.write(json.dumps(d,sort_keys=True,indent=2)+'\n')
print(json.dumps(dict(path=str(out),sha256=sha(out),changes=changes),indent=2))