"""Parser for extracting plans from AI model responses."""

import logging
import re
from typing import List, Optional, Tuple

from madison.core.plan import ActionType, Plan, PlanAction

logger = logging.getLogger(__name__)


class PlanParser:
    """Parse plans from AI model responses."""

    # Patterns for detecting different action types in natural language
    EXEC_PATTERNS = [
        r"execute:?\s*`([^`]+)`",
        r"run:?\s*`([^`]+)`",
        r"command:?\s*`([^`]+)`",
        r"I'll (execute|run):?\s*`([^`]+)`",
    ]

    READ_PATTERNS = [
        r"read:?\s*['\"]?([^'\"]+)['\"]?",
        r"read file:?\s*['\"]?([^'\"]+)['\"]?",
    ]

    WRITE_PATTERNS = [
        r"write:?\s*['\"]?([^'\"]+)['\"]?",
        r"create file:?\s*['\"]?([^'\"]+)['\"]?",
    ]

    SEARCH_PATTERNS = [
        r"search:?\s*['\"]?([^'\"]+)['\"]?",
        r"web search:?\s*['\"]?([^'\"]+)['\"]?",
    ]

    @classmethod
    def extract_actions(cls, response: str) -> List[PlanAction]:
        """Extract actions from an AI response.

        Looks for structured action descriptions in the response and converts them
        to PlanAction objects. The AI should express actions using patterns like:
        - "I'll execute: `mkdir foo`"
        - "Read file: /path/to/file"
        - "Search: query terms"

        Args:
            response: AI model response

        Returns:
            List of extracted PlanAction objects
        """
        actions = []

        # Look for exec commands
        for pattern in cls.EXEC_PATTERNS:
            matches = re.finditer(pattern, response, re.IGNORECASE)
            for match in matches:
                command = match.group(1) if match.lastindex >= 1 else match.group(0)
                if command:
                    actions.append(
                        PlanAction(
                            type=ActionType.EXEC,
                            command=command.strip(),
                            description=f"Execute: {command.strip()}",
                        )
                    )

        # Look for read operations
        for pattern in cls.READ_PATTERNS:
            matches = re.finditer(pattern, response, re.IGNORECASE)
            for match in matches:
                file_path = match.group(1)
                if file_path and "write" not in response[max(0, match.start() - 20) : match.start()].lower():
                    actions.append(
                        PlanAction(
                            type=ActionType.READ,
                            file_path=file_path.strip(),
                            description=f"Read file: {file_path.strip()}",
                        )
                    )

        # Look for write operations
        for pattern in cls.WRITE_PATTERNS:
            matches = re.finditer(pattern, response, re.IGNORECASE)
            for match in matches:
                file_path = match.group(1)
                if file_path:
                    actions.append(
                        PlanAction(
                            type=ActionType.WRITE,
                            file_path=file_path.strip(),
                            description=f"Write file: {file_path.strip()}",
                        )
                    )

        # Look for searches
        for pattern in cls.SEARCH_PATTERNS:
            matches = re.finditer(pattern, response, re.IGNORECASE)
            for match in matches:
                query = match.group(1)
                if query:
                    actions.append(
                        PlanAction(
                            type=ActionType.SEARCH,
                            query=query.strip(),
                            description=f"Search: {query.strip()}",
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
