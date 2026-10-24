
// Evidence-only layout exports appended after the complete production TU.
// No production body or type is substituted here.
extern "C" {
re4dc::texture::Header ui_fixture_header;
re4dc::texture::Texture ui_fixture_texture;
float re4dc_ui_sx=1.0f,re4dc_ui_sy=1.0f;
void ui_fixture_draw(unsigned i) { ui_draw_quad(i); }
extern const std::uintptr_t ui_fixture_layout[] = {
    1,sizeof(Entry),sizeof(re4dc::texture::Package),sizeof(Re4dcUiQuad),sizeof(GlyphQuad),
    reinterpret_cast<std::uintptr_t>(entries),reinterpret_cast<std::uintptr_t>(quads),
    reinterpret_cast<std::uintptr_t>(handles),reinterpret_cast<std::uintptr_t>(&drawn),
    reinterpret_cast<std::uintptr_t>(&ui_fixture_header),reinterpret_cast<std::uintptr_t>(&ui_fixture_texture),
    offsetof(Entry,ui_header),offsetof(Entry,ui_header_key),
    reinterpret_cast<std::uintptr_t>(glyph_cells),reinterpret_cast<std::uintptr_t>(glyph_quads),
    reinterpret_cast<std::uintptr_t>(&nglyph),reinterpret_cast<std::uintptr_t>(glyph_headers),
    reinterpret_cast<std::uintptr_t>(glyph_header_ready),reinterpret_cast<std::uintptr_t>(&glyph_drawn),
    reinterpret_cast<std::uintptr_t>(&world_autosort),reinterpret_cast<std::uintptr_t>(&overlay_layer),
    reinterpret_cast<std::uintptr_t>(&re4dc_ui_sx),reinterpret_cast<std::uintptr_t>(&re4dc_ui_sy)
};
}
