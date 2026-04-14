"""
NotebookLM Real Integration (Browser Automation via CDP)
=========================================================

Connects to your already-running Chrome (with remote debugging enabled)
to create a real NotebookLM notebook, add sources, and trigger Audio Overview.

SETUP (one-time):
-----------------
1. Launch Chrome with the debug flag:
   chrome.exe --remote-debugging-port=9222 --user-data-dir="%USERPROFILE%/chrome-debug-profile"

2. Log in to NotebookLM in that Chrome window, leave it running.

3. Verify: python tools/save_google_auth.py
"""

import re
import time
import uuid

from playwright.sync_api import Page, sync_playwright

NOTEBOOKLM_URL = "https://notebooklm.google.com/"
CDP_URL = "http://127.0.0.1:9222"
MAX_URL_SOURCES = 5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_source_urls(markdown: str) -> list[str]:
    """Parse URLs from the markdown Sources table produced by the Summarizer."""
    return re.findall(r"https?://[^\s|)>\"]+", markdown)[:MAX_URL_SOURCES]


def _open_source_dialog(page: Page) -> None:
    """Click 'Add source' to open the source picker dialog."""
    for selector in [
        "[aria-label='Add source']",
        "button:has-text('Add source')",
        "text=Add source",
    ]:
        try:
            page.click(selector, timeout=8000)
            time.sleep(1)
            return
        except Exception:
            continue
    raise RuntimeError("Could not find 'Add source' button.")


def _add_text_source(page: Page, text: str, dialog_already_open: bool = False) -> None:
    """
    Add the research brief as a 'Copied text' source.

    dialog_already_open: set True right after notebook creation, when NotebookLM
    opens the source picker automatically — no need to click 'Add source' first.
    """
    if not dialog_already_open:
        _open_source_dialog(page)

    for selector in [
        "text=Copied text",
        "text=Copy and paste text",
        "[aria-label*='copied' i]",
        "[aria-label*='paste' i]",
    ]:
        try:
            page.click(selector, timeout=5000)
            break
        except Exception:
            continue

    time.sleep(0.8)
    textarea = page.get_by_placeholder("Paste text here")
    textarea.wait_for(timeout=10000)
    textarea.fill(text[:20000])

    try:
        page.get_by_role("button", name="Insert").click(timeout=10000)
    except Exception:
        page.click("button:has-text('Insert')", timeout=10000)

    try:
        textarea.wait_for(state="hidden", timeout=20000)
    except Exception:
        time.sleep(3)

    print("[NotebookLM] Text source added.")


def _add_url_sources(page: Page, urls: list[str]) -> bool:
    """
    Add all URLs at once via the 'Websites' option.
    NotebookLM accepts multiple URLs separated by newlines in one dialog session.
    Returns True on success.
    """
    if not urls:
        return False

    try:
        _open_source_dialog(page)

        websites_btn = page.get_by_role("button", name="Websites")
        websites_btn.wait_for(state="visible", timeout=8000)
        websites_btn.click()
        time.sleep(0.8)

        # Textarea with placeholder "Paste any links"
        url_field = page.get_by_placeholder("Paste any links")
        url_field.wait_for(state="visible", timeout=8000)
        url_field.fill("\n".join(urls))
        time.sleep(0.3)

        page.get_by_role("button", name="Insert").click(timeout=8000)
        time.sleep(2)
        print(f"[NotebookLM] {len(urls)} URL source(s) added.")
        return True

    except Exception as e:
        print(f"[NotebookLM] URL sources failed: {e}")
        try:
            page.keyboard.press("Escape")
            time.sleep(0.5)
        except Exception:
            pass
        return False


def _trigger_audio_overview(page: Page) -> bool:
    """
    Trigger Audio Overview generation.

    NotebookLM flow:
      1. Click 'Generate' in the Studio panel → opens 'Customise Audio Overview' dialog
      2. Click 'Generate' inside the dialog → actually starts generation

    Fire and forget — returns True if generation was started.
    """
    time.sleep(2)

    triggered = False
    for selector in [
        "button:has-text('Generate')",
        "[aria-label*='Generate audio' i]",
        "[aria-label*='audio overview' i]",
    ]:
        try:
            btn = page.locator(selector).first
            btn.wait_for(state="visible", timeout=5000)
            btn.click()
            triggered = True
            break
        except Exception:
            continue

    if not triggered:
        print("[NotebookLM] Audio Overview Generate button not found — skipping.")
        return False

    # The 'Customise Audio Overview' dialog opens — click Generate inside it
    time.sleep(2)

    # Use JS to click — bypasses overlay/shadow DOM issues
    clicked = page.evaluate("""
        () => {
            const btns = Array.from(document.querySelectorAll('button'));
            const generate = btns.filter(b => b.innerText.toLowerCase().includes('generate')).at(-1);
            if (generate) { generate.click(); return true; }
            return false;
        }
    """)

    if clicked:
        print("[NotebookLM] Audio Overview generation started.")
        return True

    print("[NotebookLM] Could not confirm audio generation dialog.")
    return False


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def create_notebook_real(summary: str) -> dict:
    """
    Creates a real NotebookLM notebook via CDP connection to running Chrome.

    Flow:
      1. Open NotebookLM and create a new notebook
      2. Add the research brief as a text source
      3. Add source URLs extracted from the brief (all at once via Websites dialog)
      4. Trigger Audio Overview generation (fire and forget)

    NOTE: Uses sync Playwright. Call via asyncio.to_thread() from async contexts.
    """
    notebook_id = str(uuid.uuid4())[:8]
    source_urls = _extract_source_urls(summary)

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP_URL)
        context = browser.contexts[0]
        page = context.new_page()

        # ── 1. Open NotebookLM ────────────────────────────────────────────────
        page.goto(NOTEBOOKLM_URL, timeout=60000)
        page.wait_for_load_state("networkidle", timeout=30000)

        # ── 2. Create new notebook ────────────────────────────────────────────
        try:
            page.get_by_role("button", name="New notebook").click(timeout=10000)
        except Exception:
            try:
                page.click("text=New notebook", timeout=10000)
            except Exception:
                page.click("button:has-text('New')", timeout=10000)

        page.wait_for_url(lambda url: url != NOTEBOOKLM_URL, timeout=20000)
        notebook_url = page.url
        page.wait_for_load_state("networkidle", timeout=20000)

        # ── 3. Add text source ────────────────────────────────────────────────
        # The source picker dialog opens automatically after notebook creation
        _add_text_source(page, summary, dialog_already_open=True)

        # ── 4. Add URL sources (via Add source → Websites) ────────────────────
        urls_added = _add_url_sources(page, source_urls)

        # ── 5. Trigger Audio Overview ─────────────────────────────────────────
        audio_triggered = _trigger_audio_overview(page)

        # Give NotebookLM time to send the generation request before closing the tab
        if audio_triggered:
            time.sleep(4)

        page.close()

        return {
            "notebook_id": notebook_id,
            "notebook_url": notebook_url,
            "status": "CREATED",
            "audio_overview_triggered": audio_triggered,
            "url_sources_added": len(source_urls) if urls_added else 0,
        }
