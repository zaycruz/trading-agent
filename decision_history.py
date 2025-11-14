"""
Compatibility alias that exposes `src.tools.history` as `decision_history`.
"""

from src.tools import history as _real_module
import sys

sys.modules[__name__] = _real_module

