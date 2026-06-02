#!/usr/bin/env python3
"""Dependency probing helpers for install/discovery scripts."""

from __future__ import annotations

import importlib.util
import platform
import sys
from typing import Any


MODULE_HINTS = {
    "yaml": "install with python -m pip install -r requirements.txt",
    "openpyxl": "install with python -m pip install -r requirements.txt",
    "clickhouse_driver": "install with python -m pip install -r requirements.txt",
    "pymysql": "install with python -m pip install -r requirements.txt",
    "odps": "install with python -m pip install -r requirements.txt",
}


def module_installed(module: str | None) -> bool:
    return True if module is None else importlib.util.find_spec(module) is not None


def dependency_report(modules: list[str] | tuple[str, ...]) -> dict[str, Any]:
    missing = []
    installed = {}
    for module in modules:
        ok = module_installed(module)
        installed[module] = ok
        if not ok:
            missing.append({"module": module, "recommendation": MODULE_HINTS.get(module, "install the missing Python module")})
    return {
        "python": sys.executable,
        "version": sys.version.split()[0],
        "platform": platform.platform(),
        "installed_modules": installed,
        "missing_modules": missing,
        "recommended_python": "use the same Python that runs Codex skill scripts",
    }
