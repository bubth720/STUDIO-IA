"""Small public-domain synthetic fixtures. No user media or model downloads."""

from pathlib import Path

from studio_ia.core import Tools, capture


def audio_fixture(tools: Tools, path: Path, *, vfr: bool = False) -> Path:
    filters = (
        "select=if(lt(t\\,1)\\,not(mod(n\\,8))\\,if(lt(t\\,2)\\,not(mod(n\\,5))\\,not(mod(n\\,4))))"
        if vfr
        else "null"
    )
    capture(
        [
            tools.ffmpeg,
            "-v",
            "error",
            "-n",
            "-f",
            "lavfi",
            "-i",
            f"testsrc2=size=64x48:rate={120 if vfr else 25}:duration=3",
            "-itsoffset",
            "0.2",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=48000:duration=2.5",
            "-itsoffset",
            "0.2",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=880:sample_rate=44100:duration=2.5",
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-map",
            "2:a:0",
            "-vf",
            filters,
            "-fps_mode",
            "passthrough",
            "-c:v",
            "libx264",
            "-threads",
            "1",
            "-crf",
            "0",
            "-c:a:0",
            "aac",
            "-c:a:1",
            "pcm_s16le",
            "-metadata:s:a:0",
            "language=fra",
            "-metadata:s:a:1",
            "language=eng",
            "-metadata:s:a:0",
            "title=synthetic 440Hz",
            "-metadata:s:a:1",
            "title=synthetic 880Hz",
            "-avoid_negative_ts",
            "disabled",
            str(path),
        ]
    )
    return path


def motion_fixture(tools: Tools, path: Path, *, moving=False, flashing=False) -> Path:
    raw = path.with_suffix(".owned.gray")
    try:
        with raw.open("xb") as handle:
            for n in range(8):
                for y in range(32):
                    for x in range(32):
                        u = (x - (2 * n if moving else 0)) % 32
                        value = 30 + (u * 13 + y * 37 + u * y) % 150
                        handle.write(bytes([value + (20 * (n % 2) if flashing else 0)]))
        capture(
            [
                tools.ffmpeg,
                "-v",
                "error",
                "-n",
                "-f",
                "rawvideo",
                "-pixel_format",
                "gray",
                "-video_size",
                "32x32",
                "-framerate",
                "25",
                "-i",
                str(raw),
                "-c:v",
                "ffv1",
                "-threads",
                "1",
                str(path),
            ]
        )
    finally:
        raw.unlink(missing_ok=True)
    return path
