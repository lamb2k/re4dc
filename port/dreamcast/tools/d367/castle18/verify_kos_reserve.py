#!/usr/bin/env python3
"""Verify exact guest KOS reserve receipts and logged headroom.

This does not establish program identity, scene coverage, or route acceptance.
An unrelated byte count, such as an AICA stream size, is never a receipt.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re

RECEIPT = re.compile(
    r"^kos squeeze:\s+held=(\d+)\s+requested=(\d+)\s+frag=(\d+)\s+pieces=(\d+)\b.*$"
)
WATCH = re.compile(r"^kos watch:.*\bmin=(\d+)\b")


def verify(text, held=49152, minimum=4096, fragmented=None):
    rows = []
    watches = []
    for line in text.splitlines():
        match = RECEIPT.fullmatch(line)
        if match:
            row = dict(zip(("held", "requested", "frag", "pieces"),
                           map(int, match.groups())))
            row["receipt"] = line
            rows.append(row)
        match = WATCH.match(line)
        if match:
            watches.append(int(match.group(1)))
    if not rows:
        raise ValueError("No complete guest kos squeeze receipt")
    for row in rows:
        if row["held"] != held or row["requested"] != held:
            raise ValueError("Guest reserve differs from requirement: " + row["receipt"])
        if held and row["pieces"] < 1:
            raise ValueError("Nonzero reserve has no allocated pieces")
        if row["frag"] not in (0, 1) or (
                fragmented is not None and row["frag"] != fragmented):
            raise ValueError("Unexpected fragmentation mode: " + row["receipt"])
    if not watches:
        raise ValueError("No guest kos watch minimum; scene headroom is unproven")
    if min(watches) < minimum:
        raise ValueError(f"Logged headroom {min(watches)} is below {minimum}")
    return {"receipts": rows, "minimum_logged_headroom": min(watches),
            "required_reserve": held, "required_minimum": minimum,
            "scope": "Exact guest reserve and logged headroom only; identity, "
                     "scene coverage and progression require separate gates."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--held", type=int, default=49152)
    parser.add_argument("--minimum", type=int, default=4096)
    parser.add_argument("--fragmented", type=int, choices=(0, 1))
    args = parser.parse_args()
    if args.held < 0 or args.minimum < 0:
        parser.error("Reserve and minimum must be nonnegative")
    raw = args.log.read_bytes()
    body = gzip.decompress(raw) if args.log.suffix == ".gz" else raw
    try:
        result = verify(body.decode("utf-8", errors="replace"), args.held,
                        args.minimum, args.fragmented)
    except ValueError as error:
        print(json.dumps({"status": "FAIL", "reason": str(error)}))
        return 1
    result.update(status="PASS", log=str(args.log),
                  log_bytes_sha256=hashlib.sha256(raw).hexdigest())
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
