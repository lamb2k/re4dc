// Build31: bounded selection cursor and whole-part proof for ordered pages.
// This is local to one synchronous source part; no retained package ownership.
#pragma once
#include <climits>

namespace re4dc { namespace page31 {
struct Cursor {
    unsigned cluster=0,meshlet=0,end=0;
    unsigned char classification=0;
    bool started=false,active=false;
};
struct Page { unsigned count; bool done; };
inline bool indexable(unsigned first,unsigned count){
    return first<=0xffffU && count<=0x10000U-first;
}

// A page can be submitted before the next page is selected. Retain only the
// ordered proof and completion counters, never a pointer into the pick array.
struct Part {
    unsigned next,total,input=0,output=0;
    bool whole=true,published=true,positive=true;
    Part(unsigned first,unsigned count):next(first),total(count){}
    template<class Pick> void selected(const Pick* picks,unsigned count){
        for(unsigned i=0;i<count;++i){
            if(next==UINT_MAX || picks[i].let!=next || picks[i].nr!=0xffU)whole=false;
            if(next!=UINT_MAX)++next;
        }
    }
    void emitted(int result,bool did_publish,unsigned in,unsigned out){
        if(result<=0)positive=false;
        if(!did_publish)published=false;
        if(in>UINT_MAX-input || out>UINT_MAX-output){whole=false;return;}
        input+=in;output+=out;
    }
    bool complete(unsigned first)const{
        return whole && total && first<=UINT_MAX-total && next==first+total;
    }
    int result()const{return positive?1:0;}
};
}}
