"""Actual encoded synthetic sources calibrate the CPU metric without a neural claim."""

from fractions import Fraction

from generate_temporal_fixtures import motion_fixture

from studio_ia.motion import analyze_motion


def test_static_texture_and_known_translation_align(tmp_path, tools):
    _, stationary = analyze_motion(motion_fixture(tools, tmp_path / "static.mkv"), tools)
    _, pan = analyze_motion(motion_fixture(tools, tmp_path / "pan.mkv", moving=True), tools)
    assert Fraction(stationary["mean_aligned_mae_percent"]) == 0
    measured = [p for p in pan["pairs"] if p["status"] == "MEASURED_TRANSLATION"]
    assert measured and all(
        p["dx_sample_pixels"] == 1 and p["dy_sample_pixels"] == 0 for p in measured
    )
    assert all(Fraction(p["aligned_mae_percent"]) == 0 for p in measured)
    assert all(Fraction(p["unaligned_mae_percent"]) > 0 for p in measured)
    assert pan["neural_executed"] is False


def test_known_exposure_change_is_measured_not_smoothed(tmp_path, tools):
    _, report = analyze_motion(motion_fixture(tools, tmp_path / "luma.mkv", flashing=True), tools)
    assert Fraction(report["mean_aligned_luma_bias_percent"]) == Fraction(20 * 100, 255)
    assert report["ghosting"].startswith("NOT_APPLICABLE")


def test_flat_scene_motion_is_unknown_not_zero(tmp_path, tools):
    from test_scene_guard import make_clip

    _, report = analyze_motion(
        make_clip(tools, tmp_path / "flat.mp4", kind="flat", duration=1), tools
    )
    assert report["status"] == "NOT_APPLICABLE_UNOBSERVABLE_MOTION"
    assert report["mean_aligned_mae_percent"] is None
