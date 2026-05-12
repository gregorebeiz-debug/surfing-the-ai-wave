# Surfing the AI Wave — Project Context

## What This Is
An automated daily AI intelligence briefing system that collects, analyzes, filters, and delivers curated AI news and content to Gregorio's Gmail every morning at 6 AM (Bogota time) as a styled PDF.

## Architecture
**Claude Routine + Python collectors:**
1. **Collection** (Python, no AI) — 5 collectors scrape YouTube, GitHub, Reddit, newsletters, blogs
2. **Analysis + Synthesis** (Claude Routine = Sonnet) — Claude reads raw data, scores relevance, deduplicates, and writes the editorial newsletter directly
3. **Delivery** (Python + MCP) — Markdown → PDF via weasyprint, email via Gmail MCP connector

**Runs on:** Claude Routine (cloud-based cron, runs on Anthropic infrastructure)
**Cost:** $0 extra — counts against Claude Pro subscription usage
**No API keys needed for AI** — the Routine IS Claude

## Current Status
- **DONE:** All collection code written and syntax-verified
- **DONE:** Routine instructions at `routine/daily.md`
- **DONE:** Design spec at `docs/superpowers/specs/2026-05-12-surfing-ai-wave-newsletter-design.md`
- **DONE:** Config files with 30 Tier 1 + 40 Tier 2 sources
- **DONE:** GitHub repo created (private)
- **NOT DONE:** Routine setup in Claude Code (create the actual Routine with cron schedule)
- **NOT DONE:** Reddit API app creation (reddit.com/prefs/apps)
- **NOT DONE:** Gmail MCP connector setup
- **NOT DONE:** End-to-end test with real data
- **NOT DONE:** Newsletter PDF design (Phase 2 — Claude-inspired aesthetic with wave motifs)
- **NOT DONE:** YouTube channel ID resolution for some Tier 2 handles

## Key Files
| File | Purpose |
|------|---------|
| `routine/daily.md` | Routine instructions — scoring rules, editorial rules, full pipeline steps |
| `src/collect.py` | Collection entry point — runs all 5 collectors |
| `src/deliver.py` | Delivery entry point — markdown to PDF conversion |
| `src/main.py` | Local fallback orchestrator (runs collect only) |
| `src/collectors/*.py` | 5 data collectors (YouTube, GitHub, Reddit, newsletters, blogs) |
| `src/collectors/base.py` | Base collector with retry logic and rate limiting |
| `src/delivery/pdf_generator.py` | Markdown → PDF via weasyprint |
| `src/delivery/email_sender.py` | Gmail API fallback (Routine uses MCP connector instead) |
| `src/state.py` | State persistence between runs |
| `config/sources.yaml` | All 70+ sources with tiers, handles, URLs |
| `config/profile.yaml` | Gregorio's interest profile and scoring rules |
| `templates/newsletter.css` | PDF styling |
| `src/analyzer/prompts.py` | Scoring rules reference (used by Routine, not by Python) |
| `src/synthesizer/prompts.py` | Editorial rules reference (used by Routine, not by Python) |

## Source Tiers
- **Tier 1 (daily):** 15 YouTube creators, 4 official sources, 4 technical voices, 2 newsletters, 2 subreddits, 3 GitHub categories = ~30 sources
- **Tier 2 (weekly Sunday):** 24 YouTube creators, 5 technical voices, 3 podcasts, 2 newsletters, 2 subreddits, 4 GitHub categories = ~40 additional sources

## Environment Variables (Routine)
- `GITHUB_TOKEN` — For GitHub collector (repo releases, trending)
- `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET` — Reddit API (free)
- `NEWSLETTER_RECIPIENT` — Gregorio's email address

## Running Locally
```bash
pip install -r requirements.txt
python -m src.collect --test       # Test collection with 2 sources per collector
python -m src.collect --tier tier1  # Full daily collection
python -m src.collect --tier all    # Full weekly collection (includes Tier 2)
python -m src.deliver path/to/newsletter.md  # Convert markdown to PDF
```

## How the Routine Works
1. **Cron triggers** daily at 11:00 UTC (6:00 AM Bogota)
2. **Shell:** `pip install -r requirements.txt && python -m src.collect --tier tier1`
3. **Claude reads** all raw JSON files from `data/raw/YYYY-MM-DD/`
4. **Claude analyzes** each item (scoring, categorization, dedup) using rules in `routine/daily.md`
5. **Claude writes** the newsletter in Spanish with English technical terms
6. **Shell:** `python -m src.deliver` converts markdown to PDF
7. **Gmail MCP:** sends email with PDF to Gregorio
8. **Archive:** saves newsletter to `newsletters/YYYY/MM/`

## User Preferences
- **Language:** Spanish (Colombian) for newsletter, technical terms in English
- **Style:** Critical, analytical, professional — NEVER complacent
- **Content:** Depth without excess, signal over noise, actionable over informational
- **Design (Phase 2):** Claude-inspired, wave/surf motifs, blues, modern but not cyberpunk
