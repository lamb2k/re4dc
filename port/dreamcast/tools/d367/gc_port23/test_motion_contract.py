"""Actual-source counterexamples for the proposed Motion receipt contract.

These execute existing source fragments, not an implemented Motion observer.
They deliberately establish why current-pMot/prelit/cache pointers are not proof
of a visible pose's origins. No Motion coverage bit or provenance is granted.
"""
from pathlib import Path
import subprocess
import tempfile
import unittest
from test_runtime_hooks import function

HERE = Path(__file__).resolve().parent
GAME = HERE.parents[2] / 'game'
SOURCE = GAME.parents[2]


class MotionContractTests(unittest.TestCase):
    def run_fixture(self, fixture):
        with tempfile.TemporaryDirectory(prefix='gc-port23-motion-contract-', dir='/dev/shm') as temporary:
            root = Path(temporary)
            (root / 'fixture.cpp').write_text(fixture)
            subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                            '-I', str(GAME / 'platform/include'), str(root / 'fixture.cpp'),
                            '-o', str(root / 'fixture')], check=True)
            subprocess.run(['/lib64/ld-linux-x86-64.so.2', str(root / 'fixture')], check=True)

    def test_stopped_visible_pose_is_not_certified_by_prelit(self):
        push = (SOURCE / 'src/game/pl_push.cpp').read_text()
        motion = (SOURCE / 'src/game/motion.cpp').read_text()
        bridge = (GAME / 'model_bridge.cpp').read_text()
        fixture = r'''
#include <cassert>
struct MotionWork{void*blend;unsigned Mot_attr;};
struct cModel{void*pMotion;MotionWork Motion;float visible_pose;};
struct ModelData{unsigned shapeOfs;};struct cModelInfo{ModelData*pData;unsigned be_flag;};
struct cPlPush{cModel*m_Target;void stopTarget();};
#define MOTION(m) (&(m)->Motion)
''' + function(push, 'void cPlPush::stopTarget()') + '\n' + function(motion, 'void MotionBlendOff(') + '\n' + function(motion, 'void MotionPause(') + '\n' + function(bridge, 'extern "C" int re4dc_actor_model_prelit(') + r'''
int main(){int old_motion,blend;ModelData data{};cModelInfo info{&data,0};cModel m{&old_motion,{&blend,0},37.0f};cPlPush push{&m};
 assert(!re4dc_actor_model_prelit(&m,&info));MotionPause(&m);assert((m.Motion.Mot_attr&8) && m.pMotion==&old_motion && m.visible_pose==37.0f);
 MotionBlendOff(&m);assert(!m.Motion.blend && m.visible_pose==37.0f);push.stopTarget();
 assert(!m.pMotion && m.visible_pose==37.0f && re4dc_actor_model_prelit(&m,&info));
 // A null current pointer/prelit hint coexists with an unchanged old pose.
 // A future observer must retain committed-pose origin instead of inferring
 // procedural/no-motion output from either of these values.
}
'''
        self.run_fixture(fixture)

    def test_actual_interpolation_uses_previous_pose_after_current_motion_changes(self):
        motion = (SOURCE / 'src/game/motion.cpp').read_text()
        hokan = function(motion, 'void MotionHokan(')
        # Execute the actual translation portion. Quaternion/scale portions
        # are outside this bounded counterexample; they need their own receipt.
        translation = hokan[hokan.index('    w->Hokan_cnt--;'):hokan.index('        c0.x =')]
        fixture = r'''
#include <cassert>
using f32=float;using s32=int;
struct Vec{float x,y,z;};struct MotionWork{void*pMot;unsigned Hokan_cnt,Hokan_frame,Mot_attr;};
struct MotionParts{unsigned flags;};struct cModel{cModel*pParts;MotionWork Motion;MotionParts motParts;float prevMat[3][4],l_mat[3][4];};
#define MOTION(m) (&(m)->Motion)
#define MOTION_PARTS(p) (&(p)->motParts)
float observed;
void translation(cModel*m,MotionWork*w){cModel*p;float t,u;Vec pos;
''' + translation + r'''
        observed=pos.x;
    }
}
int main(){int new_motion;cModel model{},part{};model.pParts=&part;model.Motion={&new_motion,2,2,0};part.motParts.flags=0x10000000;part.prevMat[0][3]=20;part.l_mat[0][3]=2;
 translation(&model,&model.Motion);assert(observed==11 && model.Motion.pMot==&new_motion);
 // The currently selected motion does not identify prevMat's contributor.
 // Its old origin remains relevant while the committed output contains it.
 part.motParts.flags=0x10000000;translation(&model,&model.Motion);assert(observed==2);
}
'''
        self.run_fixture(fixture)

    def test_actual_key_lease_restores_proxy_and_keeps_source_header(self):
        fixture = r'''
#include "native_motion.h"
#include <cassert>
unsigned cache[2]={7,8};const void*seen;bool available=true;unsigned acquired,released;
extern "C" int re4dc_motion_acquire(const void*header,unsigned**table){seen=header;++acquired;if(!available)return 0;*table=cache;return 17;}
extern "C" void re4dc_motion_release(int token){assert(token==17);++released;}
int main(){static int original_header;unsigned proxy[1]={9};unsigned*local=proxy;
 {Re4dcMotionLease lease(&original_header,&local,proxy);assert(lease.external() && local==cache && seen==&original_header);}
 assert(local==proxy && acquired==1 && released==1);
 available=false;{Re4dcMotionLease lease(&original_header,&local,proxy);assert(!lease.external() && local==proxy);}
 assert(acquired==2 && released==1 && seen==&original_header);
 // Evaluated table/proxy address changes are not a new original asset and
 // neither pointer establishes provenance or an accepted visible use.
}
'''
        self.run_fixture(fixture)


if __name__ == '__main__':unittest.main()
