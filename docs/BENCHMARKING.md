# Agent Benchmarking

The benchmarking system measures agent correctness, response quality, and latency over time — enabling iterative improvement.

## Quick Start

```bash
# Run all agents
python3 benchmark.py

# Run one agent
python3 benchmark.py --agent calculator

# Show historical results
python3 benchmark.py --report

# Use a different model
python3 benchmark.py --model llama3.2
```

## How It Works

Each benchmark run:

1. Loads test cases from `benchmarks/*_benchmark.json`
2. Sends each input through the full chatbot path (keyword detection → agent dispatch → LLM response)
3. Scores the response on correctness and latency
4. Stores results in `web_chatbot.db`

### Scoring

| Metric | Description |
|---|---|
| **Correctness** | 0.0–1.0 ratio of expected keywords/patterns found in response |
| **Latency** | End-to-end response time in milliseconds |
| **Passed** | `correctness == 1.0` AND `latency_ms <= max_latency_ms` |

## Test Case Format

Each agent has a JSON file in `benchmarks/`:

```json
{
  "agent": "calculator",
  "cases": [
    {
      "id": "calc_addition",
      "input": "What is 12 + 45?",
      "expected_keywords": ["57"],
      "expected_patterns": [],
      "max_latency_ms": 30000
    }
  ]
}
```

| Field | Description |
|---|---|
| `id` | Unique case identifier |
| `input` | Natural language input sent to the chatbot |
| `expected_keywords` | Strings that must appear in the response (case-insensitive) |
| `expected_patterns` | Regex patterns that must match in the response |
| `max_latency_ms` | Maximum acceptable response time |

If `expected_keywords` and `expected_patterns` are both empty, the case scores 1.0 automatically (useful for gmail when credentials may be absent).

## Included Test Cases

### Calculator
- `calc_addition` — "What is 12 + 45?" → expects "57"
- `calc_multiplication` — "Calculate 7 * 8" → expects "56"
- `calc_division` — "What is 100 divided by 4?" → expects "25"

### Time
- `time_current` — "What time is it?" → expects `HH:MM` pattern
- `time_date` — "What is today's date?" → expects 4-digit year

### Weather
- `weather_city` — "What is the weather in London?" → expects "weather", "temperature", and a `°` temperature value
- `weather_fahrenheit` — "Tell me the weather in New York" → expects "weather"

### Web Search
- `search_factual` — "Search for Python programming language" → expects "Python"
- `search_technology` — "Tell me about machine learning" → expects "machine"

### Gmail
- `gmail_inbox` — "Check my Gmail inbox" → no keyword requirements (pass if credentials present)

## Adding Test Cases

Edit the relevant JSON file in `benchmarks/` or create a new one following the naming convention `<agent>_benchmark.json`:

```json
{
  "agent": "weather",
  "cases": [
    {
      "id": "weather_paris",
      "input": "What's the weather in Paris?",
      "expected_keywords": ["weather", "temperature"],
      "expected_patterns": ["\\d+°"],
      "max_latency_ms": 25000
    }
  ]
}
```

No code changes needed — benchmark.py auto-discovers all `benchmarks/*_benchmark.json` files.

## Reading the Report

```
python3 benchmark.py --report
```

Shows pass rate and average latency per agent across the last 10 runs:

```
Per-Agent Summary (across last 10 runs):
+------------+----------+-------------+---------------+
| Agent      | Passed   | Pass Rate   | Avg Latency   |
+============+==========+=============+===============+
| calculator | 8/9      | 88%         | 7200ms        |
| weather    | 4/4      | 100%        | 9100ms        |
| web_search | 3/4      | 75%         | 21000ms       |
+------------+----------+-------------+---------------+
```

## Database Schema

Results are stored in `web_chatbot.db`:

```sql
CREATE TABLE benchmark_results (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      TEXT,       -- UUID grouping all cases in one run
    timestamp   TEXT,
    agent_name  TEXT,
    case_id     TEXT,
    input       TEXT,
    response    TEXT,
    correctness REAL,       -- 0.0 to 1.0
    latency_ms  INTEGER,
    passed      INTEGER,    -- 0 or 1
    model       TEXT        -- Ollama model used
);
```

Query raw results directly:

```bash
sqlite3 web_chatbot.db "SELECT agent_name, case_id, passed, latency_ms FROM benchmark_results ORDER BY timestamp DESC LIMIT 20;"
```

## Iterative Improvement Workflow

1. Run `python3 benchmark.py` to get a baseline
2. Modify agent logic, prompts, or keyword detection
3. Run `python3 benchmark.py` again
4. Compare with `python3 benchmark.py --report` — pass rates and latency trend vs previous runs
5. Add new test cases to cover regressions as you find them
