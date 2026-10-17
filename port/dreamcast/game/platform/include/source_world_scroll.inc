// Extends the existing scrTbl publication with serial witnesses only. No
// second object table or native renderer allocation is created.
#include "re4dc_platform.h"
#include "source_world_memory.inc"
namespace {
constexpr unsigned kSourceWorldWorks=90;
unsigned sourceWorldSerial[kSourceWorldWorks]{};
cSmd* sourceWorldSmd;
unsigned sourceWorldRoomGeneration;
extern "C" int re4dc_room4_state(unsigned*,unsigned*,unsigned*,unsigned*,unsigned*);
extern "C" int re4dc_model_owned_source(const void*,unsigned);
unsigned sourceWorldRoom() {
    unsigned generation=0,c,b,s,r;
    return re4dc_room4_state(&generation,&c,&b,&s,&r)?generation:0;
}
void sourceWorldScrollClear() {
    sourceWorldSmd=nullptr;sourceWorldRoomGeneration=0;
    for(auto& serial:sourceWorldSerial)serial=0;
}
void sourceWorldScrollBind(unsigned work,cObj* object) {
    if(!pG || G_ROOM_ID!=0x200 || !pSmd || reinterpret_cast<unsigned long>(pSmd)%alignof(cSmd) ||
       !re4dc_model_owned_source(pSmd,0x10+kSourceWorldWorks*sizeof(SmdWork)) || pSmd->Flag ||
       pSmd->nModel!=kSourceWorldWorks || nScrWork!=int(kSourceWorldWorks) ||
       work>=kSourceWorldWorks || !re4dc_source_world_pool(object,0) ||
       (object->be_flag&0x201)!=1)return;
    const unsigned generation=sourceWorldRoom();if(!generation)return;
    if(sourceWorldSmd!=pSmd || sourceWorldRoomGeneration!=generation)sourceWorldScrollClear();
    sourceWorldSmd=pSmd;sourceWorldRoomGeneration=generation;
    sourceWorldSerial[work]=object->serial;
}
bool sourceWorldRange(const void* p,unsigned bytes,unsigned alignment=4) {
    return p && reinterpret_cast<unsigned long>(p)%alignment==0 && re4dc_model_owned_source(p,bytes)!=0;
}
bool sourceWorldVec(const Vec& a,const Vec& b){return a.x==b.x && a.y==b.y && a.z==b.z;}
}
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
namespace {
unsigned sourceWorldMemberField;
bool sourceWorldMemberTest(bool valid,unsigned field){if(!valid)sourceWorldMemberField=field;return valid;}
}
#define RE4DC_MEMBER_TEST(test,field) sourceWorldMemberTest((test),(field))
#else
#define RE4DC_MEMBER_TEST(test,field) (test)
#endif
extern "C" int re4dc_scroll_source_member(cModel* model,unsigned serial,unsigned* index) {
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
    sourceWorldMemberField=0;
#endif
    if(!RE4DC_MEMBER_TEST(model,1) || !RE4DC_MEMBER_TEST(index,2) || !RE4DC_MEMBER_TEST(pG,3) ||
       !RE4DC_MEMBER_TEST(G_ROOM_ID==0x200,4) || !RE4DC_MEMBER_TEST(serial,5) ||
       !RE4DC_MEMBER_TEST(sourceWorldRoomGeneration,6) || !RE4DC_MEMBER_TEST(sourceWorldRoom()==sourceWorldRoomGeneration,7) ||
       !RE4DC_MEMBER_TEST(pSmd==sourceWorldSmd,8) || !RE4DC_MEMBER_TEST(sourceWorldRange(pSmd,0x10+kSourceWorldWorks*sizeof(SmdWork),alignof(cSmd)),9) ||
       !RE4DC_MEMBER_TEST(!pSmd->Flag,10) || !RE4DC_MEMBER_TEST(pSmd->nModel==kSourceWorldWorks,11) ||
       !RE4DC_MEMBER_TEST(nScrWork==int(kSourceWorldWorks),12) ||
       !RE4DC_MEMBER_TEST(sourceWorldAllocated(scrTbl,kSourceWorldWorks*sizeof(cObj*),true),13) ||
       !RE4DC_MEMBER_TEST(re4dc_source_world_pool(model,0),14))return 0;
    // The table can retain a destroyed pool address. The publication serial,
    // checked before any info/part dereference, refuses that address's new life.
    unsigned found=kSourceWorldWorks;
    for(unsigned i=0;i<kSourceWorldWorks;++i)if(scrTbl[i]==model) {
        if(!RE4DC_MEMBER_TEST(found==kSourceWorldWorks,15) || !RE4DC_MEMBER_TEST(sourceWorldSerial[i]==serial,16))return 0;
        found=i;
    }
    if(!RE4DC_MEMBER_TEST(found!=kSourceWorldWorks,17) || !RE4DC_MEMBER_TEST(model->serial==serial,18) ||
       !RE4DC_MEMBER_TEST(model->kindid==2,19) || !RE4DC_MEMBER_TEST((model->be_flag&0x201)==1,20) ||
       !RE4DC_MEMBER_TEST(static_cast<cObj*>(model)->blk==-1,21) ||
       !RE4DC_MEMBER_TEST(model->invisible_factor==1.f,22) || !RE4DC_MEMBER_TEST(model->invisible_factor2==1.f,23))return 0;
    const auto& w=pSmd->work[found];
    if(!RE4DC_MEMBER_TEST(w.id!=0xff,24) || !RE4DC_MEMBER_TEST(w.binNo!=0xff,25) ||
       !RE4DC_MEMBER_TEST(!(w.flags&0x10),26) || !RE4DC_MEMBER_TEST(w.motNo==0xff,27) ||
       !RE4DC_MEMBER_TEST(sourceWorldVec(model->pos,w.pos),28) || !RE4DC_MEMBER_TEST(sourceWorldVec(model->ang,w.rot),29) ||
       !RE4DC_MEMBER_TEST(sourceWorldVec(model->scale,w.scale),30))return 0;
    const auto base=reinterpret_cast<unsigned long>(pSmd);
    if(!RE4DC_MEMBER_TEST(pSmd->BinTblOfs<=0x200000U,31))return 0;
    const auto* table=reinterpret_cast<const u32*>(base+pSmd->BinTblOfs);
    if(!RE4DC_MEMBER_TEST(sourceWorldRange(table,(unsigned(w.binNo)+1U)*sizeof(u32)),32) ||
       !RE4DC_MEMBER_TEST(table[w.binNo]<=0x200000U,33))return 0;
    const auto* data=reinterpret_cast<const ModelData*>(reinterpret_cast<unsigned long>(table)+table[w.binNo]);
    const auto* info=model->pModelInfo;
    if(!RE4DC_MEMBER_TEST(re4dc_source_world_pool(info,2),34) || !RE4DC_MEMBER_TEST((info->be_flag&0x201)==1,35) ||
       !RE4DC_MEMBER_TEST(info->invisible_factor==1.f,36) || !RE4DC_MEMBER_TEST(info->color[3]==255,37) ||
       !RE4DC_MEMBER_TEST(!info->pList,38) || !RE4DC_MEMBER_TEST(info->pData==data,39) ||
       !RE4DC_MEMBER_TEST(sourceWorldRange(data,sizeof(ModelData),alignof(ModelData)),40) ||
       !RE4DC_MEMBER_TEST(info->be_flag&8,41) || !RE4DC_MEMBER_TEST(!(info->be_flag&2),42) ||
       !RE4DC_MEMBER_TEST(!data->shapeOfs,43) || !RE4DC_MEMBER_TEST(data->nParts==1,44) ||
       !RE4DC_MEMBER_TEST(model->nParts==1,45) || !RE4DC_MEMBER_TEST(sourceWorldRange(data->pHead,sizeof(ModelDataHead)),46))return 0;
    // This first candidate covers unchanged one-joint room meshes only. An
    // animated gate, a changed hierarchy or an added model stays source-owned.
    const auto* part=model->pList;const auto& rest=*data->pHead;
    if(!RE4DC_MEMBER_TEST(re4dc_source_world_pool(part,3),47) || !RE4DC_MEMBER_TEST((part->be_flag&0x201)==1,48) ||
       !RE4DC_MEMBER_TEST(!part->pList,49) || !RE4DC_MEMBER_TEST(part->pParent==model,50) ||
       !RE4DC_MEMBER_TEST(rest.parentNo==0xff,51) || !RE4DC_MEMBER_TEST(sourceWorldVec(part->pos,rest.center),52) ||
       !RE4DC_MEMBER_TEST(part->ang.x==0.f,53) || !RE4DC_MEMBER_TEST(part->ang.y==0.f,54) || !RE4DC_MEMBER_TEST(part->ang.z==0.f,55) ||
       !RE4DC_MEMBER_TEST(part->scale.x==1.f,56) || !RE4DC_MEMBER_TEST(part->scale.y==1.f,57) || !RE4DC_MEMBER_TEST(part->scale.z==1.f,58))return 0;
    *index=found;return 1;
}
#undef RE4DC_MEMBER_TEST
extern "C" int re4dc_scroll_source_probe(cModel* model,unsigned* serial,unsigned* work) {
    // Other ModelRender callbacks can share these OTs. Establish their source
    // pool publication before even inspecting kind/visibility; never nominate
    // a raw callback payload merely because it points somewhere in RAM.
    if(!serial || !work ||
       (!re4dc_source_world_pool(model,0) && !re4dc_source_world_pool(model,1))){
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
        sourceWorldMemberField=60;
#endif
        return -1;
    }
    if((model->be_flag&0x201)!=1){
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
        sourceWorldMemberField=61;
#endif
        return -1;
    }
    if(model->kindid!=2 || model->invisible_factor*model->invisible_factor2==0.f)return 0;
    const unsigned current=model->serial;
    if(!re4dc_scroll_source_member(model,current,work))return -1;
    *serial=current;return 1;
}

#if RE4DC_PS2_WORLD_TRANSITION_OWNER
extern "C" unsigned re4dc_scroll_source_member_field(){return sourceWorldMemberField;}
// Original r200 authored group qualification and bounded publication witnesses.
// The raw source signature is checked before relocation. Only metadata is kept;
// no source model, material, texture or geometry array is copied.
#include "re4dc_platform.h"
#include "source_world_memory.inc"
#include "source_world_r200_profile.h"
#include "tpl.h"
namespace {
namespace r200p=source_world_r200_profile;
struct R200ScrollWitness { cModel* model; cModelInfo* info; cParts* part; unsigned serial,hash; };
R200ScrollWitness r200ScrollWitness[r200p::works]{};
cSmd* r200Smd;
cSmx* r200Smx;
unsigned r200ScrollGeneration,r200SmdHeaderHash;
bool r200RawQualified,r200ScrollPublished;
extern "C" int re4dc_room4_state(unsigned*,unsigned*,unsigned*,unsigned*,unsigned*);
extern "C" int re4dc_model_owned_source(const void*,unsigned);
unsigned r200RoomGeneration() {
    unsigned g=0,c,b,s,r;return re4dc_room4_state(&g,&c,&b,&s,&r)?g:0;
}
bool r200Range(const void* p,unsigned bytes,unsigned alignment=4) {
    return p && bytes && reinterpret_cast<unsigned long>(p)%alignment==0 &&
        re4dc_model_owned_source(p,bytes)!=0;
}
unsigned r200Hash(const void* ptr,unsigned bytes,unsigned h=2166136261U) {
    const auto* p=static_cast<const unsigned char*>(ptr);
    while(bytes--)h=(h^*p++)*16777619U;
    return h;
}
template<class T> void r200HashValue(unsigned& h,const T& value) { h=r200Hash(&value,sizeof(value),h); }
bool r200Vec(const Vec& a,const Vec& b){return a.x==b.x && a.y==b.y && a.z==b.z;}
bool r200Phase(float p){return p==p && p>=-3.402823466e38F && p<=3.402823466e38F;}
void sourceWorldR200ScrollClear() {
    r200Smd=nullptr;r200Smx=nullptr;r200ScrollGeneration=0;
    r200RawQualified=false;r200ScrollPublished=false;r200SmdHeaderHash=0;
    for(auto& w:r200ScrollWitness)w={};
}
void sourceWorldR200Qualify() {
    sourceWorldR200ScrollClear();
    if(!pG || G_ROOM_ID!=r200p::room || nScrWork!=int(r200p::works) ||
       !r200Range(pSmd,r200p::smd_bytes,alignof(cSmd)) ||
       !r200Range(pSmx,r200p::smx_bytes,alignof(cSmx)) ||
       pSmd->Version!=0x40 || pSmd->Flag || pSmd->nModel!=r200p::works || pSmx->nWork!=54 ||
       r200Hash(pSmd,r200p::smd_bytes)!=r200p::smd_fnv ||
       r200Hash(pSmx,r200p::smx_bytes)!=r200p::smx_fnv)return;
    const unsigned generation=r200RoomGeneration();if(!generation)return;
    r200Smd=pSmd;r200Smx=pSmx;r200ScrollGeneration=generation;
    r200SmdHeaderHash=r200Hash(pSmd,16);r200RawQualified=true;
}
bool r200ScrollBase(bool deep) {
    return r200RawQualified && pG && G_ROOM_ID==r200p::room &&
        r200ScrollGeneration && r200RoomGeneration()==r200ScrollGeneration &&
        pSmd==r200Smd && pSmx==r200Smx && nScrWork==int(r200p::works) &&
        r200Range(pSmd,0x10+r200p::works*sizeof(SmdWork),alignof(cSmd)) &&
        pSmd->Version==0x40 && !pSmd->Flag && pSmd->nModel==r200p::works &&
        r200Hash(pSmd,16)==r200SmdHeaderHash &&
        sourceWorldAllocated(scrTbl,r200p::works*sizeof(cObj*),true) &&
        (!deep || (r200Range(pSmx,r200p::smx_bytes,alignof(cSmx)) &&
          r200Hash(pSmx,r200p::smx_bytes)==r200p::smx_fnv &&
          r200Hash(pSmd->work,r200p::works*sizeof(SmdWork))==r200p::works_fnv));
}
bool r200Texture(TEXPalette* palette,unsigned id,unsigned& hash) {
    if(!r200Range(palette,sizeof(TEXPalette),alignof(TEXPalette)) ||
       !palette->numDescriptors || palette->numDescriptors>1024 || id>=palette->numDescriptors ||
       !r200Range(palette->descriptorArray,palette->numDescriptors*sizeof(TEXDescriptor),alignof(TEXDescriptor)))return false;
    r200HashValue(hash,*palette);
    const auto& d=palette->descriptorArray[id];r200HashValue(hash,d);
    if(!r200Range(d.textureHeader,sizeof(TEXHeader),alignof(TEXHeader)))return false;
    r200HashValue(hash,*d.textureHeader);
    if(d.CLUTHeader) {
        if(!r200Range(d.CLUTHeader,sizeof(CLUTHeader),alignof(CLUTHeader)))return false;
        r200HashValue(hash,*d.CLUTHeader);
    }
    return true;
}
bool r200MaterialTexture(const cModelInfo* info,unsigned id,unsigned& hash) {
    auto* palette=static_cast<TEXPalette*>(info->tpl_addr);
    if(!r200Range(palette,sizeof(TEXPalette),alignof(TEXPalette)))return false;
    if(id<palette->numDescriptors)return r200Texture(palette,id,hash);
    id-=palette->numDescriptors;
    return id<info->nAddTex && r200Texture(info->pAddTpl,id,hash);
}
#if RE4DC_TRANSITION_GATE_DIAG
unsigned r200FpGroupPub[r200p::works][10],r200FpGroupCur[10],r200FpGroup;
#define R200_GROUP(n) (r200FpGroup=(n))
unsigned r200FpFail;
#define R200_FAIL do{r200FpFail=__LINE__;return false;}while(0)
#else
#define R200_FAIL return false
#define R200_GROUP(n) ((void)0)
#endif
void r200Concat(const float* a,const float* b,float* out){
    for(unsigned r=0;r<3;++r)for(unsigned c=0;c<4;++c)
        out[4*r+c]=a[4*r]*b[c]+a[4*r+1]*b[4+c]+a[4*r+2]*b[8+c]+(c==3?a[4*r+3]:0.0f);
}
bool r200Inverse(const float* m,float* out){
    const float a=m[0],b=m[1],c=m[2],d=m[4],e=m[5],f=m[6],g=m[8],h=m[9],i=m[10];
    const float A=e*i-f*h,B=f*g-d*i,C=d*h-e*g,det=a*A+b*B+c*C;
    if(!(det==det) || (det<1e-12f && det>-1e-12f))return false;
    const float s=1.0f/det;
    const float r[9]={A*s,(c*h-b*i)*s,(b*f-c*e)*s,B*s,(a*i-c*g)*s,(c*d-a*f)*s,C*s,(b*g-a*h)*s,(a*e-b*d)*s};
    for(unsigned row=0;row<3;++row){
        out[4*row]=r[3*row];out[4*row+1]=r[3*row+1];out[4*row+2]=r[3*row+2];
        out[4*row+3]=-(r[3*row]*m[3]+r[3*row+1]*m[7]+r[3*row+2]*m[11]);
    }
    return true;
}
// The part's world matrix with ang 0 (scale 1, checked): model mat * T(part pos).
void r200PartRest(const cModel* model,const cParts* part,float* rest){
    const float t[12]={1,0,0,part->pos.x, 0,1,0,part->pos.y, 0,0,1,part->pos.z};
    r200Concat(&model->mat[0][0],t,rest);
}
bool r200ScrollFingerprint(unsigned work,cModel* model,unsigned& hash) {
    if(work>=r200p::works || !re4dc_source_world_pool(model,0))R200_FAIL;
    const auto& w=pSmd->work[work];const auto& witness=r200ScrollWitness[work];
    if(w.id==0xff || w.binNo==0xff || (w.flags&0x10) || w.motNo!=0xff ||
       witness.model!=model || scrTbl[work]!=model || !witness.serial || model->serial!=witness.serial ||
       model->kindid!=2 || model->type || (model->be_flag&0x207)!=7 ||
       static_cast<cObj*>(model)->blk!=-1 || model->invisible_factor!=1.f || model->invisible_factor2!=1.f ||
       model->pMotion || model->pTexChg || model->Shader_type || model->nParts!=1 ||
       !r200Vec(model->pos,w.pos) || !r200Vec(model->ang,w.rot) || !r200Vec(model->scale,w.scale))R200_FAIL;
    if(pSmd->BinTblOfs>r200p::smd_bytes ||
       (unsigned(w.binNo)+1U)*sizeof(u32)>r200p::smd_bytes-pSmd->BinTblOfs)R200_FAIL;
    const auto* table=reinterpret_cast<const u32*>(reinterpret_cast<unsigned long>(pSmd)+pSmd->BinTblOfs);
    if(!r200Range(table,(unsigned(w.binNo)+1U)*sizeof(u32)) || table[w.binNo]>r200p::smd_bytes)R200_FAIL;
    const auto* data=reinterpret_cast<const ModelData*>(reinterpret_cast<unsigned long>(table)+table[w.binNo]);
    const auto* info=model->pModelInfo;const auto* part=model->pList;
    if(info!=witness.info || part!=witness.part || !re4dc_source_world_pool(info,2) ||
       !re4dc_source_world_pool(part,3) || (info->be_flag&0x201)!=1 || !(info->be_flag&8) ||
       (info->be_flag&2) || info->pData!=data || info->pList || info->pShape ||
       info->invisible_factor!=1.f || info->color[3]!=255 || info->pTexAnim || info->texBlendTbl ||
       info->flagsDC!=((work==10 || work==16)?1:0) || !r200Phase(info->uvU) || !r200Phase(info->uvV) ||
       (work!=10 && work!=16 && (info->uvU!=0.f || info->uvV!=0.f)) ||
       !r200Range(data,sizeof(ModelData),alignof(ModelData)) || data->shapeOfs || data->nParts!=1 ||
       !data->displist_num || data->displist_num>1024 || !r200Range(data->pHead,sizeof(ModelDataHead)) ||
       (part->be_flag&0x201)!=1 || part->pList || part->pParent!=model || data->pHead->parentNo!=0xff ||
       !r200Vec(part->pos,data->pHead->center) || !r200Phase(part->ang.x) || part->ang.y!=0.f || part->ang.z!=0.f ||
       part->scale.x!=1.f || part->scale.y!=1.f || part->scale.z!=1.f)R200_FAIL;
    // Authored OT role, blend, depth/cull, material and bind matrices must remain.
    // UV phases alone are live and are sampled from ids16/10 at their exact color callbacks.
    hash=2166136261U;
#if RE4DC_TRANSITION_GATE_DIAG
    for(auto& g:r200FpGroupCur)g=2166136261U;
#define R200_HASH(value) (r200HashValue(hash,value),r200HashValue(r200FpGroupCur[r200FpGroup],value))
#else
#define R200_HASH(value) r200HashValue(hash,value)
#endif
    R200_GROUP(0);
    // Only the checked flag bits: a swinging part's model sets other be_flag bits as it moves (r200 works 8 / 9).
    {const unsigned mb=unsigned(model->be_flag)&0x207U,ib=unsigned(info->be_flag)&0x20bU;R200_HASH(mb);R200_HASH(ib);}
#if RE4DC_TRANSITION_GATE_DIAG
    if(work==8 || work==9 || work==0){static unsigned bl;if(bl<12){++bl;re4dc_log("TGD flags work=%u model=%x info=%x\n",work,unsigned(model->be_flag),unsigned(info->be_flag));}}
#endif
    R200_GROUP(1);R200_HASH(model->pParent);R200_HASH(model->mat);R200_HASH(model->l_mat);
    R200_GROUP(2);R200_HASH(model->ot_type);R200_HASH(model->z_mode);R200_HASH(model->CullMode);
    R200_HASH(model->alpha_omit);R200_HASH(model->TevScaleGroup);
    R200_GROUP(3);R200_HASH(model->AddAmb_r);R200_HASH(model->AddAmb_g);R200_HASH(model->AddAmb_b);
    R200_HASH(model->LightInfo.SelectMask);R200_GROUP(4);
    // A part may swing about X (r200 works 8 / 9, the pair opened on the 2-3 -> 3-1 frame; GC draws it rotated):
    // its live mat / l_mat / lt_inv_mat follow ang.x, so the authored rest pose (model mat * T(part pos)) is hashed.
    {float rest[12];r200PartRest(model,part,rest);R200_HASH(rest);}
    R200_HASH(part->addRot);R200_HASH(part->motParts.flags);
    R200_GROUP(5);R200_HASH(info->tpl_addr);R200_HASH(info->pAddTpl);R200_HASH(info->nAddTex);
    R200_GROUP(6);R200_HASH(info->mat);R200_GROUP(7);R200_HASH(info->color);R200_HASH(info->color2);
    R200_GROUP(8);R200_HASH(info->blend_mode);R200_HASH(info->blendRatio);R200_HASH(info->blendType);
    R200_HASH(info->anm_no);R200_HASH(info->uvScrollU);R200_HASH(info->uvScrollV);
    R200_GROUP(9);R200_HASH(*data);R200_HASH(*data->pHead);
    const ModelPart* material=data->pParts;
    for(unsigned i=0;i<data->displist_num;++i) {
        if(!r200Range(material,sizeof(ModelPart),alignof(ModelPart)) ||
           material->size>r200p::smd_bytes ||
           !r200Range(material,sizeof(ModelPart)+material->size,alignof(ModelPart)))R200_FAIL;
        R200_HASH(*material);
        if(!r200MaterialTexture(info,material->texId,hash) ||
           ((material->flags&1) && !r200MaterialTexture(info,material->bumpTex,hash)) ||
           ((material->flags&4) && !r200MaterialTexture(info,material->alphaTex,hash)) ||
           ((material->flags&16) && !r200MaterialTexture(info,material->specTexOrg,hash)))R200_FAIL;
        material=reinterpret_cast<const ModelPart*>(reinterpret_cast<unsigned long>(material)+sizeof(ModelPart)+material->size);
    }
#undef R200_HASH
    return true;
}
void sourceWorldR200ScrollBind(unsigned work,cObj* object) {
    r200ScrollPublished=false;
    if(!r200ScrollBase(false) || work>=r200p::works || !re4dc_source_world_pool(object,0) ||
       (object->be_flag&0x201)!=1 || !object->serial)return;
    r200ScrollWitness[work]={object,object->pModelInfo,object->pList,object->serial,0};
}
void sourceWorldR200ScrollPublish() {
    r200ScrollPublished=false;if(!r200ScrollBase(true))return;
    for(unsigned i=0;i<r200p::works;++i) {
        for(unsigned j=0;j<i;++j)if(scrTbl[i]==scrTbl[j])return;
        unsigned hash=0;if(!r200ScrollFingerprint(i,scrTbl[i],hash))return;
        r200ScrollWitness[i].hash=hash;
#if RE4DC_TRANSITION_GATE_DIAG
        for(unsigned g=0;g<10;++g)r200FpGroupPub[i][g]=r200FpGroupCur[g];
#endif
    }
    r200ScrollPublished=true;
}
}
#if RE4DC_TRANSITION_GATE_DIAG
#define R200_SFAIL(code) do{static unsigned sl;if(sl<8){++sl;re4dc_log("TGD scroll_storage fail=%d\n",int(code));}}while(0)
#else
#define R200_SFAIL(code) ((void)0)
#endif
extern "C" int re4dc_r200_scroll_storage_current() {
    // Address/owner proof survives a safe admission decline. Do not require
    // pose/material equality: ordinary live source rendering may still proceed.
    if(!r200ScrollPublished || !r200ScrollBase(false) ||
       !r200Range(pSmd,r200p::smd_bytes,alignof(cSmd)) ||
       !r200Range(pSmx,r200p::smx_bytes,alignof(cSmx))){R200_SFAIL(1000+int(r200ScrollPublished)*100+int(r200ScrollBase(false))*10);return 0;}
    for(unsigned i=0;i<r200p::works;++i){
        const auto& w=r200ScrollWitness[i];
        if(scrTbl[i]!=w.model || !re4dc_source_world_pool(w.model,0) ||
           w.model->serial!=w.serial || w.model->pModelInfo!=w.info || w.model->pList!=w.part ||
           !re4dc_source_world_pool(w.info,2) || !re4dc_source_world_pool(w.part,3)){R200_SFAIL(2000+int(i));return 0;}
        const auto* data=w.info->pData;
        if(w.info->pList || w.part->pList || !r200Range(data,sizeof(ModelData),alignof(ModelData)) ||
           !r200Range(data->pHead,sizeof(ModelDataHead)) || !data->displist_num || data->displist_num>1024 ||
           !r200Range(data->pParts,data->displist_num*sizeof(ModelPart),alignof(ModelPart))){R200_SFAIL(3000+int(i));return 0;}
        unsigned ignored=2166136261U;
        // ModelPart records are variable length (sizeof(ModelPart)+size), walked as r200ScrollFingerprint does;
        // indexing pParts[j] read work 6's later records at the wrong address (lane ch3found16 2026-10-17).
        const ModelPart* material=data->pParts;
        for(unsigned j=0;j<data->displist_num;++j){
            if(!r200Range(material,sizeof(ModelPart),alignof(ModelPart)) || material->size>r200p::smd_bytes ||
               !r200Range(material,sizeof(ModelPart)+material->size,alignof(ModelPart)) ||
               !r200MaterialTexture(w.info,material->texId,ignored)){R200_SFAIL(4000+int(i));return 0;}
            material=reinterpret_cast<const ModelPart*>(reinterpret_cast<unsigned long>(material)+sizeof(ModelPart)+material->size);
        }
    }
    return 1;
}
extern "C" int re4dc_r200_scroll_group() {
    if(!r200ScrollPublished || !r200ScrollBase(true))return 0;
    for(unsigned i=0;i<r200p::works;++i) {
        for(unsigned j=0;j<i;++j)if(scrTbl[i]==scrTbl[j])return 0;
        unsigned hash=0;if(!r200ScrollFingerprint(i,scrTbl[i],hash) || hash!=r200ScrollWitness[i].hash)return 0;
    }
    return 1;
}
#if RE4DC_TRANSITION_GATE_DIAG
extern "C" void re4dc_r200_scroll_diag() {
    unsigned bad=0,first=~0U;
    if(r200ScrollPublished && r200ScrollBase(true))for(unsigned i=0;i<r200p::works;++i){
        unsigned hash=0;const bool ok=r200ScrollFingerprint(i,scrTbl[i],hash);
        if(!ok || hash!=r200ScrollWitness[i].hash){
            ++bad;if(first==~0U)first=i;
            unsigned groups=0;if(ok)for(unsigned g=0;g<10;++g)if(r200FpGroupCur[g]!=r200FpGroupPub[i][g])groups|=1U<<g;
            // groups: 0 be_flag 1 model mat/l_mat/parent 2 ot/z/cull/alpha/tev 3 AddAmb/light mask 4 part mats/addRot
            // 5 tpl 6 info->mat 7 info->color/color2 8 blend/anm/uv-scroll 9 data/head/materials/textures
            if(!ok){
                if(0){cModel* m=scrTbl[i];const auto& w=pSmd->work[i];
                const cModelInfo* in=m?m->pModelInfo:nullptr;
                re4dc_log("TGD scroll work=%u model=%p wit=%p serial=%u/%u kind=%u type=%u be=%x blk=%d inv=%d,%d mot=%p texchg=%p shader=%u nparts=%u pos=%d ang=%d scale=%d wflags=%x id=%u bin=%u mot=%u info=%p/%p ibe=%x iinv=%d alpha=%u dc=%u uv=%d,%d texanim=%p blendtbl=%p\n",
                    i,(void*)m,(void*)r200ScrollWitness[i].model,m?m->serial:0U,r200ScrollWitness[i].serial,m?unsigned(m->kindid):0U,m?unsigned(m->type):0U,
                    m?unsigned(m->be_flag):0U,m?int(static_cast<cObj*>(m)->blk):0,m?int(m->invisible_factor*1000):0,m?int(m->invisible_factor2*1000):0,
                    m?(void*)m->pMotion:nullptr,m?(void*)m->pTexChg:nullptr,m?unsigned(m->Shader_type):0U,m?unsigned(m->nParts):0U,
                    m?int(r200Vec(m->pos,w.pos)):-1,m?int(r200Vec(m->ang,w.rot)):-1,m?int(r200Vec(m->scale,w.scale)):-1,
                    unsigned(w.flags),unsigned(w.id),unsigned(w.binNo),unsigned(w.motNo),(void*)in,(void*)r200ScrollWitness[i].info,
                    in?unsigned(in->be_flag):0U,in?int(in->invisible_factor*1000):0,in?unsigned(in->color[3]):0U,in?unsigned(in->flagsDC):0U,
                    in?int(in->uvU*1000):0,in?int(in->uvV*1000):0,in?(void*)in->pTexAnim:nullptr,in?(void*)in->texBlendTbl:nullptr);}
            }
            if(!ok && r200FpFail>=225){
                cModel* m=scrTbl[i];const auto& w=pSmd->work[i];
                const auto* table=reinterpret_cast<const u32*>(reinterpret_cast<unsigned long>(pSmd)+pSmd->BinTblOfs);
                const auto* data=reinterpret_cast<const ModelData*>(reinterpret_cast<unsigned long>(table)+table[w.binNo]);
                const cModelInfo* in=m->pModelInfo;const cParts* pa=m->pList;
                re4dc_log("TGD part work=%u ipool=%d ppool=%d pdata=%d ilist=%p ishape=%p texanim=%p blendtbl=%p\n",i,
                    re4dc_source_world_pool((void*)in,2),re4dc_source_world_pool((void*)pa,3),int(in->pData==data),(void*)in->pList,(void*)in->pShape,(void*)in->pTexAnim,(void*)in->texBlendTbl);
                re4dc_log("TGD part2 work=%u shape=%u nparts=%u displist=%u pbe=%x plist=%p par=%d hparent=%u center=%d ang=%d,%d,%d scale=%d,%d,%d\n",i,
                    unsigned(data->shapeOfs),unsigned(data->nParts),unsigned(data->displist_num),unsigned(pa->be_flag),(void*)pa->pList,int(pa->pParent==m),
                    unsigned(data->pHead->parentNo),int(r200Vec(pa->pos,data->pHead->center)),int(pa->ang.x*1000),int(pa->ang.y*1000),int(pa->ang.z*1000),
                    int(pa->scale.x*1000),int(pa->scale.y*1000),int(pa->scale.z*1000));
            }
            re4dc_log("TGD scroll work=%u fail_line=%u ok=%d groups=%03x\n",i,r200FpFail,ok,groups);
        }
    }
    const bool smd=pSmd && r200Range(pSmd,r200p::smd_bytes,alignof(cSmd)),smx=pSmx && r200Range(pSmx,r200p::smx_bytes,alignof(cSmx));
    re4dc_log("TGD scroll raw=%d published=%d base=%d deep=%d works=%d/%u fp_bad=%u first=%d smd=%08x/%08x smx=%08x/%08x works_fnv=%08x/%08x\n",
        r200RawQualified,r200ScrollPublished,r200ScrollBase(false),r200ScrollBase(true),nScrWork,r200p::works,bad,int(first),
        smd?r200Hash(pSmd,r200p::smd_bytes):0U,r200p::smd_fnv,smx?r200Hash(pSmx,r200p::smx_bytes):0U,r200p::smx_fnv,
        pSmd?r200Hash(pSmd->work,r200p::works*sizeof(SmdWork)):0U,r200p::works_fnv);
}
#endif
// World-space delta of a published work whose part swings about X (live part mat * inverse(rest)); 0 = draw baked.
extern "C" int re4dc_r200_part_delta(unsigned work,float* out) {
#ifdef RE4DC_TGD_NO_DELTA
    return 0;
#endif
    if(!out || !r200ScrollPublished || work>=r200p::works || !r200ScrollBase(false))return 0;
    cModel* model=r200ScrollWitness[work].model;
    if(!model || scrTbl[work]!=model || model->serial!=r200ScrollWitness[work].serial)return 0;
    const cParts* part=model->pList;
    if(!part || part!=r200ScrollWitness[work].part || part->ang.x==0.f || !r200Phase(part->ang.x))return 0;
    float rest[12],inv[12];r200PartRest(model,part,rest);
    if(!r200Inverse(rest,inv))return 0;
    r200Concat(&part->mat[0][0],inv,out);
#if RE4DC_TRANSITION_GATE_DIAG
    static unsigned lines;
    if(lines<4){++lines;re4dc_log("TGD delta work=%u ang=%d model_t=%d,%d,%d delta_r1=%d,%d,%d,%d\n",work,int(part->ang.x*1000),
        int(model->mat[0][3]),int(model->mat[1][3]),int(model->mat[2][3]),int(out[4]*1000),int(out[5]*1000),int(out[6]*1000),int(out[7]));}
#endif
    return 1;
}
extern "C" int re4dc_r200_scroll_member(cModel* model,unsigned serial,unsigned work,float* uv) {
    if(!r200ScrollPublished || !r200ScrollBase(false) || work>=r200p::works ||
       r200ScrollWitness[work].serial!=serial)return 0;
    unsigned hash=0;if(!r200ScrollFingerprint(work,model,hash) || hash!=r200ScrollWitness[work].hash)return 0;
    if(uv){uv[0]=model->pModelInfo->uvU;uv[1]=model->pModelInfo->uvV;}
    return 1;
}
extern "C" int re4dc_r200_scroll_probe(cModel* model,unsigned* serial,unsigned* work) {
    if(!serial || !work || !r200ScrollPublished || !r200ScrollBase(false))return -1;
    // Pointer comparison first; other model payloads require a live pool slot.
    for(unsigned i=0;i<r200p::works;++i)if(r200ScrollWitness[i].model==model) {
        *work=i;*serial=r200ScrollWitness[i].serial;
        return re4dc_r200_scroll_member(model,*serial,i,nullptr)?1:-1;
    }
    if(!re4dc_source_world_pool(model,0) && !re4dc_source_world_pool(model,1))return -1;
    return (model->be_flag&0x207)!=7 || model->kindid==2?-1:0;
}
extern "C" int re4dc_r200_scroll_pointers(cModel** out,unsigned count) {
    if(!out || count!=r200p::works || !r200ScrollPublished || !r200ScrollBase(false))return 0;
    for(unsigned i=0;i<count;++i)out[i]=r200ScrollWitness[i].model;
    return 1;
}
extern "C" int re4dc_r200_scroll_pointer(const cModel* model) {
    // No dereference: keeps retired source addresses suppressed after failure.
    for(const auto& witness:r200ScrollWitness)if(witness.model==model)return 1;
    return 0;
}

extern "C" int re4dc_scroll_source_transition_member(cModel* model,unsigned serial,unsigned* work,unsigned* reason) {
    if(reason)*reason=0;
    unsigned found=~0U,current=0;
    if(re4dc_r200_scroll_probe(model,&current,&found)!=1 || current!=serial || !work){
        if(reason)*reason=101;return 0;
    }
    *work=found;return 1;
}
#endif
