#!/usr/bin/env python3
"""Export selected structure offsets from a preserved, byte-bound SH4 ELF.

This reads debug information only. It never contacts a running emulator.
Requires pyelftools 0.32, installed separately in the private lane directory.
"""
import argparse
import hashlib
import json
from pathlib import Path

from elftools.elf.elffile import ELFFile


def name(die):
    item = die.attributes.get("DW_AT_name")
    return item.value.decode(errors="replace") if item else ""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("elf", type=Path)
    ap.add_argument("output", type=Path)
    a = ap.parse_args()
    wanted = {"GlobalWork", "cPlayer", "cEm", "cModel", "cCoord", "cEmMgr", "JOY", "PADStatus", "cSceSys", "SUB_SCREEN", "MotionWork", "cItemMgr", "ItemWork", "KeyWork", "SystemWork", "Camera", "CameraParam", "cPlBody", "cEm10", "Em10Work"}
    found = {}
    with a.elf.open("rb") as f:
        dwarf = ELFFile(f).get_dwarf_info()
        definitions = {}
        for cu in dwarf.iter_CUs():
            for die in cu.iter_DIEs():
                label = name(die)
                if label and die.tag in {"DW_TAG_structure_type", "DW_TAG_class_type", "DW_TAG_union_type"} and "DW_AT_byte_size" in die.attributes:
                    score = sum(c.tag in {"DW_TAG_member", "DW_TAG_inheritance"} for c in die.iter_children())
                    if label not in definitions or score > definitions[label][0]:
                        definitions[label] = (score, die)

        def info(die, prefix="", offset=0, depth=0):
            if depth > 12:
                return []
            out = []
            for child in die.iter_children():
                if child.tag not in {"DW_TAG_member", "DW_TAG_inheritance"}:
                    continue
                loc = child.attributes.get("DW_AT_data_member_location")
                delta = loc.value if loc else 0
                if not isinstance(delta, int):
                    raise ValueError(f"non-constant member offset in {name(die)}")
                target = child.get_DIE_from_attribute("DW_AT_type")
                while target.tag in {"DW_TAG_typedef", "DW_TAG_const_type", "DW_TAG_volatile_type"}:
                    target = target.get_DIE_from_attribute("DW_AT_type")
                if name(target) in definitions:
                    target = definitions[name(target)][1]
                field = name(child)
                if not field:
                    base = name(target) if child.tag == "DW_TAG_inheritance" else ""
                    out.extend(info(target, prefix + (base + "." if base else ""), offset + delta, depth + 1))
                else:
                    size = target.attributes.get("DW_AT_byte_size")
                    out.append(dict(name=prefix + field, offset=offset + delta,
                                    type=name(target), tag=target.tag,
                                    bytes=size.value if size else None))
            return out

        for label in sorted(wanted & definitions.keys()):
            die = definitions[label][1]
            found[label] = dict(bytes=die.attributes["DW_AT_byte_size"].value,
                                die_offset=die.offset, members=info(die))
    result = dict(elf_sha256=hashlib.sha256(a.elf.read_bytes()).hexdigest(),
                  read_only=True, found=found, missing=sorted(wanted - set(found)))
    if a.output.exists():
        raise SystemExit("refusing to overwrite layout receipt")
    a.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"found": list(found), "missing": result["missing"]}))


if __name__ == "__main__":
    main()
