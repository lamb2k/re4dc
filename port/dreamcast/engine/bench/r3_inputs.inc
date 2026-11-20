// Snapshot after the scheduler has advanced the pose. No camera tests or draw lists.
extern u8 gxCsScale[];
#include "pl_sub.h"
// eng-e0b: the inputs of the source's model lighting rule (cLightMgr::setModel2 + LightSetModel), so the engine
// can apply the rule itself: the model's light volume and masks, material colour, TEV scale and added ambient.
// picked[] is the game's own light pick from its last draw, kept only to test the engine's selection against.
static void m1r3_snapshot_light(cModel* model, unsigned role, unsigned index) {
    struct ModelLight { unsigned role,index,model,info,select; Vec offset,size; unsigned color,tev,addamb,picked[2],status; } r={};
    const cLightInfo& li=model->LightInfo;
    r.role=role;r.index=index;r.model=(unsigned)(uintptr_t)model;
    unsigned flags=((model->be_flag&0x8000)?1u:0u)|((model->be_flag&8)?2u:0u)|((li.Flag&4)?8u:0u);
    if(model->pModelInfo && model->pModelInfo->pData && (model->pModelInfo->pData->flags&0x40000000))flags|=4;
    r.info=(unsigned)li.Flag|((unsigned)(u8)li.PartsNo<<8)|((unsigned)li.EnableMask<<16)|(flags<<24);
    r.select=li.SelectMask;r.offset=li.Offset;r.size=li.Size;
    if(model->pModelInfo)memcpy(&r.color,model->pModelInfo->color,4);
    r.tev=(unsigned)model->TevScaleGroup|((model->TevScaleGroup<4?(unsigned)gxCsScale[model->TevScaleGroup]:255u)<<8);
    r.addamb=(unsigned)model->AddAmb_r|((unsigned)model->AddAmb_g<<8)|((unsigned)model->AddAmb_b<<16);
    for(unsigned i=0;i<8;i++){
        unsigned k=255;const cLight* l=li.pLight[i];
        if(l && LightMgr.size)k=(unsigned)(((const u8*)l-(const u8*)LightMgr.pArray)/LightMgr.size);
        r.picked[i>>2]|=(k&255)<<(8*(i&3));
    }
    r.status=pG->Status_flg[1];
    m1r3::append(m1r3::ModelLight,&r,sizeof(r));
}
static void m1r3_snapshot_model(cModel* model, unsigned role, unsigned index) {
    struct Pose { unsigned role,index,id,bone; float world[12]; } pose =
        {role,index,(unsigned)model->id|((unsigned)model->type<<8),0,{}};
    memcpy(pose.world, model->mat, sizeof(pose.world));
    m1r3::append(m1r3::Actor,&pose,sizeof(pose));
    cParts* part=model->pList;
    for(unsigned j=0; part && j<model->nParts; ++j,part=part->pList) {
        pose.bone=j+1;
        memcpy(pose.world,part->mat,sizeof(pose.world));
        m1r3::append(m1r3::Actor,&pose,sizeof(pose));
    }
    struct { unsigned role,index; Vec feet; } caster={role,index,model->pos};
    m1r3::append(m1r3::Caster,&caster,sizeof(caster));
    m1r3_snapshot_light(model,role,index);
}
static void m1r3_snapshot_inputs() {
    if(pPL) m1r3_snapshot_model(pPL,0,0);
    unsigned index=0;
    for(cEm* e=EmMgr.pAlive;e;e=(cEm*)e->pNext,++index)
        if((e->be_flag&0x201)==1 && e->id>=0x10 && e->id<=0x20)
            m1r3_snapshot_model(e,1,index);
        // eng-boss: in the El Gigante arena (r119) every other live enemy-table model too (the giant 0x2B, the
        // trees 0x43, the dog 0x29), role 3, index = the model's address (the bake finds its source model by it)
        else if((e->be_flag&0x201)==1 && pG->room_id==0x119)
            m1r3_snapshot_model(e,3,(unsigned)(uintptr_t)e);
    for(cLight* l=LightMgr.pAlive;l;l=(cLight*)l->pNext) {
        // eng-e0b: + array index (setModel2 order and SelectMask bit), xF | Attribute | Priority | kind enabled,
        // spot cone A0 (parallel: flags) and fade A1, parent model
        struct { unsigned flags,type,kind,spot; Vec world,normal; float radius,intensity;
                 GXColor color; unsigned index,bits,a0; float a1; unsigned parent; } lamp={l->be_flag,l->Type,l->Kind,l->xD,l->World,
                                       l->normal,l->Radius,l->Intensity,l->DispCol,
                                       LightMgr.size?(unsigned)(((u8*)l-(u8*)LightMgr.pArray)/LightMgr.size):255u,
                                       (unsigned)l->xF|((unsigned)l->Attribute<<8)|((unsigned)l->Priority<<16)|((unsigned)(LightMgr.checkKind(l->Kind)?1:0)<<24),
                                       l->spot.flags,l->spot.A1,(unsigned)(uintptr_t)l->pParent};
        m1r3::append(m1r3::SourceLight,&lamp,sizeof(lamp));
    }
    const cLightEnv* env=LightMgr.getEnvPtr();
    struct { GXColor scene,actors,effects; LightFog fog; } room=
        {env->AmbientScr,env->AmbientEm,env->AmbientEsp,env->Fog};
    m1r3::append(m1r3::Environment,&room,sizeof(room));
    // eng-e0b: the fourth word is the stance, PlGetWeaponNo(): 0x10 while the knife is in hand (knife routine or
    // knife key), else the equipped weapon. The engine draws Leon's knife part from it.
    struct { unsigned life,maximum,weapon,stance; } hud=
        {pG->pl_life,pG->pl_life_max,pG->weapon_no,(unsigned)PlGetWeaponNo()};
    m1r3::append(m1r3::Hud,&hud,sizeof(hud));
}

static void m1r3_snapshot_widgets(){
    for(int i=0;i<IdSys.m_maxId;++i){
        const IdUnit& u=IdSys.pUnit[i];
        if(u.be_flag==0xff || !(u.be_flag&1))continue;
        struct Widget { unsigned identity,tree,shape,hidden,key[2],mask[2]; Vec pos,rot;
                        float width,height,rgba[4],uv[4]; } w={
           (unsigned)i|((unsigned)u.classNo<<8)|((unsigned)u.markNo<<16),
           (unsigned)(u.pParent?u.pParent-IdSys.pUnit:255)|((unsigned)u.levelNo<<8)|((unsigned)u.type<<16),
           (unsigned)u.vtxType|((unsigned)u.blend_type<<8)|((unsigned)u.be_flag<<16),
           IdSys.m_disp_off[u.classNo>>5]&(0x80000000u>>(u.classNo&31)),{}, {},
           u.pos,u.rot,u.sizeX,u.size_H,{u.col[0],u.col[1],u.col[2],u.col[3]},
           {u.u0,u.v0,u.u1,u.v1}};
        if(u.type!=1){
            TexWk* wk=IdGetTexWk(u.texId,1);
            if(wk && wk->pTpl && u.texNo<wk->pTpl->numDescriptors)
                m1r3::texture_key(TEXGet(wk->pTpl,u.texNo),w.key);
            if(u.tex_flag&1){
                wk=IdGetTexWk(u.maskId,1);
                if(wk && wk->pTpl && u.maskNo<wk->pTpl->numDescriptors)
                    m1r3::texture_key(TEXGet(wk->pTpl,u.maskNo),w.mask);
            }
        }
        m1r3::append(m1r3::Hud,&w,sizeof(w));
    }
}
