/* light_view.h: a character's light inputs as the renderer's light rule reads them, in place (lane eng-e1j, ruling
 * H-016.2). Addresses into the model record only (services/draw.cpp e1_light_view), gathered for a picture as the
 * skeleton's views are; the rule (render/source_light.inc) reads each field where the behaviour keeps it. C and C++. */
#ifndef E1_LIGHT_VIEW_H
#define E1_LIGHT_VIEW_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
/* cLightInfo from EnableMask on (model.h: 0x50 .. 0x70) */
typedef struct {
    uint8_t enable;    /* EnableMask: the light kinds the model accepts (0x41: parent lights only) */
    uint8_t flag;      /* Flag: bits 0-1 the volume's shape (0 cylinder, 1 / 3 sphere, 2 box), bit 2 */
    int8_t parts;      /* PartsNo: the light origin's part + 1 (0: the model) */
    uint8_t pad;
    uint32_t select;   /* SelectMask: bit i, light i never applies */
    float offset[3];   /* the light origin's offset */
    float size[3];     /* the volume's size */
} E1LightInfoIn;
typedef struct E1LightView {
    const void* model;
    const E1LightInfoIn* info;
    const uint32_t* be_flag;      /* 0x8000: no lights; 8: added ambient */
    const uint32_t* data_flags;   /* the model data's flags (0x40000000), or 0 */
    const uint8_t* color;         /* the material colour (RGBA; black when the model has no model info) */
    const uint8_t* tev_group;     /* TevScaleGroup */
    const uint8_t* addamb;        /* AddAmb r, g, b */
    const uint32_t* status;       /* the room status word (Status_flg[1]) */
    const uint16_t* tev_table;    /* the TEV scale of each group + 1 (0: not resolved: 255), the renderer's table */
} E1LightView;
int e1_light_view(const void* model, E1LightView* v);
#ifdef __cplusplus
}
#endif
#endif
