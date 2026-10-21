// Actual EventMgr/DatTbl method bodies; projected host class layout, not target ABI.
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <sys/mman.h>
using u8=std::uint8_t;using u16=std::uint16_t;using s16=std::int16_t;using s32=std::int32_t;using u32=std::uint32_t;
static unsigned errors;
struct Logger{void err(int,int,const char*,...){++errors;}}logger,*pLog=&logger;
void memclr_asm(void*p,unsigned n){std::memset(p,0,n);}
#include "event_admission_types.inc"
// Only fields/method declarations required by the selected methods are projected.
// No event/registration decision is replaced with a test implementation.
struct DatTbl{int NumDatTbl;DatTblEntry*pWork;
int SetDat(const char*,void*,u8,void*,u8,int*);int ChkDat(const char*);};
struct EventMgr{DatTbl EvdTbl,BinTbl;
int SetEvd(char*,void*,void*,int);int SetBin(char*,void*,void*,int);};
#include "event_admission_methods.inc"
static EvtHeader* event_at(void*p){
    std::memset(p,0,4096);auto*hdr=(EvtHeader*)p;std::memcpy(hdr->tag,"event",5);hdr->nBin=2;hdr->binOfs=sizeof(EvtHeader);
    auto*e=(EvtBinEntry*)((u8*)p+hdr->binOfs);std::strcpy(e[0].name,"first.bin");std::strcpy(e[1].name,"second.bin");e[0].ofs=512;e[1].ofs=1024;return hdr;
}
int main(){
    void*mem=mmap((void*)0x90000000,8192,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE,-1,0);assert(mem==(void*)0x90000000);
    static_assert(sizeof(EvtHeader)==0x50&&sizeof(EvtBinEntry)==0x40,"source event ABI fields unchanged");
    auto*hdr=event_at(mem);DatTblEntry parents[2]{},bins[2]{};EventMgr m{{2,parents},{1,bins}};char name[]="synthetic.evd";
    assert(m.SetEvd(name,hdr,nullptr,0)==0);assert(m.EvdTbl.ChkDat(name)==1);assert(m.BinTbl.ChkDat("first.bin")==1&&m.BinTbl.ChkDat("second.bin")==0);assert(errors==3);
    // Capacity is now available, but retry returns success before visiting bins.
    m.BinTbl.NumDatTbl=2;errors=0;assert(m.SetEvd(name,hdr,nullptr,0)==1);assert(!errors&&m.BinTbl.ChkDat("second.bin")==0&&parents[0].Count==1);
    std::cout<<"partial EVD: first attempt fails after parent+bin0; retry reports success with bin1 absent PASS (defect reproduced)\n";
    std::memset(parents,0,sizeof(parents));std::memset(bins,0,sizeof(bins));errors=0;
    assert(m.SetEvd(name,hdr,nullptr,0)==1&&m.BinTbl.ChkDat("second.bin")==1&&!errors);assert(bins[0].Count==1&&bins[1].Count==1);
    // Name reuse acknowledges the prior owner instead of validating new bytes.
    auto*other=event_at((u8*)mem+4096);assert(m.SetEvd(name,other,nullptr,0)==1&&parents[0].Dat==hdr&&parents[0].Count==1);
    char first[]="first.bin";assert(m.SetBin(first,(u8*)other+512,nullptr,0)==1&&bins[0].Dat==(u8*)hdr+512&&bins[0].Count==2);
    std::cout<<"complete admission positive control and duplicate EVD/bin prior-owner/refcount semantics PASS; generation replacement remains OPEN\n";
    std::memset(parents,0,sizeof(parents));std::memset(bins,0,sizeof(bins));m.EvdTbl.NumDatTbl=0;errors=0;
    assert(m.SetEvd(name,hdr,nullptr,0)==0&&!m.BinTbl.ChkDat(first)&&errors==2);
    m.EvdTbl.NumDatTbl=2;hdr->tag[0]='X';errors=0;assert(m.SetEvd(name,hdr,nullptr,0)==0&&errors==1&&!m.EvdTbl.ChkDat(name));
    std::cout<<"parent-capacity and invalid-header failures publish no children PASS\n";
    munmap(mem,8192);return 0;
}
