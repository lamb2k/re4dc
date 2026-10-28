#!/usr/bin/env python3
"""Execute actual extracted QA_LINK datagram-ring methods on synthetic SH4 RAM.

The complete Ring struct and the datagram-limit enum are copied verbatim from
qa_link.cpp, using each arm's real Make-derived transport flags. No socket,
modem, IRQ, scheduler, timer or heap-service stub is involved in these methods.
This bounded piece does not predict PPP latency or a transport-pump deadline.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
REPLAY = DC / "tools/d367/world_replay_lean"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = result
    spec.loader.exec_module(result)
    return result


controls = module("b28_ring_controls", HERE / "build_controls.py")
profile = controls.profile
kernel = module("b28_ring_kernel", DC / "tools/d367/actor_bytes_lean/kernel_audit.py")


def extract(text):
    start = text.index("struct Ring {")
    end = text.index("\n};", start) + len("\n};")
    limit = re.search(r"enum \{ kDatagram28 = [^;]+;", text)
    assert limit and "kDatagram28 = 1200" in limit.group()
    return text[start:end], limit.group()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "sh4-cxx", "kos-root", "sdk-root"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--baseline", default=controls.BASELINE)
    parser.add_argument("--reuse", type=Path,
        help="Keep completed rows after exact fresh object/ELF identity and fragment checks; execute only missing cases")
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    cxx, kos, sdk = args.sh4_cxx.resolve(), args.kos_root.resolve(), args.sdk_root.resolve()
    baseline = subprocess.check_output(["git", "rev-parse", args.baseline], cwd=ROOT, text=True).strip()
    previous = json.loads(args.reuse.read_text()) if args.reuse else None
    if previous:
        assert previous["status"] == "PASS"
        # Permit an integration rebase only with an ancestor receipt; exact
        # fragment and freshly compiled object/ELF identities remain required.
        subprocess.run(["git", "merge-base", "--is-ancestor", previous["baseline"], baseline],
                       cwd=ROOT, check=True)
    source = DC / "game/qa_link.cpp"
    source_before = profile.sha(source)
    body, limits = extract(source.read_text())
    if previous:
        assert previous["extracted_source"]["ring_sha256"] == hashlib.sha256(body.encode()).hexdigest()
        assert previous["extracted_source"]["enum_sha256"] == hashlib.sha256(limits.encode()).hexdigest()
    sources = [Path(__file__), HERE / "build_controls.py", DC / "tools/d367/actor_bytes_lean/kernel_audit.py",
               *[REPLAY / (name + ".py") for name in
                 ("target_machine", "sh4_machine", "memory_trace", "pipeline_cost", "target_run")]]
    frozen = {str(path.relative_to(ROOT)): profile.sha(path) for path in sources}
    builder = profile.Build(out)
    prefix = str(cxx).removesuffix("g++")
    fixture = out / "fixture.cpp"
    fixture.write_text('#include <stddef.h>\n' + limits + '\n' + body + '\n'
        'struct Args { Ring* ring; void* data; unsigned count; };\n'
        'extern "C" int fixture_put(const Args* args) { return args->ring->put(args->data,args->count); }\n'
        'extern "C" int fixture_get(const Args* args) { return args->ring->get(args->data,args->count); }\n'
        'extern "C" const unsigned fixture_layout[]={sizeof(Ring),offsetof(Ring,buf),offsetof(Ring,head),offsetof(Ring,tail)};\n')
    script = out / "fixture.ld"
    script.write_text('SECTIONS { . = 0x100000; .text : { *(.text*) } .rodata : { *(.rodata*) } '
                      '.data : { *(.data*) } .bss : { *(.bss*) *(COMMON) } }\n')
    cases = [dict(name="put-command16", phase="put", count=16),
             dict(name="put-telemetry1100", phase="put", count=1100),
             dict(name="put-telemetry1130", phase="put", count=1130),
             dict(name="put-limit1200", phase="put", count=1200),
             dict(name="put-wrapped1130", phase="put", count=1130, position=4094),
             dict(name="put-oversize1201", phase="put", count=1201),
             dict(name="put-full1130", phase="put", count=1130, used=4000),
             dict(name="get-command16", phase="get", count=16),
             dict(name="get-telemetry1100", phase="get", count=1100),
             dict(name="get-limit1200", phase="get", count=1200),
             dict(name="get-wrapped1130", phase="get", count=1130, position=4094),
             dict(name="get-truncated1130", phase="get", count=1130, capacity=512),
             dict(name="get-empty", phase="get", count=0)]
    rows, configurations = [], {}
    for arm, value in (("old", 0), ("new", 1)):
        options = controls.QA + ["QA_LINK=1", controls.KNOB + "=" + str(value)]
        flags, receipt, _ = profile.derive(out / (arm + "-profile"), cxx, kos, sdk, options, units=("qa_link",))
        command = flags["qa_link"]
        assert ("-D" + controls.MACRO + "=1" in command) == bool(value)
        obj, elf = out / (arm + ".o"), out / (arm + ".elf")
        builder.run([*command, "-fstack-usage", "-c", fixture, "-o", obj], label=arm + "-compile")
        builder.run([cxx, "-m4-single", "-ml", "-nostartfiles", "-Wl,--gc-sections", "-Wl,-T," + str(script),
                     "-Wl,-e,_fixture_put", "-Wl,-u,_fixture_get", "-Wl,-u,_fixture_layout", obj, "-o", elf], label=arm + "-link")
        undefined = builder.run([prefix + "nm", "-u", elf], label=arm + "-undefined").decode()
        assert not undefined.strip(), (arm, undefined)
        program, symbols = kernel.target_machine.scalar.load_elf(elf)
        model = kernel.pipeline_cost.Model(out / (arm + "-model"), elf)
        configurations[arm] = dict(profile=receipt, object_sha256=profile.sha(obj), elf_sha256=profile.sha(elf),
            sections=profile.sections(obj), linked_sections=profile.sections(elf),
            stack_usage=profile.stack_usage(obj.with_suffix(".su")), model=model.metadata())
        if previous:
            for key in ("object_sha256", "elf_sha256"):
                assert configurations[arm][key] == previous["configurations"][arm][key], (key, "ring code changed")
        for case in cases:
            prior = next((row for row in previous["cases"] if row["arm"] == arm and row["name"] == case["name"]), None) if previous else None
            if prior:
                assert all(prior[key] == value for key, value in case.items())
                rows.append(dict(copy.deepcopy(prior), reused_from_raw_sha256=profile.sha(args.reuse)))
                print("REUSED identical target code", arm, case["name"], flush=True)
                continue
            m = kernel.Machine()
            for address, data, _ in program:
                m.map(address, data)
            layout = struct.unpack("<4I", m.bytes_at(symbols["_fixture_layout"][0], 16))
            assert layout == (4104, 0, 4096, 4100)
            count, capacity, position = case["count"], case.get("capacity", 1408), case.get("position", 0)
            packet = bytes((i * 17 + 3) & 255 for i in range(count))
            ring = bytearray([0xa5]) * 4104
            if case["phase"] == "put":
                head, tail = position + case.get("used", 0), position
                data = bytearray(packet + bytes([0xcc]) * (1408 - count))
            else:
                head, tail = position + (count + 2 if count else 0), position
                data = bytearray([0xcc]) * 1408
                for index, byte in enumerate(struct.pack("<H", count) + packet):
                    ring[(tail + index) % 4096] = byte
            struct.pack_into("<II", ring, 4096, head, tail)
            before_ring, before_data = bytearray(ring), bytearray(data)
            m.map(0x9000, struct.pack("<III", 0x20000, 0x24000, count if case["phase"] == "put" else capacity))
            m.map(0x20000, ring)
            m.map(0x24000, data)
            m.minimum_sp = m.reg[15]
            m.observe_start()
            m.execute(symbols["_fixture_" + case["phase"]][0], 0x9000)
            m.observe_stop()
            if case["phase"] == "put":
                accepted = count <= (1200 if value else 1400) and head-tail+count+2 <= 4096
                result = int(accepted)
                if accepted:
                    for index, byte in enumerate(struct.pack("<H", count) + packet):
                        before_ring[(head + index) % 4096] = byte
                    struct.pack_into("<I", before_ring, 4096, head + count + 2)
            elif not count:
                result = -1
            else:
                result = -2 if value and count > capacity else min(count, capacity)
                if result >= 0:
                    before_data[:result] = packet[:result]
                struct.pack_into("<I", before_ring, 4100, tail + count + 2)
            assert m.reg[0] == result & 0xffffffff, (arm, case, hex(m.reg[0]), result)
            assert m.bytes_at(0x20000, 4104) == before_ring, (arm, case, "ring contents")
            assert m.bytes_at(0x24000, 1408) == before_data, (arm, case, "payload contents")
            trace = SimpleNamespace(instruction_pcs=m.instruction_pcs, steps=m.steps, read=m.read)
            rows.append(dict(arm=arm, **case, result=result, instructions=m.steps,
                peak_stack_bytes=m.initial_regs[15]-m.minimum_sp,
                traffic=kernel.traffic_details(m.memory_events, m.prefetch_events),
                **kernel.price_helpers.price(model, arm + "-" + case["name"], trace)))
            print("PASS", arm, case["name"], flush=True)
    assert extract(source.read_text()) == (body, limits), "Ring or datagram enum changed during run"
    assert frozen == {path: profile.sha(ROOT / path) for path in frozen}, "harness changed during run"
    frame = {}
    for arm in ("old", "new"):
        cycles = sum(row["model_cycles"] for row in rows if row["arm"] == arm
                     and row["name"] in ("put-telemetry1130", "get-command16"))
        frame[arm] = dict(cycles=cycles, total_ms=30 + cycles / 200000)
    result = dict(status="PASS", baseline=baseline, scope=__doc__, source_sha256=frozen,
        extracted_source=dict(path=str(source.relative_to(ROOT)), file_sha256_before=source_before,
            file_sha256_after=profile.sha(source), ring_sha256=hashlib.sha256(body.encode()).hexdigest(),
            enum_sha256=hashlib.sha256(limits.encode()).hexdigest(),
            scope="Only the exact Ring and datagram-limit enum are compiled from this file. Other lifecycle edits do not enter the fixture."),
        configurations=configurations, cases=rows, memory_controls=kernel.target_machine.memory_controls(),
        reused_receipt_sha256=profile.sha(args.reuse) if previous else None,
        reused_receipt_baseline=previous["baseline"] if previous else None,
        whole_frame_modelled=dict(label="MODELLED", assumed_other_work_ms=30, cpu_mhz=200,
            assumptions="One 1130-byte enqueue and one 16-byte dequeue; all socket/PPP/game work held in the assumed remainder.", **frame),
        limitations="Bounded single-producer/single-consumer method execution with no concurrency or external services. Oversize and truncation cases intentionally change outcomes. Perfect D-cache, warm/cold-I separated; distinct lines are not measured cache misses.")
    (out / "ring-cost.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", cases=len(rows), receipt=str(out / "ring-cost.json"))))


if __name__ == "__main__":
    main()
