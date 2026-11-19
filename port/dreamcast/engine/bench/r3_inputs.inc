// Snapshot after the scheduler has advanced the pose. No camera tests or draw lists.
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
}
static void m1r3_snapshot_inputs() {
    if(pPL) m1r3_snapshot_model(pPL,0,0);
    unsigned index=0;
    for(cEm* e=EmMgr.pAlive;e;e=(cEm*)e->pNext,++index)
        if((e->be_flag&0x201)==1 && e->id>=0x10 && e->id<=0x20)
            m1r3_snapshot_model(e,1,index);
    for(cLight* l=LightMgr.pAlive;l;l=(cLight*)l->pNext) {
        struct { unsigned flags,type,kind,spot; Vec world,normal; float radius,intensity;
                 GXColor color; } lamp={l->be_flag,l->Type,l->Kind,l->xD,l->World,
                                       l->normal,l->Radius,l->Intensity,l->DispCol};
        m1r3::append(m1r3::SourceLight,&lamp,sizeof(lamp));
    }
    const cLightEnv* env=LightMgr.getEnvPtr();
    struct { GXColor scene,actors,effects; LightFog fog; } room=
        {env->AmbientScr,env->AmbientEm,env->AmbientEsp,env->Fog};
    m1r3::append(m1r3::Environment,&room,sizeof(room));
    struct { unsigned life,maximum,weapon,bullet; } hud=
        {pG->pl_life,pG->pl_life_max,pG->weapon_no,pG->bullet_type};
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
