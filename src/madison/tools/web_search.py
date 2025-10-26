"""Web search functionality for Madison."""

import logging
from typing import List

from ddgs import DDGS

from madison.exceptions import MadisonError

logger = logging.getLogger(__name__)


class WebSearcher:
    """Perform web searches using DuckDuckGo."""

    def __init__(self, max_results: int = 5):
        """Initialize web searcher.

        Args:
            max_results: Maximum number of results to return
        """
        self.max_results = max_results

    async def search(self, query: str) -> str:
        """Perform a web search.

        Args:
            query: Search query

        Returns:
            str: Formatted search results

        Raises:
            MadisonError: If search fails
        """
        try:
            if not query or not query.strip():
                raise MadisonError("Search query cannot be empty")

            logger.info(f"Searching for: {query}")

            # Use synchronous search in a try-except
            results = DDGS().text(query, max_results=self.max_results)

            if not results:
                return "[yellow]No results found for your search.[/yellow]"

            output = "[bold]Search Results:[/bold]\n\n"

            for i, result in enumerate(results, 1):
                title = result.get("title", "Untitled")
                link = result.get("href", "")
                snippet = result.get("body", "")

                output += f"[bold cyan]{i}. {title}[/bold cyan]\n"
                if link:
                    output += f"[dim]{link}[/dim]\n"
                if snippet:
                    output += f"{snippet[:200]}"
                    if len(snippet) > 200:
                        output += "..."
                output += "\n\n"

            return output

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise MadisonError(f"Search failed: {e}") from e
