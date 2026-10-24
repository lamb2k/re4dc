"""Read ordered WEC23 one-frame census; no timing/acceptance inference."""
from pathlib import Path
import argparse,json
FIELDS=("plain","indexed","pv","iv","zero","iz","zv","whole","partial","span","bad")
SCHEMA={
 "BEGIN":{"f","room","threshold"}, "FRAME_END":{"f","room","begun","ended","flushes","complete"},
 "PASS_BEGIN":{"f","p","duplicate"}, "PASS_END":{"f","p","result"},
 "FLUSH_BEGIN":{"f","p","q","parts","picks","overflow"},
 "PART":{"f","p","q","s","placement","part","first","picks","tried","result","crc","fnv"},
 "PART_COUNTS":{"f","p","q","s",*FIELDS}, "FLUSH_COUNTS":{"f","p","q","s",*FIELDS},
 "FLUSH_END":{"f","p","q","picks","sum","tried","completed","fallback","aborted","untried"},
}
def parse(text,room=None):
    rows=[]
    for line in text.splitlines():
        at=line.find("WEC23 ")
        if at<0:continue
        tokens=line[at:].split()
        if len(tokens)<2 or tokens[1] not in SCHEMA:raise ValueError("unknown record")
        row={"kind":tokens[1]}
        for token in tokens[2:]:
            key,value=token.split("=",1)
            if key in row:raise ValueError("duplicate field")
            row[key]=int(value,16 if key in ("room","crc","fnv","begun","ended") else 10)
        if set(row)!={"kind",*SCHEMA[row["kind"]]}:raise ValueError("missing/unknown field")
        if any(not 0<=value<=0xffffffff for key,value in row.items() if key not in ("kind","result")):raise ValueError("invalid unsigned field")
        rows.append(row)

    # Consume source protocol order, rather than collecting unordered sets.
    # No flush can move across a pass boundary or beyond terminal FRAME_END.
    cursor=0
    def take(kind,**identity):
        nonlocal cursor
        if cursor==len(rows) or rows[cursor]["kind"]!=kind:raise ValueError("expected "+kind)
        row=rows[cursor];cursor+=1
        if any(row[key]!=value for key,value in identity.items()):raise ValueError("mismatched "+kind+" scope")
        return row
    begin=take("BEGIN");frame=begin["f"]
    if not 1<=begin["threshold"]<=10000000 or frame<begin["threshold"]:raise ValueError("invalid capture threshold/frame")
    if room is not None and begin["room"]!=room:raise ValueError("wrong room")
    summaries=[];next_flush=1
    for p in range(3):
        start=take("PASS_BEGIN",f=frame,p=p)
        if start["duplicate"]:raise ValueError("duplicate pass")
        while cursor<len(rows) and rows[cursor]["kind"]=="FLUSH_BEGIN":
            start=take("FLUSH_BEGIN",f=frame,p=p,q=next_flush);q=next_flush;next_flush+=1
            if start["overflow"] or start["parts"]>48 or start["picks"]>320:raise ValueError("overflow")
            total={f:0 for f in FIELDS};parts=[];picked=tried=0
            for slot in range(start["parts"]):
                part=take("PART",f=frame,p=p,q=q,s=slot)
                c=take("PART_COUNTS",f=frame,p=p,q=q,s=slot)
                if part["first"]!=picked or part["result"]!=1 or part["tried"]!=part["picks"]:raise ValueError("partial/failed replay")
                if c["plain"]+c["indexed"]!=part["picks"] or c["whole"]+c["partial"]+c["zero"]!=part["picks"]:raise ValueError("part count mismatch")
                if c["iz"]>c["zero"] or c["iz"]>c["indexed"] or c["bad"]:raise ValueError("invalid part census")
                for f in FIELDS:total[f]+=c[f]
                picked+=part["picks"];tried+=part["tried"];parts.append(dict(part,counts={f:c[f] for f in FIELDS}))
            counts=take("FLUSH_COUNTS",f=frame,p=p,q=q,s=0)
            finish=take("FLUSH_END",f=frame,p=p,q=q)
            if any(counts[f]!=total[f] for f in FIELDS):raise ValueError("flush count mismatch")
            if (start["picks"]!=picked or finish["picks"]!=picked or finish["sum"]!=picked or finish["tried"]!=tried or
                finish["completed"]!=start["parts"] or finish["fallback"] or finish["aborted"] or finish["untried"]):raise ValueError("incomplete flush")
            summaries.append({"pass":p,"flush":q,"picks":picked,"counts":total,"parts":parts})
        if take("PASS_END",f=frame,p=p)["result"]!=1:raise ValueError("failed pass")
    end=take("FRAME_END",f=frame,room=begin["room"])
    if end["complete"]!=1 or end["begun"]!=7 or end["ended"]!=7:raise ValueError("incomplete frame")
    if end["flushes"]!=next_flush-1:raise ValueError("missing flush block")
    if cursor!=len(rows):raise ValueError("census record after FRAME_END")
    return {"frame":frame,"room":begin["room"],"threshold":begin["threshold"],"complete_selected_census":True,"flushes":summaries,
            "totals":{f:sum(s["counts"][f] for s in summaries) for f in FIELDS},
            "limits":"selected queue/attempts only; not accepted geometry, runtime speed, or gate acceptance"}
if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("capture");ap.add_argument("--room",type=lambda s:int(s,0));ap.add_argument("--output")
    a=ap.parse_args();report=parse(Path(a.capture).read_text(errors="replace"),a.room)
    text=json.dumps(report,indent=2)+"\n"
    if a.output:Path(a.output).write_text(text)
    else:print(text,end="")
