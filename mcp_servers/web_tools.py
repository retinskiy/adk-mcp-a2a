"""
MCP Server: web_tools
Exposes two tools over the Model Context Protocol (stdio transport):
  - search_web(query)  — DuckDuckGo text search, returns top-5 results as JSON
  - fetch_url(url)     — Fetches a URL, strips HTML, returns first 2000 chars

Run standalone:
    python -m mcp_servers.web_tools
or:
    python mcp_servers/web_tools.py

The web_researcher ADK agent connects to this server via MCPToolset + StdioServerParameters.
"""

import json
import re
import sys

import httpx
from bs4 import BeautifulSoup
from ddgs import DDGS
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("web-tools")


@mcp.tool()
def search_web(query: str) -> str:
    """Search the web using DuckDuckGo. Returns top 5 results as a JSON array.

    Each result has keys: title, href, body.
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
        return json.dumps(results, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@mcp.tool()
def fetch_url(url: str) -> str:
    """Fetch the content of a URL and return plain text (first 2000 characters).

    Strips HTML tags, scripts, and styles before returning.
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; ResearchCrew/1.0)"}
        with httpx.Client(follow_redirects=True, timeout=15) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r"\s{2,}", " ", text)
        return text[:2000]
    except Exception as exc:
        return f"Error fetching {url}: {exc}"


if __name__ == "__main__":
    mcp.run()
