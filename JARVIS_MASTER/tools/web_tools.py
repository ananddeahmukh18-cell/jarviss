"""Internet search & fetch utilities for JARVIS."""
from __future__ import annotations
import urllib.parse
from typing import Any
import requests

try:    from duckduckgo_search import DDGS; _DDG = True
except: _DDG = False

def web_search(query: str, max_results: int = 6) -> str:
    if not _DDG: return "❌ duckduckgo-search not installed"
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results: return f"🔍 No results for '{query}'"
        lines = [f"🌐 Results for: \"{query}\"\n"]
        for i, r in enumerate(results, 1):
            lines.append(f"  [{i}] {r.get('title','')}\n       {r.get('href','')}\n       {r.get('body','')[:200]}\n")
        return "\n".join(lines)
    except Exception as e: return f"❌ Search failed: {e}"

def fetch_url(url: str, timeout: int = 10) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        from html.parser import HTMLParser
        class _T(HTMLParser):
            def __init__(self): super().__init__(); self._p=[]; self._s=False
            def handle_starttag(self,t,a):
                if t in ("script","style","head","nav","footer"): self._s=True
            def handle_endtag(self,t):
                if t in ("script","style","head","nav","footer"): self._s=False
            def handle_data(self,d):
                if not self._s and d.strip(): self._p.append(d.strip())
            def text(self): return " ".join(self._p)
        p = _T(); p.feed(resp.text)
        return f"📄 {url}:\n\n{p.text()[:5000]}\n\n[truncated]"
    except Exception as e: return f"❌ Fetch failed: {e}"

def get_weather(location: str) -> str:
    try:
        r = requests.get(f"https://wttr.in/{urllib.parse.quote(location)}?format=4", timeout=8)
        r.raise_for_status()
        return f"🌤️  {location}:\n{r.text.strip()}"
    except Exception as e: return f"❌ Weather failed: {e}"

def get_ip_info() -> str:
    try:
        d: dict = requests.get("https://ipinfo.io/json", timeout=6).json()
        return (f"🌍 Network:\n   IP: {d.get('ip')}\n   City: {d.get('city')}\n"
                f"   Country: {d.get('country')}\n   ISP: {d.get('org')}")
    except Exception as e: return f"❌ IP info failed: {e}"
