"""Where the harness reads its configuration from and writes its data to."""

from __future__ import annotations

import os
from pathlib import Path

# Set this to keep data somewhere other than the project folder.
HOME_ENV_VAR = "LOCAL_AI_BENCHMARK_HOME"


def project_root() -> Path:
    """The folder that holds `configs/` and `data/`.

    In order: the folder named by LOCAL_AI_BENCHMARK_HOME; the repository this package was
    installed from (an editable install from a clone); otherwise the working folder.
    """
    configured = os.environ.get(HOME_ENV_VAR)
    if configured:
        return Path(configured).expanduser().resolve()
    source_tree = Path(__file__).resolve().parents[2]  # src/local_ai_benchmark/paths.py
    if (source_tree / "pyproject.toml").is_file() and (source_tree / "src").is_dir():
        return source_tree
    return Path.cwd()


def default_run_log() -> Path:
    return project_root() / "data" / "raw" / "runs.jsonl"
