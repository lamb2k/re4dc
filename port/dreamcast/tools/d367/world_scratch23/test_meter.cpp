#include "world_scratch.h"
#include <cassert>
#include <cstddef>
using namespace re4dc::world_scratch;
static_assert(sizeof(Snapshot)==100 && offsetof(Snapshot,iterations)==96,"old25word ABI preserved");
static Stats active(unsigned frames=0){Stats s{};s.actual=C;s.frames=frames;s.remaining=600-frames;return s;}
int main(){
    {FrameMeter m;auto s=active();m.boundary(10,false,0x109,s,0,false);m.attach(1,C,0x109,s);
     m.boundary(9,false,0x109,active(1),0,false);assert(m.totals().phase==4);}
    {FrameMeter m;auto s=active();m.boundary(10,false,0x109,s,0,false);m.attach(1,C,0x109,s);
     m.boundary(20,false,0x109,active(1),1,false);assert(m.totals().phase==4);} // live prior token
    {FrameMeter m;auto s=active();m.boundary(10,false,0x109,s,0,false);m.attach(1,C,0x109,s);
     m.boundary(20,false,0x109,s,0,false);assert(m.totals().phase==4);} // missing end
    {FrameMeter m;auto s=active();m.boundary(10,false,0,s,0,false);m.attach(1,C,0x109,s);
     assert(m.totals().phase==4);} // context became ready only after earliest boundary
    {FrameMeter m;auto s=active();m.boundary(10,false,0x109,s,0,false);m.attach(1,C,0x109,s);
     auto ended=active(1);ended.remaining=0;m.observe(ended);assert(m.totals().phase==4);} // partial cancel
    {FrameMeter m;std::uint64_t now=0;auto s=active();
     for(unsigned i=0;i<600;++i){s=active(i);m.boundary(now,i&1,0x109,s,0,false);m.attach(i+1,C,0x109,s);now+=0x100000001ULL;}
     s=active(600);s.actual=A;m.observe(s);assert(m.totals().phase==2);
     m.boundary(now,false,0x109,s,0,true);const auto t=m.totals();
     assert(t.phase==3 && t.wall_us==600ULL*0x100000001ULL && t.draw_us+t.skip_us==t.wall_us && t.drawn+t.skipped==600);}
    {FrameMeter m;auto s=active();m.boundary(1,false,0x109,s,0,false);m.attach(1,C,0x109,s);m.cancel();
     m.boundary(2,false,0x109,active(1),0,false);m.attach(2,C,0x109,active(1));assert(m.totals().phase==4);}
}
