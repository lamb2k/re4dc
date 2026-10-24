#include "include/gc_asset_gate.h"
#if RE4DC_GC_ASSET_GATE
#include "include/native_io.h"
#include <kos/fs.h>
#include <fcntl.h>
#include <cstdio>
#include <cstring>
#ifndef RE4DC_GC_ASSET_CATALOG_SHA256
#define RE4DC_GC_ASSET_CATALOG_SHA256 "0"
#endif
namespace re4dc_gcasset {
namespace {
file_t disc_catalog=FILEHND_INVALID;
unsigned disc_state;
unsigned disc_read(void*,unsigned offset,void* destination,unsigned bytes){
    Re4dcIoScope io;
    if(disc_catalog==FILEHND_INVALID || fs_seek(disc_catalog,offset,SEEK_SET)!=off_t(offset))return 0;
    const ssize_t count=fs_read(disc_catalog,destination,bytes);return count<0?0:unsigned(count);
}
bool disc_pin(Digest& digest){
    const char* text=RE4DC_GC_ASSET_CATALOG_SHA256;
    if(std::strlen(text)!=64)return false;
    for(unsigned i=0;i<64;++i){
        const unsigned char c=text[i];unsigned value;
        if(c>='0' && c<='9')value=c-'0';else if(c>='a' && c<='f')value=c-'a'+10;else return false;
        if(i&1)digest.bytes[i/2]|=value;else digest.bytes[i/2]=value<<4;
    }
    return true;
}
}
bool ensure_disc_catalog(){
    if(disc_state)return disc_state==1;
    disc_state=2;Digest expected{};
    if(!disc_pin(expected)){unresolved(SourceGeometry,"catalog-pin-missing");return false;}
    {Re4dcIoScope io;disc_catalog=fs_open("/cd/dc/gc-assets.idx",O_RDONLY);}
    if(disc_catalog==FILEHND_INVALID){unresolved(SourceGeometry,"catalog-file-missing");return false;}
    off_t bytes;{Re4dcIoScope io;bytes=fs_total(disc_catalog);}
    if(bytes<128 || bytes>128+16376*112 || !install_index(disc_read,nullptr,unsigned(bytes),expected)){
        {Re4dcIoScope io;fs_close(disc_catalog);}disc_catalog=FILEHND_INVALID;
        unresolved(SourceGeometry,"catalog-install");return false;
    }
    disc_state=1;return true;
}
void retire_disc_catalog(){
    retire_catalog();
    if(disc_catalog!=FILEHND_INVALID){Re4dcIoScope io;fs_close(disc_catalog);}
    disc_catalog=FILEHND_INVALID;disc_state=0;
}
}
#endif
