// Included by the diagnostic native UI translation unit only.
namespace m1r3 {
extern "C" {
Control m1r3_control{};
void* re4dc_static_alloc(unsigned);
}
bool recording;
void texture_image_key(const void* pixels, const void* palette,unsigned width,unsigned height,
                       unsigned format,unsigned pf,unsigned pb,unsigned (&out)[2]){
    Re4dcUiImage img={pixels,palette,width,height,format,pf,pb};
    Key k{};
    if(image_key(img,k)){out[0]=k.crc;out[1]=k.fnv;}
}
static unsigned room_id,warmup,number,presents;
void append(Kind kind,const void* ptr,unsigned size){
    if(!recording)return;
    auto& c=m1r3_control;
    if(c.overflow || c.bytes>c.capacity || c.capacity-c.bytes<8 || size>c.capacity-c.bytes-8){c.overflow=1;return;}
    const unsigned h[]={kind,size};
    memcpy(c.data+c.bytes,h,8);memcpy(c.data+c.bytes+8,ptr,size);
    c.bytes+=8+size;
}
void begin(unsigned room,unsigned tick){
    if(room!=room_id){warmup=number=0;room_id=room;}
    recording=false;presents=0;
    if((room!=0x101 && room!=0x103) || number>=300)return;
    if(warmup<300 || !m1r3_control.mode)return;
    auto& c=m1r3_control;
    if(c.mode && !c.data){
        c.capacity=384*1024;c.data=(unsigned char*)re4dc_static_alloc(c.capacity);
        if(!c.data)c.capacity=0;
    }
    c.picture=number+1;c.tick=tick;c.room=room;c.bytes=c.overflow=c.framebuffer=0;
    c.sequence=2*number+1;recording=c.mode!=0;
}
void present(){++presents;}
void finish(){
    if((room_id!=0x101 && room_id!=0x103) || number>=300)return;
    if(warmup<300){warmup+=presents!=0;return;}
    if(!recording)return;
    auto& c=m1r3_control;
    if(presents!=1)c.overflow=2;
    recording=false;
    asm volatile("" ::: "memory");
    c.sequence=2*(++number);
    while(c.ack!=c.sequence)thd_sleep(1);
}
}
