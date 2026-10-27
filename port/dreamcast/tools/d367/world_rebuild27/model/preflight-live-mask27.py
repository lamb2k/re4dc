"""Prepare the next cost arm only after main provides its exact build identity."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

p = argparse.ArgumentParser()
p.add_argument("--build", type=Path, required=True)
p.add_argument("--expected-elf", required=True)
p.add_argument("--out", type=Path, required=True)
a = p.parse_args()
sha = lambda q: hashlib.sha256(q.read_bytes()).hexdigest()
base = Path("/mnt/c/Flycast-Evidence/re4-dreamcast/world-rebuild27-20261027/hwmodel-v1-B1-cross")
old = Path("/root/re4data/private/world-rebuild27-20261027/model-stage-v1-B1")
assert sha(base / "re4dc-game.elf") == "9b669d1e6ab7a568fae586836bae52254ee0692344a4c8eca8c05e29b0c58a30"
assert sha(a.build / "re4dc-game.elf") == a.expected_elf
assert not a.out.exists()
def scalars(path):
    return dict(re.findall(r"^([A-Z][A-Z0-9_]*)=([A-Za-z0-9_.+-]+)$", path.read_text(), re.M))
x, y = scalars(base / "resolved-knobs.txt"), scalars(a.build / "resolved-knobs.txt")
assert y["WORLD_REBUILD27_LIVE_MASK"] == "1"
for name, value in dict(PC_SAMPLER="0", WORLD_CENSUS24="0", WORLD_METER="0", PACE_MODE="off", QA_MENU="0", GAME_PWC_DIAG="0", ALIVE_CAP="4", R101_ALIVE_CAP="4").items():
    assert y[name] == value, (name, y.get(name))
changes = {k:dict(before=x.get(k), after=y.get(k)) for k in sorted(x.keys() | y.keys()) if x.get(k) != y.get(k)}
unexpected = {k:v for k,v in changes.items() if k != "WORLD_REBUILD27_LIVE_MASK"}
assert not unexpected, unexpected
fixture = Path("/mnt/c/Flycast-Evidence/re4-dreamcast/world-rebuild27-20261027/fixtures-v1/cross.txt")
assert sha(fixture) == "8f426115341a7c60f1bfc053a516fa7c87440b28f65c6719c3f74ce49216f983"
a.out.mkdir(parents=True)
subprocess.run(["python3", str(Path(__file__).with_name("derive-frame27.py")), str(a.build / "re4dc-game.elf"), "--out", str(a.out / "frame-mark.json")], check=True)
record = dict(scope="Preflight only; no build or guest launched", old_evidence=str(base), old_master=str(old),
              new_build=str(a.build), old_elf_sha256=sha(base / "re4dc-game.elf"), new_elf_sha256=a.expected_elf,
              scalar_knob_changes=changes, fixture_sha256=sha(fixture), count="300:329", trace="300:329:29", seconds=55,
              limitation="Only simple scalar resolved values are compared here; full resolved files and data manifest are also bound in capture evidence. Changed programme addresses remain part of the measured whole change.")
(a.out / "preflight.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps(record, indent=2))
