"""
Gradio UI — Research Crew
=========================
Dark-themed Gradio 6 interface with live streaming of agent activity.

WHY Gradio instead of a raw FastAPI/Streamlit app?
---------------------------------------------------
Gradio 6 natively supports async generator functions as event handlers.
This means runner.run_async() — which is an AsyncGenerator[Event, None] —
maps directly onto Gradio's streaming model: yield partial (log, brief) pairs
and the UI updates after each yield without any threading or queue gymnastics.

WHY async generator (not a sync function with threads)?
-------------------------------------------------------
ADK's Runner.run_async() is a true async generator. If we called it from a
sync function we'd need asyncio.run() which can't be called inside an already-
running loop (Gradio runs its own event loop). An async def handler function
in Gradio 6 runs inside that loop directly — no bridging needed.
"""

import traceback

from dotenv import load_dotenv
load_dotenv()

import gradio as gr
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from agents.orchestrator import create_orchestrator

APP_NAME = "research_crew"

# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


async def run_research(topic: str):
    """
    Async generator — the Gradio event handler for the Run button.

    Yields (log_text: str, brief_text: str) pairs as the pipeline progresses.
    Gradio updates both output components after every yield, giving the user
    a live view of what each agent is doing.

    WHY yield after every meaningful event, not just at the end?
    ------------------------------------------------------------
    Research runs take 20-60 seconds. Without incremental updates the UI
    looks frozen. Streaming each agent's tool calls and responses keeps the
    user informed and makes the A2A + MCP delegation visible — which is the
    whole point of the demo.
    """
    if not topic or not topic.strip():
        yield "Please enter a research topic.", ""
        return

    topic = topic.strip()
    log_lines: list[str] = []
    brief = ""

    def _append(msg: str) -> str:
        """Append a line to the running log and return the full log string."""
        log_lines.append(msg)
        return "\n".join(log_lines)

    # --- Setup ---------------------------------------------------------------
    yield _append(f"Starting Research Crew for topic: {topic!r}"), brief
    yield _append("Building agent graph (Orchestrator + 3 sub-agents)..."), brief

    try:
        # create_orchestrator() is synchronous — it builds Agent objects and
        # attaches a McpToolset. No subprocess is started here yet.
        orchestrator = create_orchestrator()

        # InMemorySessionService stores conversation state in-process.
        # WHY not a persistent service? For a single-request demo, memory is
        # fine. In production use Firestore or Spanner-backed session services.
        session_service = InMemorySessionService()

        # Runner wires together the agent graph, session service, and the
        # event loop. It owns the execution lifecycle for one invocation.
        runner = Runner(
            agent=orchestrator,
            app_name=APP_NAME,
            session_service=session_service,
        )

        # create_session is async despite its return annotation showing -> Session.
        # iscoroutinefunction(InMemorySessionService.create_session) == True.
        session = await session_service.create_session(
            app_name=APP_NAME, user_id="demo_user"
        )

        yield _append("Agents ready. Sending request to orchestrator..."), brief

        # --- Event loop -------------------------------------------------------
        # runner.run_async() returns AsyncGenerator[Event, None].
        # Each Event represents one "turn" by any agent in the tree:
        #   - function_calls: the agent decided to call a tool/sub-agent
        #   - function_responses: a tool/sub-agent returned a result
        #   - final_response: the agent produced text with no pending calls
        #   - partial=True: a streaming text chunk (skip for cleaner log)

        async for event in runner.run_async(
            user_id="demo_user",
            session_id=session.id,
            new_message=Content(role="user", parts=[Part(text=topic)]),
        ):
            # Skip partial streaming chunks — they're intermediate LLM tokens,
            # not actionable events. We only want complete tool calls / responses.
            if event.partial:
                continue

            author = event.author or "system"

            # ── Tool / sub-agent calls ────────────────────────────────────────
            fn_calls = event.get_function_calls()
            if fn_calls:
                for fc in fn_calls:
                    # fc.name is the tool name (e.g. "web_researcher", "search_web")
                    yield _append(f"[{author}] --> calling {fc.name}()"), brief
                continue  # don't double-log this event below

            # ── Tool / sub-agent responses ────────────────────────────────────
            fn_responses = event.get_function_responses()
            if fn_responses:
                for fr in fn_responses:
                    yield _append(f"[{author}] <-- {fr.name}() returned"), brief
                continue

            # ── Final response from this agent ────────────────────────────────
            # is_final_response() is True when: not partial, no pending calls,
            # no pending responses. This fires once per agent per invocation.
            if event.is_final_response():
                # Collect text from all parts (ADK may split across parts)
                text = ""
                if event.content and event.content.parts:
                    text = "".join(
                        p.text for p in event.content.parts
                        if p.text  # Part.text can be None for non-text parts
                    )

                if author == "orchestrator":
                    # The root agent's final response IS the research brief.
                    brief = text
                    yield _append("Research complete!"), brief
                    return
                else:
                    # Sub-agent completed its step — log a preview.
                    preview = text[:120].replace("\n", " ")
                    yield _append(f"[{author}] done: {preview}..."), brief

    except Exception as exc:
        tb = traceback.format_exc()
        yield _append(f"Error: {exc}\n\n{tb}"), brief


# ---------------------------------------------------------------------------
# Gradio layout
# ---------------------------------------------------------------------------

ARCHITECTURE_DIAGRAM = """\
```
Research Crew — Agent Architecture
===================================================
  User Input
      |
      v
+---------------------------------------------------+
|          Orchestrator Agent  (ADK Root)           |
|              gemini-2.5-flash                 |
|  "Delegates all work to 3 sub-agents via A2A"     |
+--------+-----------------+-----------------+------+
         | A2A             | A2A             | A2A
         v                 v                 v
+----------------+ +----------------+ +----------------+
| WebResearcher  | |   Summarizer   | |  NotebookLM    |
|    Agent       | |     Agent      | |    Agent       |
|                | |                | |                |
| MCP Tools:     | |  LLM only --   | | FunctionTool:  |
|  search_web()  | |  raw JSON -->  | |  notebooklm_   |
|  fetch_url()   | |  markdown      | |  upload (real) |
+-------+--------+ +----------------+ +----------------+
        | stdio MCP protocol
        v
+----------------+
|   MCP Server   |
| web_tools.py   |
| DuckDuckGo +   |
| httpx + BS4    |
+----------------+
```
"""

EXAMPLES = [
    ["Google Agent Development Kit (ADK)"],
    ["Model Context Protocol (MCP) for AI agents"],
    ["Agent-to-Agent (A2A) communication patterns"],
    ["Retrieval-Augmented Generation in production"],
]

# CSS for monospace log panel — passed to launch() in Gradio 6, not Blocks().
# WHY moved to launch()? Gradio 6 raised the warning:
#   "theme, css have been moved from Blocks() to launch()"
CSS = """
.log-panel textarea { font-family: 'Courier New', monospace; font-size: 13px; }
"""


def build_app() -> gr.Blocks:
    """
    Build and return the Gradio Blocks app (does NOT launch it).

    WHY separate build_app() from launch()?
    ----------------------------------------
    Keeps the UI construction testable without starting a server.
    main.py owns the launch() call so it can configure host/port/theme
    in one place without Gradio printing its startup banner during imports.
    """
    with gr.Blocks(
        title="Research Crew — ADK + MCP + A2A Demo",
        # WHY NOT theme= here? Gradio 6 moved theme/css to launch().
        # Putting them in Blocks() still works but emits a deprecation warning.
    ) as app:
        gr.Markdown("# Research Crew\n### ADK + MCP + A2A Multi-Agent Pipeline Demo")
        gr.Markdown(ARCHITECTURE_DIAGRAM)

        with gr.Row():
            topic_input = gr.Textbox(
                label="Research Topic",
                placeholder="e.g. Google Agent Development Kit (ADK)",
                scale=4,
            )
            run_btn = gr.Button("Run Research Crew", variant="primary", scale=1)

        gr.Examples(examples=EXAMPLES, inputs=topic_input)

        with gr.Row():
            with gr.Column(scale=1):
                log_output = gr.Textbox(
                    label="Agent Activity Log",
                    lines=20,
                    max_lines=40,
                    interactive=False,
                    elem_classes=["log-panel"],
                )
            with gr.Column(scale=2):
                brief_output = gr.Markdown(
                    label="Research Brief",
                    value="*Your research brief will appear here...*",
                )

        # Both button click and Enter key trigger the same async generator.
        # Gradio streams each yielded (log, brief) pair to the UI in real time.
        run_btn.click(
            fn=run_research,
            inputs=topic_input,
            outputs=[log_output, brief_output],
        )
        topic_input.submit(
            fn=run_research,
            inputs=topic_input,
            outputs=[log_output, brief_output],
        )

    return app
