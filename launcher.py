"""
launcher.py
Convenience launcher: verifies required packages are installed before
starting the app, and shows a friendly message if something is missing
(useful when running from source rather than the packaged .exe).
"""
from __future__ import annotations

import importlib
import subprocess
import sys

REQUIRED_MODULES = {
    "customtkinter": "customtkinter",
    "openpyxl": "openpyxl",
    "pandas": "pandas",
    "reportlab": "reportlab",
    "matplotlib": "matplotlib",
    "PIL": "Pillow",
}


def check_dependencies() -> list[str]:
    missing = []
    for module_name, pip_name in REQUIRED_MODULES.items():
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing.append(pip_name)
    return missing


def main():
    missing = check_dependencies()
    if missing:
        print("Missing required packages:", ", ".join(missing))
        answer = input("Install them now with pip? [Y/n]: ").strip().lower()
        if answer in ("", "y", "yes"):
            subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
        else:
            print("Cannot start ShopEase POS without required packages.")
            sys.exit(1)

    from main import main as run_app
    run_app()


if __name__ == "__main__":
    main()
