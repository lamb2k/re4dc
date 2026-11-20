// Native garment service (lane eng-svc5): pl_cloth.cpp's entry points as engine code (garment.h).
//
// A garment is one row of kGarments: its chain tables and the constants its set-up writes. GarmentSet fills the
// behaviour's chain work (PlCloth, which the behaviour owns and the cloth service steps) from that row and hands it to
// the cloth service; the per-character Set / Move functions pick the rows a costume wears. The chain tables are the
// game's data, kept as engine tables (Ashley's skirt's event swing limits equal the normal ones: one table). The lapel
// pose of Ashley's alternate costume is the original's arithmetic on the SDK interface, so its bones are the
// original's on the PC.
#include "types.h"
#include "global.h"
#include "model.h"
#include "math_sub.h"
#include "pl_cloth.h"
#include "pendulum.h"
#include "garment.h"

extern "C" {
f32 sqrtf(f32 x);
f32 asinf(f32 x);
GarmentCounters garment_cnt;
int garment_control;
}

// Ashley's alternate-costume lapels (pl_cloth.cpp's name; not in include/pl_cloth.h).
void girlLapelMove(cModel* pl);

// The chain works the player units hand in (include/pl_cloth.h).
PlCloth leonHair;
PlCloth leonJacket;
PlCloth leonHolster;
PlCloth girlHair;
PlCloth girlSkirt;
PlCloth girlSweater;
PlCloth luisHair;
PlCloth adaDress;
PlCloth adaHair;
PlCloth adaRibbon;

namespace {

// ---- the chain tables (the game's garment data) ----
u8 leonHairP[21] = {65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85};
u8 leonHairUp[21] = {0xFF, 65, 66, 0xFF, 68, 0xFF, 70, 0xFF, 72, 0xFF, 74, 0xFF, 76, 0xFF, 78, 0xFF, 80, 0xFF, 82, 0xFF, 84};
u8 leonHairDp[21] = {66, 67, 0xFF, 69, 0xFF, 71, 0xFF, 73, 0xFF, 75, 0xFF, 77, 0xFF, 79, 0xFF, 81, 0xFF, 83, 0xFF, 85, 0xFF};
f32 leonHairMax[21] = {0.4f, 0.5f, 0.6f, 0.4f, 0.5f, 0.4f, 0.5f, 0.3f, 0.3f, 0.15f, 0.15f, 0.15f, 0.15f, 0.15f, 0.15f, 0.3f, 0.3f, 0.4f, 0.5f, 0.4f, 0.5f};
f32 leonHairWindS[21] = {0.0f, 0.0f, 0.0f, 1.0f, 1.0f, 1.5f, 1.5f, 2.0f, 2.0f, 2.5f, 2.5f, 3.0f, 3.0f, -2.5f, -2.5f, -2.0f, -2.0f, -1.5f, -1.5f, 0.0f, 0.0f};
f32 leonHairWindR[21] = {0.5f, 1.0f, 1.0f, 0.5f, 1.0f, 0.5f, 1.0f, 0.5f, 1.0f, 0.5f, 1.0f, 0.5f, 1.0f, 0.5f, 1.0f, 0.5f, 1.0f, 0.5f, 1.0f, 0.5f, 1.0f};
u8 leonJacketP[24] = {86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109};
u8 leonJacketLp[24] = {0xFF, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 108, 109, 0xFF, 0xFF, 0xFF};
u8 leonJacketRp[24] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
u8 leonJacketUp[24] = {0xFF, 86, 87, 0xFF, 89, 0xFF, 91, 0xFF, 93, 0xFF, 95, 0xFF, 97, 0xFF, 99, 0xFF, 101, 0xFF, 103, 0xFF, 105, 0xFF, 107, 108};
u8 leonJacketDp[24] = {87, 88, 0xFF, 90, 0xFF, 92, 0xFF, 94, 0xFF, 96, 0xFF, 98, 0xFF, 100, 0xFF, 102, 0xFF, 104, 0xFF, 106, 0xFF, 108, 109, 0xFF};
f32 leonJacketMax[24] = {0.1f, 0.2f, 0.3f, 0.1f, 0.3f, 0.1f, 0.3f, 0.1f, 0.3f, 0.1f, 0.3f, 0.1f, 0.3f, 0.1f, 0.3f, 0.1f, 0.3f, 0.1f, 0.3f, 0.1f, 0.3f, 0.1f, 0.2f, 0.3f};
f32 leonJacketWindS[24] = {0.0f, 0.0f, 0.0f, 0.4f, 0.4f, 0.9f, 0.9f, 1.2f, 1.2f, 1.5f, 1.5f, 1.7f, 1.7f, 1.9f, 1.9f, 2.1f, 2.1f, 2.4f, 2.4f, 2.8f, 2.8f, 3.1f, 3.1f, 3.1f};
f32 leonJacketWindR[24] = {1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f};
u8 leonHolsterP[2] = {29, 30};
u8 leonHolsterLp[2] = {0xFF, 0xFF};
u8 leonHolsterRp[2] = {0xFF, 0xFF};
u8 leonHolsterUp[2] = {0xFF, 0xFF};
u8 leonHolsterDp[2] = {0xFF, 0xFF};
f32 leonHolsterMax[2] = {0.1f, 0.1f};
f32 leonHolsterWindS[2] = {0.0f, 1.5f};
f32 leonHolsterWindR[2] = {0.1f, 0.1f};
u8 girlHairP[21] = {64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84};
u8 girlHairUp[21] = {0xFF, 64, 0xFF, 66, 0xFF, 68, 0xFF, 70, 71, 0xFF, 73, 74, 0xFF, 76, 77, 0xFF, 79, 80, 0xFF, 82, 83};
u8 girlHairDp[21] = {65, 0xFF, 67, 0xFF, 69, 0xFF, 71, 72, 0xFF, 74, 75, 0xFF, 77, 78, 0xFF, 80, 81, 0xFF, 83, 84, 0xFF};
f32 girlHairMax[21] = {0.4f, 0.5f, 0.4f, 0.5f, 0.4f, 0.5f, 0.3f, 0.4f, 0.5f, 0.3f, 0.4f, 0.5f, 0.3f, 0.4f, 0.5f, 0.3f, 0.4f, 0.5f, 0.3f, 0.4f, 0.5f};
f32 girlHairMaxEvt[21] = {0.4f, 0.5f, 0.1f, 0.3f, 0.4f, 0.5f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f};
f32 girlHairWindS[21] = {0.0f, 0.2f, 1.0f, 1.2f, 0.0f, 0.2f, 1.0f, 1.2f, 1.4f, 0.0f, 0.2f, 0.4f, 1.0f, 1.2f, 1.4f, 0.0f, 0.2f, 0.4f, 1.0f, 1.2f, 1.4f};
f32 girlHairWindR[21] = {0.2f, 0.3f, 0.2f, 0.3f, 0.2f, 0.3f, 0.2f, 0.3f, 0.4f, 0.2f, 0.3f, 0.4f, 0.2f, 0.3f, 0.4f, 0.2f, 0.3f, 0.4f, 0.2f, 0.3f, 0.4f};
u8 girlSkirtP[48] = {93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140};
u8 girlSkirtLp[48] = {96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 93, 94, 95};
u8 girlSkirtUp[48] = {0xFF, 93, 94, 0xFF, 96, 97, 0xFF, 99, 100, 0xFF, 102, 103, 0xFF, 105, 106, 0xFF, 108, 109, 0xFF, 111, 112, 0xFF, 114, 115, 0xFF, 117, 118, 0xFF, 120, 121, 0xFF, 123, 124, 0xFF, 126, 127, 0xFF, 129, 130, 0xFF, 132, 133, 0xFF, 135, 136, 0xFF, 138, 139};
u8 girlSkirtDp[48] = {94, 95, 0xFF, 97, 98, 0xFF, 100, 101, 0xFF, 103, 104, 0xFF, 106, 107, 0xFF, 109, 110, 0xFF, 112, 113, 0xFF, 115, 116, 0xFF, 118, 119, 0xFF, 121, 122, 0xFF, 124, 125, 0xFF, 127, 128, 0xFF, 130, 131, 0xFF, 133, 134, 0xFF, 136, 137, 0xFF, 139, 140, 0xFF};
f32 girlSkirtMax[48] = {0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f};
f32 girlSkirtWindS[48] = {0.0f, 0.0f, 0.0f, 0.2f, 0.2f, 0.2f, 0.5f, 0.5f, 0.5f, 0.5f, 0.5f, 0.5f, 1.0f, 1.0f, 1.0f, 1.2f, 1.2f, 1.2f, 1.5f, 1.5f, 1.5f, 1.8f, 1.8f, 1.8f, 2.0f, 2.0f, 2.0f, 2.2f, 2.2f, 2.2f, 2.5f, 2.5f, 2.5f, 2.7f, 2.7f, 2.7f, 3.0f, 3.0f, 3.0f, 1.0f, 1.0f, 1.0f, 1.5f, 1.5f, 1.5f, 2.0f, 2.0f, 2.0f};
f32 girlSkirtWindR[48] = {0.3f, 0.6f, 1.0f, 0.3f, 0.6f, 1.0f, 0.3f, 0.6f, 1.0f, 0.3f, 0.6f, 1.0f, 0.3f, 0.6f, 1.0f, 0.3f, 0.6f, 1.0f, 0.3f, 0.6f, 1.0f, 0.3f, 0.6f, 1.0f, 0.3f, 0.6f, 1.0f, 0.3f, 0.6f, 1.0f, 0.3f, 0.6f, 1.0f, 0.3f, 0.6f, 1.0f, 0.3f, 0.6f, 1.0f, 0.3f, 0.6f, 1.0f, 0.3f, 0.6f, 1.0f, 0.3f, 0.6f, 1.0f};
u8 girlSweaterP[8] = {85, 86, 87, 88, 89, 90, 91, 92};
u8 girlSweaterLp[8] = {87, 88, 89, 90, 91, 92, 0xFF, 0xFF};
u8 girlSweaterUp[8] = {0xFF, 85, 0xFF, 87, 0xFF, 89, 0xFF, 91};
u8 girlSweaterDp[8] = {86, 0xFF, 88, 0xFF, 90, 0xFF, 92, 0xFF};
f32 girlSweaterMax[8] = {0.3f, 0.6f, 0.3f, 0.6f, 0.3f, 0.6f, 0.3f, 0.6f};
f32 girlSweaterWindS[8] = {0.0f, 0.0f, 1.0f, 1.0f, 2.0f, 2.0f, 3.0f, 3.0f};
f32 girlSweaterWindR[8] = {0.5f, 1.0f, 0.5f, 1.0f, 0.5f, 1.0f, 0.5f, 1.0f};
u8 girlRibbonP[12] = {144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155};
u8 girlRibbonUp[12] = {0xFF, 144, 0xFF, 146, 0xFF, 148, 0xFF, 150, 0xFF, 152, 0xFF, 154};
u8 girlRibbonDp[12] = {145, 0xFF, 147, 0xFF, 149, 0xFF, 151, 0xFF, 153, 0xFF, 155, 0xFF};
f32 girlRibbonMax[12] = {0.3f, 0.6f, 0.3f, 0.6f, 0.3f, 0.6f, 0.3f, 0.6f, 0.3f, 0.6f, 0.3f, 0.6f};
f32 girlRibbonWindS[12] = {0.0f, 0.0f, 0.5f, 0.5f, 1.0f, 1.0f, 1.5f, 1.5f, 2.0f, 2.0f, 2.5f, 2.5f};
f32 girlRibbonWindR[12] = {0.5f, 1.0f, 0.5f, 1.0f, 0.5f, 1.0f, 0.5f, 1.0f, 0.5f, 1.0f, 0.5f, 1.0f};
u8 luisHairP[26] = {64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89};
u8 luisHairUp[26] = {0xFF, 64, 0xFF, 66, 67, 0xFF, 69, 70, 0xFF, 72, 0xFF, 74, 0xFF, 76, 0xFF, 78, 0xFF, 80, 0xFF, 82, 83, 0xFF, 85, 86, 0xFF, 88};
u8 luisHairDp[26] = {65, 0xFF, 67, 68, 0xFF, 70, 71, 0xFF, 73, 0xFF, 75, 0xFF, 77, 0xFF, 79, 0xFF, 81, 0xFF, 83, 84, 0xFF, 86, 87, 0xFF, 89, 0xFF};
f32 luisHairMax[26] = {0.2f, 0.3f, 0.2f, 0.3f, 0.4f, 0.2f, 0.3f, 0.4f, 0.15f, 0.15f, 0.15f, 0.15f, 0.15f, 0.15f, 0.15f, 0.15f, 0.15f, 0.15f, 0.2f, 0.3f, 0.4f, 0.2f, 0.3f, 0.4f, 0.2f, 0.3f};
f32 luisHairWindS[26] = {0.0f, 0.0f, 1.0f, 1.0f, 1.0f, 1.5f, 1.5f, 1.5f, 2.0f, 2.0f, 2.5f, 2.5f, 3.0f, 3.0f, -2.5f, -2.5f, -2.0f, -2.0f, -1.5f, -1.5f, -1.5f, -1.0f, -1.0f, -1.0f, -0.5f, -0.5f};
f32 luisHairWindR[26] = {0.5f, 1.0f, 0.5f, 1.0f, 1.0f, 0.5f, 1.0f, 1.0f, 0.5f, 1.0f, 0.5f, 1.0f, 0.5f, 1.0f, 0.5f, 1.0f, 0.5f, 1.0f, 0.5f, 1.0f, 1.0f, 0.5f, 1.0f, 1.0f, 0.5f, 1.0f};
u8 adaDressP[146] = {73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212, 213, 214, 215, 216, 217, 218};
u8 adaDressUp[146] = {0xFF, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 0xFF, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 0xFF, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 0xFF, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 0xFF, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 0xFF, 128, 129, 130, 131, 132, 133, 134, 135, 136, 0xFF, 138, 139, 140, 141, 142, 143, 144, 145, 146, 0xFF, 148, 149, 150, 151, 152, 153, 154, 155, 156, 0xFF, 158, 159, 160, 161, 162, 163, 164, 165, 166, 0xFF, 168, 169, 170, 171, 172, 173, 174, 175, 176, 0xFF, 178, 179, 180, 181, 182, 183, 184, 185, 186, 0xFF, 188, 189, 190, 191, 192, 193, 194, 195, 196, 0xFF, 198, 199, 200, 201, 202, 203, 204, 205, 206, 0xFF, 208, 209, 210, 211, 212, 213, 214, 215, 216, 217};
u8 adaDressDp[146] = {74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 0xFF, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 0xFF, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 0xFF, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 0xFF, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 0xFF, 129, 130, 131, 132, 133, 134, 135, 136, 137, 0xFF, 139, 140, 141, 142, 143, 144, 145, 146, 147, 0xFF, 149, 150, 151, 152, 153, 154, 155, 156, 157, 0xFF, 159, 160, 161, 162, 163, 164, 165, 166, 167, 0xFF, 169, 170, 171, 172, 173, 174, 175, 176, 177, 0xFF, 179, 180, 181, 182, 183, 184, 185, 186, 187, 0xFF, 189, 190, 191, 192, 193, 194, 195, 196, 197, 0xFF, 199, 200, 201, 202, 203, 204, 205, 206, 207, 0xFF, 209, 210, 211, 212, 213, 214, 215, 216, 217, 218, 0xFF};
u8 adaDressLp[146] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 198, 199, 200, 201, 202, 203, 204, 205, 206, 207};
u8 adaDressULp[146] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 0xFF, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 0xFF, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 0xFF, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 0xFF, 118, 119, 120, 121, 122, 123, 124, 125, 126, 0xFF, 128, 129, 130, 131, 132, 133, 134, 135, 136, 0xFF, 138, 139, 140, 141, 142, 143, 144, 145, 146, 0xFF, 148, 149, 150, 151, 152, 153, 154, 155, 156, 0xFF, 158, 159, 160, 161, 162, 163, 164, 165, 166, 0xFF, 168, 169, 170, 171, 172, 173, 174, 175, 176, 0xFF, 178, 179, 180, 181, 182, 183, 184, 185, 186, 0xFF, 188, 189, 190, 191, 192, 193, 194, 195, 196, 0xFF, 198, 198, 199, 200, 201, 202, 203, 204, 205, 206};
f32 adaDressMax[146] = {1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f};
f32 adaDressWindS[146] = {0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.5f, 0.5f, 0.5f, 0.5f, 0.5f, 0.5f, 0.5f, 0.5f, 0.5f, 0.5f, 0.5f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.5f, 1.5f, 1.5f, 1.5f, 1.5f, 1.5f, 1.5f, 1.5f, 1.5f, 1.5f, 1.5f, 2.0f, 2.0f, 2.0f, 2.0f, 2.0f, 2.0f, 2.0f, 2.0f, 2.0f, 2.0f, 2.0f, 2.5f, 2.5f, 2.5f, 2.5f, 2.5f, 2.5f, 2.5f, 2.5f, 2.5f, 2.5f, 3.0f, 3.0f, 3.0f, 3.0f, 3.0f, 3.0f, 3.0f, 3.0f, 3.0f, 3.0f, -2.5f, -2.5f, -2.5f, -2.5f, -2.5f, -2.5f, -2.5f, -2.5f, -2.5f, -2.5f, -2.0f, -2.0f, -2.0f, -2.0f, -2.0f, -2.0f, -2.0f, -2.0f, -2.0f, -2.0f, -1.5f, -1.5f, -1.5f, -1.5f, -1.5f, -1.5f, -1.5f, -1.5f, -1.5f, -1.5f, -1.0f, -1.0f, -1.0f, -1.0f, -1.0f, -1.0f, -1.0f, -1.0f, -1.0f, -1.0f, -0.5f, -0.5f, -0.5f, -0.5f, -0.5f, -0.5f, -0.5f, -0.5f, -0.5f, -0.5f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.5f, 0.5f, 0.5f, 0.5f, 0.5f, 0.5f, 0.5f, 0.5f, 0.5f, 0.5f, 0.5f};
f32 adaDressWindR[146] = {0.5f, 0.6f, 0.7f, 0.8f, 0.9f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 0.5f, 0.6f, 0.7f, 0.8f, 0.9f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 0.5f, 0.6f, 0.7f, 0.8f, 0.9f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 0.5f, 0.6f, 0.7f, 0.8f, 0.9f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 0.5f, 0.6f, 0.7f, 0.8f, 0.9f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 0.5f, 0.6f, 0.7f, 0.8f, 0.9f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 0.5f, 0.6f, 0.7f, 0.8f, 0.9f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 0.5f, 0.6f, 0.7f, 0.8f, 0.9f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 0.5f, 0.6f, 0.7f, 0.8f, 0.9f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 0.5f, 0.6f, 0.7f, 0.8f, 0.9f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 0.5f, 0.6f, 0.7f, 0.8f, 0.9f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 0.5f, 0.6f, 0.7f, 0.8f, 0.9f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 0.5f, 0.6f, 0.7f, 0.8f, 0.9f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 0.5f, 0.6f, 0.7f, 0.8f, 0.9f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f};
u8 adaHairP[14] = {65, 66, 67, 68, 69, 70, 71, 72, 219, 220, 221, 222, 223, 224};
u8 adaHairUp[14] = {0xFF, 65, 0xFF, 67, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 219, 0xFF, 221, 0xFF, 223};
u8 adaHairDp[14] = {66, 0xFF, 68, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 220, 0xFF, 222, 0xFF, 224, 0xFF};
f32 adaHairMax[14] = {0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.2f, 0.1f, 0.1f, 0.1f, 0.1f};
f32 adaHairWindS[14] = {0.0f, 0.0f, 0.5f, 0.5f, 1.0f, 1.5f, 2.0f, 2.5f, 3.0f, 3.0f, -2.5f, -2.5f, -2.0f, -2.0f};
f32 adaHairWindR[14] = {0.5f, 1.0f, 0.5f, 1.0f, 0.5f, 0.5f, 0.5f, 0.5f, 0.5f, 1.0f, 0.5f, 1.0f, 0.5f, 1.0f};
u8 adaRibbonP[22] = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22};
u8 adaRibbonUp[22] = {0xFF, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 0xFF, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21};
u8 adaRibbonDp[22] = {2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 0xFF, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 0xFF};
f32 adaRibbonMax[22] = {0.6f, 0.7f, 0.8f, 0.9f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 0.6f, 0.7f, 0.8f, 0.9f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f};
f32 adaRibbonWindS[22] = {0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f};
f32 adaRibbonWindR[22] = {0.5f, 0.6f, 0.7f, 0.8f, 0.9f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 0.5f, 0.6f, 0.7f, 0.8f, 0.9f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f};
CLOTH_AT_SET leonHairAt[4] = {
    {0x0000, 0x04, 0x04, 1.0f, 90.0f, {0.0f, 90.0f, 0.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x04, 0x04, 1.0f, 85.0f, {0.0f, 90.0f, 50.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x04, 0x04, 1.0f, 90.0f, {0.0f, 100.0f, 25.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x04, 0x04, 1.0f, 75.0f, {0.0f, 65.0f, 50.0f}, {0.0f, 0.0f, 0.0f}},
};
CLOTH_AT_SET leonJacketAt[6] = {
    {0x0000, 0x02, 0x02, 1.0f, 130.0f, {0.0f, 0.0f, 0.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x02, 0x02, 1.0f, 130.0f, {0.0f, -50.0f, 20.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x02, 0x11, 0.5f, 130.0f, {0.0f, 0.0f, 0.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x11, 0x11, 1.0f, 140.0f, {0.0f, 0.0f, 0.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x11, 0x12, 0.4f, 125.0f, {0.0f, 0.0f, 0.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x11, 0x16, 0.4f, 125.0f, {0.0f, 0.0f, 0.0f}, {0.0f, 0.0f, 0.0f}},
};
CLOTH_AT_SET leonHolsterAt[1] = {
    {0x0000, 0x02, 0x02, 1.0f, 90.0f, {0.0f, 50.0f, 0.0f}, {0.0f, 0.0f, 0.0f}},
};
CLOTH_AT_SET girlHairAt[5] = {
    {0x0000, 0x04, 0x04, 1.0f, 72.0f, {0.0f, 50.0f, -10.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x03, 0x04, 0.5f, 75.0f, {0.0f, 60.0f, 0.0f}, {0.0f, 60.0f, 0.0f}},
    {0x0000, 0x03, 0x03, 1.0f, 100.0f, {0.0f, -20.0f, 10.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x04, 0x04, 1.0f, 70.0f, {-3.0f, 100.0f, 42.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x04, 0x04, 1.0f, 68.0f, {-3.0f, 60.0f, 45.0f}, {0.0f, 0.0f, 0.0f}},
};
CLOTH_AT_SET girlHairAtEvt[7] = {
    {0x0000, 0x04, 0x04, 1.0f, 65.0f, {0.0f, 50.0f, -10.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x03, 0x04, 0.5f, 80.0f, {0.0f, 50.0f, 0.0f}, {0.0f, 50.0f, 0.0f}},
    {0x0000, 0x03, 0x03, 1.0f, 90.0f, {0.0f, 0.0f, 0.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x04, 0x04, 1.0f, 65.0f, {0.0f, 100.0f, 35.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x04, 0x04, 1.0f, 60.0f, {0.0f, 70.0f, 50.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x02, 0x03, 0.3f, 100.0f, {-50.0f, 0.0f, -10.0f}, {-50.0f, 0.0f, -10.0f}},
    {0x0000, 0x02, 0x03, 0.3f, 100.0f, {50.0f, 0.0f, -10.0f}, {50.0f, 0.0f, -10.0f}},
};
CLOTH_AT_SET girlSkirtAt[11] = {
    {0x0000, 0x12, 0x12, 1.0f, 80.0f, {10.0f, -50.0f, -20.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x12, 0x12, 1.0f, 80.0f, {10.0f, -100.0f, -20.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x12, 0x12, 1.0f, 80.0f, {10.0f, -150.0f, -20.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x12, 0x12, 1.0f, 80.0f, {10.0f, -200.0f, -20.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x16, 0x16, 1.0f, 80.0f, {-10.0f, -50.0f, -20.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x16, 0x16, 1.0f, 80.0f, {-10.0f, -100.0f, -20.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x16, 0x16, 1.0f, 80.0f, {-10.0f, -150.0f, -20.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x16, 0x16, 1.0f, 80.0f, {-10.0f, -200.0f, -20.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x12, 0x16, 0.5f, 80.0f, {0.0f, -50.0f, -20.0f}, {0.0f, -50.0f, -20.0f}},
    {0x0000, 0x12, 0x16, 0.5f, 80.0f, {0.0f, -100.0f, -20.0f}, {0.0f, -100.0f, -20.0f}},
    {0x0000, 0x12, 0x16, 0.5f, 85.0f, {0.0f, -150.0f, -20.0f}, {0.0f, -150.0f, -20.0f}},
};
CLOTH_AT_SET girlSkirtAtEvt[11] = {
    {0x0000, 0x12, 0x12, 1.0f, 90.0f, {10.0f, -50.0f, -20.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x12, 0x12, 1.0f, 90.0f, {10.0f, -100.0f, -20.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x12, 0x12, 1.0f, 90.0f, {10.0f, -150.0f, -20.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x12, 0x12, 1.0f, 90.0f, {10.0f, -200.0f, -20.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x16, 0x16, 1.0f, 90.0f, {-10.0f, -50.0f, -20.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x16, 0x16, 1.0f, 90.0f, {-10.0f, -100.0f, -20.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x16, 0x16, 1.0f, 90.0f, {-10.0f, -150.0f, -20.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x16, 0x16, 1.0f, 90.0f, {-10.0f, -200.0f, -20.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x12, 0x16, 0.5f, 80.0f, {0.0f, -50.0f, -20.0f}, {0.0f, -50.0f, -20.0f}},
    {0x0000, 0x12, 0x16, 0.5f, 80.0f, {0.0f, -100.0f, -20.0f}, {0.0f, -100.0f, -20.0f}},
    {0x0000, 0x12, 0x16, 0.5f, 85.0f, {0.0f, -150.0f, -20.0f}, {0.0f, -150.0f, -20.0f}},
};
CLOTH_AT_SET girlSweaterAt[6] = {
    {0x0000, 0x02, 0x02, 1.0f, 100.0f, {-70.0f, 0.0f, 0.0f}, {-70.0f, 0.0f, 0.0f}},
    {0x0000, 0x02, 0x02, 1.0f, 100.0f, {70.0f, 0.0f, 0.0f}, {70.0f, 0.0f, 0.0f}},
    {0x0000, 0x02, 0x03, 0.75f, 100.0f, {-70.0f, 0.0f, 0.0f}, {-70.0f, 0.0f, 0.0f}},
    {0x0000, 0x02, 0x03, 0.75f, 100.0f, {70.0f, 0.0f, 0.0f}, {70.0f, 0.0f, 0.0f}},
    {0x0000, 0x02, 0x03, 0.5f, 100.0f, {-70.0f, 0.0f, 0.0f}, {-70.0f, 0.0f, 0.0f}},
    {0x0000, 0x02, 0x03, 0.5f, 100.0f, {70.0f, 0.0f, 0.0f}, {70.0f, 0.0f, 0.0f}},
};
CLOTH_AT_SET girlRibbonAt[8] = {
    {0x0000, 0x02, 0x02, 1.0f, 110.0f, {-30.0f, 0.0f, 0.0f}, {-30.0f, 0.0f, 0.0f}},
    {0x0000, 0x02, 0x02, 1.0f, 110.0f, {30.0f, 0.0f, 0.0f}, {30.0f, 0.0f, 0.0f}},
    {0x0000, 0x01, 0x02, 0.75f, 110.0f, {-30.0f, 0.0f, 0.0f}, {-30.0f, 0.0f, 0.0f}},
    {0x0000, 0x01, 0x02, 0.75f, 110.0f, {30.0f, 0.0f, 0.0f}, {30.0f, 0.0f, 0.0f}},
    {0x0000, 0x01, 0x02, 0.5f, 110.0f, {-30.0f, 0.0f, 0.0f}, {-30.0f, 0.0f, 0.0f}},
    {0x0000, 0x01, 0x02, 0.5f, 110.0f, {30.0f, 0.0f, 0.0f}, {30.0f, 0.0f, 0.0f}},
    {0x0000, 0x11, 0x12, 0.2f, 140.0f, {20.0f, 0.0f, 0.0f}, {20.0f, 0.0f, 0.0f}},
    {0x0000, 0x11, 0x16, 0.2f, 140.0f, {-20.0f, 0.0f, 0.0f}, {-20.0f, 0.0f, 0.0f}},
};
CLOTH_AT_SET luisHairAt[7] = {
    {0x0000, 0x04, 0x04, 1.0f, 75.0f, {0.0f, 50.0f, 8.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x04, 0x04, 1.0f, 70.0f, {0.0f, 90.0f, 75.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x04, 0x04, 1.0f, 75.0f, {0.0f, 70.0f, 35.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x04, 0x04, 1.0f, 70.0f, {0.0f, 65.0f, 80.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x04, 0x04, 1.0f, 70.0f, {0.0f, 35.0f, 80.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x04, 0x04, 1.0f, 70.0f, {0.0f, 20.0f, 10.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x03, 0x03, 1.0f, 90.0f, {0.0f, 0.0f, 10.0f}, {0.0f, 0.0f, 0.0f}},
};
CLOTH_AT_SET adaDressAt[35] = {
    {0x0000, 0x12, 0x12, 1.0f, 85.0f, {20.0f, 100.0f, 0.0f}, {20.0f, 100.0f, 0.0f}},
    {0x0000, 0x12, 0x12, 1.0f, 85.0f, {20.0f, 50.0f, 0.0f}, {20.0f, 50.0f, 0.0f}},
    {0x0000, 0x12, 0x12, 1.0f, 85.0f, {20.0f, 0.0f, 0.0f}, {20.0f, 0.0f, 0.0f}},
    {0x0000, 0x12, 0x13, 0.8f, 95.0f, {20.0f, 0.0f, 0.0f}, {20.0f, 0.0f, 0.0f}},
    {0x0000, 0x12, 0x13, 0.6f, 95.0f, {20.0f, 0.0f, 0.0f}, {20.0f, 0.0f, 0.0f}},
    {0x0000, 0x12, 0x13, 0.4f, 95.0f, {20.0f, 0.0f, 0.0f}, {20.0f, 0.0f, 0.0f}},
    {0x0000, 0x12, 0x13, 0.2f, 95.0f, {20.0f, 0.0f, 0.0f}, {20.0f, 0.0f, 0.0f}},
    {0x0000, 0x13, 0x13, 1.0f, 95.0f, {20.0f, 0.0f, 0.0f}, {20.0f, 0.0f, 0.0f}},
    {0x0000, 0x13, 0x14, 0.8f, 95.0f, {20.0f, 0.0f, 0.0f}, {20.0f, 0.0f, 0.0f}},
    {0x0000, 0x13, 0x14, 0.6f, 95.0f, {20.0f, 0.0f, 0.0f}, {20.0f, 0.0f, 0.0f}},
    {0x0000, 0x13, 0x14, 0.4f, 95.0f, {20.0f, 0.0f, 0.0f}, {20.0f, 0.0f, 0.0f}},
    {0x0000, 0x13, 0x14, 0.2f, 95.0f, {20.0f, 0.0f, 0.0f}, {20.0f, 0.0f, 0.0f}},
    {0x0000, 0x14, 0x14, 1.0f, 95.0f, {20.0f, 0.0f, 0.0f}, {20.0f, 0.0f, 0.0f}},
    {0x0000, 0x16, 0x16, 1.0f, 85.0f, {-20.0f, 50.0f, 0.0f}, {-20.0f, 50.0f, 0.0f}},
    {0x0000, 0x16, 0x16, 1.0f, 85.0f, {-20.0f, 100.0f, 0.0f}, {-20.0f, 100.0f, 0.0f}},
    {0x0000, 0x16, 0x16, 1.0f, 85.0f, {-20.0f, 0.0f, 0.0f}, {-20.0f, 0.0f, 0.0f}},
    {0x0000, 0x16, 0x17, 0.8f, 95.0f, {-20.0f, 0.0f, 0.0f}, {-20.0f, 0.0f, 0.0f}},
    {0x0000, 0x16, 0x17, 0.6f, 95.0f, {-20.0f, 0.0f, 0.0f}, {-20.0f, 0.0f, 0.0f}},
    {0x0000, 0x16, 0x17, 0.4f, 95.0f, {-20.0f, 0.0f, 0.0f}, {-20.0f, 0.0f, 0.0f}},
    {0x0000, 0x16, 0x17, 0.2f, 95.0f, {-20.0f, 0.0f, 0.0f}, {-20.0f, 0.0f, 0.0f}},
    {0x0000, 0x17, 0x17, 1.0f, 95.0f, {-20.0f, 0.0f, 0.0f}, {-20.0f, 0.0f, 0.0f}},
    {0x0000, 0x17, 0x18, 0.8f, 95.0f, {-20.0f, 0.0f, 0.0f}, {-20.0f, 0.0f, 0.0f}},
    {0x0000, 0x17, 0x18, 0.6f, 95.0f, {-20.0f, 0.0f, 0.0f}, {-20.0f, 0.0f, 0.0f}},
    {0x0000, 0x17, 0x18, 0.4f, 95.0f, {-20.0f, 0.0f, 0.0f}, {-20.0f, 0.0f, 0.0f}},
    {0x0000, 0x17, 0x18, 0.2f, 95.0f, {-20.0f, 0.0f, 0.0f}, {-20.0f, 0.0f, 0.0f}},
    {0x0000, 0x18, 0x18, 1.0f, 95.0f, {-20.0f, 0.0f, 0.0f}, {-20.0f, 0.0f, 0.0f}},
    {0x0000, 0x12, 0x16, 0.5f, 95.0f, {0.0f, 0.0f, 0.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x12, 0x16, 0.5f, 95.0f, {0.0f, -50.0f, 0.0f}, {0.0f, -50.0f, 0.0f}},
    {0x0000, 0x12, 0x16, 0.5f, 95.0f, {0.0f, -100.0f, 0.0f}, {0.0f, -100.0f, 0.0f}},
    {0x0000, 0x12, 0x16, 0.5f, 95.0f, {0.0f, -150.0f, 0.0f}, {0.0f, -150.0f, 0.0f}},
    {0x0000, 0x12, 0x16, 0.5f, 95.0f, {0.0f, -200.0f, 0.0f}, {0.0f, -200.0f, 0.0f}},
    {0x0000, 0x12, 0x16, 0.5f, 95.0f, {0.0f, -250.0f, 0.0f}, {0.0f, -250.0f, 0.0f}},
    {0x0000, 0x13, 0x17, 0.5f, 95.0f, {0.0f, 0.0f, 0.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x13, 0x17, 0.5f, 95.0f, {0.0f, -50.0f, 0.0f}, {0.0f, -50.0f, 0.0f}},
    {0x0000, 0x13, 0x17, 0.5f, 95.0f, {0.0f, -100.0f, 0.0f}, {0.0f, -100.0f, 0.0f}},
};
CLOTH_AT_SET adaHairAt[6] = {
    {0x0000, 0x04, 0x04, 1.0f, 65.0f, {0.0f, 50.0f, -10.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x03, 0x04, 0.5f, 70.0f, {0.0f, 50.0f, 0.0f}, {0.0f, 50.0f, 0.0f}},
    {0x0000, 0x03, 0x03, 1.0f, 60.0f, {0.0f, 30.0f, 0.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x04, 0x04, 1.0f, 70.0f, {-5.0f, 100.0f, 30.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x04, 0x04, 1.0f, 70.0f, {-3.0f, 70.0f, 30.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x04, 0x04, 1.0f, 70.0f, {0.0f, 50.0f, 30.0f}, {0.0f, 0.0f, 0.0f}},
};
CLOTH_AT_SET adaRibbonAt[10] = {
    {0x0000, 0x04, 0x04, 1.0f, 90.0f, {0.0f, 0.0f, 20.0f}, {0.0f, 0.0f, 20.0f}},
    {0x0000, 0x03, 0x03, 1.0f, 70.0f, {0.0f, 0.0f, 20.0f}, {0.0f, 0.0f, 20.0f}},
    {0x0000, 0x03, 0x02, 0.666f, 130.0f, {0.0f, 0.0f, 30.0f}, {0.0f, 0.0f, 30.0f}},
    {0x0000, 0x03, 0x02, 0.333f, 130.0f, {0.0f, 0.0f, 0.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x02, 0x02, 1.0f, 130.0f, {0.0f, 0.0f, 0.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x02, 0x01, 0.666f, 130.0f, {0.0f, 0.0f, 0.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x02, 0x01, 0.333f, 130.0f, {0.0f, 0.0f, 0.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x01, 0x01, 1.0f, 130.0f, {0.0f, 0.0f, 0.0f}, {0.0f, 0.0f, 0.0f}},
    {0x0000, 0x06, 0x06, 1.0f, 130.0f, {0.0f, 0.0f, 30.0f}, {0.0f, 0.0f, 30.0f}},
    {0x0000, 0x0C, 0x0C, 1.0f, 130.0f, {0.0f, 0.0f, 30.0f}, {0.0f, 0.0f, 30.0f}},
};

// ---- the garments ----
struct Garment {
    u8 num, at_num, at_num_evt, bundle, bundle_evt;
    u8 *p, *lp, *rp, *ulp, *up, *dp;
    f32 *max, *max_evt, *wind_s, *wind_r;
    CLOTH_AT_SET *at, *at_evt;
    f32 gravity, rate, stretchy, move_rate;
    u32 flag;
};
enum { LEON_HAIR, LEON_JACKET, LEON_HOLSTER, GIRL_HAIR, GIRL_SKIRT, GIRL_SWEATER, GIRL_RIBBON, LUIS_HAIR, ADA_DRESS, ADA_HAIR,
       ADA_RIBBON };
const Garment kGarments[] = {
    // num at  evt bnd evt  p             lp             rp             ulp          up             dp
    {21, 4, 4, 4, 4, leonHairP, 0, 0, 0, leonHairUp, leonHairDp,
     leonHairMax, leonHairMax, leonHairWindS, leonHairWindR, leonHairAt, leonHairAt, 15.0f, 0.75f, 1.0f, 0.5f, 0x302},
    {24, 6, 6, 4, 4, leonJacketP, leonJacketLp, leonJacketRp, 0, leonJacketUp, leonJacketDp,
     leonJacketMax, leonJacketMax, leonJacketWindS, leonJacketWindR, leonJacketAt, leonJacketAt, 25.0f, 0.5f, 0.1f, 0.5f, 0x100},
    {2, 1, 1, 4, 4, leonHolsterP, leonHolsterLp, leonHolsterRp, 0, leonHolsterUp, leonHolsterDp,
     leonHolsterMax, leonHolsterMax, leonHolsterWindS, leonHolsterWindR, leonHolsterAt, leonHolsterAt, 25.0f, 0.7f, 1.0f, 0.5f, 0x100},
    {21, 5, 7, 4, 4, girlHairP, 0, 0, 0, girlHairUp, girlHairDp,
     girlHairMax, girlHairMaxEvt, girlHairWindS, girlHairWindR, girlHairAt, girlHairAtEvt, 15.0f, 0.75f, 1.0f, 0.5f, 0x302},
    {48, 11, 11, 4, 4, girlSkirtP, girlSkirtLp, 0, 0, girlSkirtUp, girlSkirtDp,
     girlSkirtMax, girlSkirtMax, girlSkirtWindS, girlSkirtWindR, girlSkirtAt, girlSkirtAtEvt, 10.0f, 0.9f, 1.0f, 0.5f, 0x100},
    {8, 6, 6, 4, 4, girlSweaterP, girlSweaterLp, 0, 0, girlSweaterUp, girlSweaterDp,
     girlSweaterMax, girlSweaterMax, girlSweaterWindS, girlSweaterWindR, girlSweaterAt, girlSweaterAt, 10.0f, 0.7f, 0.1f, 0.5f, 0x100},
    {12, 8, 8, 4, 4, girlRibbonP, 0, 0, 0, girlRibbonUp, girlRibbonDp,
     girlRibbonMax, girlRibbonMax, girlRibbonWindS, girlRibbonWindR, girlRibbonAt, girlRibbonAt, 10.0f, 0.7f, 0.1f, 0.5f, 0x100},
    {26, 7, 7, 4, 4, luisHairP, 0, 0, 0, luisHairUp, luisHairDp,
     luisHairMax, luisHairMax, luisHairWindS, luisHairWindR, luisHairAt, luisHairAt, 15.0f, 0.75f, 1.0f, 0.5f, 0x302},
    {146, 35, 35, 10, 2, adaDressP, adaDressLp, 0, adaDressULp, adaDressUp, adaDressDp,
     adaDressMax, adaDressMax, adaDressWindS, adaDressWindR, adaDressAt, adaDressAt, 20.0f, 0.7f, 1.0f, 0.7f, 0x000},
    {14, 6, 6, 4, 4, adaHairP, 0, 0, 0, adaHairUp, adaHairDp,
     adaHairMax, adaHairMax, adaHairWindS, adaHairWindR, adaHairAt, adaHairAt, 15.0f, 0.75f, 1.0f, 0.5f, 0x302},
    {22, 10, 10, 0, 0, adaRibbonP, 0, 0, 0, adaRibbonUp, adaRibbonDp,
     adaRibbonMax, adaRibbonMax, adaRibbonWindS, adaRibbonWindR, adaRibbonAt, adaRibbonAt, 10.0f, 0.8f, 1.0f, 0.5f, 0x200},
};

// The chain work of one garment from its row (every field written: the work may hold another garment's chain).
void fill(PlCloth* c, const Garment& g, int evt)
{
    c->Num = g.num;
    c->pCloth = g.p;
    c->pLeft = g.lp;
    c->pRight = g.rp;
    c->pUpLeft = g.ulp;
    c->pUpRight = 0;
    c->pParent = g.up;
    c->pChild = g.dp;
    c->pGravity = 0;
    c->pRate = 0;
    c->pMax = evt ? g.max_evt : g.max;
    c->pWindSin = g.wind_s;
    c->pWindRate = g.wind_r;
    c->pAtset = evt ? g.at_evt : g.at;
    c->At_num = evt ? g.at_num_evt : g.at_num;
    c->Gravity = g.gravity;
    c->Rate = g.rate;
    c->Bundle_num = evt ? g.bundle_evt : g.bundle;
    c->WindSin = 0.0f;
    c->Stretchy = g.stretchy;
    c->Move_rate = g.move_rate;
    c->pPtbl = 0;
    c->pModel = 0;
    c->Flag = g.flag;
}
void set(cModel* pl, PlCloth* c, int which, int evt = 0)
{
    fill(c, kGarments[which], evt);
    garment_cnt.sets++;
    PenClothSet(pl, (PenCloth*) c, 100.0f);
}
inline void step(cModel* pl, PlCloth* c)
{
    garment_cnt.moves++;
    PenClothMove(pl, (PenCloth*) c);
}
inline void step3(cModel* pl, PlCloth* c)
{
    garment_cnt.moves++;
    PenClothMove3(pl, (PenCloth*) c);
}
// the warp / no-cloth flags that reset the chains this tick, cleared once the garments have stepped
inline void clear_reset(cModel* pl) { pl->be_flag &= ~0x00E00000; }

}   // namespace

// ---- Leon: jacket (costume 0) or holster strap (costume 1), and hair. The callers hand in (leonHair, leonJacket,
// leonHolster); the works are used as jacket, holster and hair. ----
void PlClothSetLeon(cModel* pl, PlCloth* jacket, PlCloth* holster, PlCloth* hair)
{
    if (pG->pl_costume == 0) set(pl, jacket, LEON_JACKET);
    else garment_cnt.skipped++;
    if (pG->pl_costume == 1) set(pl, holster, LEON_HOLSTER);
    else garment_cnt.skipped++;
    set(pl, hair, LEON_HAIR);
}
void PlClothMoveLeon(cModel* pl, PlCloth* jacket, PlCloth* holster, PlCloth* hair)
{
    if (pG->pl_costume == 0) step3(pl, jacket);
    if (pG->pl_costume == 1) step3(pl, holster);
    if (!(garment_control == 1 && (pG->Frame_cnt & 1))) step(pl, hair);   // control "garmenthair"
    clear_reset(pl);
}

// ---- Ashley: hair, then skirt and sweater, or (costume 1) ribbon and lapels. The callers hand in (girlHair, girlSkirt,
// girlSweater); the works are used as skirt, hair and sweater (or ribbon). ----
void PlClothSetGirl(cModel* pl, PlCloth* skirt, PlCloth* hair, PlCloth* sweater, int evt)
{
    set(pl, hair, GIRL_HAIR, evt);
    if (pG->game_costume == 1) {
        set(pl, sweater, GIRL_RIBBON);
    } else {
        set(pl, skirt, GIRL_SKIRT, evt);
        set(pl, sweater, GIRL_SWEATER);
    }
}
void PlClothMoveGirl(cModel* pl, PlCloth* skirt, PlCloth* hair, PlCloth* sweater)
{
    step(pl, hair);
    if (pG->game_costume == 1) {
        step(pl, sweater);
        girlLapelMove(pl);
    } else {
        // the skirt is stiffer while she is carried or on a ladder (Status_flg[1] 0x200000)
        skirt->Move_rate = (pG->Status_flg[1] & 0x200000) || garment_control == 2 ? 0.9f : 0.5f;
        step3(pl, skirt);
        step(pl, sweater);
    }
    clear_reset(pl);
}

// ---- Luis: hair ----
void PlClothSetLuis(cModel* pl, PlCloth* hair) { set(pl, hair, LUIS_HAIR); }
void PlClothMoveLuis(cModel* pl, PlCloth* hair)
{
    step(pl, hair);
    clear_reset(pl);
}

// ---- Ada: dress (fewer constraint passes in events) and hair; the ribbon is a chain object of its own ----
void PlClothSetAda(cModel* pl, PlCloth* ribbon, PlCloth* dress, PlCloth* hair, int evt)
{
    set(pl, dress, ADA_DRESS, evt);
    set(pl, hair, ADA_HAIR);
}
void PlClothMoveAda(cModel* pl, PlCloth* ribbon, PlCloth* dress, PlCloth* hair)
{
    step3(pl, dress);
    step(pl, hair);
    clear_reset(pl);
}
// Ada's dress ribbon: a chain object (its own model) hung on the player's part 0x40; 0 when the model is missing.
cObjChain* AdaRibbonSet(cModel* pl, PlCloth* c, void* bin, void* tpl)
{
    if (!bin || !tpl) return 0;
    fill(c, kGarments[ADA_RIBBON], 0);
    c->pModel = pl;
    Vec pos = {0.0f, 0.0f, 0.0f}, rot = {0.0f, 0.0f, 0.0f};
    cObjChain* chain = SetChain(bin, tpl, &pos, &rot);
    chain->setChain((PenCloth*) c);
    chain->setParent(pl, 0x40, &pos, 0);
    return chain;
}

// ---- Ashley's alternate-costume lapels (parts 0x8D, 0x8E) ----
// Each lapel is first placed at its rest pose under its parent; the chest point (a weighted mix of two chest parts) is
// taken into the lapel's frame (turned by the costume's fixed tilt, rotm); the lapel is lifted away from the body by
// the angle that point rises above it, then bent about the frame's Y and Z axes by fixed shares of that angle (the
// left lapel the opposite way).
namespace {
const f32 kLapelLift[2] = {50.0f, 50.0f};   // added to the chest point's height in the lapel frame (right, left)
const f32 kLapelRateY = 0.3f, kLapelRateZ = 0.6f, kLapelWeight = 0.32f;
inline f32 lapel_rate_x() { return garment_control == 3 ? 1.4f : 1.3f; }   // control "lapelrate"
void lapel(cModel* pl, int no, int pa, int pb, f32 lift, f32 sign, Mtx rotm)
{
    Mtx frame, inv, turn;
    Vec v, axis;
    cModel* p = pl->getPartsPtr(no);
    PSMTXIdentity(p->l_mat);
    TransMatrix(p->l_mat, &p->pos);
    PSMTXConcat(p->pParent->mat, p->l_mat, p->mat);
    p->world.x = p->mat[0][3];
    p->world.y = p->mat[1][3];
    p->world.z = p->mat[2][3];
    PSMTXConcat(p->mat, rotm, frame);
    PSMTXInverse(frame, inv);
    cModel* a = pl->getPartsPtr(pa);
    cModel* b = pl->getPartsPtr(pb);
    PosToPos(&a->world, &b->world, &v, kLapelWeight);
    PSMTXMultVec(inv, &v, &v);
    v.y += lift;
    const f32 ang = v.y > 0.0f ? asinf(v.y / sqrtf(v.x * v.x + v.y * v.y + v.z * v.z)) : 0.0f;
    const f32 rx = -ang * lapel_rate_x();
    const f32 ry = (sign * ang) * kLapelRateY;   // sign is +-1: the negation is exact
    const f32 rz = (sign * ang) * kLapelRateZ;
    PSMTXRotRad(p->l_mat, 'x', rx);
    TransMatrix(p->l_mat, &p->pos);
    PSMTXConcat(p->pParent->mat, p->l_mat, p->mat);
    PSMTXConcat(p->mat, rotm, frame);
    axis.x = 0.0f, axis.y = 1.0f, axis.z = 0.0f;
    PSMTXMultVecSR(frame, &axis, &axis);
    PSMTXRotAxisRad(turn, &axis, ry);
    PSMTXConcat(turn, p->mat, p->mat);
    TransMatrix(p->mat, &p->world);
    PSMTXConcat(p->mat, rotm, frame);
    axis.x = 0.0f, axis.y = 0.0f, axis.z = 1.0f;
    PSMTXMultVecSR(frame, &axis, &axis);
    PSMTXRotAxisRad(turn, &axis, rz);
    PSMTXConcat(turn, p->mat, p->mat);
    TransMatrix(p->mat, &p->world);
}
}   // namespace
void girlLapelMove(cModel* pl)
{
    Mtx rotm;
    garment_cnt.lapels++;
    PSMTXRotRad(rotm, 'x', 0.75049156f);
    pl->getPartsPtr(4);   // the chest part is asked for first, as the original (the skeleton serves the parts it hands out)
    lapel(pl, 0x8D, 7, 8, kLapelLift[0], -1.0f, rotm);
    lapel(pl, 0x8E, 0xD, 0xE, kLapelLift[1], 1.0f, rotm);
}
