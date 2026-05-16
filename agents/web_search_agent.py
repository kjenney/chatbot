"""
Web Search Agent
Performs web searches using DuckDuckGo via ddgs library
"""

from typing import Dict, Any
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
        Perform a web search

        Args:
            query: Search query
            max_results: Maximum number of results to return
        """
        try:
            from ddgs import DDGS
            with DDGS() as d:
                hits = list(d.text(query, max_results=max_results))

            results = {
                'query': query,
                'abstract': hits[0]['body'] if hits else '',
                'abstract_source': hits[0]['title'] if hits else '',
                'abstract_url': hits[0]['href'] if hits else '',
                'related_topics': [
                    {'text': f"{h['title']}: {h['body']}", 'url': h['href']}
                    for h in hits
                ]
            }

            return {'success': True, 'data': results}
        except Exception as e:
            return {'success': False, 'error': f"Search failed: {str(e)}"}
