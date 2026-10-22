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


def resolved(die):
    while die.tag in {"DW_TAG_typedef", "DW_TAG_const_type", "DW_TAG_volatile_type", "DW_TAG_restrict_type"}:
        die=die.get_DIE_from_attribute("DW_AT_type")
    return die

def describe(die, depth=0):
    die=resolved(die)
    if depth>12:raise ValueError("type recursion")
    out={"type":name(die),"tag":die.tag,"die_offset":die.offset}
    size=die.attributes.get("DW_AT_byte_size")
    out["bytes"]=size.value if size else None
    encoding=die.attributes.get("DW_AT_encoding")
    if encoding:out["encoding"]=encoding.value
    if die.tag=="DW_TAG_pointer_type":
        out["pointee"]=None
        if "DW_AT_type" in die.attributes:
            target=resolved(die.get_DIE_from_attribute("DW_AT_type"));out["pointee"]={"type":name(target),"tag":target.tag}
    if die.tag=="DW_TAG_array_type":
        element=describe(die.get_DIE_from_attribute("DW_AT_type"),depth+1);dims=[]
        for child in die.iter_children():
            if child.tag!="DW_TAG_subrange_type":continue
            low=child.attributes.get("DW_AT_lower_bound");low=low.value if low else 0
            count=child.attributes.get("DW_AT_count");upper=child.attributes.get("DW_AT_upper_bound")
            if count:count=count.value
            elif upper and isinstance(upper.value,int):count=upper.value-low+1
            else:raise ValueError("unbounded observer array")
            dims.append(count)
        out["element"]=element;out["dimensions"]=dims
        if element["bytes"] is not None:
            total=element["bytes"]
            for n in dims:total*=n
            out["bytes"]=total
    if die.tag in {"DW_TAG_structure_type","DW_TAG_union_type"} and not name(die) and out["bytes"] is not None and out["bytes"]<=32:
        out["aggregate_members"]=[]
        for child in die.iter_children():
            if child.tag!="DW_TAG_member":continue
            loc=child.attributes.get("DW_AT_data_member_location")
            delta=loc.value if loc else 0
            out["aggregate_members"].append({"name":name(child),"offset":delta,**describe(child.get_DIE_from_attribute("DW_AT_type"),depth+1)})
    return out

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

        def info(die, prefix="", offset=0, depth=0, route=None):
            route=route or []
            if depth > 12:
                return []
            out = []
            for child in die.iter_children():
                if child.tag not in {"DW_TAG_member", "DW_TAG_inheritance"}:
                    continue
                loc = child.attributes.get("DW_AT_data_member_location")
                if loc is None and die.tag!="DW_TAG_union_type":
                    raise ValueError(f"member location unavailable in {name(die)}")
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
                    out.extend(info(target, prefix + (base + "." if base else ""), offset + delta, depth + 1, route+[dict(name=field or base or "@anonymous",die_offset=child.offset,offset=delta,tag=child.tag)]))
                else:
                    meta=describe(target)
                    out.append(dict(name=prefix+field,offset=offset+delta,**meta,
                                    route=route+[dict(name=field,die_offset=child.offset,offset=delta,tag=child.tag)]))
            return out

        for label in sorted(wanted & definitions.keys()):
            die = definitions[label][1]
            found[label] = dict(bytes=die.attributes["DW_AT_byte_size"].value,
                                die_offset=die.offset, members=info(die))
    result = dict(schema=2,elf_sha256=hashlib.sha256(a.elf.read_bytes()).hexdigest(),
                  read_only=True, found=found, missing=sorted(wanted - set(found)))
    if a.output.exists():
        raise SystemExit("refusing to overwrite layout receipt")
    a.output.write_text(json.dumps(result, indent=2) + "\n", newline="\n")
    print(json.dumps({"found": list(found), "missing": result["missing"]}))


if __name__ == "__main__":
    main()
