#!/usr/bin/env python3
"""Host-only footprint of extracted Build32 producer, allocator, registry, and consumer."""
from pathlib import Path
import importlib.util
import re
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("skin_admit32", HERE / "skin_admit32.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def sections(path: Path) -> dict[str, int]:
    lines = subprocess.check_output(["size", "-A", str(path)], text=True).splitlines()
    result = {".text": 0, ".bss": 0, ".data": 0}
    for line in lines:
        words = line.split()
        if len(words) >= 2 and words[0] in result:
            result[words[0]] = int(words[1])
    return result


def stack(path: Path) -> dict[str, int]:
    result = {}
    for line in path.read_text().splitlines():
        fields = line.rsplit("\t", 2)
        if len(fields) == 3:
            for name in ("re4dc_actor_skin_admit", "re4dc_actor_skin_commit",
                         "re4dc_skin_defer_lazy", "cost_pending", "re4dc_prim_tail"):
                if name in fields[0]:
                    result[name] = max(result.get(name, 0), int(fields[1]))
    return result


def main() -> None:
    source = mod.fixture(False).split("#define CHECK(x)")[0]
    source += '\nextern "C" int cost_pending(cModel* m,cModelInfo* i,ModelData* d,int* built){return skinDeferPending(m,i,d,built);}\n'
    with tempfile.TemporaryDirectory(prefix="re4dc-skin-cost32-") as td:
        directory = Path(td)
        rows = []
        for enabled in (0, 1):
            path = directory / f"production{enabled}.cpp"
            obj = directory / f"production{enabled}.o"
            path.write_text(source)
            cmd = ["g++", "-std=c++20", "-O2", "-fstack-usage", "-DRE4DC_GAME=1",
                   "-DRE4DC_PRIMITIVE_BUFFERS=1", "-DRE4DC_ACTOR_TRANSACTION=1",
                   "-DRE4DC_ACTOR_SKIN_RESERVE=1", "-DRE4DC_NATIVE_ACTOR_SKIN_LAZY=1",
                   "-DRE4DC_SKIN_PALETTE_LAZY=1", "-DRE4DC_NATIVE_ACTOR_SKIN=1",
                   "-DRE4DC_ACTOR_SKIN_OWNER_POOL=0", f"-DRE4DC_SKIN_ADMISSION32={enabled}",
                   "-c", str(path), "-o", str(obj)]
            subprocess.run(cmd, check=True, capture_output=True)
            rows.append((sections(obj), stack(obj.with_suffix(".su"))))
        for enabled, (section, usage) in enumerate(rows):
            print(f"enabled={enabled} sections={section} stack={usage}")
        print("delta_host_only=" + str({key: rows[1][0][key] - rows[0][0][key] for key in rows[0][0]}))
        print("SH-4 declared ticket layout=28 bytes, persistent sidecar=28+4 serial=32 bytes before alignment; target linked text/stack unmeasured")


if __name__ == "__main__":
    main()
