#!/usr/bin/env python3
"""Price bounded production gather, hint and empty-pick SH4 phases.

The full frozen native_static.cpp is compiled with the current Make-derived
public recipe. No FTRV, FSRRA, clipper or complete-emission timing is claimed.
Constructor/material acquisition and package adoption are outside the traces.
Cycles are perfect-D-cache pipeline estimates, with warm/cold I-cache arms;
32-byte demand line touches and PREF requests are distinct observations.
"""
import argparse
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import struct
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
SOURCE = DC / "game/platform/native_static.cpp"
import build_profile
sys.path.insert(0, str(HERE.parent / "world_replay_lean"))
import pipeline_cost
import target_machine
from memory_trace import summarize
from target_machine import Machine
from target_run import price

# Only the already-bound successful owner check and result accounting execute
# in the nr==0 fixture. Cold reachable edges are linked as explicit traps.
RETURN_ONE = ("re4dc_source_world_binding_valid",)
RETURN_VOID = ("re4dc_model_result",)
TRAPS = ("re4dc_source_world_group_claimed", "re4dc_source_world_binding_failed",
    "re4dc_r11f_binding_valid", "re4dc_r11f_binding_failed",
    "re4dc_model_packet_reserve", "re4dc_model_packet_begin", "re4dc_model_packet_commit", "re4dc_model_packet_abort",
    "re4dc_model_direct_begin", "re4dc_model_direct_end", "re4dc_model_packet_streaming",
    "re4dc_ps2_world_direct_begin", "re4dc_ps2_world_direct_begin_batch",
    "re4dc_ps2_world_direct_end_batch", "re4dc_ps2_world_batch_close",
    "re4dc_ui_frame", "re4dc_pvs23_observe", "re4dc_pvs23_commit", "mat_load",
    "re4dc_log", "re4dc_missing", "sq_fast_cpy")
ROOTS = ("fixture_layout", "fixture_adopt", "fixture_prepare", "fixture_gather_phase",
         "fixture_prefetch_phase", "fixture_emit_zero", "fixture_snapshot")


def build(args, output):
    output.mkdir(parents=True, exist_ok=False)
    compiler = args.sh4_cxx.resolve()
    flags, profile = build_profile.derive(output / "release-profile", compiler,
        args.kos_root.resolve(), args.sdk_root.resolve(), dependencies=True)
    builder = build_profile.Build(output)
    inputs = {str(SOURCE.relative_to(ROOT)): build_profile.sha(SOURCE),
              str((HERE / "emit_target.cpp.in").relative_to(ROOT)): build_profile.sha(HERE / "emit_target.cpp.in")}
    for p in sorted((SOURCE.parent / "include").glob("scenery_*")):
        inputs[str(p.relative_to(ROOT))] = build_profile.sha(p)
    frozen = output / "native_static.cpp"; frozen.write_bytes(SOURCE.read_bytes())
    fixture = output / "emit_target.cpp"
    fixture.write_text((HERE / "emit_target.cpp.in").read_text().replace("@NATIVE_SOURCE@", str(frozen)))
    stubs = output / "edges.S"; asm = []
    for name in (*RETURN_ONE, *RETURN_VOID, *TRAPS):
        symbol = "_" + name
        asm += [f'.section .text.{symbol},"ax"', '.align 1', f'.global {symbol}',
                f'.type {symbol},@function', symbol + ':']
        if name in TRAPS: asm += ['trapa #255']
        else:
            if name in RETURN_ONE: asm += ['mov #1,r0']
            asm += ['rts', 'nop']
        asm += [f'.size {symbol},.-{symbol}']
    for name, value in (("re4dc_cache20_mask", 4), ("re4dc_screen_wf", 0x44200000),
        ("re4dc_screen_hf", 0x43f00000), ("re4dc_screen_half_wf", 0x43a00000),
        ("re4dc_screen_half_hf", 0x43700000)):
        symbol = "_" + name
        asm += [f'.section .data.{symbol},"aw"', '.align 2', f'.global {symbol}',
                f'.type {symbol},@object', symbol + ':', f'.long {value}', f'.size {symbol},4']
    stubs.write_text('\n'.join(asm) + '\n')
    prefix = str(compiler).removesuffix("g++")
    stub_obj = output / "edges.o"
    builder.run([prefix + "gcc", "-m4-single", "-ml", "-c", stubs, "-o", stub_obj], label="edges")
    geometry = output / "pvr_geometry.o"
    builder.run([*flags["pvr_geometry"], "-c", DC / "room/pvr_geometry.cpp", "-o", geometry], label="geometry")
    linker = output / "fixture.ld"
    linker.write_text('''SECTIONS {
 /DISCARD/ : { *(.ctors*) *(.dtors*) *(.init_array*) *(.fini_array*) }
 . = 0x100000;
 .text : { *(.text*) }
 .rodata : { *(.rodata*) }
 .data : { *(.data*) }
 .bss : { *(.bss*) *(COMMON) }
}
''')
    arms = {}
    for enabled, pref in itertools.product((0, 1), repeat=2):
        name = f"e{enabled}-p{pref}"
        expanded, _ = build_profile.expand_existing(output / "release-profile", compiler,
            args.sdk_root.resolve(), profile,
            [f"SCENERY_EMIT_PREFETCH={enabled}", f"PREF_WALK={pref}"], prefix=name)
        common = [*expanded["native_static"], "-iquote", str(SOURCE.parent)]
        obj, elf = output / (name + ".o"), output / (name + ".elf")
        builder.run([*common, "-fstack-usage", "-c", fixture, "-o", obj], label=name)
        builder.run([compiler, "-m4-single", "-ml", "-nostartfiles", "-Wl,--gc-sections",
            "-Wl,-T," + str(linker), "-Wl,-e,_fixture_gather_phase",
            *("-Wl,-u,_" + x for x in ROOTS), obj, geometry, stub_obj, "-lm", "-o", elf], label=name + "-link")
        (output / (name + ".disassembly.txt")).write_bytes(builder.run(
            [prefix + "objdump", "-d", "-C", elf], label=name + "-disassembly"))
        arms[name] = dict(elf=str(elf), sha256=build_profile.sha(elf), flags=common,
            object_sha256=build_profile.sha(obj), sections=build_profile.sections(elf),
            stack_usage=build_profile.stack_usage(obj.with_suffix(".su")))
        print("BUILT", name, flush=True)
    for path, digest in inputs.items():
        assert build_profile.sha(ROOT / path) == digest, (path, "changed during build")
    result = dict(status="PASS", scope=__doc__, arms=arms, source_sha256=inputs, profile=profile,
        observed_return_edges=list(RETURN_ONE + RETURN_VOID), forbidden_edges=list(TRAPS),
        complete_geometry_timing=False, constructor_and_bind_acquisition_timed=False)
    (output / "target-build.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def package(vertices, indexed, meshlets, phase):
    """Valid one-part R4IM fixtures; actual MeshPackage::adopt validates each."""
    body = bytearray(112 if indexed else 80)
    def section(data, extra=0):
        body.extend(bytes(-len(body) % 4 + extra)); at = len(body); body.extend(data); return at
    offsets = [(k * 37 + 5) % vertices for k in range(vertices)]
    points = [struct.pack("<6H", k, k * 7 + 3, k * 11 + 1, k * 13 + 2, k * 17 + 4, 0x8000 | k)
              for k in range(vertices)]
    strips = bytearray(); lets = []; table_offsets = []
    for _ in range(meshlets):
        strips.extend(bytes(-len(strips) % 2)); at = len(strips); table_offsets.append(at)
        if indexed: strips.extend(struct.pack("<%dH" % vertices, *offsets))
        strips.extend(bytes((3, 0, 1, 2)))
        lets.append((0, at, 4, vertices, 1 | (0x8000 if indexed else 0), 0, 0, 0, 4096, 4096, 4096))
    mesh_at = section(struct.pack("<HBBHHIII12f", 1, 0, 0, vertices, 1, 0, 0, 1,
                                  0, 0, 0, 1, 1, 1, 0, 0, 0, 4096, 4096, 4096))
    part_at = section(struct.pack("<2I4B2I4f", 0, 32, 0, 0, 0, 0, 0, meshlets, .125, .25, 1/32768, 1/16384))
    let_at = section(b"".join(struct.pack("<3I8H", *l) for l in lets))
    vertex_at = section(b"".join(points), phase)
    strip_at = section(strips); palette_at = section(struct.pack("<I", 0xffffffff))
    if indexed:
        part_lod_at = section(struct.pack("<2I", 0, 1))
        cluster_at = section(struct.pack("<6H2I", 0, 0, 0, 4096, 4096, 4096, 0, 1))
        level_at = section(struct.pack("<2If", 0, meshlets, 0.))
        struct.pack_into("<8I", body, 80, 1, 1, part_lod_at, cluster_at, level_at, 0, 0, 0)
    struct.pack_into("<4s19I", body, 0, b"R4IM", 3 if indexed else 1, len(body), 0,
        1, 1, meshlets, vertices, len(strips), 1, mesh_at, part_at, let_at, vertex_at, strip_at, palette_at, 2, 0, 0, 0)
    meta = dict(vertices=vertices, indexed=indexed, meshlets=meshlets, alignment_padding=phase,
        meshlet_offset=let_at, vertex_offset=vertex_at, strip_offset=strip_at,
        strip_bytes=len(strips), table_offsets=table_offsets)
    return bytes(body), meta, points, offsets


class FixtureMachine(Machine):
    def attach(self, symbols):
        self.symbols = symbols
        self.boundary_calls = []
        self.hooks = {symbols["_" + name][0]: name for name in RETURN_ONE + RETURN_VOID + TRAPS
                      if "_" + name in symbols}

    def step(self, pc, delay=False):
        if self.memory_tracking and pc in getattr(self, "hooks", {}):
            name = self.hooks[pc]
            assert name not in TRAPS, ("forbidden external edge", name)
            self.boundary_calls.append((len(self.instruction_pcs), name, list(self.reg[4:7])))
        return super().step(pc, delay)

    def word(self, at):
        return struct.unpack("<I", self.bytes_at(at, 4))[0]


def load(arm):
    path = Path(arm["elf"]); assert build_profile.sha(path) == arm["sha256"]
    program, symbols = target_machine.scalar.load_elf(path)
    machine = FixtureMachine()
    for address, data, _ in program: machine.map(address, data)
    machine.attach(symbols)
    layout = [machine.word(symbols["_fixture_layout"][0] + 4*i) for i in range(23)]
    assert layout[:2] == [1, 32] and layout[3] == 8
    return machine, symbols, layout


def prepare(machine, symbols, layout, blob, config):
    assert len(blob) <= layout[6]
    machine.map(layout[5], blob)
    machine.execute(symbols["_fixture_adopt"][0], len(blob)); assert machine.reg[0] == 1, "package adopt failed"
    machine.map(layout[4], struct.pack("<8I", *config))
    machine.execute(symbols["_fixture_prepare"][0])


def timed(machine, symbols, entry, argument, layout, meta):
    machine.minimum_sp = machine.reg[15]; machine.boundary_calls = []
    machine.observe_start(); machine.execute(symbols["_" + entry][0], argument)
    traffic = machine.observe_stop(); trace = SimpleNamespace(instruction_pcs=list(machine.instruction_pcs),
        steps=machine.steps, read=machine.read)
    regions = {
        "package_headers": (layout[5] + meta["meshlet_offset"], meta["meshlets"] * 28),
        "vertex_pool": (layout[5] + meta["vertex_offset"], meta["vertices"] * 12),
        "offsets_and_strips": (layout[5] + meta["strip_offset"], meta["strip_bytes"]),
        "gather_buffer": (layout[9], layout[10]), "projected_cache": (layout[11], layout[12]),
        "outcodes": (layout[13], layout[14]), "emitter": (layout[15], layout[16]),
        "package_object": (layout[17], layout[18]), "picks": (layout[7], layout[8]),
        "stats": (layout[21], layout[22]), "stack": (machine.minimum_sp, machine.initial_regs[15] - machine.minimum_sp)}
    classified = {}
    for name, (start, size) in regions.items():
        events = [e for e in machine.memory_events if start <= e[3] < start + size]
        prefs = [e for e in machine.prefetch_events if start <= e[2] < start + size]
        classified[name] = summarize(events, prefs)
    row = dict(instructions=machine.steps, traffic=traffic, regions=classified,
        peak_stack_bytes=machine.initial_regs[15] - machine.minimum_sp,
        symbol_instructions=pipeline_cost.symbol_costs(trace, symbols),
        observed_edges=machine.boundary_calls)
    # Sum unique lines separately per original meshlet, rather than mistaking
    # the union of an entire run for the repeated per-meshlet working set.
    bind_boundaries = [x[0] for x in machine.boundary_calls if x[1] == "re4dc_source_world_binding_valid"]
    bounds = [0, *bind_boundaries, machine.steps]
    row["segment_data_line_touches"] = sum(summarize(
        [e for e in machine.memory_events if a <= e[0] < b])["cached"]["unique_data_lines"]
        for a, b in zip(bounds, bounds[1:]))
    row["segment_definition"] = "entry-to-first bind check, successive bind checks, final exit; not cache misses"
    return row, trace


def run(build_result, args, output):
    output.mkdir(parents=True, exist_ok=False)
    models = {name: pipeline_cost.Model(output / ("model-" + name), Path(arm["elf"]), args.host_cc)
              for name, arm in build_result["arms"].items()} if not args.no_model else {}
    rows = []
    def record(kind, name, v, indexed, count, phase, nr, lo, hi, mask=1, primed=0, next_nr=0, hint=0):
        blob, meta, points, offsets = package(v, indexed, count + 1, phase)
        path = output / (name + ".r4im"); path.write_bytes(blob)
        config = (count, nr, lo, hi, mask, primed, next_nr, hint)
        arms, semantics = {}, {}
        for arm_name, arm in build_result["arms"].items():
            machine, symbols, layout = load(arm)
            prepare(machine, symbols, layout, blob, config)
            entry = {"gather": "fixture_gather_phase", "hint": "fixture_prefetch_phase", "empty": "fixture_emit_zero"}[kind]
            row, trace = timed(machine, symbols, entry, 0, layout, meta)
            if arm_name in models: row.update(price(models[arm_name], name, trace))
            if kind == "gather":
                result = machine.reg[0]
                first, last = (0, v-1) if nr == 255 else (lo, hi)
                selected = machine.bytes_at(result + first*12, (last-first+1)*12)
                expected = b"".join(points[offsets[i] if indexed else i] for i in range(first,last+1))
                assert selected == expected, (name, arm_name, "selected gather bytes")
                if indexed and arm_name.startswith("e1") and nr != 255:
                    assert machine.bytes_at(layout[9], first*12) == bytes([0xa5])*(first*12)
                    assert machine.bytes_at(layout[9]+(last+1)*12, (256-last-1)*12) == bytes([0xa5])*((256-last-1)*12)
                row["selected_bytes_sha256"] = hashlib.sha256(selected).hexdigest(); semantics[arm_name] = selected
            elif kind == "empty":
                assert machine.reg[0] == 1
                machine.execute(symbols["_fixture_snapshot"][0])
                result = list(struct.unpack("<8I", machine.bytes_at(layout[19], 32)))
                assert result[:6] == [count,count,0,0,0,0] and result[7] == 0
                assert all(x[2] == [0,0,0] for x in row["observed_edges"] if x[1] == "re4dc_model_result")
                row["state"] = result; semantics[arm_name] = result[:6] + result[7:]
            else:
                assert machine.bytes_at(layout[9], layout[10]) == bytes([0xa5])*layout[10]
                row["stores_to_geometry"] = row["regions"]["gather_buffer"]["cached"]["store_bytes"]
                assert row["stores_to_geometry"] == 0
            arms[arm_name] = row
        if semantics:
            assert all(v == next(iter(semantics.values())) for v in semantics.values()), (name, "semantic equality")
        rows.append(dict(kind=kind, name=name, package=meta, config=dict(zip(
            ("count","nr","lo","hi","gmask","primed","next_nr","header_hint"),config)),
            package_sha256=build_profile.sha(path), arms=arms))
        (output / "progress.json").write_text(json.dumps(rows, indent=2) + "\n")
        print("PASS", kind, name, flush=True)
    phases = (0,) if args.quick else (0, 4, 16, 28)
    for v in (16, 64, 128):
        for kept in (4, v//2, v):
            lo = (v-kept)//2
            for phase in phases:
                record("gather", f"gather-v{v}-n{kept}-a{phase}", v, True, 1, phase, 1, lo, lo+kept-1)
        record("gather", f"gather-whole-v{v}", v, True, 1, 0, 255, 0, 0)
        record("gather", f"gather-plain-v{v}", v, False, 1, 0, 1, v//4, v//2-1)
    for v in (16,64,128):
        for indexed, primed, count in itertools.product((False,True),(0,v),(1,8)):
            if args.quick and count==8: continue
            record("empty", f"empty-v{v}-i{int(indexed)}-p{primed}-c{count}", v,indexed,count,0,0,0,0,primed=primed)
    for indexed, nr, mask, header in itertools.product((False,True),(1,255),(0,1),(0,1)):
        if args.quick and (mask==0 or header==0): continue
        record("hint",f"hint-i{int(indexed)}-n{nr}-m{mask}-h{header}",64,indexed,1,0,nr,16,23,mask=mask,hint=header)
    # Cross-part positive lookahead: a genuinely empty current pick executes
    # the actual interleaving/control path and safely hints the queued next one.
    for indexed in (False,True):
        record("empty",f"lookahead-i{int(indexed)}",64,indexed,1,0,0,16,23,mask=1,primed=64,next_nr=1)
    result = dict(status="PASS", scope=__doc__, checks=len(rows), cases=rows,
        memory_controls=target_machine.memory_controls(),
        model={name: model.metadata() for name,model in models.items()},
        source_sha256={str(p):build_profile.sha(p) for p in (Path(__file__),Path(target_machine.__file__),
            Path(target_machine.scalar.__file__),HERE.parent/"world_replay_lean/memory_trace.py",Path(pipeline_cost.__file__))},
        frame_population=dict(r101_parts=87,r100_parts=50,meshlets_per_part="unknown",
            formula_ms="cycles_per_eligible_meshlet * eligible_meshlets_per_part * measured_parts / 200000",
            note="200 MHz model estimate; no measured cache-miss/stall or frame-time claim"))
    (output / "target-controls.json").write_text(json.dumps(result,indent=2)+"\n")
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--sh4-cxx",type=Path)
    p.add_argument("--kos-root",type=Path)
    p.add_argument("--sdk-root",type=Path)
    p.add_argument("--build",type=Path,help="reuse an immutable target-build.json")
    p.add_argument("--build-only",action="store_true")
    p.add_argument("--host-cc",default="gcc")
    p.add_argument("--quick",action="store_true")
    p.add_argument("--no-model",action="store_true")
    args = p.parse_args(); out = args.output.resolve(); out.mkdir(parents=True,exist_ok=False)
    if args.build: result = json.loads(args.build.read_text())
    else:
        assert all((args.sh4_cxx,args.kos_root,args.sdk_root)), "toolchain/KOS/SDK required to build"
        result = build(args,out/"build")
    if not args.build_only: result=run(result,args,out/"run")
    print(json.dumps(dict(status=result["status"],checks=result.get("checks"),arms=list(result.get("arms",{})))))


if __name__ == "__main__": main()
