#include <cassert>
#include <cstdint>
#include <cstring>
#include <cstdio>
#include <initializer_list>
using u8=uint8_t;using u16=uint16_t;using u32=uint32_t;
constexpr unsigned EFF_OWNER_MAX=0xd3,EFF_TEXOBJ_MAX=500;
unsigned checks,errors,fixups,initialized;
#define CHECK(c) do{++checks;assert(c);}while(0)
#define OWNER_ERR(...) (++errors)
#define OWNER_ERR2(...) (++errors)
struct Log {template<class... A>void err(A...){++errors;}template<class... A>void warn(A...){++errors;}} logger;Log* pLog=&logger;
struct Global{u32 Debug_flg[4]{};}global;Global* pG=&global;const char* owner_name_tbl[0xd3]{};
struct GXTexObj{u8 bytes[32];};struct GXTlutObj{u8 bytes[12];};using Mtx=float[3][4];
struct TEXHeader{u32 format,width,height;void* data;};struct CLUT{void* data;u32 format,numEntries;};
struct TEXDescriptor{TEXHeader* textureHeader;CLUT* CLUTHeader;};
struct TEXPalette{u32 version,numDescriptors;TEXDescriptor* descriptors;};
struct EspAnmData{u16 Width,Height;int16_t Cx,Cy;u16 Frames;};struct SstData{};struct SstList{};
struct SstTbl{SstData* data;SstList* list;u32 owner;};
struct EspTexWk{GXTexObj* pTexObj;u16 nTexObj;GXTlutObj tlut;TEXHeader* texHdr;Mtx mtx;TEXPalette* pTpl;EspAnmData* pAnm;u32 Owner;};
struct EspEfmMotTbl{u32 num,ofs[1];};struct EspEfmWk{void* model;void* tpl;EspEfmMotTbl* mot;void* pShapeHeader;u32 owner;};
struct cEspSystem{EspTexWk Esp_tex_tbl[256];EspEfmWk efmWk[256];SstTbl estTbl[211],sstTbl[211],pathTbl[211];u8 ownerCnt[211];GXTexObj texObj[500];u8 texObjFlag[63];int GetTexObjFlag(u32);void SetTexObjFlag(u32,int);} state; cEspSystem* g_pEspSys=&state;
void EspCalcTplAddr(TEXPalette* tpl){++fixups;tpl->version=1;}
TEXDescriptor* TEXGet(TEXPalette* p,unsigned i){return &p->descriptors[i];}
template<class...A>void GXInitTexObj(GXTexObj*,A...){++initialized;}
template<class...A>void GXInitTexObjCI(GXTexObj*,A...){++initialized;}
template<class...A>void GXInitTlutObj(A...){}template<class...A>void GXLoadTlut(A...){}
void PSMTXIdentity(Mtx m){std::memset(m,0,sizeof(Mtx));m[0][0]=m[1][1]=m[2][2]=1;}
#include "actual_structs.inc"
int espTexRegist(TEXPalette*,EspAnmData*,u8,u32);int estRegist(void*,void*,u32);int sstRegist(void*,void*,u32);int pathRegist(void*,void*,u32);int efmRegist(void*,void*,void*,void*,u8,u32);
int espTexRelease(u32);int estRelease(u32);int sstRelease(u32);int pathRelease(u32);int efmRelease(u32);
#include "actual_methods.inc"
alignas(32)u8 blob[65536];TEXHeader hdr{};TEXDescriptor descriptors[500];
void reset(){std::memset(&state,0,sizeof(state));for(auto& t:state.Esp_tex_tbl)t.Owner=0xd2;for(auto& m:state.efmWk)m.owner=0xd2;for(auto* a:{state.estTbl,state.sstTbl,state.pathTbl})for(unsigned i=0;i<211;++i)a[i].owner=0xd2;errors=fixups=initialized=0;}
unsigned used(){unsigned n=0;for(unsigned i=0;i<500;++i)n+=state.GetTexObjFlag(i);return n;}
u32 fixture(unsigned a=1,unsigned b=2){std::memset(blob,0,sizeof(blob));auto*d=(EffData*)blob;d->version=11;d->ofsTexId=128;d->ofsTpl=192;d->ofsAnm=256;d->ofsEstList=d->ofsSstList=d->ofsPathList=320;d->ofsEstData=d->ofsSstData=d->ofsPathData=336;d->ofsEfmId=384;d->ofsEfm=448;
 auto* ids=(EffIdTbl*)(blob+128);ids->num=2;ids->ent[0].id=7;ids->ent[1].id=9;
 auto* ts=(EffOfsTbl*)(blob+192);ts->num=2;ts->ofs[0]=512-192;ts->ofs[1]=544-192;
 auto* an=(EffOfsTbl*)(blob+256);an->num=2;an->ofs[0]=576-256;an->ofs[1]=608-256;
 for(unsigned i=0;i<500;++i)descriptors[i]={&hdr,nullptr};
 *(TEXPalette*)(blob+512)={0,a,descriptors};*(TEXPalette*)(blob+544)={0,b,descriptors};((EspAnmData*)(blob+576))->Frames=a;((EspAnmData*)(blob+608))->Frames=b;
 auto* models=(EffIdTbl*)(blob+384);models->num=1;models->ent[0].id=11;auto* ms=(EffOfsTbl*)(blob+448);ms->num=1;ms->ofs[0]=640-448;auto* model=(EffEfmEnt*)(blob+640);model->ofsModel=32;model->ofsTpl=36;
 CHECK(uintptr_t(blob)<=UINT32_MAX);return u32(uintptr_t(blob));}
int main(){constexpr unsigned o=0x36;u32 f;
 reset();f=fixture();CHECK(EspDataLoad(f,o,0)==1);CHECK(state.ownerCnt[o]==1&&used()==3&&initialized==3);CHECK(state.estTbl[o].owner==o&&state.sstTbl[o].owner==o&&state.pathTbl[o].owner==o&&state.efmWk[11].owner==o);CHECK(EspDataLoad(f,o,0)==1&&state.ownerCnt[o]==2&&used()==3);CHECK(EspDataRelease(o,1,1)==1&&used()==3);CHECK(EspDataRelease(o,1,1)==1&&!used());
 // Other owners cannot fill a per-owner registry: only this owner's row matters.
 reset();f=fixture();for(unsigned i=0;i<210;++i)if(i!=o){state.estTbl[i].owner=i;state.sstTbl[i].owner=i;state.pathTbl[i].owner=i;}CHECK(EspDataLoad(f,o,0)==1);CHECK(state.estTbl[o].owner==o&&state.sstTbl[o].owner==o&&state.pathTbl[o].owner==o);CHECK(EspDataRelease(o,0,1)==1);CHECK(state.estTbl[5].owner==5);
 // Injected pool pressure is a service-boundary state, not proved normal gameplay occupancy.
 reset();f=fixture();CHECK(EspPullTexObj(498)!=nullptr);CHECK(EspDataLoad(f,o,0)==1);CHECK(state.ownerCnt[o]==1&&state.Esp_tex_tbl[7].Owner==o&&state.Esp_tex_tbl[9].Owner==0xd2&&state.efmWk[11].owner==o);CHECK(state.Esp_tex_tbl[9].nTexObj==2&&state.Esp_tex_tbl[9].pTexObj==nullptr);CHECK(fixups==2&&used()==499);CHECK(EspDataLoad(f,o,0)==1&&state.ownerCnt[o]==2&&state.Esp_tex_tbl[9].Owner==0xd2);CHECK(EspDataRelease(o,0,1)==1&&used()==498);for(unsigned i=0;i<498;++i)state.SetTexObjFlag(i,0);CHECK(EspDataLoad(f,o,0)==1&&used()==3&&state.Esp_tex_tbl[9].Owner==o);CHECK(EspDataRelease(o,0,1)==1&&!used());
 // A registration collision preserves its existing owner, but the outer load still publishes count/tables.
 reset();f=fixture();state.Esp_tex_tbl[7].Owner=5;CHECK(EspDataLoad(f,o,0)==1&&state.Esp_tex_tbl[7].Owner==5&&state.Esp_tex_tbl[9].Owner==o&&state.ownerCnt[o]==1);CHECK(EspDataRelease(o,0,1)==1&&state.Esp_tex_tbl[7].Owner==5&&!used());
 reset();f=fixture();state.efmWk[11].owner=5;state.efmWk[11].model=(void*)0x1234;CHECK(EspDataLoad(f,o,0)==1&&state.efmWk[11].owner==5&&state.efmWk[11].model==(void*)0x1234&&state.ownerCnt[o]==1);CHECK(EspDataRelease(o,0,1)==1&&state.efmWk[11].owner==5);
 // Frame mismatch is malformed input; no such mismatch exists in the sealed 89-file census.
 reset();f=fixture();((EspAnmData*)(blob+608))->Frames=3;CHECK(EspDataLoad(f,o,0)==1&&state.Esp_tex_tbl[9].Owner==0xd2&&state.ownerCnt[o]==1);((EspAnmData*)(blob+608))->Frames=2;CHECK(EspDataLoad(f,o,0)==1&&state.Esp_tex_tbl[9].Owner==0xd2);CHECK(EspDataRelease(o,0,1)==1);CHECK(EspDataLoad(f,o,0)==1&&state.Esp_tex_tbl[9].Owner==o);
 // Valid same-owner count prevents repeat EST/SST/path registration, even with strict duplicate flag.
 reset();f=fixture();CHECK(EspDataLoad(f,o,0)==1);auto est=state.estTbl[o];CHECK(EspDataLoad(f,o,1)==0&&state.ownerCnt[o]==2&&state.estTbl[o].data==est.data);CHECK(EspDataRelease(o,0,1)==1);
 // Original DOL has this exact boundary; this is not evidence for a port correction.
 reset();CHECK(EspPullTexObj(499)!=nullptr&&used()==499);CHECK(EspPullTexObj(1)==nullptr&&used()==499);reset();CHECK(EspPullTexObj(500)==nullptr&&!used());reset();CHECK(EspPullTexObj(0)==&state.texObj[0]&&!used());
 reset();for(unsigned i=0;i<500;i+=2)state.SetTexObjFlag(i,1);CHECK(used()==250&&EspPullTexObj(2)==nullptr);CHECK(used()==250);
 // Existing b310 first-version guard remains the sole difference in its own malformed-input control.
 reset();f=fixture();((EffData*)blob)->version=10;CHECK(EspDataLoad(f,o,0)==0);CHECK(state.ownerCnt[o]==(RE4DC_EFFECT_ADMISSION_GUARD?0:1));
 printf("REGISTRATION_BOUNDARY PASS checks=%u guard=%u (injected refusal reachability not certified)\n",checks,unsigned(RE4DC_EFFECT_ADMISSION_GUARD));
}
