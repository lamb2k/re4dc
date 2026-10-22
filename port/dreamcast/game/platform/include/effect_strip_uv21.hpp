#pragma once
// Source EspStrip_draw_poly UVs in GX quad order (0,1,3,2), including its
// signed16 conversion in the longitudinal, mirrored-t/non-mirrored-s case.
// Render-only; does not touch effect state, simulation or packet ownership.
namespace re4dc::effect_strip21 {
struct UV { float u,v; };
inline bool source_uv(int no,unsigned char repeat,int flag,unsigned tool,UV (&out)[4]){
    if(!repeat)return false;
    const float step=1.0f/float(repeat);
    float s=0,t=0,sw=1,tw=1;
    if(flag){sw=step;s=(tool&4)?1.0f-step*no:step*no;}
    else {tw=step;t=(tool&4)?1.0f-step*no:step*no;}
    if(flag){
        if(tool&2){
            if(tool&4){out[0]={s+sw,t};out[1]={s+sw,t+tw};out[2]={s,t+tw};out[3]={s,t};}
            else {out[0]={s+sw,t+tw};out[1]={s+sw,t};out[2]={s,t};out[3]={s,t+tw};}
        } else {
            if(tool&4){out[0]={s,t+tw};out[1]={s,t};out[2]={float(short(s+sw)),t};out[3]={s+sw,t+tw};}
            else {out[0]={s,t};out[1]={s,t+tw};out[2]={s+sw,t+tw};out[3]={s+sw,t};}
        }
    } else {
        if(tool&2){
            if(tool&4){out[0]={s+sw,t+tw};out[1]={s,t+tw};out[2]={s,t};out[3]={s+sw,t};}
            else {out[0]={s+sw,t};out[1]={s,t};out[2]={s,t+tw};out[3]={s+sw,t+tw};}
        } else {
            if(tool&4){out[0]={s,t+tw};out[1]={s+sw,t+tw};out[2]={s+sw,t};out[3]={s,t};}
            else {out[0]={s,t};out[1]={s+sw,t};out[2]={s+sw,t+tw};out[3]={s,t+tw};}
        }
    }
    return true;
}
} // namespace re4dc::effect_strip21
