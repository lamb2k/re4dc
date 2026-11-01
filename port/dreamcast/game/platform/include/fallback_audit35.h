#ifndef RE4DC_FALLBACK_AUDIT35_H
#define RE4DC_FALLBACK_AUDIT35_H

// Include only from an independent FALLBACK_AUDIT35 block. Appended reasons
// share FA29's IRQ-safe lifecycle and immutable QA snapshot; no second writer.
#include "fallback_audit29.h"
namespace re4dc { namespace fa35 {
enum Reason {
#define FA35_REASON(symbol, label, unit) symbol=::re4dc::fa29::symbol,
#include "fallback_audit35.def"
#undef FA35_REASON
};
inline void hit(Reason reason, uint32_t amount=1) {
    ::re4dc::fa29::hit(static_cast<::re4dc::fa29::Reason>(reason),amount);
}
} }
#endif
