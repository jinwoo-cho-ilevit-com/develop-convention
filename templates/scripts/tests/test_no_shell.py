"""C-02 — a verify command runs as an argument vector, not through a shell.

Removing the shell is what makes several other properties honest: a missing program
becomes a spawn error the command cannot forge, and no flag the runner appends can
land on a different program in a pipeline.
"""

import inspect
import sys

import contract

PY = sys.executable


def test_no_shell_run_argv_has_no_shell_parameter():
    """Structural: there is no switch to turn the shell back on."""
    assert "shell" not in inspect.signature(contract.run_argv).parameters


def test_no_shell_the_execution_call_never_enables_it():
    assert "shell=True" not in inspect.getsource(contract.run_argv)


def test_no_shell_a_glob_argument_is_passed_through_literally(repo):
    (repo / "a.txt").write_text("x", encoding="utf-8")
    (repo / "b.txt").write_text("x", encoding="utf-8")
    assert contract.run_argv(("echo", "*.txt"), cwd=repo).output.strip() == "*.txt"


def test_no_shell_a_variable_reference_is_not_expanded(repo):
    assert contract.run_argv(("echo", "$HOME"), cwd=repo).output.strip() == "$HOME"


def test_no_shell_an_operator_is_an_argument_not_an_operator(repo):
    run = contract.run_argv(("echo", "a", "&&", "b"), cwd=repo)
    assert run.output.strip() == "a && b"
    assert not (repo / "b").exists()


def test_no_shell_a_missing_program_is_a_spawn_error_not_an_exit_code(repo):
    """127 is a shell's way of saying this; without a shell the failure is unambiguous."""
    run = contract.run_argv(("definitely-not-an-installed-command",), cwd=repo)
    assert run.spawn_error is not None
    assert run.exit_code is None


def test_no_shell_a_timeout_is_recorded_rather_than_raised(repo):
    run = contract.run_argv((PY, "-c", "import time; time.sleep(30)"), cwd=repo, timeout=1)
    assert run.timed_out
    assert run.exit_code is None


def test_no_shell_stdin_is_not_inherited(repo):
    """An interactive command must fail fast rather than block until the timeout."""
    run = contract.run_argv(
        (PY, "-c", "import sys; sys.exit(1 if sys.stdin.read() == '' else 0)"),
        cwd=repo,
        timeout=10,
    )
    assert not run.timed_out
    assert run.exit_code == 1


def test_no_shell_output_is_truncated_with_a_marker(repo):
    run = contract.run_argv(
        (PY, "-c", f"print('x' * {contract.OUTPUT_CAPTURE_CHARS + 500})"), cwd=repo
    )
    assert run.truncated
    assert len(run.output) < contract.OUTPUT_CAPTURE_CHARS + 200
