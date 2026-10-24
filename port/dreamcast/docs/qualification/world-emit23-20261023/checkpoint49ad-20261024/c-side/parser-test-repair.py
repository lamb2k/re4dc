from pathlib import Path
p=Path('/root/work/lanes/world-emit23-census/port/dreamcast/tools/d367/world_emit23/test_census.py')
s=p.read_text()
needle='        checks["actual-log-parser-and-five-negatives"]="PASS"'
replacement='''        checks["actual-log-parser-and-five-negatives"]="PASS"
        lines=[line for line in captured.splitlines() if line.startswith("WEC23 ")]
        q2=[line for line in lines if " q=2" in line]
        remaining=[line for line in lines if " q=2" not in line]
        def log(lines):return "\\n".join(lines)+"\\n"
        # A valid globally second flush can occur in another active pass.
        before_p1_end=next(i for i,line in enumerate(remaining) if line.startswith("WEC23 PASS_END") and " p=1 " in line)
        multipass=remaining[:before_p1_end]+[line.replace(" p=0 "," p=1 ") for line in q2]+remaining[before_p1_end:]
        assert [x["pass"] for x in parse(log(multipass),0x101)["flushes"]]==[0,1]
        protocol={
            "flush-after-frame-end":log(remaining+q2),
            "flush-wrong-active-pass":log([line.replace(" p=0 "," p=1 ") if " q=2" in line else line for line in lines]),
            "reverse-complete-records":log(list(reversed(lines))),
            "future-threshold":captured.replace("threshold=360","threshold=999999"),
            "zero-threshold":captured.replace("threshold=360","threshold=0"),
            "out-of-range-threshold":captured.replace("threshold=360","threshold=10000001"),
            "global-flush-id-reuse":log([line.replace(" q=2 "," q=1 ") for line in multipass]),
            "global-flush-id-gap":log([line.replace(" q=2 "," q=3 ") for line in lines]),
            "duplicate-begin":log([lines[0]]+lines),
            "record-after-frame-end":log(lines+[lines[1]]),
        }
        swapped=list(lines);at=next(i for i,line in enumerate(swapped) if line.startswith("WEC23 PART "))
        swapped[at],swapped[at+1]=swapped[at+1],swapped[at]
        protocol["counts-before-part"]=log(swapped)
        swapped=list(lines);at=next(i for i,line in enumerate(swapped) if line.startswith("WEC23 FLUSH_COUNTS "))
        swapped[at],swapped[at+1]=swapped[at+1],swapped[at]
        protocol["flush-end-before-counts"]=log(swapped)
        for name,altered in protocol.items():
            try:parse(altered,0x101)
            except ValueError:checks["protocol-"+name]="REJECTED"
            else:raise AssertionError("ordered protocol accepted "+name)
        checks["actual-log-valid-multipass"]="PASS"'''
assert s.count(needle)==1;s=s.replace(needle,replacement)
p.write_text(s)
