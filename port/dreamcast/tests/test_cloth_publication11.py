"""CF11-PUB-01: actual source producer, prepared bands and shared FIFO drain/reset.

Synthetic host evidence only. The reader is the game's single-context scalar
API/external sequence protocol, not a concurrently executing C++ thread.
"""
from pathlib import Path
import importlib.util
import os
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
INC = ROOT / "game/platform/include"
BASE = "020a4c38d061860612020764bb1e8ad008d66092"


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tests" / (name + ".py"))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


TILES = module("test_cloth_tiles11")
MATERIAL = module("test_cloth_material11")
OWNER = module("test_plan_owner_scoped")


def native_hooks(source):
    reset = OWNER.function(source, "void reset_deferred(){")
    drain = OWNER.function(source, "        if(deferred_first->lighting==kEffectQuad21Tag){")
    abort_start = source.index("    completed_frame.aborted=stream_aborted;")
    abort_end = source.index("\n#endif", abort_start)
    abort = source[abort_start:abort_end]
    if "#if defined(RE4DC_CLOTH_PUBLICATION11)" in abort:
        abort += "\n#endif"
    # These bodies are extracted, not a second implementation of the hooks.
    return r'''
void* deferred_light_sets=nullptr;void* deferred_basis=nullptr;void* deferred_lights=nullptr;
#define AVD_EVENT(...) ((void)0)
''' + reset + r'''
void actual_drain(){while(deferred_first && !stream_aborted){
''' + drain + r'''
#line 10000 "cf11-synthetic-drain"
 assert(false);}
 reset_deferred();}
void actual_frame_completion(){struct {bool aborted;} completed_frame;
''' + abort + "\n}\n"


def fixture(source=None, native=None):
    stub, code = TILES.actual_source_fixture(source)
    code = code.split("int main(){", 1)[0]
    code = '#if RE4DC_CLOTH_PUBLICATION11\n#include "cloth_publication11.inc"\n#endif\n' + code
    code = code.replace("Entry* resolve(", "void(*source_hook)()=nullptr;\nEntry* resolve(")
    code = code.replace("++opens;return missing?", "++opens;if(source_hook)source_hook();return missing?")
    if native is None:
        native = (ROOT / "game/platform/native_ui.cpp").read_text()
    code += native_hooks(native)
    return stub, code


class ClothPublication11(unittest.TestCase):
    def build(self, stub, code, *, sanitize=False, observation=True, includes=None, object_only=False):
        with tempfile.TemporaryDirectory(prefix="re4dc-cloth-publication11-") as td:
            tmp = Path(td)
            (tmp / "dc").mkdir()
            (tmp / "dc/pvr.h").write_text(stub)
            cpp, exe = tmp / "fixture.cpp", tmp / "check"
            cpp.write_text(code)
            args = ["g++", "-std=c++20", "-O2", "-g0", "-w", "-fno-pie", "-no-pie", "-fstack-usage",
                    "-ffile-prefix-map=" + str(tmp) + "=/cloth-pub11-fixture",
                    "-DRE4DC_FX_STRIP21=1", "-DRE4DC_CLOTH_NATIVE=1", "-DRE4DC_NATIVE_DRAW_OUTCOMES=1",
                    "-DRE4DC_CLOTH_SHEET11=1", "-DRE4DC_CLOTH_TILES11=1", "-DRE4DC_PS2_UPLOAD_INCARNATION=1",
                    "-DRE4DC_UI_HANDLES=1", "-DRE4DC_TA_DIRECT=1", "-DRE4DC_EFFECT_SPRITE_MAX=256",
                    "-I" + str(tmp), "-I" + str(ROOT / "room")]
            if observation is not None:
                args.append("-DRE4DC_CLOTH_PUBLICATION11=" + str(int(observation)))
            args += ["-I" + str(p) for p in (includes or [INC])]
            if sanitize:
                args += ["-fsanitize=address,undefined", "-fno-omit-frame-pointer"]
            if object_only:
                pp = subprocess.run([*args, "-E", "-P", str(cpp)], capture_output=True, text=True)
                self.assertEqual(pp.returncode, 0, pp.stderr)
                run = subprocess.run([*args, "-c", str(cpp), "-o", str(exe)], capture_output=True, text=True)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.last_stack = "\n".join(path.read_text() for path in tmp.glob("*.su"))
                return pp.stdout, exe.read_bytes()
            run = subprocess.run([*args, str(cpp), str(ROOT / "room/pvr_geometry.cpp"), "-o", str(exe)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            run = subprocess.run([str(exe)], capture_output=True, text=True, env=dict(os.environ, ASAN_OPTIONS="detect_leaks=0"))
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)

    def test_actual_producer_drain_abort_lifetime_overflow_and_snapshots(self):
        stub, code = fixture()
        code += r'''
using Receipt=re4dc::cloth_pub11::Receipt;
auto& observer=re4dc_cloth_publication11;
Receipt read(unsigned id=0){Receipt r{};assert(re4dc_cloth_snapshot11(id?id:observer.newest,0,&r));return r;}
void start(unsigned width,unsigned rows,std::vector<Vec>& grid){
 reset_deferred();fresh();source_hook=nullptr;set_sheet(width,rows,grid);
}
void reuse(){++cloth11_incarnation[0];source_hook=nullptr;}
void native_frame_change(){++frame;source_hook=nullptr;}
void generation_change(){re4dc::cloth_pub11::grid_write(0);source_hook=nullptr;}
void fail_send(){stream_aborted=true;after_send_hook=nullptr;}
int main(){std::vector<Vec> grid;
 // Two distinct pool owners share exactly one prepared texture/cache slot.
 start(2,3,grid);source_draws_finished=false;ClothWk[1]=ClothWk[0];
 auto a=re4dc_cloth_native(&ClothWk[0],lights,&pos,1);const unsigned first=observer.newest;
 auto b=re4dc_cloth_native(&ClothWk[1],lights,&pos,1);const unsigned second=observer.newest;
 auto r0=read(first),r1=read(second);
 assert(a.queued==2&&b.queued==2&&r0.slot==0&&r1.slot==1&&r0.id!=r1.id);
 assert(r0.texture_slot==r1.texture_slot&&r0.upload_incarnation==r1.upload_incarnation);
 assert(r0.prepared&&r0.accepted==2&&!r0.direct&&!r0.drained&&!r0.discarded);
 assert(r0.incarnation==cloth11_incarnation[0]&&r0.source_frame==pG->Frame_cnt&&r0.native_frame==frame);
 assert(r0.primary_slot==~0U&&!r0.primary_upload&&!r0.material&&r0.finished);
 actual_drain();r0=read(first);r1=read(second);
 assert(r0.drained==2&&r1.drained==2&&!r0.discarded&&!r1.discarded&&packet_log.size()==4);
 assert(r0.last_drain_frame==frame&&r1.last_drain_frame==frame&&r0.last_discard_frame==~0U);
 // Stream sends stay observable even if a later frame abort rejects the image.
 stream_aborted=true;actual_frame_completion();assert(read(first).flags&re4dc::cloth_pub11::FrameAborted);
 assert(read(first).drained==2); // no claim of presentation, no rewriting sends
 // Texture I/O may replace a source pool cell before prepared ownership binds.
 start(2,2,grid);source_hook=reuse;
 auto result=re4dc_cloth_native(&ClothWk[0],lights,&pos,1);auto r=read();
 assert(result.outcome==Outcome::PartialAbort&&!r.prepared&&!r.direct&&!r.accepted);
 assert(r.end_incarnation==r.incarnation+1&&(r.flags&re4dc::cloth_pub11::SourceChanged));
 start(2,2,grid);retire_at_transform=1;
 result=re4dc_cloth_native(&ClothWk[0],lights,&pos,1);r=read();
 assert(result.outcome==Outcome::PartialAbort&&r.prepared&&!r.direct&&!r.accepted&&r.end_incarnation!=r.incarnation);
 // Source and native frame numbers are separate clocks, never texture identity.
 start(2,2,grid);++pG->Frame_cnt;result=re4dc_cloth_native(&ClothWk[0],lights,&pos,1);r=read();
 assert(result.submitted==1&&r.source_frame==r.native_frame+1&&(r.flags&re4dc::cloth_pub11::FrameMismatch));
 start(2,2,grid);source_hook=native_frame_change;result=re4dc_cloth_native(&ClothWk[0],lights,&pos,1);r=read();
 assert(result.submitted==1&&r.end_native_frame==r.native_frame+1&&(r.flags&re4dc::cloth_pub11::FrameMismatch));
 // A source grid generation change is reported without changing admission.
 start(2,2,grid);source_hook=generation_change;result=re4dc_cloth_native(&ClothWk[0],lights,&pos,1);r=read();
 assert(result.submitted==1&&r.end_grid_generation==r.grid_generation+1&&(r.flags&re4dc::cloth_pub11::SourceChanged));
 start(2,2,grid);missing=true;result=re4dc_cloth_native(&ClothWk[0],lights,&pos,1);r=read();
 assert(result.outcome==Outcome::Refused&&r.outcome==unsigned(Outcome::Refused)&&!r.prepared&&!r.accepted&&!r.direct);
 start(2,2,grid);source_draws_finished=false;deferred_top=8192;spill_available=false;
 result=re4dc_cloth_native(&ClothWk[0],lights,&pos,1);r=read();
 assert(result.outcome==Outcome::Refused&&r.prepared&&!r.accepted&&!r.direct);
 // Partial publication retains the old source receipt and exact admitted prefix.
 start(2,3,grid);after_send_hook=retire_after_first;
 result=re4dc_cloth_native(&ClothWk[0],lights,&pos,1);r=read();
 assert(result.outcome==Outcome::PartialAbort&&r.submitted==1&&r.direct==1&&!r.accepted);
 assert(r.end_incarnation!=r.incarnation&&(r.flags&re4dc::cloth_pub11::SourceChanged));
 // Queue acceptance is distinct from queue-reset discard and aborting drain.
 start(2,2,grid);source_draws_finished=false;
 result=re4dc_cloth_native(&ClothWk[0],lights,&pos,1);unsigned id=observer.newest;
 assert(read(id).accepted==1&&!read(id).drained);stream_aborted=true;reset_deferred();r=read(id);
 assert(r.queued==1&&r.accepted==1&&!r.drained&&r.discarded==1&&(r.flags&re4dc::cloth_pub11::FrameAborted));
 assert(r.last_discard_frame==frame&&r.last_drain_frame==~0U);
 start(2,3,grid);source_draws_finished=false;result=re4dc_cloth_native(&ClothWk[0],lights,&pos,1);id=observer.newest;
 after_send_hook=fail_send;actual_drain();r=read(id);
 assert(r.accepted==2&&r.send_aborted==1&&r.discarded==1&&!r.drained&&(r.flags&re4dc::cloth_pub11::FrameAborted));
 start(2,2,grid);source_draws_finished=false;result=re4dc_cloth_native(&ClothWk[0],lights,&pos,1);id=observer.newest;
 ++frame;actual_drain();r=read(id);assert(r.drained==1&&(r.flags&re4dc::cloth_pub11::FrameMismatch)&&r.last_drain_frame==frame);
 // Ring overwrite must not attribute an old node to the new draw using its row.
 start(2,2,grid);source_draws_finished=false;
 for(unsigned n=0;n<17;++n)re4dc_cloth_native(&ClothWk[0],lights,&pos,1);
 const unsigned newest=observer.newest,oldest=newest-16,stale_before=observer.stale;
 Receipt unchanged{};unchanged.id=123;assert(!re4dc_cloth_snapshot11(oldest,0,&unchanged)&&unchanged.id==123);
 assert(observer.overwritten&&observer.lost_pending);actual_drain();assert(observer.stale==stale_before+1);
 assert(read(newest).accepted==1&&read(newest).drained==1&&!read(newest).discarded);
 // Old reader versions, odd writer snapshots, and exhausted sequences reject.
 r=read();const unsigned version=observer.sequence;
 observer.abort(frame);assert(!re4dc_cloth_snapshot11(newest,version,&unchanged)&&unchanged.id==123);
 const unsigned even=observer.sequence;observer.sequence=even+1;
 assert(!re4dc_cloth_snapshot11(newest,0,&unchanged));observer.sequence=even;
 // Receipt ID and sequence never wrap/revive stale nodes; failure is diagnostic.
 start(2,2,grid);observer.newest=~0U;
 const unsigned packets=send_calls;result=re4dc_cloth_native(&ClothWk[0],lights,&pos,1);
 assert(result.submitted==1&&send_calls==packets+1&&observer.exhausted);
 observer.sequence=~0U-1U;result=re4dc_cloth_native(&ClothWk[0],lights,&pos,1);
 assert(result.submitted==1&&observer.sequence==~0U&&!re4dc_cloth_snapshot11(newest,0,&unchanged));
}
'''
        for sanitize in (False, True):
            with self.subTest(sanitize=sanitize):
                self.build(stub, code, sanitize=sanitize)

    def test_actual_grid_writers_and_nonwrapping_generation(self):
        source = (REPO / "src/game/cloth.cpp").read_text()
        move = OWNER.function(source, "void Cloth::move()")
        pose = OWNER.function(source, "void Cloth::SetPosAng(")
        stub, code = fixture()
        code = code.replace("Vec* pNor;void* m_pMem;unsigned be_flag;", "Vec* pNor;void* m_pMem;unsigned be_flag;Vec* pSpd;unsigned x70;void move();void SetPosAng(Vec,Vec);")
        code += r'''
float T_PARAM=.06f;
void PSVECScale(const Vec* a,Vec* b,float t){*b={a->x*t,a->y*t,a->z*t};}
void PSVECAdd(const Vec* a,const Vec* b,Vec* c){*c={a->x+b->x,a->y+b->y,a->z+b->z};}
void RotMatrix(Mtx m,Vec*){PSMTXScale(m,1,1,1);}void TransMatrix(Mtx,Vec*){}
''' + move + "\n" + pose + r'''
int main(){fresh();std::vector<Vec> grid;set_sheet(2,2,grid);Vec speeds[4]{};
 auto& c=ClothWk[0];c.pSpd=speeds;c.x70=0;
 const auto initial=grid;const unsigned g=re4dc::cloth_pub11::grid_generation[0];
 c.move();assert(re4dc::cloth_pub11::grid_generation[0]==g+1);
 assert(!std::memcmp(initial.data(),grid.data(),grid.size()*sizeof(Vec)));
 c.SetPosAng({},{});assert(re4dc::cloth_pub11::grid_generation[0]==g+2);
 re4dc::cloth_pub11::grid_generation[0]=~0U;c.move();c.move();
 assert(!re4dc::cloth_pub11::grid_generation[0]);
 re4dc_cloth_native(&c,lights,&pos,1);Receipt r{};
 assert(re4dc_cloth_snapshot11(re4dc_cloth_publication11.newest,0,&r));
 assert(!r.grid_generation&&(r.flags&re4dc::cloth_pub11::GenerationUnknown));
}
'''.replace("Receipt r{}", "re4dc::cloth_pub11::Receipt r{}")
        self.build(stub, code, sanitize=True)

    def test_material_fixture_and_primary_secondary_identity(self):
        stub, code = MATERIAL.fixture()
        code = '#include "cloth_publication11.inc"\n' + code
        code = code.replace('assert(!munmap(mapping,4096));', r'''
 re4dc::cloth_pub11::Receipt receipt{};
 assert(re4dc_cloth_snapshot11(re4dc_cloth_publication11.newest,0,&receipt));
 assert(receipt.material==1&&receipt.prepared&&receipt.texture_slot==1&&receipt.primary_slot==0);
 assert(receipt.upload_incarnation&&receipt.primary_upload&&receipt.accepted==1&&!receipt.drained);
 assert(!munmap(mapping,4096));''')
        MATERIAL.ClothMaterial11().build_run(stub, code, sanitize=True, extra=("-DRE4DC_CLOTH_PUBLICATION11=1",))

    def test_default_off_actual_source_native_and_queue_hook_identity(self):
        source = subprocess.check_output(["git", "show", BASE + ":src/game/cloth.cpp"], cwd=REPO, text=True)
        native = subprocess.check_output(["git", "show", BASE + ":port/dreamcast/game/platform/native_ui.cpp"], cwd=REPO, text=True)
        with tempfile.TemporaryDirectory(prefix="cloth-pub11-baseline-") as td:
            old_inc = Path(td)
            for name in ("native_cloth_sheet11.hpp", "native_cloth_sheet11.inc", "native_effect_strip21.inc"):
                (old_inc / name).write_bytes(subprocess.check_output(["git", "show", BASE + ":port/dreamcast/game/platform/include/" + name], cwd=REPO))
            controls = []
            for observation in (None, False):
                for old in (True, False):
                    stub, code = fixture(source if old else None, native if old else None)
                    code += r'''
extern "C" re4dc::NativeDrawResult force_adapter(Cloth* c,cLight** l,Vec* p,float size){
 return re4dc_cloth_native(c,l,p,size);}
'''
                    pp, obj = self.build(stub, code, observation=observation, includes=[old_inc, INC] if old else [INC], object_only=True)
                    tokens = re.findall(r'"(?:\\.|[^"\\])*"|\w+|[^\s]', pp)
                    controls.append((tokens, obj))
            for i, control in enumerate(controls):
                self.assertEqual(control[0], controls[0][0], "preprocessor arm " + str(i))
                self.assertEqual(control[1], controls[0][1], "object arm " + str(i))

    def test_reserved_effect_word_and_non_cloth_packets(self):
        # Audit every production publisher of this exact tag. The model view's
        # actual change masks are never borrowed: only tag-specific ignored data.
        publishers = []
        for path in (ROOT / "game/platform").rglob("*"):
            if path.suffix in (".inc", ".cpp") and "node->lighting=kEffectQuad21Tag" in path.read_text():
                publishers.append(path.name)
                text = path.read_text()
                if path.name != "native_cloth_sheet11.inc":
                    self.assertEqual(set(re.findall(r"node->changed\[(\d+)\]", text)), {"0"})
                    self.assertEqual(text.count("node->lighting=kEffectQuad21Tag"), text.count("auto* node=new(storage+*top) DeferredPart{};") + text.count("auto* node=new(storage+*tp) DeferredPart{};"))
        self.assertEqual(sorted(publishers), ["native_cloth_sheet11.inc", "native_effect_strip21.inc", "native_flashlight_pool.inc"])
        stub, code = fixture()
        code += r'''
int main(){fresh();source_draws_finished=false;const unsigned newest=re4dc_cloth_publication11.newest;
 const unsigned stale=re4dc_cloth_publication11.stale;auto q=quad();
 assert(re4dc_effect_quad_result(&q).queued==1);
 float positions[]={-1,1,-10,1,1,-10,-1,-1,-10,1,-1,-10};
 Re4dcEffectMesh21 m{};m.image=q.image;m.cols=m.rows=2;m.positions=positions;m.v_step=1;
 m.color=q.color;m.src=q.src;m.dst=q.dst;
 std::memcpy(m.projection,q.projection,sizeof m.projection);std::memcpy(m.viewport,q.viewport,sizeof m.viewport);
 assert(re4dc_effect_mesh21_result(&m).queued==1);
 for(auto* n=deferred_first;n;n=n->next)assert(!n->changed[1]);
 actual_drain();assert(packet_log.size()==2&&re4dc_cloth_publication11.newest==newest&&re4dc_cloth_publication11.stale==stale);
}
'''
        self.build(stub, code, sanitize=True)

    def test_bounded_host_stack_and_storage(self):
        stub, code = fixture()
        code += r'''
extern "C" re4dc::NativeDrawResult force_adapter(Cloth* c,cLight** l,Vec* p,float size){
 return re4dc_cloth_native(c,l,p,size);}
'''
        sizes, cloth_frames = [], []
        for enabled in (False, True):
            self.build(stub, code, observation=enabled, object_only=True)
            rows = [line.split("\t") for line in self.last_stack.splitlines()]
            relevant = [row for row in rows if "force_adapter(" in row[0] or "re4dc_cloth_native(" in row[0] or "lambda()" in row[0]]
            self.assertTrue(relevant, self.last_stack)
            self.assertTrue(all("static" in row[2] or "bounded" in row[2] for row in rows), self.last_stack)
            sizes.append(max(int(row[1]) for row in relevant))
            cloth_frames.append({re.search(r"re4dc_cloth_\w+", row[0]).group(): int(row[1]) for row in rows if re.search(r"re4dc_cloth_\w+", row[0])})
        print("CF11 host -O2 adapter stack OFF/ON:", sizes, "; declared diagnostic storage=1848 bytes, queue/heap delta=0")
        print("CF11 host -O2 individual cloth function stack OFF/ON:", cloth_frames)

    def test_primary_make_selector_scope_and_dependency(self):
        with tempfile.TemporaryDirectory(prefix="cloth-pub11-make-") as td:
            (Path(td) / "Makefile.rules").write_text("")
            make = ["make", "--no-print-directory", "-f", "Makefile", "-n", "KOS_BASE=" + td]
            targets = ["obj/src/game/cloth.o", "obj/platform/native_ui.o", "obj/platform/gx_stub.o", "obj/src/game/esp_sub.o"]
            deps = ["EFFECT_SPRITES=1", "FX_STRIP21=1", "CLOTH_NATIVE=1", "NATIVE_DRAW_OUTCOMES=1", "PS2_UPLOAD_INCARNATION=1", "CLOTH_SHEET11=1"]
            outputs = []
            for value in (None, "0", "1"):
                run = subprocess.run([*make, *targets, *deps, *([] if value is None else ["CLOTH_PUBLICATION11=" + value])], cwd=ROOT / "game", capture_output=True, text=True)
                self.assertEqual(run.returncode, 0, run.stderr)
                outputs.append([line for line in run.stdout.splitlines() if line.startswith("kos-c++")])
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual(len(outputs[2]), 4)
            for i, line in enumerate(outputs[2]):
                self.assertEqual(line.count("-DRE4DC_CLOTH_PUBLICATION11=1"), int(i < 2))
            for value in ("", "1 ", "0 ", "1\t", "$(subst x, ,x)1", "0 1", "%", "01", "-1", "2"):
                run = subprocess.run([*make, *targets, *deps, "CLOTH_PUBLICATION11=" + value], cwd=ROOT / "game", capture_output=True, text=True)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn("CLOTH_PUBLICATION11 must be", run.stderr)
            run = subprocess.run([*make, *targets, *deps, "CLOTH_PUBLICATION11=1", "CLOTH_SHEET11=0"], cwd=ROOT / "game", capture_output=True, text=True)
            self.assertNotEqual(run.returncode, 0)
            self.assertIn("CLOTH_PUBLICATION11 needs", run.stderr)


if __name__ == "__main__":
    unittest.main()
