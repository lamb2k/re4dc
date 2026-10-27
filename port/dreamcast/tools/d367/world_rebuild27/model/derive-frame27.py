"""Derive the external frame mark from this ELF's own DWARF and symbols."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("elf", type=Path)
parser.add_argument("--out", type=Path, required=True)
args = parser.parse_args()
tool = "/opt/toolchains/dc/sh-elf/bin/sh-elf-"
symbols = {}
for line in subprocess.check_output([tool + "nm", "-S", str(args.elf)], text=True).splitlines():
    fields = line.split()
    if len(fields) == 4 and fields[-1] in ("_Global", "_pG"):
        symbols[fields[-1]] = {"address": int(fields[0], 16), "size": int(fields[1], 16)}
assert set(symbols) == {"_Global", "_pG"}, symbols
proc = subprocess.Popen([tool + "readelf", "--debug-dump=info", str(args.elf)], stdout=subprocess.PIPE, text=True)
offsets = set()
stack = []
for line in proc.stdout:
    tag = re.match(r"\s*<(\d+)><[0-9a-f]+>:", line)
    if tag:
        d = int(tag.group(1))
        while stack and stack[-1]["depth"] >= d:
            stack.pop()
        kind = re.search(r"\((DW_TAG_\w+)\)", line)
        stack.append(dict(depth=d, kind=kind.group(1) if kind else None, name=None))
        continue
    if stack and "DW_AT_name" in line:
        stack[-1]["name"] = line.rsplit(":", 1)[-1].strip()
    if stack and "DW_AT_data_member_location" in line and stack[-1]["name"] == "Frame_cnt":
        if stack[-1]["kind"] == "DW_TAG_member" and len(stack) >= 2 and stack[-2]["name"] == "GlobalWork":
            offsets.add(int(line.rsplit(":", 1)[-1].strip(), 0))
assert proc.wait() == 0
assert len(offsets) == 1, offsets
offset = offsets.pop()
virtual = symbols["_Global"]["address"] + offset
physical = virtual & 0x1fffffff
result = dict(elf=str(args.elf.resolve()), elf_sha256=hashlib.sha256(args.elf.read_bytes()).hexdigest(),
              source="ELF DWARF GlobalWork::Frame_cnt and ELF _Global symbol; src/game/main.cpp binds pG=&Global",
              symbols=symbols, frame_offset=offset, virtual=f"{virtual:08x}", physical=f"{physical:08x}")
args.out.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
