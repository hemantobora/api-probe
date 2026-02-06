from api_probe.execution.results import ExecutionResult, RunResult, ProbeResult
from api_probe.reporting.reporter import Reporter


def test_reporter_silent_on_success(capsys):
    run = RunResult(run_index=0, run_name="Run 1", probe_results=[
        ProbeResult(probe_name="P1", success=True),
        ProbeResult(probe_name="P2", success=True),
    ])
    result = ExecutionResult(run_results=[run])

    Reporter().report(result)

    captured = capsys.readouterr()
    # No output on success
    assert captured.err == ""
    assert captured.out == ""


def test_reporter_prints_failures(capsys):
    failed_probe = ProbeResult(probe_name="P1", success=False, errors=[])
    passed_probe = ProbeResult(probe_name="P2", success=True)
    run = RunResult(run_index=0, run_name="Run 1", probe_results=[failed_probe, passed_probe])
    result = ExecutionResult(run_results=[run])

    Reporter().report(result)

    captured = capsys.readouterr()
    # Should print a summary with counts and probe name
    assert "VALIDATION FAILURES" in captured.err
    assert "SUMMARY" in captured.err
    assert "Failed Probes" in captured.err
    assert "P1" in captured.err