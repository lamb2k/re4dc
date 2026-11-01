// Generated admission facts for the two private r11f version3 profiles.
// prepare_enemy_motions.py --bounded-profile; source and every FCV SHA remain
// in the independently sealed private manifest. No generic cap increase.
// Called only after the header/REL extents are proved within the loaded body.
unsigned bounded_profile(const unsigned char* a,unsigned bytes,unsigned rel,const unsigned char* mtc) {
    struct Profile { unsigned module,cap,count,bytes,table_crc,body_crc,descriptor_bss; };
    static constexpr Profile profiles[]={
        {61u,131072u,82u,1035392u,0x3766221du,0x13e11ff5u,52u},
        {47u,32768u,69u,384064u,0x5f23565eu,0xddcc1084u,0u},
        // pl11-hot (castle lane 2026-10-15): pl11-r11f + Ashley's 8 near-enemy clips retained in the body.
        {47u,32768u,61u,411744u,0x3913017bu,0xeb2fce03u,0u},
        // pl11-walk: additive source ARC22/23/37 retention for the confirmed r202 follow working set.
        {47u,32768u,58u,423136u,0x99957b47u,0xe0461bb7u,0u},
#if RE4DC_MOTION_PS2_PL11
        // pl11-hot with its motion from PS2 pl11.dat (purge-motion25, data set pmash25): same rows and body size.
        {47u,32768u,61u,411744u,0x70063c28u,0xdd1db0cdu,0u},
#endif
    };
    for(const auto& p:profiles) {
        if(bytes!=p.bytes || word(mtc+28)!=p.cap || word(mtc+12)!=p.count || word(mtc+20)!=p.table_crc ||
           word(a+rel)!=p.module || word(a+rel+28)!=0xdc000001u || word(a+rel+32)!=p.descriptor_bss)continue;
        bool exact=true;
        for(unsigned i=1;i<16;++i)if(i!=7u && i!=8u && word(a+rel+4*i))exact=false;
        if(exact && net_crc32le(a,bytes)==p.body_crc)return p.cap;
    }
    return 0;
}
