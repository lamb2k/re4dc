#!/usr/bin/env python3
"""Replay selected sealed cone traces with hwsim's default instruction cache.

This is a cold-cache synthetic link-layout sensitivity study. Data accesses,
DMA and store-queue bus cost remain excluded; no hardware or scene claim.
"""
import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    out = args.output.resolve()
    source = args.target.resolve() / "target-controls.json"
    original = json.loads(source.read_text())
    rows = []
    for row in original["cases"]:
        if row.get("mode") not in (0, 1):
            continue
        if not ((row["case"] == "front-grid64-294indices" and row["batch"] in (1, 6))
                or (row["case"] in ("off-axis-grid64", "front-nonplanar-rotated-grid36",
                                    "front-nonplanar-rotated-grid64") and row["batch"] == 1)):
            continue
        old_command = row["pipeline"]["command"]
        trace = Path(old_command[-1])
        assert sha(trace) == row["pipeline"]["trace_sha256"]
        name = "%s-batch%d-mode%d" % (row["case"], row["batch"], row["mode"])
        prefix = out / name
        command = [item for item in old_command if item != "--perfect-ic"]
        command[command.index("--out") + 1] = str(prefix)
        assert "--perfect-dc" in command and "--no-dma" in command
        assert command[command.index("--sq-cost") + 1] == "0"
        result = subprocess.run(command, capture_output=True, text=True)
        prefix.with_suffix(".log").write_text(result.stdout + result.stderr)
        assert not result.returncode, result.stderr
        totals = dict(line.split() for line in prefix.with_suffix(".sum.txt").read_text().splitlines())
        assert int(totals["insns"]) == row["instructions"]
        for key in ("dfills_per_frame", "writebacks_per_frame", "dma_bytes_per_frame",
                    "dma_starts_per_frame", "dma_bus_cycles_per_frame"):
            assert float(totals[key]) == 0, (name, key, totals[key])
        with prefix.with_suffix(".pcs.tsv").open() as stream:
            pcs = list(csv.DictReader(stream, delimiter="\t"))
        assert sum(int(pc["exec"]) for pc in pcs) == row["instructions"]
        categories = {key: sum(float(pc[key]) for pc in pcs)
                      for key in ("base", "dep_load", "dep_fpu", "dep_fdiv", "dep_other",
                                  "flock", "branch", "imiss", "dmiss", "pfwait", "sq", "uncached")}
        assert all(categories[k] == 0 for k in ("dmiss", "pfwait", "sq", "uncached"))
        assert categories["imiss"] > 0 and float(totals["ifills_per_frame"]) > 0
        rows.append(dict(case=row["case"], batch=row["batch"], mode=row["mode"],
                         instructions=row["instructions"], accepted=row["accepted"],
                         perfect_ic_cycles=row["pipeline"]["model_cycles"],
                         default_ic_cycles=int(totals["cycles"]),
                         instruction_line_fills=int(float(totals["ifills_per_frame"])),
                         categories=categories, command=command,
                         trace_sha256=sha(trace)))
    assert len(rows) == 10
    report = dict(status="PASS", scope=__doc__, cases=rows,
                  primary_receipt=str(source), primary_receipt_sha256=sha(source),
                  model_source_sha256=original["pipeline_model"]["source_sha256"],
                  model_binary_sha256=sha(Path(rows[0]["command"][0])),
                  model_elf_sha256=sha(Path(rows[0]["command"][rows[0]["command"].index("--elf") + 1])),
                  original_elf_sha256=original["elf_sha256"],
                  instruction_cache="hwsim default cold 8 KiB direct mapped, 32-byte lines, IIX=0",
                  flags=["--perfect-dc", "--no-dma", "--sq-cost", "0"],
                  limits="Only these synthetic instruction traces and their standalone link layout. No other renderer code or data traffic; no warmed scene cache, PVR, DMA, hardware time, or FPS claim.")
    path = out / "icache-sensitivity.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    for row in rows:
        print(row["case"], row["batch"], row["mode"], row["perfect_ic_cycles"],
              row["default_ic_cycles"], row["instruction_line_fills"])
    print("PASS", path)


if __name__ == "__main__":
    main()
