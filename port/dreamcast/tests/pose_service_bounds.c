/* Malformed/truncated source-format probes; run under ASan + UBSan. */
#include "../engine/pose_service.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc,char **argv)
{
    FILE *f;
    long bytes;
    unsigned char *data;
    size_t n,k;
    unsigned v;
    int32_t parents[3]={-1,0,1};
    float rest[9]={0};
    re4ps_skeleton skeleton={3,parents,rest};
    re4ps_track tracks[3];
    re4ps_clip clip;
    re4ps_local locals[3];
    re4ps_matrix matrices[3];
    assert(argc==2);
    f=fopen(argv[1],"rb"); assert(f);
    assert(!fseek(f,0,SEEK_END)); bytes=ftell(f); assert(bytes>0);
    rewind(f); data=malloc((size_t)bytes); assert(data);
    assert(fread(data,1,(size_t)bytes,f)==(size_t)bytes); fclose(f);
    for (n=0;n<(size_t)bytes;++n) {
        /* Exact-sized allocation makes ASan see the real truncated boundary. */
        unsigned char *cut=malloc(n?n:1); assert(cut);
        memcpy(cut,data,n);
        assert(re4ps_open_edcl(&clip,tracks,3,cut,n,11,&skeleton)!=RE4PS_OK);
        assert(!clip.frames); free(cut);
    }
    for (k=0;k<(size_t)bytes;++k) {
        unsigned char saved=data[k];
        for (v=0;v<256;++v) {
            data[k]=(unsigned char)v;
            if (!re4ps_open_edcl(&clip,tracks,3,data,(size_t)bytes,11,&skeleton)) {
                assert(!re4ps_sample(&skeleton,&clip,-1,NULL,locals,3));
                assert(!re4ps_sample(&skeleton,&clip,(float)clip.frames,NULL,locals,3));
                assert(!re4ps_compose(&skeleton,locals,NULL,NULL,matrices,3));
            }
        }
        data[k]=saved;
    }
    free(data);
    puts("ASan/UBSan truncation and byte-mutation probes PASS");
    return 0;
}
