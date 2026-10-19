/* EDCL decoder/sampler math reused from edemo18, generalized for phase 1B.
 * Bounded loading is outside the tick. Pose buffers and masks belong to the
 * actor adapter; immutable clips can be shared without sharing pose/clocks. */
#include "pose_service.h"
#include <math.h>
#include <string.h>

static uint16_t u16(const uint8_t *p) { return (uint16_t)(p[0] | (p[1] << 8)); }
static uint32_t u32(const uint8_t *p) { return (uint32_t)u16(p) | ((uint32_t)u16(p+2) << 16); }
static int16_t i16(const uint8_t *p) { return (int16_t)u16(p); }
static float f32(const uint8_t *p) { uint32_t u=u32(p); float f; memcpy(&f,&u,4); return f; }
static int take(size_t *at, size_t amount, size_t size)
{
    if (*at > size || amount > size-*at) return 0;
    *at += amount;
    return 1;
}
static uint16_t key_count(uint32_t frames, unsigned shift)
{
    return (uint16_t)(((frames-1 + ((1u<<shift)-1)) >> shift)+1);
}

int re4ps_validate_skeleton(const re4ps_skeleton *s)
{
    uint32_t i;
    if (!s || !s->bone_count || !s->parent || !s->rest_translation) return RE4PS_ARGUMENT;
    if (s->bone_count > INT32_MAX) return RE4PS_CAPACITY;
    for (i=0; i<s->bone_count; ++i) {
        unsigned j;
        if (s->parent[i] < -1 || s->parent[i] >= (int32_t)i) return RE4PS_HIERARCHY;
        for (j=0; j<3; ++j) if (!isfinite(s->rest_translation[3*i+j])) return RE4PS_NUMERIC;
    }
    return RE4PS_OK;
}

static int parse_clip(re4ps_clip *out, re4ps_track *tracks, const uint8_t *p,
                      size_t bytes, const re4ps_skeleton *s, unsigned version)
{
    size_t at=4;
    uint32_t i, nf;
    re4ps_clip result;
    if (bytes<4 || !u16(p) || p[2]!=s->bone_count ||
        p[3]!=(version==1?RE4PS_DEMO_FINAL:RE4PS_SOURCE_LOCAL)) return RE4PS_FORMAT;
    nf=u16(p);
    for (i=0; i<s->bone_count; ++i) {
        re4ps_track t;
        uint8_t flags;
        size_t start;
        uint32_t k;
        if (!take(&at,1,bytes)) return RE4PS_FORMAT;
        flags=p[at-1];
        memset(&t,0,sizeof(t));
        t.rotation_shift=(flags>>3)&3;
        t.translation_shift=(flags>>5)&3;
        t.translation_mode=flags&6;
        if (t.translation_mode==4) return RE4PS_FORMAT;
        t.rotation_keys=(flags&1)?key_count(nf,t.rotation_shift):1;
        start=at;
        if (!take(&at,6u*t.rotation_keys,bytes)) return RE4PS_FORMAT;
        t.rotation=p+start;
        /* Bit 47 is reserved; the dropped quaternion index occupies bits 45..46. */
        for (k=0;k<t.rotation_keys;++k) if (t.rotation[6*k+5]&0x80) return RE4PS_FORMAT;
        t.translation_keys=1;
        if (t.translation_mode) {
            start=at;
            if (!take(&at,4,bytes)) return RE4PS_FORMAT;
            t.translation_scale=f32(p+start);
            if (!isfinite(t.translation_scale) || t.translation_scale<=0) return RE4PS_NUMERIC;
            t.translation_keys=t.translation_mode==2?1:key_count(nf,t.translation_shift);
            start=at;
            if (!take(&at,6u*t.translation_keys,bytes)) return RE4PS_FORMAT;
            t.translation=p+start;
        }
        if (flags&0x80) {
            start=at;
            if (!take(&at,6u*nf,bytes)) return RE4PS_FORMAT;
            t.scale=p+start;
        }
        tracks[i]=t;
    }
    if (!take(&at,(4-at%4)%4,bytes) || !take(&at,4,bytes)) return RE4PS_FORMAT;
    result.root_scale=f32(p+at-4);
    if (!isfinite(result.root_scale) || result.root_scale<=0) return RE4PS_NUMERIC;
    result.root_track=p+at;
    if (!take(&at,12u*nf,bytes)) return RE4PS_FORMAT;
    result.bone_count=s->bone_count; result.frames=nf; result.tracks=tracks;
    result.pose_stage=p[3];
    *out=result;
    return RE4PS_OK;
}

int re4ps_open_edcl(re4ps_clip *out,re4ps_track *tracks,size_t capacity,
                   const void *data,size_t bytes,uint16_t entry,const re4ps_skeleton *s)
{
    const uint8_t *p=(const uint8_t *)data;
    size_t first, selected=0, end=bytes;
    uint32_t count, i, prev=0, version;
    int found=0, result;
    if (!out || !tracks || !p) return RE4PS_ARGUMENT;
    memset(out,0,sizeof(*out));
    result=re4ps_validate_skeleton(s);
    if (result) return result;
    if (capacity<s->bone_count) return RE4PS_CAPACITY;
    if (bytes<8 || memcmp(p,"EDCL",4)) return RE4PS_FORMAT;
    version=u16(p+4);
    if (version!=1 && version!=2) return RE4PS_FORMAT;
    count=u16(p+6); first=8u+8u*count;
    if (!count || first>bytes) return RE4PS_FORMAT;
    for (i=0;i<count;++i) {
        const uint8_t *e=p+8+8*i;
        uint32_t offset=u32(e+4);
        if (offset<first || offset>=bytes || (i && offset<=prev)) return RE4PS_FORMAT;
        if (found && !end) end=offset;
        if (u16(e)==entry) {
            if (found) return RE4PS_FORMAT;
            selected=offset; found=1; end=0;
            if (bytes-offset<4 || u16(e+2)!=u16(p+offset)) return RE4PS_FORMAT;
        }
        prev=offset;
    }
    if (!found) return RE4PS_FORMAT;
    if (!end) end=bytes;
    return parse_clip(out,tracks,p+selected,end-selected,s,version);
}

int re4ps_required(const re4ps_skeleton *s,const uint8_t *requested,
                   const re4ps_dependency *dep,size_t count,uint8_t *out,size_t capacity)
{
    uint32_t i;
    size_t k;
    int changed, result=re4ps_validate_skeleton(s);
    if (result) return result;
    if (!out || (count && !dep)) return RE4PS_ARGUMENT;
    if (capacity<s->bone_count) return RE4PS_CAPACITY;
    for (k=0;k<count;++k) if (dep[k].source>=s->bone_count || dep[k].destination>=s->bone_count) return RE4PS_HIERARCHY;
    for (i=0;i<s->bone_count;++i) out[i]=requested?!!requested[i]:1;
    do {
        changed=0;
        for (i=s->bone_count;i--;) if (out[i] && s->parent[i]>=0 && !out[s->parent[i]]) {
            out[s->parent[i]]=1; changed=1;
        }
        for (k=0;k<count;++k) if (out[dep[k].destination] && !out[dep[k].source]) {
            out[dep[k].source]=1; changed=1;
        }
    } while (changed);
    return RE4PS_OK;
}

static void decode_q48(const uint8_t *p,float q[4])
{
    uint32_t lo=u32(p), hi=u16(p+4);
    unsigned index=hi>>13, i, k=0;
    const float K=1.41421356f/32767.0f, L=0.70710678f;
    float v[3], sum;
    v[0]=(float)(((hi<<2)|(lo>>30))&0x7fff)*K-L;
    v[1]=(float)((lo>>15)&0x7fff)*K-L;
    v[2]=(float)(lo&0x7fff)*K-L;
    sum=1.0f-(v[0]*v[0]+v[1]*v[1]+v[2]*v[2]);
    for (i=0;i<4;++i) q[i]=i==index?sqrtf(fmaxf(sum,0.0f)):v[k++];
}
static void mix_q(float out[4],const float a[4],const float b[4],float t)
{
    float sign=0, norm=0;
    unsigned i;
    for (i=0;i<4;++i) sign+=a[i]*b[i];
    sign=sign<0?-1.0f:1.0f;
    for (i=0;i<4;++i) { out[i]=a[i]+(sign*b[i]-a[i])*t; norm+=out[i]*out[i]; }
    norm=1.0f/sqrtf(norm);
    for (i=0;i<4;++i) out[i]*=norm;
}
static unsigned segment(unsigned count,unsigned shift,unsigned frames,float f,float *t)
{
    unsigned k=((unsigned)f)>>shift, a,b;
    if (k>count-2) k=count-2;
    a=k<<shift; b=(k+1)<<shift;
    if (b>frames-1) b=frames-1;
    *t=b==a?0:(f-a)/(float)(b-a);
    return k;
}
static void sample_track(const re4ps_track *t,unsigned nf,float f,const float *rest,re4ps_local *out)
{
    unsigned k,j;
    float u;
    if (t->rotation_keys==1) decode_q48(t->rotation,out->q);
    else {
        float a[4],b[4];
        k=segment(t->rotation_keys,t->rotation_shift,nf,f,&u);
        decode_q48(t->rotation+6*k,a); decode_q48(t->rotation+6*(k+1),b);
        mix_q(out->q,a,b,u);
    }
    if (!t->translation_mode) memcpy(out->t,rest,3*sizeof(float));
    else if (t->translation_keys==1) {
        for (j=0;j<3;++j) out->t[j]=i16(t->translation+2*j)*t->translation_scale;
    } else {
        k=segment(t->translation_keys,t->translation_shift,nf,f,&u);
        for (j=0;j<3;++j) {
            float a=i16(t->translation+6*k+2*j), b=i16(t->translation+6*(k+1)+2*j);
            out->t[j]=(a+(b-a)*u)*t->translation_scale;
        }
    }
    if (!t->scale) out->s[0]=out->s[1]=out->s[2]=1;
    else {
        unsigned a=(unsigned)f,b=a+1<nf?a+1:a;
        u=f-a;
        for (j=0;j<3;++j) {
            float x=i16(t->scale+6*a+2*j),y=i16(t->scale+6*b+2*j);
            out->s[j]=(x+(y-x)*u)*(1.0f/4096.0f);
        }
    }
}
static int sample_arguments(const re4ps_skeleton *s,const re4ps_clip *c,float f,const void *out,size_t cap)
{
    if (!s || !c || !out || !s->bone_count || !s->rest_translation || !c->tracks ||
        s->bone_count!=c->bone_count || !c->frames) return RE4PS_ARGUMENT;
    if (cap<s->bone_count) return RE4PS_CAPACITY;
    if (!isfinite(f)) return RE4PS_NUMERIC;
    f=fmaxf(0,fminf(f,(float)c->frames-1));
    if (c->pose_stage==RE4PS_SOURCE_LOCAL && f!=floorf(f)) return RE4PS_SOURCE_FALLBACK;
    return RE4PS_OK;
}
int re4ps_sample(const re4ps_skeleton *s,const re4ps_clip *c,float f,
                 const uint8_t *required,re4ps_local *out,size_t cap)
{
    uint32_t i;
    int result=sample_arguments(s,c,f,out,cap);
    if (result) return result;
    f=fmaxf(0,fminf(f,(float)c->frames-1));
    for (i=0;i<s->bone_count;++i) if (!required || required[i]) sample_track(&c->tracks[i],c->frames,f,s->rest_translation+3*i,&out[i]);
    return RE4PS_OK;
}
int re4ps_layers(const re4ps_skeleton *s,const re4ps_layer *layers,size_t count,
                 const uint8_t *required,re4ps_local *out,size_t cap)
{
    size_t k;
    uint32_t i;
    if (!layers || !count || layers[0].weight!=1 || layers[0].bone_mask) return RE4PS_ARGUMENT;
    /* Validate every layer before writing any output. */
    for (k=0;k<count;++k) {
        int r=sample_arguments(s,layers[k].clip,layers[k].frame,out,cap);
        if (r) return r;
        if (!isfinite(layers[k].weight) || layers[k].weight<0 || layers[k].weight>1) return RE4PS_ARGUMENT;
    }
    re4ps_sample(s,layers[0].clip,layers[0].frame,required,out,cap);
    for (k=1;k<count;++k) {
        const re4ps_layer *l=&layers[k];
        float f=fmaxf(0,fminf(l->frame,(float)l->clip->frames-1));
        if (!l->weight) continue;
        for (i=0;i<s->bone_count;++i) if ((!required || required[i]) && (!l->bone_mask || l->bone_mask[i])) {
            re4ps_local b;
            float q[4];
            unsigned j;
            sample_track(&l->clip->tracks[i],l->clip->frames,f,s->rest_translation+3*i,&b);
            mix_q(q,out[i].q,b.q,l->weight);
            memcpy(out[i].q,q,sizeof(q));
            for (j=0;j<3;++j) {
                out[i].t[j]+=(b.t[j]-out[i].t[j])*l->weight;
                out[i].s[j]+=(b.s[j]-out[i].s[j])*l->weight;
            }
        }
    }
    return RE4PS_OK;
}
static void local_matrix(re4ps_matrix *out,const re4ps_local *l)
{
    float x=l->q[0],y=l->q[1],z=l->q[2],w=l->q[3],*m=out->m;
    unsigned r,c;
    m[0]=1-2*(y*y+z*z); m[1]=2*(x*y-z*w); m[2]=2*(x*z+y*w); m[3]=l->t[0];
    m[4]=2*(x*y+z*w); m[5]=1-2*(x*x+z*z); m[6]=2*(y*z-x*w); m[7]=l->t[1];
    m[8]=2*(x*z-y*w); m[9]=2*(y*z+x*w); m[10]=1-2*(x*x+y*y); m[11]=l->t[2];
    for (r=0;r<3;++r) for (c=0;c<3;++c) m[4*r+c]*=l->s[c];
}
static void compose_matrix(re4ps_matrix *out,const re4ps_matrix *a,const re4ps_matrix *b)
{
    unsigned r,c;
    for (r=0;r<3;++r) for (c=0;c<4;++c)
        out->m[4*r+c]=a->m[4*r]*b->m[c]+a->m[4*r+1]*b->m[4+c]+a->m[4*r+2]*b->m[8+c]+(c==3?a->m[4*r+3]:0);
}
int re4ps_compose(const re4ps_skeleton *s,const re4ps_local *local,const uint8_t *required,
                  const re4ps_matrix *root,re4ps_matrix *out,size_t cap)
{
    uint32_t i;
    if (!s || !s->bone_count || !s->parent || !local || !out) return RE4PS_ARGUMENT;
    if (cap<s->bone_count) return RE4PS_CAPACITY;
    /* Check the dependency contract before consuming potentially stale parents. */
    for (i=0;i<s->bone_count;++i) {
        int32_t p=s->parent[i];
        if (p < -1 || p >= (int32_t)i) return RE4PS_HIERARCHY;
        if ((!required || required[i]) && p>=0 && required && !required[p]) return RE4PS_HIERARCHY;
    }
    for (i=0;i<s->bone_count;++i) if (!required || required[i]) {
        re4ps_matrix m;
        int32_t p=s->parent[i];
        local_matrix(&m,&local[i]);
        if (p>=0) compose_matrix(&out[i],&out[p],&m);
        else if (root) compose_matrix(&out[i],root,&m);
        else out[i]=m;
    }
    return RE4PS_OK;
}
