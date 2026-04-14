# Research Crew — ADK + MCP + A2A Demo

A multi-agent research pipeline built with **Google ADK**, **Model Context Protocol (MCP)**, and **Agent-to-Agent (A2A)** communication. Enter any research topic and get back a structured brief complete with a simulated NotebookLM podcast excerpt and FAQ.

---

## Architecture

```
User Input (Gradio UI)
        │
        ▼
┌───────────────────────────────────────────────────────────┐
│          Orchestrator Agent  (ADK Root)                   │
│              gemini-2.0-flash-exp                         │
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
│  fetch_url()    │ │  data into MD   │ │  upload (mock)  │
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
| **MCP** (Model Context Protocol) | Tool serving layer | The `web_tools.py` server exposes `search_web` and `fetch_url` as MCP tools; ADK connects via `MCPToolset` + stdio transport. Decouples tool implementation from agent logic. |
| **A2A** (Agent-to-Agent) | Sub-agent delegation | Each specialist agent is wrapped in `AgentTool` and registered with the orchestrator. The orchestrator calls them like functions, but each runs its own LLM loop. |
| **Gradio** | UI layer | Async generator support enables live streaming of the agent activity log |
| **NotebookLM** | Content enrichment | Mocked in this demo; see `tools/notebooklm_mock.py` for how the real Enterprise API would integrate |

---

## Project Structure

```
adk-mcp-a2a/
├── .env.example              # Copy to .env and add your API key
├── requirements.txt
├── main.py                   # Entry point
├── agents/
│   ├── orchestrator.py       # Root ADK agent — delegates via A2A
│   ├── web_researcher.py     # Sub-agent — MCP search + fetch
│   ├── summarizer.py         # Sub-agent — structures findings
│   └── notebooklm_agent.py   # Sub-agent — podcast + FAQ
├── mcp_servers/
│   └── web_tools.py          # MCP server: search_web + fetch_url
├── tools/
│   └── notebooklm_mock.py    # Realistic mock of NotebookLM Enterprise API
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

### 2. Configure your API key

```bash
cp .env.example .env
# Edit .env and paste your Gemini API key:
# GOOGLE_API_KEY=AIza...
```

Get a key at [Google AI Studio](https://aistudio.google.com/apikey).

### 3. Run

```bash
python main.py
```

Open [http://localhost:7860](http://localhost:7860) in your browser.

---

## Demo Script (Interview Ready)

> "Let me show you a multi-agent pipeline I built using three of the most important emerging standards in agentic AI."

1. **Open the UI** — point out the architecture diagram at the top.

2. **Enter a topic** — try `"Google Agent Development Kit (ADK)"` or `"Model Context Protocol (MCP) for AI agents"`.

3. **Click Run Research Crew** — narrate as each step appears in the log:
   - *"First the Orchestrator delegates to the WebResearcher agent via A2A — that's just an `AgentTool` wrapping a second ADK agent."*
   - *"The WebResearcher connects to a local MCP server — a separate process — and calls `search_web` and `fetch_url` over the stdio MCP protocol."*
   - *"Then A2A again to the Summarizer, which uses the LLM to structure raw JSON into a markdown brief."*
   - *"Finally the NotebookLM agent — in production this would call the NotebookLM Enterprise API; here it mocks a realistic podcast excerpt and FAQ."*

4. **Show the brief** — scroll the output panel. Point out executive summary, key findings, sources table, podcast excerpt, FAQ.

5. **Key talking points:**
   - ADK handles session state, event streaming, and tool registration
   - MCP decouples tool servers from agents — swap `web_tools.py` for any other MCP server
   - A2A lets specialists focus on one job; the orchestrator just routes
   - The Gradio streaming works via ADK's `runner.run_async()` async event stream

---

## NotebookLM Notebook

The real research notebook for this project lives at:
**https://notebooklm.google.com/notebook/31e70cf0-e72b-450d-8ac5-883f0b8636bc**

The `notebooklm_agent.py` file documents exactly how to replace the mock with real
NotebookLM Enterprise API calls when access becomes available.

---

## Running the MCP server standalone (for debugging)

```bash
python mcp_servers/web_tools.py
```

Or test the tools directly in Python:

```python
from mcp_servers.web_tools import search_web, fetch_url
print(search_web("Google ADK agents"))
print(fetch_url("https://google.github.io/adk-docs/"))
```
