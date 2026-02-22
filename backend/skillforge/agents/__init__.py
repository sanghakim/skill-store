"""
Agent Pool - Five specialized worker agents:
  1. PlannerAgent   - Decomposes complex tasks into sub-task DAGs
  2. ExecutorAgent  - Invokes skills to perform actual work
  3. ReviewerAgent  - Validates results and ensures quality
  4. ResearchAgent  - Gathers information and analyzes data
  5. CreativeAgent  - Generates content and proposes ideas
"""

from skillforge.agents.base import BaseAgent
from skillforge.agents.planner import PlannerAgent
from skillforge.agents.executor import ExecutorAgent
from skillforge.agents.reviewer import ReviewerAgent
from skillforge.agents.research import ResearchAgent
from skillforge.agents.creative import CreativeAgent

__all__ = [
    "BaseAgent",
    "PlannerAgent",
    "ExecutorAgent",
    "ReviewerAgent",
    "ResearchAgent",
    "CreativeAgent",
]
