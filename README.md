# Agent System

A lightweight full-stack agentic task runner built with **FastAPI** and **React**. The agent parses natural language tasks, scores and selects the most appropriate tool, executes it, and returns a fully numbered execution trace. For compound tasks it chains multiple tools sequentially via a **MultiStepOrchestrator**, threading the output of each step into the next.

---

## Table of Contents

- [Quick Start](#quick-start)
  - [Running the Backend](#running-the-backend)
  - [Running the Frontend](#running-the-frontend)
  - [Docker](#docker)
- [Dependencies](#dependencies)
- [Architecture](#architecture)
  - [File Structure](#file-structure)
  - [Single-Step Decision Logic](#single-step-decision-logic)
  - [Multi-Step Orchestration Logic](#multi-step-orchestration-logic)
- [Available Tools](#available-tools)
- [API Reference](#api-reference)
- [Example Tasks](#multi-step-chain-examples)
- [Test Results](#test-results)
- [Bonus Features](#bonus-features)
- [Assumptions & Trade-offs](#assumptions--trade-offs)
- [Time Spent](#time-spent)
- [What I'd Improve With More Time](#what-id-improve-with-more-time)

---

## Quick Start

> **Requirement:** Node.js **v18 or higher**. Run `node --version` to check. Upgrade at https://nodejs.org if needed.

Both backend and frontend must run simultaneously in separate terminals.

---

### Running the Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate          # Mac / Linux
.venv\Scripts\activate             # Windows (Command Prompt)
.venv\Scripts\Activate.ps1         # Windows (PowerShell)

pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

| URL | Purpose |
|---|---|
| `http://localhost:8000` | Base API |
| `http://localhost:8000/docs` | Interactive Swagger UI |
| `http://localhost:8000/health` | Health check |

The SQLite database (`tasks.db`) is created automatically on first startup.

---

### Running the Frontend

```bash
cd frontend
npm install
npm run dev
```

UI at `http://localhost:3000`. Vite proxies `/api/*` to `http://localhost:8000` automatically.

---

### Docker

```bash
# From the project root
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | `http://localhost:3000` |
| Backend API | `http://localhost:8000` |

```bash
docker compose down      # stop
docker compose down -v   # stop + remove DB volume
```

> **Windows note:** If you see `ca.pem: The system cannot find the path specified`, you have stale Docker Machine environment variables. Clear them in PowerShell: `Remove-Item Env:DOCKER_HOST; Remove-Item Env:DOCKER_CERT_PATH; Remove-Item Env:DOCKER_TLS_VERIFY; Remove-Item Env:DOCKER_MACHINE_NAME`

---

## Dependencies

### Backend

| Package | Version | Purpose |
|---|---|---|
| Python | 3.11+ | Runtime |
| FastAPI | 0.111.0 | Web framework |
| Uvicorn | 0.30.1 | ASGI server |
| Pydantic | v2.7.4 | Request/response validation |
| aiosqlite | 0.20.0 | SQLite persistence |
| pytest | any | Test runner (`pip install pytest`) |

### Frontend

| Package | Version | Purpose |
|---|---|---|
| Node.js | 18+ | Runtime |
| React | 18.3.1 | UI framework |
| Vite | 5.3.4 | Build tool + dev server |

---

## Architecture

### File Structure

```
agent-system/
├── backend/
│   ├── app.py                     # FastAPI routes, CORS, lifespan
│   ├── agent/
│   │   ├── controller.py          # AgentController: scoring, selection, fallback, orchestration dispatch
│   │   └── orchestrator.py        # MultiStepOrchestrator: compound task detection, chaining, injection
│   ├── tools/
│   │   ├── base.py                # BaseTool abstract class
│   │   ├── calculator.py          # CalculatorTool
│   │   ├── text_processor.py      # TextProcessorTool
│   │   ├── weather_mock.py        # WeatherMockTool
│   │   ├── base64_tool.py         # Base64Tool 
│   │   └── fallback_explainer.py  # FallbackExplainerTool (last-resort fallback)
│   ├── storage/db.py              # SQLite CRUD
│   └── tests/test_all.py          # 55 unit + integration tests
└── frontend/
    └── src/
        ├── App.jsx                # Root component
        ├── api.js                 # HTTP client
        └── components/
            ├── TaskInput.jsx
            ├── ResultPanel.jsx
            ├── TraceViewer.jsx    # Renders [STAGE N] labels for multi-step traces
            ├── HistoryList.jsx
            └── ToolsPanel.jsx
```

---

### Single-Step Decision Logic

```
Input task
    │
    ▼
Is it multi-step?  (MultiStepOrchestrator.is_multistep)
    │ NO
    ▼
1. SCORING  — every tool (except FallbackExplainerTool) is scored:
     +10  base keyword match  (tool.can_handle)
     +25  explicit "base64" / "b64" keyword     → Base64Tool
     +20  numeric operator pattern "3 + 5"      → CalculatorTool
     +20  "weather" / "forecast" keyword        → WeatherMockTool
     +15  text op keyword ("uppercase", etc.)   → TextProcessorTool
    │
    ▼
2. SELECTION  — highest score wins; registration order breaks ties
    │
    ▼
3. EXECUTION  — tool.execute(task) → ToolResult(output, steps, error)
    │
    ├─ SUCCESS → wrap in AgentResponse, save to SQLite, return
    │
    └─ ERROR  → FALLBACK CHAIN
                  │
                  ├─ Another domain tool that can_handle(task)?
                  │   → execute it (e.g. calc error → text tool)
                  │
                  └─ No match → FallbackExplainerTool
                                  .prepare(error)   ← injects error context
                                  .execute(task)    ← returns human explanation + tips
```

---

### Multi-Step Orchestration Logic

When a task contains a **chaining connector** — `then`, `and then`, `followed by`, `after that` — the `MultiStepOrchestrator` takes over:

```
Input: "base64 encode 'hello' then count the characters of the result"
    │
    ▼
1. DETECTION
   MultiStepOrchestrator.is_multistep() finds "then" → True
    │
    ▼
2. SPLITTING
   _split() → ["base64 encode 'hello'",  "count the characters of the result"]
    │
    ▼
3. SEQUENTIAL EXECUTION  (for each sub-task)
   │
   ├─ Stage 1: "base64 encode 'hello'"
   │    AgentController.run_single() → Base64Tool
   │    output: "aGVsbG8="
   │    prev_output = "aGVsbG8="
   │
   └─ Stage 2: "count the characters of the result"
        _inject_output() finds "the result" → replaces with '"aGVsbG8="'
        injected: 'count the characters of "aGVsbG8="'
        AgentController.run_single() → TextProcessorTool
        output: "8 characters"
    │
    ▼
4. MERGE TRACE
   All sub-traces are renumbered and annotated:
     Step 5: [STAGE 1] Received input: "base64 encode 'hello'"
     Step 6: [STAGE 1] Encoded 5 bytes → 8 Base64 characters
     ...
     Step 12: [STAGE 2] Injecting previous output → "count the characters of \"aGVsbG8=\"
     Step 13: [STAGE 2] Operation: count characters → 8 characters
    │
    ▼
5. RETURN AgentResponse
   output:      "8 characters"
   tools_used:  ["Base64Tool", "TextProcessorTool"]
   sub_results: [{stage:1, tool:"Base64Tool", output:"aGVsbG8="},
                 {stage:2, tool:"TextProcessorTool", output:"8 characters"}]
```

**Output injection** replaces these references in the next sub-task:
`the result` · `the output` · `the answer` · `it` · `that` · `{result}`

If the sub-task already contains a quoted string, injection is skipped — the explicit target takes priority.

**Chain stops on the first error.** The completed stages are returned as partial results with an `error` field on the response.

---

## Available Tools

### CalculatorTool
Evaluates arithmetic expressions using a safe AST evaluator (no `eval()`).

| Input | Output |
|---|---|
| `3 + 5` | `8` |
| `(10 - 2) * 4` | `32` |
| `2 ** 8` | `256` |
| `sqrt(144)` | `12` |
| `square root of 25` | `5` |
| `5 plus 3 times 2` | `11` |
| `10 / 0` | Error → FallbackExplainerTool |

---

### TextProcessorTool
Text transformations via natural language instructions.

| Input | Output |
|---|---|
| `uppercase "hello world"` | `HELLO WORLD` |
| `lowercase "THE SKY"` | `the sky` |
| `title case "the lord of the rings"` | `The Lord Of The Rings` |
| `reverse "racecar"` | `racecar` |
| `word count of "the quick brown fox"` | `4 words` |
| `count the characters of "hello"` | `5 characters` |
| `palindrome check "A man a plan a canal Panama"` | `is a palindrome ✓` |
| `snake_case "my variable name"` | `my_variable_name` |
| `camelCase "my variable name"` | `myVariableName` |

---

### WeatherMockTool
Mock weather data for 20 hardcoded cities. Unknown cities get generic conditions.

| Input | Output |
|---|---|
| `weather in London` | Full report: condition, °C/°F, humidity, wind |
| `forecast for Tokyo` | Full report |
| `temperature in Dubai` | Full report |
| `weather in Atlantis` | Generic mock data |
| `weather` (no city) | Error → FallbackExplainerTool |

Supported cities: London, New York, Tokyo, Sydney, Paris, Berlin, Dubai, Moscow, Toronto, Singapore, Los Angeles, Chicago, Mumbai, Cairo, Amsterdam, Seoul, Bangkok, Cape Town, Rome, Beijing.

---

### Base64Tool
Encodes and decodes Base64 strings in multiple modes.

| Input | Output |
|---|---|
| `base64 encode "hello world"` | `aGVsbG8gd29ybGQ=` |
| `base64 decode "aGVsbG8gd29ybGQ="` | `hello world` |
| `decode "aGVsbG8"` (no padding) | `hello` |
| `base64 encode "user@example.com"` | `dXNlckBleGFtcGxlLmNvbQ==` |
| `url-safe base64 encode "hello+world"` | URL-safe encoded (no `+` or `/`) |
| `url-safe base64 decode "aGVsbG8="` | `hello` |
| `base64 info "SGVsbG8gV29ybGQ="` | Encoded length, decoded bytes, content type, decoded value |
| `base64 "aGVsbG8="` | Auto-detects → decodes → `hello` |
| `base64 "hello world"` | Auto-detects → encodes → `aGVsbG8gd29ybGQ=` |
| `base64 decode "invalid!!!"` | Error → FallbackExplainerTool |

**Auto-detect mode**: if the input matches the Base64 character set and is ≥4 characters, the tool attempts to decode; otherwise it encodes.

---

### FallbackExplainerTool
Never selected normally (empty keywords, zero score). Activated automatically when any other tool fails. Receives the error context via `prepare(error)` and returns a tailored explanation with actionable suggestions.

| Trigger | Explanation returned |
|---|---|
| Division by zero | Why it's undefined + valid alternatives |
| No city for weather | How to include a city name + supported list |
| Invalid Base64 | Valid character set + correctly formatted examples |
| Unparseable expression | Correct operator syntax + examples |
| Generic error | Task type overview + all supported formats |

---

### Multi-Step Chain Examples

### Example 1 — Encode then decode (round-trip)
```
Task:    base64 encode 'hello' then decode the result
Stage 1: Base64Tool       → aGVsbG8=
Stage 2: Base64Tool       → hello
Output:  hello
```

### Example 2 — Encode then count characters
```
Task:    base64 encode 'hello' then count the characters of the result
Stage 1: Base64Tool       → aGVsbG8=  (8 chars)
Stage 2: TextProcessorTool → 8 characters
Output:  8 characters
```

### Example 3 — Calculate then reverse
```
Task:    calculate 6 * 7 then reverse the result
Stage 1: CalculatorTool   → 42
Stage 2: TextProcessorTool → 24   (reversed)
Output:  24
```

### Example 4 — Uppercase then reverse
```
Task:    uppercase 'hello' followed by reverse the result
Stage 1: TextProcessorTool → HELLO
Stage 2: TextProcessorTool → OLLEH
Output:  OLLEH
```

### Example 5 — Three-stage chain
```
Task:    base64 encode 'hi' then reverse the result then count the characters
Stage 1: Base64Tool        → aGk=
Stage 2: TextProcessorTool → =kGa    (reversed)
Stage 3: TextProcessorTool → 4 characters
Output:  4 characters
```

### Example 6 — Weather then text op (partial chaining)
```
Task:    weather in Tokyo, then uppercase the condition
Stage 1: WeatherMockTool   → ☀️ Weather in Tokyo\nCondition: Clear\n...
Stage 2: TextProcessorTool →☀️ Weather in Tokyo\NCondition: CLEAR\N...
Output: Weather in Tokyo
        Condition: CLEAR
        Temperature: 24°C / 75.2°F
        Humidity: 58%
        Wind: 10 km/h
        As of: 2026-03-14 22:49 UTC (mock data)
```

### Example 7 — Calculate then reverse followed by Add operation (Chain with repeat callback)
```
Task:    calculate 6 * 7 after that reverse the result, then add 4
Stage 1: CalculatorTool   → 42
Stage 2: TextProcessorTool → 24
Stage 3: CalculatorTool → 28
Output:  28
```

---

## API Reference

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/tools` | List all tools |
| `POST` | `/tasks` | Submit a task |
| `GET` | `/tasks?limit=50` | Task history |
| `GET` | `/tasks/{id}` | Full task detail |
| `GET` | `/tasks/{id}/steps` | Execution trace only |
| `DELETE` | `/tasks/{id}` | Delete a task |

**Multi-step response** includes an extra `sub_results` array:

```json
{
  "id": 7,
  "task": "base64 encode 'hello' then count the characters of the result",
  "output": "8 characters",
  "tools_used": ["Base64Tool", "TextProcessorTool"],
  "steps": [
    "Step 1: Received compound task — ...",
    "Step 2: Detected 2 sub-tasks — orchestrating sequential execution",
    "Step 5: [STAGE 1] Received input: \"base64 encode 'hello'\"",
    "Step 9: [STAGE 1] Completed — output: \"aGVsbG8=\"",
    "Step 10: [STAGE 2] Injecting previous output → \"count the characters of \\\"aGVsbG8=\\\"\"",
    "Step 13: [STAGE 2] Operation: count characters → 8 characters",
    "Step 16: All 2 stages completed — returning final result to user"
  ],
  "sub_results": [
    {"stage": 1, "task": "base64 encode 'hello'",                      "tool": "Base64Tool",        "output": "aGVsbG8=",       "error": null},
    {"stage": 2, "task": "count the characters of \"aGVsbG8=\"",       "tool": "TextProcessorTool", "output": "8 characters",   "error": null}
  ],
  "timestamp": "2026-03-14T10:30:00+00:00",
  "error": null
}
```

---

## Test Results

```bash
cd backend
pip install pytest
python -m pytest tests/test_all.py -v
```

**Results: 93 passed, 0 failed**

```
tests/test_all.py::TestTextProcessorTool::test_uppercase PASSED                                          [  1%] 
tests/test_all.py::TestTextProcessorTool::test_lowercase PASSED                                          [  2%] 
tests/test_all.py::TestTextProcessorTool::test_title_case PASSED                                         [  3%] 
tests/test_all.py::TestTextProcessorTool::test_reverse PASSED                                            [  4%] 
tests/test_all.py::TestTextProcessorTool::test_word_count PASSED                                         [  5%] 
tests/test_all.py::TestTextProcessorTool::test_palindrome_true PASSED                                    [  6%]
tests/test_all.py::TestTextProcessorTool::test_palindrome_false PASSED                                   [  7%] 
tests/test_all.py::TestTextProcessorTool::test_steps_populated PASSED                                    [  8%] 
tests/test_all.py::TestTextProcessorTool::test_can_handle_positive PASSED                                [  9%] 
tests/test_all.py::TestTextProcessorTool::test_can_handle_negative PASSED                                [ 10%] 
tests/test_all.py::TestCalculatorTool::test_addition PASSED                                              [ 11%] 
tests/test_all.py::TestCalculatorTool::test_subtraction PASSED                                           [ 12%]
tests/test_all.py::TestCalculatorTool::test_multiplication PASSED                                        [ 13%] 
tests/test_all.py::TestCalculatorTool::test_division PASSED                                              [ 15%] 
tests/test_all.py::TestCalculatorTool::test_power PASSED                                                 [ 16%] 
tests/test_all.py::TestCalculatorTool::test_sqrt PASSED                                                  [ 17%] 
tests/test_all.py::TestCalculatorTool::test_sqrt_natural PASSED                                          [ 18%] 
tests/test_all.py::TestCalculatorTool::test_word_ops PASSED                                              [ 19%] 
tests/test_all.py::TestCalculatorTool::test_complex_expr PASSED                                          [ 20%]
tests/test_all.py::TestCalculatorTool::test_division_by_zero PASSED                                      [ 21%] 
tests/test_all.py::TestCalculatorTool::test_can_handle_positive PASSED                                   [ 22%] 
tests/test_all.py::TestCalculatorTool::test_can_handle_negative PASSED                                   [ 23%] 
tests/test_all.py::TestWeatherMockTool::test_known_city PASSED                                           [ 24%] 
tests/test_all.py::TestWeatherMockTool::test_unknown_city_fallback PASSED                                [ 25%] 
tests/test_all.py::TestWeatherMockTool::test_has_humidity PASSED                                         [ 26%] 
tests/test_all.py::TestWeatherMockTool::test_has_wind PASSED                                             [ 27%] 
tests/test_all.py::TestWeatherMockTool::test_has_fahrenheit PASSED                                       [ 29%] 
tests/test_all.py::TestWeatherMockTool::test_no_city_error PASSED                                        [ 30%] 
tests/test_all.py::TestWeatherMockTool::test_bare_forecast_error PASSED                                  [ 31%] 
tests/test_all.py::TestWeatherMockTool::test_can_handle_positive PASSED                                  [ 32%] 
tests/test_all.py::TestWeatherMockTool::test_can_handle_negative PASSED                                  [ 33%]
tests/test_all.py::TestBase64Tool::test_encode_hello_world PASSED                                        [ 34%] 
tests/test_all.py::TestBase64Tool::test_encode_empty_string PASSED                                       [ 35%] 
tests/test_all.py::TestBase64Tool::test_encode_special_chars PASSED                                      [ 36%] 
tests/test_all.py::TestBase64Tool::test_encode_numbers PASSED                                            [ 37%] 
tests/test_all.py::TestBase64Tool::test_decode_hello_world PASSED                                        [ 38%] 
tests/test_all.py::TestBase64Tool::test_decode_without_padding PASSED                                    [ 39%]
tests/test_all.py::TestBase64Tool::test_decode_invalid_raises_error PASSED                               [ 40%] 
tests/test_all.py::TestBase64Tool::test_decode_reverses_encode PASSED                                    [ 41%] 
tests/test_all.py::TestBase64Tool::test_url_safe_encode PASSED                                           [ 43%] 
tests/test_all.py::TestBase64Tool::test_url_safe_decode PASSED                                           [ 44%] 
tests/test_all.py::TestBase64Tool::test_validate_valid_string PASSED                                     [ 45%] 
tests/test_all.py::TestBase64Tool::test_validate_invalid_string PASSED                                   [ 46%] 
tests/test_all.py::TestBase64Tool::test_info_returns_metadata PASSED                                     [ 47%]
tests/test_all.py::TestBase64Tool::test_info_invalid_string_errors PASSED                                [ 48%] 
tests/test_all.py::TestBase64Tool::test_auto_detect_decodes_valid_b64 PASSED                             [ 49%] 
tests/test_all.py::TestBase64Tool::test_auto_detect_encodes_plaintext PASSED                             [ 50%] 
tests/test_all.py::TestBase64Tool::test_steps_populated PASSED                                           [ 51%] 
tests/test_all.py::TestBase64Tool::test_steps_include_operation PASSED                                   [ 52%] 
tests/test_all.py::TestBase64Tool::test_can_handle_base64 PASSED                                         [ 53%] 
tests/test_all.py::TestBase64Tool::test_cannot_handle_weather PASSED                                     [ 54%] 
tests/test_all.py::TestFallbackExplainerTool::test_can_handle_always_true PASSED                         [ 55%] 
tests/test_all.py::TestFallbackExplainerTool::test_no_keywords PASSED                                    [ 56%] 
tests/test_all.py::TestFallbackExplainerTool::test_div_by_zero_explanation PASSED                        [ 58%] 
tests/test_all.py::TestFallbackExplainerTool::test_no_city_explanation PASSED                            [ 59%] 
tests/test_all.py::TestFallbackExplainerTool::test_generic_fallback PASSED                               [ 60%] 
tests/test_all.py::TestFallbackExplainerTool::test_steps_populated PASSED                                [ 61%]
tests/test_all.py::TestAgentControllerRouting::test_routes_to_calculator PASSED                          [ 62%] 
tests/test_all.py::TestAgentControllerRouting::test_routes_to_weather PASSED                             [ 63%] 
tests/test_all.py::TestAgentControllerRouting::test_routes_to_text PASSED                                [ 64%] 
tests/test_all.py::TestAgentControllerRouting::test_routes_to_base64 PASSED                              [ 65%] 
tests/test_all.py::TestAgentControllerRouting::test_steps_numbered PASSED                                [ 66%] 
tests/test_all.py::TestAgentControllerRouting::test_timestamp_present PASSED                             [ 67%]
tests/test_all.py::TestAgentControllerRouting::test_unknown_task_error PASSED                            [ 68%] 
tests/test_all.py::TestAgentControllerRouting::test_five_tools_listed PASSED                             [ 69%] 
tests/test_all.py::TestAgentControllerRouting::test_fallback_not_in_normal_run PASSED                    [ 70%] 
tests/test_all.py::TestAgentControllerFallback::test_div_by_zero_activates_fallback PASSED               [ 72%] 
tests/test_all.py::TestAgentControllerFallback::test_div_by_zero_has_suggestions PASSED                  [ 73%] 
tests/test_all.py::TestAgentControllerFallback::test_div_by_zero_trace_shows_chain PASSED                [ 74%] 
tests/test_all.py::TestAgentControllerFallback::test_no_city_activates_fallback PASSED                   [ 75%]
tests/test_all.py::TestAgentControllerFallback::test_natural_language_div_zero PASSED                    [ 76%] 
tests/test_all.py::TestAgentControllerFallback::test_fallback_response_no_error PASSED                   [ 77%] 
tests/test_all.py::TestAgentControllerFallback::test_fallback_output_is_string PASSED                    [ 78%] 
tests/test_all.py::TestOrchestratorDetection::test_detects_then PASSED                                   [ 79%] 
tests/test_all.py::TestOrchestratorDetection::test_detects_and_then PASSED                               [ 80%] 
tests/test_all.py::TestOrchestratorDetection::test_detects_followed_by PASSED                            [ 81%] 
tests/test_all.py::TestOrchestratorDetection::test_detects_comma_then PASSED                             [ 82%]
tests/test_all.py::TestOrchestratorDetection::test_single_task_not_multistep PASSED                      [ 83%] 
tests/test_all.py::TestOrchestratorDetection::test_splits_correctly PASSED                               [ 84%] 
tests/test_all.py::TestOrchestratorDetection::test_splits_three_parts PASSED                             [ 86%] 
tests/test_all.py::TestOrchestratorInjection::test_injects_the_result PASSED                             [ 87%] 
tests/test_all.py::TestOrchestratorInjection::test_injects_it PASSED                                     [ 88%] 
tests/test_all.py::TestOrchestratorInjection::test_no_injection_when_quoted PASSED                       [ 89%] 
tests/test_all.py::TestOrchestratorInjection::test_no_injection_without_ref PASSED                       [ 90%]
tests/test_all.py::TestMultiStepEndToEnd::test_encode_then_decode PASSED                                 [ 91%] 
tests/test_all.py::TestMultiStepEndToEnd::test_encode_then_count_characters PASSED                       [ 92%] 
tests/test_all.py::TestMultiStepEndToEnd::test_calculate_then_reverse PASSED                             [ 93%] 
tests/test_all.py::TestMultiStepEndToEnd::test_uppercase_then_reverse PASSED                             [ 94%] 
tests/test_all.py::TestMultiStepEndToEnd::test_three_stage_chain PASSED                                  [ 95%] 
tests/test_all.py::TestMultiStepEndToEnd::test_tools_used_contains_both PASSED                           [ 96%]
tests/test_all.py::TestMultiStepEndToEnd::test_steps_contain_stage_labels PASSED                         [ 97%] 
tests/test_all.py::TestMultiStepEndToEnd::test_sub_results_structure PASSED                              [ 98%] 
tests/test_all.py::TestMultiStepEndToEnd::test_single_step_not_treated_as_multistep PASSED               [100%] 

================================================ 93 passed in 0.30s ================================================
```

---

## Bonus Features

### ✅ Base64Tool (new)
Four operations: standard encode/decode, URL-safe encode/decode, inspect (info), and auto-detect mode. No external dependencies — uses Python's built-in `base64` module. Both validators enforce the correct character sets (`[A-Za-z0-9+/=]` for standard, `[A-Za-z0-9\-_=]` for URL-safe) before attempting decode, preventing false positives on arbitrary strings.

### ✅ Multi-Step Orchestration (new)
`MultiStepOrchestrator` in `agent/orchestrator.py` detects compound tasks by scanning for chaining connectors (`then`, `and then`, `followed by`, `after that`, `, then`). It splits the task, executes each sub-task via `AgentController.run_single()`, and injects the previous output when the next sub-task references `the result`, `it`, `that`, or `{result}`. All sub-traces are merged into one flat numbered list with `[STAGE N]` prefixes. The API response includes a `sub_results` array exposing per-stage details.

### ✅ Dockerfile & Containerisation
`Dockerfile.backend` (Python 3.11 slim + Uvicorn), `Dockerfile.frontend` (Node 20 → Nginx alpine multi-stage), `docker-compose.yml` (health-checked backend gate, named SQLite volume), `nginx.conf` (static serving + `/api` reverse proxy). Each service uses its own `context:` path to avoid Windows path-resolution issues.

### ✅ Retry / Fallback Logic
`FallbackExplainerTool` is the fallback error handler. `_fallback_tool()` always returns a tool — first any other domain tool that `can_handle()` the input, then `FallbackExplainerTool` as the backstop. Error context is injected via `prepare(error)` so explanations are tailored to the exact failure mode.

### ⬜ Real-Time Streaming
Not implemented. Planned via `EventSourceResponse` in FastAPI.

### ⬜ RBAC
Not implemented. Planned JWT-based roles: `user` (own tasks only) and `admin` (all tasks + tool management).

---

## Assumptions & Trade-offs

**Heuristic tool scoring, not LLM routing.** Fast, deterministic, no API keys needed. Trade-off: Phrasing is specific for the scorer. An LLM router handles ambiguity better but adds latency and cost.

**Output injection is reference-based, not semantic.** The orchestrator looks for literal phrases ("the result", "it", "that") to decide when to thread outputs. This is predictable and transparent but won't infer intent from novel phrasing. A semantic approach would require NLP or an LLM.

**Chain stops on the first error.** Completed stages are returned as partial results. A retry-per-stage model would be more resilient but adds complexity without a clear benefit at this scale.

**"count" and "characters" are broad keywords.** Adding them to `TextProcessorTool` enables chained tasks like `count the characters of the result`, but could cause that tool to be chosen for unrelated inputs that happen to include those words. The scoring booster (`+15` only when specific text-op patterns are present) mitigates most false positives.

**SQLite for persistence.** Zero-config and appropriate for single-instance use. The storage layer (`storage/db.py`) is fully isolated, it can be swapped for PostgreSQL by replacing that one module.

**CORS fully open.** `allow_origins=["*"]` is intentional for local development. Lock to known origins before production.

---

## Time Spent

| Phase | Time |
|---|---|
| Architecture + scaffold | 60 min |
| CalculatorTool, TextProcessorTool, WeatherMockTool | 60 min |
| AgentController (scoring, fallback) | 60 min |
| Base64Tool (all 6 operations) | 60 min |
| MultiStepOrchestrator (detection, splitting, injection, trace merge) | 60 min |
| SQLite storage + FastAPI routes | 30 min |
| React frontend (all components + styling) | 60 min |
| Tests (93 cases) | 40 min |
| Docker, Nginx, README | 45 min |
| Error Handling, Code Cleanup, Issue Fixes | 60 mins |

---

## What I'd Improve With More Time

**1. Real-time streaming via SSE** — stream each `Step N:` as it is produced. The `TraceViewer` would animate steps into view one by one, making multi-step chains feel genuinely live.

**2. LLM-based routing** — replace the keyword scorer with a language model call for ambiguous or compound-intent tasks. Particularly valuable for the orchestrator's output injection, which currently requires exact reference phrases.

**3. Parallel multi-step execution** — when two sub-tasks are independent (no `{result}` reference), run them concurrently with `asyncio.gather()` and merge results. Current implementation is strictly sequential.

**4. RBAC** — JWT auth, `user` and `admin` roles. Admin can view/delete all tasks and manage tool registrations. User sees only their own history.

**5. Runtime tool registration** — allow admins to register a new tool via the API by uploading a Python module, without a server restart. The `AgentController` would hot-reload its tool registry.

**6. E2E tests** — Playwright tests driving the full browser flow: multi-step task submission, trace expansion, history click, delete.

**7. Better input parsing** — replace regex-based target extraction with a spaCy dependency parser for more robust handling of free-form natural language.
