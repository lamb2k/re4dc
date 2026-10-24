// Diagnostic identity hash, adapted from aica_bank_v2_sha256.cpp's no-heap
// SHA256 implementation. Included only inside gc_asset_gate.cpp's namespace.
struct IdentitySha {
    unsigned state[8], used=0, bytes=0; unsigned char block[64];
    IdentitySha() {
        const unsigned initial[]={0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
        std::memcpy(state,initial,sizeof state);
    }
    static unsigned rotate(unsigned x,unsigned n) { return (x>>n)|(x<<(32-n)); }
    void transform() {
        static const unsigned k[]={
        0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
        0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
        0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
        0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
        0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
        0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
        0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
        0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
        unsigned w[16];for(unsigned i=0;i<16;++i) { const unsigned char* p=block+4*i;w[i]=(unsigned(p[0])<<24)|(unsigned(p[1])<<16)|(unsigned(p[2])<<8)|p[3]; }
        unsigned a=state[0],b=state[1],c=state[2],d=state[3],e=state[4],f=state[5],g=state[6],h=state[7];
        for(unsigned i=0;i<64;++i) {
            if(i>=16) { unsigned x=w[(i-15)&15],y=w[(i-2)&15];w[i&15]+=(rotate(x,7)^rotate(x,18)^(x>>3))+w[(i-7)&15]+(rotate(y,17)^rotate(y,19)^(y>>10)); }
            unsigned t=h+(rotate(e,6)^rotate(e,11)^rotate(e,25))+((e&f)^((~e)&g))+k[i]+w[i&15];
            unsigned s=(rotate(a,2)^rotate(a,13)^rotate(a,22))+((a&b)^(a&c)^(b&c));
            h=g;g=f;f=e;e=d+t;d=c;c=b;b=a;a=t+s;
        }
        state[0]+=a;state[1]+=b;state[2]+=c;state[3]+=d;state[4]+=e;state[5]+=f;state[6]+=g;state[7]+=h;
    }
    void update(const void* data,unsigned n) {
        const unsigned char* p=static_cast<const unsigned char*>(data);bytes+=n;
        while(n) { unsigned take=n<64-used?n:64-used;std::memcpy(block+used,p,take);used+=take;p+=take;n-=take;if(used==64) {transform();used=0;} }
    }
    void finish(unsigned char* digest) {
        const unsigned bits=bytes*8;block[used++]=0x80;
        if(used>56) {std::memset(block+used,0,64-used);transform();used=0;}
        std::memset(block+used,0,60-used);block[60]=bits>>24;block[61]=bits>>16;block[62]=bits>>8;block[63]=bits;transform();
        for(unsigned i=0;i<32;++i)digest[i]=state[i/4]>>(24-(i%4)*8);
    }
};
