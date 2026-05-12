# Surfing the AI Wave — System Design Spec

## Context

Gregorio is a business administrator who has deeply self-taught AI over the past few years. He uses Claude Code, builds automation agents, and actively follows the AI ecosystem. His core problem: the AI sector moves too fast to consume all relevant information, and most content is noise — derivative channels copying leaders, hype without substance, and scattered across too many platforms.

This system solves that by automating daily research, filtering, analysis, and delivery of a curated AI intelligence briefing. The goal is not a "news summary" — it's an actionable intelligence system that helps Gregorio stay at the edge of AI developments efficiently, distinguishing what moves the needle from what's noise.

---

## 1. Architecture

### Pattern: Deterministic Pipeline + AI at 2 Strategic Points

The system is a Python pipeline orchestrated by GitHub Actions cron. AI is used only where it adds real value: analysis (Gemini Flash) and editorial synthesis (Claude Sonnet). Everything else — data collection, PDF generation, email delivery — is deterministic Python code.

**Why this over multi-agent:** Agents consume tokens on "thinking" about flow control. A Python script doesn't hallucinate, doesn't waste tokens, and is trivially debuggable. AI is reserved for tasks requiring intelligence.

### Execution Flow

```
PHASE 1 — COLLECTION (2:00-2:30 AM) — Python, no AI
├── youtube_collector.py    (youtube-transcript-api, free)
├── github_collector.py     (GitHub REST API, free)
├── reddit_collector.py     (Reddit API via PRAW, free)
├── newsletter_collector.py (RSS/web scraping, free)
└── blog_collector.py       (web scraping, free)
    All run in parallel. Output → /data/raw/YYYY-MM-DD/

PHASE 2 — ANALYSIS (2:30-4:00 AM) — Gemini 2.5 Flash (free tier)
└── analyzer.py
    ├── Extract key points per item
    ├── Classify by topic category
    ├── Assign relevance score (1-10) via rule-based prompt
    ├── Semantic dedup (cosine similarity > 0.90)
    └── Output → /data/analyzed/YYYY-MM-DD/analysis.json

PHASE 3 — SYNTHESIS (4:00-5:00 AM) — Claude Sonnet 4.6 API
└── synthesizer.py
    ├── Reads full analysis.json
    ├── Editorial decisions: merge vs separate, section placement
    ├── Writes newsletter in Markdown
    └── Output → /data/output/YYYY-MM-DD/newsletter.md

PHASE 4 — DELIVERY (5:00-6:00 AM) — Python, no AI
└── delivery.py
    ├── Markdown → PDF (weasyprint + CSS template)
    ├── Compose email with top highlights
    ├── Attach PDF
    └── Send via Gmail API → Gregorio's personal Gmail
```

### Scheduling

| Schedule | Scope | Target delivery |
|----------|-------|-----------------|
| Daily (Mon-Sat) | Tier 1 sources only (~30 sources) | 6:00 AM |
| Weekly (Sunday) | Tier 1 + Tier 2 sources (~70 sources) | 6:00 AM |

### Infrastructure

- **Runtime:** GitHub Actions (free tier: 2,000 min/month)
- **Estimated usage:** ~30 min/day x 30 + ~60 min x 4 Sundays = ~1,140 min/month (57% of budget)
- **State persistence:** `state.json` committed to repo after each run — tracks processed video_ids, post_ids, repo versions
- **Secrets:** API keys stored as GitHub Actions secrets (Gemini API key, Anthropic API key, Gmail OAuth credentials)

### Cost

| Component | Tool | Monthly Cost |
|-----------|------|-------------|
| YouTube transcripts | youtube-transcript-api | $0 |
| Web scraping | requests + BeautifulSoup | $0 |
| Reddit API | PRAW (free tier) | $0 |
| GitHub API | REST API (free, 5K req/hr) | $0 |
| Analysis (~100 items/day) | Gemini 2.5 Flash free tier | $0 |
| Synthesis (1 call/day) | Claude Sonnet 4.6 API | ~$3.50-7.00 |
| GitHub Actions | Free tier | $0 |
| **TOTAL** | | **~$3.50-7.00/month** |

---

## 2. Source Tiers

### Tier 1 — Daily Scan (~30 sources)

#### YouTube Creators (15)
| Creator | Specialty | Dedup Group |
|---------|-----------|-------------|
| Andrej Karpathy | AI research, education, original thought | — |
| Nick Saraev | AI automation, agencies, tools | Automation Cluster |
| Nate Herk | n8n, automation, AI business | Automation Cluster |
| Jack Roberts | AI automation, agencies | Automation Cluster |
| Chase AI | AI tools, automation | Automation Cluster |
| AI Foundations | AI agents, automation | Automation Cluster |
| Greg Isenberg | AI + business building | — |
| Jeff Su | AI productivity, office workflows | — |
| Sabrina Ramonov | SaaS building with AI | — |
| Alex Finn | Live builds, AI products | — |
| Brad \| AI & Automation | Claude Code, MCP, open source | — |
| Jay E \| RoboNuggets | AI content creation | — |
| UI Collective | Design systems + AI | — |
| Adrian Saenz | Finance + AI | — |
| Alejavi Rivera | AI tutorials (Spanish) | — |

**Automation Cluster rule:** Nick Saraev, Nate Herk, Jack Roberts, Chase AI, AI Foundations cover overlapping territory. Smart merge: if content is substantially the same, show only the best (most views, best creator, or first publisher). If approach is meaningfully different (e.g., one does tutorial, another analyzes implications), show separately.

#### Official Sources (4)
| Source | What to monitor |
|--------|----------------|
| OpenAI | Blog, changelog, announcements |
| Anthropic/Claude | Blog, changelog, model releases |
| Google DeepMind | Blog, model releases |
| Y Combinator | YouTube, blog posts |

#### Independent Technical Voices (4)
| Person | Platform | Why essential |
|--------|----------|---------------|
| Simon Willison | Blog (simonwillison.net), X, GitHub | Most important independent AI voice. Coined prompt injection, agentic engineering. |
| Swyx / Latent Space | Podcast, Substack | #1 technical AI podcast. Digest for user, don't recommend listening. |
| Andrew Ng | Newsletter "The Batch", LinkedIn | Authoritative weekly AI overview. |
| Jim Fan | X, NVIDIA blog | Best translator of complex AI research. |

#### Newsletters (2) — Auto-digest, not for user to read
| Newsletter | Focus |
|------------|-------|
| The Rundown AI | Best daily AI news digest |
| TLDR AI | More technical daily digest |

#### Reddit (2)
| Subreddit | Focus |
|-----------|-------|
| r/LocalLLaMA | Open-source AI, model evaluations, practical tips |
| r/ClaudeAI | Claude-specific tips, problems, workflows |

#### GitHub (3 categories)
| What | How |
|------|-----|
| GitHub Trending AI/ML | Daily trending repos in AI/ML topics |
| Releases of monitored repos | Ollama, n8n, OpenClaw, Dify, ComfyUI, LangChain, vLLM, Open WebUI |
| awesome-llm-agents | Community curation of best AI agent resources |

### Tier 2 — Weekly Scan (Sunday only, ~40 additional sources)

#### YouTube Creators (24)
Brock Mesarich, Benjamin Cordero, Migue Baena IA, Lewis Jackson, Davie Fogarty, THE ECOM KING, Futurepedia, Aprendizaje Supervisado, Grow with Alex, Miles Deutscher, Brendan Gillen, Alex Robinson, Alek, AI Pathways, AI Master, WealthManagement Informa, Simon Scrapes, and others added over time.

#### Technical Voices (5)
| Person | Platform |
|--------|----------|
| Yann LeCun | X (@ylecun) |
| Jeremy Howard / Answer.AI | YouTube, blog |
| Nathan Lambert (Interconnects) | Newsletter |
| Sebastian Raschka (Ahead of AI) | Blog |
| Gary Marcus | X, Substack — skeptical counterweight |

#### Podcasts (3) — Digest only, never recommend listening
| Podcast | Focus |
|---------|-------|
| Dwarkesh Podcast | Deepest technical AI interviews |
| TWIML AI | Broadest coverage (700+ episodes) |
| Practical AI | Production-focused |

#### Newsletters (2)
| Newsletter | Focus |
|------------|-------|
| Ben's Bites | Startup/founder-centric |
| Import AI (Jack Clark) | Policy, deep analysis |

#### Reddit (2)
| Subreddit | Focus |
|-----------|-------|
| r/MachineLearning | Research papers, academic discussions |
| r/artificial | General AI news |

#### GitHub Additional
| What | Focus |
|------|-------|
| Hugging Face Trending | Models and papers trending |
| Individual repos trending | Skills, tools, templates from individual devs |
| MCP ecosystem | New MCP servers (7,260+ and growing) |
| Palantir / StackAI | Enterprise AI releases (sporadic) |

---

## 3. Newsletter Content Structure

### Daily Newsletter Sections

#### Section 1: "The Wave Today" — News that moves the needle
- **When:** Always (if nothing relevant: "Calm seas today")
- **Content:** Official announcements, model launches, significant ecosystem changes
- **Format:** 2-4 items max. Each: headline + why it matters (2-3 lines) + source(s) + link
- **Merge rule:** If 3+ creators cover the same announcement → merge into 1 item, cite sources

#### Section 2: "Deep Dives" — Content worth exploring directly
- **When:** When videos/posts have `action_type = "deep_dive"`
- **Content:** Live demos, practical tutorials, unique deep technical analysis
- **Format:** Each item separate by creator:
  - Creator + video title
  - What it covers + why worth your time (3-5 lines)
  - "Why watch": one line with specific value (e.g., "Shows step-by-step MCP server setup in Claude Code")
  - Direct link + video duration
- **Merge rule:** Same topic, different approach → both shown with differentiation note. Same approach → only the best.

#### Section 3: "Tool & Repo Watch" — New tools and repos
- **When:** When relevant repos/tools are detected
- **Content:** Trending repos, releases, new AI tools, skills, templates
- **Format per item:**
  - Name + what it does (1 line)
  - Why it matters for you (1-2 lines)
  - Stars/forks (if GitHub)
  - Direct link
  - Suggested action: "Install", "Explore", "Monitor", "Info only"

#### Section 4: "Community Pulse" — What the community is discussing
- **When:** When significant discussions exist in Reddit/communities
- **Content:** Trending posts in r/LocalLLaMA, r/ClaudeAI, relevant debates
- **Format:**
  - Discussion topic + source community
  - Main viewpoints/consensus (2-3 lines)
  - Link to thread if comments are worth reading

#### Section 5: "Signal Board" — Quick catch-all
- **When:** Always (catch-all for items that don't warrant their own section)
- **Format:** Bullet points, 1 line each with link and relevance indicator

#### Conditional Section: "Buyer Beware" — Hype alert
- **When:** Multiple creators promote something but red flags exist (negative Reddit reviews, retractions, predatory pricing)
- **Content:** "Everyone is talking about [X], but watch out because..."

### Weekly Newsletter (Sunday) — Additional Sections

- **"Week in Review"** — Trends, dominant themes, sector direction
- **"Podcast Digest"** — Key points from Dwarkesh, TWIML, Practical AI, Latent Space (extracted, not recommended to listen)
- **"Knowledge Stack"** — Technical blogs, relevant papers, educational resources

### Editorial Rules (Sonnet system prompt)

1. Never repeat the same information twice in the newsletter
2. If a topic is covered by 3+ sources with the same angle → merge into 1 item, cite sources
3. If a creator does a live demo of something practical → Deep Dives section, always
4. If it's just opinion/reaction without original content → Signal Board as bullet point
5. Prioritize by actionability: Can Gregorio DO something with this? → top. Just informative? → bottom
6. Videos: recommend watching ONLY when visual format adds value (demos, tutorials, configurations). If someone is just talking → extract the info, don't send to watch
7. Repos: always include suggested action (install, explore, monitor)
8. Daily target length: 1,200-1,800 words (~7-10 min reading)
9. Weekly target length: 2,500-3,500 words (~15-20 min reading)

---

## 4. Analysis Pipeline Detail

### Item Schema (output of analyzer.py)

```json
{
  "id": "yt_nicksaraev_abc123",
  "title": "Build an AI Agent That Actually Works",
  "source_type": "youtube",
  "source_channel": "Nick Saraev",
  "source_tier": 1,
  "category": "AI Agents",
  "relevance_score": 8.5,
  "key_points": [
    "Demonstrates CrewAI agent building from scratch",
    "Shows real production deployment on Vercel",
    "Compares 3 frameworks: CrewAI vs LangGraph vs AutoGen"
  ],
  "action_type": "deep_dive",
  "why_relevant": "Practical tutorial with live demo — directly applicable to Gregorio's agent building projects",
  "duplicate_group_id": null,
  "is_best_in_group": true,
  "original_url": "https://youtube.com/watch?v=abc123",
  "video_duration_minutes": 22,
  "published_date": "2026-05-11",
  "raw_content_path": "/data/raw/2026-05-12/youtube/nicksaraev_abc123.json"
}
```

### Relevance Scoring Rules (Gemini Flash prompt)

```
Score 9-10: Directly about Gregorio's core tools/workflows (Claude Code, AI agents, automation)
            AND includes practical demo/tutorial/new release
Score 7-8:  About Gregorio's interest areas with actionable content
            (new tool worth trying, significant update to known tool, deep technical analysis)
Score 5-6:  Relevant topic but informational only (news, opinions, predictions)
Score 3-4:  Tangentially related (general tech, business with light AI angle)
Score 1-2:  Not relevant (entertainment, off-topic, pure hype)

Modifiers:
+2 if live demo or step-by-step tutorial
+1 if new tool/repo with >100 stars in first 48h
+1 if from Tier 1 creator
-2 if pure opinion/reaction with no original content
-3 if substantially duplicate of another item (mark for merge)
```

### Deduplication Logic

1. **URL/title hash:** Catches exact duplicates instantly
2. **Semantic similarity:** Generate embeddings per item, cosine similarity > 0.90 → same topic
3. **Within duplicate groups:** Pick "best" based on: (a) creator tier, (b) view count, (c) first published, (d) has demo/tutorial

---

## 5. State Management

### state.json (committed to repo after each run)

```json
{
  "last_run": "2026-05-12T05:30:00Z",
  "last_weekly_run": "2026-05-11T05:30:00Z",
  "processed": {
    "youtube_video_ids": ["abc123", "def456", ...],
    "reddit_post_ids": ["t3_xyz789", ...],
    "github_repos_seen": {"ollama/ollama": "v0.5.2", ...},
    "blog_urls": ["https://simonwillison.net/2026/May/11/...", ...]
  },
  "stats": {
    "total_items_collected": 87,
    "items_after_dedup": 52,
    "items_in_newsletter": 18,
    "gemini_api_calls": 96,
    "sonnet_api_calls": 1,
    "execution_time_minutes": 28
  }
}
```

### Data Retention
- Raw data: keep 7 days, then auto-delete via cleanup step in GitHub Actions workflow
- Analyzed data: keep 30 days, then auto-delete
- Newsletter output (MD + PDF): keep indefinitely (committed to repo under /newsletters/YYYY/MM/)
- State.json: rolling window — only tracks IDs from last 7 days to prevent unbounded growth. Pruned automatically at start of each run.
- Timezone: All timestamps in America/Bogota (UTC-5). Cron schedule adjusted accordingly.

---

## 6. Error Handling & Monitoring

| Failure | Response |
|---------|----------|
| YouTube API rate limit | Retry with exponential backoff (max 3 retries). If fails, skip that video, note in newsletter. |
| Reddit API down | Skip Reddit section for the day. Note "Reddit unavailable today" in newsletter. |
| Gemini API failure | Retry 3x. If persists, fall back to simpler extraction (regex-based key point extraction). |
| Sonnet API failure | Retry 3x. If persists, send raw analysis.json as email attachment with apology note. |
| No new content found | Send short "Calm seas today" newsletter. Don't skip the email — consistency builds the habit. |
| GitHub Actions timeout | Alert via email. Investigate. Most likely cause: too many YouTube transcripts. |

### Quality Calibration (First 2 Weeks)
- Gregorio reviews newsletters and provides feedback on scoring accuracy
- Adjust relevance scoring rules in Gemini prompt based on feedback
- Track: items that scored high but weren't interesting, items that scored low but should have been featured

---

## 7. Technology Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Language | Python 3.12+ | Best library ecosystem for scraping, APIs, data processing |
| YouTube transcripts | youtube-transcript-api | Free, no API key, reliable |
| Web scraping | requests + BeautifulSoup4 | Lightweight, sufficient for blogs/newsletters |
| Reddit | PRAW (Python Reddit API Wrapper) | Official wrapper, 60 req/min |
| GitHub | PyGithub or requests | REST API, 5K req/hr |
| Analysis AI | Google Gemini 2.5 Flash (free tier) | Free, 1,500 req/day, good for extraction |
| Synthesis AI | Claude Sonnet 4.6 (Anthropic API) | Best writing quality at reasonable cost |
| Embeddings | Gemini text-embedding (free tier, included in 1,500 req/day) | For semantic dedup — avoids installing heavy local model in GitHub Actions |
| PDF generation | weasyprint | HTML/CSS → PDF with custom design |
| Email | Gmail API (OAuth2) | Direct integration, Gregorio's personal Gmail |
| Scheduling | GitHub Actions (cron) | Free, reliable, cloud-based |
| State | state.json in repo | Simple, version-controlled, no external DB needed |

---

## 8. User Profile (for AI prompts)

This profile is embedded in both Gemini and Sonnet system prompts:

```
User: Gregorio
Background: Business administrator, self-taught AI practitioner
Experience level: Intermediate-advanced (uses Claude Code, builds agents, understands LLMs)
Core interests (ranked by priority):
1. Claude Code, Claude ecosystem, MCP servers, skills
2. AI Agents (CrewAI, LangGraph, autonomous systems, OpenClaw)
3. AI Automation workflows (n8n, Make.com, custom pipelines)
4. LLMs (GPT, Claude, Gemini, Kimi, open-source models)
5. Web design/development with AI (Vercel, Next.js, AI-assisted design)
6. AI for business (ecommerce, marketing, brand, finance)
7. AI media generation (video: Higgsfield, SeaDance; voice: ElevenLabs; images)
8. Investment/wealth management with AI
9. Agentic OS, memory systems, RAG architectures

Communication preference: Spanish (Colombian), but technical terms in English
Analysis style: Critical, analytical, professional — never complacent
Content preference: Depth without excess, lean without losing substance, signal over noise
```

---

## 9. Newsletter Design (Phase 2 — Future)

Design will be implemented separately. Requirements captured:
- Visual, graphic, modern aesthetic
- Claude-inspired design language (not cyberpunk)
- Wave/surf motifs reflecting "Surfing the AI Wave" branding
- Blues as primary color palette
- Clean typography similar to Anthropic's brand
- Tables, visual hierarchies, possibly surfboard/wave decorative elements
- Professional but young and fresh feel
- PDF must be well-designed, not just text dump

---

## 10. Verification Plan

### How to test end-to-end:
1. **Unit tests:** Each collector returns valid JSON for a known input
2. **Integration test:** Run full pipeline with a small subset (3 YouTube channels, 1 subreddit) and verify output quality
3. **Scoring calibration:** Run analyzer on 20 known items (10 high-relevance, 10 low-relevance) and verify scores match expectations
4. **Dedup test:** Feed 5 videos about the same topic and verify correct merging
5. **Email delivery:** Send test newsletter to Gregorio's Gmail and confirm PDF attachment renders correctly
6. **Cost monitoring:** Track actual API usage for first week and verify it's within $3.50-7/month budget
7. **GitHub Actions:** Verify cron triggers at 2 AM, completes within 30-60 minutes, and handles failures gracefully
