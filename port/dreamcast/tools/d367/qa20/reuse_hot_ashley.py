#!/usr/bin/env python3
"""Install the admitted pl11-hot body without replacing qualified sound banks.

All paths are explicit private inputs. No assets are included with this utility.
The original generator's source wrapper contains raw GC sound; the current disc
wrapper contains the already-qualified prebuilt AICA bank. Preserve that wrapper.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import le_mirror

SOURCE_SHA = "ecf3098097fcb2b2c86d632b62fd3d9112e61f5e39b56819db6a2e277fffcfa2"
BODY_SHA = "af13cc94d08e944c3470d62f73713fa26b4147215fae821e242eddaa228da72c"


def build(current, body):
    sha = lambda b: hashlib.sha256(b).hexdigest()
    if sha(current) != SOURCE_SHA or sha(body) != BODY_SHA:
        raise ValueError("Input is not the qualified current wrapper / admitted hot body")
    result = le_mirror.replace_native_payload(current, body)
    slot = le_mirror.native_payload_slot(current)
    if current[:slot] != result[:slot] or current[slot + 16:] != result[slot + 16:len(current)]:
        raise ValueError("Bytes outside the native payload header changed")
    if result[len(current):] != body or not current.count(b"AIC1"):
        raise ValueError("Expected appended body and prebuilt AICA bank")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current-drs", type=Path, required=True)
    parser.add_argument("--hot-body", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = build(args.current_drs.read_bytes(), args.hot_body.read_bytes())
    with args.out.open("xb") as out:
        out.write(result)
    print(json.dumps({"bytes": len(result), "sha256": hashlib.sha256(result).hexdigest(),
                      "unchanged_transport_and_sound": True}))
