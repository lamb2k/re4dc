// Included once in native_ui.cpp before its private renderer namespace.
#include "cloth_publication11.hpp"
extern "C" {
re4dc::cloth_pub11::Collector re4dc_cloth_publication11;
unsigned re4dc_cloth_snapshot11(unsigned id,unsigned expected,re4dc::cloth_pub11::Receipt* out){
    return re4dc_cloth_publication11.snapshot(id,expected,out);
}
}
