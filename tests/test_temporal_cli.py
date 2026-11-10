import json
import subprocess
import sys

from studio_ia.media import sha256


def test_actual_cli_audit_and_explicit_planning(tmp_path, tools):
    from test_scene_guard import make_clip

    source = make_clip(tools, tmp_path / "source.mp4", kind="split", duration=1)
    before = sha256(source)
    audit = subprocess.run(
        [
            sys.executable,
            "-m",
            "studio_ia.cli",
            "temporal-audit",
            str(source),
            "--audio",
            "--motion",
        ],
        capture_output=True,
        check=True,
    )
    report = json.loads(audit.stdout)
    assert report["timeline"]["complete"] and report["audio"]["audio_track_count"] == 0
    assert report["neural_executed"] is False
    refused = subprocess.run(
        [sys.executable, "-m", "studio_ia.cli", "interpolation-plan", str(source)],
        capture_output=True,
    )
    assert refused.returncode == 1
    plan = subprocess.run(
        [sys.executable, "-m", "studio_ia.cli", "interpolation-plan", str(source), "--x2"],
        capture_output=True,
        check=True,
    )
    assert json.loads(plan.stdout)["can_execute_neural"] is False
    overwrite = subprocess.run(
        [
            sys.executable,
            "-m",
            "studio_ia.cli",
            "temporal-audit",
            str(source),
            "--json",
            str(source),
        ],
        capture_output=True,
    )
    assert overwrite.returncode == 1 and sha256(source) == before
