#include "actor_ganado_ps2_stump.h"
#ifndef RE4DC_ACTOR_GANADO_APP0_GRIP
#define RE4DC_ACTOR_GANADO_APP0_GRIP 0
#endif
// The combined pl08 + registry recipe needs 61 fixed roles plus six room roles, and 30 fixed blobs plus
// three room blobs. Widen only this combination; all narrower recipes keep their original layout and code.
#if RE4DC_ACTOR_PL08 && RE4DC_NATIVE_MODEL_REGISTRY
#define RE4DC_ACTOR_WIDE_IDENTITY 1
// ACTOR_GANADO_PS2_STUMP (lane stump17 10-17) adds 25 fixed roles (5 stumps + 4 hand poses x 5 appearances) and 9 fixed
// blobs: base 88 roles / 39 blobs with the pool recipe. r117's room package needs 42 roles / 31 blobs, so the pool
// layout takes the ROLES5 widths (160 role bits, 128 blob bits) with the knob; ROLES5 plus the knob takes 192 role bits
// (ROLES5's 98 room rows above the larger base).
#if RE4DC_NMR_POOL && (RE4DC_NMR_ROLES5 || RE4DC_ACTOR_GANADO_PS2_STUMP)
#define RE4DC_ACTOR_WIDE_BLOBS 1
#else
#define RE4DC_ACTOR_WIDE_BLOBS 0
#endif
#if RE4DC_NMR_POOL
// NATIVE_MODEL_REGISTRY_POOL: a pool descriptor carries one role row per pool section (the zealot / soldier pools: ~20),
// beside a partner package's rows; 128 role bits leave 66 room rows. NATIVE_MODEL_REGISTRY_ROLES5 (lane cast16
// 2026-10-16): 160 role bits (98 room rows) for the rooms whose pools load many types (r227 em14 x4, island r320).
#if RE4DC_NMR_ROLES5 && RE4DC_ACTOR_GANADO_PS2_STUMP
constexpr unsigned kRoleMaskWords=6,kBlobMaskBits=128;
#elif RE4DC_ACTOR_WIDE_BLOBS
// ROLES5 also widens the asset template mask to 128 source blobs (r214: 31 base + 51 room blobs).
constexpr unsigned kRoleMaskWords=5,kBlobMaskBits=128;
#else
constexpr unsigned kRoleMaskWords=4,kBlobMaskBits=64;
#endif
#else
constexpr unsigned kRoleMaskWords=3,kBlobMaskBits=64;
#endif
#if RE4DC_ACTOR_WIDE_BLOBS
// Two-word template mask with the operators the lifetime code uses on the u64 one.
struct BlobMask {
    std::uint64_t w[2];
    constexpr BlobMask(unsigned v=0u):w{v,0u}{}
    friend BlobMask operator<<(BlobMask a,unsigned s){BlobMask r;if(!s)return a;if(s>=64u){r.w[1]=a.w[0]<<(s-64u);return r;}
        r.w[0]=a.w[0]<<s;r.w[1]=(a.w[1]<<s)|(a.w[0]>>(64u-s));return r;}
    friend BlobMask operator>>(BlobMask a,unsigned s){BlobMask r;if(!s)return a;if(s>=64u){r.w[0]=a.w[1]>>(s-64u);return r;}
        r.w[1]=a.w[1]>>s;r.w[0]=(a.w[0]>>s)|(a.w[1]<<(64u-s));return r;}
    friend BlobMask operator&(BlobMask a,BlobMask b){a.w[0]&=b.w[0];a.w[1]&=b.w[1];return a;}
    friend BlobMask operator|(BlobMask a,BlobMask b){a.w[0]|=b.w[0];a.w[1]|=b.w[1];return a;}
    BlobMask operator~()const{BlobMask r;r.w[0]=~w[0];r.w[1]=~w[1];return r;}
    BlobMask& operator&=(BlobMask b){w[0]&=b.w[0];w[1]&=b.w[1];return *this;}
    BlobMask& operator|=(BlobMask b){w[0]|=b.w[0];w[1]|=b.w[1];return *this;}
    explicit operator bool()const{return (w[0]|w[1])!=0u;}
    explicit operator unsigned()const{return unsigned(w[0]);}
};
#else
using BlobMask=std::uint64_t;
#endif
#else
#define RE4DC_ACTOR_WIDE_IDENTITY 0
#define RE4DC_ACTOR_WIDE_BLOBS 0
#if RE4DC_ACTOR_GANADO_PS2_STUMP
constexpr unsigned kRoleMaskWords=3,kBlobMaskBits=64;  // the stump / hand rows without pl08 + registry: 79 roles, 35 blobs
using BlobMask=std::uint64_t;
#else
constexpr unsigned kRoleMaskWords=2,kBlobMaskBits=32;
using BlobMask=unsigned;
#endif
#endif
constexpr unsigned kRoleMaskBits=kRoleMaskWords*32u;
// Private real source facts, normalized at adoption only. No mesh arrays.
static const Texture t_em12_473[] = {
{1946439074u,2058306121u,256u,256u,14u,{1u,1u,1u,1u,0u,0u,0u,0u},4294967295u,{0u,0u,0u}},
{149391415u,1735864054u,256u,256u,14u,{1u,1u,1u,1u,0u,0u,0u,0u},4294967295u,{0u,0u,0u}},
{3042983801u,3809298302u,256u,256u,14u,{1u,1u,1u,1u,0u,0u,0u,0u},4294967295u,{0u,0u,0u}},
};
static const Texture t_em15_445[] = {
{278946511u,3897410138u,256u,256u,14u,{1u,1u,1u,1u,0u,0u,0u,0u},4294967295u,{0u,0u,0u}},
{978041062u,940117262u,256u,256u,14u,{1u,1u,1u,1u,0u,0u,0u,0u},4294967295u,{0u,0u,0u}},
{2610130182u,639229323u,256u,256u,14u,{1u,1u,1u,1u,0u,0u,0u,0u},4294967295u,{0u,0u,0u}},
};
static const Texture t_em15_477[] = {
{2614095805u,3625741105u,256u,256u,14u,{1u,1u,1u,1u,0u,0u,0u,0u},4294967295u,{0u,0u,0u}},
{1267036948u,4074767808u,256u,256u,14u,{1u,1u,1u,1u,0u,0u,0u,0u},4294967295u,{0u,0u,0u}},
{1710877097u,1483325243u,256u,256u,14u,{1u,1u,1u,1u,0u,0u,0u,0u},4294967295u,{0u,0u,0u}},
};
static const Texture t_em15_481[] = {
{55292393u,2892269999u,256u,256u,14u,{1u,1u,1u,1u,0u,0u,0u,0u},4294967295u,{0u,0u,0u}},
{1364191771u,90764165u,256u,256u,14u,{1u,1u,1u,1u,0u,0u,0u,0u},4294967295u,{0u,0u,0u}},
{1539271701u,2988734327u,256u,256u,14u,{1u,1u,1u,1u,0u,0u,0u,0u},4294967295u,{0u,0u,0u}},
};
static const Texture t_em15_458[] = {
{2248446375u,2303382372u,256u,256u,14u,{1u,1u,1u,1u,0u,0u,0u,0u},4294967295u,{0u,0u,0u}},
{1695196641u,4271094591u,256u,256u,14u,{1u,1u,1u,1u,0u,0u,0u,0u},4294967295u,{0u,0u,0u}},
{1756572056u,3908708126u,256u,256u,14u,{1u,1u,1u,1u,0u,0u,0u,0u},4294967295u,{0u,0u,0u}},
};
static const Texture t_pl00_5[] = {
{526539925u,2062370825u,256u,128u,14u,{1u,1u,1u,1u,0u,0u,0u,0u},4294967295u,{0u,0u,0u}},
{189264623u,2402348103u,128u,64u,3u,{1u,1u,1u,1u,0u,0u,0u,0u},4294967295u,{0u,0u,0u}},
{603371856u,2661364161u,128u,128u,14u,{1u,1u,1u,1u,0u,0u,0u,0u},4294967295u,{0u,0u,0u}},
{368566668u,299668448u,256u,256u,14u,{1u,1u,1u,1u,0u,0u,0u,0u},4294967295u,{0u,0u,0u}},
{474694314u,1979195436u,128u,128u,3u,{1u,1u,1u,1u,0u,0u,0u,0u},4294967295u,{0u,0u,0u}},
{2274042816u,3875768371u,128u,128u,14u,{1u,1u,1u,1u,0u,0u,0u,0u},4294967295u,{0u,0u,0u}},
{3189306440u,2720529342u,64u,64u,3u,{1u,1u,1u,1u,0u,0u,0u,0u},4294967295u,{0u,0u,0u}},
{713701007u,1992305410u,128u,256u,14u,{1u,1u,1u,1u,0u,0u,0u,0u},4294967295u,{0u,0u,0u}},
};
static const Texture t_pl00_7[] = {
{2889358106u,987661489u,64u,128u,14u,{1u,1u,1u,1u,0u,0u,0u,0u},4294967295u,{0u,0u,0u}},
{2498354262u,118342730u,64u,128u,0u,{1u,1u,1u,1u,0u,0u,0u,0u},4294967295u,{0u,0u,0u}},
{2057167357u,239165205u,64u,128u,14u,{1u,1u,1u,1u,0u,0u,0u,0u},4294967295u,{0u,0u,0u}},
{2498354262u,118342730u,64u,128u,0u,{1u,1u,1u,1u,0u,0u,0u,0u},4294967295u,{0u,0u,0u}},
{3722900266u,192740815u,256u,128u,14u,{1u,1u,1u,1u,0u,0u,0u,0u},4294967295u,{0u,0u,0u}},
};
static const Texture t_pl00_17[] = {
{3439488109u,978632617u,128u,64u,14u,{1u,1u,1u,1u,0u,0u,0u,0u},4294967295u,{0u,0u,0u}},
{206246671u,791587696u,64u,32u,3u,{1u,1u,1u,1u,0u,0u,0u,0u},4294967295u,{0u,0u,0u}},
};
static const Part p_em12_472[] = {
{{0u,1u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},8032u,682u,1213925994u,1015215941u},
{{0u,2u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},3104u,228u,1349404484u,4199712078u},
{{0u,2u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},384u,36u,1446756461u,3882571853u},
{{0u,2u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},384u,36u,4123309521u,996190203u},
{{0u,2u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},6592u,552u,1919119433u,1521587078u},
};
static const Model m_em12_472 = {{2684355328u,4u,34u,822u,950u,3u,75u,75u,5u,537069592u},{6576u,3196829425u,3152513138u},{3800u,1147617924u,2991066842u},{600u,4145389082u,4228854728u},{3888u,930404666u,1553610668u},p_em12_472};
static const Part p_em12_474[] = {
{{0u,0u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},512u,34u,817476800u,3126281177u},
{{0u,0u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},352u,26u,1423389766u,248444425u},
{{0u,0u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},640u,37u,3499723803u,257120620u},
{{2u,0u,255u,255u,0u,127u,127u,127u,0u,0u,70u,0u,255u},544u,48u,27735809u,3723413782u},
{{0u,0u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},11008u,944u,2616583853u,1366484147u},
};
static const Model m_em12_474 = {{2684355328u,4u,34u,602u,631u,3u,32u,32u,5u,537069592u},{4816u,1933639271u,1837817862u},{2524u,910941489u,1030201414u},{256u,3913660121u,1443817088u},{2892u,2888813737u,3900451799u},p_em12_474};
static const Part p_em12_448[] = {
{{0u,2u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},2496u,217u,634125105u,556828952u},
};
static const Model m_em12_448 = {{2147484416u,4u,34u,114u,114u,3u,2u,2u,1u,537069592u},{912u,2049620157u,4223744493u},{912u,185339134u,3157497573u},{16u,564339596u,1966452497u},{700u,641173998u,1167924792u},p_em12_448};
static const Part p_em12_453[] = {
{{0u,2u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},2560u,217u,1882816811u,1595489994u},
};
static const Model m_em12_453 = {{2147484416u,4u,34u,114u,114u,3u,2u,2u,1u,537069592u},{912u,1577544336u,678727201u},{912u,1971968216u,904927376u},{16u,922119481u,609657675u},{700u,3856362429u,3206175656u},p_em12_453};
static const Part p_em15_444[] = {
{{0u,1u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},8000u,662u,2181394663u,2300323244u},
{{0u,2u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},1952u,144u,156732366u,4062547117u},
{{0u,2u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},384u,36u,3004553778u,2423524479u},
{{0u,2u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},384u,36u,715239269u,407121607u},
{{0u,2u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},6656u,582u,3404719256u,1404725007u},
};
static const Model m_em15_444 = {{2684355328u,4u,34u,770u,882u,3u,75u,75u,5u,537069592u},{6160u,3741280179u,3448910962u},{3528u,3110001761u,507855784u},{600u,639603552u,2193853772u},{3704u,915775928u,4161981869u},p_em15_444};
static const Part p_em15_446[] = {
{{0u,0u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},512u,34u,1281416366u,3892807705u},
{{0u,0u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},672u,37u,1890828989u,613838837u},
{{0u,0u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},384u,26u,346797693u,1474780517u},
{{2u,0u,255u,255u,0u,127u,127u,127u,0u,0u,70u,0u,255u},832u,80u,1369225975u,2911951763u},
{{0u,0u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},10912u,942u,1914229440u,139826466u},
};
static const Model m_em15_446 = {{2684354560u,4u,34u,616u,641u,3u,32u,32u,5u,536938497u},{4928u,4199602618u,3264994632u},{2564u,977966666u,2511375369u},{256u,4292904604u,256718155u},{2812u,2134684877u,1794811701u},p_em15_446};
static const Part p_em15_448[] = {
{{0u,2u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},2496u,217u,634125105u,556828952u},
};
static const Model m_em15_448 = {{2147484416u,4u,34u,114u,114u,3u,2u,2u,1u,537069592u},{912u,2049620157u,4223744493u},{912u,185339134u,3157497573u},{16u,564339596u,1966452497u},{700u,641173998u,1167924792u},p_em15_448};
static const Part p_em15_453[] = {
{{0u,2u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},2560u,217u,1882816811u,1595489994u},
};
static const Model m_em15_453 = {{2147484416u,4u,34u,114u,114u,3u,2u,2u,1u,537069592u},{912u,1577544336u,678727201u},{912u,1971968216u,904927376u},{16u,922119481u,609657675u},{700u,3856362429u,3206175656u},p_em15_453};
static const Part p_em15_476[] = {
{{0u,1u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},8128u,674u,1264299766u,3366264923u},
{{0u,0u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},224u,18u,2082799879u,3171969837u},
{{0u,0u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},224u,18u,2260892195u,193752871u},
{{0u,2u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},5632u,482u,2727610454u,1605626905u},
{{0u,2u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},1920u,146u,1763639291u,2964621386u},
};
static const Model m_em15_476 = {{2684355328u,4u,34u,716u,831u,3u,80u,80u,5u,537069592u},{5728u,637834422u,2499390985u},{3324u,2573550980u,3845796711u},{640u,3354425050u,3209075661u},{3420u,3734810811u,2442662555u},p_em15_476};
static const Part p_em15_478[] = {
{{0u,0u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},512u,34u,1281416366u,3892807705u},
{{0u,0u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},544u,33u,2678301823u,1185866419u},
{{0u,0u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},384u,30u,3941661197u,4101645166u},
{{2u,0u,255u,255u,0u,178u,178u,178u,0u,0u,70u,0u,255u},544u,48u,4075969297u,3531852416u},
{{0u,0u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},10368u,912u,2646462920u,2758476318u},
};
static const Model m_em15_478 = {{2684355328u,4u,34u,587u,604u,3u,29u,29u,5u,537069592u},{4696u,3673672060u,2094131865u},{2416u,444409735u,2149623128u},{232u,2699860241u,3115857365u},{2704u,3724684158u,2539636230u},p_em15_478};
static const Part p_em15_480[] = {
{{0u,1u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},5952u,518u,2615033801u,3100060313u},
{{0u,2u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},864u,72u,497277232u,1744334961u},
{{0u,2u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},1952u,146u,3419551411u,3059370979u},
{{0u,2u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},800u,72u,3041627658u,2280623624u},
{{0u,1u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},960u,73u,3332110874u,1414764945u},
{{0u,2u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},7264u,630u,1587950281u,1771734748u},
};
static const Model m_em15_480 = {{2684355328u,4u,34u,831u,891u,3u,85u,85u,6u,537069592u},{6648u,4000407823u,3024841202u},{3564u,2268134957u,893953369u},{680u,1726231289u,3406774145u},{3752u,1092425323u,1904761928u},p_em15_480};
static const Part p_em15_482[] = {
{{0u,0u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},512u,34u,1411852821u,643039946u},
{{0u,0u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},640u,37u,1667192920u,2341061294u},
{{0u,0u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},352u,26u,3135746427u,1129081064u},
{{2u,0u,255u,255u,0u,102u,102u,102u,0u,0u,70u,0u,255u},544u,48u,3659503559u,703935896u},
{{0u,0u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},10688u,924u,2683778141u,3047915248u},
};
static const Model m_em15_482 = {{2684355328u,4u,34u,591u,615u,3u,33u,33u,5u,537069592u},{4728u,3664658628u,2416323280u},{2460u,3509652193u,468090738u},{264u,3753808946u,2026112165u},{2864u,967018350u,193626142u},p_em15_482};
static const Part p_em15_457[] = {
{{0u,1u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},8384u,706u,3000164684u,3810504894u},
{{0u,2u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},256u,14u,3356025763u,1024039377u},
{{0u,2u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},3104u,228u,987759869u,3002995998u},
{{0u,2u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},3072u,280u,2338133509u,4134688301u},
{{0u,2u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},608u,54u,3433460560u,3936042536u},
{{0u,2u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},608u,54u,3958718891u,2205148716u},
};
static const Model m_em15_457 = {{2684355328u,4u,34u,737u,836u,3u,90u,90u,6u,537069592u},{5896u,4140860198u,243706262u},{3344u,1774100112u,992275505u},{720u,1683879962u,789095532u},{3564u,2251173470u,2675175768u},p_em15_457};
static const Part p_em15_459[] = {
{{0u,0u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},512u,34u,817476800u,3126281177u},
{{0u,0u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},352u,26u,1423389766u,248444425u},
{{0u,0u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},640u,37u,3499723803u,257120620u},
{{0u,0u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},768u,48u,3946699777u,2760165099u},
{{2u,0u,255u,255u,0u,127u,127u,127u,0u,0u,70u,0u,255u},544u,48u,3617217164u,2915447792u},
{{0u,0u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},11040u,962u,1793926555u,1390264846u},
};
static const Model m_em15_459 = {{2684355328u,4u,34u,636u,663u,3u,34u,34u,6u,537069592u},{5088u,2408577388u,3624319586u},{2652u,2120639746u,2736553762u},{272u,3505229016u,1930681763u},{3112u,2305079571u,417722763u},p_em15_459};
static const Part p_pl00_4[] = {
{{0u,2u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},5376u,452u,3504056466u,1225071419u},
{{3u,3u,4u,255u,0u,20u,17u,17u,0u,0u,45u,0u,255u},4672u,430u,1351486249u,2426449037u},
{{3u,3u,4u,255u,0u,20u,17u,17u,0u,0u,45u,0u,255u},4736u,430u,603682710u,1437735752u},
{{0u,7u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},672u,42u,4196500894u,3410790990u},
{{0u,7u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},320u,20u,2638897142u,989075623u},
{{3u,0u,1u,255u,0u,51u,51u,51u,0u,0u,50u,0u,255u},448u,38u,1412747353u,1884930500u},
{{3u,0u,1u,255u,0u,51u,51u,51u,0u,0u,50u,0u,255u},448u,38u,1378822044u,2298347663u},
{{0u,7u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},5920u,566u,3271060689u,1689674621u},
{{0u,7u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},192u,14u,2050821417u,1424951134u},
{{3u,0u,1u,255u,0u,51u,51u,51u,0u,0u,60u,0u,255u},2464u,212u,3226542554u,2527968981u},
{{3u,0u,1u,255u,0u,63u,63u,63u,0u,0u,60u,0u,255u},640u,45u,1648036422u,2807631029u},
{{3u,0u,1u,255u,0u,25u,25u,25u,0u,0u,60u,0u,255u},416u,45u,2046966748u,1872512813u},
{{3u,0u,1u,255u,0u,51u,51u,51u,0u,0u,60u,0u,255u},320u,25u,1905355990u,304260897u},
{{3u,0u,1u,255u,0u,63u,63u,63u,0u,0u,60u,0u,255u},1920u,162u,3719919096u,798925575u},
};
static const Model m_pl00_4 = {{2684355328u,4u,119u,1484u,1489u,8u,107u,107u,14u,537069592u},{11872u,1037130222u,2571716413u},{5956u,2851895294u,3723850031u},{856u,684290440u,1719870259u},{5380u,2025842072u,3841411194u},p_pl00_4};
static const Part p_pl00_10[] = {
{{3u,3u,4u,255u,0u,25u,25u,25u,0u,0u,50u,0u,255u},1632u,142u,1889455619u,4216105040u},
{{2u,3u,255u,255u,0u,25u,25u,25u,0u,0u,60u,0u,255u},768u,84u,1075445974u,1723480362u},
{{3u,3u,4u,255u,0u,25u,25u,25u,0u,0u,60u,0u,255u},608u,64u,4070553087u,3553164121u},
{{2u,3u,255u,255u,0u,127u,127u,127u,0u,0u,40u,0u,255u},608u,38u,1301861106u,1651334476u},
{{0u,3u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},3840u,323u,3981538065u,295626826u},
{{3u,5u,6u,255u,0u,20u,17u,17u,0u,0u,45u,0u,255u},736u,60u,2120751191u,3724356044u},
{{3u,3u,4u,255u,0u,20u,17u,17u,0u,0u,45u,0u,255u},8064u,683u,657188017u,1205694997u},
{{3u,3u,4u,255u,0u,25u,25u,25u,0u,0u,60u,0u,255u},736u,67u,768028205u,4017771554u},
};
static const Model m_pl00_10 = {{2684355328u,4u,117u,797u,983u,8u,89u,89u,8u,537069592u},{6376u,542395644u,2324769308u},{3932u,2418720164u,3074477909u},{712u,3964022087u,491533772u},{2656u,3586933848u,105004474u},p_pl00_10};
static const Part p_pl00_13[] = {
{{2u,0u,255u,255u,0u,76u,76u,76u,0u,0u,50u,0u,255u},736u,54u,3998678639u,1884396334u},
{{0u,0u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},640u,51u,3405601789u,3364323484u},
};
static const Model m_pl00_13 = {{2684355328u,4u,119u,58u,65u,8u,1u,1u,2u,537069592u},{464u,997523196u,3294798416u},{260u,3377731365u,2236256946u},{8u,2110163525u,3219048136u},{256u,303633636u,1861136508u},p_pl00_13};
static const Part p_pl00_8[] = {
{{0u,4u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},9664u,900u,1559970043u,767105594u},
};
static const Model m_pl00_8 = {{2684355072u,4u,35u,475u,421u,5u,37u,37u,1u,537069592u},{3800u,924007527u,1715219636u},{1684u,2031651919u,2779209930u},{296u,1269328889u,1402187723u},{1900u,2925819431u,4217937466u},p_pl00_8};
static const Part p_pl00_6[] = {
{{0u,4u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},6080u,550u,3883433335u,1318778816u},
{{0u,4u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},448u,38u,3757845521u,57461423u},
{{0u,4u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},512u,38u,948743304u,2901352925u},
{{0u,4u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},1952u,156u,2168449868u,1137733989u},
{{2u,4u,255u,255u,1u,38u,38u,38u,0u,0u,70u,0u,255u},960u,88u,2005234939u,94381524u},
{{2u,4u,255u,255u,1u,38u,38u,38u,0u,0u,50u,0u,255u},928u,88u,1769577525u,1709075215u},
};
static const Model m_pl00_6 = {{2684355072u,4u,33u,542u,552u,5u,12u,12u,6u,537069592u},{4336u,3165957313u,2427825152u},{2208u,3723660861u,4277762876u},{96u,3662083178u,17742705u},{2308u,2945488830u,2144071405u},p_pl00_6};
static const Part p_pl00_9[] = {
{{4u,2u,255u,3u,255u,0u,0u,0u,0u,0u,0u,0u,255u},192u,16u,3166701468u,75968753u},
{{4u,2u,255u,3u,255u,0u,0u,0u,0u,0u,0u,0u,255u},352u,32u,2338182946u,391538694u},
{{4u,0u,255u,1u,255u,0u,0u,0u,0u,0u,0u,0u,255u},352u,32u,1967961690u,843443539u},
{{4u,2u,255u,3u,255u,0u,0u,0u,0u,0u,0u,0u,255u},256u,24u,817576075u,1538365934u},
{{4u,0u,255u,1u,255u,0u,0u,0u,0u,0u,0u,0u,255u},256u,24u,4111708465u,1629839374u},
{{4u,2u,255u,3u,255u,0u,0u,0u,0u,0u,0u,0u,255u},192u,16u,3744880695u,32654502u},
{{4u,0u,255u,1u,255u,0u,0u,0u,0u,0u,0u,0u,255u},192u,16u,4264053430u,772379378u},
{{4u,0u,255u,1u,255u,0u,0u,0u,0u,0u,0u,0u,255u},1280u,144u,2424132061u,332280093u},
{{4u,2u,255u,3u,255u,0u,0u,0u,0u,0u,0u,0u,255u},416u,46u,3468611995u,720977709u},
{{4u,0u,255u,1u,255u,0u,0u,0u,0u,0u,0u,0u,255u},416u,46u,3667398415u,1947566917u},
{{4u,2u,255u,3u,255u,0u,0u,0u,0u,0u,0u,0u,255u},608u,64u,3421287374u,2487366806u},
{{4u,0u,255u,1u,255u,0u,0u,0u,0u,0u,0u,0u,255u},608u,64u,3647953554u,3717152923u},
{{4u,0u,255u,1u,255u,0u,0u,0u,0u,0u,0u,0u,255u},896u,72u,17137522u,3470707253u},
{{4u,0u,255u,1u,255u,0u,0u,0u,0u,0u,0u,0u,255u},736u,54u,3017825266u,2391881896u},
{{4u,0u,255u,1u,255u,0u,0u,0u,0u,0u,0u,0u,255u},544u,48u,40639697u,3333721639u},
{{4u,0u,255u,1u,255u,0u,0u,0u,0u,0u,0u,0u,255u},448u,48u,3124742604u,2080779253u},
{{4u,0u,255u,1u,255u,0u,0u,0u,0u,0u,0u,0u,255u},448u,48u,2153837795u,2126960246u},
{{4u,0u,255u,1u,255u,0u,0u,0u,0u,0u,0u,0u,255u},448u,48u,1300731022u,3807353240u},
{{4u,0u,255u,1u,255u,0u,0u,0u,0u,0u,0u,0u,255u},448u,48u,3970327405u,3498396118u},
{{4u,0u,255u,1u,255u,0u,0u,0u,0u,0u,0u,0u,255u},480u,48u,4023747757u,1971943050u},
{{4u,0u,255u,1u,255u,0u,0u,0u,0u,0u,0u,0u,255u},448u,48u,2259793442u,215677399u},
{{4u,0u,255u,1u,255u,0u,0u,0u,0u,0u,0u,0u,255u},448u,48u,1843017884u,2784034310u},
{{4u,0u,255u,1u,255u,0u,0u,0u,0u,0u,0u,0u,255u},448u,48u,4017372664u,2008501400u},
{{4u,0u,255u,1u,255u,0u,0u,0u,0u,0u,0u,0u,255u},448u,48u,2944439253u,3794782515u},
{{4u,0u,255u,1u,255u,0u,0u,0u,0u,0u,0u,0u,255u},480u,48u,420583795u,1295888061u},
{{4u,0u,255u,1u,255u,0u,0u,0u,0u,0u,0u,0u,255u},448u,48u,188531632u,1855771990u},
{{4u,0u,255u,1u,255u,0u,0u,0u,0u,0u,0u,0u,255u},448u,48u,3520261465u,3715281382u},
{{4u,0u,255u,1u,255u,0u,0u,0u,0u,0u,0u,0u,255u},352u,32u,1550511526u,2295783182u},
{{4u,0u,255u,1u,255u,0u,0u,0u,0u,0u,0u,0u,255u},320u,32u,2432710535u,2536603330u},
{{4u,0u,255u,1u,255u,0u,0u,0u,0u,0u,0u,0u,255u},864u,96u,4262469360u,2843854338u},
{{4u,0u,255u,1u,255u,0u,0u,0u,0u,0u,0u,0u,255u},352u,32u,3784010086u,3922802489u},
{{4u,0u,255u,1u,255u,0u,0u,0u,0u,0u,0u,0u,255u},320u,32u,2956355895u,114708108u},
{{4u,0u,255u,1u,255u,0u,0u,0u,0u,0u,0u,0u,255u},192u,16u,918827382u,1690413001u},
{{4u,2u,255u,3u,255u,0u,0u,0u,0u,0u,0u,0u,255u},224u,24u,2806326154u,3426958171u},
{{4u,0u,255u,1u,255u,0u,0u,0u,0u,0u,0u,0u,255u},224u,24u,3347366639u,2582328483u},
{{4u,0u,255u,1u,255u,0u,0u,0u,0u,0u,0u,0u,255u},2848u,288u,3569332183u,2021923639u},
{{4u,2u,255u,3u,255u,0u,0u,0u,0u,0u,0u,0u,255u},928u,96u,4073394296u,1979684176u},
{{4u,0u,255u,1u,255u,0u,0u,0u,0u,0u,0u,0u,255u},928u,96u,563086312u,1183266417u},
{{4u,0u,255u,1u,255u,0u,0u,0u,0u,0u,0u,0u,255u},352u,32u,3173248778u,3336069636u},
};
static const Model m_pl00_9 = {{2684355072u,4u,33u,1586u,1517u,5u,141u,141u,39u,537069592u},{12688u,506053830u,4250013422u},{6068u,184977462u,2170137753u},{1128u,1673407508u,937144145u},{6644u,2046616419u,3015748617u},p_pl00_9};
static const Part p_pl00_24[] = {
{{0u,0u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},4896u,439u,3352159545u,2916515817u},
{{3u,0u,1u,255u,0u,25u,25u,25u,0u,0u,60u,0u,255u},1760u,153u,1146758465u,261400593u},
};
static const Model m_pl00_24 = {{2684354560u,4u,2u,298u,307u,2u,2u,2u,2u,536938497u},{2384u,2178872745u,1983474962u},{1228u,252061853u,686825227u},{16u,2891620465u,2787928658u},{1056u,274647771u,3434716877u},p_pl00_24};
static const Part p_wep02_10[] = {
{{0u,0u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},5088u,439u,4140785717u,3468471562u},
{{3u,0u,1u,255u,0u,25u,25u,25u,0u,0u,60u,0u,255u},1792u,153u,3055691186u,1060641769u},
};
static const Model m_wep02_10 = {{2684354560u,4u,2u,298u,324u,2u,2u,2u,2u,536938497u},{2384u,551836485u,1477015050u},{1296u,1999429191u,378652863u},{16u,2023828804u,1372183546u},{1056u,1823263216u,967337197u},p_wep02_10};
static const Part p_extra_451[] = {
{{0u,2u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},2496u,217u,3641054988u,1534844006u},
};
static const Model m_extra_451 = {{2147484416u,4u,34u,114u,114u,3u,2u,2u,1u,537069592u},{912u,3136458814u,1152925029u},{912u,2991623821u,4169556938u},{16u,564339596u,1966452497u},{700u,1604073923u,272925336u},p_extra_451};
static const Part p_extra_456[] = {
{{0u,2u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},2560u,217u,1767087690u,3637799140u},
};
static const Model m_extra_456 = {{2147484416u,4u,34u,114u,114u,3u,2u,2u,1u,537069592u},{912u,3817238399u,1445984293u},{912u,3808720552u,280768947u},{16u,922119481u,609657675u},{700u,901021376u,1894476040u},p_extra_456};
static const Part p_extra_467[] = {
{{0u,0u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},1632u,126u,2686625579u,2795563369u},
{{0u,0u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},288u,18u,416420385u,2128887935u},
};
static const Model m_extra_467 = {{2684355328u,4u,34u,78u,115u,1u,2u,2u,2u,537069592u},{624u,242322032u,2464053443u},{460u,2906250874u,2040515029u},{16u,3375885294u,1131448789u},{340u,79823614u,2926407376u},p_extra_467};
static const Part p_extra_484[] = {
{{0u,0u,255u,255u,255u,0u,0u,0u,0u,0u,0u,0u,255u},3200u,230u,1569886695u,301147693u},
};
static const Model m_extra_484 = {{2684355328u,4u,34u,121u,175u,1u,6u,6u,1u,537069592u},{968u,3158842242u,534096828u},{700u,2974067242u,2931511648u},{48u,2593962771u,3390889994u},{756u,11672476u,3683351780u},p_extra_484};
static const Texture t_extra_468[] = {
{3623679845u,1639440447u,64u,64u,14u,{1u,1u,1u,1u,0u,0u,0u,0u},4294967295u,{0u,0u,0u}},
};
static const Texture t_extra_469[] = {
{1578314968u,4252408067u,128u,128u,14u,{1u,1u,1u,1u,0u,0u,0u,0u},4294967295u,{0u,0u,0u}},
};
static const Texture t_extra_485[] = {
{750636811u,1963015600u,128u,128u,14u,{1u,1u,1u,1u,0u,0u,0u,0u},4294967295u,{0u,0u,0u}},
};
static const Texture t_extra_486[] = {
{137436048u,3095878342u,128u,128u,14u,{1u,1u,1u,1u,0u,0u,0u,0u},4294967295u,{0u,0u,0u}},
};
#if RE4DC_ACTOR_GANADO_PS2_STUMP
#include "actor_material_records_ps2_stump.inc"
#endif
#if RE4DC_ACTOR_PL08
#include "actor_material_records_pl08.inc"
#endif
#if RE4DC_LEON_HEADLESS
#include "actor_material_records_leon_neck.inc"
#endif
#if RE4DC_NATIVE_MODEL_REGISTRY && !RE4DC_NATIVE_MODEL_REGISTRY_PACK
#include "native_model_registry_facts.inc" // private registry bundle (tools/d367/model_registry.py)
#endif
static const Role roles[] = {
{0u,0u,472u,473u,&m_em12_472,t_em12_473,3u},
{0u,1u,474u,473u,&m_em12_474,t_em12_473,3u},
{0u,2u,448u,473u,&m_em12_448,t_em12_473,3u},
{0u,3u,453u,473u,&m_em12_453,t_em12_473,3u},
{1u,0u,444u,445u,&m_em15_444,t_em15_445,3u},
{1u,1u,446u,445u,&m_em15_446,t_em15_445,3u},
{1u,2u,448u,445u,&m_em15_448,t_em15_445,3u},
{1u,3u,453u,445u,&m_em15_453,t_em15_445,3u},
{2u,0u,476u,477u,&m_em15_476,t_em15_477,3u},
{2u,1u,478u,477u,&m_em15_478,t_em15_477,3u},
{2u,2u,448u,477u,&m_em15_448,t_em15_477,3u},
{2u,3u,453u,477u,&m_em15_453,t_em15_477,3u},
{3u,0u,480u,481u,&m_em15_480,t_em15_481,3u},
{3u,1u,482u,481u,&m_em15_482,t_em15_481,3u},
{3u,2u,448u,481u,&m_em15_448,t_em15_481,3u},
{3u,3u,453u,481u,&m_em15_453,t_em15_481,3u},
{4u,0u,457u,458u,&m_em15_457,t_em15_458,3u},
{4u,1u,459u,458u,&m_em15_459,t_em15_458,3u},
{4u,2u,448u,458u,&m_em15_448,t_em15_458,3u},
{4u,3u,453u,458u,&m_em15_453,t_em15_458,3u},
{256u,0u,4u,5u,&m_pl00_4,t_pl00_5,8u},
{256u,1u,10u,5u,&m_pl00_10,t_pl00_5,8u},
{256u,2u,13u,5u,&m_pl00_13,t_pl00_5,8u},
{256u,3u,8u,7u,&m_pl00_8,t_pl00_7,5u},
{256u,4u,6u,7u,&m_pl00_6,t_pl00_7,5u},
{256u,5u,10u,17u,&m_wep02_10,t_pl00_17,2u},
{256u,6u,24u,17u,&m_pl00_24,t_pl00_17,2u},
{256u,7u,9u,7u,&m_pl00_9,t_pl00_7,5u},
{1u,2u,451u,445u,&m_extra_451,t_em15_445,3u},
{1u,3u,456u,445u,&m_extra_456,t_em15_445,3u},
{1u,4u,467u,468u,&m_extra_467,t_extra_468,1u},
{1u,4u,467u,469u,&m_extra_467,t_extra_469,1u},
{1u,4u,484u,485u,&m_extra_484,t_extra_485,1u},
{1u,4u,484u,486u,&m_extra_484,t_extra_486,1u},
{2u,2u,451u,477u,&m_extra_451,t_em15_477,3u},
{2u,3u,456u,477u,&m_extra_456,t_em15_477,3u},
{2u,4u,467u,468u,&m_extra_467,t_extra_468,1u},
{2u,4u,467u,469u,&m_extra_467,t_extra_469,1u},
{2u,4u,484u,485u,&m_extra_484,t_extra_485,1u},
{2u,4u,484u,486u,&m_extra_484,t_extra_486,1u},
{3u,2u,451u,481u,&m_extra_451,t_em15_481,3u},
{3u,3u,456u,481u,&m_extra_456,t_em15_481,3u},
{3u,4u,467u,468u,&m_extra_467,t_extra_468,1u},
{3u,4u,467u,469u,&m_extra_467,t_extra_469,1u},
{3u,4u,484u,485u,&m_extra_484,t_extra_485,1u},
{3u,4u,484u,486u,&m_extra_484,t_extra_486,1u},
{4u,2u,451u,458u,&m_extra_451,t_em15_458,3u},
{4u,3u,456u,458u,&m_extra_456,t_em15_458,3u},
{4u,4u,467u,468u,&m_extra_467,t_extra_468,1u},
{4u,4u,467u,469u,&m_extra_467,t_extra_469,1u},
{4u,4u,484u,485u,&m_extra_484,t_extra_485,1u},
{4u,4u,484u,486u,&m_extra_484,t_extra_486,1u},
#if RE4DC_ACTOR_PL08
#include "actor_material_records_pl08_roles.inc"
#endif
#if RE4DC_LEON_HEADLESS
#include "actor_material_records_leon_headless_roles.inc"
#endif
#if RE4DC_ACTOR_GANADO_APP0_GRIP
#include "actor_material_records_app0_grip.inc"
#endif
#if RE4DC_ACTOR_GANADO_PS2_STUMP
{0u,1u,475u,473u,&m_ps2_var_475,t_em12_473,3u},
{1u,1u,447u,445u,&m_ps2_var_447,t_em15_445,3u},
{2u,1u,479u,477u,&m_ps2_var_479,t_em15_477,3u},
{3u,1u,483u,481u,&m_ps2_var_483,t_em15_481,3u},
{4u,1u,460u,458u,&m_ps2_var_460,t_em15_458,3u},
{0u,2u,449u,473u,&m_ps2_var_449,t_em12_473,3u},
{0u,2u,450u,473u,&m_ps2_var_450,t_em12_473,3u},
{0u,3u,454u,473u,&m_ps2_var_454,t_em12_473,3u},
{0u,3u,455u,473u,&m_ps2_var_455,t_em12_473,3u},
{1u,2u,449u,445u,&m_ps2_var_449,t_em15_445,3u},
{1u,2u,450u,445u,&m_ps2_var_450,t_em15_445,3u},
{1u,3u,454u,445u,&m_ps2_var_454,t_em15_445,3u},
{1u,3u,455u,445u,&m_ps2_var_455,t_em15_445,3u},
{2u,2u,449u,477u,&m_ps2_var_449,t_em15_477,3u},
{2u,2u,450u,477u,&m_ps2_var_450,t_em15_477,3u},
{2u,3u,454u,477u,&m_ps2_var_454,t_em15_477,3u},
{2u,3u,455u,477u,&m_ps2_var_455,t_em15_477,3u},
{3u,2u,449u,481u,&m_ps2_var_449,t_em15_481,3u},
{3u,2u,450u,481u,&m_ps2_var_450,t_em15_481,3u},
{3u,3u,454u,481u,&m_ps2_var_454,t_em15_481,3u},
{3u,3u,455u,481u,&m_ps2_var_455,t_em15_481,3u},
{4u,2u,449u,458u,&m_ps2_var_449,t_em15_458,3u},
{4u,2u,450u,458u,&m_ps2_var_450,t_em15_458,3u},
{4u,3u,454u,458u,&m_ps2_var_454,t_em15_458,3u},
{4u,3u,455u,458u,&m_ps2_var_455,t_em15_458,3u},
#endif
#if RE4DC_NATIVE_MODEL_REGISTRY && !RE4DC_NATIVE_MODEL_REGISTRY_PACK
#include "native_model_registry_roles.inc"
#endif
};
static const SourceBlob source_blobs[] = {
{&m_em12_472,2u,472u,{34336u,2997423784u,3272199119u}},
{&m_em12_474,2u,474u,{24512u,453315272u,3010720984u}},
{&m_em12_448,2u,448u,{5888u,1499917228u,791628390u}},
{&m_em12_453,2u,453u,{5952u,1647175752u,605450942u}},
{&m_em15_444,2u,444u,{32352u,3840264440u,1872904324u}},
{&m_em15_446,2u,446u,{24704u,1381831128u,717566172u}},
{&m_em15_448,2u,448u,{5888u,1499917228u,791628390u}},
{&m_em15_453,2u,453u,{5952u,1647175752u,605450942u}},
{&m_em15_476,2u,476u,{30176u,2233623600u,647840425u}},
{&m_em15_478,2u,478u,{23392u,3981545666u,1202855768u}},
{&m_em15_480,2u,480u,{33472u,1246683236u,845007980u}},
{&m_em15_482,2u,482u,{24032u,3673810097u,1399340653u}},
{&m_em15_457,2u,457u,{30592u,2846045305u,1709299521u}},
{&m_em15_459,2u,459u,{25984u,704445181u,3369395744u}},
{&m_pl00_4,1u,4u,{55520u,3899481476u,1971272157u}},
{&m_pl00_10,1u,10u,{33280u,367828794u,4056977168u}},
{&m_pl00_13,1u,13u,{4864u,747595294u,3701262740u}},
{&m_pl00_8,1u,8u,{23104u,3908073075u,3552951803u}},
{&m_pl00_6,1u,6u,{20832u,4192286635u,3164217089u}},
{&m_pl00_9,1u,9u,{49376u,471224945u,249341549u}},
{&m_pl00_24,1u,24u,{11584u,2233619000u,2194923148u}},
{&m_wep02_10,3u,10u,{11872u,2216956229u,3376609189u}},
{&m_extra_451,2u,451u,{5888u,3446078520u,2841889831u}},
{&m_extra_456,2u,456u,{5952u,3566550875u,4284573839u}},
{&m_extra_467,2u,467u,{4256u,3007827131u,2804973797u}},
{&m_extra_484,2u,484u,{6528u,1573052172u,1172918242u}},
#if RE4DC_ACTOR_GANADO_PS2_STUMP
{&m_ps2_var_475,2u,475u,{3200u,1128395770u,2403039293u}},
{&m_ps2_var_447,2u,447u,{2944u,1978383310u,1061756992u}},
{&m_ps2_var_479,2u,479u,{2976u,1450011754u,3920562518u}},
{&m_ps2_var_483,2u,483u,{2912u,1990468374u,1286629251u}},
{&m_ps2_var_460,2u,460u,{3040u,1374730771u,2938463957u}},
{&m_ps2_var_449,2u,449u,{5888u,2529276789u,3486964274u}},
{&m_ps2_var_450,2u,450u,{5888u,3608060527u,2496883440u}},
{&m_ps2_var_454,2u,454u,{5952u,1963098602u,1580596659u}},
{&m_ps2_var_455,2u,455u,{5952u,4022166836u,2700100576u}},
#endif
#if RE4DC_ACTOR_PL08
#include "actor_material_records_pl08_blobs.inc"
#endif
#if RE4DC_LEON_HEADLESS
RE4DC_LEON_NECK_BLOB,
#endif
#if RE4DC_NATIVE_MODEL_REGISTRY && !RE4DC_NATIVE_MODEL_REGISTRY_PACK
#include "native_model_registry_blobs.inc"
#endif
};
#if RE4DC_NATIVE_MODEL_REGISTRY_PACK
// NATIVE_MODEL_REGISTRY_PACK: the room package's identity rows (coarse_actor_registry_pack.inc builds them from the
// validated package and publishes them for one room generation; actor_lifetime.inc retires them at room leave).
// They follow the reviewed rows above in one index space: role r >= kBaseRoles is room row r-kBaseRoles, blob
// t >= kBaseBlobs room blob t-kBaseBlobs. The capacity constants above bound both lifetime masks.
constexpr unsigned kBaseRoles=sizeof(roles)/sizeof(roles[0]),kBaseBlobs=sizeof(source_blobs)/sizeof(source_blobs[0]);
constexpr unsigned kRoomRoles=kRoleMaskBits-kBaseRoles,kRoomBlobs=kBlobMaskBits-kBaseBlobs;
static_assert(kBaseRoles<kRoleMaskBits && kBaseBlobs<kBlobMaskBits,"room identity rows need free mask bits");
struct RoomRows { const Role* roles;const SourceBlob* blobs;unsigned role_count,blob_count,generation; };
RoomRows room_rows{};
inline unsigned role_count() {return kBaseRoles+room_rows.role_count;}
inline const Role& role_row(unsigned r) {return r<kBaseRoles?roles[r]:room_rows.roles[r-kBaseRoles];}
inline unsigned blob_count() {return kBaseBlobs+room_rows.blob_count;}
inline const SourceBlob& blob_row(unsigned t) {return t<kBaseBlobs?source_blobs[t]:room_rows.blobs[t-kBaseBlobs];}
#define RE4DC_ROLE_COUNT (re4dc_material::role_count())
#define RE4DC_ROLE(r) (re4dc_material::role_row(r))
#define RE4DC_BLOB_COUNT (re4dc_material::blob_count())
#define RE4DC_BLOB(t) (re4dc_material::blob_row(t))
#else
#define RE4DC_ROLE_COUNT sizeof(roles)/sizeof(roles[0])
#define RE4DC_ROLE(r) roles[r]
#define RE4DC_BLOB_COUNT sizeof(source_blobs)/sizeof(source_blobs[0])
#define RE4DC_BLOB(t) source_blobs[t]
#endif
