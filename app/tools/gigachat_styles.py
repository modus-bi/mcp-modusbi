"""Readable BI adaptations; styles never alter source bindings or data colors."""
STYLES={
    "corporate_clean":{"name":"Современный корпоративный / SaaS","catalog_number":5,"background":"#F2F5F8","surface":"#FFFFFF","text":"#20313F","muted":"#526474","accent":"#245F8A","border":"#D7E0E8","radius":8,"title_font":"GolosUIWebRegular,Arial,sans-serif"},
    "clean_minimalism":{"name":"Чистый минимализм","catalog_number":1,"background":"#FAFAF8","surface":"#FFFFFF","text":"#232620","muted":"#5A6259","accent":"#AD4D0B","border":"#E1E3DC","radius":2,"title_font":"GolosUIWebRegular,Arial,sans-serif"},
    "swiss":{"name":"Швейцарский стиль","catalog_number":3,"background":"#F4F4F2","surface":"#FFFFFF","text":"#1C1C1C","muted":"#555555","accent":"#B42318","border":"#D6D6D2","radius":0,"title_font":"Arial,sans-serif"},
    "warm_minimalism":{"name":"Тёплый минимализм","catalog_number":2,"background":"#F3F0E8","surface":"#FFFEFA","text":"#34382C","muted":"#62664F","accent":"#656A3A","border":"#DDDCCB","radius":10,"title_font":"Georgia,serif"},
}


def style_css(style, panel_ids):
    if style not in STYLES:raise ValueError("Unknown report style; read giga_list_report_styles")
    t=STYLES[style];css=[]
    for idx in panel_ids:
        s=f"#panel_{idx}"
        css += [f".hsGridLayout:has(>{s}){{background:{t['background']};}}",
            f"{s}{{background:{t['surface']}!important;color:{t['text']};border:1px solid {t['border']}!important;border-radius:{t['radius']}px!important;box-shadow:none;}}",
            f"{s} .hsChartContainer{{background-color:{t['surface']}!important;}}",
            f"{s} .componentHeader{{font-family:{t['title_font']};font-size:17px;line-height:1.35;color:{t['text']}!important;background:{t['surface']}!important;padding:10px 14px;border-bottom:2px solid {t['accent']}!important;position:relative;z-index:5;flex-shrink:0;}}",
            f"{s} .HsTilemapChart .tile-label{{transform:translate(6.5px,14px);font-weight:500;}}",
            f"{s} h1,{s} h2,{s} h3{{font-family:{t['title_font']};color:{t['text']};}}",
            f"{s} .hsTextBlock p{{color:{t['muted']};}}",
            f"{s} .r-ss-input,{s} .r-ss-dropdown{{background:#fff;color:{t['text']};}}",
            f"{s} .r-ss-dropdown{{border:1px solid {t['accent']};box-shadow:0 4px 12px #00000018;}}"]
    return "\n".join(css)
