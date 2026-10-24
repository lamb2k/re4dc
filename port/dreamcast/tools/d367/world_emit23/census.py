"""Read exact WEC23 one-frame selected-queue census; no timing/acceptance inference."""
from pathlib import Path
import argparse,json,re
FIELDS=("plain","indexed","pv","iv","zero","iz","zv","whole","partial","span","bad")
def parse(text,room=None):
    rows=[]
    for line in text.splitlines():
        at=line.find("WEC23 ")
        if at<0:continue
        tokens=line[at:].split();row={"kind":tokens[1]}
        for token in tokens[2:]:
            key,value=token.split("=",1)
            if key in row:raise ValueError("duplicate field")
            row[key]=int(value,16 if key in ("room","crc","fnv","begun","ended") else 10)
        if any(value<0 for key,value in row.items() if key not in ("kind","result")):raise ValueError("negative counter")
        rows.append(row)
    def only(kind):
        out=[r for r in rows if r["kind"]==kind]
        if len(out)!=1:raise ValueError("expected one "+kind)
        return out[0]
    begin,end=only("BEGIN"),only("FRAME_END");frame=begin["f"]
    if any(r["f"]!=frame for r in rows):raise ValueError("mixed capture frames")
    if room is not None and begin["room"]!=room:raise ValueError("wrong room")
    if end["room"]!=begin["room"] or end["complete"]!=1 or end["begun"]!=7 or end["ended"]!=7:raise ValueError("incomplete frame")
    if any(r["kind"] not in ("BEGIN","FRAME_END","PASS_BEGIN","PASS_END","FLUSH_BEGIN","PART","PART_COUNTS","FLUSH_COUNTS","FLUSH_END") for r in rows):raise ValueError("unknown record")
    for p in range(3):
        starts=[r for r in rows if r["kind"]=="PASS_BEGIN" and r["p"]==p]
        stops=[r for r in rows if r["kind"]=="PASS_END" and r["p"]==p]
        if len(starts)!=1 or len(stops)!=1 or starts[0]["duplicate"] or stops[0]["result"]!=1:raise ValueError("incomplete/failed/duplicate pass")
    if any("p" in r and r["p"] not in range(3) for r in rows):raise ValueError("invalid pass")
    summaries=[];seen=set()
    for start in (r for r in rows if r["kind"]=="FLUSH_BEGIN"):
        key=(start["p"],start["q"])
        if key in seen:raise ValueError("duplicate flush")
        seen.add(key)
        records=[r for r in rows if (r.get("p"),r.get("q"))==key]
        def one(kind,slot=None):
            a=[r for r in records if r["kind"]==kind and (slot is None or r.get("s")==slot)]
            if len(a)!=1:raise ValueError("missing/duplicate "+kind)
            return a[0]
        finish=one("FLUSH_END");counts=one("FLUSH_COUNTS")
        if start["overflow"] or start["parts"]>48 or start["picks"]>320:raise ValueError("overflow")
        total={f:0 for f in FIELDS};parts=[];picked=tried=0
        for slot in range(start["parts"]):
            part=one("PART",slot);c=one("PART_COUNTS",slot)
            if part["first"]!=picked or part["result"]!=1 or part["tried"]!=part["picks"]:raise ValueError("partial/failed replay")
            if c["plain"]+c["indexed"]!=part["picks"] or c["whole"]+c["partial"]+c["zero"]!=part["picks"]:raise ValueError("part count mismatch")
            if c["iz"]>c["zero"] or c["iz"]>c["indexed"] or c["bad"]:raise ValueError("invalid part census")
            for f in FIELDS:total[f]+=c[f]
            picked+=part["picks"];tried+=part["tried"];parts.append(dict(part,counts={f:c[f] for f in FIELDS}))
        if len(records)!=3+2*start["parts"]:raise ValueError("orphan/unknown flush record")
        if any(counts[f]!=total[f] for f in FIELDS):raise ValueError("flush count mismatch")
        if (start["picks"]!=picked or finish["picks"]!=picked or finish["sum"]!=picked or finish["tried"]!=tried or
            finish["completed"]!=start["parts"] or finish["fallback"] or finish["aborted"] or finish["untried"]):raise ValueError("incomplete flush")
        summaries.append({"pass":key[0],"flush":key[1],"picks":picked,"counts":total,"parts":parts})
    if any(r["kind"] in ("PART","PART_COUNTS","FLUSH_COUNTS","FLUSH_END") and (r["p"],r["q"]) not in seen for r in rows):raise ValueError("orphan flush")
    return {"frame":frame,"room":begin["room"],"complete_selected_census":True,"flushes":summaries,
            "totals":{f:sum(s["counts"][f] for s in summaries) for f in FIELDS},
            "limits":"selected queue/attempts only; not accepted geometry, runtime speed, or gate acceptance"}
if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("capture");ap.add_argument("--room",type=lambda s:int(s,0));ap.add_argument("--output")
    a=ap.parse_args();report=parse(Path(a.capture).read_text(errors="replace"),a.room)
    text=json.dumps(report,indent=2)+"\n"
    if a.output:Path(a.output).write_text(text)
    else:print(text,end="")
