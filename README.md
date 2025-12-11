# Reddit Mastermind Planner

Planning layer for a Reddit growth engine. This repo **does not post to Reddit**; it generates high‑quality weekly plans (what to post, where, when, and from which persona) plus ChatGPT‑ready briefs to draft the actual copy.

The goal is realism and long‑term Reddit presence: threads that earn upvotes, feel natural, and accumulate into search/LLM‑citable discussions over time.

## What It Produces

- **WeeklyCalendar**: a week of `PlannedAction`s (new posts + comment actions).
- **Prompt briefs**: short, structured prompts for ChatGPT to draft each action.
- **EvaluationReport**: authenticity/diversity/cadence/alignment scores + warnings.
- **Multi‑week continuity**: optional `PostingHistoryEntry` input to rotate pillars/personas and avoid repetition across weeks.
- **CSV export** (SlideForge schema): `P1/C1` post+comment tables with keyword IDs.

## Inputs

The core entrypoint `generate_content_calendar()` takes:

- `CompanyInfo`
- `Persona[]` (2+)
- `Subreddit[]`
- `ChatGPTQueryTemplate[]` (funnel stage + angle)
- `num_posts_per_week`
- optional `PostingHistoryEntry[]`
- `week_index`

Optional keyword targeting is supported via `CompanyInfo.keywords` and `ContentIdea.keyword_ids`.

## How It Works

Pipeline (per `AGENTS.md`):

- `derive_content_pillars()` — derive 5–7 content themes
- `build_weekly_target()` — set weekly quotas/ratios and rotate pillars from history
- `generate_candidate_ideas()` — create candidate ideas from templates (and optional LLM)
- `score_idea()` + `select_weekly_actions()` — score candidates and pick the best N actions within hard caps
- `generate_prompt_brief()` — write ChatGPT-ready briefs for each action
- `evaluate_calendar()` — score the calendar and emit warnings

Key behaviors:

- **Pillars = diversity guidance**, not hard caps.
- **40/60 mix** of new posts vs comments by default.
- **Risk flags** discourage promo/self‑shill language and repetition.
- **Threading** links comment actions into believable multi‑persona chains.
- **Templates drive topics** in deterministic mode; **Premium LLM mode** adds creativity when enabled.

## Quick Start

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run Streamlit UI (CSV input/output)
streamlit run app.py

# Run a sample week in code
python -m src.planning.calendar

# Tests
python3 -m pytest tests/ -v
```

### Premium LLM Mode

Premium mode uses `gpt-4o-mini` to generate extra ideas and CSV copy.  
Set your key in `.env` or the environment:

```bash
echo "OPENAI_API_KEY=sk-..." > .env
```

Quick mode (default) is deterministic and runs in <1s; Premium mode runs bounded parallel calls and typically takes ~15–25s.

## Example (Python)

```python
from src.config.slideforge import get_slideforge_config
from src.planning.calendar import generate_content_calendar

company, personas, subreddits, templates = get_slideforge_config()

calendar, evaluation = generate_content_calendar(
    company=company,
    personas=personas,
    subreddits=subreddits,
    templates=templates,
    num_posts_per_week=10,
    history=[],
    week_index=1,
    use_llm=False,  # Quick mode
)
```

## CLI

```bash
# Generate a week from python config
python3 -m src.cli --posts 10 --week 1

# Disable LLM (Quick mode)
python3 -m src.cli --no-llm

# Use history for multi‑week rotation
python3 -m src.cli --history-file history.json

# CSV mode (company info CSV → calendar CSV)
python3 -m src.cli csv --company "My Company - Company Info.csv" --output calendar.csv
```

## Available Sample Configs

| Config | Description |
|--------|-------------|
| `slideforge` | B2B presentation builder (default) |
| `devtools` | Developer tools / code analysis |
| `ecommerce` | Sustainable fashion brand |
| `minimal` | Edge‑case testing |

```bash
python3 -m src.cli --list-configs
```

## Testing

```bash
python3 -m pytest tests/ -v
```

Current suite covers quotas, pillar rotation, template usage, threading, multi‑week variety, and LLM‑off determinism. (106 tests passing.)

## Docs

- `AGENTS.md` — canonical spec and behavioral rules.
- `INTERNAL.md` — deeper notes on CSV schemas, tuning, and dev workflow.
