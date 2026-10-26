"""Cold composite serialization and actual payload/UI lifetime acknowledgements."""
from pathlib import Path
import hashlib
import struct
import subprocess
import tempfile
import unittest
from test_runtime_hooks import function

HERE=Path(__file__).resolve().parent
GAME=HERE.parents[2]/'game'


class StaticManifestTests(unittest.TestCase):
    def test_actual_static_scope_refuses_external_colour_and_fresh_replay_class(self):
        ui=(GAME/'platform/native_ui.cpp').read_text()
        scope=(GAME/'platform/include/gc_asset_static_source.inc').read_text()
        fixture=r'''
#include "gc_asset_static.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <string>
using namespace re4dc_gcasset;
bool sq;std::string logs;
extern "C" void re4dc_log(const char*fmt,...){assert(!sq);char out[256];va_list ap;va_start(ap,fmt);vsnprintf(out,sizeof out,fmt,ap);va_end(ap);logs+=out;}
struct Lighting{bool ambient_vertex=false,material_vertex=false;};
struct Re4dcModelPart{const void*model;const void*info;unsigned alpha_state=255;const Lighting*lighting=nullptr;};
unsigned identity=0x01230000U,role=1,resolutions;
extern "C" unsigned re4dc_gcasset_model_identity(const void*,const void*,const void**out){assert(!sq);++resolutions;*out=nullptr;return identity;}
extern "C" unsigned re4dc_gcasset_weapon_consumer(const void*,const void*,unsigned,unsigned){return role;}
'''+scope+r'''
const void* gcasset_probe_part;const void* gcasset_probe_caller;const void* gcasset_probe_outer;
SourceUse gcasset_model_pending;
'''+function(ui,'void gcasset_model_prepare(')+'\n'+function(ui,'void gcasset_model_accept(')+r'''
PayloadProof proof,receipt;int owner,index_owner,wrong;
void flush(){payload_flush_all();member_flush();}
void text(const Digest&d,char*out){for(unsigned i=0;i<32;++i)sprintf(out+2*i,"%02x",d.bytes[i]);}
void ack(Re4dcModelPart*p,const void*o=&owner){GcStaticSourceScope selected(proof,o,p);gcasset_model_prepare(p);sq=true;gcasset_model_accept();sq=false;}
void unknown(unsigned visit,Re4dcModelPart*p,const void*o=&owner,bool weapon=true){logs.clear();begin(0x111,visit,Required);ack(p,o);flush();end(visit);assert(logs.find("source_geometry=0")!=std::string::npos && logs.find("weapon=0")!=std::string::npos && logs.find("GC-ASSET v=")==std::string::npos);if(weapon)assert(logs.find("consumer=3")!=std::string::npos);}
int main(){unsigned char data[512]={17};StaticManifest m;assert(static_manifest_begin(m,StaticView,0x111,7,data,sizeof data));for(unsigned i=0;i<StaticRoleCount;++i){assert(static_manifest_note(m,StaticRole(i),NotApplicable));}
 Digest geometry{},manifest;memcpy(geometry.bytes,m.data+32,32);assert(static_manifest_seal(m,manifest));char a[65],b[65];text(geometry,a);text(manifest,b);a[40]=b[40]=0;CatalogRow rows[]={{"geometry",a,geometry,PS2},{"layout",b,manifest,PS2}};assert(install(rows,2));assert(payload_capture_composite(proof,&owner,data,sizeof data,nullptr,0,m));
 int model,info;Lighting lighting;Re4dcModelPart p{&model,&info,255,&lighting};source_use={77,1U<<SourceGeometry,&wrong,&wrong};
 begin(0x111,1,Required);ack(&p);assert(source_use.serial==77 && source_use.model==&wrong);flush();end(1);assert(logs.find("source_geometry=2")!=std::string::npos && logs.find("weapon=2")!=std::string::npos);
 p.alpha_state=511;unknown(2,&p);p.alpha_state=255;lighting.ambient_vertex=true;unknown(3,&p);lighting.ambient_vertex=false;lighting.material_vertex=true;unknown(4,&p);lighting.material_vertex=false;
 unknown(5,&p,&wrong);identity=0x010a0000U;unknown(6,&p,&owner,false);identity=0xffffffffU;unknown(7,&p,&owner,false);identity=0x01230000U;
 const unsigned old=proof.serial,mask=(1U<<SourceGeometry)|(1U<<Weapon);payload_invalidate(proof,&owner);unknown(8,&p);payload_retire(proof);data[0]=18;assert(static_manifest_begin(m,StaticView,0x111,7,data,sizeof data));for(unsigned i=0;i<StaticRoleCount;++i){assert(static_manifest_note(m,StaticRole(i),NotApplicable));}assert(payload_capture_composite(proof,&owner,data,sizeof data,nullptr,0,m));
 role=0;const unsigned before=resolutions;{ReplayScope replay(old,mask,&proof);unknown(9,&p);}assert(resolutions==before);{ReplayScope replay(0,mask,&proof);unknown(10,&p);}assert(resolutions==before);
 // Parsed-owner receipt retains only checked original digest+read count.
 payload_retire(proof);assert(payload_capture_receipt(receipt,&index_owner,geometry,sizeof data));assert(!receipt.base && receipt.bytes==sizeof data);data[0]=99;
 StaticManifest policy;assert(static_manifest_begin(policy,StaticView,0x111,7,data,sizeof data));assert(static_manifest_receipt(policy,STD_INDEX,receipt,&index_owner,1,StaticConsumedSpan));assert(!memcmp(policy.data+64+STD_INDEX*52+20,geometry.bytes,32));
 StaticManifest bad;assert(static_manifest_begin(bad,StaticView,0x111,7,data,sizeof data));payload_invalidate(receipt,&index_owner);assert(!static_manifest_receipt(bad,STD_INDEX,receipt,&index_owner));payload_retire(receipt);
}
'''
        payload=(GAME/'platform/gc_asset_payloads.cpp').read_text()
        self.compile(fixture,payload)
        for label,old,new in [
            ('source colour bypass','if(part && ((part->alpha_state&256) || (part->lighting &&','if(false && ((part->alpha_state&256) || (part->lighting &&'),
            ('ambiguous class positive','if(!use.mask){use.mask=1U<<re4dc_gcasset::SourceGeometry;use.serial=0;}','if(!use.mask){use.mask=1U<<re4dc_gcasset::SourceGeometry;}'),
            ('fresh replay class lookup','re4dc_gcasset::replay_use.serial!=0xffffffffU?re4dc_gcasset::replay_use.mask:gcasset_static_consumer(part)','gcasset_static_consumer(part)'),
        ]:
            with self.subTest(mutant=label):
                self.assertEqual(fixture.count(old),1)
                self.compile(fixture.replace(old,new),payload,reject=True)

    def test_actual_composite_and_known_unknown_lifetimes(self):
        ui=(GAME/'platform/native_ui.cpp').read_text()
        payload=(GAME/'platform/gc_asset_payloads.cpp').read_text()
        geometry=bytes([17])*512
        side=bytes([23])*80
        framed=b'GCSTC001'+struct.pack('<6I',1,3,0x111,12,7,0)+hashlib.sha256(geometry).digest()
        framed+=b''.join(struct.pack('<5I',i+1,4,80,1,i)+hashlib.sha256(side).digest() for i in range(12))
        self.assertEqual(len(framed),688)
        expected=hashlib.sha256(framed).hexdigest()
        fixture=r'''
#include "gc_asset_static.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <string>
using namespace re4dc_gcasset;
bool sq;std::string logs;
extern "C" void re4dc_log(const char*fmt,...){assert(!sq);char out[256];va_list ap;va_start(ap,fmt);vsnprintf(out,sizeof out,fmt,ap);va_end(ap);logs+=out;}
struct Re4dcModelPart{const void*model;const void*info;};
const void* gcasset_probe_part;const void* gcasset_probe_caller;const void* gcasset_probe_outer;
SourceUse gcasset_model_pending;
'''+function(ui,'void gcasset_model_prepare(')+'\n'+function(ui,'void gcasset_model_accept(')+r'''
PayloadProof proof,view,copy;
unsigned char geometry[512],side[80],other[512];int owner,view_owner,copy_owner;
void text(const Digest&d,char*out){for(unsigned i=0;i<32;++i)sprintf(out+2*i,"%02x",d.bytes[i]);}
std::string id(const Digest&d){char out[65];text(d,out);return std::string(out,40);}
StaticManifest build(StaticOwner kind=StaticWorld){StaticManifest m;assert(static_manifest_begin(m,kind,0x111,7,geometry,sizeof geometry));
 for(unsigned i=0;i<StaticRoleCount;++i){assert(static_manifest_bytes(m,StaticRole(i),side,sizeof side,1,i));}return m;}
void catalog(const StaticManifest&m,Provenance interpretation){Digest a{},b{};memcpy(a.bytes,m.data+32,32);b=fingerprint(m.data,sizeof m.data);static std::string aid,bid;static CatalogRow rows[2];aid=id(a);bid=id(b);rows[0]={"geometry",aid.c_str(),a,PS2};rows[1]={"layout",bid.c_str(),b,interpretation};assert(install(rows,2));}
void ack(PayloadProof& p,int*o,unsigned serial=~0U){PayloadScope scope(p,o,nullptr,nullptr,(1U<<SourceGeometry)|(1U<<Weapon));if(serial!=~0U)source_use.serial=serial;gcasset_model_prepare(nullptr);sq=true;gcasset_model_accept();sq=false;}
void flush(){payload_flush_all();member_flush();}
void zero_counts(){assert(logs.find("source_geometry=0")!=std::string::npos && logs.find("weapon=0")!=std::string::npos && logs.find("consumer=3")!=std::string::npos && logs.find("GC-ASSET v=")==std::string::npos);}
int main(){memset(geometry,17,sizeof geometry);memset(side,23,sizeof side);memset(other,31,sizeof other);
 auto m=build();Digest digest;assert(static_manifest_seal(m,digest));char hex[65];text(digest,hex);assert(std::string(hex)=="EXPECTED");
 // Whole geometry PS2 cannot hide the independently GC interpretation asset.
 catalog(m,GameCube);begin(0x111,1,Required);assert(payload_capture_composite(proof,&owner,geometry,sizeof geometry,side,sizeof side,m));ack(proof,&owner);flush();end(1);assert(logs.find("kind=layout")!=std::string::npos && logs.find("provenance=gc")!=std::string::npos);payload_retire(proof);
 // All twelve roles, exact state/extent/version/flags/profile and original
 // byte digests participate. Changed role files cannot match the old catalog.
 catalog(m,PS2);for(unsigned role=0;role<StaticRoleCount;++role){auto changed=m;changed.data[64+role*52+20]^=1;Digest next;assert(static_manifest_seal(changed,next));assert(memcmp(next.bytes,digest.bytes,32));}
 for(unsigned field: {8U,12U,16U}){auto changed=m;changed.data[64+R4SG*52+field]^=1;Digest next;assert(static_manifest_seal(changed,next));assert(memcmp(next.bytes,digest.bytes,32));}
 // Incomplete/unproven states fail BEFORE publication, even with a catalog
 // explicitly marking that candidate's complete serialized bytes PS2.
 unsigned visit=2;
 for(unsigned role=0;role<StaticRoleCount;++role)for(unsigned state: {unsigned(Rejected),unsigned(Unproven)}){
  auto bad=m;bad.data[64+role*52+4]=state;catalog(bad,PS2);logs.clear();begin(0x111,visit,Required);
  assert(!payload_capture_composite(proof,&owner,geometry,sizeof geometry,side,sizeof side,bad));assert(!proof.serial);ack(proof,&owner);flush();end(visit++);zero_counts();
 }
 auto bad=m;bad.seen&=~(1U<<SCPS);assert(!static_manifest_seal(bad,digest));bad=m;assert(!static_manifest_note(bad,R4SG,Absent));assert(!static_manifest_seal(bad,digest));bad=m;bad.data[64+SCPS*52]=1;assert(!static_manifest_seal(bad,digest));bad=m;bad.data[64+SDO3_BASE80*52+8]=79;assert(!static_manifest_seal(bad,digest));
 // Explicit disabled/absent/not-applicable rows are distinct and never
 // implied by zero initialization or a missing parser branch.
 StaticManifest empty;assert(static_manifest_begin(empty,StaticView,0x111,7,geometry,sizeof geometry));
 for(unsigned i=0;i<StaticRoleCount;++i){assert(static_manifest_note(empty,StaticRole(i),i%3==0?NotApplicable:i%3==1?Disabled:Absent));}assert(static_manifest_seal(empty,digest));
 // Ordinary owners lack a physical sidecar, but still emit its manifest.
 catalog(empty,GameCube);logs.clear();begin(0x111,visit,Required);assert(!payload_capture_composite(view,&view_owner,other,sizeof other,nullptr,0,empty));assert(payload_capture_composite(view,&view_owner,geometry,sizeof geometry,nullptr,0,empty));ack(view,&view_owner);flush();end(visit++);assert(logs.find("kind=layout")!=std::string::npos && logs.find("provenance=gc")!=std::string::npos);
 assert(payload_copy_register(copy,&copy_owner,side,sizeof side));assert(!payload_copy_publish(copy,&copy_owner,view,view.serial));flush();payload_retire(copy);payload_retire(view);
 // Capture is before controlled mutation; seal/publication does not hash
 // prepared geometry or rewritten sidecars a second time.
 m=build();catalog(m,PS2);geometry[0]^=1;side[0]^=1;assert(payload_capture_composite(proof,&owner,geometry,sizeof geometry,side,sizeof side,m));AssetDescription asset;assert(describe_checked(proof.asset,&asset));assert(!memcmp(asset.digest.bytes,m.data+32,32));
 logs.clear();begin(0x111,visit,Required);logs.clear();ack(proof,&owner);const unsigned old=proof.serial;sq=true;payload_invalidate(proof,&owner);assert(!proof.serial && logs.empty());sq=false;flush();end(visit++);assert(logs.find("source_geometry=2")!=std::string::npos && logs.find("weapon=2")!=std::string::npos);payload_retire(proof);
 // A missing proof keeps its known class and cannot inherit the ambient
 // healthy original. Saved zero stays zero after same-owner rebind.
 logs.clear();begin(0x111,visit,Required);ack(proof,&owner);flush();end(visit++);zero_counts();
 m=build();catalog(m,PS2);assert(payload_capture_composite(proof,&owner,geometry,sizeof geometry,side,sizeof side,m));
 logs.clear();begin(0x111,visit,Required);{ReplayScope replay(0,(1U<<SourceGeometry)|(1U<<Weapon),&proof);ack(proof,&owner);}flush();end(visit++);zero_counts();
 logs.clear();begin(0x111,visit,Required);ack(proof,&owner,old);flush();end(visit++);zero_counts();
 logs.clear();begin(0x111,visit,Required);sq=true;payload_invalidate(proof,&owner);sq=false;ack(proof,&owner);flush();end(visit++);zero_counts();payload_retire(proof);
 assert(install(nullptr,0));
}
'''.replace('EXPECTED',expected)
        self.compile(fixture,payload)
        mutants=[
            ('mesh-only publication',' || !static_manifest_seal(manifest,composite)',''),
            ('foreign geometry base','base!=manifest.geometry_base || ',''),
            ('missing manifest acknowledgement','if(proof.layout_bytes || (!proof.layout && proof.layout_asset.value))','if(false)'),
            ('unknown class erased','source_use={0,mask,model,info,&proof};','source_use={};'),
            ('replay recapture','if(replay_use.serial!=0xffffffffU){','if(false){'),
            ('missing invalidation','void payload_invalidate(PayloadProof& proof,const void* owner){\n    proof.serial=0;','void payload_invalidate(PayloadProof& proof,const void* owner){'),
            ('lost prior accepted prefix','if(!proof.owner || !proof.asset.value)','if(!proof.owner || !proof.serial || !proof.asset.value)'),
        ]
        for label,old,new in mutants:
            with self.subTest(mutant=label):
                self.assertEqual(payload.count(old),1)
                self.compile(fixture,payload.replace(old,new),reject=True)

    def compile(self,fixture,payload,reject=False):
        with tempfile.TemporaryDirectory(prefix='gc-port23-static-manifest-',dir='/dev/shm') as scratch:
            root=Path(scratch);(root/'fixture.cpp').write_text(fixture);(root/'payload.cpp').write_text(payload)
            subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-DRE4DC_GC_ASSET_GATE=1',
                            '-I',str(GAME/'platform/include'),'-I',str(GAME/'platform'),str(root/'fixture.cpp'),str(root/'payload.cpp'),
                            str(GAME/'platform/gc_asset_gate.cpp'),str(GAME/'platform/gc_asset_members.cpp'),'-o',str(root/'fixture')],check=True)
            result=subprocess.run(['/lib64/ld-linux-x86-64.so.2',str(root/'fixture')],capture_output=reject,text=True)
            if reject:self.assertNotEqual(result.returncode,0,'compiled composite mutant escaped runtime assertions')
            else:result.check_returncode()


if __name__=='__main__':unittest.main()
