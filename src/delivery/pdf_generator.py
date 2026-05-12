"""Converts newsletter Markdown to styled PDF."""
from __future__ import annotations

from pathlib import Path

import markdown
from weasyprint import HTML


TEMPLATE_DIR = Path(__file__).parent.parent.parent / "templates"


def markdown_to_pdf(newsletter_md: str, output_path: str) -> Path:
    """Convert newsletter Markdown to a styled PDF."""
    css_path = TEMPLATE_DIR / "newsletter.css"
    css_content = css_path.read_text(encoding="utf-8") if css_path.exists() else ""

    # Convert Markdown to HTML
    html_body = markdown.markdown(
        newsletter_md,
        extensions=["tables", "fenced_code", "nl2br"],
    )

    full_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <style>{css_content}</style>
</head>
<body>
{html_body}
</body>
</html>"""

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    HTML(string=full_html).write_pdf(str(output))
    print(f"[pdf] Generated PDF: {output} ({output.stat().st_size / 1024:.1f} KB)")
    return output
