"""Where the run log goes, wherever the command is run from."""

from __future__ import annotations

from pathlib import Path

from local_ai_benchmark import cli, paths

REPO = Path(__file__).resolve().parents[1]


def test_a_source_checkout_writes_to_its_own_data_folder(monkeypatch, tmp_path):
    monkeypatch.delenv(paths.HOME_ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)  # run from somewhere else entirely

    assert paths.project_root() == REPO
    assert paths.default_run_log() == REPO / "data" / "raw" / "runs.jsonl"


def test_the_environment_variable_overrides_the_project_folder(monkeypatch, tmp_path):
    monkeypatch.setenv(paths.HOME_ENV_VAR, str(tmp_path))

    assert paths.default_run_log() == tmp_path.resolve() / "data" / "raw" / "runs.jsonl"


def test_an_installed_package_without_a_source_tree_uses_the_working_folder(monkeypatch, tmp_path):
    monkeypatch.delenv(paths.HOME_ENV_VAR, raising=False)
    installed = tmp_path / "site-packages" / "local_ai_benchmark" / "paths.py"
    monkeypatch.setattr(paths, "__file__", str(installed))
    monkeypatch.chdir(tmp_path)

    assert paths.project_root() == tmp_path


def test_the_cli_resolves_the_default_at_run_time(monkeypatch, tmp_path):
    monkeypatch.setenv(paths.HOME_ENV_VAR, str(tmp_path))
    args = cli.build_parser().parse_args(["ask", "--model", "m", "--prompt", "p"])

    assert cli.run_log(args) == tmp_path.resolve() / "data" / "raw" / "runs.jsonl"


def test_an_explicit_output_wins(tmp_path):
    target = tmp_path / "elsewhere.jsonl"
    args = cli.build_parser().parse_args(
        ["ask", "--model", "m", "--prompt", "p", "--output", str(target)]
    )

    assert cli.run_log(args) == target
