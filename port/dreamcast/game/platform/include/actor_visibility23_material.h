#pragma once
// Source eligibility is separate from disabled backend face rejection.
namespace actor_visibility23 { namespace material23 {
enum Reason : unsigned { Blend=1,Masked=2,Alpha=4,MaskImage=8,MaskRef=16,BackendCull=32,
 Stream=64,Skin=128,Owned=256,Stride=512,Palette=1024,Depth=2048,SourceCull=4096 };
struct Inputs {
 unsigned blend,flags,alpha,mask_ref,cull,depth,stride;
 bool mask,same_stream,skin,owned,palette;
};
inline unsigned refusal(const Inputs& p){
 return (p.blend?Blend:0U)|((p.flags&4U)?Masked:0U)|(p.alpha!=255?Alpha:0U)|
  (p.mask?MaskImage:0U)|(p.mask_ref!=256?MaskRef:0U)|(p.cull>2?BackendCull:0U)|
  (!p.same_stream?Stream:0U)|(!p.skin?Skin:0U)|(!p.owned?Owned:0U)|
  (p.stride!=8?Stride:0U)|(!p.palette?Palette:0U)|(p.depth?Depth:0U);
}
inline bool diagnostic_provenance(unsigned reason,bool owner,bool info){
 return owner&&info&&!(reason&(Stream|Skin|Owned|Stride|Palette));
}
inline bool source_one_sided(unsigned id,bool first_two,bool current,unsigned flags,unsigned source_mode,
                             unsigned mapped,unsigned depth,unsigned blend){
 return id==0x2b&&first_two&&current&&(flags&1U)&&!(flags&0x4000U)&&source_mode<=1&&
        (mapped==1||mapped==2)&&!depth&&!blend;
}
} }
