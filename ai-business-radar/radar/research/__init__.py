"""Deterministic research outputs from derived features.

No network, no raw-body reads, no third-party LLM handoff, no advice.
"""

from .queue import build_research_queue, write_research_queue
from .evidence import build_evidence, write_evidence
from .jquants_evidence import build_jquants_evidence, render_jquants_evidence, write_jquants_evidence
from .llm_handoff import build_llm_handoff, write_llm_handoff

__all__ = [
    "build_research_queue",
    "write_research_queue",
    "build_evidence",
    "write_evidence",
    "build_jquants_evidence",
    "render_jquants_evidence",
    "write_jquants_evidence",
    "build_llm_handoff",
    "write_llm_handoff",
]
