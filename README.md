# Meta Ads Analytics Agent 🤖

Hey there 👋. This is an AI agent I built to automate Meta Ads reporting end-to-end. If you've ever spent time manually pulling campaign data and writing weekly client updates, this is what replacing that workflow looks like.

## What it actually does

Two AI agents, one pipeline:

1. **Data Analyst Agent:** Hits the Meta Graph API directly, pulls account and campaign-level metrics (spend, ROAS, CPP, purchases, CPM, CTR, adds to cart), and structures everything with safe fallbacks so the pipeline doesn't break if a campaign is paused or a field comes back empty.

2. **Comms Lead Agent:** Takes that structured data and writes a client-facing performance update in a specific brand voice, sourced from a tone reference file. No generic AI output. The agent is explicitly constrained to avoid filler language and produce updates that sound like a real human wrote them.

## Stack

- **[CrewAI](https://crewai.com):** Orchestrates the two-agent pipeline sequentially
- **[OpenRouter](https://openrouter.ai):** Routes LLM calls with native model fallbacks (no custom retry logic needed)
- **Meta Graph API v22.0:** The data source
- **Python + python-dotenv:** Environment management, no hardcoded keys

## How agent reliability is handled

A few things I built deliberately to keep this stable on free-tier infrastructure:

- `max_rpm=2` on both agents, avoiding rate limit trips on OpenRouter's free tier
- `temperature=0.0` on all LLM calls, locking output to deterministic, data-grounded responses
- Primary + fallback model routing via OpenRouter's `extra_body` parameter. If the primary model is unavailable, it falls over to the backup automatically
- Custom `MetaTokenExpiredError`: if the Meta API token expires, the pipeline halts immediately with an actionable message instead of a cryptic stack trace
- `MetaAPIError` for everything else (429s, 500s), with the same clean exit behaviour
- All `.get()` parsing with explicit fallbacks, so the pipeline never crashes on a missing field

## Setup

```bash
# 1. Clone and install
git clone https://github.com/iamaditya-gaur/meta-ads-analytics-agent.git
cd meta-ads-analytics-agent
pip install -r requirements.txt
```

```bash
# 2. Add your credentials
cp .env.example .env
```

Your `.env` needs three things:

```
META_ACCESS_TOKEN=your_60_day_token
META_AD_ACCOUNT_ID=your_ad_account_id
OPENROUTER_API_KEY=your_openrouter_key
```

Optional, override defaults per run:

```
CLIENT_NAME=Coffee Beanery
REPORT_PERIOD=Mar 22 - Mar 29
DATE_PRESET=last_7d
```

```bash
# 3. Run
python main.py
```

The final report saves to `client_report.md` automatically.

## Project structure

```
meta-ads-analytics-agent/
├── agents/
│   ├── data_analyst_agent.py   # Meta API fetching + CrewAI agent config
│   └── comms_lead_agent.py     # Report writing + tone enforcement
├── tasks/
│   ├── extraction_tasks.py     # Data structuring task definition
│   └── writing_tasks.py        # Report generation task definition
├── tone_context.txt            # Brand voice reference for the Comms Lead
├── main.py                     # Orchestration entry point
└── requirements.txt
```

## What's next (V2 roadmap)

This is a working V1. It runs, it reports, it doesn't break. What I'm planning to add:

- Dynamic date range inputs instead of env-variable-only presets
- Multi-account support (connect more than one Meta ad account per run)
- Slack/email delivery of the final report
- Scheduled execution so it runs automatically without manual triggers

---

Built by a PM who got tired of doing this manually. Questions or ideas, open an issue.
