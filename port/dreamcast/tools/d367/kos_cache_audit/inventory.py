#!/usr/bin/env python3
"""Source token census, not runtime reachability or a linked-program call graph."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from prepare import COMMENT, validate

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
API = re.compile(r"\b((?:arch_)?dcache_(?:wback|flush)_(?:all|range)|"
                 r"DC(?:Flush|Store)Range(?:NoSync)?|RE4DC_DCACHE_WBACK|"
                 r"dma_map_src|arch_exec(?:_at)?|g1_ata_write_lba_dma|"
                 r"sci_(?:spi_)?dma_write_data|pvr_dma_transfer|pvr_txr_load_dma|"
                 r"pvr_dma_load_ta|pvr_dma_yuv_conv|pvr_txr_load_kimg)\b")


def census(root, folders):
    paths = subprocess.check_output(["rg", "--files", *folders, "-g", "*.c", "-g", "*.cpp",
        "-g", "*.h", "-g", "*.hpp", "-g", "*.inc", "-g", "*.s", "-g", "*.S"],
        cwd=root, text=True).splitlines()
    result, hashes = [], {}
    for relative in sorted(paths):
        text = (root / relative).read_text()
        plain = COMMENT.sub(lambda m: "\n" * m[0].count("\n"), text)
        for match in API.finditer(plain):
            line = plain.count("\n", 0, match.start()) + 1
            original = text.splitlines()[line - 1].strip()
            role = "reference (call, macro alias or address-taking)"
            if re.search(r"\b(?:void|int|dma_addr_t|sci_result_t)\s+" + re.escape(match[1]) + r"\s*\(", original):
                role = "definition or declaration"
            elif original.startswith("#define"):
                role = "macro definition"
            result.append(dict(path=relative, line=line, symbol=match[1], role=role, source=original))
            hashes[relative] = hashlib.sha256((root / relative).read_bytes()).hexdigest()
    return dict(references=result, source_sha256=hashes)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kos-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    _, callers = validate(args.kos_root)
    result = dict(scope=__doc__, base=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
        text=True).strip(), kos_inline_callers=callers,
        repository=census(ROOT, ["src", "include", "port/dreamcast/game", "port/dreamcast/room", "port/dreamcast/engine"]),
        kos=census(args.kos_root, ["kernel", "include", "addons"]))
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: len(result[key]["references"]) for key in ("repository", "kos")}))


if __name__ == "__main__":
    main()
