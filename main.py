"""
Research Crew — Entry Point
===========================
Loads .env, suppresses known non-actionable warnings, prints a welcome
banner, then builds and launches the Gradio UI.

Usage:
    python main.py
"""

import os
import warnings

# Suppress the ADK PLUGGABLE_AUTH experimental feature banner.
# This is an internal ADK feature flag, not user-actionable.
warnings.filterwarnings("ignore", category=UserWarning, module="google.adk")

# Load .env BEFORE importing any Google/ADK modules so that GOOGLE_API_KEY
# is in os.environ when the SDK initialises.
from dotenv import load_dotenv
load_dotenv()

BANNER = """
+--------------------------------------------------------------+
|           Research Crew  --  ADK + MCP + A2A                |
+--------------------------------------------------------------+
|  Architecture:                                               |
|    Orchestrator (ADK)                                        |
|      +- A2A -> WebResearcher  (MCP: search_web, fetch_url)  |
|      +- A2A -> Summarizer     (LLM: structures findings)    |
|      +- A2A -> NotebookLM     (Real notebook + FAQ)         |
+--------------------------------------------------------------+
|  Model  : gemini-2.5-flash  (Vertex AI)                      |
|  UI     : Gradio 6 (async streaming log)                     |
|  Server : http://localhost:7860                              |
+--------------------------------------------------------------+
"""


def main() -> None:
    use_vertex = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower() in ("1", "true", "yes")
    if use_vertex:
        project = os.getenv("GOOGLE_CLOUD_PROJECT", "(not set)")
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        print(f"Backend: Vertex AI  |  project={project}  |  location={location}")
        print("  Credentials: gcloud Application Default Credentials")
        print("  Run 'gcloud auth application-default login' if not done yet.\n")
    else:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("WARNING: GOOGLE_API_KEY not set.")
            print("  Copy .env.example -> .env and add your Gemini API key.")
            print("  Get one free at: https://aistudio.google.com/apikey\n")
        else:
            print(f"Backend: Gemini API  |  key={api_key[:8]}...")

    print(BANNER)

    # Deferred import so .env is loaded before any ADK SDK initialisation
    # (ADK reads GOOGLE_API_KEY at import time in some versions).
    from ui.gradio_app import CSS, build_app

    app = build_app()

    # In Gradio 6, theme and css belong in launch(), not Blocks().
    # WHY theme=gr.themes.Default()?
    #   The built-in themes are stable across Gradio minor versions.
    #   Soft is readable with the monospace log panel.
    import gradio as gr
    app.launch(
        server_name="0.0.0.0",  # bind to all interfaces so it's reachable in Docker
        server_port=7860,
        share=False,
        theme=gr.themes.Soft(),
        css=CSS,
        quiet=True,             # suppress Gradio's verbose startup output
    )


if __name__ == "__main__":
    main()
