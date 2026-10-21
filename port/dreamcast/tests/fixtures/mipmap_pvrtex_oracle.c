/* Independent oracle: link with the pinned pvrtex decoder, not mipmap_vq.py. */
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include "pvr_texture_decoder.h"

int mipmap_oracle_decode(const void *payload, size_t bytes, unsigned native_format,
                         unsigned side, int mipmapped, unsigned level,
                         unsigned char *rgba, size_t capacity) {
    const ptPixelFormat formats[3] = { PT_RGB565, PT_ARGB1555, PT_ARGB4444 };
    if(native_format > 2 || side < 8 || side > 1024 || (side & (side - 1)))
        return -1;
    const ptPixelFormat format = formats[native_format];
    if(bytes != CalcTextureSize(side, side, format, mipmapped, 1, 2048))
        return -2;
    unsigned output_side = mipmapped ? 1u << level : side;
    if(output_side > side || capacity < output_side * output_side * 4u)
        return -3;
    PvrTexDecoder decoder;
    ptdInit(&decoder);
    ptdSetSize(&decoder, side, side, mipmapped);
    ptdSetPixelFormat(&decoder, format);
    ptdSetCompressedSource(&decoder, NULL, payload, PVR_FULL_CODEBOOK, 0);
    ptdDecode(&decoder);
    memcpy(rgba, decoder.result_mips[mipmapped ? level : 0],
           output_side * output_side * 4u);
    ptdFree(&decoder);
    return (int)(output_side * output_side * 4u);
}

/* Compact uncompressed PAL4 with the package's unchanged ARGB4444 palette. */
int mipmap_oracle_decode_pal4(const void *payload, size_t bytes,
                              unsigned side, int mipmapped, unsigned level,
                              unsigned char *rgba, size_t capacity) {
    if(side < 8 || side > 1024 || (side & (side - 1)))
        return -1;
    size_t texels = CalcTextureSize(side, side, PT_PALETTE_4B, mipmapped, 0, 0);
    if(bytes != texels + 32)
        return -2;
    unsigned output_side = mipmapped ? 1u << level : side;
    if(output_side > side || capacity < output_side * output_side * 4u)
        return -3;
    pxlABGR8888 palette[16];
    for(unsigned i = 0; i < 16; ++i) {
        uint16_t word;
        memcpy(&word, (const unsigned char *)payload + texels + 2u * i, 2);
        unsigned char color[4] = {
            ((word >> 8u) & 15u) * 17u, ((word >> 4u) & 15u) * 17u,
            (word & 15u) * 17u, (word >> 12u) * 17u
        };
        memcpy(&palette[i], color, 4);
    }
    PvrTexDecoder decoder;
    ptdInit(&decoder);
    ptdSetSize(&decoder, side, side, mipmapped);
    ptdSetPixelFormat(&decoder, PT_PALETTE_4B);
    ptdSetUncompressedSource(&decoder, payload);
    ptdSetPalette(&decoder, 16, palette);
    ptdDecode(&decoder);
    memcpy(rgba, decoder.result_mips[mipmapped ? level : 0],
           output_side * output_side * 4u);
    ptdFree(&decoder);
    return (int)(output_side * output_side * 4u);
}

/* Native uncompressed16-bit mip layout, decoded by the actual pinned codec. */
int mipmap_oracle_decode_twiddled(const void *payload, size_t bytes,
                                 unsigned native_format, unsigned side,
                                 int mipmapped, unsigned level,
                                 unsigned char *rgba, size_t capacity) {
    const ptPixelFormat formats[3] = { PT_RGB565, PT_ARGB1555, PT_ARGB4444 };
    if(native_format > 2 || side < 8 || side > 1024 || (side & (side - 1)))
        return -1;
    if(bytes != CalcTextureSize(side, side, formats[native_format], mipmapped, 0, 0))
        return -2;
    unsigned output_side = mipmapped ? 1u << level : side;
    if(output_side > side || capacity < output_side * output_side * 4u)
        return -3;
    PvrTexDecoder decoder;
    ptdInit(&decoder);
    ptdSetSize(&decoder, side, side, mipmapped);
    ptdSetPixelFormat(&decoder, formats[native_format]);
    ptdSetUncompressedSource(&decoder, payload);
    ptdDecode(&decoder);
    memcpy(rgba, decoder.result_mips[mipmapped ? level : 0],
           output_side * output_side * 4u);
    ptdFree(&decoder);
    return (int)(output_side * output_side * 4u);
}
