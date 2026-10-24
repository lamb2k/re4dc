#pragma once
using matrix_t=float[4][4];
static void mat_load(const matrix_t* m){std::memcpy(vp_host_xmtrx,*m,sizeof(matrix_t));}
static void mat_trans_nodiv(float& x,float& y,float& z,float& w){VP_FTRV(x,y,z,w);}
