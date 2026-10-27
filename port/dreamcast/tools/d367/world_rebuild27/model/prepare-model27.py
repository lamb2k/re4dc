"""Prepare a private CD-R model arm from the full pinned release file tree."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

p = argparse.ArgumentParser()
p.add_argument("--arm", choices=("A", "B1", "C4"), required=True)
p.add_argument("--root", type=Path, required=True)
p.add_argument("--build", type=Path, required=True)
p.add_argument("--fixture", type=Path, required=True)
args = p.parse_args()
private = Path("/root/re4data/private/world-rebuild27-20261027")
source = private / "stage-source-A"
reference = json.loads((private / "stage-source-manifest.json").read_text())
out = args.root.resolve()
assert not out.exists() and source not in out.parents
sha = lambda q: hashlib.sha256(q.read_bytes()).hexdigest()
def manifest(tree):
    return {str(q.relative_to(tree)): dict(size=q.stat().st_size, sha256=sha(q)) for q in tree.rglob("*") if q.is_file()}
assert manifest(source) == reference, "Pinned full release tree changed"
out.mkdir(parents=True)
data = out / "data"
shutil.copytree(source, data, copy_function=os.link)
def replace(destination, src):
    if destination.exists():
        destination.unlink()
    shutil.copyfile(src, destination)
allow = {"1ST_READ.BIN", "dc/warp.txt"}
for q in sorted(args.build.glob("*.ovl")):
    destination = data / "dc" / q.name
    replace(destination, q)
    allow.add("dc/" + q.name)
assert len(list(args.build.glob("*.ovl"))) == 15
candidate = {"A": None, "B1": "B1-structural-floor", "C4": "C4-exact-protected-pieces"}[args.arm]
rel = Path("dc/native/r101")
if candidate:
    for name in ("ps2-world.r4pw", "ps2-world.ids", "ps2-world.r4tc", "room.r4rc"):
        assert sha(private / candidate / name) == sha(source / rel / name), name
    for name in ("ps2-world.re4mesh", "ps2-world.r4sg"):
        replace(data / rel / name, private / candidate / name)
        allow.add(str(rel / name))
replace(data / "dc/warp.txt", args.fixture)
# The existing CD-R packer creates the scrambled boot programme before it
# hard-links DATA. Remove only the new clone's inherited boot-programme link.
(data / "1ST_READ.BIN").unlink()
before = manifest(data)
unexpected = [k for k in set(reference) | set(before) if reference.get(k) != before.get(k) and k not in allow]
assert not unexpected, unexpected
tool = "/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy"
subprocess.run([tool, "-R", ".stack", "-O", "binary", str(args.build / "re4dc-game.elf"), str(out / "raw-program.bin")], check=True)
receipt = dict(arm=args.arm, source=str(source), source_files=len(reference), source_manifest_sha256=sha(private / "stage-source-manifest.json"),
               fixture_sha256=sha(args.fixture), build=str(args.build), elf_sha256=sha(args.build / "re4dc-game.elf"),
               raw_program_sha256=sha(out / "raw-program.bin"), allowed_differences=sorted(allow),
               data_manifest=before, transport="MODELLED only: existing single-track LBA0 MODE1/2048 CD-R packer, scrambled boot programme and generated CD-ROM IP.BIN")
(out / "preparation.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({k:v for k,v in receipt.items() if k != "data_manifest"}, indent=2))
