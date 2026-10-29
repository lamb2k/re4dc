#pragma once

// Out-of-band identity: get() never reads T while deciding whether T is live.
// The room API checks epoch/heap/range before reading its own cell header.
extern "C" int re4dc_room4_live_generation(unsigned*);
extern "C" int re4dc_room4_cell_valid(const void*,unsigned,unsigned);
extern "C" unsigned re4dc_room4_cell_incarnation(const void*,unsigned,unsigned);
namespace re4dc { namespace sob05 {
template<class T> struct Cell {
    T* pointer=nullptr;
    unsigned generation=0,incarnation=0;
    void clear(){pointer=nullptr;generation=incarnation=0;}
    T* get(){
        unsigned now=0;
        if(!pointer || !re4dc_room4_live_generation(&now) || now!=generation ||
           !incarnation || re4dc_room4_cell_incarnation(pointer,sizeof(T),generation)!=incarnation){
            clear();return nullptr;
        }
        return pointer;
    }
    bool bind(T* p,unsigned expected_generation){
        clear();unsigned now=0;
        if(!p || !re4dc_room4_live_generation(&now) || now!=expected_generation)return false;
        const unsigned token=re4dc_room4_cell_incarnation(p,sizeof(T),now);
        if(!token)return false;
        pointer=p;generation=now;incarnation=token;return true;
    }
};
}}
