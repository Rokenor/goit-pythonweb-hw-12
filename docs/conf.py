"""Конфігурація Sphinx для документації Contacts API.

Документація збирається з docstrings безпосередньо в коді (autodoc),
тому щоб оновити її, достатньо перезапустити ``make html`` у теці ``docs``.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Значення-заглушки, щоб імпорт `src.conf.config` не вимагав справжнього .env
os.environ.setdefault("DB_URL", "sqlite+aiosqlite:///./docs.db")
os.environ.setdefault("JWT_SECRET", "docs-secret")
os.environ.setdefault("MAIL_USERNAME", "example@meta.ua")
os.environ.setdefault("MAIL_PASSWORD", "docs-password")
os.environ.setdefault("MAIL_FROM", "example@meta.ua")
os.environ.setdefault("CLD_NAME", "docs-cloud")
os.environ.setdefault("CLD_API_KEY", "000000000000000")
os.environ.setdefault("CLD_API_SECRET", "docs-secret")

# -- Загальні відомості про проєкт -------------------------------------------
project = "Contacts API"
copyright = "2026, Oleksandr Kovrizhnykh"
author = "Oleksandr Kovrizhnykh"
release = "3.0.0"
language = "uk"

# -- Розширення --------------------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

autodoc_member_order = "bysource"
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
}
autodoc_mock_imports = ["libgravatar"]

suppress_warnings = ["ref.python"]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "sqlalchemy": ("https://docs.sqlalchemy.org/en/20/", None),
}

# -- HTML --------------------------------------------------------------------
html_theme = "alabaster"
html_static_path = ["_static"]
