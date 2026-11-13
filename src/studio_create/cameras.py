"""Virtual cameras and Level Sequence planning (Director V0), engine-agnostic.

A shot is a named Cine Camera with lens settings and keyframes in seconds; the
sequence converts time to exact frame numbers with rational frame rates. Nothing is
rendered here: the Unreal-side script turns this plan into a Level Sequence.
"""

import math
from fractions import Fraction


class CameraError(ValueError):
    """Invalid shot or sequence; never silently rounded."""


PRESETS = ("travelling", "orbit", "wide", "crane")


def _frames(seconds: Fraction, fps: Fraction) -> int:
    frames = seconds * fps
    if frames.denominator != 1:
        raise CameraError(f"{seconds} s à {fps} i/s ne donne pas un nombre entier d'images.")
    return int(frames)


def _look_at(src: list[float], dst: list[float]) -> list[float]:
    """Pitch, yaw, roll in degrees (Unreal FRotator order) from src towards dst."""
    dx, dy, dz = (dst[i] - src[i] for i in range(3))
    yaw = math.degrees(math.atan2(dy, dx))
    pitch = math.degrees(math.atan2(dz, math.hypot(dx, dy)))
    return [round(pitch, 3), round(yaw, 3), 0.0]


def shot(
    layout: dict,
    preset: str,
    *,
    name: str,
    duration_s: str | int = 12,
    focal_mm: float = 35.0,
    aperture: float = 4.0,
    height_cm: int = 1500,
) -> dict:
    """One shot from the city layout. Keyframes: t (rational s), location, rotation."""
    if preset not in PRESETS:
        raise CameraError(f"Preset inconnu : {preset} ({', '.join(PRESETS)}).")
    duration = Fraction(str(duration_s))
    if not 1 <= duration <= 120:
        raise CameraError("Durée de plan : 1 à 120 s.")
    if not 8 <= focal_mm <= 300 or not 1.0 <= aperture <= 22:
        raise CameraError("Focale 8–300 mm et ouverture f/1–f/22 requises.")
    bounds = layout["bounds"]
    cx = (bounds["min"][0] + bounds["max"][0]) / 2
    cy = (bounds["min"][1] + bounds["max"][1]) / 2
    span = max(bounds["max"][0] - bounds["min"][0], bounds["max"][1] - bounds["min"][1])
    road = next(r for r in layout["roads"] if r["id"] == layout["avenue"])["rect"]
    avenue_y = (road["min"][1] + road["max"][1]) / 2
    centre = [cx, cy, 0.0]
    keys: list[tuple[Fraction, list[float], list[float]]] = []
    if preset == "travelling":
        start = [road["min"][0] + 500.0, avenue_y, float(height_cm)]
        end = [road["max"][0] - 500.0, avenue_y, float(height_cm)]
        rotation = [-10.0, 0.0, 0.0]
        keys = [(Fraction(0), start, rotation), (duration, end, rotation)]
    elif preset == "orbit":
        radius = span * 0.75
        steps = 16  # dense keys: the interpolated path stays close to a circle
        for step in range(steps + 1):
            angle = math.radians(step * 360 / steps)
            location = [
                round(cx + radius * math.cos(angle), 1),
                round(cy + radius * math.sin(angle), 1),
                float(height_cm * 3),
            ]
            keys.append((duration * step / steps, location, _look_at(location, centre)))
    elif preset == "wide":
        location = [round(cx - span, 1), cy, float(height_cm * 4)]
        keys = [(Fraction(0), location, _look_at(location, centre))]
    else:  # crane: rises above the avenue while looking along it
        base = [road["min"][0] + 500.0, avenue_y, 200.0]
        top = [road["min"][0] + 500.0, avenue_y, float(height_cm * 4)]
        target = [cx, avenue_y, 0.0]
        keys = [
            (Fraction(0), base, _look_at(base, target)),
            (duration, top, _look_at(top, target)),
        ]
    # Unwrap yaw so interpolation never spins the camera through ±180°.
    for index in range(1, len(keys)):
        previous_yaw = keys[index - 1][2][1]
        rotation = list(keys[index][2])
        while rotation[1] - previous_yaw > 180:
            rotation[1] -= 360
        while rotation[1] - previous_yaw < -180:
            rotation[1] += 360
        keys[index] = (keys[index][0], keys[index][1], rotation)
    return {
        "name": name,
        "preset": preset,
        "duration_s": str(duration),
        "camera": {
            "focal_mm": focal_mm,
            "aperture": aperture,
            "focus_cm": round(math.dist(keys[0][1], centre), 1),
        },
        "interpolation": "CUBIC_AUTO" if len(keys) > 1 else "CONSTANT",
        "keyframes": [{"t": str(t), "location": loc, "rotation": rot} for t, loc, rot in keys],
    }


def sequence(shots: list[dict], *, fps: str = "24", name: str = "SEQ_Ville") -> dict:
    """Place shots back to back with camera cuts; exact frame ranges."""
    if not 1 <= len(shots) <= 8:
        raise CameraError("Une séquence contient 1 à 8 plans.")
    names = [s["name"] for s in shots]
    if len(set(names)) != len(names):
        raise CameraError("Noms de caméras en double.")
    rate = Fraction(fps)
    if rate not in (
        Fraction(24),
        Fraction(25),
        Fraction(30),
        Fraction(24000, 1001),
        Fraction(30000, 1001),
    ):
        raise CameraError("Cadences prises en charge : 24, 25, 30, 24000/1001, 30000/1001.")
    start, cuts = 0, []
    for item in shots:
        length = _frames(Fraction(item["duration_s"]), rate)
        # Shot boundaries are exact; inner keyframes snap to the nearest frame (documented).
        keys = [
            {**key, "frame": start + math.floor(Fraction(key["t"]) * rate + Fraction(1, 2))}
            for key in item["keyframes"]
        ]
        cuts.append(
            {
                "camera": item["name"],
                "start_frame": start,
                "end_frame": start + length,
                "keyframes": keys,
            }
        )
        start += length
    return {"name": name, "fps": str(rate), "total_frames": start, "cuts": cuts}
