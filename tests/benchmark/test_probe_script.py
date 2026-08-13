"""Regression tests for the probe script's own failure reporting (Plan 17 §1.3).

``scripts/contamination_probe.py`` printed ``wrote {path}`` outside the write
loop, so on 2026-08-11 three models reported success with no file on disk — a
silent failure in the silent-failure benchmark's own tooling. The gate is
narrow and non-negotiable: a run where nothing lands must create no file **and**
exit non-zero.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import httpx
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_probe_module():
    path = REPO_ROOT / "scripts" / "contamination_probe.py"
    spec = importlib.util.spec_from_file_location("contamination_probe", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["contamination_probe"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def probe_config(tmp_path: Path) -> Path:
    path = tmp_path / "models.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "defaults": {"trials": 1},
                "budget": {"max_usd_total": 0.0},
                # No pacing: these tests must not sleep.
                "limits": {"rpm": None, "requests_per_day": None},
                "retry": {"backoff_base": 0.0, "max_total_seconds": 1.0},
                "models": [{"id": "test/model", "label": "Test", "tracks": ["bare"]}],
            }
        )
    )
    return path


def _run(module, config: Path, out: Path, handler, monkeypatch) -> int:
    """Invoke the script's main() against a mocked transport."""
    from geocase.benchmark.runner.policy import Pacing

    def fake_build_client(self, **kwargs):
        from geocase.benchmark.runner.openrouter import OpenRouterClient

        return OpenRouterClient(
            api_key="test-key",
            policy=self.retry,
            transport=httpx.MockTransport(handler),
        )

    monkeypatch.setattr(Pacing, "build_client", fake_build_client)
    return module.main(
        [
            "--config",
            str(config),
            "--out",
            str(out),
            "--domain",
            "geo",
            "--delay",
            "0",
            "--task-budget",
            "1",
        ]
    )


def test_all_429_writes_nothing_and_exits_non_zero(
    tmp_path, probe_config, monkeypatch, capsys
):
    """The 2026-08-11 phantom-'wrote' failure, pinned."""
    module = _load_probe_module()
    out = tmp_path / "probes"

    def handler(request):
        return httpx.Response(429, json={"error": "rate limited"})

    rc = _run(module, probe_config, out, handler, monkeypatch)

    assert rc != 0, "a run where nothing landed must exit non-zero"
    assert not list(out.glob("*.json")), "wrote a probe file with no probes in it"
    err = capsys.readouterr().err
    assert "NO probes landed" in err


def test_successful_probe_writes_a_file_and_exits_zero(
    tmp_path, probe_config, monkeypatch, capsys
):
    module = _load_probe_module()
    out = tmp_path / "probes"

    def handler(request):
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "watch the antimeridian"}}],
                "usage": {"cost": 0.0},
            },
        )

    rc = _run(module, probe_config, out, handler, monkeypatch)

    assert rc == 0
    written = list(out.glob("*.json"))
    assert len(written) == 1
    assert "wrote" in capsys.readouterr().out
