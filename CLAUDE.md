# Surfing the AI Wave — Project Context

## What This Is
An automated daily AI intelligence briefing system that collects, analyzes, filters, and delivers curated AI news and content to Gregor's Gmail every morning at 6 AM (Bogota time) as a styled PDF.

## Architecture
**Deterministic Python pipeline + AI at 2 strategic points:**
1. **Collection** (Python, no AI) — 5 collectors scrape YouTube, GitHub, Reddit, newsletters, blogs
2. **Analysis** (Gemini 2.5 Flash, free tier) — Extract key points, classify, score relevance, deduplicate
3. **Synthesis** (Claude Sonnet 4.6 API) — Editorial newsletter writing with merge/separate logic
4. **Delivery** (Python, no AI) — Markdown → PDF → Gmail

**Runs on:** GitHub Actions cron (daily Mon-Sat 2AM, weekly Sunday 1AM Bogota time)
**Cost:** ~$3.50-7/month (Gemini free tier + Sonnet API only)

## Current Status
- **DONE:** All code is written and syntax-verified (32 files, ~1,870 lines)
- **DONE:** Design spec at `docs/superpowers/specs/2026-05-12-surfing-ai-wave-newsletter-design.md`
- **DONE:** Config files with 30 Tier 1 + 40 Tier 2 sources
- **NOT DONE:** API keys setup (Anthropic, Reddit, Gmail OAuth2)
- **NOT DONE:** GitHub repo creation and secrets configuration
- **NOT DONE:** End-to-end test with real data
- **NOT DONE:** Newsletter PDF design (Phase 2 — Claude-inspired aesthetic with wave motifs)
- **NOT DONE:** YouTube channel ID resolution (handles are configured but UC... IDs need verification)

## Key Files
| File | Purpose |
|------|---------|
| `src/main.py` | Main orchestrator — runs all 4 phases sequentially |
| `src/collectors/*.py` | 5 data collectors (YouTube, GitHub, Reddit, newsletters, blogs) |
| `src/analyzer/analyzer.py` | Gemini Flash analysis pipeline |
| `src/analyzer/dedup.py` | Semantic dedup via embeddings |
| `src/analyzer/prompts.py` | Gemini prompt with scoring rules |
| `src/synthesizer/synthesizer.py` | Sonnet newsletter synthesis |
| `src/synthesizer/prompts.py` | Editorial rules and newsletter structure |
| `src/delivery/pdf_generator.py` | Markdown → PDF via weasyprint |
| `src/delivery/email_sender.py` | Gmail API email with PDF attachment |
| `src/state.py` | State persistence between runs |
| `config/sources.yaml` | All 70+ sources with tiers, handles, URLs |
| `config/profile.yaml` | Gregor's interest profile and scoring rules |
| `templates/newsletter.css` | Basic PDF styling (Phase 1) |
| `.github/workflows/daily.yml` | GitHub Actions daily cron |
| `.github/workflows/weekly.yml` | GitHub Actions weekly cron |

## Source Tiers
- **Tier 1 (daily):** 15 YouTube creators, 4 official sources, 4 technical voices, 2 newsletters, 2 subreddits, 3 GitHub categories = ~30 sources
- **Tier 2 (weekly Sunday):** 24 YouTube creators, 5 technical voices, 3 podcasts, 2 newsletters, 2 subreddits, 4 GitHub categories = ~40 additional sources

## API Keys Needed (GitHub Secrets)
- `ANTHROPIC_API_KEY` — For Sonnet synthesis (~$3.50-7/month)
- `GEMINI_API_KEY` — For Flash analysis (free tier, 1,500 req/day)
- `GITHUB_TOKEN` — Auto-provided by GitHub Actions
- `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET` — Reddit API (free)
- `GMAIL_CLIENT_ID` + `GMAIL_CLIENT_SECRET` + `GMAIL_REFRESH_TOKEN` — Gmail OAuth2
- `NEWSLETTER_RECIPIENT` — Gregor's email address

## Running Locally
```bash
pip install -r requirements.txt
python -m src.main --test --skip-email  # Test mode with limited sources
python -m src.main --tier tier1          # Full daily run
python -m src.main --tier all            # Full weekly run (includes Tier 2)
```

## User Preferences
- **Language:** Spanish (Colombian) for newsletter, technical terms in English
- **Style:** Critical, analytical, professional — NEVER complacent
- **Content:** Depth without excess, signal over noise, actionable over informational
- **Design (Phase 2):** Claude-inspired, wave/surf motifs, blues, modern but not cyberpunk
