"""
Web Search Agent
Performs web searches using DuckDuckGo API
"""

from typing import Dict, Any
import requests
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
            # Using DuckDuckGo Instant Answer API (no key needed)
            url = "https://api.duckduckgo.com/"
            params = {
                'q': query,
                'format': 'json',
                'no_html': 1,
                'skip_disambig': 1
            }

            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()

            results = {
                'query': query,
                'abstract': data.get('Abstract', ''),
                'abstract_source': data.get('AbstractSource', ''),
                'abstract_url': data.get('AbstractURL', ''),
                'related_topics': []
            }

            # Add related topics
            for topic in data.get('RelatedTopics', [])[:max_results]:
                if 'Text' in topic:
                    results['related_topics'].append({
                        'text': topic.get('Text', ''),
                        'url': topic.get('FirstURL', '')
                    })

            return {
                'success': True,
                'data': results
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Search failed: {str(e)}"
            }
