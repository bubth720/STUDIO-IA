import json

import pytest

from studio_ia.core import StudioError
from studio_ia.pipeline import Request, build_plan, run_plan
from studio_ia.plans_v2 import compare_timing, frame_table, load_plan


def test_legacy_plan_replay_without_filter_reinterpretation(source, tools, tmp_path):
    old = build_plan(Request(str(source), str(tmp_path / "legacy.mp4"), scale=2), tools)
    frozen = load_plan(old.to_dict())
    assert frozen.data["migration"]["filter_graph_reinterpreted"] is False
    assert frozen.cpu_plan().to_dict() == old.to_dict()
    persisted = tmp_path / "closed-and-reopened.json"
    persisted.write_text(json.dumps(frozen.to_dict()))
    restored = load_plan(json.loads(persisted.read_text()))
    assert restored.identity == frozen.identity
    assert run_plan(restored.cpu_plan(), tools, tmp_path / "job")["status"] == "PASS"


def test_plan_does_not_share_mutable_caller_data(source, tools, tmp_path):
    data = build_plan(Request(str(source), str(tmp_path / "out.mp4")), tools).to_dict()
    plan = load_plan(data)
    identity = plan.identity
    data["filters"].append("bad")
    plan.to_dict()["cpu_plan"]["filters"].append("also-bad")
    assert plan.identity == identity and "bad" not in plan.cpu_plan().filters


@pytest.mark.parametrize("version", [0, 3, 100])
def test_future_schema_refused(version):
    with pytest.raises(StudioError, match="schéma"):
        load_plan({"schema_version": version})


def test_real_frame_table_and_exact_comparison(source, tools):
    table = frame_table(source, tools)
    compare_timing(table, table)
    altered = json.loads(json.dumps(table))
    altered["frames"][1]["pts"] += 1
    with pytest.raises(StudioError, match="Horodatage"):
        compare_timing(table, altered)
    with pytest.raises(StudioError, match="budget"):
        frame_table(source, tools, max_frames=1)
