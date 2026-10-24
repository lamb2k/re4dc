"""Bind newly received actual poststage evidence; preserve earlier UNKNOWN templates."""
from pathlib import Path
import json,sys,types
HERE=Path(__file__).resolve().parent
p=HERE/'common.py';c=types.ModuleType('guest_common');c.__file__=str(p);sys.modules[c.__name__]=c;exec(compile(p.read_bytes(),str(p),'exec'),c.__dict__);k=c.context()
root=c.META_ROOTS[1];final=root/'FINAL-READBACK.json';assert c.sha(final)=='4dd7b532825d198b4f35f7f2cea576638e37339fc9e5e04cb5a4b4dd5fd7bb49'
grant=c.read(HERE/'ROOT-GUEST-GRANT-TEMPLATE.json');grant['poststage']={'path':str(final),'identity':c.row(final)};grant['metadata_allowlists'][str(root)]=sorted(str(p.relative_to(root)) for p in root.rglob('*') if p.is_file())
for arm in ['off','on']:c.check_poststage(grant,k,arm,hash_tracks=False)
(HERE/'ROOT-GUEST-GRANT-TEMPLATE.json').rename(HERE/'ROOT-GUEST-GRANT-TEMPLATE-UNBOUND.json');c.fresh(HERE/'ROOT-GUEST-GRANT-TEMPLATE.json',grant)
c.fresh(HERE/'POSTSTAGE-PINS.json',dict(actual_final={'path':str(final),'identity':c.row(final)},seal={'path':str(root/'REVIEW-SEAL.json'),'identity':c.row(root/'REVIEW-SEAL.json')},static_only=True,guest_permission=False))
print(json.dumps(dict(status='ACTUAL_POSTSTAGE_BOUND_NO_GUEST',resources=c.capacity(k))))
