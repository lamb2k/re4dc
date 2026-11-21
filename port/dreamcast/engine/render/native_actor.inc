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
    uint16_t strip_first,strip_count;   /* lane eng-draw3: the part's strips in the model's strip order (strip_code) */
    uint8_t all_sided,pad8;             /* lane eng-draw3 arm CB: every strip of the part one-sided */
} RtPart;
typedef struct {
    const unsigned* h; const float* bind; const SkinWeight* w; const uint8_t* strips;
    SourceVector *pos,*nrm; RtPart* parts; PartSphere* spheres; uint16_t* part_ws; float* bone_radius;
    uint16_t* bones_used; unsigned nbones_used;
    uint8_t* sided;   /* lane eng-draw3 arm CB: per strip (model order), 1 one-sided (closed surface), else 0; NULL arm off */
} RtModel;
/* Lane eng-draw3, step 5: character back-face culling, a LOOK ARM (run-time only, never the default). Boot file CBCULL,
   read when the pack opens (before play). A strip is one-sided when every edge of each of its triangles is shared with
   another triangle of the model (a closed surface, found at load from the pack's own position indices across all
   parts), and it is not hair (roles 7 and 8, cards seen from both sides). Under the arm, a one-sided strip none of whose
   triangles faces the camera is dropped before its normals are lit and before emission, and a part whose strips are
   all one-sided gets the chip's culling (ISP culling mode 3, the world's) in its header. */
static int cb_arm=-1;
static unsigned cb_onesided_strips,cb_strips;
typedef struct {unsigned n; RtModel m[];} RtCatalog;

#define ACTOR_POS_LIMIT 4096
#define ACTOR_WS_LIMIT 384   /* eng-boss: El Gigante (PS2 cast) has 276 weight sets */
#define ACTOR_STRIP_LIMIT 8192
#include "source_light.inc"
#include "content_actor.inc"
static uint16_t pos_records[ACTOR_POS_LIMIT+2][4] __attribute__((aligned(32)));
static const uint16_t dummy_uv[2];
static shz_mat4x4_t skin_project[ACTOR_WS_LIMIT] __attribute__((aligned(32)));
static float skin_world[ACTOR_WS_LIMIT][12] __attribute__((aligned(32)));
static float bone_rows[ACTOR_WS_LIMIT][12] __attribute__((aligned(32)));
static float bone_scale[ACTOR_WS_LIMIT];
/* The rows build_ws blends (lane eng-e1e): bone_rows (12 floats a bone) by default; the E1 actor pass points them at
   the skeleton service's published palette (16 floats a bone, already in this layout) and reads it in place. */
static const float* ws_rows=&bone_rows[0][0];
static unsigned ws_stride=12;
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
/* Lane eng-draw3 (step 3, the per-model fixed cost): the sphere-against-frustum test of part_cull.h without a branch per
   plane. The same distance and the same two comparisons per plane, folded into the masks by compare-and-move: one block
   a sphere where the loop made two conditional branches a plane (the tier ends a block at each and charges the next
   block's first memory reads again). Used by the whole-character test and the part classes of both passes. */
static inline unsigned sphere_planes6_flat(const float (*fr)[4],const float* c,float r,int* inside){
    unsigned out=0;int in=1;const float nr=-r;
#pragma GCC unroll 6
    for(unsigned j=0;j<6;j++){
        const float d=fr[j][0]*c[0]+fr[j][1]*c[1]+fr[j][2]*c[2]+fr[j][3];
        out|=(unsigned)(d<nr)<<j;
        in&=!(d<r);
    }
    *inside&=in;
    return out;
}
static inline unsigned sphere_planes(const float* c,float r,int* inside){return sphere_planes6_flat((const float (*)[4])frustum,c,r,inside);}
/* part_class (part_cull.h) on the flat test: the same loop, the same early stop */
static inline unsigned part_class_flat(const float (*fr)[4],const PartSphere* sp,unsigned n,const float (*rows)[12],const float* scale){
    unsigned out=63;int inside=1;
    for(unsigned k=0;k<n && (out||inside);k++,sp++){
        const float* r=rows[sp->bone];float c[3];
        for(unsigned a=0;a<3;a++)c[a]=r[4*a]*sp->c[0]+r[4*a+1]*sp->c[1]+r[4*a+2]*sp->c[2]+r[4*a+3];
        out&=sphere_planes6_flat(fr,c,sp->r*scale[sp->bone],&inside);
    }
    return out?0:inside?1:2;
}
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

/* Arm CB (load time): per strip of the model (parts in order, strips in order), 1 when every edge of every
   non-degenerate triangle is used by at least two triangles of the model (original position indices) and the part is
   not hair. Returns NULL when out of memory (the arm then leaves the model as it is). */
static uint8_t* cb_sides(const unsigned* h,const NativePart* parts,const uint8_t* strips){
    unsigned tris=0,nstrip=0;
    for(unsigned p=0;p<h[4];p++){const uint8_t* q=strips+parts[p].at,*end=q+parts[p].size;
        while(q<end){unsigned n=*(const unsigned*)q;tris+=n-2;nstrip++;q+=4+8*n;}}
    unsigned size=1024;while(size<6*tris+16)size<<=1;
    uint32_t* key=malloc(4*size);uint8_t* count=calloc(size,1);uint8_t* out=calloc(nstrip+1,1);
    if(!key||!count||!out){free(key);free(count);free(out);return NULL;}
    #define CB_SLOT(a,b) ({uint32_t k_=(a)<(b)?(a)<<16|(b):(b)<<16|(a),i_=(k_*2654435761u)>>8&(size-1); \
        while(count[i_] && key[i_]!=k_)i_=(i_+1)&(size-1); key[i_]=k_; i_;})
    for(int pass=0;pass<2;pass++){
        unsigned s=0;
        for(unsigned p=0;p<h[4];p++){
            const uint8_t* q=strips+parts[p].at,*end=q+parts[p].size;const unsigned hair=parts[p].role==7||parts[p].role==8;
            while(q<end){unsigned n=*(const unsigned*)q;const IndexCorner* c=(const void*)(q+4);q+=4+8*n;
                unsigned closed=!hair;
                for(unsigned k=2;k<n;k++){
                    unsigned a=c[k-2].position,b=c[k-1].position,d=c[k].position;
                    if(a==b||b==d||a==d)continue;
                    if(!pass){unsigned i;i=CB_SLOT(a,b);if(count[i]<255)count[i]++;i=CB_SLOT(b,d);if(count[i]<255)count[i]++;
                              i=CB_SLOT(a,d);if(count[i]<255)count[i]++;}
                    else closed&=count[CB_SLOT(a,b)]>=2 && count[CB_SLOT(b,d)]>=2 && count[CB_SLOT(a,d)]>=2;
                }
                if(pass){out[s]=closed;cb_onesided_strips+=closed;cb_strips++;}
                s++;
            }
        }
    }
    #undef CB_SLOT
    free(key);free(count);
    return out;
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
        free(m->sided);
    }
    free(cat);s->runtime=NULL;
}
int native_actor_open(NativeScene* s){
    RtCatalog* cat=calloc(1,sizeof(RtCatalog)+s->models.n*sizeof(RtModel));
    if(!cat)return 0;
    cat->n=s->models.n;s->runtime=cat;
    if(cb_arm<0){file_t f=fs_open("/cd/CBCULL",O_RDONLY);cb_arm=f>=0;if(f>=0){fs_close(f);printf("CBCULL: lane eng-draw3 look arm, character back faces culled\n");}}
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
        m->sided=cb_arm>0?cb_sides(h,parts,strips):NULL;   /* lane eng-draw3 arm CB (original position indices) */
        m->pos=malloc(8*npos+16);m->nrm=malloc(8*nnrm+16);m->parts=calloc(h[4],sizeof(RtPart));
        m->spheres=malloc(sizeof(PartSphere)*(nsph+1));m->part_ws=malloc(2*(nws+1));
        m->bone_radius=calloc(h[0],sizeof(float));m->bones_used=malloc(2*h[0]+2);
        if(!m->pos||!m->nrm||!m->parts||!m->spheres||!m->part_ws||!m->bone_radius||!m->bones_used)return 0;
        /* pass 2: per-part streams sorted by weight set, corner indices rewritten in place, spheres */
        npos=nnrm=nsph=nws=0;unsigned nstrip=0;
        for(unsigned p=0;p<h[4];p++){
            RtPart* rp=m->parts+p;rp->src=parts+p;
            memset(pmap,0xff,2*h[2]);memset(nmap,0xff,2*h[3]);memset(seen_ws,0,h[1]);memset(seen_bone,0,h[0]);
            rp->pos_first=npos;rp->nrm_first=nnrm;rp->strip_first=nstrip;
            uint8_t* q=strips+parts[p].at,*end=q+parts[p].size;
            unsigned pc=0,nc=0;
            while(q<end){unsigned n=*(const unsigned*)q;const IndexCorner* c=(const void*)(q+4);nstrip++;
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
            rp->pos_count=pc;rp->nrm_count=nc;rp->strip_count=nstrip-rp->strip_first;
            if(nstrip>ACTOR_STRIP_LIMIT)return 0;
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
        if(m->sided)for(unsigned p=0;p<h[4];p++){
            RtPart* rp=m->parts+p;unsigned all=rp->strip_count>0;
            for(unsigned k=0;k<rp->strip_count;k++)all&=m->sided[rp->strip_first+k];
            rp->all_sided=all;
        }
    }
    for(unsigned i=0;i<ACTOR_POS_LIMIT+2;i++)pos_records[i][0]=pos_records[i][1]=i;
    if(cb_arm>0)printf("CBCULL: %u of %u character strips one-sided (closed), the rest drawn from both sides\n",cb_onesided_strips,cb_strips);
    return 1;
}

/* ---- per picture ---- */
/* The player's stance from the HUD head record (life, maximum, weapon, stance): 1 while the knife is in hand. */
/* Lane eng-e1j (H-016.2): the E1 images read the stance from the game state when drawing (hud_stance_live, set by
   services/draw.cpp); the bench reads the pack's recorded word. */
unsigned (*hud_stance_live)(void);
static int knife_stance(const NativeScene* s){
    if(hud_stance_live)return hud_stance_live()==0x10;
    return s->words[5]>=4 && s->state[5][3]==0x10;
}
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
    DC_ADD(DC_A_CALLS,1);   /* lane eng-draw1: once per character drawn (E1), once per pass (bench) */
    /* lane eng-draw3 (step 3): once a picture, not once a character: the frustum, the view-projection and the light
       order depend only on the picture's camera and room lights (m1_state[1] is the picture number, never the same for
       two pictures in a row) */
    static const NativeScene* done_scene;static uint32_t done_picture;
    if(done_scene==s && done_picture==m1_state[1] && m1_state[1])return;
    done_scene=s;done_picture=m1_state[1];
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
static void build_ws_once(const RtModel* m,unsigned i);
/* lane eng-draw1: counted; lab arm DL_WS2 builds each weight set twice */
static void build_ws(const RtModel* m,unsigned i){
    DC_ADD(DC_A_WS,1);
    build_ws_once(m,i);
    if(DC_ARM(DL_WS2))build_ws_once(m,i);
}
/* Lane eng-draw3 (C3): the blend unrolled by weight count (one block, no per-element loop: the tier charged each of the
   12 x count iterations as a block of its own), a single-bone set copied without a memcpy call, the four columns
   projected without a loop, and the view-projection loaded into XMTRX once per character (ws_begin), not once per set.
   The sums are the same: each element starts from a zero the compiler cannot fold (ws_zero) and adds w[k] x row[k]
   in k order, as the loop did. */
static volatile float ws_zero_store;   /* 0, read through a volatile once per character */
static float ws_zero;
static inline void ws_begin(void){ws_zero=ws_zero_store;shz_xmtrx_load_4x4(&view_project);}
static void build_ws_once(const RtModel* m,unsigned i){
    const SkinWeight* w=m->w+i;float* out=skin_world[i];
    const float* r0=ws_rows+ws_stride*w->bone[0];
    if(w->count==1 && w->w[0]==1.f){
#pragma GCC unroll 12
        for(unsigned j=0;j<12;j++)out[j]=r0[j];
    }else if(w->count==2){
        const float* r1=ws_rows+ws_stride*w->bone[1];const float w0=w->w[0],w1=w->w[1],z=ws_zero;
#pragma GCC unroll 12
        for(unsigned j=0;j<12;j++){float sum=z;sum+=w0*r0[j];sum+=w1*r1[j];out[j]=sum;}
    }else if(w->count==3){
        const float* r1=ws_rows+ws_stride*w->bone[1],*r2=ws_rows+ws_stride*w->bone[2];
        const float w0=w->w[0],w1=w->w[1],w2=w->w[2],z=ws_zero;
#pragma GCC unroll 12
        for(unsigned j=0;j<12;j++){float sum=z;sum+=w0*r0[j];sum+=w1*r1[j];sum+=w2*r2[j];out[j]=sum;}
    }else{
        const float w0=w->count?w->w[0]:0.f,z=ws_zero;
#pragma GCC unroll 12
        for(unsigned j=0;j<12;j++){float sum=z;if(w->count)sum+=w0*r0[j];out[j]=sum;}
    }
    shz_mat4x4_t* pm=skin_project+i;
    shz_vec4_t v=shz_xmtrx_transform_vec4(shz_vec4_init(out[0],out[4],out[8],0.f));
    pm->elem[0]=v.x;pm->elem[1]=v.y;pm->elem[2]=v.z;pm->elem[3]=v.w;
    v=shz_xmtrx_transform_vec4(shz_vec4_init(out[1],out[5],out[9],0.f));
    pm->elem[4]=v.x;pm->elem[5]=v.y;pm->elem[6]=v.z;pm->elem[7]=v.w;
    v=shz_xmtrx_transform_vec4(shz_vec4_init(out[2],out[6],out[10],0.f));
    pm->elem[8]=v.x;pm->elem[9]=v.y;pm->elem[10]=v.z;pm->elem[11]=v.w;
    v=shz_xmtrx_transform_vec4(shz_vec4_init(out[3],out[7],out[11],1.f));
    pm->elem[12]=v.x;pm->elem[13]=v.y;pm->elem[14]=v.z;pm->elem[15]=v.w;
    if(!ws_light_off)ws_light(i,out);   /* eng-look: off on a baked-lighting cache hit */
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
static pvr_vertex_t* emit_part_once(pvr_vertex_t* sq,const NativeScene* s,const RtModel* m,const RtPart* rp,unsigned state,float near,unsigned* emitted_parts);
static uint8_t dc_apos[ACTOR_POS_LIMIT],dc_anrm[ACTOR_POS_LIMIT];   /* census marks (lane eng-draw1) */
/* lane eng-draw1: counted per part; lab arm DL_EMIT2 emits the part twice; arm N (near not a number) as before lane
   eng-e1l: no near outcode, no near clipping */
static pvr_vertex_t* emit_part(pvr_vertex_t* sq,const NativeScene* s,const RtModel* m,const RtPart* rp,unsigned state,float near,unsigned* emitted_parts){
    dc_clip=DC_A_CLIPTRIS;
    if(!dc_mute){DC_ADD(DC_A_PARTS,1);DC_ADD(DC_A_PARTS_BOUND,state==2);DC_ADD(DC_A_POS,rp->pos_count);}
    if(DC_ARM(DL_CENSUS)){memset(dc_apos+rp->pos_first,0,rp->pos_count);memset(dc_anrm+rp->nrm_first,0,rp->nrm_count);}
    sq=emit_part_once(sq,s,m,rp,state,DC_NEAR(near),emitted_parts);
    if(DC_ARM(DL_CENSUS) && rp->src->role!=8){   /* census: positions skinned and normals lit that no kept triangle used */
        unsigned pn=0,pp=0,nn=0,np=0,cn=0,cp=0;
        for(unsigned i=rp->pos_first;i<(unsigned)rp->pos_first+rp->pos_count;i++){pn+=!(dc_apos[i]&1);pp+=!(dc_apos[i]&2);cn+=!(dc_apos[i]&4);cp+=!(dc_apos[i]&8);}
        dc_n[DC_V_A_CDEADPOS_N]+=cn;dc_n[DC_V_A_CDEADPOS_P]+=cp;
        for(unsigned i=rp->nrm_first;i<(unsigned)rp->nrm_first+rp->nrm_count;i++){nn+=!(dc_anrm[i]&1);np+=!(dc_anrm[i]&2);}
        dc_n[DC_V_A_DEADPOS_N]+=pn;dc_n[DC_V_A_DEADPOS_P]+=pp;dc_n[DC_V_A_DEADNRM_N]+=nn;dc_n[DC_V_A_DEADNRM_P]+=np;
    }
    if(DC_ARM(DL_EMIT2)){unsigned again=0;dc_mute=1;sq=emit_part_once(sq,s,m,rp,state,near,&again);dc_mute=0;}
    return sq;
}
/* Lane eng-draw3 (E3): a boundary part's strips are tested once a picture, after its positions are skinned and before
   any normal is lit: mark_part writes each strip's code (STRIP_DROPPED: every corner outside one plane, never drawn;
   else the corners' combined outcode, bit 5 = crosses the near plane) and lists the normals the kept strips use, so only
   those are lit; the emission (opaque and translucent calls) reads the codes instead of testing again. */
#define STRIP_DROPPED 0x80u
static uint8_t strip_code_pool[2][ACTOR_STRIP_LIMIT];
static const uint8_t* cur_strip_codes;
static uint16_t nrm_list[ACTOR_POS_LIMIT],nrm_stamp[ACTOR_POS_LIMIT],nrm_stamp_now;
/* Returns how many normals to light, listed in nrm_list, or MARK_ALL when no strip was dropped (light the part's whole
   range: the common case on close pictures, where listing every corner cost more than it saved: run r1a, hill +0.9 ms).
   When some strips are dropped, the kept strips' normals are marked with plain stores (no branch a corner) and listed by
   one branch-free pass over the part's normal range. */
#define MARK_ALL (~0u)
static unsigned mark_part(const RtModel* m,const RtPart* rp,const uint8_t* codes,uint8_t* sc){
    const uint8_t* p=m->strips+rp->src->at,*stop=p+rp->src->size;
    const unsigned keep=DC_ARM(DL_NAN)?31u:63u;
    const uint8_t* sided=m->sided?m->sided+rp->strip_first:NULL;   /* arm CB only */
    uint8_t* const sc0=sc+rp->strip_first;unsigned dropped=0;
    sc=sc0;
    while(p<stop){
        unsigned n=*(const unsigned*)p;const IndexCorner* v=(const void*)(p+4);p=(const uint8_t*)(v+n);
        unsigned common=63,combined=0;
        for(unsigned j=0;j<n;j++){unsigned code=codes[v[j].position];common&=code;combined|=code;}
        if(common&keep){*sc++=STRIP_DROPPED;dropped++;if(sided)sided++;continue;}
        if(sided && *sided++ && !(combined&keep&32)){   /* arm CB: a one-sided strip with no triangle facing the camera */
            unsigned front=0;
            for(unsigned k=2;k<n && !front;k++){
                const pvr_vertex_t *a=cur_projected+v[k&1?k-1:k-2].position,*b=cur_projected+v[k&1?k-2:k-1].position,
                                   *c=cur_projected+v[k].position;
                front=(b->x-a->x)*(c->y-a->y)-(c->x-a->x)*(b->y-a->y)<0;   /* the census's sign: positive is the far side */
            }
            if(!front){*sc++=STRIP_DROPPED;dropped++;continue;}
        }
        *sc++=combined&keep;
    }
    if(!dropped)return MARK_ALL;
    if(!++nrm_stamp_now){memset(nrm_stamp,0,sizeof nrm_stamp);nrm_stamp_now=1;}
    const uint16_t stamp=nrm_stamp_now;
    p=m->strips+rp->src->at;sc=sc0;
    while(p<stop){
        unsigned n=*(const unsigned*)p;const IndexCorner* v=(const void*)(p+4);p=(const uint8_t*)(v+n);
        if(*sc++&STRIP_DROPPED)continue;
        for(unsigned j=0;j<n;j++)nrm_stamp[v[j].normal]=stamp;
    }
    unsigned nl=0;
    for(unsigned i=rp->nrm_first,e=i+rp->nrm_count;i<e;i++){nrm_list[nl]=i;nl+=nrm_stamp[i]==stamp;}
    return nl;
}
/* the normals of one drawn part: the kept strips' (boundary part with dropped strips) or all of them */
static inline void light_part(const RtModel* m,const RtPart* rp,unsigned st,const uint8_t* codes,uint8_t* sc,uint32_t* lit,int light){
    const unsigned nl=st==2?mark_part(m,rp,codes,sc):MARK_ALL;
    if(!light)return;
    if(nl==MARK_ALL)light_normals_source(m->nrm+rp->nrm_first,rp->nrm_count,lit+rp->nrm_first);
    else light_normals_list(m->nrm,nrm_list,nl,lit);
}
static pvr_vertex_t* emit_part_once(pvr_vertex_t* sq,const NativeScene* s,const RtModel* m,const RtPart* rp,unsigned state,float near,unsigned* emitted_parts){
    const uint8_t* p=m->strips+rp->src->at,*stop=p+rp->src->size;
    int header=0;
    const pvr_vertex_t* proj=cur_projected;const uint32_t* lit=cur_lit;
    const uint8_t* sc=cur_strip_codes+rp->strip_first;
    unsigned strips=0,out=0,corners=0,clipstrips=0;
    while(p<stop){
        unsigned n=*(const unsigned*)p;const IndexCorner* v=(const void*)(p+4);p=(const uint8_t*)(v+n);
        unsigned combined=0;
        strips++;
        if(state==2){
            combined=*sc++;
            if(combined&STRIP_DROPPED){out++;continue;}
        }
        if(!header){
            const unsigned* hdr=(const unsigned*)row(&s->assets.header,rp->src->hdr)+1;
            for(unsigned j=0;j<8;j++)((volatile unsigned*)sq)[j]=hdr[j];
            if(rp->all_sided && m->sided)((volatile unsigned*)sq)[1]=hdr[1]|3u<<27;   /* arm CB: the chip culls (mode 3) */
            advance(&sq);header=1;
        }
        if(DC_ARM(DL_CENSUS) && !dc_mute){   /* census (counts only) */
            const unsigned cull=((const unsigned*)row(&s->assets.header,rp->src->hdr)+1)[1]>>27&3;unsigned any=0;
            for(unsigned k=2;k<n;k++){
                const IndexCorner *ca=v+(k&1?k-1:k-2),*cb=v+(k&1?k-2:k-1),*cc=v+k;
                if(combined&32){any|=15;dc_apos[ca->position]|=15;dc_apos[cb->position]|=15;dc_apos[cc->position]|=15;
                    dc_anrm[ca->normal]|=15;dc_anrm[cb->normal]|=15;dc_anrm[cc->normal]|=15;continue;}
                const pvr_vertex_t *a=proj+ca->position,*b=proj+cb->position,*c=proj+cc->position;
                if(rp->src->role==8){dc_census_tr(a->x,a->y,b->x,b->y,c->x,c->y);continue;}
                unsigned kept;dc_census_tri(DC_V_A_TRIS,a->x,a->y,a->z,b->x,b->y,b->z,c->x,c->y,c->z,cull,&kept);
                any|=kept;dc_apos[ca->position]|=kept;dc_apos[cb->position]|=kept;dc_apos[cc->position]|=kept;
                dc_anrm[ca->normal]|=kept;dc_anrm[cb->normal]|=kept;dc_anrm[cc->normal]|=kept;
            }
            if(rp->src->role!=8){
                if(!(any&1)){dc_n[DC_V_A_DEADSTRIPS_N]++;dc_n[DC_V_A_DEADCORNERS_N]+=n;}
                if(!(any&2)){dc_n[DC_V_A_DEADSTRIPS_P]++;dc_n[DC_V_A_DEADCORNERS_P]+=n;}
                if(!(any&4)){dc_n[DC_V_A_CDEADSTRIPS_N]++;dc_n[DC_V_A_CDEADCORNERS_N]+=n;}
                if(!(any&8)){dc_n[DC_V_A_CDEADSTRIPS_P]++;dc_n[DC_V_A_CDEADCORNERS_P]+=n;}
            }
        }
        if(!(combined&32)){sq=m1_emit_actor_strip(sq,v,n,proj,lit);corners+=n;}
        else{
            clipstrips++;
            Corner a=clip_corner(v),b=clip_corner(v+1);
            for(unsigned j=2;j<n;j++){Corner c=clip_corner(v+j);clipped(&sq,j&1?b:a,j&1?a:b,c,near);a=b;b=c;}
        }
    }
    *emitted_parts+=header;
    if(!dc_mute){DC_ADD(DC_A_STRIPS,strips);DC_ADD(DC_A_STRIPS_OUT,out);DC_ADD(DC_A_CORNERS,corners);
                 DC_ADD(DC_A_CLIPSTRIPS,clipstrips);DC_ADD(DC_A_HEADERS,header);}
    return sq;
}
void native_actor_pass(NativeScene* s,unsigned translucent){
    const RtCatalog* cat=s->runtime;
    const ActorPose* pose=(const void*)s->state[1];const ActorPose* end=pose+s->words[1]/16;
    const float* camera=(const float*)s->state[0];float near=camera[18]/(camera[17]-1),far=camera[25];
    volatile unsigned* census=m1_part_counts[(m1_state[1]-1)%300];
    if(!translucent){census[0]=census[1]=0;actor_frame_setup(s);++actor_serial;content_actor_frame();content_light_frame(s);}
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
        uint8_t* strip_codes=strip_code_pool[model!=0];cur_strip_codes=strip_codes;
        if(translucent){   /* eng-look: Leon's hair layer (role 8) of the model drawn this picture */
            unsigned emitted=0;m=cat->m+lod_chosen[ordinal];h=m->h;cur_pos=m->pos;
            for(unsigned p=0;p<h[4];p++)if(m->parts[p].src->role==8 && state[p])sq=emit_part(sq,s,m,m->parts+p,state[p],near,&emitted);
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
        if(all){memset(state,0,16);census[1]+=considered;lod_chosen[ordinal]=model;continue;}
        if(content_card(s,actor,h[0],model,ordinal,m1_content[CS_CARDS]?actor_px(s,lo,hi):1e9f,s->assets.header.n)){memset(state,0,16);lod_chosen[ordinal]=model;continue;}
        {unsigned v=content_pick(s,model,lo,hi,ordinal);if(v!=model){m=cat->m+v;h=m->h;cur_pos=m->pos;}}   /* eng-look */
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
            unsigned st=part_class_flat((const float (*)[4])frustum,m->spheres+rp->sphere_first,rp->sphere_count,(const float (*)[12])bone_rows,bone_scale);
            state[p]=st;visible+=st!=0;
            if(!st)census[1]++;
        }
        if(!visible)continue;
        /* lane eng-draw3 (E3): Leon's knife part (role 2), drawn in the knife stance only, is not skinned or lit out of it */
        if(!model && !knife_stance(s))for(unsigned p=0;p<h[4];p++)if(m->parts[p].src->role==2)state[p]=0;
        if(m->sided)for(unsigned p=0;p<h[4];p++)if(state[p]==1)state[p]=2;   /* arm CB: every drawn part's strips tested */
        /* 4. weight sets used by visible parts */
        int lit_fill=0;uint32_t* lit_cached=content_lit(s,actor,h[0],model,lod_chosen[ordinal],m,ordinal,
            m1_content[CS_BAKED]==3?actor_px(s,lo,hi):1e9f,&lit_fill);   /* eng-look: step B (baked lighting cache) */
        ws_light_off=lit_cached && !lit_fill;
        if(!ws_light_off)source_lights(s,actor,h[0],model_light(s,actor),&cur_lights);
        memset(ws_ready,0,h[1]);
        ws_begin();
        for(unsigned p=0;p<h[4];p++){
            if(!state[p])continue;const RtPart* rp=m->parts+p;
            for(unsigned k=0;k<rp->ws_count;k++){unsigned i=m->part_ws[rp->ws_first+k];if(!ws_ready[i])build_ws(m,i);}
        }
        if(lit_fill)for(unsigned i=0;i<h[1];i++)if(!ws_ready[i])build_ws(m,i);
        /* 5. positions and normals of visible parts */
        for(unsigned p=0;p<h[4];p++){
            if(!state[p])continue;const RtPart* rp=m->parts+p;const unsigned st_p=state[p];
            unsigned n=rp->pos_count;
            pos_records[n][0]=pos_records[n+1][0]=0;
            PositionPass a={pos_records,n,m->pos+rp->pos_first,dummy_uv,(void*)(proj+rp->pos_first),codes+rp->pos_first,8,
                            skin_project[0].elem,ws_ready,h[1],640,480,near,far,0,0,0,0};
            re4dc_avk_pos_skin_u16(&a);
            if(DC_ARM(DL_SKIN2))re4dc_avk_pos_skin_u16(&a);   /* lane eng-draw1 lab arm (bench): positions skinned twice */
            pos_records[n][0]=n;pos_records[n+1][0]=n+1;
            /* lane eng-draw3 (E3): a boundary part's strips are tested here; only its kept strips' normals are lit */
            light_part(m,rp,st_p,codes,strip_codes,lit,!lit_cached);
        }
        if(lit_fill){const RtPart* lp=m->parts+h[4]-1;light_normals_source(m->nrm,lp->nrm_first+lp->nrm_count,lit_cached);}
        if(lit_cached)cur_lit=lit_cached;
        /* 6. opaque parts now; hair (role 7) in the translucent pass from the same pools */
        unsigned emitted=0;
        for(unsigned p=0;p<h[4];p++){
            if(!state[p] || m->parts[p].src->role==8)continue;
            /* Leon's role-2 part is the knife in hand: drawn in the knife stance only (eng-e0b: the recorded stance,
               PlGetWeaponNo() == 0x10); its state is 0 out of it (above) */
            unsigned before=emitted;sq=emit_part(sq,s,m,m->parts+p,state[p],near,&emitted);
            if(emitted==before)census[1]++;
        }
    }
    sq_wait();sq_unlock();
}
