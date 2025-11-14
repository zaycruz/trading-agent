"""
Compatibility alias that exposes `src.tools.analysis` as `analysis_tools`.
"""

from src.tools import analysis as _real_module
import sys

sys.modules[__name__] = _real_module

