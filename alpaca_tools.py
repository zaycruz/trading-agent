"""
Compatibility alias that exposes `src.tools.alpaca` as `alpaca_tools`.
"""

from src.tools import alpaca as _real_module
import sys

sys.modules[__name__] = _real_module

