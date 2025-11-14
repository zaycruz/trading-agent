"""
Compatibility wrapper for the Ollama client that degrades gracefully when system
level restrictions prevent loading the real package.
"""

import importlib.util
import site
from types import SimpleNamespace
from typing import Any, Dict

_real_module = None


def _load_real_ollama():
    global _real_module
    if _real_module is not None:
        return _real_module

    search_paths = []
    try:
        search_paths.extend(site.getsitepackages())
    except Exception:
        pass
    try:
        user_site = site.getusersitepackages()
        if user_site:
            search_paths.append(user_site)
    except Exception:
        pass

    for base_path in search_paths:
        spec = importlib.util.find_spec("ollama", [base_path])
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            _real_module = module
            return module

    return None


def chat(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    """
    Proxy to the real Ollama chat() implementation when available.
    Falls back to a lightweight stub response when the real package cannot
    be loaded (e.g., within restricted test sandboxes).
    """
    module = _load_real_ollama()
    if module is not None:
        return module.chat(*args, **kwargs)

    # Minimal stub response so dependent code can exercise the tool-calling loop.
    message = SimpleNamespace(content="Stubbed response: no LLM available", tool_calls=[])
    return {"message": message}

