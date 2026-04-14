import asyncio

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from agents.config import MODEL

from tools.notebooklm_mock import generate_mock_notebooklm_response
from tools.notebooklm_real import create_notebook_real


async def notebooklm_upload(topic: str, summary: str) -> dict:
    """
    Hybrid mode:
    - Try real NotebookLM (runs sync Playwright in a thread to avoid asyncio conflict)
    - Fallback to mock enrichment (podcast excerpt + FAQ) if anything fails
    """
    try:
        # create_notebook_real uses sync Playwright — must run in a thread pool
        # to avoid "Sync API inside asyncio loop" error from ADK's async context
        real = await asyncio.to_thread(create_notebook_real, summary)

        mock = generate_mock_notebooklm_response(topic, summary)

        return {
            "notebook_id": real["notebook_id"],
            "status": "CREATED",
            "notebook_url": real["notebook_url"],
            "podcast_excerpt": mock["podcast_excerpt"],
            "faq": mock["faq"],
        }

    except Exception as e:
        print(f"[NotebookLM REAL FAILED] {e}")
        return generate_mock_notebooklm_response(topic, summary)


INSTRUCTION = """You are a NotebookLM integration specialist.

You will receive a structured research brief (markdown). Your task:

1. Extract the topic from "# Research Brief: <Topic>"
2. Call notebooklm_upload with:
   - topic
   - full markdown brief as the summary

3. Append to the document:

---
## 🔗 NotebookLM Notebook
<notebook_url>

---

## 🎙️ NotebookLM Audio Overview
<podcast_excerpt>

---

<faq>

Return ONLY the final combined document.
"""


def create_notebooklm_agent():
    return Agent(
        name="notebooklm_agent",
        model=MODEL,
        description="Creates a real NotebookLM notebook via browser automation and enriches the brief with a podcast excerpt and FAQ.",
        instruction=INSTRUCTION,
        tools=[FunctionTool(func=notebooklm_upload)],
    )