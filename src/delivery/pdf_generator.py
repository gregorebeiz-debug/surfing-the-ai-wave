"""Converts newsletter Markdown to styled PDF.

Primary: WeasyPrint (requires GLib/Pango — available on Linux/CCR).
Fallback: ReportLab (pure Python, works everywhere).
"""
from __future__ import annotations

import re
from pathlib import Path


TEMPLATE_DIR = Path(__file__).parent.parent.parent / "templates"

# ─── Color Palette (Claude-inspired + wave blues) ────────────
COLORS = {
    "title": "#1e3a5f",         # Deep navy for main title
    "h2_bg": "#1e3a5f",         # Dark navy background for section headers
    "h2_text": "#ffffff",       # White text on section headers
    "h3_text": "#1e3a5f",       # Navy for item headers
    "h3_bg": "#f0f7ff",         # Light blue background for item cards
    "h3_border": "#2563eb",     # Blue left border for cards
    "body": "#1e293b",          # Dark slate for body text
    "italic": "#475569",        # Medium gray for italic/sources
    "accent": "#d4956a",        # Warm Claude-orange accent
    "link": "#2563eb",          # Blue for links
    "hr": "#93c5fd",            # Light blue for separators
    "wave_bar": "#2563eb",      # Blue bar at top
    "bullet_dot": "#2563eb",    # Blue bullet dots
    "footer": "#94a3b8",        # Muted gray for footer
    "buyer_beware_bg": "#fef2f2",  # Light red for warnings
    "buyer_beware_border": "#ef4444",
}


def _pdf_with_weasyprint(html: str, output: Path) -> None:
    from weasyprint import HTML
    HTML(string=html).write_pdf(str(output))


def _pdf_with_reportlab(newsletter_md: str, output: Path) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, HRFlowable,
        Table, TableStyle, KeepTogether,
    )

    C = {k: colors.HexColor(v) for k, v in COLORS.items()}

    doc = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        leftMargin=2.2 * cm,
        rightMargin=2.2 * cm,
        topMargin=2.0 * cm,
        bottomMargin=2.5 * cm,
    )

    # ─── Styles ──────────────────────────────────────────
    s = {
        "h1": ParagraphStyle(
            "h1", fontSize=24, leading=28, fontName="Helvetica-Bold",
            textColor=C["title"], spaceAfter=2, spaceBefore=0,
        ),
        "h2": ParagraphStyle(
            "h2", fontSize=13, leading=16, fontName="Helvetica-Bold",
            textColor=C["h2_text"], spaceBefore=16, spaceAfter=8,
        ),
        "h3": ParagraphStyle(
            "h3", fontSize=11, leading=14, fontName="Helvetica-Bold",
            textColor=C["h3_text"], spaceBefore=12, spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "body", fontSize=9.5, leading=14.5, fontName="Helvetica",
            textColor=C["body"], spaceAfter=5,
        ),
        "italic": ParagraphStyle(
            "italic", fontSize=9.5, leading=14, fontName="Helvetica-Oblique",
            textColor=C["italic"], spaceAfter=6,
        ),
        "intro": ParagraphStyle(
            "intro", fontSize=9.5, leading=14, fontName="Helvetica-Oblique",
            textColor=C["italic"], spaceAfter=10,
            leftIndent=12, borderPadding=(6, 8, 6, 8),
        ),
        "bullet": ParagraphStyle(
            "bullet", fontSize=9.5, leading=13.5, fontName="Helvetica",
            textColor=C["body"], leftIndent=16, spaceAfter=4,
            bulletIndent=4,
        ),
        "footer": ParagraphStyle(
            "footer", fontSize=8, leading=10, fontName="Helvetica-Oblique",
            textColor=C["footer"], alignment=TA_CENTER, spaceBefore=16,
        ),
    }

    story = []

    # ─── Wave bar at top ─────────────────────────────────
    wave_bar = Table(
        [[""]],
        colWidths=[doc.width],
        rowHeights=[4],
    )
    wave_bar.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C["wave_bar"]),
        ("LINEBELOW", (0, 0), (-1, -1), 0, colors.white),
    ]))
    story.append(wave_bar)
    story.append(Spacer(1, 12))

    lines = newsletter_md.splitlines()
    is_first_italic = True  # Track if we're on the editorial intro
    in_buyer_beware = False

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            story.append(Spacer(1, 3))
            continue

        # ─── H1: Title ───────────────────────────────────
        if stripped.startswith("# "):
            text = _md_inline(stripped[2:])
            story.append(Paragraph(text, s["h1"]))

            # Add accent underline after title
            accent_line = HRFlowable(
                width="40%", thickness=3, color=C["accent"],
                spaceAfter=4, spaceBefore=2,
            )
            story.append(accent_line)

        # ─── H2: Section header with dark background ─────
        elif stripped.startswith("## "):
            text = _md_inline(stripped[3:])
            in_buyer_beware = "buyer beware" in stripped.lower() or "beware" in stripped.lower()

            # Section header as table with background
            header_table = Table(
                [[Paragraph(text, s["h2"])]],
                colWidths=[doc.width],
            )
            bg = C["buyer_beware_border"] if in_buyer_beware else C["h2_bg"]
            header_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), bg),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("ROUNDEDCORNERS", [4, 4, 4, 4]),
            ]))
            story.append(Spacer(1, 10))
            story.append(header_table)
            story.append(Spacer(1, 6))
            is_first_italic = False

        # ─── H3: Item card with left border ──────────────
        elif stripped.startswith("### "):
            text = _md_inline(stripped[4:])
            card = Table(
                [[Paragraph(text, s["h3"])]],
                colWidths=[doc.width],
            )
            card.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), C["h3_bg"]),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("LINEBEFORECOL", (0, 0), (0, -1), 3, C["h3_border"]),
            ]))
            story.append(card)

        # ─── Horizontal rule ─────────────────────────────
        elif stripped.startswith("---"):
            story.append(Spacer(1, 6))
            story.append(HRFlowable(
                width="100%", thickness=2, color=C["hr"],
                spaceAfter=6, spaceBefore=2,
            ))

        # ─── Bullets ─────────────────────────────────────
        elif stripped.startswith("- ") or stripped.startswith("* ") or stripped.startswith("• "):
            bullet_text = stripped[2:] if stripped[0] in "-*" else stripped[2:]
            text = _md_inline(bullet_text)
            story.append(Paragraph(
                f'<font color="{COLORS["bullet_dot"]}">●</font>  {text}',
                s["bullet"],
            ))

        # ─── Italic paragraphs (editorial intro, sources) ─
        elif stripped.startswith("*") and stripped.endswith("*") and not stripped.startswith("**"):
            text = _md_inline(stripped[1:-1])
            if is_first_italic:
                # Wrap editorial intro in accent-bordered box
                intro_table = Table(
                    [[Paragraph(f"<i>{text}</i>", s["intro"])]],
                    colWidths=[doc.width],
                )
                intro_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fdf8f4")),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 14),
                    ("LINEBEFORECOL", (0, 0), (0, -1), 3, C["accent"]),
                ]))
                story.append(intro_table)
                story.append(Spacer(1, 8))
                is_first_italic = False
            else:
                story.append(Paragraph(f"<i>{text}</i>", s["italic"]))

        # ─── Table rows ──────────────────────────────────
        elif stripped.startswith("|"):
            cells = [c.strip() for c in stripped.split("|") if c.strip() and not set(c.strip()) <= set("-: ")]
            if cells:
                text = "  |  ".join(_md_inline(c) for c in cells)
                story.append(Paragraph(text, s["bullet"]))

        # ─── Regular paragraphs ──────────────────────────
        else:
            text = _md_inline(stripped)

            # Check if this is the footer stats line
            if i >= len(lines) - 3 and ("items analizados" in stripped or "Fuentes:" in stripped):
                story.append(Spacer(1, 8))
                story.append(HRFlowable(
                    width="60%", thickness=1, color=C["hr"],
                    spaceAfter=6,
                ))
                story.append(Paragraph(f"<i>{text}</i>", s["footer"]))
            elif in_buyer_beware:
                # Buyer beware content with warning styling
                warn_table = Table(
                    [[Paragraph(text, s["body"])]],
                    colWidths=[doc.width],
                )
                warn_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fef2f2")),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("LINEBEFORECOL", (0, 0), (0, -1), 3, C["buyer_beware_border"]),
                ]))
                story.append(warn_table)
            else:
                story.append(Paragraph(text, s["body"]))

    # ─── Wave bar at bottom ──────────────────────────────
    story.append(Spacer(1, 12))
    wave_bar_bottom = Table(
        [[""]],
        colWidths=[doc.width],
        rowHeights=[3],
    )
    wave_bar_bottom.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C["accent"]),
    ]))
    story.append(wave_bar_bottom)

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
    text = re.sub(r"`(.*?)`", r'<font name="Courier" color="#334155">\1</font>', text)
    # Links: [text](url) — show as colored text
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        rf'<a href="\2"><font color="{COLORS["link"]}">\1</font></a>',
        text,
    )
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
