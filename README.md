# 🔶 Post Discussion Summarizer

A Streamlit app that fetches Hacker News discussions and uses Google Gemini to generate structured summaries, sentiment analysis, and community insights — with persistent caching and structured logging.

---

## Quick Start

### 1. Prerequisites
- Python 3.9+
- A Google Gemini API key

### 2. Install Dependencies
```bash
pip install streamlit google-genai pydantic python-dotenv requests beautifulsoup4
```

### 3. Configure API Key
Create a `.env` file in the project root:
```
GEMINI_API_KEY=your_api_key_here
```
Alternatively, paste the key directly into the app sidebar under the **API Key** expander at runtime.

### 4. Run the App
```bash
streamlit run post_summarizer_stapp_cache.py
```
The app will open in your browser at `http://localhost:8501`

---

## Features

| Feature | Description |
|---|---|
| **Dual Input Modes** | Analyze top N posts from the HN homepage, or paste a specific discussion URL |
| **Structured Analysis** | Generates summary, key themes, notable insights, sentiment, controversy signal, and reasoning trace |
| **Persistent Cache** | Results saved to `cache.json` — avoids repeat Gemini calls for already-processed URLs |
| **API Key Flexibility** | Reads from `.env` automatically; falls back to sidebar input if not found |
| **Processing Lock** | UI controls disabled during analysis to prevent conflicting actions mid-run |
| **Collapsible Results** | Each post's analysis shown in its own expandable section |
| **Download Results** | Export the full analysis as a `.txt` file directly from the UI |
| **Structured Logging** | All events logged to `logs/app.log` with timestamp and module name |

---

## How It Works

### Top N Posts Mode
1. Fetches the HN homepage and parses the top N post titles and their discussion links (`item?id=...`)
2. For each post: checks cache → returns instantly on hit; calls Gemini on miss
3. Saves new results to `cache.json` and displays with a progress bar
4. Each result shown in a collapsible section labelled with the post title

### Single URL Mode
1. User pastes a HN discussion URL (`https://news.ycombinator.com/item?id=...`)
2. Page title extracted from the HTML `<title>` tag for accurate result heading
3. Cache check → Gemini call if needed → result displayed and cached

> **Note:** Always paste HN/ycomb discussion URLs (`item?id=...`), not external article links. The app analyzes the comments thread, not the article itself.

---

## Code Structure

| Function | Responsibility |
|---|---|
| `Summarizer` (Pydantic) | Defines the output schema for Gemini responses |
| `_load_cache / _save_cache` | Read and write `cache.json` |
| `get_or_analyze()` | Cache lookup wrapper — returns cached result or triggers a Gemini call |
| `read_data_url()` | Fetches raw HTML from a URL |
| `get_top_posts()` | Scrapes HN homepage for post titles and discussion URLs |
| `get_page_title()` | Extracts `<title>` tag from a fetched page |
| `gemini_completions()` | Calls Gemini API and returns a validated `Summarizer` object |
| `format_result()` | Formats the output into a readable plain-text block |

---

## Output Format

Each analyzed post produces a structured block:

```
============================================================
<Post Title>
<URL>
============================================================

SUMMARY
-------
<summary text>

KEY THEMES
----------
  • Theme 1
  • Theme 2

NOTABLE INSIGHTS
----------------
  1. Insight one
  2. Insight two

COMMUNITY SENTIMENT
-------------------
<sentiment>

CONTROVERSY SIGNAL
------------------
<controversy level>

REASONING TRACE
---------------
<model's chain of thought>
```

---

## Caching

Results are stored in `cache.json` as a flat key-value map of URL to formatted result string. The cache persists across app restarts.

- **Cache hit** — result returned instantly
- **Cache miss** — Gemini is called, result saved to disk before returning
- **Cache log** — shown in a collapsible expander after each run
- **Clear cache** — available in the sidebar to wipe `cache.json`

---

## Logging

All events are written to `logs/app.log` in append mode. The directory is created automatically on first run.

**Log format:**
```
YYYY-MM-DD-HH-MM-SS - <module> - <LEVEL> - <message>
```

**Log levels:**
- `DEBUG` — URL fetches, response sizes, Gemini call details
- `INFO` — cache hits/misses, post counts, analysis start/complete
- `ERROR` — failures with full stack traces

---

## Project Structure

```
.
├── post_summarizer_stapp_cache.py  # Main application
├── cache.json                   # Persistent cache (auto-created)
├── logs/
│   └── app.log                     # Application logs (auto-created)
├── .env                            # API key (not committed)
└── README.md
```

---

## Notes

- The `.env` file must be in the same directory as the script for `python-dotenv` to pick it up
- `custom_url`, `mode`, and `n_posts` are stored in `st.session_state` to survive Streamlit reruns during the analyze flow
- The processing lock (`st.session_state.processing`) disables all sidebar controls during a run to prevent mid-run disruption
