"""Phase C feature generation.

Scope: EDINET DB financials raw -> data/derived only.
No network, no env, no research queue, no advice.
"""

from .compute import compute_financial_features
from .build import build_financial_features

__all__ = ["compute_financial_features", "build_financial_features"]
