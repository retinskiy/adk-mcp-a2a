"""
Web Researcher Agent
====================
ADK sub-agent that uses MCP tools (search_web, fetch_url) from the local
mcp_servers/web_tools.py server to gather raw research on a topic.

WHY MCP here instead of plain Python functions?
------------------------------------------------
We could have imported search_web/fetch_url directly, but using the MCP
protocol means the tool server is a separate process with its own runtime
boundary. In production you'd swap web_tools.py for any public MCP server
(Brave Search, Exa, Firecrawl, etc.) without touching the agent code.
That's the whole value proposition of MCP: tool servers are interchangeable.

WHY StdioServerParameters (subprocess, not SSE)?
-------------------------------------------------
For a local demo, stdio is the simplest transport — no port management,
no auth, no network. The ADK framework starts the subprocess, pipes JSON
over stdin/stdout, and shuts it down automatically when the agent is done.
Use SseConnectionParams or StreamableHTTPConnectionParams for remote servers.

WHY pass McpToolset directly to tools=[] instead of extracting tool objects?
-----------------------------------------------------------------------------
The new McpToolset (ADK 1.x) is a BaseToolset that manages the MCP session
lifecycle internally. The ADK Runner calls get_tools() on it at the right
moment and closes the connection when the invocation ends. We never touch
the subprocess directly — the framework owns it.
"""

import sys
from pathlib import Path

from google.adk.agents import Agent

from agents.config import MODEL

# StdioConnectionParams wraps StdioServerParameters and adds a 'timeout'
# field for the handshake — subprocess startup can be slow on cold Python
# imports, so 30s gives the MCP server time to load.
from google.adk.tools.mcp_tool.mcp_toolset import (
    McpToolset,
    StdioConnectionParams,
    StdioServerParameters,
)

# Absolute path so the subprocess can be launched from any working directory.
_SERVER_PATH = str(Path(__file__).parent.parent / "mcp_servers" / "web_tools.py")

INSTRUCTION = """You are a web research specialist.

Given a research topic, you MUST:
1. Call search_web with a focused query to find relevant sources.
2. Call fetch_url on the 2 most promising URLs from the search results.
3. Return a JSON object (as plain text) in exactly this shape:
   {
     "topic": "<the research topic>",
     "sources": [
       {"url": "...", "title": "...", "snippet": "...", "content": "..."},
       ...
     ],
     "raw_findings": "<2-3 sentences summarising the most important facts found>"
   }

Do NOT return anything other than the JSON object. Be thorough but concise.
"""


def create_web_researcher() -> Agent:
    """
    Synchronous factory — builds the agent and attaches the McpToolset.

    WHY synchronous now (was async before)?
    ----------------------------------------
    The old pseudocode called MCPToolset.from_server() which doesn't exist.
    In ADK 1.x, McpToolset is constructed synchronously and passed into
    tools=[]. The framework establishes the actual subprocess connection
    lazily, on the first tool invocation inside run_async(). This means:
      - No async factory needed here.
      - No exit_stack to track — the toolset closes itself.
      - The orchestrator factory becomes synchronous too (simpler chain).
    """
    # McpToolset is constructed here but the subprocess is NOT started yet.
    # The ADK Runner will call toolset.get_tools() before the first LLM turn,
    # which spawns the subprocess and performs the MCP handshake.
    toolset = McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=sys.executable,   # same Python interpreter in the venv
                args=[_SERVER_PATH],      # our FastMCP server
            ),
            timeout=30.0,                 # seconds to wait for MCP handshake
                                          # (cold Python starts can be ~5s)
        )
    )

    return Agent(
        name="web_researcher",
        model=MODEL,
        description=(
            "Searches the web and fetches URL content to gather raw research "
            "on a topic. Returns structured JSON with sources and key findings."
        ),
        instruction=INSTRUCTION,
        # Pass the toolset directly — Agent will call toolset.get_tools()
        # during execution and toolset.close() when the invocation ends.
        tools=[toolset],
    )
