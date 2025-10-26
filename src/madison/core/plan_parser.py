"""Parser for extracting plans from AI model responses."""

import logging
import re
from typing import List, Optional, Tuple

from madison.core.plan import ActionType, Plan, PlanAction

logger = logging.getLogger(__name__)


class PlanParser:
    """Parse plans from AI model responses."""

    # Strict patterns - only match backtick-delimited commands
    # These extract the command from within backticks
    EXEC_PATTERNS = [
        r"`([^`]+)`",  # Match anything in backticks
    ]

    # File path patterns - be more specific to avoid false positives
    READ_PATTERNS = [
        r"read(?:\s+file)?:?\s*`([^`]+)`",  # read: `path`
        r"read(?:\s+file)?:?\s+([/\w\.\-]+)",  # read: /path/to/file
    ]

    WRITE_PATTERNS = [
        r"write(?:\s+file)?:?\s*`([^`]+)`",  # write: `path`
        r"(?:write|create)(?:\s+file)?:?\s+([/\w\.\-]+)",  # write/create: /path/to/file
    ]

    SEARCH_PATTERNS = [
        r"search:?\s*`([^`]+)`",  # search: `query`
        r"(?:web\s+)?search:?\s+(.+?)(?:\n|$)",  # search: query (to end of line)
    ]

    @classmethod
    def extract_actions(cls, response: str) -> List[PlanAction]:
        """Extract actions from an AI response.

        Looks for structured action descriptions in the response and converts them
        to PlanAction objects. The AI should express actions using patterns like:
        - "`mkdir foo`" (backtick-delimited command)
        - "read: `path/to/file`"
        - "search: `query`"

        Args:
            response: AI model response

        Returns:
            List of extracted PlanAction objects
        """
        actions = []
        seen_commands = set()  # Track seen commands to avoid duplicates

        # Look for exec commands - extract from backticks first
        # Only treat as command if it looks like a shell command
        for pattern in cls.EXEC_PATTERNS:
            matches = re.finditer(pattern, response, re.IGNORECASE)
            for match in matches:
                command = match.group(1).strip() if match.lastindex and match.lastindex >= 1 else match.group(0).strip()

                # Skip if empty, looks like a file path, or we've seen it before
                if not command or "/" in command or command in seen_commands:
                    continue

                # Only add if it looks like a shell command (not just a word)
                if " " in command or any(char in command for char in ["$", "-", ";"]):
                    seen_commands.add(command)
                    actions.append(
                        PlanAction(
                            type=ActionType.EXEC,
                            command=command,
                            description=f"Execute: {command}",
                        )
                    )

        # Look for read operations
        seen_reads = set()
        for pattern in cls.READ_PATTERNS:
            matches = re.finditer(pattern, response, re.IGNORECASE)
            for match in matches:
                if not match.groups():
                    continue
                file_path = match.group(1).strip()
                # Skip if empty, already seen, or preceded by "write"
                if (
                    not file_path
                    or file_path in seen_reads
                    or "write" in response[max(0, match.start() - 20) : match.start()].lower()
                ):
                    continue
                seen_reads.add(file_path)
                actions.append(
                    PlanAction(
                        type=ActionType.READ,
                        file_path=file_path,
                        description=f"Read file: {file_path}",
                    )
                )

        # Look for write operations
        seen_writes = set()
        for pattern in cls.WRITE_PATTERNS:
            matches = re.finditer(pattern, response, re.IGNORECASE)
            for match in matches:
                if not match.groups():
                    continue
                file_path = match.group(1).strip()
                if not file_path or file_path in seen_writes:
                    continue
                seen_writes.add(file_path)
                actions.append(
                    PlanAction(
                        type=ActionType.WRITE,
                        file_path=file_path,
                        description=f"Write file: {file_path}",
                    )
                )

        # Look for searches
        seen_searches = set()
        for pattern in cls.SEARCH_PATTERNS:
            matches = re.finditer(pattern, response, re.IGNORECASE)
            for match in matches:
                if not match.groups():
                    continue
                query = match.group(1).strip()
                if not query or query in seen_searches:
                    continue
                seen_searches.add(query)
                actions.append(
                    PlanAction(
                        type=ActionType.SEARCH,
                        query=query,
                        description=f"Search: {query}",
                    )
                )

        return actions

    @classmethod
    def build_plan(
        cls, response: str, reasoning: str = "", description: str = ""
    ) -> Optional[Plan]:
        """Build a plan from an AI response.

        Args:
            response: AI model response
            reasoning: Explanation of why this plan is needed
            description: High-level summary of the plan

        Returns:
            Plan object if actions were found, None otherwise
        """
        actions = cls.extract_actions(response)

        if not actions:
            return None

        # Use provided description or generate from response
        if not description:
            # Try to extract first sentence as description
            sentences = response.split(". ")
            description = sentences[0] if sentences else "Execute plan"

        if not reasoning:
            reasoning = "Performing requested actions"

        return Plan(
            reasoning=reasoning,
            description=description,
            actions=actions,
        )

    @classmethod
    def extract_action_details(cls, action: PlanAction, response: str) -> PlanAction:
        """Extract additional details for an action from the response.

        For write operations, tries to find content in the response.
        For complex operations, extracts reasoning.

        Args:
            action: The action to enhance
            response: The full response to search

        Returns:
            Updated PlanAction with additional details
        """
        if action.type == ActionType.WRITE and action.file_path:
            # Try to extract content for write operations
            # Look for patterns like: content: "...", content="""...""", etc.
            patterns = [
                rf"write to.*?{re.escape(action.file_path)}.*?content:?\s*['\"`]([^'\"` ]+)['\"`]",
                rf"content:?\s*['\"`]([^'\"` ]+)['\"`]",
            ]
            for pattern in patterns:
                match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
                if match:
                    action.content = match.group(1)
                    break

        return action
