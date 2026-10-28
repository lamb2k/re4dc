#pragma once
#include <cstdint>

// Build33 only: reuse final TA state, never source arrays, matrices or lighting.
// The caller owns the existing synchronous packet/SQ window and must invalidate
// this receipt at every foreign submission, scene/list change and owner reset.
namespace re4dc::sob33 {
constexpr unsigned kMarker=0xa8,kSingle=1,kLarge=2,kBlended=4;
inline bool marked(unsigned marker){return (marker&0xf8U)==kMarker;}
inline unsigned marker(unsigned parts,unsigned blend){
    return kMarker|(parts==1?kSingle:0U)|(parts>16?kLarge:0U)|(blend?kBlended:0U);
}
inline bool eligible_class(unsigned kind,unsigned id){
    return (kind==0 && (id==0x41 || id==0x43 || id==0x45 || id==0x46)) ||
           (kind==1 && id==0x21);
}
enum Decision : unsigned { First,Reuse,Foreign,Format,Boundary,Header,DecisionCount };
enum Barrier : unsigned {
    SourceReset,DeferredReset,FrameReset,SceneBoundary,ListBoundary,PacketAbort,
    StreamSend,ForeignDirect,CustomPacket,EmptyPacket,BarrierCount
};

inline bool supported(const std::uint32_t* header,unsigned list){
    if(!header || (list!=0 && list!=2 && list!=4))return false;
    const std::uint32_t command=header[0];
    // Polygon, packed colour, single volume: both UV formats have 32-byte
    // vertices. Bit7 cheap-shadow reception is compatible; bit6 two-volume
    // mode and intensity/floating-colour records require different layouts.
    return (command&0xf0000070U)==0x80000000U && ((command>>24)&7U)==list;
}

struct Run {
    std::uint32_t words[8]{};
    unsigned frame=0,list=0,byte_serial=0;
    bool valid=false,pending=false,reused=false;

    void barrier(){valid=false;pending=false;reused=false;}
    Decision begin(const std::uint32_t* header,unsigned next_frame,unsigned next_list,
                   unsigned next_serial,bool eligible){
        if(!eligible){barrier();return Foreign;}
        if(!supported(header,next_list)){barrier();return Format;}
        Decision result=First;
        if(valid){
            if(frame!=next_frame || list!=next_list || byte_serial!=next_serial)result=Boundary;
            else{
                result=Reuse;
                for(unsigned i=0;i<8;++i)if(words[i]!=header[i]){result=Header;break;}
            }
        }
        // A nested/uncompleted begin has no completed-strip authority. The
        // fresh header is retained only provisionally until finish succeeds.
        if(result!=Reuse){
            for(unsigned i=0;i<8;++i)words[i]=header[i];
            frame=next_frame;list=next_list;byte_serial=next_serial;
        }
        valid=false;pending=true;reused=result==Reuse;
        return result;
    }
    bool finish(unsigned next_frame,unsigned next_list,unsigned next_serial,
                unsigned vertices,bool complete_eol){
        const bool accepted=pending && vertices && vertices<=32767 && complete_eol &&
            frame==next_frame && list==next_list &&
            next_serial-byte_serial==(vertices+(reused?0U:1U))*32U;
        pending=false;valid=accepted;
        if(accepted)byte_serial=next_serial;
        return accepted;
    }
};

struct Stats {
    unsigned decisions[DecisionCount]{};
    unsigned direct_reused=0,packet_reused=0,list_reused[5]{};
    unsigned category_seen[3]{},category_reused[3]{};
    unsigned completed=0,incomplete=0,empty=0,barriers=0;
    unsigned barrier_causes[BarrierCount]{};
    void begin(Decision result,unsigned list,bool direct,unsigned marker=0){
        ++decisions[result];
        if(marked(marker))for(unsigned i=0;i<3;++i)if(marker&(1U<<i)){
            ++category_seen[i];if(result==Reuse)++category_reused[i];
        }
        if(result==Reuse){
            if(direct)++direct_reused;else ++packet_reused;
            if(list<5)++list_reused[list];
        }
    }
};
}
