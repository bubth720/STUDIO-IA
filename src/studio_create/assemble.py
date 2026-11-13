"""Assemble a rendered PNG sequence into a verified video (Render Manager V0).

Unreal's Movie Render Queue writes images; FFmpeg (already required by STUDIO IA)
turns them into H.264 MP4. The result is published atomically only after ffprobe
confirms the exact frame count, frame rate and duration. Missing frames are refused.
"""

import json
import re
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path


class AssemblyError(RuntimeError):
    """Incomplete or unreadable render; nothing is published."""


FRAME = re.compile(r"^(?P<stem>.+)\.(?P<number>\d{4,})\.png$")


def find_frames(directory: Path) -> tuple[str, list[int]]:
    stems: dict[str, list[int]] = {}
    for path in directory.glob("*.png"):
        match = FRAME.match(path.name)
        if match:
            stems.setdefault(match["stem"], []).append(int(match["number"]))
    if len(stems) != 1:
        raise AssemblyError(
            f"Une seule séquence d'images attendue dans {directory}, trouvé {len(stems)}."
        )
    stem, numbers = next(iter(stems.items()))
    numbers.sort()
    if numbers != list(range(numbers[0], numbers[0] + len(numbers))):
        raise AssemblyError("Images manquantes dans la séquence : rendu incomplet.")
    return stem, numbers


def assemble(
    directory: Path, fps: str, output: Path, *, expected_frames: int, ffmpeg: str | None = None
) -> dict:
    ffmpeg = ffmpeg or shutil.which("ffmpeg")
    ffprobe = None
    if ffmpeg:
        sibling = Path(ffmpeg).with_name(Path(ffmpeg).name.replace("ffmpeg", "ffprobe"))
        ffprobe = str(sibling) if sibling.is_file() else shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise AssemblyError("FFmpeg/ffprobe introuvables.")
    if output.exists():
        raise AssemblyError(f"La destination existe déjà : {output}. Aucun écrasement.")
    stem, numbers = find_frames(directory)
    if len(numbers) != expected_frames:
        raise AssemblyError(f"{len(numbers)} images rendues pour {expected_frames} attendues.")
    digits = len(next(directory.glob(f"{stem}.*.png")).name.rsplit(".", 2)[1])
    rate = Fraction(fps)
    temporary = output.with_name(f".{output.stem}.partial{output.suffix}")
    temporary.unlink(missing_ok=True)
    command = [
        ffmpeg,
        "-v",
        "error",
        "-n",
        "-framerate",
        str(rate),
        "-start_number",
        str(numbers[0]),
        "-i",
        str(directory / f"{stem}.%0{digits}d.png"),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-crf",
        "18",
        "-movflags",
        "+faststart",
        str(temporary),
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        probe = json.loads(
            subprocess.run(
                [
                    ffprobe,
                    "-v",
                    "error",
                    "-count_frames",
                    "-select_streams",
                    "v:0",
                    "-show_entries",
                    "stream=nb_read_frames,r_frame_rate,width,height",
                    "-of",
                    "json",
                    str(temporary),
                ],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
        )["streams"][0]
        frames = int(probe["nb_read_frames"])
        if frames != expected_frames or Fraction(probe["r_frame_rate"]) != rate:
            raise AssemblyError(
                f"Vidéo incohérente : {frames} images à {probe['r_frame_rate']} i/s."
            )
        temporary.rename(output)
    except subprocess.CalledProcessError as exc:
        raise AssemblyError(f"FFmpeg a échoué : {exc.stderr.strip()[:500]}") from exc
    finally:
        temporary.unlink(missing_ok=True)
    return {
        "output": str(output),
        "frames": frames,
        "fps": str(rate),
        "duration_s": str(Fraction(frames) / rate),
        "resolution": [int(probe["width"]), int(probe["height"])],
        "source": "PNG_SEQUENCE",
    }
