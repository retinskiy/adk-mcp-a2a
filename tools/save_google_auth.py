"""
Run this ONCE to verify your Chrome debug setup.

1. Open Chrome manually with the debug port:
   "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222

2. Log in to NotebookLM in that Chrome window.

3. Run this script to verify the connection works:
   python tools/save_google_auth.py
"""

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    try:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        pages = browser.contexts[0].pages if browser.contexts else []
        print(f"✅ Connected to Chrome. Open tabs: {len(pages)}")
        for page in pages:
            print(f"   - {page.url}")
        browser.close()
    except Exception as e:
        print(f"❌ Could not connect: {e}")
        print("\nMake sure Chrome is running with:")
        print('  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222')
