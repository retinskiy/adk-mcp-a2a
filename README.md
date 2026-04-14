# Research Crew — ADK + MCP + A2A Demo

A multi-agent research pipeline built with **Google ADK**, **Model Context Protocol (MCP)**, and **Agent-to-Agent (A2A)** communication. Enter any research topic and get back a structured brief — plus a **real NotebookLM notebook** created automatically via browser automation, with a simulated podcast excerpt and FAQ.

---

## Architecture

```
User Input (Gradio UI)
        │
        ▼
┌───────────────────────────────────────────────────────────┐
│          Orchestrator Agent  (ADK Root)                   │
│              gemini-2.5-flash  (Vertex AI)                │
│  "Research coordinator — delegates all work via A2A"      │
└────────┬──────────────────┬───────────────────┬───────────┘
         │ A2A (AgentTool)  │ A2A (AgentTool)   │ A2A (AgentTool)
         ▼                  ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  WebResearcher  │ │   Summarizer    │ │  NotebookLM     │
│     Agent       │ │     Agent       │ │     Agent       │
│                 │ │                 │ │                 │
│ Uses MCP tools: │ │  LLM only —     │ │ FunctionTool:   │
│  search_web()   │ │  structures raw │ │  notebooklm_    │
│  fetch_url()    │ │  data into MD   │ │  upload (real)  │
└────────┬────────┘ └─────────────────┘ └─────────────────┘
         │ stdio MCP protocol
         ▼
┌─────────────────┐
│   MCP Server    │
│ web_tools.py    │
│                 │
│ DuckDuckGo +    │
│ httpx + BS4     │
└─────────────────┘
```

### Data Flow

```
topic ──► [WebResearcher] ──► JSON sources
                                    │
                                    ▼
                           [Summarizer] ──► Markdown brief
                                                  │
                                                  ▼
                                      [NotebookLM] ──► Brief + Podcast + FAQ
                                                              │
                                                              ▼
                                                        Gradio UI
```

---

## Technology Breakdown

| Technology | Role in this project | Why |
|------------|---------------------|-----|
| **Google ADK** | Agent orchestration framework | Provides `Agent`, `AgentTool`, `Runner`, and session management — the backbone of the pipeline |
| **MCP** (Model Context Protocol) | Tool serving layer | The `web_tools.py` server exposes `search_web` and `fetch_url` as MCP tools; ADK connects via `McpToolset` + stdio transport. Decouples tool implementation from agent logic. |
| **A2A** (Agent-to-Agent) | Sub-agent delegation | Each specialist agent is wrapped in `AgentTool` and registered with the orchestrator. The orchestrator calls them like functions, but each runs its own LLM loop. |
| **Gradio** | UI layer | Async generator support enables live streaming of the agent activity log |
| **NotebookLM** | Content enrichment | Real notebook created via Playwright + CDP (browser automation). Mock enrichment (podcast + FAQ) fills in until the Enterprise API is available. |

---

## Project Structure

```
adk-mcp-a2a/
├── .env.example              # Copy to .env and fill in credentials
├── requirements.txt
├── main.py                   # Entry point
├── agents/
│   ├── config.py             # Shared model name constant
│   ├── orchestrator.py       # Root ADK agent — delegates via A2A
│   ├── web_researcher.py     # Sub-agent — MCP search + fetch
│   ├── summarizer.py         # Sub-agent — structures findings
│   └── notebooklm_agent.py   # Sub-agent — real notebook + enrichment
├── mcp_servers/
│   └── web_tools.py          # MCP server: search_web + fetch_url
├── tools/
│   ├── notebooklm_real.py    # Playwright/CDP browser automation for NotebookLM
│   ├── notebooklm_mock.py    # Mock podcast excerpt + FAQ enrichment
│   └── save_google_auth.py   # Verify Chrome CDP connection
└── ui/
    └── gradio_app.py         # Gradio interface with streaming log
```

---

## Setup

### 1. Clone and install

```bash
git clone <repo-url>
cd adk-mcp-a2a
pip install -r requirements.txt
```

### 2. Configure credentials

**Option A — Vertex AI (recommended, no quota issues):**

```bash
cp .env.example .env
# .env already configured for Vertex AI — just set your project:
# GOOGLE_CLOUD_PROJECT=your-gcp-project-id
```

Then authenticate:
```bash
gcloud auth application-default login
gcloud services enable aiplatform.googleapis.com --project=YOUR_PROJECT
```
Billing must be enabled on the project. Model Garden → Gemini must be enabled once in the Cloud Console.

**Option B — Gemini API key:**

```bash
cp .env.example .env
# Comment out the Vertex AI block, uncomment:
# GOOGLE_API_KEY=AIza...
```

Get a key at [Google AI Studio](https://aistudio.google.com/apikey).

### 3. Install Playwright browser

```bash
playwright install chromium
```

### 4. Launch Chrome with remote debugging

Close all Chrome windows first, then:

```powershell
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%USERPROFILE%\chrome-debug-profile"
```

Log in to [https://notebooklm.google.com/](https://notebooklm.google.com/) in that window and leave it open.

Verify the connection:
```bash
python tools/save_google_auth.py
```

### 5. Run

```bash
python main.py
```

Open [http://localhost:7860](http://localhost:7860) in your browser.

---

## Demo Script

> "How to use it"

1. **Open the UI**

2. **Enter a topic** — try `"Google Agent Development Kit (ADK)"` or `"Model Context Protocol (MCP) for AI agents"`.

3. **Click Run Research Crew** — workflow:
   - *"First the Orchestrator delegates to the WebResearcher agent via A2A — that's just an `AgentTool` wrapping a second ADK agent."*
   - *"The WebResearcher connects to a local MCP server — a separate process — and calls `search_web` and `fetch_url` over the stdio MCP protocol."*
   - *"Then A2A again to the Summarizer, which uses the LLM to structure raw JSON into a markdown brief."*
   - *"Finally the NotebookLM agent — it opens Chrome via CDP and creates a real NotebookLM notebook with the research pasted in as a source. The podcast excerpt and FAQ are simulated."*

4. **Look at the brief** — scroll the output panel. Pay attention to the executive summary, key findings, sources table, podcast excerpt, FAQ.

5. **Key points:**
   - ADK handles session state, event streaming, and tool registration
   - MCP decouples tool servers from agents — swap `web_tools.py` for any other MCP server
   - A2A lets specialists focus on one job; the orchestrator just routes
   - The Gradio streaming works via ADK's `runner.run_async()` async event stream

---

## NotebookLM Integration

The pipeline creates a **real NotebookLM notebook** on every run via Playwright browser automation connecting to Chrome over CDP (Chrome DevTools Protocol). The research brief is pasted directly as a source.

The podcast excerpt and FAQ are generated by `tools/notebooklm_mock.py` until the NotebookLM Enterprise API becomes publicly available.

---

## Running the MCP server standalone (for debugging)

```bash
python mcp_servers/web_tools.py
```

Or test the tools directly in Python (bypassing MCP protocol):

```python
import sys; sys.path.insert(0, '.')
from mcp_servers.web_tools import search_web, fetch_url
print(search_web("Google ADK agents"))
print(fetch_url("https://adk.dev/"))
```

Note: in production the agent connects via `McpToolset` + stdio, not direct import.
