#include "native_world.h"
#include <math.h>
#include <string.h>
#include <stdlib.h>
/* The pack is 32-byte aligned and every R4IM / R4SG field is naturally aligned (strides 68, 36, 28, 20, 16, 12, 8):
   direct loads. (memcpy-based reads became a libc call per field, 10,000 a picture.) */
static inline uint32_t u32(const void* p){return *(const uint32_t*)p;}
static inline uint16_t u16(const void* p){return *(const uint16_t*)p;}
static inline float f32(const void* p){return *(const float*)p;}
static int range(unsigned off,unsigned count,unsigned stride,unsigned size){
    return off<=size && count<=(size-off)/stride;
}
int native_world_open(NativeWorld* w,const void* data,size_t size){
    const uint8_t* b=data;
    if(size<28||memcmp(b,"NWR3",4))return 0;
    unsigned n=u32(b+4),c=u32(b+8),ml=u32(b+12),mt=u32(b+16),pl=u32(b+20),cl=u32(b+24);
    if(ml<112 || (uint64_t)28+ml+mt+pl+cl>size || (uint64_t)n*84!=pl || (uint64_t)c*32!=cl)return 0;
    const uint8_t *m=b+28;
    if(memcmp(m,"R4IM",4)||u32(m+4)!=3||u32(m+8)!=ml||u32(m+20)*(uint64_t)8!=mt)return 0;
    const unsigned strides[]={68,36,28,12,1,4};
    for(unsigned k=0;k<6;k++)if(!range(u32(m+40+4*k),u32(m+16+4*k),strides[k],ml))return 0;
    if(!range(u32(m+88),u32(m+20),8,ml)||!range(u32(m+92),u32(m+80),20,ml)||!range(u32(m+96),u32(m+84),12,ml))return 0;
    *w=(NativeWorld){m,m+ml+mt+pl+cl,(const void*)(m+ml),(const void*)(m+ml+mt),(const void*)(m+ml+mt+pl),c,n,size-(28+ml+mt+pl+cl)};
    if(w->group_bytes && (w->group_bytes<32 || memcmp(w->groups,"R4SG",4) ||
        u32(w->groups+12)>32 || 32+(uint64_t)16*u32(w->groups+12)*u32(m+24)!=w->group_bytes))return 0;
    for(unsigned i=0;i<u32(m+24);i++){
        const uint8_t* info=m+u32(m+48)+28*i;
        unsigned base=u32(info),start=u32(info+4),span=u32(info+8),verts=u16(info+12);
        int indexed=u16(info+14)&32768;
        if(verts>256 || !range(start,span+(indexed?2*verts:0),1,u32(m+32)))return 0;
        const uint8_t* strip=m+u32(m+56)+start;
        for(unsigned j=0;j<verts;j++)if((uint64_t)base+(indexed?u16(strip+2*j):j)>=u32(m+28))return 0;
        if(indexed)strip+=2*verts;
        for(unsigned j=0;j<span;){
            unsigned length=strip[j++];if(length<3||length>span-j)return 0;
            for(unsigned k=0;k<length;k++)if(strip[j++]>=verts)return 0;
        }
    }
    for(unsigned i=0;i<c;i++)if(!range(w->cells[i].first,w->cells[i].count,1,n))return 0;
    for(unsigned i=0;i<n;i++)if(w->places[i].mesh>=u32(m+16))return 0;
    for(unsigned i=0;i<u32(m+16);i++){
        const uint8_t *r=m+u32(m+40)+68*i;
        if(!range(u32(r+12),u32(r+16),1,u32(m+20)))return 0;
    }
    for(unsigned i=0;i<u32(m+20);i++){
        const uint8_t *r=m+u32(m+88)+8*i;
        if(!range(u32(r),u32(r+4),1,u32(m+80)))return 0;
    }
    for(unsigned i=0;i<u32(m+80);i++){
        const uint8_t *r=m+u32(m+92)+20*i;
        if(!u32(r+16)||!range(u32(r+12),u32(r+16),1,u32(m+84)))return 0;
    }
    for(unsigned i=0;i<u32(m+84);i++){
        const uint8_t *r=m+u32(m+96)+12*i;
        if(!range(u32(r),u32(r+4),1,u32(m+24)))return 0;
    }
    return 1;
}
// Plane equations in object coordinates allow all children to share one transform.
static void compose(NativeFrustum* out,const NativeFrustum* in,const float* m){
    for(unsigned p=0;p<6;p++)for(unsigned j=0;j<4;j++)
        out->p[p][j]=in->p[p][0]*m[j]+in->p[p][1]*m[j+4]+in->p[p][2]*m[j+8]+(j==3?in->p[p][3]:0);
}
/* Box against the planes in 'in'; returns 0 when outside one of them, else stores in *mask the planes the box
   straddles. Children of a box test only the planes their parent straddled. Plane 0 (near) always gives the
   box's nearest distance for the level choice. */
static inline int box_test(const NativeFrustum* f,unsigned in,const float* c,const float* h,unsigned* mask,float* nearest){
    unsigned m=0;
    {
        const float* p=f->p[0];
        float s=p[0]*c[0]+p[1]*c[1]+p[2]*c[2]+p[3];
        float r=fabsf(p[0])*h[0]+fabsf(p[1])*h[1]+fabsf(p[2])*h[2];
        *nearest=s-r;
        if(in&1){if(s+r<0)return 0;if(s<r)m=1;}
    }
    for(unsigned i=1;i<6;i++){
        if(!(in&(1u<<i)))continue;
        const float* p=f->p[i];
        float s=p[0]*c[0]+p[1]*c[1]+p[2]*c[2]+p[3];
        float r=fabsf(p[0])*h[0]+fabsf(p[1])*h[1]+fabsf(p[2])*h[2];
        if(s+r<0)return 0;
        if(s<r)m|=1u<<i;
    }
    *mask=m;return 1;
}
static inline int grid_test(const NativeFrustum* f,unsigned in,const uint8_t* r,unsigned* mask,float* nearest){
    float c[3],h[3];
    for(unsigned i=0;i<3;i++){float a=u16(r+2*i),b=u16(r+6+2*i);c[i]=(a+b)*.5f;h[i]=(b-a)*.5f;}
    return box_test(f,in,c,h,mask,nearest);
}
void native_world_frustum(const float* camera,NativeFrustum* world){
    const float* p=camera+12;
    float near=p[6]/(p[5]-1),far=camera[25];
    NativeFrustum view={{{0,0,-1,-near},{0,0,1,far},{p[1],0,p[2]-1,0},{-p[1],0,-p[2]-1,0},{0,p[3],p[4]-1,0},{0,-p[3],-p[4]-1,0}}};
    compose(world,&view,camera);
}
/* Load-time layout for the draw: per meshlet, each strip group gets its own contiguous vertex range (vertices
   shared between groups are listed once per group), so a picture stages only the selected groups' vertices, once
   each. Strip indices are rewritten in place to the new order. A meshlet whose grouped list would pass 255
   keeps its order and stages whole. */
int native_world_runtime(NativeWorld* w){
    const uint8_t* m=w->mesh;unsigned nm=u32(m+24);
    unsigned G=w->group_bytes?u32(w->groups+12):1;
    w->group_count=G;
    w->rt=calloc(nm,sizeof(NativeMeshletRt));w->rt_range=malloc(2*nm*G+2);
    if(!w->rt||!w->rt_range)return 0;
    unsigned total=0,dup=0,full=0;
    static int16_t map[256];
    for(int pass=0;pass<2;pass++){
        unsigned at=0;
        for(unsigned l=0;l<nm;l++){
            const uint8_t* info=m+u32(m+48)+28*l;
            unsigned start=u32(info+4),span=u32(info+8),verts=u16(info+12);int indexed=u16(info+14)&32768;
            uint8_t* strip=(uint8_t*)(m+u32(m+56)+start);const uint16_t* src=indexed?(const uint16_t*)strip:NULL;
            if(indexed)strip+=2*verts;
            NativeMeshletRt* rt=w->rt+l;uint8_t* range=w->rt_range+2*G*l;
            unsigned n=0,before=0,nonempty=0;
            for(unsigned g=0;g<G;g++){
                unsigned after=w->group_bytes?u16(w->groups+32+16*(l*G+g)+12):span;
                if(after>before)nonempty|=1u<<g;
                for(unsigned i=0;i<256;i++)map[i]=-1;
                unsigned first=n;
                for(unsigned j=before;j<after;){unsigned len=strip[j++];
                    for(unsigned k=0;k<len;k++,j++){unsigned v=strip[j];if(map[v]<0)map[v]=n++;}}
                range[2*g]=first>255?255:first;range[2*g+1]=n-first>255?255:n-first;
                before=after;
            }
            rt->nonempty=nonempty;
            if(n>255){rt->full=1;n=verts;for(unsigned g=0;g<G;g++){range[2*g]=0;range[2*g+1]=verts;}}
            rt->count=n;rt->remap=at;
            if(pass){
                if(rt->full){for(unsigned i=0;i<verts;i++)w->rt_remap[at+i]=src?src[i]:i;full++;}
                else{
                    before=0;
                    for(unsigned g=0;g<G;g++){
                        unsigned after=w->group_bytes?u16(w->groups+32+16*(l*G+g)+12):span;
                        for(unsigned i=0;i<256;i++)map[i]=-1;
                        unsigned next=range[2*g];
                        for(unsigned j=before;j<after;){unsigned len=strip[j++];
                            for(unsigned k=0;k<len;k++,j++){unsigned v=strip[j];
                                if(map[v]<0){map[v]=next;w->rt_remap[at+next]=src?src[v]:v;next++;}
                                strip[j]=map[v];}}
                        before=after;
                    }
                    dup+=n-verts;
                }
            }
            at+=n;
        }
        if(!pass){total=at;w->rt_remap=malloc(2*total+2);if(!w->rt_remap)return 0;}
    }
    /* Vertex colours in TA form per staged vertex (the material decides 4444 or 555), in staging order. */
    w->rt_color=malloc(4*total+8);if(!w->rt_color)return 0;
    uint8_t* flags=calloc(nm,1);if(!flags)return 0;
    const uint8_t *meshes=m+u32(m+40),*plod=m+u32(m+88),*clusters=m+u32(m+92),*levels=m+u32(m+96);
    unsigned conflicts=0;
    for(unsigned part=0;part<u32(m+20);part++){
        unsigned f=(w->materials[part].flags&1)|2;
        unsigned a=u32(plod+8*part),b=a+u32(plod+8*part+4);
        for(unsigned k=a;k<b;k++){
            const uint8_t* cl=clusters+20*k;unsigned lev=u32(cl+12),last=lev+u32(cl+16);
            for(;lev<last;lev++){unsigned l=u32(levels+12*lev),stop=l+u32(levels+12*lev+4);
                for(;l<stop;l++){if(flags[l] && flags[l]!=f)conflicts++;flags[l]=f;}}
        }
    }
    (void)meshes;
    for(unsigned l=0;l<nm;l++){
        const uint8_t* info=m+u32(m+48)+28*l;
        const uint16_t* vertices=(const uint16_t*)(m+u32(m+52)+12*u32(info));
        for(unsigned i=0;i<w->rt[l].count;i++)
            w->rt_color[w->rt[l].remap+i]=world_color(vertices[6*w->rt_remap[w->rt[l].remap+i]+5],flags[l]&1);
    }
    free(flags);w->rt_flag_conflicts=conflicts;
    {
        uint16_t* v=(uint16_t*)(m+u32(m+52));unsigned n=u32(m+28);
        for(unsigned i=0;i<n;i++,v+=6){v[0]^=0x8000;v[1]^=0x8000;v[2]^=0x8000;v[3]^=0x8000;v[4]^=0x8000;}
        for(unsigned part=0;part<u32(m+20);part++){
            float* uv=(float*)(m+u32(m+44)+36*part+20);
            uv[0]+=32768.f*uv[2];uv[1]+=32768.f*uv[3];
        }
    }
    w->rt_vertices=total;w->rt_duplicates=dup;w->rt_full=full;
    return 1;
}
/* Stored mask: a mode byte, then raw bits (0) or runs (1): alternating runs starting with zeros, u8 lengths,
   255 = 255 and continue. Returns the bits decoded (into out, if given) and the bytes read in *used; 0 on a
   malformed stream. */
static unsigned vis_rle(const uint8_t* p,const uint8_t* end,unsigned nbits,uint8_t* out,unsigned* used){
    if(p>=end)return 0;
    if(*p==0){unsigned n=(nbits+7)/8;if((unsigned)(end-p)<1+n)return 0;if(out)memcpy(out,p+1,n);*used=1+n;return nbits;}
    if(*p!=1)return 0;
    unsigned at=0,bit=0;const uint8_t* q=p+1;
    if(out)memset(out,0,(nbits+7)/8);
    while(at<nbits){
        unsigned run=0;
        for(;;){if(q>=end)return 0;unsigned r=*q++;run+=r;if(r!=255)break;}
        if(at+run>nbits)return 0;
        if(bit && out){
            unsigned i=at,e=at+run;
            for(;i<e && (i&7);i++)out[i>>3]|=1u<<(i&7);
            for(;i+8<=e;i+=8)out[i>>3]=0xff;
            for(;i<e;i++)out[i>>3]|=1u<<(i&7);
        }
        at+=run;bit^=1;
    }
    *used=q-p;return at;
}
int native_vis_open(NativeVis* v,const void* data,size_t size,const NativeWorld* w){
    const uint32_t* h=data;const float* f=(const float*)(h+16);
    memset(v,0,sizeof(*v));
    if(size<128||h[0]!=0x32534956||h[14]!=size||h[2]!=w->place_count)return 0;
    v->ninst=h[1];v->nplace=h[2];v->nx=h[3];v->nz=h[4];v->ncells=h[5];v->ni=h[6];v->ibytes=h[7];
    v->ax=h[8];v->ay=h[9];v->az=h[10];v->nbits=h[11];v->cbytes=h[12];v->nc=h[13];
    v->org[0]=f[0];v->org[1]=f[1];v->cell=f[2];v->alo[0]=f[3];v->alo[1]=f[4];v->alo[2]=f[5];v->acube=f[6];v->yunit=f[7];
    if(v->ibytes!=(v->ninst+7)/8||v->cbytes!=(v->nbits+7)/8||!(v->cell>0)||!(v->acube>0)||!(v->yunit>0)||v->ni>=0xffff||v->nc>=0xffff)return 0;
    uint64_t at=128+4ull*(2*v->nplace+1),rows=at;at+=8ull*v->nz;
    uint64_t cells=at;at+=8ull*v->ncells;uint64_t cols=at;at+=4ull*v->ax*v->az;
    uint64_t ioff=at;at+=4ull*(v->ni+1);uint64_t coff=at;at+=4ull*(v->nc+1);
    if(at>size)return 0;
    v->place_base=h+32;v->mesh_first=v->place_base+v->nplace+1;
    v->rows=(const uint32_t*)((const uint8_t*)data+rows);v->cells=(const void*)((const uint8_t*)data+cells);
    v->cols=(const void*)((const uint8_t*)data+cols);v->ioff=(const void*)((const uint8_t*)data+ioff);
    v->coff=(const void*)((const uint8_t*)data+coff);v->rle=(const uint8_t*)data+at;
    size_t rle_bytes=size-at;
    if(v->place_base[v->nplace]!=v->ninst)return 0;
    /* rows: spans inside the grid and the cell array */
    for(unsigned z=0;z<v->nz;z++){
        unsigned x0=v->rows[2*z]&0xffff,n=v->rows[2*z]>>16,first=v->rows[2*z+1];
        if(x0+n>v->nx||first+(uint64_t)n>v->ncells)return 0;
    }
    for(unsigned k=0;k<v->ncells;k++){
        const NativeVisCell* c=v->cells+k;
        if((c->imask==0xffff)!=(c->cmask==0xffff))return 0;
        if(c->imask!=0xffff && (c->imask>=v->ni||c->cmask>=v->nc||c->ylo>c->yhi))return 0;
    }
    for(unsigned k=0;k<v->ax*v->az;k++){
        const NativeVisColumn* c=v->cols+k;
        if(c->ny && (c->bit>=v->nbits||c->y0+(unsigned)c->ny>v->ay))return 0;
    }
    /* every mask decodes to exactly its bit count and stays inside the stream */
    for(unsigned k=0;k<v->ni;k++){unsigned used;
        if(v->ioff[k]>v->ioff[k+1]||v->ioff[k+1]>rle_bytes)return 0;
        if(vis_rle(v->rle+v->ioff[k],v->rle+v->ioff[k+1],v->ninst,NULL,&used)!=v->ninst||used!=v->ioff[k+1]-v->ioff[k])return 0;}
    for(unsigned k=0;k<v->nc;k++){unsigned used;
        if(v->coff[k]>v->coff[k+1]||v->coff[k+1]>rle_bytes)return 0;
        if(vis_rle(v->rle+v->coff[k],v->rle+v->coff[k+1],v->nbits,NULL,&used)!=v->nbits||used!=v->coff[k+1]-v->coff[k])return 0;}
    /* every placement's cluster range must match the world */
    const uint8_t* m=w->mesh;const uint8_t *meshes=m+u32(m+40),*plod=m+u32(m+88);
    for(unsigned j=0;j<v->nplace;j++){
        if(w->places[j].sky){if(v->place_base[j+1]!=v->place_base[j])return 0;continue;}
        const uint8_t* mh=meshes+68*w->places[j].mesh;unsigned first=u32(mh+12),end=first+u32(mh+16),lo=~0u,hi=0;
        for(unsigned part=first;part<end;part++){unsigned a=u32(plod+8*part),b=a+u32(plod+8*part+4);if(b>a){if(a<lo)lo=a;if(b>hi)hi=b;}}
        if(lo==~0u){lo=hi=0;}
        if(v->mesh_first[j]!=lo||v->place_base[j+1]-v->place_base[j]!=hi-lo)return 0;
    }
    v->ibits=malloc(v->ibytes+4);v->cbits=malloc(v->cbytes+4);
    if(!v->ibits||!v->cbits)return 0;
    v->cur_i=v->cur_c=~0u;
    return 1;
}
void native_vis_close(NativeVis* v){free(v->ibits);free(v->cbits);v->ibits=v->cbits=NULL;}
/* The camera's cell and band select this picture's hidden sets; anything the table does not cover draws all. */
unsigned native_vis_select(NativeWorld* w,const float* c){
    w->vis_inst=w->vis_cubes=NULL;
    NativeVis* v=w->vis;if(!v)return VIS_NONE;
    float x=-(c[0]*c[3]+c[4]*c[7]+c[8]*c[11]),y=-(c[1]*c[3]+c[5]*c[7]+c[9]*c[11]),z=-(c[2]*c[3]+c[6]*c[7]+c[10]*c[11]);
    float fx=(x-v->org[0])/v->cell,fz=(z-v->org[1])/v->cell;
    if(!(fx>=0)||!(fz>=0))return VIS_OUTSIDE;
    unsigned cx=(unsigned)fx,cz=(unsigned)fz;
    if(cx>=v->nx||cz>=v->nz)return VIS_OUTSIDE;
    unsigned x0=v->rows[2*cz]&0xffff,n=v->rows[2*cz]>>16;
    if(cx<x0||cx>=x0+n)return VIS_UNBAKED;
    const NativeVisCell* cell=v->cells+v->rows[2*cz+1]+(cx-x0);
    if(cell->imask==0xffff)return VIS_UNBAKED;
    if(!(y>=cell->ylo*v->yunit && y<=cell->yhi*v->yunit))return VIS_HEIGHT;
    unsigned used;
    if(v->cur_i!=cell->imask){vis_rle(v->rle+v->ioff[cell->imask],v->rle+v->ioff[cell->imask+1],v->ninst,v->ibits,&used);v->cur_i=cell->imask;}
    if(v->cur_c!=cell->cmask){vis_rle(v->rle+v->coff[cell->cmask],v->rle+v->coff[cell->cmask+1],v->nbits,v->cbits,&used);v->cur_c=cell->cmask;}
    w->vis_inst=v->ibits;w->vis_cubes=v->cbits;
    return VIS_MASK;
}
/* eng-look content step W: clusters whose nearest point is past native_world_lod_dist (mm) take their level
   native_world_lod_shift steps coarser (clamped to the last level). 0 = the projected-size level only (today). */
unsigned native_world_lod_shift;float native_world_lod_dist;
void native_world_free(NativeWorld* w){free(w->rt_color);w->rt_color=NULL;free(w->rt);free(w->rt_remap);free(w->rt_range);w->rt=NULL;w->rt_remap=NULL;w->rt_range=NULL;}
int native_world_select(const NativeWorld* w,const float* camera,float pixels,NativePiece* out,unsigned capacity){
    const float* p=camera+12;
    float near=p[6]/(p[5]-1);
    NativeFrustum world;native_world_frustum(camera,&world);
    const uint8_t* m=w->mesh;
    const uint8_t *meshes=m+u32(m+40),*plod=m+u32(m+88),*clusters=m+u32(m+92),*levels=m+u32(m+96),*meshlets=m+u32(m+48);
    unsigned count=0,G=w->group_count;
    for(unsigned i=0;i<w->cell_count;i++){
        float z;unsigned cm;const NativeCell* cell=w->cells+i;
        if(!box_test(&world,63,cell->center,cell->half,&cm,&z))continue;
        for(unsigned j=cell->first;j<cell->first+cell->count;j++){
            const NativePlacement* place=w->places+j;unsigned pm;
            if(place->sky||!box_test(&world,cm,place->center,place->half,&pm,&z))continue;
            NativeFrustum local;compose(&local,&world,place->grid);
            const uint8_t* hidden=w->vis_inst;unsigned hidden_base=hidden?w->vis->place_base[j]-w->vis->mesh_first[j]:0;
            const uint8_t* mesh=meshes+68*place->mesh;
            unsigned first=u32(mesh+12),end=first+u32(mesh+16);
            float lod=fabsf(p[1])*320*place->scale/pixels;
            for(unsigned part=first;part<end;part++){
                const uint8_t* span=plod+8*part;
                unsigned a=u32(span),b=a+u32(span+4);
                unsigned header=w->materials[part].header;
                for(unsigned k=a;k<b;k++){
                    const uint8_t* cl=clusters+20*k;unsigned km;
                    if(hidden){unsigned q=hidden_base+k;if(hidden[q>>3]>>(q&7)&1)continue;}
                    if(!grid_test(&local,pm,cl,&km,&z))continue;
                    unsigned lev=u32(cl+12),last=lev+u32(cl+16);
                    while(lev+1<last && f32(levels+12*(lev+1)+8)*lod<=z+near)++lev;
                    if(native_world_lod_shift && z+near>native_world_lod_dist){lev+=native_world_lod_shift;if(lev>=last)lev=last-1;}   /* eng-look */
                    unsigned l=u32(levels+12*lev),stop=l+u32(levels+12*lev+4);
                    for(;l<stop;l++){
                        unsigned lm=0;
                        if(km && !grid_test(&local,km,meshlets+28*l+16,&lm,&z))continue;
                        if(count>=capacity)return -1;
                        unsigned mask=w->rt[l].nonempty;
                        if(lm && w->group_bytes){
                            const uint8_t* group=w->groups+32+16*(l*G);unsigned keep=0;
                            for(unsigned g=0;g<G;g++,group+=16){unsigned gm;
                                if((mask>>g&1) && grid_test(&local,lm,group,&gm,&z))keep|=1u<<g;}
                            mask=keep;
                            if(!mask)continue;
                        }
                        out[count++]=(NativePiece){j,part,l,header,lm&1?2:1,mask};
                    }
                }
            }
        }
    }
    return count;
}
