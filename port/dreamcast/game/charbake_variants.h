#pragma once
// charbake (tools/d367/charbake/charbake.py table; charbake.mk CHARBAKE_TOGGLE test builds): the character
// texture variants the look toggle can select. Keys and labels only: the packages are private and a
// CHARBAKE_TOGGLE disc carries them in its tex.pak (charbake.py pak --add). Variant 0 is the play build.
// hair_colour: the keys of the hair colour images; hair_pair: the colour + mask pair keys the runtime derives from
// them (native_ui.cpp model_mask_key), which the hair materials draw.
namespace re4dc_charbake {
struct Variant { char label[4]; unsigned leon_crc, leon_fnv, ganado_crc, ganado_fnv, hair_colour_crc[2], hair_colour_fnv[2],
                 hair_pair_crc[2], hair_pair_fnv[2]; };
constexpr unsigned kLeonCrc=0xec255e66U, kLeonFnv=0x76812316U, kGanadoCrc=0x1279a218U, kGanadoFnv=0xf8cb0063U;
constexpr Variant variants[] = {
    {"CUR",0xec255e66U,0x76812316U,0x1279a218U,0xf8cb0063U,{0xac381b1aU,0x7a9de1fdU},{0x3ade84b1U,0x0e415f15U},{0xfc24a99cU,0x9cf7f055U},{0x03d13534U,0xd40aae38U}},  // leon play, ganado play, hair play
    {"AO",0xb627530bU,0x9a0b6350U,0x1ffce19fU,0x1dee5492U,{0xac381b1aU,0x7a9de1fdU},{0x3ade84b1U,0x0e415f15U},{0xfc24a99cU,0x9cf7f055U},{0x03d13534U,0xd40aae38U}},  // leon ao, ganado ao, hair play
    {"SKY",0x3eef2044U,0x72f5709dU,0x0307f7a7U,0x11ae8763U,{0xac381b1aU,0x7a9de1fdU},{0x3ade84b1U,0x0e415f15U},{0xfc24a99cU,0x9cf7f055U},{0x03d13534U,0xd40aae38U}},  // leon aosky, ganado aosky, hair play
    {"GCB",0x4ee2229cU,0xce6b2de4U,0xb929ae73U,0xcf5e23b2U,{0x463edd54U,0x8d620ef1U},{0x95033757U,0xe722dbdaU},{0xc869d36eU,0x72cc6b7dU},{0xbf59146fU,0x2ad1a6a8U}},  // leon gcb, ganado gcb, hair gcb
    {"LVQ",0x49abeafeU,0x882b9aa5U,0x1279a218U,0xf8cb0063U,{0xac381b1aU,0x7a9de1fdU},{0x3ade84b1U,0x0e415f15U},{0xfc24a99cU,0x9cf7f055U},{0x03d13534U,0xd40aae38U}},  // leon vq, ganado play, hair play
    {"GVQ",0x172a4735U,0x95d0fae5U,0xb929ae73U,0xcf5e23b2U,{0x463edd54U,0x8d620ef1U},{0x95033757U,0xe722dbdaU},{0xc869d36eU,0x72cc6b7dU},{0xbf59146fU,0x2ad1a6a8U}},  // leon gcbvq, ganado gcb, hair gcb
};
constexpr unsigned kCount = sizeof(variants) / sizeof(variants[0]);
}
