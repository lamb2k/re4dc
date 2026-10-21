"""Read-only attribution of the sealed inventory pair. Never reruns a guest."""
from pathlib import Path
from collections import Counter
import argparse, hashlib, json, re, struct


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse(path):
    lines = path.read_text(errors="replace").splitlines()
    phase = "cold"
    events, holds, preloads = [], [], []
    for number, line in enumerate(lines, 1):
        if line.startswith("native texture hold: claims=1"):
            phase = "held"
            holds.append({"line": number, "text": line})
        if line.startswith("native texture unclaim: claims=0"):
            phase = "return"
        if line.startswith("native texture hold restore: picks="):
            phase = "restore"
        match = re.search(r"native UI: load .*?/([0-9a-f]{8}-[0-9a-f]{8})\.re4tex (\d+)x(\d+) fmt=(\d+)", line)
        if match:
            events.append({"line": number, "key": match[1], "width": int(match[2]),
                           "height": int(match[3]), "format": int(match[4]), "phase": phase})
        match = re.search(r"native UI: upload ok vram=(\d+)", line)
        if match and events:
            events[-1]["upload_bytes"] = int(match[1])
        if line.startswith("native texture preload: frame="):
            preloads.append({"line": number, "phase": phase, "text": line})
            if phase == "restore":
                phase = "after-restore"
        if "native texture claim: movie window" in line:
            holds.append({"line": number, "text": line})
    return {"path": str(path), "sha256": sha(path), "events": events,
            "phase_counts": dict(Counter(e["phase"] for e in events)),
            "holds": holds, "preloads": preloads}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence", type=Path, required=True)
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--pack", type=Path, help="optional exact original pack; reads selected members only")
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    assert not args.output.exists(), "use a new output; sealed receipts are immutable"
    result = {"kind": "sealed-log-source-attribution", "arms": {}}
    for arm in ("off", "on"):
        result["arms"][arm] = parse(args.evidence / f"inventory-{arm}-01" / "run-output.txt")
    off, on = (result["arms"][arm] for arm in ("off", "on"))
    restore = lambda arm: {e["key"] for e in arm["events"] if e["phase"] == "restore"}
    after = lambda arm: {e["key"] for e in arm["events"] if e["phase"] == "after-restore"}
    extra = restore(on) - restore(off)
    seen_after_off = extra & after(off)
    result["comparison"] = {
        "extra_on_restore_keys": sorted(extra),
        "extra_keys_later_opened_by_off": sorted(seen_after_off),
        "extra_keys_without_later_off_open_in_capture": sorted(extra - seen_after_off),
        "extra_on_restore_upload_bytes": sum(e.get("upload_bytes", 0) for e in on["events"]
                                             if e["phase"] == "restore" and e["key"] in extra),
        "no_later_off_open_upload_bytes": sum(e.get("upload_bytes", 0) for e in on["events"]
                                              if e["phase"] == "restore" and e["key"] in extra-seen_after_off),
    }
    if args.pack:
        selected = []
        with args.pack.open("rb") as handle:
            digest = hashlib.file_digest(handle, "sha256").hexdigest()
            total = handle.tell()
            handle.seek(0)
            magic, version, count, index_offset, data_offset = struct.unpack("<8s4I", handle.read(24))
            assert magic == b"RE4PAK1\0" and version == 1
            assert 24 <= index_offset <= data_offset <= total and index_offset + 16*count <= data_offset
            for i in range(count):
                handle.seek(index_offset+16*i)
                crc, fnv, offset, size = struct.unpack("<4I", handle.read(16))
                key = f"{crc:08x}-{fnv:08x}"
                if key not in extra:
                    continue
                assert data_offset <= offset and size >= 144 and offset+size <= total
                handle.seek(offset)
                blob = handle.read(size)
                assert len(blob) == size
                texture = struct.unpack_from("<64s8I", blob, 48)
                selected.append({"key": key, "offset": offset, "stored_member_bytes": size,
                                 "member_sha256": hashlib.sha256(blob).hexdigest(),
                                 "width": texture[1], "height": texture[2], "format": texture[3],
                                 "texture_payload_bytes": texture[5], "flags": texture[6], "layout": texture[7]})
        assert {r["key"] for r in selected} == extra
        result["pack"] = {"path": str(args.pack), "sha256": digest, "bytes": total,
                          "selected_members": selected,
                          "stored_member_bytes": sum(r["stored_member_bytes"] for r in selected),
                          "texture_payload_bytes": sum(r["texture_payload_bytes"] for r in selected)}
    source = args.source.read_text()
    # Pin the actual shared field writes. These do not establish a draw timestamp.
    patterns = ["#define RE4DC_HOLD_EVICTED", "#define RE4DC_TOUCH", "e.frame=frame;++resident",
                "if(frame)for(auto& e:entries)if(e.valid && e.frame==frame)e.frame=frame-1;",
                "if(hold_restore)"]
    result["source"] = {"path": str(args.source), "sha256": sha(args.source), "pins": [
        {"line": n, "text": line} for n, line in enumerate(source.splitlines(), 1)
        if any(pattern in line for pattern in patterns)]}
    result["limits"] = [
        "Log opens are requests, not proof of visible draw use or physical optical seeks.",
        "No later OFF open within the capture does not prove the texture is unnecessary on a later camera/path.",
        "The shared Entry.frame field is written by preloads and ordinary lookups; it is not exclusively a last-drawn timestamp.",
        "No counterfactual traffic or performance saving is calculated from these package upload bytes.",
        "Host-time pair has one actual menu cycle and different source return frames; physical Dreamcast acceptance is open."]
    result["pair_receipt"] = {"path": str(args.evidence / "inventory-pair-result.json"),
                              "sha256": sha(args.evidence / "inventory-pair-result.json")}
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"phase_counts": {a: result["arms"][a]["phase_counts"] for a in ("off", "on")},
                      "extra_restore": len(extra), "later_off_open": len(seen_after_off),
                      "not_later_off_open": len(extra-seen_after_off),
                      "upload_bytes": result["comparison"]["extra_on_restore_upload_bytes"],
                      "output": str(args.output)}))


if __name__ == "__main__":
    main()
