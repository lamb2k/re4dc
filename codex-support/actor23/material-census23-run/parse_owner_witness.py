"""Strict, source-bound owner-witness log reader; never runtime certification."""
import argparse
import hashlib
import json
import math
import re
import struct
from pathlib import Path

SOURCE_PARENT = "18a9db3b400721c00ab5aa3a912cbd5681547919"
SCHEMA_ID = "actor-owner-witness23-material-r1"
FORMAT_SOURCE_SHA256 = "a88b27192ba5b8bad40b2e06fd86491a721999118ddff9f4f591e8743fc69e68"
STATE_SOURCE_SHA256 = "783b5ba9ad88f98a977d2fc6c48d59445defa29bfcf19c31ee1c55f460ebfa84"
MAX_LOG_BYTES = 64 * 1024 * 1024
MAX = 0xffffffff
# Ordered fields exactly match the frozen printf records. h=hex, p=pointer,
# w6/w25=raw float words; all other fields are decimal unsigned32.
SCHEMA = {
 "AV23WINDOW": "event frame mode mask:h left once metadata_checks metadata_bytes",
 "AV23": "frame mode n query sections wall hidden bound would skip tri xf",
 "AV23WORK": "frame groups hit miss scan material identity numeric capacity reset world_ok world_draw metadata_checks metadata_bytes",
 "AV23OWNER": "complete qualified fail:h mode binds owner:p id:h serial epoch life unattributed samples maxlines",
 "AV23OWNER_PART": "role info:p query bound potential would skip positions triangles refused refuse:h",
 "AV23OWNER_SAMPLE": "slot token workspace mode owner:p id:h serial epoch life role info:p",
 "AV23OWNER_SOURCE": "slot flags:h room:h game ui lod meshlet path nv nt potential committed",
 "AV23OWNER_ADDR": "slot positions:p blob:p records:p",
 "AV23OWNER_BOX": "slot words:w6",
 "AV23OWNER_VIEW": "slot words:w25",
 "AV23OWNER_WORLD": "slot stage field result storage:p current_storage:p metadata:p current_metadata:p",
 "AV23OWNER_RECEIPT": "slot owner active complete epoch stamp frame current_frame scene current_scene",
 "AV23OWNER_COVER": "slot fpscr:h current_fpscr:h coverage:h required:h room:h bytes version",
 "AV23OWNER_RANGE": "slot near:h8 far:h8 current_near:h8 current_far:h8",
}
ROWS = tuple("AV23OWNER_" + n for n in ("SAMPLE", "SOURCE", "ADDR", "BOX", "VIEW", "WORLD", "RECEIPT", "COVER", "RANGE"))
MARKER = re.compile(r"\bAV23(?:[A-Z_]+)?\b")
LOSS = re.compile(r"(?:log|logger|ring)[^\r\n]{0,40}(?:overflow|overrun|truncat|dropp)|(?:overflow|overrun|truncat|dropp)[^\r\n]{0,40}(?:log|logger|ring)", re.I)

class Invalid(ValueError):
 pass

def need(ok, message):
 if not ok:
  raise Invalid(message)

def u32(text, kind):
 if kind == "p" and text == "(nil)":
  return 0
 if kind == "p":
  need(bool(re.fullmatch(r"(?:0x)?[0-9a-f]+", text)), "bad pointer")
  value = int(text, 16)
 elif kind in ("h", "h8"):
  need(bool(re.fullmatch(r"[0-9a-f]{8}" if kind == "h8" else r"[0-9a-f]+", text)), "bad hexadecimal")
  value = int(text, 16)
 else:
  need(bool(re.fullmatch(r"0|[1-9][0-9]*", text)), "bad decimal")
  value = int(text)
 need(value <= MAX, "unsigned32 range exceeded")
 return value

def decode(line):
 need(len(line.encode("ascii")) < 256, "native line buffer exceeded/truncated")
 tokens = line.split(" "); name = tokens.pop(0)
 need(name in SCHEMA, "unknown witness/window record")
 fields = SCHEMA[name].split()
 need(len(tokens) == len(fields), "missing/extra/truncated fields: " + name)
 out = {}
 for token, spec in zip(tokens, fields):
  key, _, kind = spec.partition(":")
  need(token.startswith(key + "="), "wrong/duplicate field order: " + name)
  value = token[len(key)+1:]
  if kind.startswith("w"):
   values = value.split(",")
   need(len(values) == int(kind[1:]), "raw word count: " + name)
   out[key] = [u32(v, "h8") for v in values]
  else:
   out[key] = u32(value, kind)
 return name, out

def finite(word):
 value = struct.unpack("<f", struct.pack("<I", word))[0]
 need(math.isfinite(value), "nonfinite raw float")
 return value

def parse(data, assertions=None):
 """Return observations only; malformed/refused data never qualify a runtime."""
 result = {"schema_source_parent": SOURCE_PARENT, "schema": SCHEMA_ID, "format_source_sha256": FORMAT_SOURCE_SHA256,
           "qualified": False, "runtime_qualification": "PENDING_SEPARATE_VERIFIED_RUNTIME_RECEIPT",
           "caller_assertions": assertions or {}, "format_complete": False}
 try:
  need(isinstance(data, bytes) and len(data) <= MAX_LOG_BYTES, "log size/type bound")
  result["log_sha256"] = hashlib.sha256(data).hexdigest()
  if assertions is not None:
   need(isinstance(assertions, dict), "binding assertions must be JSON object")
   need(bool(re.fullmatch(r"[0-9a-f]{40}", str(assertions.get("source", "")))), "caller source assertion syntax")
   need(assertions.get("source_parent") == SOURCE_PARENT and assertions.get("format_source_sha256") == FORMAT_SOURCE_SHA256, "caller schema source assertion mismatch")
   need(assertions.get("log_sha256") == result["log_sha256"], "caller log assertion mismatch")
   need(bool(re.fullmatch(r"[0-9a-f]{64}", str(assertions.get("programme_sha256", "")))), "missing caller programme assertion")
   need(assertions.get("reader_complete") is True and assertions.get("log_overflow") is False, "caller reports incomplete/overflowed reader")
  text = data.decode("utf8", "strict")
  need(not LOSS.search(text), "log loss/overflow marker")
  records = []
  for line in text.splitlines():
   matches = list(MARKER.finditer(line))
   if not matches:
    continue
   need(len(matches) == 1, "multiple records in one line")
   suffix = line[matches[0].start():]
   name, row = decode(suffix)
   records.append((name, row))
   need(len(records) <= 1241, "record/window bound exceeded")
  cursor = 0
  def take(name):
   nonlocal cursor
   need(cursor < len(records) and records[cursor][0] == name, "missing/out-of-order/duplicate " + name)
   row = records[cursor][1]; cursor += 1
   return row
  start = take("AV23WINDOW")
  need(start["event"] == 1 and start["left"] == 599 and start["once"] == 1, "no exact window start")
  mode = start["mode"]
  need(mode in (1, 2) and start["mask"] == (0x20 if mode == 1 else 0x40), "mode0/invalid/refused window")
  frames = {}; prior = -1
  for n in range(1, 601):
   frame = take("AV23"); work = take("AV23WORK")
   need(frame["mode"] == mode and frame["n"] == n and frame["frame"] > prior, "incomplete/reordered window samples")
   need(work["frame"] == frame["frame"], "work/sample frame mismatch")
   need(n != 1 or frame["frame"] == start["frame"], "start/sample mismatch")
   need(all(v != MAX for k, v in frame.items() if k not in ("frame", "mode", "n")), "aggregate overflow sentinel")
   frames[frame["frame"]] = frame; prior = frame["frame"]
  end = take("AV23WINDOW")
  need(end["event"] == 3 and end["frame"] > prior and end["mode"] == 0 and end["left"] == 0 and end["once"] == 1 and end["mask"] == start["mask"], "incomplete/cancelled/refused window")
  summary = take("AV23OWNER")
  need(summary["complete"] == summary["qualified"] == 1 and summary["fail"] == 0 and summary["mode"] == mode and summary["binds"] == 600, "incomplete/overflow/refused owner window")
  need(summary["samples"] == 4 and summary["maxlines"] == 39 and summary["unattributed"] != MAX, "schema capacity/overflow mismatch")
  need(summary["owner"] and summary["id"] == 0x2b and summary["epoch"] and summary["life"], "not a live owner2b identity")
  parts = [take("AV23OWNER_PART"), take("AV23OWNER_PART")]
  expected = []
  for role, p in enumerate(parts):
   need(p["role"] == role and all(v != MAX for v in p.values()), "role duplicate/overflow")
   need(p["potential"] <= p["bound"] <= p["query"], "inconsistent role counters")
   need(bool(p["info"]) == bool(p["query"]), "role info/query mismatch")
   need(p["would"] >= p["potential"] and bool(p["would"]) == bool(p["potential"]), "inconsistent potential records")
   need(p["skip"] == (p["potential"] if mode == 2 else 0), "skip/potential mode mismatch")
   need(p["positions"] == (p["would"] if mode == 2 else 0), "actual/potential positions mismatch")
   need(p["triangles"] >= p["skip"] and bool(p["triangles"]) == bool(p["skip"]), "inconsistent actual triangles")
   need(p["refused"] <= p["query"]-p["bound"] and bool(p["refused"]) == bool(p["refuse"]), "inconsistent material refusals")
   need(not p["refuse"] & ~0x183f, "unknown/unsafe provenance reason bits")
   if p["bound"] > p["potential"]: expected.append(2 * role)
   if p["potential"]: expected.append(2 * role + 1)
  # Aggregate rows are ceilings/closure only, never a source of owner identity.
  for owner_key, global_key in (("query", "query"), ("bound", "sections"), ("potential", "hidden"), ("would", "would"), ("positions", "skip"), ("triangles", "tri")):
   need(sum(x[owner_key] for x in parts) <= sum(x[global_key] for x in frames.values()), "owner counters exceed whole-window counters")
  need(parts[0]["query"] + parts[1]["query"] > 0, "no attributed cohort")
  need(not (parts[0]["info"] and parts[0]["info"] == parts[1]["info"]), "body/head info alias")
  tokens = set(); samples = []; refused = 0
  for slot in expected:
   rows = [take(name) for name in ROWS]
   need(all(x["slot"] == slot for x in rows), "missing/duplicate/unexpected sample slot")
   q, s, a, box, view, w, receipt, cover, ranges = rows
   role = slot // 2; potential = slot % 2; p = parts[role]
   need(q["role"] == role and q["info"] == p["info"] and q["mode"] == mode, "sample role/context mismatch")
   need(all(q[k] == summary[k] for k in ("owner", "id", "serial", "epoch", "life")), "owner lifetime mismatch")
   need(q["token"] and q["token"] not in tokens and q["workspace"] in frames, "duplicate token/outside-window workspace")
   tokens.add(q["token"])
   need(s["flags"] & 1 and not s["flags"] & 0x4000 and s["room"] == 0x119 and s["path"] in (0, 1) and s["nv"] and s["nt"], "refused source identity")
   need(s["potential"] == potential and s["committed"] == (potential if mode == 2 else 0), "potential/actual skip mismatch")
   need(all(a[k] for k in ("positions", "blob", "records")), "missing actual source addresses")
   floats = [finite(v) for v in box["words"]]
   need(all(floats[i] <= floats[i+3] for i in range(3)), "invalid posed box")
   for v in view["words"]: finite(v)
   decoded_range = {k: finite(v) for k, v in ranges.items() if k != "slot"}
   need(w["stage"] <= 5 and w["result"] in (0, 1), "unknown world outcome")
   if potential:
    need(w["stage"] == 5 and w["field"] in (5, 7) and w["result"] == 1, "potential has refused world")
    need(w["storage"] and w["storage"] == w["current_storage"] and w["metadata"] and w["metadata"] == w["current_metadata"], "stale world addresses")
    need(receipt["owner"] == receipt["complete"] == 1 and receipt["active"] == 0 and receipt["epoch"] and receipt["epoch"] == receipt["stamp"], "refused world receipt")
    need(receipt["frame"] == receipt["current_frame"] == s["ui"] and receipt["scene"] and receipt["scene"] == receipt["current_scene"], "stale world frame/scene")
    need(cover["fpscr"] == cover["current_fpscr"] and cover["coverage"] == cover["required"] and cover["required"] and cover["room"] == 0x119 and cover["bytes"] == 1376 and cover["version"] == 2, "refused coverage/metadata/FPSCR")
    need(ranges["near"] == ranges["current_near"] and decoded_range["current_far"] <= decoded_range["far"] and decoded_range["near"] > 0 and decoded_range["current_far"] >= decoded_range["near"], "stale/invalid world range")
    need(p["would"] >= s["nv"] and (mode != 2 or p["triangles"] >= s["nt"]), "sample exceeds role totals")
   elif w["result"] == 0:
    refused += 1  # A correctly retained draw is never a positive cut witness.
   samples.append({"slot": slot, "role": role, "token": q["token"], "workspace": q["workspace"], "field": w["field"], "potential": bool(potential), "actual_pre_position_skip": bool(s["committed"]), "lod": s["lod"], "path": s["path"], "meshlet": s["meshlet"]})
  need(cursor == len(records), "unexpected/duplicate/trailing witness records")
  result.update(format_complete=True, reported_window_qualified=True, mode=mode,
                owner={k: summary[k] for k in ("owner", "id", "serial", "epoch", "life")},
                roles=parts, samples=samples, refused_draw_samples=refused,
                reported_owner2b_material_refusals=sum(p["refused"] for p in parts),
                reported_owner2b_potential_sections=sum(p["potential"] for p in parts),
                reported_owner2b_pre_position_skips=sum(p["skip"] for p in parts),
                reported_owner2b_positions_avoided=sum(p["positions"] for p in parts))
 except (Invalid, UnicodeError, ValueError, OverflowError) as exc:
  result["error"] = str(exc)
 return result

def main():
 ap = argparse.ArgumentParser(description=__doc__)
 ap.add_argument("log", type=Path)
 ap.add_argument("--binding", type=Path, help="Optional caller assertions; never closure evidence")
 args = ap.parse_args()
 need(args.log.stat().st_size <= MAX_LOG_BYTES, "log size bound")
 result = parse(args.log.read_bytes(), json.loads(args.binding.read_text()) if args.binding else None)
 print(json.dumps(result, indent=2))
 return 0 if result["format_complete"] else 2

if __name__ == "__main__":
 raise SystemExit(main())
