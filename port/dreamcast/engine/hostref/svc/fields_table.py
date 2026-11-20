#!/usr/bin/env python3
"""fields_table.py: which cParts fields code outside the skeleton units reads and writes, from census runs of the
reference (census.py's census.json, RE4_SVC_TRACE=1). For SERVICES.md "Fields behaviour reads".

    fields_table.py <census dir>... [--md out.md]

One row per field and direction: the functions (unit), accesses per traced tick (the largest over the runs), how
many different bones, and the fixtures. The skeleton units' own accesses (model, motion, ik, ...) are left out:
those are what the native service replaces; so are accesses by the host and the census itself.
"""
import collections
import json
import sys

SKIP_FIELDS = {"be_flag", "pNext", "vptr"}


def main():
    dirs = [a for a in sys.argv[1:] if not a.startswith("--")]
    md = sys.argv[sys.argv.index("--md") + 1] if "--md" in sys.argv else None
    if md in dirs:
        dirs.remove(md)
    rows = collections.OrderedDict()
    for d in dirs:
        j = json.load(open(d + "/census.json"))
        traced = None
        for line in open(d + "/fields.tsv"):
            if line.startswith("# ticks"):
                traced = int(line.split("\t")[1])
                break
        name = d.rstrip("/").split("/")[-1]
        per = collections.defaultdict(lambda: [0, set(), 0])
        for f in j["fields"]:
            if f["region"] != "parts" or f["kind"] in ("skeleton", "host") or f["field"] in SKIP_FIELDS:
                continue
            key = (f["field"], "W" if f["write"] else "R")
            func = f["func"].split("(")[0] + " (" + f["unit"] + ")"
            r = per[key]
            r[0] += f["count"]
            r[1].add(func)
            r[2] |= int(f["bones"], 16)
        for key, (n, funcs, bones) in per.items():
            row = rows.setdefault(key, {"per_tick": 0.0, "funcs": set(), "bones": 0, "fixtures": []})
            row["per_tick"] = max(row["per_tick"], n / max(traced, 1))
            row["funcs"] |= funcs
            row["bones"] |= bones
            row["fixtures"].append(name)
    out = ["| Field | R/W | Accesses a tick (most) | Bones (index < 63) | Code | Fixtures |", "|---|---|---:|---:|---|---|"]
    for (field, rw), r in sorted(rows.items(), key=lambda x: (x[0][0], x[0][1])):
        out.append("| %s | %s | %.1f | %d | %s | %s |" % (field, rw, r["per_tick"], bin(r["bones"]).count("1"),
                                                          ", ".join(sorted(r["funcs"])), ", ".join(r["fixtures"])))
    text = "\n".join(out) + "\n"
    if md:
        open(md, "w").write(text)
    print(text)


if __name__ == "__main__":
    main()
