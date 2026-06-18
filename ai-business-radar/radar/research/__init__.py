"""Deterministic research outputs from derived features.

No network, no raw-body reads, no third-party LLM handoff, no advice.
"""

from .queue import build_research_queue, write_research_queue
from .evidence import build_evidence, write_evidence

__all__ = [
    "build_research_queue",
    "write_research_queue",
    "build_evidence",
    "write_evidence",
]
