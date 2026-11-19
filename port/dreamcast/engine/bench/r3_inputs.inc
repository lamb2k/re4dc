// Snapshot after the scheduler has advanced the pose. No camera tests or draw lists.
static void m1r3_snapshot_model(cModel* model, unsigned role, unsigned index) {
    struct Pose { unsigned role,index,id,bone; float world[12]; } pose =
        {role,index,model->id,0,{}};
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
