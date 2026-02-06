from types import SimpleNamespace

from api_probe.cli import run_command


def test_run_command_missing_file(tmp_path):
    missing_path = tmp_path / "missing.yaml"
    if missing_path.exists():
        missing_path.unlink()

    exit_code = run_command(str(missing_path))
    assert exit_code == 2


def test_run_command_success(monkeypatch, tmp_path):
    # Dummy config file path (will not be read because we monkeypatch loader)
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text("probes: []\n")

    # Monkeypatch dependencies in cli module
    import api_probe.cli as cli
    from api_probe.config.models import Config

    def fake_load_config(path):  # noqa: ARG001
        return {"probes": []}

    class DummyParser:
        def parse(self, cfg):  # noqa: ARG001
            return Config(probes=[], executions=[])

    class DummyExecutor:
        def execute(self, config):  # noqa: ARG001
            # success True emulates all probes passing
            return SimpleNamespace(success=True)

    class DummyReporter:
        def report(self, result):  # noqa: ARG001
            # No-op
            return None

    monkeypatch.setattr(cli, "load_config", fake_load_config)
    monkeypatch.setattr(cli, "ConfigParser", lambda: DummyParser())
    monkeypatch.setattr(cli, "ProbeExecutor", lambda: DummyExecutor())
    monkeypatch.setattr(cli, "Reporter", lambda: DummyReporter())

    exit_code = run_command(str(cfg_path))
    assert exit_code == 0


def test_run_command_failure(monkeypatch, tmp_path):
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text("probes: []\n")

    import api_probe.cli as cli
    from api_probe.config.models import Config

    def fake_load_config(path):  # noqa: ARG001
        return {"probes": []}

    class DummyParser:
        def parse(self, cfg):  # noqa: ARG001
            return Config(probes=[], executions=[])

    class DummyExecutor:
        def execute(self, config):  # noqa: ARG001
            # success False emulates failures in probes
            return SimpleNamespace(success=False)

    class DummyReporter:
        def report(self, result):  # noqa: ARG001
            return None

    monkeypatch.setattr(cli, "load_config", fake_load_config)
    monkeypatch.setattr(cli, "ConfigParser", lambda: DummyParser())
    monkeypatch.setattr(cli, "ProbeExecutor", lambda: DummyExecutor())
    monkeypatch.setattr(cli, "Reporter", lambda: DummyReporter())

    exit_code = run_command(str(cfg_path))
    assert exit_code == 1
