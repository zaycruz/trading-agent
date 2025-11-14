"""
Compatibility alias that exposes `src.tools.web_search` as `web_search`.
"""

from src.tools import web_search as _real_module
import sys

sys.modules[__name__] = _real_module

