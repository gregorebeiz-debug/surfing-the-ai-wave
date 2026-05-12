"""Converts newsletter Markdown to styled PDF.

Primary: WeasyPrint (requires GLib/Pango — available on Linux/CCR).
Fallback: ReportLab (pure Python, works everywhere).
"""
from __future__ import annotations

import re
from pathlib import Path


TEMPLATE_DIR = Path(__file__).parent.parent.parent / "templates"

# ─── Color Palette (Claude-inspired ocean blues + warm accent) ────
COLORS = {
    "title": "#0f2b46",           # Darkest navy for main title
    "subtitle": "#64748b",        # Slate for date line
    "h2_bg": "#0f2b46",           # Dark navy section headers
    "h2_text": "#ffffff",         # White text on headers
    "h3_text": "#0f2b46",         # Navy for item titles
    "h3_bg": "#f0f6ff",           # Lightest blue for item cards
    "h3_border": "#3b82f6",       # Bright blue left border
    "body": "#1e293b",            # Dark slate body text
    "italic": "#64748b",          # Slate for sources/italic
    "accent": "#d4956a",          # Warm Claude-orange accent
    "link": "#2563eb",            # Blue for links
    "hr": "#bfdbfe",              # Very light blue separators
    "wave_top": "#1e40af",        # Deep blue wave bar
    "wave_bottom": "#d4956a",     # Warm accent bottom bar
    "bullet_dot": "#3b82f6",      # Bright blue bullet dots
    "footer": "#94a3b8",          # Muted gray for footer
    "intro_bg": "#fdf8f4",        # Cream for editorial intro
    "intro_border": "#d4956a",    # Warm accent for intro border
    "card_bg": "#f8fafc",         # Very subtle gray for content cards
    "deep_dive_bg": "#fefce8",    # Warm yellow tint for deep dives
    "deep_dive_border": "#d4956a",# Warm accent for deep dive border
    "tool_bg": "#f0fdf4",         # Light green for tool watch
    "tool_border": "#22c55e",     # Green border for tools
    "community_bg": "#faf5ff",    # Light purple for community pulse
    "community_border": "#a855f7",# Purple for community
    "signal_bg": "#f8fafc",       # Subtle gray for signal board
    "buyer_beware_bg": "#fef2f2", # Light red for warnings
    "buyer_beware_border": "#ef4444",
    "wave_label": "#93c5fd",      # Light blue for wave emoji/label
}


def _pdf_with_weasyprint(html: str, output: Path) -> None:
    from weasyprint import HTML
    HTML(string=html).write_pdf(str(output))


def _pdf_with_reportlab(newsletter_md: str, output: Path) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, HRFlowable,
        Table, TableStyle, KeepTogether,
    )

    C = {k: colors.HexColor(v) for k, v in COLORS.items()}

    doc = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        leftMargin=2.0 * cm,
        rightMargin=2.0 * cm,
        topMargin=1.5 * cm,
        bottomMargin=2.0 * cm,
    )

    # ─── Styles ──────────────────────────────────────────
    s = {
        "h1": ParagraphStyle(
            "h1", fontSize=26, leading=30, fontName="Helvetica-Bold",
            textColor=C["title"], spaceAfter=0, spaceBefore=0,
        ),
        "date": ParagraphStyle(
            "date", fontSize=10, leading=12, fontName="Helvetica",
            textColor=C["subtitle"], spaceAfter=6, spaceBefore=2,
        ),
        "h2": ParagraphStyle(
            "h2", fontSize=12, leading=15, fontName="Helvetica-Bold",
            textColor=C["h2_text"], spaceBefore=0, spaceAfter=0,
        ),
        "h3": ParagraphStyle(
            "h3", fontSize=10.5, leading=13, fontName="Helvetica-Bold",
            textColor=C["h3_text"], spaceBefore=0, spaceAfter=0,
        ),
        "body": ParagraphStyle(
            "body", fontSize=9.5, leading=14, fontName="Helvetica",
            textColor=C["body"], spaceAfter=4,
        ),
        "body_card": ParagraphStyle(
            "body_card", fontSize=9.5, leading=14, fontName="Helvetica",
            textColor=C["body"], spaceAfter=3,
            leftIndent=0,
        ),
        "italic": ParagraphStyle(
            "italic", fontSize=9, leading=13, fontName="Helvetica-Oblique",
            textColor=C["italic"], spaceAfter=5,
        ),
        "intro": ParagraphStyle(
            "intro", fontSize=9.5, leading=14, fontName="Helvetica-Oblique",
            textColor=colors.HexColor("#475569"), spaceAfter=0,
        ),
        "bullet": ParagraphStyle(
            "bullet", fontSize=9, leading=13, fontName="Helvetica",
            textColor=C["body"], leftIndent=14, spaceAfter=3,
            bulletIndent=2,
        ),
        "signal_bullet": ParagraphStyle(
            "signal_bullet", fontSize=8.5, leading=12.5, fontName="Helvetica",
            textColor=C["body"], leftIndent=14, spaceAfter=2,
            bulletIndent=2,
        ),
        "footer": ParagraphStyle(
            "footer", fontSize=7.5, leading=10, fontName="Helvetica-Oblique",
            textColor=C["footer"], alignment=TA_CENTER, spaceBefore=8,
        ),
        "link_line": ParagraphStyle(
            "link_line", fontSize=9, leading=12, fontName="Helvetica-Bold",
            textColor=C["link"], spaceAfter=2, spaceBefore=4,
        ),
    }

    story = []

    # ─── Top wave bar (gradient effect with 2 bars) ─────
    wave_bar = Table(
        [[""]],
        colWidths=[doc.width],
        rowHeights=[5],
    )
    wave_bar.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C["wave_top"]),
    ]))
    story.append(wave_bar)

    thin_accent = Table(
        [[""]],
        colWidths=[doc.width],
        rowHeights=[2],
    )
    thin_accent.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C["wave_bottom"]),
    ]))
    story.append(thin_accent)
    story.append(Spacer(1, 14))

    lines = newsletter_md.splitlines()
    is_first_italic = True
    current_section = ""  # Track which section we're in
    pending_card_lines = []  # Buffer lines for card grouping

    def _flush_card():
        """Flush buffered card content."""
        nonlocal pending_card_lines
        if not pending_card_lines:
            return
        # Build card content
        elements = []
        for cl in pending_card_lines:
            elements.append(Paragraph(_md_inline(cl), s["body_card"]))

        # Determine card colors based on section
        if "deep dive" in current_section:
            bg = C["deep_dive_bg"]
            border = C["deep_dive_border"]
        elif "tool" in current_section or "repo" in current_section:
            bg = C["tool_bg"]
            border = C["tool_border"]
        elif "community" in current_section:
            bg = C["community_bg"]
            border = C["community_border"]
        elif "buyer" in current_section or "beware" in current_section:
            bg = C["buyer_beware_bg"]
            border = C["buyer_beware_border"]
        else:
            bg = C["card_bg"]
            border = C["h3_border"]

        inner = []
        for el in elements:
            inner.append([el])

        card = Table(
            inner,
            colWidths=[doc.width - 0.5 * cm],
        )
        card.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), bg),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, -1), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("LINEBEFORECOL", (0, 0), (0, -1), 3, border),
        ]))
        story.append(card)
        story.append(Spacer(1, 4))
        pending_card_lines = []

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            if pending_card_lines:
                # Empty line might end a card block
                pass
            else:
                story.append(Spacer(1, 2))
            continue

        # ─── H1: Title ───────────────────────────────────
        if stripped.startswith("# ") and not stripped.startswith("## "):
            _flush_card()
            text = _md_inline(stripped[2:])
            story.append(Paragraph(text, s["h1"]))
            # Accent underline
            story.append(Spacer(1, 2))
            accent_line = HRFlowable(
                width="35%", thickness=3, color=C["accent"],
                spaceAfter=2, spaceBefore=0,
            )
            story.append(accent_line)

        # ─── Date line (detect pattern like "Martes, 12 de mayo...")
        elif re.match(r"^(Lunes|Martes|Mi[eé]rcoles|Jueves|Viernes|S[aá]bado|Domingo)", stripped):
            _flush_card()
            story.append(Paragraph(_md_inline(stripped), s["date"]))
            story.append(Spacer(1, 4))

        # ─── H2: Section header ─────────────────────────
        elif stripped.startswith("## "):
            _flush_card()
            text = _md_inline(stripped[3:])
            section_lower = stripped.lower()
            current_section = section_lower

            # Determine header color based on section
            if "buyer" in section_lower or "beware" in section_lower:
                bg = C["buyer_beware_border"]
            elif "deep dive" in section_lower:
                bg = colors.HexColor("#92400e")  # Warm brown
            elif "tool" in section_lower or "repo" in section_lower:
                bg = colors.HexColor("#166534")  # Dark green
            elif "community" in section_lower or "pulse" in section_lower:
                bg = colors.HexColor("#581c87")  # Dark purple
            elif "signal" in section_lower:
                bg = colors.HexColor("#334155")  # Dark slate
            else:
                bg = C["h2_bg"]

            header_table = Table(
                [[Paragraph(text, s["h2"])]],
                colWidths=[doc.width],
            )
            header_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), bg),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("ROUNDEDCORNERS", [4, 4, 4, 4]),
            ]))
            story.append(Spacer(1, 12))
            story.append(header_table)
            story.append(Spacer(1, 8))
            is_first_italic = False

        # ─── H3: Item header with colored card ──────────
        elif stripped.startswith("### "):
            _flush_card()
            text = _md_inline(stripped[4:])

            # Determine card header colors
            if "deep dive" in current_section:
                bg = C["deep_dive_bg"]
                border = C["deep_dive_border"]
            elif "tool" in current_section or "repo" in current_section:
                bg = C["tool_bg"]
                border = C["tool_border"]
            elif "community" in current_section:
                bg = C["community_bg"]
                border = C["community_border"]
            else:
                bg = C["h3_bg"]
                border = C["h3_border"]

            card = Table(
                [[Paragraph(text, s["h3"])]],
                colWidths=[doc.width],
            )
            card.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), bg),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("LINEBEFORECOL", (0, 0), (0, -1), 3, border),
            ]))
            story.append(Spacer(1, 6))
            story.append(card)
            story.append(Spacer(1, 3))

        # ─── Horizontal rule ────────────────────────────
        elif stripped.startswith("---"):
            _flush_card()
            story.append(Spacer(1, 4))
            story.append(HRFlowable(
                width="100%", thickness=1.5, color=C["hr"],
                spaceAfter=4, spaceBefore=2,
            ))

        # ─── Bullets ────────────────────────────────────
        elif stripped.startswith("- ") or stripped.startswith("* ") or stripped.startswith("\u2022 "):
            _flush_card()
            bullet_text = stripped[2:] if stripped[0] in "-*" else stripped[2:]
            text = _md_inline(bullet_text)

            # Signal Board uses compact style
            if "signal" in current_section:
                story.append(Paragraph(
                    f'<font color="{COLORS["bullet_dot"]}">&#x25CF;</font>  {text}',
                    s["signal_bullet"],
                ))
            else:
                story.append(Paragraph(
                    f'<font color="{COLORS["bullet_dot"]}">&#x25CF;</font>  {text}',
                    s["bullet"],
                ))

        # ─── Italic paragraphs (editorial intro, sources)
        elif stripped.startswith("*") and stripped.endswith("*") and not stripped.startswith("**"):
            _flush_card()
            text = _md_inline(stripped[1:-1])
            if is_first_italic:
                # Editorial intro in warm accent box
                intro_table = Table(
                    [[Paragraph(f"<i>{text}</i>", s["intro"])]],
                    colWidths=[doc.width],
                )
                intro_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), C["intro_bg"]),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ("LEFTPADDING", (0, 0), (-1, -1), 14),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("LINEBEFORECOL", (0, 0), (0, -1), 3, C["intro_border"]),
                ]))
                story.append(intro_table)
                story.append(Spacer(1, 10))
                is_first_italic = False
            else:
                story.append(Paragraph(f"<i>{text}</i>", s["italic"]))

        # ─── Link lines: [Ver video](URL) on its own line
        elif stripped.startswith("[") and "](" in stripped and stripped.endswith(")"):
            _flush_card()
            text = _md_inline(stripped)
            story.append(Paragraph(f"&#x25B6;  {text}", s["link_line"]))

        # ─── Table rows ─────────────────────────────────
        elif stripped.startswith("|"):
            _flush_card()
            cells = [c.strip() for c in stripped.split("|") if c.strip() and not set(c.strip()) <= set("-: ")]
            if cells:
                text = "  |  ".join(_md_inline(c) for c in cells)
                story.append(Paragraph(text, s["bullet"]))

        # ─── Regular paragraphs ─────────────────────────
        else:
            # Footer stats line
            if i >= len(lines) - 5 and ("items analizados" in stripped or "Fuentes:" in stripped):
                _flush_card()
                text = _md_inline(stripped)
                story.append(Spacer(1, 6))
                story.append(HRFlowable(
                    width="50%", thickness=1, color=C["hr"],
                    spaceAfter=6,
                ))
                story.append(Paragraph(f"<i>{text}</i>", s["footer"]))
            else:
                text = _md_inline(stripped)
                story.append(Paragraph(text, s["body"]))

    _flush_card()

    # ─── Bottom bars (wave effect) ──────────────────────
    story.append(Spacer(1, 16))
    bottom_accent = Table(
        [[""]],
        colWidths=[doc.width],
        rowHeights=[2],
    )
    bottom_accent.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C["wave_bottom"]),
    ]))
    story.append(bottom_accent)

    bottom_bar = Table(
        [[""]],
        colWidths=[doc.width],
        rowHeights=[4],
    )
    bottom_bar.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C["wave_top"]),
    ]))
    story.append(bottom_bar)

    # Branding footer
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        '<font color="#94a3b8">Surfing the AI Wave</font>  '
        '<font color="#d4956a">|</font>  '
        '<font color="#94a3b8">Intelligence briefing for Gregorio</font>',
        s["footer"],
    ))

    doc.build(story)


def _md_inline(text: str) -> str:
    """Convert inline Markdown (bold, italic, links, backticks) to ReportLab XML."""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Bold+italic: ***text***
    text = re.sub(r"\*\*\*(.*?)\*\*\*", r"<b><i>\1</i></b>", text)
    # Bold: **text**
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
    # Italic: *text*
    text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", text)
    # Inline code: `text`
    text = re.sub(r"`(.*?)`", r'<font name="Courier" size="8" color="#334155">\1</font>', text)
    # Links: [text](url) — show as colored underlined text
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        rf'<a href="\2"><font color="{COLORS["link"]}"><u>\1</u></font></a>',
        text,
    )
    # Arrow references: → URL → make italic
    arrow = "\u2192"
    text = re.sub(arrow + r"\s+(\S+)", f'<font color="#64748b">{arrow} \\1</font>', text)
    return text


def markdown_to_pdf(newsletter_md: str, output_path: str) -> Path:
    """Convert newsletter Markdown to a styled PDF."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    # Try WeasyPrint first (full CSS support, used in CCR/Linux)
    try:
        css_path = TEMPLATE_DIR / "newsletter.css"
        css_content = css_path.read_text(encoding="utf-8") if css_path.exists() else ""
        import markdown as md_lib
        html_body = md_lib.markdown(newsletter_md, extensions=["tables", "fenced_code", "nl2br"])
        full_html = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><style>{css_content}</style></head>
<body>{html_body}</body>
</html>"""
        _pdf_with_weasyprint(full_html, output)
    except Exception:
        # Fallback: ReportLab (pure Python, no system deps)
        _pdf_with_reportlab(newsletter_md, output)

    print(f"[pdf] Generated PDF: {output} ({output.stat().st_size / 1024:.1f} KB)")
    return output
