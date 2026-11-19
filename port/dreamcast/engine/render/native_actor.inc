#include "native_scene.h"
/* Characters (E0 step 2). Per actor and picture:
   1. reject the whole actor by per-bone spheres around the bone origins (no matrix work);
   2. compose each bone matrix once (pose x inverse bind x position quantum);
   3. reject or accept each part by its per-bone spheres, before any skinning: a part is out when one frustum
      plane has all its spheres outside, and fully inside when every sphere is inside every plane;
   4. blend, project and light-fold only the weight sets that visible parts use;
   5. positions on the SH-4 kernel re4dc_avk_pos_skin_u16 (screen x, y, 1/w and outcode per position), normals in
      a short ftrv loop, both over per-part streams sorted by weight set (one matrix load per run);
   6. emit strips: inside parts with no tests, boundary parts with per-strip outcodes and near clipping.
   The pack's model catalogue is converted at load (conversion cost is outside the picture). */
typedef struct {unsigned role,index,identity,bone; float world[12];} ActorPose;
typedef struct {uint8_t bone[3],count;float w[3];} SkinWeight;
typedef struct {unsigned role,hdr,at,size;} NativePart;
typedef struct {float dir[3],rgb[3];} Incident;
/* avk_sh4.S argument blocks (offsets fixed by the assembly). */
typedef struct {
    const void *records; unsigned count; const SourceVector *positions;
    const uint16_t *uv; void *output; uint8_t *outcode; unsigned stride;
    const float *matrices; const uint8_t *ready; unsigned entries;
    float width,height,near_plane,far_plane,au,bu,av,bv;
} PositionPass;
extern unsigned re4dc_avk_pos_skin_u16(const PositionPass*);
_Static_assert(sizeof(PositionPass)==72,"AVK ABI");

#include "part_cull.h"
typedef struct {
    const NativePart* src;
    uint16_t pos_first,pos_count,nrm_first,nrm_count;
    uint16_t sphere_first,sphere_count,ws_first,ws_count;
} RtPart;
typedef struct {
    const unsigned* h; const float* bind; const SkinWeight* w; const uint8_t* strips;
    SourceVector *pos,*nrm; RtPart* parts; PartSphere* spheres; uint16_t* part_ws; float* bone_radius;
    uint16_t* bones_used; unsigned nbones_used;
} RtModel;
typedef struct {unsigned n; RtModel m[];} RtCatalog;

#define ACTOR_POS_LIMIT 4096
#define ACTOR_WS_LIMIT 256
#include "source_light.inc"
static uint16_t pos_records[ACTOR_POS_LIMIT+2][4] __attribute__((aligned(32)));
static const uint16_t dummy_uv[2];
static shz_mat4x4_t skin_project[ACTOR_WS_LIMIT] __attribute__((aligned(32)));
static float skin_world[ACTOR_WS_LIMIT][12] __attribute__((aligned(32)));
static float bone_rows[ACTOR_WS_LIMIT][12] __attribute__((aligned(32)));
static float bone_scale[ACTOR_WS_LIMIT];
static uint8_t ws_ready[ACTOR_WS_LIMIT];
static pvr_vertex_t projected_pool[2][ACTOR_POS_LIMIT] __attribute__((aligned(32)));
static uint32_t colors_pool[2][ACTOR_POS_LIMIT] __attribute__((aligned(32)));
static uint8_t outcode_pool[2][ACTOR_POS_LIMIT];
static uint8_t part_state[128][16];       /* per actor ordinal: 0 out, 1 inside, 2 boundary */
static float frustum[6][4];
static shz_mat4x4_t view_project __attribute__((aligned(32)));
volatile unsigned m1_part_counts[300][2];
extern volatile uint32_t m1_state[8];

static void multiply34(float* out,const float* a,const float* b){
    for(unsigned i=0;i<3;i++)for(unsigned j=0;j<4;j++)
        out[i*4+j]=a[4*i]*b[j]+a[4*i+1]*b[j+4]+a[4*i+2]*b[j+8]+(j==3?a[4*i+3]:0);
}
static float column_scale(const float* m){
    float a=m[0]*m[0]+m[4]*m[4]+m[8]*m[8],b=m[1]*m[1]+m[5]*m[5]+m[9]*m[9],c=m[2]*m[2]+m[6]*m[6]+m[10]*m[10];
    return sqrtf(m1_maxf(a,m1_maxf(b,c)));
}
static inline unsigned sphere_planes(const float* c,float r,int* inside){return sphere_planes6((const float (*)[4])frustum,c,r,inside);}
static unsigned model_lights(const NativeScene* s,const ActorPose* pose,Incident* lamps){
    unsigned used=0;float strength[3]={};
    const NativeLamp* source=(const void*)s->state[2];
    unsigned n=s->words[2]*4/sizeof(*source);
    for(unsigned i=0;i<n;i++){
        const NativeLamp* l=source+i;float dx=l->pos[0]-pose->world[3],dy=l->pos[1]-pose->world[7],dz=l->pos[2]-pose->world[11];
        float dd=dx*dx+dy*dy+dz*dz;
        if(!(l->radius>0) || dd>=l->radius*l->radius)continue;
        float d=sqrtf(m1_maxf(dd,.001f)),gain=m1_maxf(0,(1-d/l->radius)*l->intensity);
        float value=gain*(l->rgb[0]+l->rgb[1]+l->rgb[2]);
        unsigned k=0;while(k<used && strength[k]>=value)++k;
        if(k==3||value<=0)continue;
        if(used<3)++used;
        for(unsigned t=used-1;t>k;t--){lamps[t]=lamps[t-1];strength[t]=strength[t-1];}
        strength[k]=value;
        lamps[k]=(Incident){{dx/d,dy/d,dz/d},{gain*l->rgb[0],gain*l->rgb[1],gain*l->rgb[2]}};
    }
    return used;
}
static unsigned model_index(const ActorPose* a){
    if(!a->role)return 0;
    if(a->role==2)return a->identity;
    unsigned type=a->identity>>8;
    if((a->identity&255)==0x12 && type==1)return 1;
    switch(type){case 3:return 3;case 4:return 4;case 11:return 5;default:return 2;}
}

/* ---- load-time conversion of the pack's model catalogue ---- */
static int ws_cmp_key(const SourceVector* v){return v->bone;}
static void sort_by_ws(SourceVector* v,uint16_t* old,unsigned n){
    for(unsigned i=1;i<n;i++){        /* stable insertion sort: runs are long, inputs small */
        SourceVector x=v[i];uint16_t o=old[i];unsigned j=i;
        while(j && ws_cmp_key(v+j-1)>ws_cmp_key(&x)){v[j]=v[j-1];old[j]=old[j-1];j--;}
        v[j]=x;old[j]=o;
    }
}
void native_actor_close(NativeScene* s){
    RtCatalog* cat=s->runtime;if(!cat)return;
    for(unsigned i=0;i<cat->n;i++){
        RtModel* m=cat->m+i;
        free(m->pos);free(m->nrm);free(m->parts);free(m->spheres);free(m->part_ws);free(m->bone_radius);free(m->bones_used);
    }
    free(cat);s->runtime=NULL;
}
int native_actor_open(NativeScene* s){
    RtCatalog* cat=calloc(1,sizeof(RtCatalog)+s->models.n*sizeof(RtModel));
    if(!cat)return 0;
    cat->n=s->models.n;s->runtime=cat;
    static uint16_t pmap[ACTOR_POS_LIMIT],nmap[ACTOR_POS_LIMIT],old[2*ACTOR_POS_LIMIT];
    static uint8_t seen_ws[ACTOR_WS_LIMIT],seen_bone[ACTOR_WS_LIMIT];
    static float lo[ACTOR_WS_LIMIT][3],hi[ACTOR_WS_LIMIT][3];
    for(unsigned mi=0;mi<cat->n;mi++){
        RtModel* m=cat->m+mi;
        const unsigned* h=row(&s->models,mi);
        if(h[0]>ACTOR_WS_LIMIT||h[1]>ACTOR_WS_LIMIT||h[2]>ACTOR_POS_LIMIT||h[3]>ACTOR_POS_LIMIT||h[4]>16)return 0;
        m->h=h;m->bind=(const void*)(h+6);m->w=(const void*)(m->bind+12*h[0]);
        const SourceVector* pos=(const void*)(m->w+h[1]),*norm=pos+h[2];
        const NativePart* parts=(const void*)(norm+h[3]);
        uint8_t* strips=(uint8_t*)(parts+h[4]);m->strips=strips;
        /* pass 1: sizes */
        unsigned npos=0,nnrm=0,nsph=0,nws=0;
        for(unsigned p=0;p<h[4];p++){
            memset(pmap,0xff,2*h[2]);memset(nmap,0xff,2*h[3]);memset(seen_ws,0,h[1]);memset(seen_bone,0,h[0]);
            const uint8_t* q=strips+parts[p].at,*end=q+parts[p].size;
            while(q<end){unsigned n=*(const unsigned*)q;const IndexCorner* c=(const void*)(q+4);
                for(unsigned j=0;j<n;j++){
                    if(pmap[c[j].position]==0xffff){pmap[c[j].position]=0;npos++;
                        const SkinWeight* w=m->w+pos[c[j].position].bone;
                        if(!seen_ws[pos[c[j].position].bone]){seen_ws[pos[c[j].position].bone]=1;nws++;}
                        for(unsigned k=0;k<w->count;k++)if(!seen_bone[w->bone[k]]){seen_bone[w->bone[k]]=1;nsph++;}}
                    if(nmap[c[j].normal]==0xffff){nmap[c[j].normal]=0;nnrm++;}
                }
                q=(const uint8_t*)(c+n);}
        }
        if(npos>ACTOR_POS_LIMIT||nnrm>ACTOR_POS_LIMIT)return 0;
        m->pos=malloc(8*npos+16);m->nrm=malloc(8*nnrm+16);m->parts=calloc(h[4],sizeof(RtPart));
        m->spheres=malloc(sizeof(PartSphere)*(nsph+1));m->part_ws=malloc(2*(nws+1));
        m->bone_radius=calloc(h[0],sizeof(float));m->bones_used=malloc(2*h[0]+2);
        if(!m->pos||!m->nrm||!m->parts||!m->spheres||!m->part_ws||!m->bone_radius||!m->bones_used)return 0;
        /* pass 2: per-part streams sorted by weight set, corner indices rewritten in place, spheres */
        npos=nnrm=nsph=nws=0;
        for(unsigned p=0;p<h[4];p++){
            RtPart* rp=m->parts+p;rp->src=parts+p;
            memset(pmap,0xff,2*h[2]);memset(nmap,0xff,2*h[3]);memset(seen_ws,0,h[1]);memset(seen_bone,0,h[0]);
            rp->pos_first=npos;rp->nrm_first=nnrm;
            uint8_t* q=strips+parts[p].at,*end=q+parts[p].size;
            unsigned pc=0,nc=0;
            while(q<end){unsigned n=*(const unsigned*)q;const IndexCorner* c=(const void*)(q+4);
                for(unsigned j=0;j<n;j++){
                    if(pmap[c[j].position]==0xffff){pmap[c[j].position]=pc;m->pos[npos+pc]=pos[c[j].position];old[pc]=c[j].position;pc++;}
                    if(nmap[c[j].normal]==0xffff){nmap[c[j].normal]=nc;m->nrm[nnrm+nc]=norm[c[j].normal];old[ACTOR_POS_LIMIT+nc]=c[j].normal;nc++;}
                }
                q=(uint8_t*)(c+n);}
            sort_by_ws(m->pos+npos,old,pc);sort_by_ws(m->nrm+nnrm,old+ACTOR_POS_LIMIT,nc);
            for(unsigned i=0;i<pc;i++)pmap[old[i]]=npos+i;
            for(unsigned i=0;i<nc;i++)nmap[old[ACTOR_POS_LIMIT+i]]=nnrm+i;
            q=strips+parts[p].at;
            while(q<end){unsigned n=*(const unsigned*)q;IndexCorner* c=(void*)(q+4);
                for(unsigned j=0;j<n;j++){c[j].position=pmap[c[j].position];c[j].normal=nmap[c[j].normal];}
                q=(uint8_t*)(c+n);}
            rp->pos_count=pc;rp->nrm_count=nc;
            /* weight-set list and per-bone model-space boxes of the part's positions */
            rp->ws_first=nws;rp->sphere_first=nsph;
            for(unsigned i=0;i<pc;i++){
                const SourceVector* v=m->pos+npos+i;const SkinWeight* w=m->w+v->bone;
                if(!seen_ws[v->bone]){seen_ws[v->bone]=1;m->part_ws[nws++]=v->bone;}
                for(unsigned k=0;k<w->count;k++){
                    unsigned b=w->bone[k];
                    if(!seen_bone[b]){seen_bone[b]=1;for(unsigned a=0;a<3;a++)lo[b][a]=hi[b][a]=v->xyz[a];}
                    for(unsigned a=0;a<3;a++){lo[b][a]=m1_minf(lo[b][a],v->xyz[a]);hi[b][a]=m1_maxf(hi[b][a],v->xyz[a]);}
                }
            }
            for(unsigned b=0;b<h[0];b++){
                if(!seen_bone[b])continue;
                PartSphere* sp=m->spheres+nsph++;sp->bone=b;sp->r=0;
                for(unsigned a=0;a<3;a++)sp->c[a]=.5f*(lo[b][a]+hi[b][a]);
                for(unsigned i=0;i<pc;i++){
                    const SourceVector* v=m->pos+npos+i;const SkinWeight* w=m->w+v->bone;unsigned use=0;
                    for(unsigned k=0;k<w->count;k++)use|=w->bone[k]==b;
                    if(!use)continue;
                    float dx=v->xyz[0]-sp->c[0],dy=v->xyz[1]-sp->c[1],dz=v->xyz[2]-sp->c[2];
                    sp->r=m1_maxf(sp->r,sqrtf(dx*dx+dy*dy+dz*dz));
                }
                sp->r=sp->r*1.01f+1;
                /* bone-origin radius for the whole-actor test: |bind x (q c)| + q r |bind| */
                const float* bm=m->bind+12*b;float c[3];
                for(unsigned a=0;a<3;a++)c[a]=.0625f*(bm[4*a]*sp->c[0]+bm[4*a+1]*sp->c[1]+bm[4*a+2]*sp->c[2])+bm[4*a+3];
                float rad=sqrtf(c[0]*c[0]+c[1]*c[1]+c[2]*c[2])+.0625f*sp->r*column_scale(bm);
                m->bone_radius[b]=m1_maxf(m->bone_radius[b],rad);
            }
            rp->ws_count=nws-rp->ws_first;rp->sphere_count=nsph-rp->sphere_first;
            npos+=pc;nnrm+=nc;
        }
        m->nbones_used=0;
        for(unsigned b=0;b<h[0];b++)if(m->bone_radius[b]>0)m->bones_used[m->nbones_used++]=b;
    }
    for(unsigned i=0;i<ACTOR_POS_LIMIT+2;i++)pos_records[i][0]=pos_records[i][1]=i;
    return 1;
}

/* ---- per picture ---- */
/* The player's stance from the HUD head record (life, maximum, weapon, stance): 1 while the knife is in hand. */
static int knife_stance(const NativeScene* s){return s->words[5]>=4 && s->state[5][3]==0x10;}
volatile uint32_t m1_vis_actors;
/* Baked visibility: an actor is skipped when every 2 m cube its bone-sphere box touches is hidden from the camera's cell. */
/* Actor columns exist only where actors can stand, each with a cube range; an actor is skipped when every
   column its bone-sphere box touches is hidden and the box stays inside those columns' ranges. Anything else
   (outside the room box, a column with no range, above or below the range) keeps it visible. */
static int actor_hidden(const NativeVis* v,const uint8_t* cubes,const float* lo,const float* hi){
    int a[3],b[3];const unsigned dim[3]={v->ax,v->ay,v->az};
    for(unsigned i=0;i<3;i++){
        float l=(lo[i]-v->alo[i])/v->acube,h=(hi[i]-v->alo[i])/v->acube;
        if(!(l>=0)||!(h<dim[i]))return 0;
        a[i]=(int)l;b[i]=(int)h;
    }
    for(int z=a[2];z<=b[2];z++)for(int x=a[0];x<=b[0];x++){
        const NativeVisColumn* col=v->cols+x+v->ax*z;
        if(a[1]<col->y0 || b[1]>=col->y0+col->ny || !(cubes[col->bit>>3]>>(col->bit&7)&1))return 0;
    }
    return 1;
}

static unsigned actor_serial;
static void actor_frame_setup(const NativeScene* s){
    const float* camera=(const float*)s->state[0];
    NativeFrustum f;native_world_frustum(camera,&f);
    for(unsigned j=0;j<6;j++){
        float n=sqrtf(f.p[j][0]*f.p[j][0]+f.p[j][1]*f.p[j][1]+f.p[j][2]*f.p[j][2]),inv=n>0?1.f/n:0;
        for(unsigned k=0;k<4;k++)frustum[j][k]=f.p[j][k]*inv;
    }
    static const float identity[]={1,0,0,0,0,1,0,0,0,0,1,0};
    view_project=projection_grid(camera,identity);
    for(unsigned c=0;c<4;c++)view_project.elem[4*c+2]=view_project.elem[4*c+3];   /* z = w for the kernel */
    lamps_frame(s);
}
/* Blend one weight set, project it for the position kernel and evaluate the model's lights for it. */
static void build_ws(const RtModel* m,unsigned i){
    const SkinWeight* w=m->w+i;float* out=skin_world[i];
    if(w->count==1 && w->w[0]==1.f)memcpy(out,bone_rows[w->bone[0]],48);
    else for(unsigned j=0;j<12;j++){float sum=0;for(unsigned k=0;k<w->count;k++)sum+=w->w[k]*bone_rows[w->bone[k]][j];out[j]=sum;}
    shz_xmtrx_load_4x4(&view_project);
    shz_mat4x4_t* pm=skin_project+i;
    for(unsigned c=0;c<4;c++){
        shz_vec4_t v=shz_xmtrx_transform_vec4(shz_vec4_init(out[c],out[4+c],out[8+c],c==3?1.f:0.f));
        pm->elem[4*c]=v.x;pm->elem[4*c+1]=v.y;pm->elem[4*c+2]=v.z;pm->elem[4*c+3]=v.w;
    }
    ws_light(i,out);
    ws_ready[i]=1;
}
static const pvr_vertex_t* cur_projected;static const uint32_t* cur_lit;static const uint8_t* cur_codes;
static const SourceVector* cur_pos;
static Corner clip_corner(const IndexCorner* c){
    const pvr_vertex_t* v=cur_projected+c->position;const SourceVector* p=cur_pos+c->position;
    const float* m=skin_project[p->bone].elem;
    float w=m[3]*p->xyz[0]+m[7]*p->xyz[1]+m[11]*p->xyz[2]+m[15],mag=w<0?-w:w;
    return (Corner){v->x*mag,v->y*mag,w,c->u*(1.f/32768),c->v*(1.f/32768),cur_lit[c->normal]};
}
extern pvr_vertex_t* m1_emit_actor_strip(pvr_vertex_t* sq,const IndexCorner* corners,unsigned n,const pvr_vertex_t* proj,const uint32_t* lit);
static pvr_vertex_t* emit_part(pvr_vertex_t* sq,const NativeScene* s,const RtModel* m,const RtPart* rp,unsigned state,float near,unsigned* emitted_parts){
    const uint8_t* p=m->strips+rp->src->at,*stop=p+rp->src->size;
    int header=0;
    const pvr_vertex_t* proj=cur_projected;const uint32_t* lit=cur_lit;const uint8_t* codes=cur_codes;
    while(p<stop){
        unsigned n=*(const unsigned*)p;const IndexCorner* v=(const void*)(p+4);p=(const uint8_t*)(v+n);
        unsigned combined=0;
        if(state==2){
            unsigned common=63;
            for(unsigned j=0;j<n;j++){unsigned code=codes[v[j].position];common&=code;combined|=code;}
            if(common)continue;
        }
        if(!header){
            const unsigned* hdr=(const unsigned*)row(&s->assets.header,rp->src->hdr)+1;
            for(unsigned j=0;j<8;j++)((volatile unsigned*)sq)[j]=hdr[j];
            advance(&sq);header=1;
        }
        if(!(combined&32))sq=m1_emit_actor_strip(sq,v,n,proj,lit);
        else{
            Corner a=clip_corner(v),b=clip_corner(v+1);
            for(unsigned j=2;j<n;j++){Corner c=clip_corner(v+j);clipped(&sq,j&1?b:a,j&1?a:b,c,near);a=b;b=c;}
        }
    }
    *emitted_parts+=header;
    return sq;
}
void native_actor_pass(NativeScene* s,unsigned translucent){
    const RtCatalog* cat=s->runtime;
    const ActorPose* pose=(const void*)s->state[1];const ActorPose* end=pose+s->words[1]/16;
    const float* camera=(const float*)s->state[0];float near=camera[18]/(camera[17]-1),far=camera[25];
    volatile unsigned* census=m1_part_counts[(m1_state[1]-1)%300];
    if(!translucent){census[0]=census[1]=0;actor_frame_setup(s);++actor_serial;}
    pvr_vertex_t* sq=(pvr_vertex_t*)sq_lock((void*)PVR_TA_INPUT);
    unsigned ordinal=0;
    for(;pose<end;ordinal++){
        const ActorPose* next=pose+1;while(next<end && next->bone)next++;
        const ActorPose* actor=pose;pose=next;
        unsigned model=model_index(actor);
        const RtModel* m=cat->m+model;const unsigned* h=m->h;
        if(next-actor<h[0]+1 || ordinal>=128)continue;
        if(translucent && model)continue;
        uint8_t* state=part_state[ordinal];
        const pvr_vertex_t* proj=projected_pool[model!=0];uint32_t* lit=colors_pool[model!=0];uint8_t* codes=outcode_pool[model!=0];
        cur_projected=proj;cur_lit=lit;cur_codes=codes;cur_pos=m->pos;
        if(translucent){
            unsigned emitted=0;
            for(unsigned p=0;p<h[4];p++)if(m->parts[p].src->role==7 && state[p])sq=emit_part(sq,s,m,m->parts+p,state[p],near,&emitted);
            continue;
        }
        unsigned considered=h[4];census[0]+=considered;
        /* 1. whole actor: spheres around bone origins */
        unsigned all=63;float lo[3]={1e30f,1e30f,1e30f},hi[3]={-1e30f,-1e30f,-1e30f};
        for(unsigned i=0;i<m->nbones_used;i++){
            unsigned b=m->bones_used[i];const float* wm=actor[b+1].world;int dummy=1;
            float c[3]={wm[3],wm[7],wm[11]},r=m->bone_radius[b]*column_scale(wm)*1.02f+1;
            all&=sphere_planes(c,r,&dummy);
            for(unsigned a=0;a<3;a++){lo[a]=m1_minf(lo[a],c[a]-r);hi[a]=m1_maxf(hi[a],c[a]+r);}
        }
        if(!all && s->world.vis_cubes && actor_hidden(s->world.vis,s->world.vis_cubes,lo,hi)){all=1;m1_vis_actors++;}
        if(all){memset(state,0,h[4]);census[1]+=considered;continue;}
        /* 2. bones: pose x inverse bind x quantum */
        for(unsigned i=0;i<m->nbones_used;i++){
            unsigned b=m->bones_used[i];float* r=bone_rows[b];
            multiply34(r,actor[b+1].world,m->bind+12*b);
            for(unsigned k=0;k<3;k++){r[k]*=.0625f;r[4+k]*=.0625f;r[8+k]*=.0625f;}
            bone_scale[b]=column_scale(r);
        }
        /* 3. parts */
        unsigned visible=0;
        for(unsigned p=0;p<h[4];p++){
            const RtPart* rp=m->parts+p;
            unsigned st=part_class((const float (*)[4])frustum,m->spheres+rp->sphere_first,rp->sphere_count,(const float (*)[12])bone_rows,bone_scale);
            state[p]=st;visible+=st!=0;
            if(!st)census[1]++;
        }
        if(!visible)continue;
        /* 4. weight sets used by visible parts */
        source_lights(s,actor,h[0],model_light(s,actor),&cur_lights);
        memset(ws_ready,0,h[1]);
        for(unsigned p=0;p<h[4];p++){
            if(!state[p])continue;const RtPart* rp=m->parts+p;
            for(unsigned k=0;k<rp->ws_count;k++){unsigned i=m->part_ws[rp->ws_first+k];if(!ws_ready[i])build_ws(m,i);}
        }
        /* 5. positions and normals of visible parts */
        for(unsigned p=0;p<h[4];p++){
            if(!state[p])continue;const RtPart* rp=m->parts+p;
            unsigned n=rp->pos_count;
            pos_records[n][0]=pos_records[n+1][0]=0;
            PositionPass a={pos_records,n,m->pos+rp->pos_first,dummy_uv,(void*)(proj+rp->pos_first),codes+rp->pos_first,8,
                            skin_project[0].elem,ws_ready,h[1],640,480,near,far,0,0,0,0};
            re4dc_avk_pos_skin_u16(&a);
            pos_records[n][0]=n;pos_records[n+1][0]=n+1;
            light_normals_source(m->nrm+rp->nrm_first,rp->nrm_count,lit+rp->nrm_first);
        }
        /* 6. opaque parts now; hair (role 7) in the translucent pass from the same pools */
        unsigned emitted=0;
        for(unsigned p=0;p<h[4];p++){
            if(!state[p] || m->parts[p].src->role==7)continue;
            /* Leon's role-2 part is the knife in hand: drawn in the knife stance only (eng-e0b: the recorded stance,
               PlGetWeaponNo() == 0x10). */
            if(!model && m->parts[p].src->role==2 && knife_stance(s)==0)continue;
            unsigned before=emitted;sq=emit_part(sq,s,m,m->parts+p,state[p],near,&emitted);
            if(emitted==before)census[1]++;
        }
    }
    sq_wait();sq_unlock();
}
