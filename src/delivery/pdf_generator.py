"""Converts newsletter Markdown to styled PDF.

Primary: WeasyPrint (requires GLib/Pango — available on Linux/CCR).
Fallback: ReportLab (pure Python, works everywhere).
"""
from __future__ import annotations

import re
from pathlib import Path


TEMPLATE_DIR = Path(__file__).parent.parent.parent / "templates"


def _pdf_with_weasyprint(html: str, output: Path) -> None:
    from weasyprint import HTML
    HTML(string=html).write_pdf(str(output))


def _pdf_with_reportlab(newsletter_md: str, output: Path) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, HRFlowable, ListFlowable, ListItem
    )

    doc = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        leftMargin=2.5*cm,
        rightMargin=2.5*cm,
        topMargin=2.5*cm,
        bottomMargin=2.5*cm,
    )

    base = getSampleStyleSheet()

    styles = {
        "h1": ParagraphStyle("h1", parent=base["Heading1"], fontSize=20, textColor=colors.HexColor("#CC785C"), spaceAfter=6),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontSize=14, textColor=colors.HexColor("#CC785C"), spaceBefore=14, spaceAfter=4),
        "h3": ParagraphStyle("h3", parent=base["Heading3"], fontSize=11, textColor=colors.HexColor("#333333"), spaceBefore=10, spaceAfter=3),
        "body": ParagraphStyle("body", parent=base["Normal"], fontSize=9, leading=14, spaceAfter=6),
        "italic": ParagraphStyle("italic", parent=base["Normal"], fontSize=9, leading=14, textColor=colors.HexColor("#666666"), spaceAfter=8),
        "bullet": ParagraphStyle("bullet", parent=base["Normal"], fontSize=9, leading=13, leftIndent=12),
    }

    story = []

    for line in newsletter_md.splitlines():
        stripped = line.strip()
        if not stripped:
            story.append(Spacer(1, 4))
            continue

        if stripped.startswith("# "):
            text = _md_inline(stripped[2:])
            story.append(Paragraph(text, styles["h1"]))
        elif stripped.startswith("## "):
            text = _md_inline(stripped[3:])
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#DDDDDD")))
            story.append(Paragraph(text, styles["h2"]))
        elif stripped.startswith("### "):
            text = _md_inline(stripped[4:])
            story.append(Paragraph(text, styles["h3"]))
        elif stripped.startswith("---"):
            story.append(Spacer(1, 4))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#DDDDDD")))
            story.append(Spacer(1, 4))
        elif stripped.startswith("- ") or stripped.startswith("* "):
            text = _md_inline(stripped[2:])
            story.append(Paragraph(f"• {text}", styles["bullet"]))
        elif stripped.startswith("*") and stripped.endswith("*") and not stripped.startswith("**"):
            text = _md_inline(stripped[1:-1])
            story.append(Paragraph(f"<i>{text}</i>", styles["italic"]))
        elif stripped.startswith("|"):
            # Simple table row — render as monospace paragraph
            cells = [c.strip() for c in stripped.split("|") if c.strip() and not set(c.strip()) <= set("-: ")]
            if cells:
                text = "  |  ".join(_md_inline(c) for c in cells)
                story.append(Paragraph(text, styles["bullet"]))
        else:
            text = _md_inline(stripped)
            story.append(Paragraph(text, styles["body"]))

    doc.build(story)


def _md_inline(text: str) -> str:
    """Convert inline Markdown (bold, italic, links, backticks) to ReportLab XML."""
    # Escape XML special chars first
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Bold+italic: ***text***
    text = re.sub(r"\*\*\*(.*?)\*\*\*", r"<b><i>\1</i></b>", text)
    # Bold: **text**
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
    # Italic: *text*
    text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", text)
    # Inline code: `text`
    text = re.sub(r"`(.*?)`", r"<font name='Courier'>\1</font>", text)
    # Links: [text](url) — show text only
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
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
