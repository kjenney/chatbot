"""
Web Search Agent
Performs web searches using DuckDuckGo via ddgs library
"""

from typing import Dict, Any, List, Optional
from agents.base_agent import BaseAgent


class WebSearchAgent(BaseAgent):
    """Sub-agent to perform web searches"""

    def __init__(self):
        super().__init__(
            name="web_search",
            description="Searches the web for information using DuckDuckGo"
        )

    def execute(self, query: str, max_results: int = 5, **kwargs) -> Dict[str, Any]:
        """
        Perform a web search combining news and text results,
        with full-content fetch for the most relevant hit.

        Args:
            query: Search query (may include year suffix for text search)
            max_results: Maximum number of results to return
        """
        try:
            from ddgs import DDGS
            import re
            hits: List[Dict] = []

            # Strip trailing year for news — news is already recent
            news_query = re.sub(r'\s+\d{4}$', '', query).strip()

            with DDGS() as d:
                # News first — more current for real-time queries
                try:
                    for h in d.news(news_query, max_results=3):
                        hits.append({
                            'title': h.get('title', ''),
                            'body': h.get('body', ''),
                            'href': h.get('url', ''),
                            'date': h.get('date', '')[:10],
                        })
                except Exception:
                    pass

                # Text search fills the rest
                for h in d.text(query, max_results=max_results):
                    hits.append({
                        'title': h.get('title', ''),
                        'body': h.get('body', ''),
                        'href': h.get('href', ''),
                        'date': '',
                    })

            # Deduplicate by title prefix
            seen: set = set()
            unique: List[Dict] = []
            for h in hits:
                key = h['title'][:40]
                if key not in seen:
                    seen.add(key)
                    unique.append(h)

            unique = unique[:max_results]

            # Prefer Wikipedia URLs (static HTML, reliable content) over JS-heavy news sites
            wiki_hits = [h for h in unique if 'wikipedia.org' in h.get('href', '')]
            news_hits = sorted(
                [h for h in unique if h.get('date') and 'wikipedia.org' not in h.get('href', '')],
                key=lambda h: h['date'],
                reverse=True,
            )
            fetch_order = wiki_hits + news_hits

            full_content: Optional[str] = None
            for h in fetch_order:
                if h.get('href'):
                    full_content = self._fetch_page_text(h['href'], max_chars=2000)
                    if full_content:
                        break

            topics = []
            for h in unique:
                label = f"[{h['date']}] " if h.get('date') else ''
                topics.append({
                    'text': f"{label}{h['title']}: {h['body']}",
                    'url': h['href'],
                })

            # Prepend full article content so LLM sees the most detailed source first
            abstract = ''
            if full_content:
                abstract = f"FULL ARTICLE CONTENT:\n{full_content}"
            elif topics:
                abstract = topics[0]['text']

            results = {
                'query': query,
                'abstract': abstract,
                'abstract_source': unique[0]['title'] if unique else '',
                'abstract_url': unique[0]['href'] if unique else '',
                'related_topics': topics,
            }

            return {'success': True, 'data': results}
        except Exception as e:
            return {'success': False, 'error': f"Search failed: {str(e)}"}

    def _fetch_page_text(self, url: str, max_chars: int = 1500) -> Optional[str]:
        """Fetch a URL and return cleaned plain text."""
        try:
            import requests
            from html.parser import HTMLParser

            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                              'AppleWebKit/537.36 (KHTML, like Gecko) '
                              'Chrome/120.0.0.0 Safari/537.36'
            }
            r = requests.get(url, headers=headers, timeout=8)
            if r.status_code != 200:
                return None

            class TextExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.chunks: List[str] = []
                    self._skip = False

                def handle_starttag(self, tag, attrs):
                    if tag in ('script', 'style', 'nav', 'footer', 'header'):
                        self._skip = True

                def handle_endtag(self, tag):
                    if tag in ('script', 'style', 'nav', 'footer', 'header'):
                        self._skip = False

                def handle_data(self, data):
                    if not self._skip:
                        text = data.strip()
                        if len(text) > 20:
                            self.chunks.append(text)

            parser = TextExtractor()
            parser.feed(r.text)
            text = ' '.join(parser.chunks)
            # Collapse whitespace
            import re
            text = re.sub(r'\s+', ' ', text).strip()
            return text[:max_chars] if text else None
        except Exception:
            return None
