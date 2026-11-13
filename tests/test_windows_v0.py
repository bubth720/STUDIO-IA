"""Windows V0 integration: machine profile, resource policy, comparison zoom, tabs.

The machine profile uses SIMULATED Vulkan device lists where a GPU is needed: these
tests check the policy (GPU choice, tile size, refusals), never real GPU capability.
"""

import pytest

from studio_ia import system_profile as sp

GIB = sp.GIB


def device(index, kind, vram, name="GPU"):
    return {
        "index": index,
        "name": name,
        "device_type": kind,
        "device_local_bytes": vram,
        "physical_gpu": kind in (1, 2),
    }


def test_discrete_gpu_preferred_over_integrated_listed_first():
    devices = [device(0, 1, 2 * GIB, "Intel UHD"), device(1, 2, 4 * GIB, "GTX 1650")]
    assert sp.pick_gpu(devices)["name"] == "GTX 1650"
    assert sp.pick_gpu([device(0, 4, 16 * GIB, "llvmpipe")]) is None


@pytest.mark.parametrize(
    ("vram", "tile"),
    [(None, None), (GIB // 2, None), (GIB, 32), (2 * GIB, 64), (4 * GIB, 128), (8 * GIB, 256)],
)
def test_tile_size_follows_device_memory(vram, tile):
    assert sp.recommended_tile(vram) == tile


def test_profile_without_gpu_keeps_cpu_and_refuses_ai(tmp_path):
    data = sp.profile(tmp_path, vulkan={"status": "BLOCKED", "reason": "X", "devices": []})
    assert data["capabilities"]["restore_ai"] == "BLOCKED"
    assert data["capabilities"]["create_scene_preparation"] == "READY"
    assert any("CPU classique seul" in item for item in data["limits"])
    assert data["recommendations"]["ncnn_tile"] is None


def test_profile_with_small_and_usable_gpus(tmp_path):
    tiny = sp.profile(
        tmp_path, vulkan={"status": "COMPATIBLE", "devices": [device(0, 2, GIB // 2)]}
    )
    assert tiny["capabilities"]["restore_ai"] == "BLOCKED"
    assert any("< 1 Gio" in item for item in tiny["limits"])
    laptop = sp.profile(
        tmp_path,
        vulkan={
            "status": "COMPATIBLE",
            "devices": [device(0, 1, GIB, "iGPU"), device(1, 2, 4 * GIB, "dGPU")],
        },
    )
    assert laptop["capabilities"]["restore_ai"] == "POSSIBLE_NOT_QUALIFIED"
    assert laptop["recommendations"] == {
        **laptop["recommendations"],
        "ncnn_tile": 128,
        "ncnn_gpu_index": 1,
    }
    assert laptop["recommendations"]["basis"].startswith("ESTIMATES")


def test_real_profile_runs_on_this_machine(tmp_path):
    data = sp.profile(tmp_path)
    assert data["cpu"]["logical_cores"] and data["schema_version"] == 1
    for item in data["gpu"]["devices"]:
        assert "device_local_bytes" in item and "device_type_name" in item


@pytest.mark.gui
def test_comparison_zoom_is_synchronised_and_exportable(qapp):
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QColor, QPixmap

    from studio_ia.ui import Comparison

    widget = Comparison()
    widget.resize(640, 480)
    before, after = QPixmap(64, 48), QPixmap(128, 96)
    before.fill(QColor("red"))
    after.fill(QColor("blue"))
    widget.before, widget.after = before, after
    widget.set_zoom(2.0, QPointF(0.25, 0.25))
    region_b, region_a = widget._source(before), widget._source(after)
    # Same normalised region on both images, whatever their resolutions.
    assert (region_b.x() / 64, region_b.width() / 64) == (
        region_a.x() / 128,
        region_a.width() / 128,
    )
    assert region_b.width() == 32
    widget.set_zoom(50)
    assert widget.zoom == 8.0
    widget.set_zoom(0.1)
    assert widget.zoom == 1.0 and widget.center == QPointF(0.5, 0.5)
    widget.set_zoom(2.0, QPointF(0.5, 0.5))
    image = widget.composite()
    assert (image.width(), image.height()) == (64 * 2 + 8, 48 + 28)
    assert "Avant 64×48" in widget.info() and "Après 128×96" in widget.info()


@pytest.mark.gui
def test_window_has_restore_create_and_hardware_tabs(tmp_path, qapp):
    from PySide6.QtTest import QTest

    from studio_ia.ui import Window

    window = Window(tmp_path / "état")
    try:
        window.show()
        labels = [window.tabs.tabText(i) for i in range(window.tabs.count())]
        assert labels[0].startswith("RESTORE") and labels[1].startswith("CREATE")
        assert labels[2] == "Matériel et diagnostic"
        create, hardware = window.extra_panels
        create.generate_button.click()
        for _ in range(100):
            QTest.qWait(50)
            if create.scene and hardware.data:
                break
        assert create.scene and create.map.scene is create.scene
        assert "Rendu Unreal : non effectué" in create.info.text()
        assert hardware.data["schema_version"] == 1
        assert "RESTORE classique" in hardware.text.toPlainText()
    finally:
        window.pool.shutdown(wait=True)
        for panel in window.extra_panels:
            panel.shutdown()
        qapp.processEvents()
        window.manager.close()
        window.close()
