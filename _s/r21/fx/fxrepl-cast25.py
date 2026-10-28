"""Replace keys of a base tex.pak with the .re4tex packages of one dir (fx_ps2_pack pack semantics). Writes out pak + sidecar."""
import hashlib, json, sys
from pathlib import Path
sys.path.insert(0, "/root/work/lanes/cast-ps2-25/port/dreamcast/tools/d367")
import tex_merge, texpack

base_path, out_path, side_path, d = sys.argv[1:5]
base = tex_merge.read(base_path)
merged = dict(base)
changed, added = [], []
for f in sorted(Path(d).glob("*.re4tex")):
    key = tuple(int(v, 16) for v in f.stem.split("-"))
    data = f.read_bytes()
    if key in base:
        if base[key] != data:
            changed.append(f.stem)
    else:
        added.append(f.stem)
    merged[key] = data
blob, count = texpack.build(merged)
Path(out_path).write_bytes(blob)
sha = lambda b: hashlib.sha256(b).hexdigest()
side = dict(base=sha(Path(base_path).read_bytes()), out=sha(blob), count=count, added=added, changed=changed)
json.dump(side, open(side_path, "w"), indent=1)
print("replaced", len(changed), "added", len(added), "count", count, side["out"][:16])
