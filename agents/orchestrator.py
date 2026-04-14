"""
Orchestrator Agent
==================
Root ADK agent that coordinates the Research Crew pipeline via A2A delegation.

WHY A2A (Agent-to-Agent) instead of a single monolithic agent?
---------------------------------------------------------------
Three reasons you'll want to articulate in an interview:

1. Separation of concerns — each agent has one job and one system prompt.
   A single prompt trying to "search, summarise, AND format as NotebookLM"
   produces inconsistent results because the LLM has to context-switch.

2. Independent failure & retry — if the Summarizer hallucintates, we can
   re-invoke just that agent without re-running the expensive web search.

3. Tool isolation — the WebResearcher needs MCP web tools; the Summarizer
   needs none. Mixing tool sets in one agent confuses the model about when
   to call what. Separate agents have clean tool namespaces.

WHY AgentTool (not sub_agents=[]) for A2A delegation?
------------------------------------------------------
sub_agents=[] causes automatic delegation based on the LLM's routing
decision, which is non-deterministic. AgentTool wraps each agent as an
explicit callable tool, so the orchestrator's instruction can enforce strict
ordering: "call web_researcher FIRST, then summarizer, then notebooklm_agent."
The orchestrator controls the pipeline sequencing, not the model's whims.

Architecture:
    Orchestrator (ADK root)
        ├─ AgentTool(web_researcher)   — MCP stdio → DuckDuckGo + httpx
        ├─ AgentTool(summarizer)       — LLM-only, no tools
        └─ AgentTool(notebooklm_agent) — Python FunctionTool (mock)
"""

from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

from agents.config import MODEL
from agents.notebooklm_agent import create_notebooklm_agent
from agents.summarizer import create_summarizer
from agents.web_researcher import create_web_researcher

INSTRUCTION = """You are the Research Crew Orchestrator — a senior research coordinator.

When given a research topic, you MUST follow these steps IN ORDER. Do not skip any step.

STEP 1 — Gather raw data:
  Call the web_researcher tool, passing the research topic as input.
  Wait for it to return a JSON object with sources and raw findings.

STEP 2 — Structure findings:
  Call the summarizer tool, passing the COMPLETE JSON output from Step 1 as input.
  Wait for it to return a structured markdown research brief.

STEP 3 — Enrich with NotebookLM:
  Call the notebooklm_agent tool, passing the COMPLETE markdown brief from Step 2 as input.
  Wait for it to return the enriched document (brief + notebook URL + podcast excerpt + FAQ).

STEP 4 — Return final document:
  Return the complete enriched document from Step 3 to the user, unmodified.

Critical rules:
- ALWAYS call all three sub-agents, even if earlier results look incomplete.
- Pass the COMPLETE output of each step as input to the next step.
- Do NOT generate research yourself — delegate everything to the sub-agents.
"""


def create_orchestrator() -> Agent:
    """
    Synchronous factory — creates all sub-agents and the orchestrator.

    WHY synchronous (was async before)?
    ------------------------------------
    Now that McpToolset is constructed synchronously (see web_researcher.py),
    there's no async setup work to do anywhere in the agent graph. Making this
    sync means the caller (Gradio) can build the orchestrator inline before
    handing off to run_async(). Simpler call chain, no spurious event loops.
    """
    web_researcher = create_web_researcher()
    summarizer = create_summarizer()
    notebooklm = create_notebooklm_agent()

    return Agent(
        name="orchestrator",
        model=MODEL,
        description="Coordinates the Research Crew pipeline: research -> summarise -> NotebookLM.",
        instruction=INSTRUCTION,
        tools=[
            # WHY AgentTool? It exposes each agent as a named, callable tool.
            # The orchestrator's LLM sees three tools in its function registry:
            #   web_researcher(input), summarizer(input), notebooklm_agent(input)
            # and its instruction tells it exactly when to call each one.
            AgentTool(agent=web_researcher),
            AgentTool(agent=summarizer),
            AgentTool(agent=notebooklm),
        ],
    )
