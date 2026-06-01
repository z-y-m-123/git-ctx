import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "git_ctx.py"


def run_cli(cwd, *args, input_text=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )


def write_rules(cwd, **overrides):
    rules = {
        "project": "demo",
        "description": "Demo project",
        "techStack": ["Python"],
        "codingStandards": ["Use type hints"],
        "architectureDecisions": ["Keep the CLI dependency-free"],
        "testingStrategy": {"framework": "pytest"},
    }
    rules.update(overrides)
    (cwd / ".ai-rules.json").write_text(
        json.dumps(rules, indent=2) + "\n",
        encoding="utf-8",
    )


def assert_ok(result):
    assert result.returncode == 0, result.stderr + result.stdout


def test_init_status_validate_and_export(tmp_path):
    assert_ok(run_cli(tmp_path, "init", "--template", "cli-tool"))

    status = run_cli(tmp_path, "status")
    assert_ok(status)
    assert "Nothing to commit" in status.stdout

    write_rules(tmp_path)
    validate = run_cli(tmp_path, "validate")
    assert_ok(validate)
    assert "No issues found" in validate.stdout

    export = run_cli(tmp_path, "export")
    assert_ok(export)
    assert (tmp_path / ".cursorrules").exists()
    assert (tmp_path / ".windsurfrules").exists()
    assert (tmp_path / "CLAUDE.md").exists()
    assert (tmp_path / ".github" / "copilot-instructions.md").exists()


def test_commit_diff_tag_and_checkout(tmp_path):
    assert_ok(run_cli(tmp_path, "init"))
    write_rules(tmp_path)

    commit = run_cli(tmp_path, "commit", "-m", "add demo rules")
    assert_ok(commit)
    assert "Committed as version 2" in commit.stdout

    tag = run_cli(tmp_path, "tag", "add", "2", "stable")
    assert_ok(tag)

    show = run_cli(tmp_path, "show", "stable", "--json")
    assert_ok(show)
    assert '"project": "demo"' in show.stdout

    write_rules(tmp_path, project="broken")
    diff = run_cli(tmp_path, "diff", "stable")
    assert_ok(diff)
    assert "-  \"project\": \"demo\"," in diff.stdout
    assert "+  \"project\": \"broken\"," in diff.stdout

    checkout = run_cli(tmp_path, "checkout", "-f", "stable")
    assert_ok(checkout)
    restored = json.loads((tmp_path / ".ai-rules.json").read_text(encoding="utf-8"))
    assert restored["project"] == "demo"


def test_branch_switch_and_merge(tmp_path):
    assert_ok(run_cli(tmp_path, "init"))
    write_rules(tmp_path, project="base")
    assert_ok(run_cli(tmp_path, "commit", "-m", "base rules"))

    assert_ok(run_cli(tmp_path, "branch", "experiment"))

    write_rules(tmp_path, project="main")
    assert_ok(run_cli(tmp_path, "commit", "-m", "main rules"))

    switch = run_cli(tmp_path, "switch", "experiment", "-f")
    assert_ok(switch)
    current = json.loads((tmp_path / ".ai-rules.json").read_text(encoding="utf-8"))
    assert current["project"] == "base"

    write_rules(tmp_path, project="experiment")
    assert_ok(run_cli(tmp_path, "commit", "-m", "experiment rules"))

    assert_ok(run_cli(tmp_path, "switch", "main", "-f"))
    merge = run_cli(tmp_path, "merge", "experiment", "-f")
    assert_ok(merge)
    merged = json.loads((tmp_path / ".ai-rules.json").read_text(encoding="utf-8"))
    assert merged["project"] == "experiment"
