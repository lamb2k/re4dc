#!/usr/bin/env python3
"""Reject missing KOS cache replacements before link.sh can generate stubs."""
import argparse
from pathlib import Path
import subprocess
from prepare import validate

SYMBOL = "_arch_dcache_wback_all_p2"
ROOTS = {
    "exec": "_arch_exec_at",
    "dmac": "_dma_map_src",
    "g1ata": "_g1_ata_write_lba_dma",
    "broadband_adapter": "_bba_tx",
}


def check(prefix, directory, kos=None):
    if kos is not None:
        validate(kos)
    for name, root in ROOTS.items():
        symbols = subprocess.check_output([prefix + "nm", str(directory / (name + ".o"))], text=True)
        entries = {tuple(line.split()[-2:]) for line in symbols.splitlines()}
        if ("U", SYMBOL) not in entries:
            raise ValueError(name + ": missing P2 helper reference")
        if ("T", root) not in entries:
            raise ValueError(name + ": missing archive replacement root " + root)
    symbols = subprocess.check_output([prefix + "nm", str(directory / "cache_p2.o")], text=True)
    entries = {tuple(line.split()[-2:]) for line in symbols.splitlines()}
    if ("T", SYMBOL) not in entries:
        raise ValueError("P2 helper must be a real defined function")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--kos-root", type=Path, required=True)
    args = parser.parse_args()
    check(args.prefix, args.directory, args.kos_root)
    print("KOS_CACHE_P2: all four KOS replacements and real P2 helper present")


if __name__ == "__main__":
    main()
