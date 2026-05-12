"""Delivery entry point: converts newsletter markdown to PDF.

Usage:
    python -m src.deliver data/output/2026-05-12/newsletter.md
    python -m src.deliver path/to/newsletter.md --output custom-output.pdf
"""
from __future__ import annotations

import argparse
from pathlib import Path

from .delivery.pdf_generator import markdown_to_pdf


def main():
    parser = argparse.ArgumentParser(description="Convert newsletter Markdown to PDF")
    parser.add_argument("markdown_file", help="Path to the newsletter markdown file")
    parser.add_argument("--output", "-o", help="Output PDF path (default: same dir as input)")
    args = parser.parse_args()

    md_path = Path(args.markdown_file)
    if not md_path.exists():
        print(f"[deliver] File not found: {md_path}")
        return

    newsletter_md = md_path.read_text(encoding="utf-8")

    if args.output:
        pdf_path = args.output
    else:
        pdf_path = str(md_path.parent / md_path.stem) + ".pdf"

    markdown_to_pdf(newsletter_md, pdf_path)
    print(f"[deliver] PDF ready: {pdf_path}")


if __name__ == "__main__":
    main()
