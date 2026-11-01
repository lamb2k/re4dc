#!/usr/bin/env python3
"""Preserve world receipts while interning repeated numeric traffic records.

No measured or modeled number is rounded or dropped. Only repeated traffic
objects, repetitive per-case command paths, and asserted-zero uncached/SQ
traffic are compacted. The full raw receipt hash identifies the original run.
"""
import argparse
import hashlib
import json
from pathlib import Path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    raw=args.input.read_bytes();data=json.loads(raw)
    assert data["status"]=="PASS"
    if "cases" in data:
        traffic={}
        for row in data["cases"]:
            value=row["traffic"]
            for region in ("uncached","store_queue"):
                assert all(x==0 for x in value.pop(region).values())
            prefetch=value.pop("prefetch")
            assert all(prefetch[k]==0 for k in ("requests","unique_requested_lines","sq_flush_requests"))
            value.pop("scope")
            key="traffic-"+digest(json.dumps(value,sort_keys=True,separators=(",",":")).encode())[:16]
            assert key not in traffic or traffic[key]==value
            traffic[key]=value;row["traffic"]=key
            row.pop("command");row["cold_icache"].pop("command")
        data["traffic_records"]=traffic
        data["traffic_scope"]="All data events are cached synthetic RAM. Zero uncached, SQ and prefetch traffic was asserted. Opcode fetches are excluded; literal loads retained. Distinct 32-byte lines are touches, not cache misses."
        data["model_commands"]={
            "warm":"hwsim --elf <model-address-view.elf> --out <case> --perfect-ic --perfect-dc --no-dma --sq-cost 0 <case.bin>",
            "cold_i":"hwsim --elf <model-address-view.elf> --out <case> --perfect-dc --no-dma --sq-cost 0 <case.bin>"}
    data["raw_receipt_sha256"]=digest(raw)
    data["compactor_sha256"]=digest(Path(__file__).read_bytes())
    with args.output.open("x") as f:
        json.dump(data,f,indent=2);f.write("\n")
    print(json.dumps(dict(status="PASS",input_bytes=len(raw),output_bytes=args.output.stat().st_size,output=str(args.output))))


if __name__=="__main__":main()
