"""EF11 wide tiles: compile the production cloth adapter and native band consumer."""
from pathlib import Path
import importlib.util
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
INC = ROOT / "game/platform/include"
BASE = "39ed524a3b0a4727148aaa5a45eaaea4d211cede"
SPEC = importlib.util.spec_from_file_location("cloth_previous", ROOT / "tests/test_native_cloth_sheet11.py")
PREVIOUS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREVIOUS)


def actual_source_fixture(source=None):
    if source is None:
        source = (REPO / "src/game/cloth.cpp").read_text()
    start = source.index("#if defined(RE4DC_NATIVE_DRAW_OUTCOMES)", source.index("static int re4dc_cloth_visible"))
    end = source.index("\n#endif\n\n// clothTrans builds", start)
    adapter = source[start:end]
    epoch_start = source.index("#if defined(RE4DC_CLOTH_SHEET11)", source.index("Cloth ClothWk[8]"))
    epoch_end = source.index("\n#endif", epoch_start) + len("\n#endif")
    epochs = source[epoch_start:epoch_end]
    stub, code = PREVIOUS.packet_harness()
    code = code.replace("void stream_send(const void* data,unsigned bytes){",
                        "std::vector<std::vector<pvr_vertex_t>> packet_log; "
                        "void(*after_send_hook)()=nullptr; unsigned send_calls=0;\n"
                        "void stream_send(const void* data,unsigned bytes){\n"
                        " ++send_calls;auto* v=(const pvr_vertex_t*)data;"
                        "packet_log.emplace_back(v,v+bytes/sizeof(pvr_vertex_t));")
    code = code.replace("sent_colors.push_back(reinterpret_cast<const pvr_vertex_t*>(data)[1].argb);}",
                        "sent_colors.push_back(reinterpret_cast<const pvr_vertex_t*>(data)[1].argb);"
                        "if(after_send_hook)after_send_hook();}")
    code += r'''
#include "native_cloth_sheet11.hpp"
using u32=unsigned;using f32=float;using Mtx=float[3][4];struct Vec{float x,y,z;};
struct Color{unsigned char r,g,b,a;};struct cLight{Color DispCol;unsigned xD;float Radius;Vec World;};
struct Env{Color AmbientScr{255,255,255,255};};struct LightManager{Env e;Env* getEnvPtr(){return &e;}} LightMgr;
struct Global{struct{Mtx v_mat;}Cam;unsigned Frame_cnt;}global_value,*pG=&global_value;
struct Cloth{void* tex;void* pTobjA;unsigned divH,divV;void* tlut;unsigned x74;Color color;float Scale;
             Mtx mat;Vec* pVer;Vec* pNor;void* m_pMem;unsigned be_flag;};
Cloth ClothWk[8];
''' + epochs + r'''
unsigned transforms=0,retire_at_transform=0;bool retired=false;
void PSMTXScale(Mtx m,float,float,float){std::memset(m,0,sizeof(Mtx));m[0][0]=m[1][1]=m[2][2]=1;}
void PSMTXConcat(const Mtx,const Mtx,Mtx out){PSMTXScale(out,1,1,1);}
void PSMTXMultVec(const Mtx,const Vec* p,Vec* out){assert(!retired);++transforms;*out=*p;
 if(transforms==retire_at_transform){++cloth11_incarnation[0];retired=true;}}
float GetDistance3(Vec*,Vec*){return 0;}
void projection(float* out){auto q=quad();std::memcpy(out,q.projection,sizeof q.projection);}
void viewport(float* out){auto q=quad();std::memcpy(out,q.viewport,sizeof q.viewport);}
#define RE4DC_GXF_GET_PROJECTION(p) projection(p)
#define RE4DC_GXF_GET_VIEWPORT(p) viewport(p)
''' + adapter + r'''
using Outcome=re4dc::NativeDrawOutcome;
unsigned tex[]={1,(64<<16)|64,14,0};cLight* lights[8]{};Vec pos{};
void fresh(){reset();packet_log.clear();send_calls=transforms=retire_at_transform=0;retired=false;after_send_hook=nullptr;
 source_draws_finished=true;stream_aborted=false;frame_ready=true;draining_parts=false;direct_open=false;
 missing=false;spill_available=true;entry.valid=true;entry.upload_incarnation=1;entry.package.value.width=64;
 compiles=opens=0;ClothWk[0].be_flag=0x31;cloth11_incarnation[0]=1;pG->Frame_cnt=frame;}
void set_sheet(unsigned width,unsigned rows,std::vector<Vec>& grid){grid.resize(width*rows);
 for(unsigned r=0;r<rows;++r)for(unsigned c=0;c<width;++c)grid[r*width+c]={float(c)*.001f,float(r),-10};
 auto& cloth=ClothWk[0];cloth={};cloth.tex=tex;cloth.divH=width;cloth.divV=rows;cloth.pVer=grid.data();
 cloth.be_flag=0x31;cloth.Scale=1;cloth.color={128,64,32,192};}
void retire_after_first(){++cloth11_incarnation[0];after_send_hook=nullptr;}
int main(){
 for(unsigned width:{2U,99U,100U,101U,255U}){
  fresh();std::vector<Vec> grid;set_sheet(width,4,grid);auto original=grid;
  const auto result=re4dc_cloth_native(&ClothWk[0],lights,&pos,1);
  const unsigned tiles=width<=100?1:1+(width-2)/99;
  assert(result.outcome==Outcome::Submitted&&result.submitted==3*tiles&&!result.fallback_allowed());
  assert(packet_log.size()==3*tiles&&opens==1&&compiles==1);
  assert(transforms==(width<=100?4*width:6*(width+tiles-1)));
  assert(!std::memcmp(original.data(),grid.data(),grid.size()*sizeof(Vec)));
  for(unsigned r=0;r<3;++r)for(unsigned t=0;t<tiles;++t){
   const unsigned first=width<=100?0:t*99,columns=width<=100?width:std::min(100U,width-first);
   const auto& packet=packet_log[r*tiles+t];assert(packet.size()==2*columns+1);
   assert(packet[0].flags==4&&packet[2*columns].flags==PVR_CMD_VERTEX_EOL);
   const float du=1.f/float(width-1),dv=1.f/3.f;
   assert(packet[1].u==float(first)*du&&packet[2*columns].u==float(first+columns-1)*du);
   assert(packet[1].v==float(r)*dv&&packet[2].v==(float(r)*dv+dv));
   if(t+1<tiles){const auto& next=packet_log[r*tiles+t+1];
    assert(packet[2*columns-1].u==next[1].u&&packet[2*columns].u==next[2].u);
    assert(packet[2*columns-1].x==next[1].x&&packet[2*columns-1].y==next[1].y&&
           packet[2*columns].x==next[2].x&&packet[2*columns].y==next[2].y);}
  }
 }
 // A late owner change after the first published tile is terminal: no next
 // source read or stale GX replay may follow that publication.
 fresh();std::vector<Vec> grid;set_sheet(101,4,grid);after_send_hook=retire_after_first;
 auto result=re4dc_cloth_native(&ClothWk[0],lights,&pos,1);
 assert(result.outcome==Outcome::PartialAbort&&result.submitted==1&&!result.fallback_allowed());
 assert(packet_log.size()==1&&transforms==200);
 // A change while transforming the first tile stops before publication.
 fresh();set_sheet(101,4,grid);retire_at_transform=4;
 result=re4dc_cloth_native(&ClothWk[0],lights,&pos,1);
 assert(result.outcome==Outcome::PartialAbort&&!result.published()&&!result.fallback_allowed());
 assert(packet_log.empty()&&transforms==4);
 fresh();set_sheet(99,4,grid);retire_at_transform=4;
 result=re4dc_cloth_native(&ClothWk[0],lights,&pos,1);
 assert(result.outcome==Outcome::PartialAbort&&!result.published()&&!result.fallback_allowed());
 assert(packet_log.empty()&&transforms==4);
 // The next tile's queue refusal retains the first admitted tile and reports
 // partial completion, never a fallback that would replay those triangles.
 fresh();set_sheet(101,2,grid);source_draws_finished=false;spill_available=false;
 deferred_top=16384+kEffectQuad21Node+(201*sizeof(pvr_vertex_t));
 result=re4dc_cloth_native(&ClothWk[0],lights,&pos,1);
 assert(result.outcome==Outcome::PartialAbort&&result.queued==1&&!result.fallback_allowed());
 assert(deferred_count==1&&packet_log.empty()&&transforms==204);
 // Resource refusal before publication still permits only a live source's
 // pre-publication fallback; an unsupported second material is unchanged.
 fresh();set_sheet(255,4,grid);missing=true;result=re4dc_cloth_native(&ClothWk[0],lights,&pos,1);
 assert(result.outcome==Outcome::Refused&&!transforms&&!send_calls);
 fresh();set_sheet(255,4,grid);ClothWk[0].pTobjA=&ClothWk[0];
 result=re4dc_cloth_native(&ClothWk[0],lights,&pos,1);
 assert(result.outcome==Outcome::UnsupportedBeforePublication&&!transforms&&!opens);
 // A near-plane seam keeps every source strip cell once and in column order.
 fresh();set_sheet(101,2,grid);grid[99].z=-.5f;
 result=re4dc_cloth_native(&ClothWk[0],lights,&pos,1);
 assert(result.outcome==Outcome::Submitted&&packet_log.size()==100&&result.submitted==100);
 const float du=1.f/100.f;
 for(unsigned i=0;i<100;++i){const auto& packet=packet_log[i];
  assert(packet.size()>1&&packet.size()<=13);
  float lo=2,hi=-1;for(unsigned k=1;k<packet.size();++k){lo=std::min(lo,packet[k].u);hi=std::max(hi,packet[k].u);}
  assert(lo>=float(i)*du-1e-6f&&hi<=float(i+1)*du+1e-6f);
 }
}
'''
    return stub, code


class ClothTiles11(unittest.TestCase):
    def test_default_off_source_and_native_object_identity(self):
        baseline_source = subprocess.check_output(["git", "show", f"{BASE}:src/game/cloth.cpp"],
                                                  cwd=REPO, text=True)
        baseline_native = subprocess.check_output(
            ["git", "show", f"{BASE}:port/dreamcast/game/platform/include/native_cloth_sheet11.inc"],
            cwd=REPO, text=True)
        with tempfile.TemporaryDirectory(prefix="re4dc-cloth-tiles11-off-") as td:
            tmp = Path(td)
            (tmp / "dc").mkdir()
            stub, current = actual_source_fixture()
            _, old = actual_source_fixture(baseline_source)
            (tmp / "dc/pvr.h").write_text(stub)
            source_file = tmp / "source.cpp"
            object_file = tmp / "source.o"
            for zero in (False, True):
                flags = ["-std=c++20", "-O2", "-g0", "-w", "-DRE4DC_FX_STRIP21=1", "-DRE4DC_CLOTH_NATIVE=1",
                         "-DRE4DC_NATIVE_DRAW_OUTCOMES=1", "-DRE4DC_CLOTH_SHEET11=1",
                         "-DRE4DC_PS2_UPLOAD_INCARNATION=1", "-DRE4DC_UI_HANDLES=1", "-DRE4DC_TA_DIRECT=1",
                         "-DRE4DC_EFFECT_SPRITE_MAX=256", "-I" + str(tmp), "-I" + str(INC),
                         "-I" + str(ROOT / "room")]
                if zero:
                    flags.append("-DRE4DC_CLOTH_TILES11=0")
                objects = []
                preprocessed = []
                for code in (old, current):
                    source_file.write_text(code.split("int main(){")[0])
                    preprocessed.append(subprocess.check_output(["g++", "-E", "-P", *flags, str(source_file)], text=True))
                    subprocess.run(["g++", *flags, "-c", str(source_file), "-o", str(object_file)], check=True)
                    objects.append(object_file.read_bytes())
                self.assertEqual(preprocessed[0], preprocessed[1])
                self.assertEqual(objects[0], objects[1])
            # The platform translation unit includes the sheet implementation
            # through native_effect_strip21.inc. Compare that actual include
            # chain against the integrated parent for both OFF settings.
            old_inc = tmp / "old_include"
            old_inc.mkdir()
            (old_inc / "native_effect_strip21.inc").write_bytes((INC / "native_effect_strip21.inc").read_bytes())
            (old_inc / "native_cloth_sheet11.inc").write_text(baseline_native)
            stub, packet_code = PREVIOUS.packet_harness()
            for zero in (False, True):
                flags = ["-std=c++20", "-O2", "-g0", "-w", "-DRE4DC_FX_STRIP21=1", "-DRE4DC_CLOTH_NATIVE=1",
                         "-DRE4DC_NATIVE_DRAW_OUTCOMES=1", "-DRE4DC_CLOTH_SHEET11=1",
                         "-DRE4DC_PS2_UPLOAD_INCARNATION=1", "-DRE4DC_UI_HANDLES=1", "-DRE4DC_TA_DIRECT=1",
                         "-DRE4DC_EFFECT_SPRITE_MAX=256", "-I" + str(tmp), "-I" + str(ROOT / "room")]
                if zero:
                    flags.append("-DRE4DC_CLOTH_TILES11=0")
                objects = []
                for include in (old_inc, INC):
                    source_file.write_text(packet_code)
                    subprocess.run(["g++", *flags, "-I" + str(include), "-I" + str(INC),
                                    "-c", str(source_file), "-o", str(object_file)], check=True)
                    objects.append(object_file.read_bytes())
                self.assertEqual(objects[0], objects[1])

    def test_make_scope(self):
        with tempfile.TemporaryDirectory(prefix="re4dc-cloth-tiles11-make-") as td:
            tmp = Path(td)
            kos = tmp / "kos-stub"
            kos.mkdir()
            (kos / "Makefile.rules").write_text("")
            targets = ["obj/src/game/cloth.o", "obj/platform/native_ui.o", "obj/src/game/esp_sub.o"]
            make = ["make", "--no-print-directory", "-f", "Makefile", "-n", "KOS_BASE=" + str(kos)]
            deps = ["EFFECT_SPRITES=1", "FX_STRIP21=1", "CLOTH_NATIVE=1", "NATIVE_DRAW_OUTCOMES=1",
                    "PS2_UPLOAD_INCARNATION=1", "CLOTH_SHEET11=1"]
            outputs = []
            for value in (None, "0", "1"):
                args = [*make, *targets, *deps]
                if value is not None:
                    args.append("CLOTH_TILES11=" + value)
                run = subprocess.run(args, capture_output=True, text=True, cwd=ROOT / "game")
                self.assertEqual(run.returncode, 0, run.stderr)
                outputs.append([line for line in run.stdout.splitlines() if line.startswith("kos-c++")])
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual(len(outputs[2]), len(targets))
            for i, line in enumerate(outputs[2]):
                self.assertEqual(line.count("-DRE4DC_CLOTH_TILES11=1"), int(i < 2))
            for value in ("", "0 1", "2", "-1"):
                run = subprocess.run([*make, targets[0],
                                      *deps, "CLOTH_TILES11=" + value], capture_output=True, text=True, cwd=ROOT / "game")
                self.assertNotEqual(run.returncode, 0)
            run = subprocess.run([*make, targets[0],
                                  *deps, "CLOTH_TILES11=1", "CLOTH_SHEET11=0"],
                                 capture_output=True, text=True, cwd=ROOT / "game")
            self.assertNotEqual(run.returncode, 0)

    def test_actual_wide_source_to_native_packets(self):
        stub, code = actual_source_fixture()
        requested = os.environ.get("CLOTH_TILES11_SANITIZE")
        modes = (False, True) if requested is None else (requested == "1",)
        for sanitize in modes:
            with self.subTest(sanitize=sanitize), tempfile.TemporaryDirectory(prefix="re4dc-cloth-tiles11-") as td:
                tmp = Path(td)
                (tmp / "dc").mkdir()
                (tmp / "dc/pvr.h").write_text(stub)
                cpp = tmp / "fixture.cpp"
                cpp.write_text(code)
                exe = tmp / "check"
                args = ["g++", "-std=c++20", "-O2", "-DRE4DC_FX_STRIP21=1", "-DRE4DC_CLOTH_NATIVE=1",
                        "-DRE4DC_NATIVE_DRAW_OUTCOMES=1", "-DRE4DC_CLOTH_SHEET11=1", "-DRE4DC_CLOTH_TILES11=1",
                        "-DRE4DC_PS2_UPLOAD_INCARNATION=1", "-DRE4DC_UI_HANDLES=1", "-DRE4DC_TA_DIRECT=1",
                        "-DRE4DC_EFFECT_SPRITE_MAX=256", "-fno-pie", "-no-pie", "-I" + str(tmp),
                        "-I" + str(INC), "-I" + str(ROOT / "room"), str(cpp),
                        str(ROOT / "room/pvr_geometry.cpp"), "-o", str(exe)]
                if sanitize:
                    args += ["-fsanitize=address,undefined", "-fno-omit-frame-pointer"]
                build = subprocess.run(args, capture_output=True, text=True)
                self.assertEqual(build.returncode, 0, build.stderr)
                env = dict(os.environ, ASAN_OPTIONS="detect_leaks=0")
                run = subprocess.run([str(exe)], capture_output=True, text=True, env=env)
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)


if __name__ == "__main__":
    unittest.main()
