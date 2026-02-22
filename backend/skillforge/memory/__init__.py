"""
Three-Layer Memory Architecture:
  Layer 1: WorkingMemory  - Session-scoped, current conversation state
  Layer 2: EpisodicMemory - Persistent, past session history & patterns
  Layer 3: SemanticMemory - Permanent, vector-based knowledge & preferences
"""

from skillforge.memory.working import WorkingMemory
from skillforge.memory.episodic import EpisodicMemory
from skillforge.memory.semantic import SemanticMemory
from skillforge.memory.context_bus import ContextBus
from skillforge.memory.manager import MemoryManager

__all__ = [
    "WorkingMemory",
    "EpisodicMemory",
    "SemanticMemory",
    "ContextBus",
    "MemoryManager",
]
