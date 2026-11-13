"""Generate synthetic input media. No downloads."""

import argparse
from pathlib import Path

from studio_ia.core import Tools, capture


def fixture(tools: Tools, output: Path, size="320x180", duration=8, audio=True, extra=None) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    args = [
        tools.ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-n",
        "-f",
        "lavfi",
        "-i",
        f"testsrc2=size={size}:rate=25:duration={duration}",
    ]
    if audio:
        args += ["-f", "lavfi", "-i", f"sine=frequency=440:sample_rate=48000:duration={duration}"]
    args += ["-c:v", "libx264", "-threads", "2", "-pix_fmt", "yuv420p"]
    if audio:
        args += ["-c:a", "aac", "-shortest"]
    capture(args + (extra or []) + [str(output)], timeout=120)
    return output


def generate(root: Path, tools: Tools) -> dict[str, Path]:
    return {
        "F01": fixture(tools, root / "F01_with_audio.mp4"),
        "F02": fixture(tools, root / "F02_silent.mp4", size="640x360", duration=5, audio=False),
        "F03": fixture(tools, root / "F03_été avec espaces ; $ littéral.mp4", duration=2),
        "F05": fixture(tools, root / "F05_portrait.mp4", size="360x640", duration=2),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    for key, path in generate(args.destination, Tools.discover()).items():
        print(key, path.name)
