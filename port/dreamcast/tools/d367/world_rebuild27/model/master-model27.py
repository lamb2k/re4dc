"""Master and independently verify the existing model-only CD-R transport."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

p = argparse.ArgumentParser()
p.add_argument("stage", type=Path)
p.add_argument("--tree", type=Path, required=True)
p.add_argument("--build", type=Path, required=True)
a = p.parse_args()
root = a.stage.resolve()
assert root.parent == Path("/root/re4data/private/world-rebuild27-20261027") and root.name.startswith("model-stage-")
out = root / "disc"
assert not out.exists(), "Use a new output, preserving the previous master"
env = dict(os.environ, PATH="/opt/toolchains/dc/sh-elf/bin:" + os.environ["PATH"])
with (root / "master.log").open("x") as stream:
    subprocess.run(["bash", str(Path(__file__).with_name("model-mkdisc27.sh")), str(a.build / "re4dc-game.elf"),
                    str(root / "data"), str(out)], check=True, env=env, stdout=stream, stderr=subprocess.STDOUT)
subprocess.run(["python3", str(a.tree / "port/dreamcast/tools/d367/fullplay/fp_iso.py"), "manifest", str(out / "disc.bin"),
                "--lba", "0", "-o", str(root / "disc-manifest.json")], check=True)
r = json.loads((root / "preparation.json").read_text())
master = json.loads((root / "disc-manifest.json").read_text())
before = r["data_manifest"]
assert set(master) == set(before) | {"1ST_READ.BIN"}
assert all(master[k] == before[k] for k in before), "On-disc asset differs from verified prepared tree"
sha = lambda q: hashlib.sha256(q.read_bytes()).hexdigest()
scrambled = root / "expected-scrambled.bin"
subprocess.run(["/root/work/kos/utils/scramble/scramble", str(root / "raw-program.bin"), str(scrambled)], check=True)
assert master["1ST_READ.BIN"]["sha256"] == sha(scrambled)
disc = out / "disc.bin"
with disc.open("rb") as stream:
    ip = stream.read(32768)
receipt = dict(disc_sha256=sha(disc), disc_bytes=disc.stat().st_size, programme=master["1ST_READ.BIN"],
               raw_program_sha256=r["raw_program_sha256"], elf_sha256=r["elf_sha256"],
               generated_cdr_ip_sha256=hashlib.sha256(ip).hexdigest(),
               source_gdi_ip_sha256=sha(root.parent / "stage-source-IP.BIN"),
               all_game_files_matched_prepared_tree=True, files=len(master),
               transport="MODELLED only; stock LBA0 CD-R with generated CD-ROM boot IP and scrambled programme; no GDEMU parity claimed")
(root / "master-identity.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt, indent=2))
