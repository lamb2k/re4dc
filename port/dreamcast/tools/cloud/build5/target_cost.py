#!/usr/bin/env python3
"""Build and price actual SH4 world replay/lookahead around a geometry edge.

Actual native_static.cpp layout, chunk_flush, chunk_emit and prefetch helpers
are retained. emit_pick alone is an observed external geometry edge. A separate
gather entry executes the exact scalar indexed-copy body. No vertex transform,
clipping, TA work, D-cache misses or whole frame is timed.
Loads/stores/PREF are opcode observations, not estimates of external traffic.
The unchanged Build 1 fixture linker and return-edge assembly are reused as
test infrastructure; no runtime assembly or linker change is introduced.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
D367 = DC / "tools/d367"
SOURCE = DC / "game/platform/native_static.cpp"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


sys.path.insert(0, str(D367 / "world_replay_lean"))
import pipeline_cost
import target_machine
from memory_trace import summarize
old_run = module("emit_cost_replay_run", D367 / "world_replay_lean/target_run.py")
profile = module("emit_cost_profile", D367 / "world_select_lean2/build_profile.py")
sys.path.insert(0, str(D367 / "world_setup_spike"))
import generate_fixture
import selection_cases
check_runtime = module("emit_cost_extractor", D367 / "world_submit_spike/check_runtime.py")


def build(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    compiler = args.sh4_cxx.resolve()
    flags, receipt = profile.derive(output / "release-profile", compiler,
        args.kos_root.resolve(), args.sdk_root.resolve(), cost_dependencies=True)
    builder = profile.Build(output)
    source = SOURCE.read_text()
    inputs = [SOURCE, HERE / "target_cost.py", HERE / "cost_fixture.cpp.in",
              *sorted((SOURCE.parent / "include").glob("scenery_*"))]
    input_hashes={str(p.relative_to(ROOT)):profile.sha(p) for p in inputs}
    emit = check_runtime.function(source, "int emit_pick(const Pick& pk){")
    controlled = source.replace(emit,
        "int emit_pick(const Pick& pk){return fixture_emit_control(this,&pk);}")
    modified = output / "native_static.cpp"
    modified.write_text('extern "C" int fixture_emit_control(void*,const void*);\n' + controlled)
    generated = output / "selection_fixture.cpp"
    extracted = generate_fixture.generate_source(generated, SOURCE)
    text = generated.read_text().replace(str(SOURCE.resolve()), str(modified))
    extra = (HERE / "cost_fixture.cpp.in").read_text()
    extra = extra.replace("@CHUNK_PART@", check_runtime.function(source, "struct ChunkPart {"))
    extra = extra.replace("@CHUNK_FLUSH@", check_runtime.function(source, "auto chunk_flush=[&]()->int{"))
    fixture = output / "target_fixture.cpp"
    fixture.write_text(text + "\n" + extra)

    # Exact test-only return/trap stubs from world_replay_lean/target_build.py.
    one = ("fixture_emit_control", "re4dc_model_packet_streaming", "re4dc_ui_frame")
    void = ("mat_load", "re4dc_model_result", "re4dc_model_direct_end",
            "re4dc_ps2_world_direct_end_batch", "re4dc_ps2_world_batch_close", "re4dc_model_packet_abort")
    traps = ("re4dc_model_packet_commit", "re4dc_log", "re4dc_missing")
    asm = []
    for name in (*one, *void, *traps):
        symbol = "_" + name
        asm += [f'.section .text.{symbol},"ax"', '.align 1', f'.global {symbol}',
                f'.type {symbol},@function', symbol + ':']
        if name in traps:
            asm += ['trapa #255']
        else:
            if name in one:
                asm += ['mov #1,r0']
            asm += ['rts', 'nop']
        asm += [f'.size {symbol},.-{symbol}']
    for name, value in (("re4dc_screen_wf", 0x44200000), ("re4dc_screen_hf", 0x43f00000),
                        ("re4dc_screen_half_wf", 0x43a00000), ("re4dc_screen_half_hf", 0x43700000)):
        symbol = "_" + name
        asm += [f'.section .data.{symbol},"aw"', '.align 2', f'.global {symbol}',
                f'.type {symbol},@object', symbol + ':', f'.long {value}', f'.size {symbol},4']
    edges = output / "edges.S"
    edges.write_text('\n'.join(asm) + '\n')
    edge_obj = output / "edges.o"
    prefix = str(compiler).removesuffix("g++")
    builder.run([prefix + "gcc", "-m4-single", "-ml", "-c", edges, "-o", edge_obj], label="edges")
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
    roots = ("fixture_layout", "fixture_adopt", "fixture_configure", "fixture_reset",
             "fixture_replay_layout", "fixture_prepare_replay", "fixture_replay",
             "fixture_picks_per_part", "fixture_replay_partial", "fixture_replay_total",
             "fixture_prepare_gather", "fixture_gather_entry", "fixture_gather_layout")
    prior = ["SCENERY_SELECT_ONLY=1", "SCENERY_REPLAY_LEAN=1", "SCENERY_SUBMIT_BATCH=1",
             "SCENERY_UV_SNAPSHOT=1", "SCENERY_SELECT_LEAN2=1", "PREF_WALK=0"]
    arms = {}
    for on in (0, 1):
        name = f"q{on}"
        expanded, arm_receipt = profile.expand_existing(output / "release-profile", compiler,
            args.sdk_root.resolve(), receipt, [*prior, f"SCENERY_EMIT_PREFETCH={on}"], prefix=name)
        arm_flags = [*expanded["native_static"], "-iquote", str(SOURCE.parent)]
        obj, elf = output / (name + ".o"), output / (name + ".elf")
        builder.run([*arm_flags, "-fstack-usage", "-c", fixture, "-o", obj], label=name)
        builder.run([compiler, "-m4-single", "-ml", "-nostartfiles", "-Wl,--gc-sections",
            "-Wl,-T," + str(linker), "-Wl,-e,_fixture_replay", *("-Wl,-u,_" + x for x in roots),
            obj, geometry, edge_obj, "-lm", "-o", elf], label=name + "-link")
        (output / (name + ".disassembly.txt")).write_bytes(builder.run(
            [prefix + "objdump", "-d", "-C", elf], label=name + "-disassembly"))
        arms[name] = dict(elf=str(elf), sha256=profile.sha(elf), object_sha256=profile.sha(obj),
            sections=profile.sections(elf), stack_usage=profile.stack_usage(obj.with_suffix(".su")),
            flags=arm_flags, profile=arm_receipt)
    for path,digest in input_hashes.items():
        assert profile.sha(ROOT/path)==digest,(path,"source changed during target build")
    report = dict(status="PASS", scope=__doc__, base="dc87c465", arms=arms,
        profile=receipt, extraction=extracted,
        emit_pick_replaced_sha256=hashlib.sha256(emit.encode()).hexdigest(),
        source_sha256=input_hashes,
        fixture_sha256=profile.sha(fixture))
    (output / "cost-build.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


class Machine(old_run.FixtureMachine):
    def observe_geometry(self):
        at, pick = self.reg[4:6]
        fields = self.fields
        def word(name, size=4):
            return self.word(at + fields[name], size)
        if not word("bound", 1):
            # The established check observes reset state and every live input.
            super().observe_geometry()
        else:
            row = dict(self.edge_records[-1], pick=self.bytes_at(pick, 6).hex())
            self.edge_records.append(row)
            self.emit_instruction_boundaries.append(len(self.instruction_pcs))
            for name in ("input", "output", "slots"):
                self.putword(at + fields[name], word(name) + 7)


def load(path):
    program, symbols = target_machine.scalar.load_elf(path)
    machine = Machine()
    for address, data, _ in program:
        machine.map(address, data)
    layout = [machine.word(symbols["_fixture_layout"][0] + 4 * i) for i in range(22)]
    replay = [machine.word(symbols["_fixture_replay_layout"][0] + 4 * i) for i in range(36)]
    assert layout[:4] == [1, 164, 252, 8] and replay[0] == 1
    machine.attach(symbols, replay)
    return machine, symbols, layout


def case_data(indexed, vertex_count=12):
    assert vertex_count % 4 == 0 and 12 <= vertex_count <= 256
    span=vertex_count//4
    let = selection_cases.meshlet([[(i*300+k*2, 100+(k&1)*5, 100) for k in range(span)] for i in range(4)])
    pkg, groups, cones = selection_cases.package([[[(0., [let] * 320)]]], indexed=indexed)
    if indexed:
        pkg = bytearray(pkg)
        mesh_at, strip_at = struct.unpack_from("<I", pkg, 48)[0], struct.unpack_from("<I", pkg, 56)[0]
        for i in range(320):
            first_strip = struct.unpack_from("<I", pkg, mesh_at + 28 * i + 4)[0]
            # Reverse pool offsets: first demanded vertex is not the pool base.
            struct.pack_into("<%dH" % vertex_count, pkg, strip_at + first_strip, *reversed(range(vertex_count)))
        pkg = bytes(pkg)
    config = selection_cases.defaults()
    config["inside"] = 1
    inp = selection_cases.input_bytes(config)
    data = struct.pack("<5I", 0x31505357, len(inp), len(pkg), len(groups), len(cones))
    return data + inp + pkg + groups + cones


def storage_traffic(machine,layout,gathered):
    base=layout[7]
    at=lambda offset:machine.word(base+offset)
    ranges=dict(meshlet_headers=(base+at(48),base+at(48)+28*at(24)),
        vertices=(base+at(52),base+at(52)+12*at(28)),
        offsets_and_strips=(base+at(56),base+at(56)+at(32)),
        gather=(gathered[0],gathered[0]+gathered[1]),
        picks=(gathered[2],gathered[2]+gathered[3]),
        stack=(machine.initial_regs[15]-65536,machine.initial_regs[15]))
    result={}
    remaining=list(machine.memory_events)
    prefetches=list(machine.prefetch_events)
    for name,(lo,hi) in ranges.items():
        selected=[e for e in remaining if lo<=e[3] and e[3]+e[4]<=hi]
        prefs=[e for e in prefetches if lo<=e[2]<hi]
        remaining=[e for e in remaining if e not in selected]
        prefetches=[e for e in prefetches if e not in prefs]
        result[name]=summarize(selected,prefs)
    result["other"]=summarize(remaining,prefetches)
    return result


def run(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    receipt = json.loads(args.build.read_text())
    paths = {name: Path(arm["elf"]) for name, arm in receipt["arms"].items()}
    models = {name: pipeline_cost.Model(output / ("model-" + name), path, args.host_cc)
              for name, path in paths.items()}
    machines={name:load(path) for name,path in paths.items()}
    rows = []
    shapes = [(1, 1), (1, 4), (1, 8), (8, 1), (8, 4), (32, 1), (32, 8)]
    for indexed in (False, True):
        data = case_data(indexed)
        (output / ("indexed.fixture" if indexed else "plain.fixture")).write_bytes(data)
        for partial in (0, 1):
            for parts, picks in shapes:
                name = f"{'indexed' if indexed else 'plain'}-partial{partial}-parts{parts}-picks{picks}"
                collected, semantics = {}, {}
                for arm, path in paths.items():
                    assert profile.sha(path) == receipt["arms"][arm]["sha256"]
                    machine, symbols, layout = machines[arm]
                    old_run.prepare(machine, symbols, layout, data)
                    machine.putword(symbols["_fixture_picks_per_part"][0], picks)
                    machine.putword(symbols["_fixture_replay_partial"][0], partial)
                    machine.execute(symbols["_fixture_prepare_replay"][0], parts)
                    machine.edge_records=[];machine.result_records=[];machine.end_records=[]
                    machine.emit_instruction_boundaries=[];machine.streaming_calls=0
                    row, trace = old_run.timed(machine, symbols, "fixture_replay")
                    row["pipeline"] = old_run.price(models[arm], name, trace)
                    gathered=[machine.word(symbols["_fixture_gather_layout"][0]+4*i) for i in range(4)]
                    row["storage_traffic"]=storage_traffic(machine,layout,gathered)
                    result = list(struct.unpack("<8I", machine.bytes_at(machine.layout[5], 32)))
                    assert result[:6] == [1, parts, 0, 0, 0, 0]
                    assert len(machine.edge_records) == parts * picks
                    assert machine.end_records == [7 * picks] * parts
                    assert len(machine.result_records) == parts
                    semantics[arm] = (result, machine.edge_records, machine.result_records, machine.end_records)
                    row.update(parts=parts, picks_per_part=picks, total_picks=parts*picks,
                        warm_cycles_per_part=row["pipeline"]["model_cycles"]/parts,
                        cold_i_cycles_per_part=row["pipeline"]["cold_icache"]["model_cycles"]/parts,
                        warm_cycles_per_meshlet=row["pipeline"]["model_cycles"]/(parts*picks),
                        cold_i_cycles_per_meshlet=row["pipeline"]["cold_icache"]["model_cycles"]/(parts*picks))
                    collected[arm] = row
                assert semantics["q0"] == semantics["q1"], (name, "replay inputs/state changed")
                before, after = collected["q0"], collected["q1"]
                rows.append(dict(name=name, indexed=indexed, partial=partial, parts=parts,
                    picks_per_part=picks, arms=collected,
                    warm_cycle_delta=after["pipeline"]["model_cycles"]-before["pipeline"]["model_cycles"],
                    cold_i_cycle_delta=after["pipeline"]["cold_icache"]["model_cycles"]-before["pipeline"]["cold_icache"]["model_cycles"]))
                print(json.dumps(dict(name=name, status="PASS")), flush=True)
    gather_rows=[]
    for indexed in (False, True):
        data=case_data(indexed,96)
        (output / ("gather-indexed.fixture" if indexed else "gather-plain.fixture")).write_bytes(data)
        for partial in (0,1,2):
            name=f"gather-{'indexed' if indexed else 'plain'}-partial{partial}"
            collected,semantics={},{}
            for arm,path in paths.items():
                machine,symbols,layout=machines[arm]
                old_run.prepare(machine,symbols,layout,data)
                machine.putword(symbols["_fixture_replay_partial"][0],partial)
                machine.execute(symbols["_fixture_prepare_replay"][0],1)
                gathered=[machine.word(symbols["_fixture_gather_layout"][0]+4*i) for i in range(4)]
                machine.map(gathered[2]+3,bytes([2,24,47]))
                machine.execute(symbols["_fixture_prepare_gather"][0])
                row,trace=old_run.timed(machine,symbols,"fixture_gather_entry")
                row["pipeline"]=old_run.price(models[arm],name,trace)
                row["storage_traffic"]=storage_traffic(machine,layout,gathered)
                returned=machine.reg[0]
                # Group metadata is not sufficient to prove every clip-strip
                # index lies in lo..hi. Nonempty partial gathers stay full.
                lo,hi=(0,96) if partial!=2 else (0,0)
                semantics[arm]=machine.bytes_at(returned+12*lo,12*(hi-lo))
                if indexed and arm=="q1":
                    untouched=(machine.bytes_at(gathered[0],12*lo)==bytes([0xa5])*(12*lo)
                        and machine.bytes_at(gathered[0]+12*hi,gathered[1]-12*hi)==bytes([0xa5])*(gathered[1]-12*hi))
                    assert untouched,(name,"writes outside selected gather window")
                    row["untouched_outside_copied"]=True
                row.update(input_vertices=96,copied_vertices=(96 if arm=="q0" else hi-lo) if indexed else 0,
                    selected_vertices=96 if partial==0 else 24 if partial==1 else 0,
                    compared_gather_vertices=hi-lo)
                collected[arm]=row
            assert semantics["q0"]==semantics["q1"],(name,"selected gathered vertices differ")
            before,after=collected["q0"],collected["q1"]
            gather_rows.append(dict(name=name,indexed=indexed,partial=partial,arms=collected,
                warm_cycle_delta=after["pipeline"]["model_cycles"]-before["pipeline"]["model_cycles"],
                cold_i_cycle_delta=after["pipeline"]["cold_icache"]["model_cycles"]-before["pipeline"]["cold_icache"]["model_cycles"]))
            print(json.dumps(dict(name=name,status="PASS")),flush=True)
    report = dict(status="PASS", scope=__doc__, build=str(args.build.resolve()),
        build_sha256=profile.sha(args.build), models={k:v.metadata() for k,v in models.items()},
        memory_controls=target_machine.memory_controls(), rows=rows,gather_rows=gather_rows,
        whole_frame="No measured or modelled whole-frame gain: geometry, actual r101 pick distribution and D-cache stalls are excluded.")
    (output / "cost-controls.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    bp = sub.add_parser("build")
    bp.add_argument("--output", type=Path, required=True)
    bp.add_argument("--sh4-cxx", type=Path, required=True)
    bp.add_argument("--kos-root", type=Path, required=True)
    bp.add_argument("--sdk-root", type=Path, required=True)
    rp = sub.add_parser("run")
    rp.add_argument("--output", type=Path, required=True)
    rp.add_argument("--build", type=Path, required=True)
    rp.add_argument("--host-cc", default="gcc")
    args = parser.parse_args()
    result = build(args) if args.command == "build" else run(args)
    print(json.dumps(dict(status=result["status"], output=str(args.output))))


if __name__ == "__main__":
    main()
