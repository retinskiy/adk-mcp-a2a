"""
NotebookLM Mock Tool
====================
Simulates the NotebookLM Enterprise API response.

HOW REAL NotebookLM ENTERPRISE API WOULD WORK:
-----------------------------------------------
1. Authenticate via Google Cloud service account (OAuth2, scope: cloud-platform).
2. POST to https://notebooklm.googleapis.com/v1/notebooks
   with JSON body: {"sources": [{"text": "<your_summary>"}]}
3. Poll GET /v1/notebooks/{id}/operations until status == "DONE".
4. POST /v1/notebooks/{id}/audio_overview:generate to trigger podcast generation.
5. Poll until audio is ready, then retrieve the transcript and audio URL.

Because the NotebookLM public API is in limited preview, this mock returns
realistic-looking output so the demo works end-to-end without credentials.

See also: https://notebooklm.google.com/notebook/31e70cf0-e72b-450d-8ac5-883f0b8636bc
"""


def generate_mock_notebooklm_response(topic: str, summary: str) -> dict:
    """Return a mock NotebookLM-style response containing a podcast excerpt and FAQ."""
    podcast_excerpt = f"""
🎙️ **AI Podcast Excerpt** *(NotebookLM Audio Overview — simulated)*

**Host A:** Welcome back! Today we're diving deep into *{topic}*. I have to say,
after reading through all these sources, there are some genuinely surprising angles here.

**Host B:** Absolutely. What struck me first is how rapidly this space is evolving.
The research shows that the core developments aren't happening in isolation — they're
feeding into each other in ways that weren't obvious even two years ago.

**Host A:** Right, and the summary really crystallised it: the key players are racing
to establish standards, but the community seems to be one step ahead with open
implementations.

**Host B:** Exactly. And for anyone listening who's new to this, the short version is:
{topic[:100]}{'...' if len(topic) > 100 else ''} is becoming a foundational piece of
the infrastructure stack — not just a niche tool.

**Host A:** We'll link to all the sources in the notebook. Next week we're covering
practical applications. Stay curious!
""".strip()

    faq = f"""
## Frequently Asked Questions

**Q1: What is the single most important takeaway about {topic}?**
A: Based on the research, the defining characteristic is rapid adoption driven by
both open-source momentum and enterprise investment, creating a compounding effect
on tooling maturity.

**Q2: What are the main risks or challenges?**
A: Fragmentation of standards, security surface area expansion, and the skills gap
in organisations trying to adopt quickly without foundational knowledge.

**Q3: Who are the key contributors or organisations to watch?**
A: The research highlights both hyperscaler platforms and independent open-source
communities as co-drivers — neither alone is sufficient.

**Q4: How should a developer or team get started?**
A: Start with the official documentation of the primary framework, build a small
proof-of-concept, then evaluate integration points with existing infrastructure
before committing to a production path.

**Q5: Where can I go deeper?**
A: The sources collected in this research brief are a strong starting point.
The NotebookLM notebook contains all source material with inline citations
and supports audio overviews generated directly from the uploaded content.
""".strip()

    return {
        "notebook_id": "31e70cf0-e72b-450d-8ac5-883f0b8636bc",
        "status": "COMPLETED",
        "podcast_excerpt": podcast_excerpt,
        "faq": faq,
    }
