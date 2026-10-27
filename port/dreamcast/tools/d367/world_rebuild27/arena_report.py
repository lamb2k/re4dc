#!/usr/bin/env python3
"""Read existing benchmark/TAIL_METER/PACE logs. No synthetic GPU timing model.

All three arms must complete with accepted whole pace windows and real GPU stamps.
Use --environment cache-model-flycast for emulator logs; console is reserved for
logs captured from physical hardware. Input files may contain one selected arm each.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys

VARIANTS = {1: "original", 2: "simplifiedR4", 3: "baked"}


def values(line):
    return dict(re.findall(r"([A-Za-z_][A-Za-z_0-9.]*)=([^\s]+)", line))


def number(data, key):
    return int(data.get(key, "0").rstrip("%"))


def percentile(items, q):
    return sorted(items)[max(0, math.ceil(len(items) * q) - 1)] if items else None


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixtures(paths):
    """Only the bench row's number/name may differ. Preserve every other command."""
    normalized = []
    metadata = []
    for expected, path in enumerate(paths, 1):
        rows, lines = [], []
        for line in path.read_text().splitlines():
            tokens = line.split("#", 1)[0].split()
            if not tokens:
                continue
            if tokens[0] == "bench":
                if len(tokens) != 5 or int(tokens[1]) != expected:
                    raise ValueError(f"{path}: expected one bench row numbered {expected}")
                rows.append((int(tokens[2]), int(tokens[3])))
                tokens[1], tokens[4] = "SCENE", "VARIANT"
            lines.append(" ".join(tokens))
        if len(rows) != 1:
            raise ValueError(f"{path}: expected exactly one bench row")
        normalized.append(lines)
        metadata.append({"path": str(path), "sha256": digest(path), "begin": rows[0][0], "end": rows[0][1]})
    if any(lines != normalized[0] for lines in normalized[1:]):
        raise ValueError("fixture commands differ beyond bench scene number/name")
    return metadata


def parse(paths, run):
    arms, errors = {}, []
    for path in paths:
        current, pending, measuring = None, None, False
        for line in path.read_text(errors="replace").splitlines():
            data = values(line)
            if "arena27: INVALID" in line:
                errors.append(f"{path}: rejected fixture")
            if "arena27: armed " in line:
                if number(data, "run") != run:
                    current = None
                    continue
                current = number(data, "scene")
                if current not in VARIANTS or data.get("variant") != VARIANTS[current]:
                    errors.append(f"{path}: invalid arm metadata")
                    current = None
                    continue
                if current in arms:
                    errors.append(f"{path}: duplicate arm {current} run {run}")
                arms[current] = {"metadata": data, "tails": [], "pace": [], "result": {}, "ta": {}, "summary": {}, "stream_warmup": [], "stream_measured": [], "source": str(path)}
                measuring = False
            boundary = re.search(r"bench: scene (\d+) (begin|end) room frame", line)
            if boundary and int(boundary[1]) == current:
                measuring = boundary[2] == "begin"
                if boundary[2] == "end":
                    current = None
            if "native stream: " in line and current in arms:
                arms[current]["stream_measured" if measuring else "stream_warmup"].append(data)
            if "arena27: window " in line and number(data, "run") == run:
                pending = number(data, "scene")
            elif "PACE vmu " in line:
                if pending in arms:
                    arms[pending]["pace"].append(data)
                pending = None
            elif "tail: sc=" in line and current in arms and number(data, "sc") == current:
                meta = arms[current]["metadata"]
                if int(meta["begin"]) < number(data, "f") < int(meta["end"]):
                    arms[current]["tails"].append(data)
            elif "arena27: result " in line and number(data, "run") == run:
                scene = number(data, "scene")
                if scene in arms:
                    arms[scene]["summary"] = data
            elif "bench: result run " in line:
                match = re.search(r"bench: result run (\d+) scene (\d+)", line)
                if match and int(match[1]) == run and int(match[2]) in arms:
                    arms[int(match[2])]["result"] = data
            elif "bench: ta run " in line:
                match = re.search(r"bench: ta run (\d+) scene (\d+)", line)
                if match and int(match[1]) == run and int(match[2]) in arms:
                    arms[int(match[2])]["ta"] = data
    return arms, errors


def report(args):
    arms, errors = parse(args.logs, args.run)
    wanted = [args.single_arm] if args.single_arm else [1, 2, 3]
    fixture_meta = fixtures(args.fixtures) if args.fixtures else []
    if not fixture_meta:
        errors.append("supply --fixtures warp.txt bench2.txt bench3.txt to verify matched camera/pose commands")
    build_ids, ranges = set(), set()
    rows = []
    for scene in wanted:
        arm = arms.get(scene)
        if arm is None:
            errors.append(f"missing arm {scene} ({VARIANTS[scene]})")
            continue
        meta, summary, result, ta = (arm[k] for k in ("metadata", "summary", "result", "ta"))
        build_ids.add(meta.get("build"))
        ranges.add((number(meta, "begin"), number(meta, "end")))
        if fixture_meta and (number(meta, "begin"), number(meta, "end")) != (fixture_meta[scene - 1]["begin"], fixture_meta[scene - 1]["end"]):
            errors.append(f"arm {scene}: log/fixture frame range differs")
        if not summary or number(summary, "end_frame") != number(meta, "end"):
            errors.append(f"arm {scene}: measured range did not finish exactly")
        if summary.get("variant") != VARIANTS[scene]:
            errors.append(f"arm {scene}: result variant missing or mismatched")
        if number(result, "windows") < 2 or len(arm["pace"]) != number(result, "windows"):
            errors.append(f"arm {scene}: need at least two accepted complete PACE windows, matching result count")
        for key in ("cpu_n", "gpu_n"):
            if not number(summary, key):
                errors.append(f"arm {scene}: no {key} samples")
        if not arm["tails"]:
            errors.append(f"arm {scene}: missing frame-tail samples")
        stream = arm["stream_measured"]
        baseline = arm["stream_warmup"][-1] if arm["stream_warmup"] else None
        counter_delta = None
        if not number(ta, "scenes"):
            required = ("model_bytes", "ta_used", "ta_peak", "discarded", "black_frames", "missing")
            if not baseline or not stream:
                errors.append(f"arm {scene}: TA count unavailable; need warmup baseline and measured native stream rows")
            elif any(key not in row for row in [baseline, *stream] for key in required):
                errors.append(f"arm {scene}: incomplete native stream row")
            else:
                counter_delta = {key: number(stream[-1], key) - number(baseline, key)
                                 for key in ("discarded", "black_frames", "missing")}
                for key in counter_delta:
                    samples = [number(baseline, key), *(number(row, key) for row in stream)]
                    if any(b != a for a, b in zip(samples, samples[1:])):
                        errors.append(f"arm {scene}: native stream {key} changed during measured samples")
                if any(number(row, "model_bytes") <= 0 for row in stream):
                    errors.append(f"arm {scene}: native stream has no model bytes on a measured sample")
        pace = arm["pace"]
        reg_n = sum(number(x, "reg_n") for x in pace)
        if not reg_n:
            errors.append(f"arm {scene}: no PVR registration samples")
        vb = number(result, "vblanks")
        gpu_n, cpu_n = number(summary, "gpu_n"), number(summary, "cpu_n")
        tails = arm["tails"]
        tail_stat = {}
        for key in ("work", "blk", "ta", "rnd", "queue"):
            samples = [number(x, key) for x in tails if key not in ("rnd", "queue") or number(x, "lag") != 99]
            tail_stat[key] = {"n": len(samples), "mean_us": sum(samples) / len(samples) if samples else None,
                              "p95_us": percentile(samples, .95), "max_us": max(samples) if samples else None}
        rows.append({"scene": scene, "variant": VARIANTS[scene], "build": meta.get("build"),
                     "room_frames": [number(meta, "begin"), number(meta, "end")],
                     "accepted_windows": number(result, "windows"), "drawn": number(result, "drawn"),
                     "ticks": number(result, "ticks"), "fps": number(result, "drawn") * 59.94 / vb if vb else None,
                     "present_ms": vb * 16.683 / number(result, "drawn") if number(result, "drawn") else None,
                     "gpu_render_ms": number(summary, "gpu_sum_ns") / gpu_n / 1e6 if gpu_n else None,
                     "pvr_registration_ms": sum(number(x, "reg_avg_us") * number(x, "reg_n") for x in pace) / reg_n / 1000 if reg_n else None,
                     "cpu_ms_per_tick": number(summary, "cpu_sum_us") / cpu_n / 1000 if cpu_n else None,
                     "cpu_sample_windows": cpu_n, "gpu_samples": gpu_n, "registration_samples": reg_n,
                     "ta_bytes_per_presented_frame": {key: number(ta, key) for key in ("op_b", "opm_b", "tr_b", "trm_b", "pt_b")} if number(ta, "scenes") else None,
                     "ta_count_status": "TA_HASH=4 available" if number(ta, "scenes") else "unavailable on streamed renderer; existing native stream samples used",
                     "native_stream": {"measured_samples": len(stream), "warmup_baseline": baseline,
                                       "counter_delta": counter_delta,
                                       "model_bytes_samples": [number(row, "model_bytes") for row in stream],
                                       "ta_used_samples": [number(row, "ta_used") for row in stream],
                                       "ta_peak_samples": [number(row, "ta_peak") for row in stream]},
                     "tail": tail_stat, "source": arm["source"]})
    if len(build_ids) > 1 or None in build_ids:
        errors.append("arms must identify the same build")
    if len(ranges) > 1:
        errors.append("arms have different measured room-frame ranges")
    return {"schema": "house-arena27-v1", "environment": args.environment,
            "timing_label": "physical console" if args.environment == "console" else "cache-model Flycast; GPU timings are not hardware accurate",
            "run": args.run, "valid": not errors, "errors": errors, "fixtures": fixture_meta,
            "logs": [{"path": str(p), "sha256": digest(p)} for p in args.logs], "arms": rows}


def markdown(data):
    lines = [f"House arena27: {data['timing_label']}", "", "| Variant | GPU render ms | PVR registration ms | Present ms | CPU ms/tick | FPS | Windows |", "|---|---:|---:|---:|---:|---:|---:|"]
    fmt = lambda value: "missing" if value is None else f"{value:.3f}"
    for row in data["arms"]:
        lines.append("| " + " | ".join([row["variant"], *(fmt(row[k]) for k in ("gpu_render_ms", "pvr_registration_ms", "present_ms", "cpu_ms_per_tick", "fps")), str(row["accepted_windows"])]) + " |")
    for row in data["arms"]:
        if row["ta_bytes_per_presented_frame"] is None:
            stream = row["native_stream"]
            lines += ["", f"{row['variant']}: TA list-byte count unavailable (streamed renderer). Native stream samples: {stream['measured_samples']}; model bytes {stream['model_bytes_samples']}; TA used {stream['ta_used_samples']}; TA peak {stream['ta_peak_samples']}; observed counter delta {stream['counter_delta']}."]
    if data["errors"]:
        lines += ["", "INCOMPLETE / INVALID: " + "; ".join(data["errors"])]
    lines += ["", "Registration, TA-done latency, GPU rendering and CPU work overlap. Do not add these columns. CPU is per tick; presentation is per drawn picture."]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("logs", nargs="+", type=Path)
    ap.add_argument("--environment", required=True, choices=("console", "cache-model-flycast"))
    ap.add_argument("--fixtures", nargs=3, type=Path, metavar=("WARP", "BENCH2", "BENCH3"))
    ap.add_argument("--run", type=int, default=1)
    ap.add_argument("--single-arm", type=int, choices=(1, 2, 3))
    ap.add_argument("--json", type=Path)
    ap.add_argument("--markdown", type=Path)
    args = ap.parse_args()
    try:
        data = report(args)
    except (ValueError, OSError) as error:
        ap.error(str(error))
    text = markdown(data)
    if args.json:
        args.json.write_text(json.dumps(data, indent=2) + "\n")
    if args.markdown:
        args.markdown.write_text(text)
    print(text, end="")
    return 0 if data["valid"] else 2


if __name__ == "__main__":
    sys.exit(main())
