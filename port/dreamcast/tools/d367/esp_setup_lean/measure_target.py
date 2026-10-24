#!/usr/bin/env python3
"""Price compiled SH4 effect setup, with observed demand bytes and 32-byte lines.

Packet construction retains the complete native UI translation unit, real
Entry/Package layouts and real descriptor methods. The unchanged KOS sprite
context/compiler is compiled separately from its pinned source with the same
target CPU options; its miss-only cost is shown separately. No texture lookup,
allocation, draw queue walk, PVR transfer, cache misses or frame is executed.
Warm/cold-I prices use the existing perfect-D synthetic pipeline model.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
sys.path.insert(0, str(HERE.parent / "world_replay_lean"))
import pipeline_cost
import target_machine
from memory_trace import summarize, region
import build_profile as profile


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


old_run = module("esp_target_price", HERE.parent / "world_replay_lean/target_run.py")
extractor = module("esp_target_extract", HERE.parent / "world_submit_spike/check_runtime.py")


def build(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    compiler, kos, sdk = args.sh4_cxx.resolve(), args.kos_root.resolve(), args.sdk_root.resolve()
    builder = profile.Build(output)
    prefix = str(compiler).removesuffix("g++")
    native = DC / "game/platform/native_ui.cpp"
    texture = DC / "room/texture_package.cpp"
    source = texture.read_text()
    signatures = ("std::uint32_t pvr_format(const Texture& texture) {",
                  "const Texture* Package::textures() const {",
                  "pvr_ptr_t Package::pvr_texture(std::uint32_t index) const {")
    bodies = [extractor.function(source, sig) for sig in signatures]
    methods = output / "texture_methods.cpp"
    methods.write_text('#include "' + str(DC / "room/texture_package.hpp") + '"\n'
                       'namespace re4dc::texture {\n' + '\n'.join(bodies) + '\n}\n')
    fixture = output / "packet_fixture.cpp"
    fixture.write_text((HERE / "packet_fixture.cpp.in").read_text()
        .replace("@TEXTURE_HEADER@", str(DC / "room/texture_package.hpp"))
        .replace("@NATIVE_SOURCE@", str(native)))
    esp_source=ROOT/"src/game/esp_sub.cpp"
    esp_text=esp_source.read_text()
    begin=esp_text.index("    ESPCT(2);",esp_text.index("void EspCommonTrans(cEsp* esp)\n{"))+len("    ESPCT(2);")
    end=esp_text.index("\n#if defined(RE4DC_ESP_SPRITE_FAST)",begin)
    setup_phase=esp_text[begin:end]
    assert "EspSpriteEmit" not in setup_phase and "FxEssentialSetupCut" in setup_phase
    cut_fixture=output/"cut_fixture.cpp"
    cut_fixture.write_text((HERE/"cut_fixture.cpp.in").read_text()
        .replace("@ESP_SOURCE@",str(esp_source)).replace("@SETUP_PHASE@",setup_phase))
    edges=output/"matrix_edges.c"
    edges.write_text('''void low_RotMatrix(void* m,void* r){}
void re4dc_zam_MTXRotRad(void* m,char axis,float angle){}
void re4dc_zam_MTXConcat(const void* a,const void* b,void* c){}
void re4dc_zam_MTXMultVec(const void* m,const void* a,void* b){}
float EspGetCameraPan(void){return 0.0f;}
void fixture_emit_edge(void* p){}
''')
    edge_obj=output/"matrix_edges.o"
    builder.run([prefix+"gcc",*profile.target_flags(kos),"-c",edges,"-o",edge_obj],label="matrix-edges")
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
    fails = output / "fail.c"
    fails.write_text('int hardware_sys_mode(int* region){return 0;}\n'
                     'void __assert(const char* f,int l,const char* e,const char* m,const char* u)'
                     '{for(;;){}}\n')
    fail_obj = output / "fail.o"
    builder.run([prefix + "gcc", *profile.target_flags(kos), "-c", fails, "-o", fail_obj], label="fail")
    arms, profiles = {}, {}
    for level in (0, 3):
        directory = output / f"profile-fx{level}"
        _, receipt = profile.derive(directory, compiler, kos, sdk, fx_level=level)
        profiles[f"fx{level}"] = receipt
        flags, texture_profile = profile.expand_existing(directory, compiler, sdk, receipt,
            prefix="texture", specs=(("texture", "native-reuse/texture_package.o", "../room/texture_package.cpp", ""),))
        texture_obj = output / f"fx{level}-texture.o"
        builder.run([*flags["texture"], "-fstack-usage", "-c", methods, "-o", texture_obj], label=f"fx{level}-texture")
        prim = kos / "kernel/arch/dreamcast/hardware/pvr/pvr_prim.c"
        prim_obj = output / f"fx{level}-pvr-prim.o"
        kos_flags = [prefix + "gcc", *profile.target_flags(kos), "-I" + str(directory / "kos-overlay"),
                     "-std=gnu11", "-ffp-contract=off", "-fstack-usage"]
        builder.run([*kos_flags, "-c", prim, "-o", prim_obj], label=f"fx{level}-pvr-prim")
        for enabled in (0, 1):
            name = f"fx{level}-q{enabled}"
            flags, arm_profile = profile.expand_existing(directory, compiler, sdk, receipt,
                [f"ESP_SETUP_LEAN={enabled}"], prefix=name)
            obj, elf = output / (name + ".o"), output / (name + ".elf")
            builder.run([*flags["native_ui"], "-fstack-usage", "-c", fixture, "-o", obj], label=name)
            builder.run([compiler, "-m4-single", "-ml", "-nostartfiles", "-Wl,--gc-sections",
                "-Wl,-T," + str(linker), "-Wl,-e,_fixture_keep_packet", "-Wl,-u,_fixture_layout",
                obj, texture_obj, prim_obj, fail_obj, "-o", elf], label=name + "-link")
            (output / (name + ".disassembly.txt")).write_bytes(builder.run(
                [prefix + "objdump", "-d", "-C", elf], label=name + "-disassembly"))
            arms[name] = dict(elf=str(elf), elf_sha256=profile.sha(elf), object_sha256=profile.sha(obj),
                sections=profile.sections(obj), stack_usage=profile.stack_usage(obj.with_suffix(".su")),
                profile=arm_profile["native_ui"])
            cut_obj,cut_elf=output/(name+"-cut.o"),output/(name+"-cut.elf")
            builder.run([*flags["esp_sub"],"-fstack-usage","-c",cut_fixture,"-o",cut_obj],label=name+"-cut")
            builder.run([compiler,"-m4-single","-ml","-nostartfiles","-Wl,--gc-sections",
                "-Wl,-T,"+str(linker),"-Wl,-e,_fixture_setup","-Wl,-u,_fixture_cut_layout",
                "-Wl,-u,_fixture_early","-Wl,-u,_fixture_prime",cut_obj,edge_obj,"-o",cut_elf],label=name+"-cut-link")
            (output/(name+"-cut.disassembly.txt")).write_bytes(builder.run(
                [prefix+"objdump","-d","-C",cut_elf],label=name+"-cut-disassembly"))
            arms[name]["cut"]=dict(elf=str(cut_elf),elf_sha256=profile.sha(cut_elf),object_sha256=profile.sha(cut_obj),
                stack_usage=profile.stack_usage(cut_obj.with_suffix(".su")),profile=arm_profile["esp_sub"])
            print("BUILT", name, flush=True)
        profiles[f"fx{level}"]["texture_methods"] = texture_profile
        profiles[f"fx{level}"]["kos_helpers"] = dict(source=str(prim), sha256=profile.sha(prim), flags=kos_flags,
            scope="Pinned unchanged KOS context/header compiler; standalone CPU flags, not a linked release KOS library")
    inputs = [native, texture, DC / "room/texture_package.hpp", HERE / "packet_fixture.cpp.in", HERE/"cut_fixture.cpp.in", Path(__file__),
              HERE / "build_profile.py", DC / "game/effects30.mk", ROOT / "src/game/esp_sub.cpp"]
    result = dict(status="PASS", scope=__doc__, arms=arms, profiles=profiles,
        source_sha256={str(path.relative_to(ROOT)):profile.sha(path) for path in inputs},
        extraction={signature:hashlib.sha256(body.encode()).hexdigest() for signature,body in zip(signatures,bodies)},
        setup_phase_sha256=hashlib.sha256(setup_phase.encode()).hexdigest(),
        compiler_version=builder.run([compiler,"--version"], label="compiler").decode().splitlines()[0],
        compiler_sha256=profile.sha(compiler))
    (output / "target-build.json").write_text(json.dumps(result,indent=2)+"\n")
    return result


class Machine(target_machine.Machine):
    def word(self, address, size=4):
        return int.from_bytes(self.bytes_at(address, size), "little")

    def put(self, address, value, size=4):
        self.map(address, int(value).to_bytes(size, "little"))

    def step(self, pc, delay=False):
        if pc in getattr(self,"hooks",{}):
            name=self.hooks[pc]
            self.edge_calls.append(name)
            if name=="re4dc_zam_MTXMultVec":
                # An explicit, unpriced return value from the unchanged math
                # edge. It changes no control flow after this call.
                self.map(self.reg[6],struct.pack("<3f",10.,20.,-100.))
        # MOVCA.L allocates a dirty line and stores R0. Only the architectural
        # four-byte store is observed; no line fill or allocation time is claimed.
        opcode = self.fetch(pc)
        # GCC converts unsigned image dimensions through a temporary double.
        # Fixtures use legal positive texture dimensions, so only the exact
        # signed-int -> double -> single conversion sequence is admitted.
        if opcode & 0xf0ff == 0xf02d and self.fpscr & (1 << 19):
            n = (opcode >> 8) & 15
            assert not n & 1 and self.fpscr & 3 == 0 and 0 <= self.fpul < 0x80000000
            bits = struct.unpack("<Q", struct.pack("<d", float(self.fpul)))[0]
            self.sf(n, bits >> 32); self.sf(n+1, bits & 0xffffffff)
            self.instruction_pcs.append(pc); self.steps += 1
            return pc+2
        if opcode & 0xf0ff == 0xf0bd:
            n = (opcode >> 8) & 15
            assert not n & 1 and self.fpscr & (1 << 19) and self.fpscr & 3 == 0
            value = struct.unpack("<d", struct.pack("<Q", (self.f(n) << 32) | self.f(n+1)))[0]
            self.fpul = struct.unpack("<I", struct.pack("<f", value))[0]
            self.instruction_pcs.append(pc); self.steps += 1
            return pc+2
        if opcode & 0xf0ff == 0x4005:  # ROTR used by the unchanged KOS ctz helper.
            self.instruction_pcs.append(pc)
            self.steps += 1
            n = (opcode >> 8) & 15
            old = self.reg[n]
            self.t = old & 1
            self.reg[n] = ((old >> 1) | ((old & 1) << 31)) & 0xffffffff
            return pc+2
        if opcode & 0xf0ff == 0x00c3:
            previous = self.executing_pc, self.executing_ordinal
            self.executing_pc, self.executing_ordinal = pc, len(self.instruction_pcs)
            self.instruction_pcs.append(pc)
            self.steps += 1
            at = self.reg[(opcode >> 8) & 15]
            try:
                self.write(at, self.reg[0], 4)
            finally:
                self.executing_pc, self.executing_ordinal = previous
            return pc+2
        return super().step(pc, delay)


LAYOUT = ("version", "sprite_size", "entry_size", "node_size", "sprite", "entry", "metadata",
          "pointers", "packet", "nodes", "data_off", "header_off", "pointers_off", "color_off", "src_off",
          "dst_off", "screen_off", "x_off", "y_off", "z_off", "u_off", "v_off", "image_off", "width_off",
          "height_off", "lighting_off", "header_key", "header_key_size", "header_cache", "node_stride", "packet_offset")


def load(path):
    segments,symbols=target_machine.scalar.load_elf(path)
    machine=Machine()
    for at,data,_ in segments:machine.map(at,data)
    layout_at=symbols["_fixture_layout"][0]
    layout=dict(zip(LAYOUT,[machine.word(layout_at+4*i) for i in range(len(LAYOUT))]))
    assert layout["version"]==1
    entries=[(name,address) for name,(address,_,_) in symbols.items() if "fx_packet" in name]
    assert len(entries)==1,entries
    return machine,symbols,layout,entries[0][1]


def prepare(machine,layout):
    at=layout["entry"]
    for off,value in (("data_off",layout["metadata"]),("header_off",layout["metadata"]),
                      ("pointers_off",layout["pointers"])):
        machine.put(at+layout[off],value)
    header=bytearray(48+96)
    struct.pack_into("<2I",header,20,1,48)
    struct.pack_into("<8I",header,48+64,64,64,2,0,8192,0,1,0)
    machine.map(layout["metadata"],header)
    machine.put(layout["pointers"],0xa4000000)
    at=layout["sprite"]
    machine.map(at,bytes(layout["sprite_size"]))
    machine.put(at+layout["image_off"]+layout["width_off"],64)
    machine.put(at+layout["image_off"]+layout["height_off"],64)
    machine.put(at+layout["color_off"],0x8f6a3c18)
    machine.put(at+layout["src_off"],4,1)
    machine.put(at+layout["dst_off"],5,1)
    for field,values in (("x_off",(80.,120.,120.,80.)),("y_off",(90.,90.,130.,130.)),
                         ("z_off",(.1,.1,.1,.1)),("u_off",(0.,1.,1.,0.)),("v_off",(0.,0.,1.,1.))):
        machine.map(at+layout[field],struct.pack("<4f",*values))
    for n in range(3):machine.put(layout["nodes"]+n*layout["node_stride"]+layout["lighting_off"],1)


def call(machine,layout,entry,owner,previous):
    machine.reg[5]=layout["entry"]
    machine.reg[6]=owner+layout["packet_offset"] if owner else layout["packet"]
    machine.reg[7]=previous if owner else 0
    machine.execute(entry,layout["sprite"])


def observed(events,prefetches=()):
    row=summarize(events,prefetches)
    cached=[e for e in events if region(e[3])=="cached"]
    line_visits=sum(len({(address&0x1fffffff)>>5 for address in range(e[3],e[3]+e[4])}) for e in cached)
    row["cached"]["demand_line_visits"]=line_visits
    row["cached"]["repeated_demand_line_visits"]=line_visits-row["cached"]["unique_data_lines"]
    return row


def packet_regions(machine,layout):
    groups=dict(packet=(layout["packet"],96),sprite=(layout["sprite"],layout["sprite_size"]),
        nodes=(layout["nodes"],3*layout["node_stride"]),
        header_key=(layout["header_key"],layout["header_key_size"]),header_cache=(layout["header_cache"],32),
        package=(layout["entry"],layout["entry_size"]),metadata=(layout["metadata"],144),
        texture_pointers=(layout["pointers"],4),stack=(machine.initial_regs[15]-1024,1028))
    remaining=list(machine.memory_events);result={}
    for name,(address,size) in groups.items():
        selected=[e for e in remaining if address<=e[3] and e[3]+e[4]<=address+size]
        remaining=[e for e in remaining if e not in selected]
        result[name]=observed(selected)["cached"]
    result["other_including_literals"]=observed(remaining)["cached"]
    return result


CUT_LAYOUT=("version","effect_size","global_size","effect","global","parent","animation","pG",
    "frame_off","camera_off","owner_off","id_off","tex_off","parts_off","tool_off","size_x_off",
    "size_y_off","mul_off","position_off","angle_off","matrix_off","parent_off","essential","torch",
    "parent_matrix_off","parent_size","classes","trim_frame","ess_frame")


def cut_load(path):
    program,symbols=target_machine.scalar.load_elf(path);machine=Machine()
    for at,data,_ in program:machine.map(at,data)
    at=symbols["_fixture_cut_layout"][0]
    layout=dict(zip(CUT_LAYOUT,[machine.word(at+4*i) for i in range(len(CUT_LAYOUT))]))
    assert layout["version"]==1
    edges=("low_RotMatrix","re4dc_zam_MTXRotRad","re4dc_zam_MTXConcat","re4dc_zam_MTXMultVec",
           "EspGetCameraPan","fixture_emit_edge")
    machine.hooks={symbols["_"+name][0]:name for name in edges if "_"+name in symbols}
    machine.edge_calls=[]
    return machine,symbols,layout


def cut_prepare(machine,symbols,layout,level,scenario):
    machine.put(layout["pG"],layout["global"])
    machine.put(layout["global"]+layout["frame_off"],7)
    machine.put(layout["essential"],int(level==3),1)
    machine.put(layout["torch"],0)
    effect=layout["effect"]
    machine.map(effect,bytes(layout["effect_size"]))
    machine.put(effect+layout["parent_off"],layout["parent"])
    machine.put(effect+layout["owner_off"],0xd0 if scenario!="keep" else 0x10,1)
    machine.put(effect+layout["tex_off"],0x5f if scenario!="keep" else 0x23,1)
    machine.put(effect+layout["parts_off"],255,1)
    for field,value in (("size_x_off",50.),("size_y_off",70.),("mul_off",1.)):
        machine.map(effect+layout[field],struct.pack("<f",value))
    machine.map(effect+layout["position_off"],struct.pack("<3f",10.,20.,-100.))
    matrix=struct.pack("<12f",1,0,0,0,0,1,0,0,0,0,1,0)
    machine.map(effect+layout["matrix_off"],matrix)
    machine.map(layout["global"]+layout["camera_off"],matrix)
    machine.map(layout["parent"]+layout["parent_matrix_off"],matrix)
    machine.map(layout["animation"],struct.pack("<4H",64,64,0,0))
    machine.execute(symbols["_fixture_prime"][0])
    if scenario=="unprimed":
        for field in ("trim_frame","ess_frame"):
            if layout[field]:machine.put(layout[field],0xffffffff)
    machine.edge_calls=[]


def measure_cut(output,arms,host_cc):
    rows=[]
    for arm,info in arms.items():
        if "cut" not in info:continue
        path=Path(info["cut"]["elf"]);assert profile.sha(path)==info["cut"]["elf_sha256"]
        model=pipeline_cost.Model(output/("cut-model-"+arm),path,host_cc)
        for scenario in ("cut","keep","unprimed"):
            for phase in ("early","setup"):
                machine,symbols,layout=cut_load(path)
                level=int(arm[2]);cut_prepare(machine,symbols,layout,level,scenario)
                machine.reg[5]=0 if phase=="early" else layout["animation"]
                machine.minimum_sp=machine.reg[15];machine.observe_start()
                machine.execute(symbols["_fixture_"+phase][0],layout["effect"])
                machine.observe_stop()
                trace=SimpleNamespace(instruction_pcs=list(machine.instruction_pcs),steps=machine.steps,read=machine.read)
                rejected=level==3 and arm.endswith("q1") and scenario=="cut"
                if phase=="early":assert machine.reg[0]==int(rejected)
                else:assert (not machine.edge_calls)==rejected,(arm,scenario,machine.edge_calls)
                row=dict(arm=arm,scenario=scenario,phase=phase,rejected_early=rejected,
                    instructions=machine.steps,traffic=observed(machine.memory_events,machine.prefetch_events),
                    effect_traffic=observed([e for e in machine.memory_events if layout["effect"]<=e[3]<layout["effect"]+layout["effect_size"]]),
                    peak_stack_bytes=machine.initial_regs[15]-machine.minimum_sp,
                    matrix_and_emit_edges=machine.edge_calls,pipeline=old_run.price(model,scenario+"-"+phase,trace),
                    symbol_instructions=pipeline_cost.symbol_costs(trace,symbols))
                rows.append(row)
                print("CUT",arm,scenario,phase,row["pipeline"]["model_cycles"],flush=True)
    return rows


def run(args):
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=False)
    receipt=json.loads(args.build.read_text())
    rows=[]
    for name,arm in receipt["arms"].items():
        path=Path(arm["elf"]);assert profile.sha(path)==arm["elf_sha256"]
        model=pipeline_cost.Model(output/("model-"+name),path,args.host_cc)
        for scenario in ("key-miss","identical-hit","argb-miss","owner-break","head-sentinel","direct"):
            machine,symbols,layout,entry=load(path);prepare(machine,layout)
            node=layout["nodes"];stride=layout["node_stride"]
            prior_header=None
            if scenario!="key-miss":
                call(machine,layout,entry,node,node)
                prior_header=machine.bytes_at(node+layout["packet_offset"],32)
            if scenario=="argb-miss":machine.put(layout["sprite"]+layout["color_off"],0x8f6a3c19)
            previous=node+(2*stride if scenario=="owner-break" else stride if scenario=="head-sentinel" else 0)
            owner=0 if scenario=="direct" else node+stride
            before=bytes([0x5a])*96;machine.map(layout["packet"],before)
            machine.minimum_sp=machine.reg[15];machine.observe_start()
            call(machine,layout,entry,owner,previous)
            machine.observe_stop()
            trace=SimpleNamespace(instruction_pcs=list(machine.instruction_pcs),steps=machine.steps,read=machine.read)
            packet=machine.bytes_at(layout["packet"],96)
            body_only=name.endswith("q1") and scenario=="identical-hit"
            assert (packet[:32]==before[:32])==body_only,(name,scenario,"header-store result")
            effective=prior_header+packet[32:] if body_only else packet
            row=dict(arm=name,scenario=scenario,instructions=machine.steps,
                peak_stack_bytes=machine.initial_regs[15]-machine.minimum_sp,
                traffic=observed(machine.memory_events,machine.prefetch_events),
                packet_traffic=observed([e for e in machine.memory_events if layout["packet"]<=e[3]<layout["packet"]+96]),
                storage_regions=packet_regions(machine,layout),
                packet_sha256=hashlib.sha256(packet).hexdigest(),body_sha256=hashlib.sha256(packet[32:]).hexdigest(),
                effective_packet_sha256=hashlib.sha256(effective).hexdigest(),
                body_only=body_only,packet_bytes_to_send=64 if body_only else 96,
                pipeline=old_run.price(model,scenario,trace),
                symbol_instructions=pipeline_cost.symbol_costs(trace,symbols))
            rows.append(row)
            print("MEASURED",name,scenario,row["pipeline"]["model_cycles"],row["traffic"]["cached"],flush=True)
    for scenario in {row["scenario"] for row in rows}:
        group=[row for row in rows if row["scenario"]==scenario]
        assert len({row["effective_packet_sha256"] for row in group})==1,(scenario,"effective TA packet changed")
        assert len({row["body_sha256"] for row in group})==1,(scenario,"sprite body changed")
        if scenario!="identical-hit":assert len({row["packet_sha256"] for row in group})==1,(scenario,"full packet changed")
    cut_rows=measure_cut(output,receipt["arms"],args.host_cc)
    result=dict(status="PASS",scope=__doc__,rows=rows,cut_rows=cut_rows,build_sha256=profile.sha(args.build),build=str(args.build),
        model_source_sha256=profile.sha(pipeline_cost.MODEL),memory_observer_controls=target_machine.memory_controls())
    (output/"target-results.json").write_text(json.dumps(result,indent=2)+"\n")
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest="command",required=True)
    b=sub.add_parser("build")
    for name in ("output","sh4-cxx","kos-root","sdk-root"):b.add_argument("--"+name,type=Path,required=True)
    r=sub.add_parser("run")
    r.add_argument("--output",type=Path,required=True);r.add_argument("--build",type=Path,required=True)
    r.add_argument("--host-cc",default="gcc")
    args=parser.parse_args()
    (build if args.command=="build" else run)(args)
