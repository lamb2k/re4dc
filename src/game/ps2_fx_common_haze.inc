// Default-off, render-owned adapter; see common recipes and source proof.
#include "ps2_fx_common_haze_recipes.h"
#include <stddef.h>
static ps2fx::CommonHazeClock s_common_haze[2];
static u8* s_common_pool;
static u32 s_common_frame;
static u16 s_common_room;
static unsigned s_common_generation,s_common_slots,s_common_accepted;
extern "C" int ESP_IsActive(cEsp*);
extern "C" int re4dc_room4_state(unsigned*,unsigned*,unsigned*,unsigned*,unsigned*);
static int Ps2fxCommonSignature(const cEsp* e,const Ps2fxCommonRow& r)
{
    return (e->m_Be_flg&1) && e->m_Id==0x15 && e->info.owner==0xd0 && e->info.Core_kind==r.kind &&
        static_cast<const cPs2fxEsp15*>(e)->m_Free.Range==r.gc_range &&
        e->m_Col_start_r==r.rgba[0] && e->m_Col_start_g==r.rgba[1] && e->m_Col_start_b==r.rgba[2];
}
static ps2fx::CommonHazeBinding Ps2fxCommonIdentity(const cEsp* e,unsigned row,unsigned first)
{
    const ps2fx::CommonHazeBinding id={s_common_generation,e->info.Call_no,e->info.Core_pEm,
        (u16)first,(u16)row,e->info.Core_flg,e->info.Core_kind,e->info.owner};
    return id;
}
static int Ps2fxCommonSource(cEsp* e,const Ps2fxCommonRow& r)
{
    // All qualified SST records use Parts_no 0xfe and Release_time 0.
    // EspSeqSet copies the timer verbatim and binds these particles to world.
    const Ps2fxEsp15Work& w=static_cast<cPs2fxEsp15*>(e)->m_Free;
    return ps2fx::population_source_matches(r.room,e->m_Life_max,e->m_Parts_no,e->m_Tool_flg,
               e->m_Tex_id,e->m_Type,e->parent==pEffParentWorld) &&
        !e->info.Core_pEm && (e->info.Core_flg==0x4001 || e->info.Core_flg==0x6001) && !e->m_pMod &&
        !e->m_Flg && e->m_Release_time==0 && !e->m_Blend_type && e->xA4==1 && e->xA5==4 && e->xA6==5 &&
        !e->m_Shimmer_type && !e->m_Shimmer_pow && !e->m_MaskTex_id && !e->m_Ptn_no && e->m_Anm_rate==0x20 &&
        e->m_Size_base_x==e->m_Size_base_y && e->m_Size_base_x>=r.gc_size-40.0f && e->m_Size_base_x<=r.gc_size+40.0f &&
        e->m_D_size_plus==.9900000095367432f && e->m_D_speed==1.0f &&
        e->m_Speed_plus.x==0 && e->m_Speed_plus.y==0 && e->m_Speed_plus.z==0 &&
        e->m_Ang.x==0 && e->m_Ang.y==0 && e->m_Ang_plus.x==0 && e->m_Ang_plus.y==0 &&
        e->m_Col_start_a==r.rgba[3] && e->m_Col_d_r==1 && e->m_Col_d_g==1 && e->m_Col_d_b==1 && e->m_Col_d_a==1 &&
        e->m_Col_max_cnt==r.color_max && !e->m_Col_start_cnt && !e->m_Pos_start_cnt && !e->m_Size_start_cnt &&
        e->m_Del_far==r.work[0]*10 && e->m_Del_near==r.work[1]*10 && w.Min_y==r.gc_min_y &&
        w.Del_ratio==1.0f-(f32)r.work[2]/100.0f && w.Room_del_frame==r.work[3] &&
        ESP_IsActive(e) && EspSpriteEligible(e);
}
// Read-only refusal evidence; admission continues to use the original predicates.
// Float observations are exact IEEE words, avoiding decimal rounding in logs.
static unsigned Ps2fxCommonBits(f32 value){unsigned bits;memcpy(&bits,&value,4);return bits;}
struct Ps2fxCommonRefusal {unsigned code,got,want,slot,age,mul,plus;};
static Ps2fxCommonRefusal Ps2fxCommonSourceRefusal(cEsp* e,const Ps2fxCommonRow& r)
{
    Ps2fxCommonRefusal d={};const Ps2fxEsp15Work& w=static_cast<cPs2fxEsp15*>(e)->m_Free;
#define PS2FX_COMMON_I(tag,actual,expected) if((actual)!=(expected)){d.code=tag;d.got=(unsigned)(actual);d.want=(unsigned)(expected);return d;}
#define PS2FX_COMMON_F(tag,actual,expected) if((actual)!=(expected)){d.code=tag;d.got=Ps2fxCommonBits(actual);d.want=Ps2fxCommonBits(expected);return d;}
    PS2FX_COMMON_I(1,e->m_Life_max,0);PS2FX_COMMON_I(2,e->m_Parts_no,0xfe);
    PS2FX_COMMON_I(3,e->m_Tool_flg,r.room==0x10f?0x80U:0U);
    PS2FX_COMMON_I(4,e->m_Tex_id,r.room==0x104 || r.room==0x10f?0x1eU:0x1fU);
    PS2FX_COMMON_I(5,e->m_Type,0);
    PS2FX_COMMON_I(6,(size_t)e->parent,(size_t)pEffParentWorld);PS2FX_COMMON_I(7,e->info.Core_pEm,0);
    if(e->info.Core_flg!=0x4001 && e->info.Core_flg!=0x6001){d.code=8;d.got=e->info.Core_flg;d.want=0x4001;return d;}
    PS2FX_COMMON_I(9,(size_t)e->m_pMod,0);PS2FX_COMMON_I(10,e->m_Flg,0);PS2FX_COMMON_I(11,e->m_Release_time,0);
    PS2FX_COMMON_I(12,e->m_Blend_type,0);PS2FX_COMMON_I(13,e->xA4,1);PS2FX_COMMON_I(14,e->xA5,4);PS2FX_COMMON_I(15,e->xA6,5);
    PS2FX_COMMON_I(16,e->m_Shimmer_type,0);PS2FX_COMMON_I(17,e->m_Shimmer_pow,0);PS2FX_COMMON_I(18,e->m_MaskTex_id,0);
    PS2FX_COMMON_I(19,e->m_Ptn_no,0);PS2FX_COMMON_I(20,e->m_Anm_rate,0x20);
    PS2FX_COMMON_F(21,e->m_Size_base_x,e->m_Size_base_y);
    if(!(e->m_Size_base_x>=r.gc_size-40.0f)){d.code=22;d.got=Ps2fxCommonBits(e->m_Size_base_x);d.want=Ps2fxCommonBits(r.gc_size-40.0f);return d;}
    if(!(e->m_Size_base_x<=r.gc_size+40.0f)){d.code=23;d.got=Ps2fxCommonBits(e->m_Size_base_x);d.want=Ps2fxCommonBits(r.gc_size+40.0f);return d;}
    PS2FX_COMMON_F(24,e->m_D_size_plus,.9900000095367432f);PS2FX_COMMON_F(25,e->m_D_speed,1.0f);
    PS2FX_COMMON_F(26,e->m_Speed_plus.x,0);PS2FX_COMMON_F(27,e->m_Speed_plus.y,0);PS2FX_COMMON_F(28,e->m_Speed_plus.z,0);
    PS2FX_COMMON_F(29,e->m_Ang.x,0);PS2FX_COMMON_F(30,e->m_Ang.y,0);PS2FX_COMMON_F(31,e->m_Ang_plus.x,0);PS2FX_COMMON_F(32,e->m_Ang_plus.y,0);
    PS2FX_COMMON_I(33,e->m_Col_start_a,r.rgba[3]);PS2FX_COMMON_F(34,e->m_Col_d_r,1);PS2FX_COMMON_F(35,e->m_Col_d_g,1);
    PS2FX_COMMON_F(36,e->m_Col_d_b,1);PS2FX_COMMON_F(37,e->m_Col_d_a,1);
    PS2FX_COMMON_I(38,e->m_Col_max_cnt,r.color_max);PS2FX_COMMON_I(39,e->m_Col_start_cnt,0);
    PS2FX_COMMON_I(40,e->m_Pos_start_cnt,0);PS2FX_COMMON_I(41,e->m_Size_start_cnt,0);
    PS2FX_COMMON_I(42,e->m_Del_far,r.work[0]*10);PS2FX_COMMON_I(43,e->m_Del_near,r.work[1]*10);PS2FX_COMMON_F(44,w.Min_y,r.gc_min_y);
    PS2FX_COMMON_F(45,w.Del_ratio,1.0f-(f32)r.work[2]/100.0f);PS2FX_COMMON_I(46,w.Room_del_frame,r.work[3]);
    PS2FX_COMMON_I(47,ESP_IsActive(e)!=0,1);PS2FX_COMMON_I(48,EspSpriteEligible(e)!=0,1);
#undef PS2FX_COMMON_I
#undef PS2FX_COMMON_F
    return d;
}
static Ps2fxCommonRefusal Ps2fxCommonGroupRefusal(cEsp* e,const Ps2fxCommonRow& r,
    const ps2fx::CommonHazeBinding& id,unsigned row,unsigned slot,unsigned count,unsigned age,f32 mul,f32 plus)
{
    Ps2fxCommonRefusal d=Ps2fxCommonSourceRefusal(e,r);
    if(!d.code){
        const ps2fx::CommonHazeBinding now=Ps2fxCommonIdentity(e,row,id.first_slot);
#define PS2FX_COMMON_G(tag,actual,expected) if(!d.code && (actual)!=(expected)){d.code=tag;d.got=(unsigned)(actual);d.want=(unsigned)(expected);}
        PS2FX_COMMON_G(49,now.generation,id.generation);PS2FX_COMMON_G(50,now.call,id.call);PS2FX_COMMON_G(51,now.core,id.core);
        PS2FX_COMMON_G(52,now.first_slot,id.first_slot);PS2FX_COMMON_G(53,now.recipe,id.recipe);PS2FX_COMMON_G(54,now.flags,id.flags);
        PS2FX_COMMON_G(55,now.kind,id.kind);PS2FX_COMMON_G(56,now.owner,id.owner);PS2FX_COMMON_G(57,e->m_Life_time,age);
        if(!d.code && e->m_Size_mul!=mul){d.code=58;d.got=Ps2fxCommonBits(e->m_Size_mul);d.want=Ps2fxCommonBits(mul);}
        if(!d.code && e->m_Size_plus!=plus){d.code=59;d.got=Ps2fxCommonBits(e->m_Size_plus);d.want=Ps2fxCommonBits(plus);}
        if(!d.code && count>r.count){d.code=60;d.got=count;d.want=r.count;}
#undef PS2FX_COMMON_G
    }
    if(!d.code)d.code=255; // Original predicate refused, diagnostic mirror did not identify it.
    d.slot=slot;d.age=e->m_Life_time;d.mul=Ps2fxCommonBits(e->m_Size_mul);d.plus=Ps2fxCommonBits(e->m_Size_plus);return d;
}
static void Ps2fxCommonRefusalLog(unsigned group,unsigned row,unsigned count,unsigned age,f32 mul,f32 plus,
                                 const Ps2fxCommonRefusal& failure,unsigned input_issues)
{
    struct Stamp {u8* pool;unsigned frame,generation,row;bool seen;};static Stamp stamp[2]={};
    if(group>=2)return;
    Stamp& last=stamp[group];
    if(last.seen && last.pool==s_common_pool && last.frame==s_common_frame &&
       last.generation==s_common_generation && last.row==row)return;
    last={s_common_pool,s_common_frame,s_common_generation,row,true};
    const Ps2fxCommonRow& r=kPs2CommonHaze[row];Ps2fxCommonRefusal d=failure;
    if(!d.code){d.slot=2048;d.age=age;d.mul=Ps2fxCommonBits(mul);d.plus=Ps2fxCommonBits(plus);
        if(input_issues){d.code=61;d.got=input_issues;}
        else if(count!=r.count){d.code=62;d.got=count;d.want=r.count;}
        else {d.code=63;d.got=0;d.want=1;} // The unchanged enabled predicate failed its area-state term.
    }
    re4dc_log("PS2FXCOMMON_REFUSE f=%u r=%03x row=%u why=%u got=%08x want=%08x slot=%u count=%u expected_count=%u "
              "age=%u expected_age=%u mul=%08x expected_mul=%08x plus=%08x expected_plus=%08x input=%x\n",
              s_common_frame,(unsigned)G_ROOM_ID,row,d.code,d.got,d.want,d.slot,count,(unsigned)r.count,
              d.age,age,d.mul,Ps2fxCommonBits(mul),d.plus,Ps2fxCommonBits(plus),input_issues);
}
// Refusal codes 1..48 follow Ps2fxCommonSource's field order above (8 accepts
// 0x4001 or 0x6001; 22/23 are lower/upper bounds). 49..56 identify binding fields;
// 57 age, 58 multiplier, 59 increment, 60 excess count, 61 input prerequisites,
// 62 incomplete count, 63 area disabled, 255 unmatched diagnostic mirror.
static int Ps2fxCommonIndoors(int& indoors)
{
    indoors=(pG->Status_flg[1]&0x02000000)!=0;
    if(G_ROOM_ID!=0x101)return 1;
    // EffAreaUpdate resets to forced indoor before the Stop20 return.
    indoors=(pG->Status_flg[1]&0x800)!=0;
    if(pG->Stop_flg&0x20)return 1;
    SstArea* areas=g_pEspSys->pSstArea;
    if(!areas || areas->num!=19)return 0;
    const SstAreaEnt& ent=areas->ent[10];
    const AreaData& data=*reinterpret_cast<const AreaData*>(ent.area);
    static const AreaXZ4 gc={3.737884521484375f,5759.1259765625f,3500.0f,
        {{16768.234375f,-29085.21484375f},{23186.787109375f,-31056.982421875f},
         {24521.90625f,-27215.91796875f},{17823.53125f,-25192.62109375f}}};
    const AreaXZ4& x=data.u.xz4;
    if(ent.no!=10 || ent.be_flag!=1 || ent.area_no!=255 || ent.flag!=1 || data.Be_flag!=1 || data.type!=AREA_TYPE_XZ4 ||
       x.floor!=gc.floor || x.height!=gc.height || x.radius!=gc.radius)return 0;
    for(unsigned i=0;i<4;++i)if(x.p[i].x!=gc.p[i].x || x.p[i].z!=gc.p[i].z)return 0;
    AreaXZ4 ps2=x;ps2.height=5827.89599609375f;
    ps2.p[2].x=24412.912109375f;ps2.p[2].z=-26902.986328125f;
    ps2.p[3].x=17953.720703125f;ps2.p[3].z=-25024.001953125f;
    Vec pos;
    if(!(pG->Status_flg[2]&0x10000)){if(!pPL)return 0;pos=pPL->pos;pos.y+=100.0f;}
    else pos=pG->Cam.param.pos;
    unsigned flagged=0;
    for(unsigned i=0;i<areas->num;++i)if(areas->ent[i].flag&1){
        ++flagged;
        if(i==10 ? areaHitCheck_xz4(&ps2,&pos)==1 : AreaHitCheck(areas->ent[i].area,&pos)==1)indoors=1;
    }
    return flagged==13;
}
// Submission refusal codes are the ordered guards below. Values are raw IEEE
// words for floats; want is the equality/reference bound (code 1 excludes it).
// Report only the first refusal for this source frame/row.
static int Ps2fxCommonSubmitRefuse(const Ps2fxCommonRow& row,unsigned why,unsigned got,unsigned want,unsigned item=0)
{
    static unsigned last_frame[14],last_room[14];static bool reported[14];
    const unsigned index=(unsigned)(&row-kPs2CommonHaze),frame=(unsigned)pG->Frame_cnt;
    if(index<14 && (!reported[index] || last_frame[index]!=frame || last_room[index]!=G_ROOM_ID)){
        re4dc_log("PS2FXCOMMON_SUBMIT f=%u r=%03x row=%u tex=%u why=%u got=%08x want=%08x item=%u\n",
            frame,(unsigned)G_ROOM_ID,index,(unsigned)row.visual.texture,why,got,want,item);
        reported[index]=true;last_frame[index]=frame;last_room[index]=G_ROOM_ID;
    }
    return 0;
}
static int Ps2fxCommonSubmit(const Ps2fxCommonRow& row,const ps2fx::CommonHazeState& state,unsigned& submitted)
{
    const ps2fx::CommonHazeRecipe& recipe=row.visual;
    EspTexWk* tw=&g_pEspSys->Esp_tex_tbl[recipe.texture];
    if(tw->Owner==0xd2)return Ps2fxCommonSubmitRefuse(row,1,tw->Owner,0xd2);
    if(!tw->pTpl)return Ps2fxCommonSubmitRefuse(row,2,0,1);
    if(tw->pTpl->numDescriptors!=1)return Ps2fxCommonSubmitRefuse(row,3,tw->pTpl->numDescriptors,1);
    if(!tw->pAnm)return Ps2fxCommonSubmitRefuse(row,4,0,1);
    if(tw->pAnm->Cx)return Ps2fxCommonSubmitRefuse(row,5,tw->pAnm->Cx,0);
    if(tw->pAnm->Cy)return Ps2fxCommonSubmitRefuse(row,6,tw->pAnm->Cy,0);
    if(tw->pAnm->Width!=128)return Ps2fxCommonSubmitRefuse(row,7,tw->pAnm->Width,128);
    if(tw->pAnm->Height!=128)return Ps2fxCommonSubmitRefuse(row,8,tw->pAnm->Height,128);
    if(tw->pAnm->Frames!=1)return Ps2fxCommonSubmitRefuse(row,9,tw->pAnm->Frames,1);
    const TEXDescriptor* td=TEXGet(tw->pTpl,0);
    if(!td)return Ps2fxCommonSubmitRefuse(row,10,0,1);
    if(!td->textureHeader)return Ps2fxCommonSubmitRefuse(row,11,0,1);
    const TEXHeader* th=td->textureHeader;
    Re4dcUiImage image={th->data,NULL,th->width,th->height,th->format,0xffffffffU,0};
    if(td->CLUTHeader){image.palette=td->CLUTHeader->data;image.palette_format=td->CLUTHeader->format;
        image.palette_bytes=td->CLUTHeader->numEntries*2;}
    f32 viewport[6];GXGetViewportv(viewport);const Mtx44& projection=pG->Cam.ProjMat;
    const f32 near_d=projection[2][3]/(projection[2][2]-1.0f),far_d=projection[2][3]/projection[2][2];
    for(unsigned i=0;i<6;++i)if(!ps2fx::CommonHazeClock::finite(viewport[i]))
        return Ps2fxCommonSubmitRefuse(row,12,Ps2fxCommonBits(viewport[i]),0,i);
    for(unsigned i=0;i<4;++i)for(unsigned j=0;j<4;++j)if(!ps2fx::CommonHazeClock::finite(projection[i][j]))
        return Ps2fxCommonSubmitRefuse(row,13,Ps2fxCommonBits(projection[i][j]),0,i*4+j);
    if(viewport[2]<=0)return Ps2fxCommonSubmitRefuse(row,14,Ps2fxCommonBits(viewport[2]),0);
    if(viewport[3]<=0)return Ps2fxCommonSubmitRefuse(row,15,Ps2fxCommonBits(viewport[3]),0);
    if(!ps2fx::CommonHazeClock::finite(near_d))return Ps2fxCommonSubmitRefuse(row,16,Ps2fxCommonBits(near_d),0);
    if(!ps2fx::CommonHazeClock::finite(far_d))return Ps2fxCommonSubmitRefuse(row,17,Ps2fxCommonBits(far_d),0);
    if(near_d<=0)return Ps2fxCommonSubmitRefuse(row,18,Ps2fxCommonBits(near_d),0);
    if(far_d<=near_d)return Ps2fxCommonSubmitRefuse(row,19,Ps2fxCommonBits(far_d),Ps2fxCommonBits(near_d));
    Re4dcEffectSprite sprites[ps2fx::CommonHazeState::Capacity];unsigned count=0;
    for(unsigned n=0;n<recipe.count;++n){
        const ps2fx::HazeParticle& particle=state.particles[n];
        Vec point={particle.position.x,particle.position.y,particle.position.z},center;
        PSMTXMultVec(pG->Cam.v_mat,&point,&center);center.z+=1.0f;
        const f32 depth=-center.z;
        if(!ps2fx::CommonHazeClock::finite(depth))return Ps2fxCommonSubmitRefuse(row,20,Ps2fxCommonBits(depth),0,n);
        if(depth<near_d || depth>far_d)continue;
        const f32 alpha=state.alpha(recipe,depth);
        if(!ps2fx::CommonHazeClock::finite(alpha))return Ps2fxCommonSubmitRefuse(row,21,Ps2fxCommonBits(alpha),0,n);
        if(alpha>255)return Ps2fxCommonSubmitRefuse(row,22,Ps2fxCommonBits(alpha),Ps2fxCommonBits(255.0f),n);
        u32 r=recipe.rgba[0],g=recipe.rgba[1],b=recipe.rgba[2],a=alpha>0?(u32)alpha:0;
        if(EffIsSetFinalCol()){GXColor final;EffGetFinalCol(&final);r=r*final.r>>8;g=g*final.g>>8;b=b*final.b>>8;a=a*final.a>>8;}
        if(!a)continue;
        Re4dcEffectSprite& sprite=sprites[count++];sprite.image=image;
        const f32 co=cosf(particle.angle),si=sinf(particle.angle),size=particle.size*state.size_mul;
        static const f32 x[4]={-.5f,.5f,.5f,-.5f},y[4]={.5f,.5f,-.5f,-.5f};
        static const f32 u[4]={0,1,1,0},v[4]={0,0,1,1};
        for(unsigned i=0;i<4;++i){
            const f32 vx=center.x+(co*x[i]-si*y[i])*size,vy=center.y+(si*x[i]+co*y[i])*size;
            const f32 px=(projection[0][0]*vx+projection[0][2]*center.z)/depth;
            const f32 py=(projection[1][1]*vy+projection[1][2]*center.z)/depth;
            sprite.x[i]=(viewport[2]*.5f*px+viewport[0]+viewport[2]*.5f)*640.0f/viewport[2];
            sprite.y[i]=(-viewport[3]*.5f*py+viewport[1]+viewport[3]*.5f)*480.0f/viewport[3];
            sprite.z[i]=1.0f/depth;
            sprite.u[i]=tw->mtx[0][0]*u[i]+tw->mtx[0][1]*v[i]+tw->mtx[0][3];
            sprite.v[i]=tw->mtx[1][0]*u[i]+tw->mtx[1][1]*v[i]+tw->mtx[1][3];
        }
        sprite.color=(a<<24)|(r<<16)|(g<<8)|b;sprite.src=4;sprite.dst=5;sprite.screen=0;sprite.pad=0;
#if RE4DC_TA_BIN_DIAG
        sprite.pad=2;
#endif
    }
    if(!re4dc_effect_haze_batch(sprites,count,&submitted))return Ps2fxCommonSubmitRefuse(row,23,count,0);
    return 1;
}
static void Ps2fxCommonHazeDraw()
{
    struct Group {ps2fx::CommonHazeBinding id;unsigned row,count;u16 age;f32 mul,plus;int bad;Ps2fxCommonRefusal refusal;};
    Group groups[2]={};unsigned group_count=0,issues=0,submitted=0,candidates=0;
    s_common_accepted=0;s_common_frame=(u32)pG->Frame_cnt;
    u8* pool=g_pEspSys?g_pEspSys->pEspBuf:NULL;
    unsigned generation=0,cells,bytes,stale,refused;
    const int resident=re4dc_room4_state(&generation,&cells,&bytes,&stale,&refused);
    if(pool!=s_common_pool || G_ROOM_ID!=s_common_room || generation!=s_common_generation){
        for(unsigned i=0;i<2;++i)s_common_haze[i].clear();
    }
    s_common_pool=pool;s_common_room=G_ROOM_ID;s_common_generation=generation;
    s_common_slots=g_pEspSys?g_pEspSys->nEsp:0;
    if(!(re4dc_ps2fx&PS2FX_HAZE)){
        for(unsigned i=0;i<2;++i)s_common_haze[i].clear();
        return;
    }
    for(unsigned i=0;i<sizeof(kPs2CommonHaze)/sizeof(kPs2CommonHaze[0]);++i)if(kPs2CommonHaze[i].room==G_ROOM_ID){
        if(group_count==2){issues|=1;break;}groups[group_count++].row=i;
    }
    if(!group_count){for(unsigned i=0;i<2;++i)s_common_haze[i].clear();return;}
    if(!resident || !pool || s_common_slots>2048)issues|=2;
    else for(unsigned slot=0;slot<s_common_slots;++slot){
        cEsp* e=(cEsp*)(pool+slot*0x150);
        for(unsigned i=0;i<group_count;++i){Group& g=groups[i];const Ps2fxCommonRow& r=kPs2CommonHaze[g.row];
            if(!Ps2fxCommonSignature(e,r))continue;
            ++candidates;
            if(!g.count){g.id=Ps2fxCommonIdentity(e,g.row,slot);g.age=e->m_Life_time;g.mul=e->m_Size_mul;g.plus=e->m_Size_plus;}
            ++g.count;
            if(!Ps2fxCommonSource(e,r) || !(g.id==Ps2fxCommonIdentity(e,g.row,g.id.first_slot)) ||
               g.age!=e->m_Life_time || g.mul!=e->m_Size_mul || g.plus!=e->m_Size_plus || g.count>r.count){
                if(!g.bad)g.refusal=Ps2fxCommonGroupRefusal(e,r,g.id,g.row,slot,g.count,g.age,g.mul,g.plus);
                g.bad=1;
            }
        }
    }
    int indoors=0;if(!(issues&2) && !Ps2fxCommonIndoors(indoors))issues|=4;
    Vec view,side,up=pG->Cam.up;
    PSVECSubtract(&pG->Cam.param.at,&pG->Cam.param.pos,&view);PSVECCrossProduct(&view,&up,&side);
    ps2fx::HazeCamera camera={};
    const f32 lengths[3]={view.x*view.x+view.y*view.y+view.z*view.z,
        side.x*side.x+side.y*side.y+side.z*side.z,up.x*up.x+up.y*up.y+up.z*up.z};
    for(unsigned i=0;i<3;++i)if(!ps2fx::CommonHazeClock::finite(lengths[i]) || lengths[i]<=0)issues|=8;
    if(!(issues&8)){
        PSVECNormalize(&view,&view);PSVECNormalize(&side,&side);PSVECNormalize(&up,&up);
        camera.position={pG->Cam.param.pos.x,pG->Cam.param.pos.y,pG->Cam.param.pos.z};
        camera.view={view.x,view.y,view.z};camera.side={side.x,side.y,side.z};camera.up={up.x,up.y,up.z};
    }
    const unsigned input_issues=issues;
    for(unsigned i=0;i<2;++i){
        if(i>=group_count){s_common_haze[i].clear();continue;}
        Group& g=groups[i];const Ps2fxCommonRow& r=kPs2CommonHaze[g.row];
        const bool enabled=!input_issues && !g.bad && g.count==r.count && (r.kind==1 || EffGetAreaState(r.kind-12));
        if(g.count && (!enabled)){issues|=0x10;Ps2fxCommonRefusalLog(i,g.row,g.count,g.age,g.mul,g.plus,g.refusal,input_issues);}
        if(s_common_haze[i].sample(enabled,g.id,(u32)pG->Frame_cnt,g.age,g.mul,g.plus,r.gc_initial_plus,r.visual,camera,indoors!=0)){
            unsigned draws=0;
            if(Ps2fxCommonSubmit(r,s_common_haze[i].state,draws)){s_common_accepted|=1U<<i;submitted+=draws;}
            else issues|=0x20;
        }
        issues|=s_common_haze[i].issues<<8;
    }
    static unsigned last_issues,last_accepted;static u16 last_room;static int reported;
    if(!reported || last_room!=G_ROOM_ID || last_issues!=issues || last_accepted!=s_common_accepted){
        re4dc_log("PS2FXCOMMON f=%u r=%03x candidates=%u accepted=%x submitted=%u issues=%x\n",
            (unsigned)pG->Frame_cnt,(unsigned)G_ROOM_ID,candidates,s_common_accepted,submitted,issues);
        reported=1;last_room=G_ROOM_ID;last_issues=issues;last_accepted=s_common_accepted;
    }
}
// Trans prepares image k after Render(k-1); the next Render consumes image k
// before Frame_cnt advances. This token owns no source pointers to dereference.
struct Ps2fxCommonPending {
    u8* pool;u32 frame;u16 room;unsigned slots,generation;bool pending;
};
static Ps2fxCommonPending s_common_pending={};
static void Ps2fxCommonHazePrepare()
{
    s_common_accepted=0;s_common_pending={};
    if(!pG || !g_pEspSys || !g_pEspSys->pEspBuf || g_pEspSys->nEsp>2048)return;
    unsigned generation=0,cells,bytes,stale,refused;
    if(!re4dc_room4_state(&generation,&cells,&bytes,&stale,&refused) || !generation)return;
    s_common_pending={g_pEspSys->pEspBuf,(u32)pG->Frame_cnt,(u16)G_ROOM_ID,g_pEspSys->nEsp,generation,true};
}
extern "C" void re4dc_ps2_fx_common_render(int coarse,int skipping)
{
    const Ps2fxCommonPending ticket=s_common_pending;s_common_pending={};
#if defined(RE4DC_LAB32) && RE4DC_LAB32
    LAB_PHASE(LabFx, );
#endif
    // Consume before every refusal; duplicate calls neither replay the batch
    // nor undo its accepted suppression before the queued source callbacks.
    if(!ticket.pending || !coarse || skipping || !pG || !g_pEspSys ||
       ticket.frame!=(u32)pG->Frame_cnt || ticket.room!=G_ROOM_ID ||
       ticket.pool!=g_pEspSys->pEspBuf || ticket.slots!=g_pEspSys->nEsp)return;
    unsigned generation=0,cells,bytes,stale,refused;
    if(!re4dc_room4_state(&generation,&cells,&bytes,&stale,&refused) || generation!=ticket.generation)return;
    Ps2fxCommonHazeDraw();
}
static int Ps2fxCommonHazeSuppress(cEsp* e)
{
    if(!s_common_accepted || !(re4dc_ps2fx&PS2FX_HAZE) || !g_pEspSys || s_common_pool!=g_pEspSys->pEspBuf ||
       s_common_slots!=g_pEspSys->nEsp || s_common_room!=G_ROOM_ID || s_common_frame!=(u32)pG->Frame_cnt)return 0;
    for(unsigned i=0;i<2;++i)if(s_common_accepted&(1U<<i)){
        const ps2fx::CommonHazeBinding& id=s_common_haze[i].binding;
        if(Ps2fxCommonSignature(e,kPs2CommonHaze[id.recipe]) && id==Ps2fxCommonIdentity(e,id.recipe,id.first_slot))return 1;
    }
    return 0;
}
