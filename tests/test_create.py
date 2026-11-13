"""STUDIO CREATE V0 foundations — tests runnable WITHOUT Unreal Engine.

Covers the mission's CREATE acceptance tests where possible without the engine:
1 (Unreal absent), 2 (compatible install detected, on a SIMULATED directory tree whose
files are never executed), 3/4 (city + two cameras + sequence as data), 5 (video
assembly from a synthetic PNG sequence with real FFmpeg), 8 (accents/spaces, existing
project, unknown command). No test launches Unreal or claims an Unreal render.
"""

import json
from pathlib import Path

import pytest

from studio_create import assemble, bridge, cameras, city, contracts
from studio_create.cli import main


def test_same_seed_same_city_and_different_seed_differs():
    a = city.generate(city.CityParams(seed=2048, blocks_x=6, blocks_y=1))
    b = city.generate(city.CityParams(seed=2048, blocks_x=6, blocks_y=1))
    c = city.generate(city.CityParams(seed=2049, blocks_x=6, blocks_y=1))
    assert a == b and a["layout_sha256"] == b["layout_sha256"]
    assert a["layout_sha256"] != c["layout_sha256"]


@pytest.mark.parametrize("density", ["low", "medium", "high"])
@pytest.mark.parametrize("seed", [0, 7, 2048, 99991])
def test_no_building_on_road_sidewalk_or_overlapping(density, seed):
    layout = city.generate(city.CityParams(seed=seed, blocks_x=4, blocks_y=3, density=density))
    city.validate_layout(layout)  # raises on any collision
    assert layout["buildings"] and layout["props"]["lamps"] and layout["roads"]
    road = layout["roads"][0]["rect"]
    assert all(not city._overlap(b["footprint"], road) for b in layout["buildings"])


def test_validator_catches_a_building_moved_onto_the_road():
    layout = city.generate(city.CityParams(seed=1))
    road = next(r for r in layout["roads"] if r["id"] == layout["avenue"])["rect"]
    layout["buildings"][0]["footprint"] = {
        "min": list(road["min"]),
        "max": [road["min"][0] + 500, road["max"][1]],
    }
    with pytest.raises(city.CityError):
        city.validate_layout(layout)


@pytest.mark.parametrize(
    "changes",
    [
        {"blocks_x": 0},
        {"density": "extrême"},
        {"height_min_cm": 9000, "height_max_cm": 900},
        {"seed": -1},
    ],
)
def test_invalid_parameters_are_refused(changes):
    with pytest.raises(city.CityError):
        city.CityParams(**changes).validate()


def test_two_cameras_and_sequence_have_exact_frames():
    scene = contracts.build_scene(
        city.CityParams(seed=2048, blocks_x=6, blocks_y=1),
        [("Avenue", "travelling"), ("Orbite", "orbit")],
        fps="24",
    )
    seq = scene["sequence"]
    assert [c["camera"] for c in seq["cuts"]] == ["Avenue", "Orbite"]
    assert seq["total_frames"] == 2 * 12 * 24
    assert seq["cuts"][1]["start_frame"] == seq["cuts"][0]["end_frame"] == 288
    travelling = scene["cameras"][0]
    assert travelling["keyframes"][0]["location"][1] == travelling["keyframes"][1]["location"][1]
    assert travelling["keyframes"][1]["location"][0] > travelling["keyframes"][0]["location"][0]


def test_ntsc_shot_that_is_not_a_whole_number_of_frames_is_refused():
    layout = city.generate(city.CityParams())
    shot = cameras.shot(layout, "wide", name="Large", duration_s=12)
    with pytest.raises(cameras.CameraError, match="entier"):
        cameras.sequence([shot], fps="30000/1001")


def test_duplicate_camera_names_and_unknown_preset_are_refused():
    layout = city.generate(city.CityParams())
    shot = cameras.shot(layout, "wide", name="A")
    with pytest.raises(cameras.CameraError):
        cameras.sequence([shot, shot])
    with pytest.raises(cameras.CameraError):
        cameras.shot(layout, "drone-fpv", name="B")


def test_scene_tampering_is_detected():
    scene = contracts.build_scene(city.CityParams(seed=5), [("A", "wide")])
    scene["layout"]["buildings"][0]["height_cm"] += 100
    with pytest.raises(contracts.ContractError, match="empreinte"):
        contracts.validate_scene(scene)


def test_scene_actions_are_flat_and_cover_the_whole_scene():
    scene = contracts.build_scene(city.CityParams(seed=3), [("A", "travelling"), ("B", "crane")])
    actions = contracts.scene_actions(scene)
    ops = [a["op"] for a in actions]
    assert ops[0] == "new_level" and ops[-1] == "save_level"
    assert ops.count("camera") == 2 and ops.count("sequence") == 1 and ops.count("lighting") == 1
    boxes = {a["id"] for a in actions if a["op"] == "box"}
    assert {b["id"] for b in scene["layout"]["buildings"]} <= boxes
    json.dumps(actions)  # serialisable for the command file


def test_project_and_restore_job_contracts():
    project = contracts.new_project("Démo-1".encode("ascii", "ignore").decode() or "Demo", "create")
    assert contracts.validate_project(project)["paths"]["exports"] == "exports"
    with pytest.raises(contracts.ContractError):
        contracts.validate_project({**project, "paths": {"media": "../hors-projet"}})
    job = {
        "schema_version": 1,
        "source": "media/film ancien.mkv",
        "profile": "live-action",
        "model": {"name": "realesrgan-x4plus", "manifest_sha256": "c" * 64},
        "params": {},
        "outputs": ["exports/film restauré.mkv"],
        "state": "pending",
    }
    assert contracts.validate_restore_job(job)["state"] == "pending"
    for bad in ({"profile": "cinéma"}, {"state": "done"}, {"source": "C:/absolu.mp4"}):
        with pytest.raises(contracts.ContractError):
            contracts.validate_restore_job({**job, **bad})


def test_t1_unreal_absent_gives_actionable_diagnostic(tmp_path):
    report = bridge.doctor(env={"HOME": str(tmp_path / "vide"), bridge.ENV_ROOTS: ""})
    report["installations"] = [
        i for i in report["installations"] if not i["root"].startswith("/opt")
    ]
    if not report["installations"]:
        assert report["status"] == "NOT_FOUND"
        assert "Unreal Engine 5.8" in report["actions"][0]
    assert report["render_verified"] is False and report["network"] == "NO_PORT_OPENED"


def fake_install(root: Path, version=(5, 8, 0), plugins=bridge.REQUIRED_PLUGINS):
    """SIMULATED Unreal tree: placeholder files only, never executed by any test."""
    (root / "Engine" / "Build").mkdir(parents=True)
    (root / "Engine" / "Build" / "Build.version").write_text(
        json.dumps(
            {"MajorVersion": version[0], "MinorVersion": version[1], "PatchVersion": version[2]}
        ),
        encoding="utf-8",
    )
    binaries = root / "Engine" / "Binaries" / bridge._platform_dir()
    binaries.mkdir(parents=True)
    suffix = ".exe" if bridge.os.name == "nt" else ""
    for name in ("UnrealEditor", "UnrealEditor-Cmd"):
        (binaries / f"{name}{suffix}").write_text("SIMULATED, NEVER EXECUTED")
    for plugin in plugins:
        folder = root / "Engine" / "Plugins" / "Simulated" / plugin
        folder.mkdir(parents=True)
        (folder / f"{plugin}.uplugin").write_text("{}")
    return root


def test_t2_simulated_compatible_install_is_identified_but_never_called_tested(tmp_path):
    root = fake_install(tmp_path / "Epic Games" / "UE_5.8")
    report = bridge.doctor(env={"HOME": str(tmp_path / "vide"), bridge.ENV_ROOTS: str(root)})
    mine = next(i for i in report["installations"] if i["root"] == str(root))
    assert mine["version"] == "5.8.0" and mine["status"] == "COMPATIBLE_NOT_TESTED"
    assert all(mine["plugins"].values())
    assert report["status"] == "READY_FOR_MANUAL_TEST" and report["render_verified"] is False


def test_incompatible_version_or_missing_plugin_is_explained(tmp_path):
    old = fake_install(tmp_path / "UE_5.3", version=(5, 3, 2))
    partial = fake_install(tmp_path / "UE_5.8", plugins=("PythonScriptPlugin",))
    assert bridge.inspect_install(old)["status"] == "INCOMPATIBLE"
    problems = bridge.inspect_install(partial)["problems"]
    assert any("MovieRenderPipeline" in p for p in problems)


def test_t8_project_creation_with_accents_and_refusal_of_existing(tmp_path):
    destination = tmp_path / "Projets à moi" / "Ville d'essai 日本語"
    destination.parent.mkdir()
    info = bridge.create_project(destination, "VilleEssai")
    assert info["status"] == "OK" and info["uproject"].endswith("VilleEssai.uproject")
    project = json.loads((destination / "project.json").read_text(encoding="utf-8"))
    assert contracts.validate_project(project)["mode"] == "create"
    uproject = json.loads((destination / "VilleEssai.uproject").read_text(encoding="utf-8"))
    assert {p["Name"] for p in uproject["Plugins"]} == set(bridge.REQUIRED_PLUGINS)
    with pytest.raises(bridge.BridgeError, match="existe déjà"):
        bridge.create_project(destination, "VilleEssai")
    assert not list(destination.parent.glob(".*.partial"))


def test_command_files_and_argv_are_built_but_never_launched(tmp_path, monkeypatch):
    monkeypatch.setattr(bridge.subprocess, "run", lambda *a, **k: pytest.fail("must not launch"))
    project = tmp_path / "projet"
    bridge.create_project(project)
    scene = contracts.build_scene(
        city.CityParams(seed=2048), [("Avenue", "travelling"), ("Orbite", "orbit")]
    )
    command = bridge.write_command(project, "build_city", scene)
    data = json.loads(command.read_text(encoding="utf-8"))
    assert data["command"] == "build_city" and data["actions"][0]["op"] == "new_level"
    install = bridge.inspect_install(fake_install(tmp_path / "UE_5.8"))
    argv = bridge.script_argv(install, project / "StudioCreate.uproject", "build_city.py", command)
    assert argv[0] == install["editor_cmd"] and "-run=pythonscript" in argv
    payload = bridge.render_payload(scene, project)
    assert payload["expected_frames"] == scene["sequence"]["total_frames"]
    with pytest.raises(bridge.BridgeError):
        bridge.write_command(project, "format_disk", {})


def test_unreal_side_scripts_are_present_and_marked_not_executed():
    scripts = Path(bridge.TEMPLATE) / "Content" / "Python" / "studio_create_unreal"
    for name in ("build_city.py", "render.py"):
        text = (scripts / name).read_text(encoding="utf-8")
        assert "STATUS: NOT EXECUTED" in text
        compile(text, name, "exec")  # syntax only; importing needs the Unreal runtime


def synthetic_png_sequence(tools, directory: Path, frames: int, rate: str = "24"):
    directory.mkdir(parents=True)
    import subprocess

    subprocess.run(
        [
            tools.ffmpeg,
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"testsrc2=size=128x72:rate={rate}",
            "-frames:v",
            str(frames),
            "-start_number",
            "0",
            str(directory / "SEQ_Ville.%04d.png"),
        ],
        check=True,
    )


def test_t5_png_sequence_assembled_and_verified(tools, tmp_path):
    frames = tmp_path / "rendu synthétique"
    synthetic_png_sequence(tools, frames, 48)
    output = tmp_path / "séquence.mp4"
    result = assemble.assemble(frames, "24", output, expected_frames=48, ffmpeg=tools.ffmpeg)
    assert (
        result["frames"] == 48 and result["duration_s"] == "2" and result["resolution"] == [128, 72]
    )
    assert output.stat().st_size > 0
    with pytest.raises(assemble.AssemblyError, match="existe déjà"):
        assemble.assemble(frames, "24", output, expected_frames=48, ffmpeg=tools.ffmpeg)


def test_missing_frame_is_refused_and_nothing_published(tools, tmp_path):
    frames = tmp_path / "trou"
    synthetic_png_sequence(tools, frames, 10)
    (frames / "SEQ_Ville.0004.png").unlink()
    with pytest.raises(assemble.AssemblyError, match="manquantes"):
        assemble.assemble(frames, "24", tmp_path / "x.mp4", expected_frames=10, ffmpeg=tools.ffmpeg)
    assert not (tmp_path / "x.mp4").exists()


def test_cli_scene_doctor_and_project(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "vide"))
    monkeypatch.setenv(bridge.ENV_ROOTS, "")
    out = tmp_path / "scène.json"
    assert main(["scene", str(out), "--seed", "2048", "--blocks-x", "6", "--blocks-y", "1"]) == 0
    scene = contracts.validate_scene(json.loads(out.read_text(encoding="utf-8")))
    assert len(scene["cameras"]) == 2
    assert main(["new-project", str(tmp_path / "p 1")]) == 0
    assert main(["build-city", str(tmp_path / "p 1"), str(out)]) == 0
    assert main(["new-project", str(tmp_path / "p 1")]) == 1
    assert "existe déjà" in capsys.readouterr().err


def test_orbit_is_dense_and_yaw_never_jumps():
    layout = city.generate(city.CityParams())
    orbit = cameras.shot(layout, "orbit", name="Orbite")
    yaws = [k["rotation"][1] for k in orbit["keyframes"]]
    assert len(yaws) == 17
    assert all(abs(b - a) <= 180 for a, b in zip(yaws, yaws[1:], strict=False))
    assert abs(yaws[-1] - yaws[0]) == 360  # one full, continuous turn
