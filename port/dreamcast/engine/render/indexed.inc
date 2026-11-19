/* Shared with the game's generated avk_sh4.S. The assembly reads two records
   ahead. The dummy UV and guarded identity records are always addressable. */
typedef struct {
    const void *records; unsigned count; const SourceVector *positions;
    const uint16_t *uv; void *output; uint8_t *outcode; unsigned stride;
    const float *matrices; const uint8_t *ready; unsigned entries;
    float width,height,near_plane,far_plane,au,bu,av,bv;
} PositionPass;
typedef struct {
    const void *records; unsigned count; const SourceVector *normals;
    uint32_t *output; unsigned stride; const float *colors,*directions;
    const uint8_t *ready; unsigned entries,alpha;
} NormalPass;
extern unsigned re4dc_avk_pos_skin_u16(const PositionPass*);
extern unsigned re4dc_avk_pos_rigid_u16(const PositionPass*);
extern unsigned re4dc_avk_light_skin_n16(const NormalPass*);
extern unsigned re4dc_avk_light_rigid_n16(const NormalPass*);
_Static_assert(sizeof(PositionPass)==72 && sizeof(NormalPass)==40,"AVK ABI");

static uint16_t records[INDEX_LIMIT+2][4] __attribute__((aligned(32)));
static const uint16_t dummy_uv[2];
static pvr_vertex_t projected_local[INDEX_LIMIT] __attribute__((aligned(32)));
static pvr_vertex_t lit[INDEX_LIMIT] __attribute__((aligned(32)));
static uint8_t codes_local[INDEX_LIMIT],ready[PALETTE_LIMIT];
static pvr_vertex_t projected_shared[8192] __attribute__((aligned(32)));
static uint8_t codes_shared[8192];
static shz_mat4x4_t matrices_shared[1536] __attribute__((aligned(32)));
static unsigned projected_at[1536],picture_serial;
static pvr_vertex_t *projected;
static uint8_t *codes;
static shz_mat4x4_t *skin;

static shz_mat4x4_t matrices_local[PALETTE_LIMIT] __attribute__((aligned(32)));
static float dirs[PALETTE_LIMIT][12] __attribute__((aligned(32)));


static void guard_records(unsigned n,int enable){
    for(unsigned i=n;i<n+2;i++)records[i][0]=records[i][1]=enable?0:i;
}
static void position_table(Transform *x,float q){
    if(!ready[0]){
        memset(ready,1,sizeof(ready));
        for(unsigned i=0;i<INDEX_LIMIT+2;i++)records[i][0]=records[i][1]=i;
    }

    for(unsigned i=0;i<(x->bones?x->bones:1);i++){
        matrix(x,i);skin[i]=x->m;
        for(unsigned col=0;col<4;col++){
            float *m=skin[i].elem+4*col;
            m[2]=m[3];
            if(col<3)for(unsigned j=0;j<4;j++)m[j]*=q;
        }
    }

}
typedef struct { unsigned flat,rgb,alpha,half; float dir[3][4],color[16],us,vs; } Fold;
static uint32_t light_normals(const IndexedPart *g,const SourceVector *normal,
                              const Light *l,const Transform *x,const Fold *fold){
    if(fold && fold->flat)return fold->alpha | fold->rgb;
    if(!fold && (!l || !l->n)){
        unsigned rgb=0xff;
        for(unsigned i=0;i<3;i++){float v=l?l->ambient[i]:255;rgb=rgb*256+(unsigned)(v>255?255:v);}
        return rgb;
    }
    float colors[16] __attribute__((aligned(8)))={0};
    unsigned count=fold?3:(l->n<3?l->n:3);
    if(fold)memcpy(colors,fold->color,sizeof(colors));else{
    for(unsigned i=0;i<count;i++)
        for(unsigned c=0;c<3;c++)colors[4*i+c]=.5f*l->lamp[i].rgb[c];
    memcpy(colors+12,l->ambient,12);
    }
    unsigned bones=x->bones?x->bones:1;
    for(unsigned bone=0;bone<bones;bone++){
        const float *p=x->bone_rows+12*bone;
        for(unsigned i=0;i<3;i++){
            const float *v=fold?fold->dir[i]:l->lamp[i].dir;
            for(unsigned c=0;c<3;c++){
                float d=x->bones?p[3*c]*v[0]+p[3*c+1]*v[1]+p[3*c+2]*v[2]:v[c];
                dirs[bone][4*i+c]=i<count?(fold?d:d*g->nq*32767.f):0;
            }
            dirs[bone][4*i+3]=0;
        }
    }
    NormalPass a={records,g->normals,normal,&lit[0].argb,8,colors,dirs[0],ready,bones,fold?fold->alpha:0xff000000};
    guard_records(g->normals,1);
    if(x->bones)re4dc_avk_light_skin_n16(&a);else re4dc_avk_light_rigid_n16(&a);
    guard_records(g->normals,0);
    if(fold && fold->half)for(unsigned i=0;i<g->normals;i++){unsigned c=lit[i].argb;lit[i].argb=(c&0xff000000)|((c>>1)&0x7f7f7f);}
    return 0;
}
static inline void indexed_emit(pvr_vertex_t **sq,const IndexCorner *c,const IndexedPart *g,
                                unsigned color,float us,float vs,float du,float dv,unsigned end){
    const pvr_vertex_t *v=projected+c->position;
    pvr_vertex_t *d=*sq;
    d->flags=end?PVR_CMD_VERTEX_EOL:PVR_CMD_VERTEX;
    d->x=v->x;d->y=v->y;d->z=v->z;
    int u=g->signed_uv?(int16_t)c->u:(int)c->u,vv=g->signed_uv?(int16_t)c->v:(int)c->v;
    d->u=u*us+du;d->v=vv*vs+dv;
    d->argb=color?color:lit[c->normal].argb;d->oargb=0;advance(sq);
}
static Corner clip_vertex(const IndexCorner *c,const IndexedPart *g,const SourceVector *pos,unsigned color,float us,float vs,float du,float dv){
    const pvr_vertex_t *v=projected+c->position;
    const SourceVector *p=pos+c->position;
    const float *m=skin[p->bone].elem;
    float w=m[3]*p->xyz[0]+m[7]*p->xyz[1]+m[11]*p->xyz[2]+m[15];
    float mag=w<0?-w:w;
    return (Corner){v->x*mag,v->y*mag,w,(g->signed_uv?(int16_t)c->u:(int)c->u)*us+du,
        (g->signed_uv?(int16_t)c->v:(int)c->v)*vs+dv,color?color:lit[c->normal].argb};
}
static void indexed_part(pvr_vertex_t **sq,Transform *x,const IndexedPart *g,const Light *l,const Fold *fold,const unsigned *shared){
    const SourceVector *pos=(const SourceVector*)(g+1),*norm=pos+g->positions;
    projected=shared?projected_shared+shared[0]:projected_local;
    codes=shared?codes_shared+shared[0]:codes_local;
    skin=shared?matrices_shared+shared[1]:matrices_local;
    if(!shared || projected_at[shared[1]]!=picture_serial){
    position_table(x,g->q);
    PositionPass a={records,g->positions,pos,dummy_uv,projected,codes,8,skin[0].elem,ready,x->bones,
        640,480,x->near,x->camera[18]/x->camera[17],0,0,0,0};
    guard_records(g->positions,1);
    if(x->bones)re4dc_avk_pos_skin_u16(&a);else re4dc_avk_pos_rigid_u16(&a);
    guard_records(g->positions,0);
    if(shared)projected_at[shared[1]]=picture_serial;
    }
    unsigned color=light_normals(g,norm,l,x,fold);
    const uint32_t *p=(const uint32_t*)(norm+g->normals);
    float scale=g->signed_uv?1.f/256:1.f/32768;
    float su=fold?fold->us:1,sv=fold?fold->vs:1;
    float us=scale*su,vs=scale*sv,du=g->du*su,dv=g->dv*sv;
    for(unsigned s=0;s<g->strips;s++){
        unsigned n=*p++,all=63,any=0;const IndexCorner *c=(const IndexCorner*)p;
        p=(const uint32_t*)(c+n);
        for(unsigned j=0;j<n;j++){unsigned oc=codes[c[j].position];all&=oc;any|=oc;}
        if(all)continue;
        if(!(any&32)){
            for(unsigned j=0;j<n;j++){__builtin_prefetch(c+j+4);indexed_emit(sq,c+j,g,color,us,vs,du,dv,j+1==n);}
        }else{
            Corner prev=clip_vertex(c,g,pos,color,us,vs,du,dv),curr=clip_vertex(c+1,g,pos,color,us,vs,du,dv);
            for(unsigned j=2;j<n;j++){
                Corner next=clip_vertex(c+j,g,pos,color,us,vs,du,dv);
                clipped(sq,j&1?curr:prev,j&1?prev:curr,next,x->near);prev=curr;curr=next;
            }
        }
    }
}
