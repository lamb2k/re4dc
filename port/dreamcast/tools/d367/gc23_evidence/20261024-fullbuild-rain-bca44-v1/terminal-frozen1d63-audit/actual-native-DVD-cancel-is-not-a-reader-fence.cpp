
#include <cassert>
using s32=int;struct DVDCommandBlock{int state;};using DVDCBCallback=void(*)(s32,DVDCommandBlock*);constexpr int DVD_STATE_END=0;bool native_read_still_active=true;unsigned callbacks;
void callback(s32 result,DVDCommandBlock*b){assert(result==0&&b->state==DVD_STATE_END&&native_read_still_active);++callbacks;}
int DVDCancelAsync(DVDCommandBlock* block, DVDCBCallback callback)
{
    block->state = DVD_STATE_END;
    if (callback) {
        callback(0, block);
    }
    return 1;
}
s32 DVDCancelAll(void)
{
    return 0;
}
int main(){DVDCommandBlock b{1};assert(DVDCancelAsync(&b,callback)==1);assert(callbacks==1&&native_read_still_active&&b.state==DVD_STATE_END);assert(DVDCancelAll()==0&&native_read_still_active);}
