import textwrap

from app.services.executor import RESULT_END, RESULT_START, run_code, validate_code


def test_blocked_imports_and_names():
    assert validate_code("import os")
    assert validate_code("import subprocess")
    assert validate_code("from shutil import rmtree")
    assert validate_code("open('x')")
    assert validate_code("eval('1+1')")
    assert validate_code("__import__('os')")
    assert validate_code("().__class__.__bases__")
    assert validate_code("x.system('ls')")


def test_allowed_code_passes_validation():
    code = textwrap.dedent(
        """
        import json
        import pandas as pd
        df = pd.DataFrame({"a": [1, 2]})
        print(json.dumps({"total": int(df["a"].sum())}))
        """
    )
    assert validate_code(code) == []


def test_syntax_error_is_reported():
    violations = validate_code("def broken(:")
    assert violations and "Syntax error" in violations[0]


def test_happy_path_with_result_and_chart(tmp_path):
    code = textwrap.dedent(
        f"""
        import matplotlib
        matplotlib.use("Agg")
        import json
        import matplotlib.pyplot as plt

        values = [1, 2, 3]
        plt.bar(["a", "b", "c"], values)
        plt.savefig("charts/test_chart.png")
        plt.close()

        print("{RESULT_START}")
        print(json.dumps({{"total": sum(values)}}))
        print("{RESULT_END}")
        """
    )
    result = run_code(code, tmp_path / "run", timeout_seconds=60)
    assert result.ok, result.error or result.stderr
    assert result.result == {"total": 6}
    assert len(result.charts) == 1
    assert result.charts[0].name == "test_chart.png"


def test_rejected_code_does_not_run(tmp_path):
    result = run_code("import os\nos.listdir('.')", tmp_path / "run")
    assert not result.ok
    assert "safety policy" in (result.error or "")


def test_runtime_error_is_captured(tmp_path):
    result = run_code("raise ValueError('boom')", tmp_path / "run")
    assert not result.ok
    assert "boom" in result.stderr


def test_timeout_kills_infinite_loop(tmp_path):
    result = run_code(
        "while True:\n    pass", tmp_path / "run", timeout_seconds=3
    )
    assert not result.ok
    assert result.error
