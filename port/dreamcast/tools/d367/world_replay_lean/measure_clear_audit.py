#!/usr/bin/env python3
"""Record a narrow production/fixture disassembly audit of constructor clears.

This is not a claim that the whole setup fixture is byte-identical to production.
It records the real replay lambda, the literal R6 lengths immediately preceding
its constructor memset calls, and nearby instructions for independent review.
The production caller retains real geometry; the fixture has a controlled edge.
Different capture/register allocation and inlining can change other instructions.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def function(text,match):
    starts=list(re.finditer(r"^([0-9a-f]+) <([^\n]+)>:\n",text,re.M))
    found=[(i,m) for i,m in enumerate(starts) if match(m.group(2))]
    assert len(found)==1,[(m.group(1),m.group(2)) for _,m in found]
    index,start=found[0]
    end=starts[index+1].start() if index+1<len(starts) else len(text)
    return start.group(2),int(start.group(1),16),text[start.start():end]


def calls(body,base,lengths):
    rows=[]
    for line in body.splitlines():
        m=re.match(r"\s*([0-9a-f]+):\s+(?:[0-9a-f]{2}\s+){2}\s*(\S+)\s*(.*)",line)
        if m:
            rows.append((int(m.group(1),16),m.group(2),m.group(3),line))
    result=[];begin=0
    for expected in lengths:
        matches=[]
        for i in range(begin,len(rows)):
            address,op,operand,line=rows[i]
            immediate=re.match(r"#(-?\d+),r6\b",operand) if op=="mov" else None
            literal=re.search(r",r6\s+!\s+([0-9a-f]+)\b",operand) if op in ("mov.w","mov.l") else None
            value=int(immediate.group(1)) if immediate else int(literal.group(1),16) if literal else None
            if value==expected:
                matches.append(i)
        assert matches,(expected,"constructor length absent")
        index=matches[0]
        following=[i for i in range(index+1,min(index+33,len(rows))) if rows[i][1]=="jsr"]
        assert following,(expected,"nearby indirect call absent")
        call=following[0]
        assert not any(re.search(r",r6\s*(?:!|$)",rows[i][2]) for i in range(index+1,call)),"R6 changed before call"
        result.append(dict(requested_bytes=expected,
            argument_load_offset=hex(rows[index][0]-base),call_offset=hex(rows[call][0]-base),
            argument_instruction=rows[index][3],call_instruction=rows[call][3],
            review_excerpt="\n".join(row[3] for row in rows[max(0,index-2):call+2])))
        begin=call+1
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--production",type=Path,required=True)
    parser.add_argument("--target-build",type=Path,required=True)
    parser.add_argument("--objdump",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    target=json.loads(args.target_build.read_text())
    production=json.loads((args.production/"build-controls.json").read_text())
    assert target["status"]==production["status"]=="PASS"
    rows=[]
    for replay,label in ((0,"zero"),(1,"on")):
        lengths=[776,209] if replay==0 else [36,776,209]
        for kind,path in (("production",args.production/f"s1-b0-native_static-{label}.o"),
                          ("fixture",Path(target["arms"][f"r{replay}-b0"]["elf"]))):
            assembly=subprocess.check_output([str(args.objdump),"-drC",str(path)],text=True)
            name,base,body=function(assembly,lambda name:
                ("ps2_pass" in name if kind=="production" else name.startswith("fixture_replay"))
                and "lambda()#1" in name and "operator()" in name)
            assert "memset" in body
            clear_calls=calls(body,base,lengths)
            rows.append(dict(kind=kind,replay=replay,artifact_sha256=sha(path),function=name,
                function_disassembly_sha256=hashlib.sha256(body.encode()).hexdigest(),
                function_disassembly=body,clear_calls=clear_calls,
                requested_clear_bytes=sum(lengths),
                frequency="Each queued replay part" if replay==0 else "Once per nonempty replay batch"))
    result=dict(status="PASS",scope=__doc__,
        production_receipt_sha256=sha(args.production/"build-controls.json"),
        target_build_receipt_sha256=sha(args.target_build),rows=rows,
        reviewed_interpretation=[
            "Both production and controlled target compile the same 776-byte and 209-byte overlapping clears.",
            "Baseline repeats those clears inside its per-part replay loop.",
            "Candidate moves them before the loop, adds one 36-byte material snapshot clear, and uses narrow restart stores per row.",
            "These requested clear lengths include overlap; they are not distinct bytes or cache-miss counts.",
            "The dominant store reduction is supported by untouched production code; other fixture instruction costs remain model estimates."])
    args.output.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(dict(status=result["status"],output=str(args.output))))


if __name__=="__main__":
    main()
