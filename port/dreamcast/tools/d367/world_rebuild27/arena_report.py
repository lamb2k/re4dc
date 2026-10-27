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

VARIANTS = {1: "original", 2: "simplifiedR4", 3: "baked"}  # historical v1 API/log labels
VARIANTS_V2 = {1: "Original", 2: "Rebuilt", 3: "Sparse"}
GEOMETRY_METRICS = ("transformed_positions", "transformed_cache", "transformed_clip", "emitted_corners", "emitted_triangles", "fallback", "aborts")


def names(metadata):
    return VARIANTS_V2 if number(metadata, "schema") == 2 else VARIANTS


def crc(value):
    if type(value) is int:
        if not 0 <= value <= 0xffffffff:
            raise ValueError("CRC/hash integer outside uint32 range")
        return f"{value:08x}"
    if not isinstance(value, str):
        raise ValueError("CRC/hash must be a uint32 integer or hexadecimal string")
    text = value.lower().removeprefix("0x")
    if not re.fullmatch(r"[0-9a-f]{1,8}", text):
        raise ValueError("invalid CRC/hash word: " + text)
    return text.zfill(8)



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
        file_arms = set()  # footer rows are valid only for scenes armed in this file/run
        for line in path.read_text(errors="replace").splitlines():
            data = values(line)
            if "arena27: INVALID" in line:
                errors.append(f"{path}: rejected fixture")
            if "arena27: armed " in line:
                if number(data, "run") != run:
                    current = None
                    continue
                current = number(data, "scene")
                if current not in VARIANTS or data.get("variant") != names(data)[current]:
                    errors.append(f"{path}: invalid arm metadata")
                    current = None
                    continue
                if current in arms:
                    errors.append(f"{path}: duplicate arm {current} run {run}")
                file_arms.add(current)
                arms[current] = {"metadata": data, "tails": [], "pace": [], "result": {}, "ta": {}, "summary": {}, "stream_warmup": [], "stream_measured": [], "identity": {}, "geometry": {}, "source": str(path)}
                measuring = False
            boundary = re.search(r"bench: scene (\d+) (begin|end) room frame", line)
            if boundary and int(boundary[1]) == current:
                measuring = boundary[2] == "begin"
                if boundary[2] == "end":
                    current = None
            if "native stream: " in line and current in arms:
                arms[current]["stream_measured" if measuring else "stream_warmup"].append(data)
            if "arena27: identity " in line:
                scene = number(data, "variant") + 1
                if scene in file_arms:
                    previous = arms[scene]["identity"]
                    if previous and previous != data:
                        errors.append(f"{path}: conflicting loaded package identities for arm {scene}")
                    arms[scene]["identity"] = data
            if any(marker in line for marker in ("arena27: geo_pass ", "arena27: geo_metric ", "arena27: geo_sample ")) and number(data, "run") == run:
                scene, pass_id = number(data, "scene"), number(data, "pass")
                if scene in file_arms:
                    geometry = arms[scene]["geometry"].setdefault(pass_id, {"summary": {}, "metrics": {}, "samples": []})
                    if "arena27: geo_pass " in line:
                        if geometry["summary"]:
                            errors.append(f"{path}: duplicate geometry summary arm {scene} pass {pass_id}")
                        geometry["summary"] = data
                    elif "arena27: geo_metric " in line:
                        key = data.get("name")
                        if key in geometry["metrics"]:
                            errors.append(f"{path}: duplicate geometry metric arm {scene} pass {pass_id} {key}")
                        geometry["metrics"][key] = data
                    else:
                        geometry["samples"].append(data)
            if "arena27: window " in line and number(data, "run") == run:
                pending = number(data, "scene")
            elif "PACE vmu " in line:
                if pending in file_arms:
                    arms[pending]["pace"].append(data)
                pending = None
            elif "tail: sc=" in line and current in arms and number(data, "sc") == current:
                meta = arms[current]["metadata"]
                if int(meta["begin"]) < number(data, "f") < int(meta["end"]):
                    arms[current]["tails"].append(data)
            elif "arena27: result " in line and number(data, "run") == run:
                scene = number(data, "scene")
                if scene in file_arms:
                    arms[scene]["summary"] = data
            elif "bench: result run " in line:
                match = re.search(r"bench: result run (\d+) scene (\d+)", line)
                if match and int(match[1]) == run and int(match[2]) in file_arms:
                    arms[int(match[2])]["result"] = data
            elif "bench: ta run " in line:
                match = re.search(r"bench: ta run (\d+) scene (\d+)", line)
                if match and int(match[1]) == run and int(match[2]) in file_arms:
                    arms[int(match[2])]["ta"] = data
    return arms, errors


def geometry_report(arm, scene, errors):
    meta = arm["metadata"]
    begin, end = number(meta, "begin"), number(meta, "end")
    result, active = [], []
    if set(arm["geometry"]) - {0, 1, 2}:
        errors.append(f"arm {scene}: invalid geometry pass")
    for pass_id in (0, 1, 2):
        entry = arm["geometry"].get(pass_id)
        if not entry or not number(entry["summary"], "n"):
            result.append({"pass": pass_id, "status": "not observed", "frames": 0})
            continue
        active.append(pass_id)
        summary, metrics = entry["summary"], entry["metrics"]
        n = number(summary, "n")
        if n <= 0 or not begin <= number(summary, "first") <= number(summary, "last") < end:
            errors.append(f"arm {scene} pass {pass_id}: geometry frame range outside measured window")
        if n > number(summary, "ui_last") - number(summary, "ui_first") + 1:
            errors.append(f"arm {scene} pass {pass_id}: more observations than unique rendered frames")
        if any(number(summary, k) for k in ("invalid", "sequence_bad", "identity_bad")):
            errors.append(f"arm {scene} pass {pass_id}: invalid, duplicate or changing geometry observations")
        if set(metrics) != set(GEOMETRY_METRICS):
            errors.append(f"arm {scene} pass {pass_id}: incomplete geometry metric set")
        totals = {}
        for key in GEOMETRY_METRICS:
            metric = metrics.get(key, {})
            total, lo, hi = (number(metric, k) for k in ("sum", "min", "max"))
            if not 0 <= lo <= hi or not lo * n <= total <= hi * n:
                errors.append(f"arm {scene} pass {pass_id}: inconsistent metric {key}")
            if key in ("fallback", "aborts") and total:
                errors.append(f"arm {scene} pass {pass_id}: nonzero {key}")
            totals[key] = {"sum": total, "mean_per_observed_frame": total / n, "min": lo, "max": hi}
        baselines = [x for x in entry["samples"] if x.get("phase") == "baseline"]
        measured = [x for x in entry["samples"] if x.get("phase") == "measured"]
        if len(baselines) != 1 or not 0 <= number(baselines[0], "frame") < begin:
            errors.append(f"arm {scene} pass {pass_id}: missing or invalid warmup baseline")
        slots = [number(x, "slot") for x in measured]
        if not measured or len(slots) != len(set(slots)) or 3 not in slots:
            errors.append(f"arm {scene} pass {pass_id}: missing/duplicate measured camera samples")
        for sample in measured:
            if not begin <= number(sample, "frame") < end or number(sample, "valid") != 1 or number(sample, "result") <= 0:
                errors.append(f"arm {scene} pass {pass_id}: invalid measured camera sample")
            if crc(sample.get("camera", "")) != crc(summary.get("camera", "")):
                errors.append(f"arm {scene} pass {pass_id}: camera sample identity differs")
        if measured and number(next((x for x in measured if number(x, "slot") == 3), {}), "frame") != number(summary, "last"):
            errors.append(f"arm {scene} pass {pass_id}: last camera sample does not close aggregate")
        result.append({"pass": pass_id, "status": "observed", "frames": n,
                       "source_room_frames": [number(summary, "first"), number(summary, "last")],
                       "camera_hash": crc(summary.get("camera", "")), "mesh_crc": crc(summary.get("mesh_crc", "")),
                       "mesh_bytes": number(summary, "mesh_bytes"), "metrics": totals,
                       "baseline": baselines[0] if baselines else None, "camera_samples": measured,
                       "frustum_rejections": None, "strip_group_rejections": None,
                       "rejection_status": "not supported by this exact observation path"})
    if not active:
        errors.append(f"arm {scene}: counts build has no observed geometry pass")
    if not any(x.get("metrics", {}).get("emitted_triangles", {}).get("sum", 0) > 0 for x in result):
        errors.append(f"arm {scene}: no emitted house triangles in measured geometry")
    return result


def asset_receipt(path):
    if not path:
        return None, {}
    data = json.loads(path.read_text())
    entries = data.get("arms", [])
    if not isinstance(entries, list):
        raise ValueError("asset receipt arms must be an exact A/B/C list")
    result = {}
    for position, item in enumerate(entries, 1):
        label = item.get("arm")
        if type(label) is int and label in (1, 2, 3):
            scene = label
        elif isinstance(label, str) and label in ("A", "B", "C"):
            scene = ord(label) - ord("A") + 1
        else:
            raise ValueError("asset receipt has unknown arm; expected integer 1..3 or A/B/C")
        if scene in result or scene != position:
            raise ValueError("asset receipt has duplicate or out-of-order arm")
        for key in ("candidate_sha256", "candidate_crc", "candidate_bytes", "l0_triangles"):
            if key not in item:
                raise ValueError(f"asset receipt arm {label} missing {key}")
        if not re.fullmatch(r"[0-9a-f]{64}", item["candidate_sha256"]):
            raise ValueError("asset receipt candidate SHA256 invalid")
        crc(item["candidate_crc"])
        result[scene] = item
    if set(result) != {1, 2, 3}:
        raise ValueError("asset receipt must identify all three arms")
    return {"path": str(path), "sha256": digest(path), "schema": data.get("schema"), "arms": entries}, result


def report(args):
    arms, errors = parse(args.logs, args.run)
    warnings = []
    allow_target_miss = bool(getattr(args, "allow_target_miss", False))
    wanted = [args.single_arm] if args.single_arm else [1, 2, 3]
    fixture_meta = fixtures(args.fixtures) if args.fixtures else []
    if not fixture_meta:
        errors.append("supply --fixtures warp.txt bench2.txt bench3.txt to verify matched camera/pose commands")
    receipt_meta, expected_assets = asset_receipt(getattr(args, "asset_receipt", None))
    versions, counts_modes, cameras = set(), set(), set()
    build_ids, ranges = set(), set()
    rows = []
    for scene in wanted:
        arm = arms.get(scene)
        if arm is None:
            errors.append(f"missing arm {scene} ({VARIANTS[scene]})")
            continue
        meta, summary, result, ta = (arm[k] for k in ("metadata", "summary", "result", "ta"))
        version = 2 if number(meta, "schema") == 2 else 1
        counts = number(meta, "counts") if version == 2 else 0
        versions.add(version); counts_modes.add(counts)
        variant = names(meta)[scene]
        build_ids.add(meta.get("build"))
        ranges.add((number(meta, "begin"), number(meta, "end")))
        if fixture_meta and (number(meta, "begin"), number(meta, "end")) != (fixture_meta[scene - 1]["begin"], fixture_meta[scene - 1]["end"]):
            errors.append(f"arm {scene}: log/fixture frame range differs")
        if not summary or number(summary, "end_frame") != number(meta, "end"):
            errors.append(f"arm {scene}: measured range did not finish exactly")
        if summary.get("variant") != variant:
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
        geometry = geometry_report(arm, scene, errors) if version == 2 and counts else None
        identity = arm["identity"]
        triangle_target = None
        if version == 2:
            if counts not in (0, 1):
                errors.append(f"arm {scene}: invalid counts mode")
            if not expected_assets:
                errors.append(f"arm {scene}: v2 requires --asset-receipt with author package identities")
            else:
                expected = expected_assets[scene]
                triangles = int(expected["l0_triangles"])
                lo, hi = {1: (2940, 2940), 2: (900, 1500), 3: (300, 600)}[scene]
                target_met = lo <= triangles <= hi
                waived = not target_met and scene in (2, 3) and allow_target_miss
                reason = "Preserve black interior liners and roof undersides; look and production acceptance remain open."
                triangle_target = {"range": [lo, hi], "actual": triangles, "target_met": target_met,
                                   "measurement_exception": waived, "reason": reason if not target_met else None}
                if not target_met:
                    message = f"arm {scene}: package triangle target {triangles} outside {lo}..{hi}"
                    if waived:
                        warnings.append(message + "; explicit measurement exception only. " + reason)
                    else:
                        errors.append(message)
                if not identity or number(identity, "schema") != 2 or crc(identity.get("mesh_crc", "")) != crc(expected["candidate_crc"]) or number(identity, "mesh_bytes") != int(expected["candidate_bytes"]):
                    errors.append(f"arm {scene}: verified loaded package identity missing/mismatched")
                for observation in geometry or []:
                    if observation["status"] == "observed":
                        if observation["mesh_crc"] != crc(expected["candidate_crc"]) or observation["mesh_bytes"] != int(expected["candidate_bytes"]):
                            errors.append(f"arm {scene}: geometry package identity differs from author receipt")
                        cameras.add(observation["camera_hash"])
        rows.append({"scene": scene, "variant": variant, "build": meta.get("build"),
                     "instrumented_counts": bool(counts), "geometry": geometry, "triangle_target": triangle_target,
                     "asset_identity": expected_assets.get(scene) if version == 2 else None,
                     "loaded_identity": identity if version == 2 else None,
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
    if len(versions) > 1 or len(counts_modes) > 1:
        errors.append("do not combine v1/v2 or counts/timing builds in one comparison")
    if len(cameras) > 1:
        errors.append("geometry camera identity differs between measured passes/arms")
    if len(build_ids) > 1 or None in build_ids:
        errors.append("arms must identify the same build")
    if len(ranges) > 1:
        errors.append("arms have different measured room-frame ranges")
    return {"schema": "house-arena27-v2" if versions == {2} else "house-arena27-v1", "asset_receipt": receipt_meta, "environment": args.environment,
            "timing_label": "physical console" if args.environment == "console" else "cache-model Flycast; GPU timings are not hardware accurate",
            "run": args.run, "valid": not errors, "errors": errors, "warnings": warnings,
            "allow_target_miss": allow_target_miss,
            "budget_qualified": (len(rows) == len(wanted) and all(row["triangle_target"] and row["triangle_target"]["target_met"] for row in rows)) if versions == {2} else None,
            "eligibility": "invalid" if errors else "measurement-only-target-miss" if warnings else "validated",
            "fixtures": fixture_meta,
            "logs": [{"path": str(p), "sha256": digest(p)} for p in args.logs], "arms": rows}


def markdown(data):
    lines = [f"House arena27: {data['timing_label']}", "", "| Variant | GPU render ms | PVR registration ms | Present ms | CPU ms/tick | FPS | Windows |", "|---|---:|---:|---:|---:|---:|---:|"]
    fmt = lambda value: "missing" if value is None else f"{value:.3f}"
    for row in data["arms"]:
        lines.append("| " + " | ".join([row["variant"], *(fmt(row[k]) for k in ("gpu_render_ms", "pvr_registration_ms", "present_ms", "cpu_ms_per_tick", "fps")), str(row["accepted_windows"])]) + " |")
    for row in data["arms"]:
        target = row.get("triangle_target")
        if target and not target["target_met"]:
            status = "explicit measurement exception; triangle target remains missed" if target["measurement_exception"] else "strict triangle target check failed"
            lines += ["", f"{row['variant']}: TARGET MISS, {target['actual']} triangles versus {target['range'][0]}..{target['range'][1]}; {status}. {target['reason']}"]
        if row.get("instrumented_counts"):
            lines += ["", f"{row['variant']}: COUNTS BUILD. Timing is instrumented; use the separate counts=0 build for performance."]
            for observation in row["geometry"] or []:
                if observation["status"] != "observed":
                    lines.append(f"Pass {observation['pass']}: not observed; no zero-output pass invented.")
                    continue
                metric = observation["metrics"]
                lines.append(f"Pass {observation['pass']}, {observation['frames']} observed pictures: transformed {metric['transformed_positions']['mean_per_observed_frame']:.3f}, emitted corners {metric['emitted_corners']['mean_per_observed_frame']:.3f}, emitted triangles {metric['emitted_triangles']['mean_per_observed_frame']:.3f} per picture; camera {observation['camera_hash']}. Frustum/strip-group rejection details unavailable.")
        if row["ta_bytes_per_presented_frame"] is None:
            stream = row["native_stream"]
            lines += ["", f"{row['variant']}: TA list-byte count unavailable (streamed renderer). Native stream samples: {stream['measured_samples']}; model bytes {stream['model_bytes_samples']}; TA used {stream['ta_used_samples']}; TA peak {stream['ta_peak_samples']}; observed counter delta {stream['counter_delta']}."]
    if data.get("warnings"):
        lines += ["", "Measurement eligibility: " + data["eligibility"] + ". Geometry budget qualified: false."]
    if data["errors"]:
        lines += ["", "INCOMPLETE / INVALID: " + "; ".join(data["errors"])]
    lines += ["", "Registration, TA-done latency, GPU rendering and CPU work overlap. Do not add these columns. CPU is per tick; presentation is per drawn picture."]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("logs", nargs="+", type=Path)
    ap.add_argument("--environment", required=True, choices=("console", "cache-model-flycast"))
    ap.add_argument("--fixtures", nargs=3, type=Path, metavar=("WARP", "BENCH2", "BENCH3"))
    ap.add_argument("--asset-receipt", type=Path, help="v2 private author receipt with exact A/B/C package identities")
    ap.add_argument("--allow-target-miss", action="store_true", help="permit measurement of B/C triangle-target misses; all identity/completion checks and exact A=2940 remain mandatory")
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
