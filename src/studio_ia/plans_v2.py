"""Immutable, versioned envelopes; legacy CPU plans retain their exact semantics."""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from studio_ia.core import StudioError, Tools, capture
from studio_ia.media import MediaInfo
from studio_ia.models import canonical
from studio_ia.pipeline import Plan, Request


@dataclass(frozen=True)
class PlanV2:
    payload: str

    @property
    def data(self) -> dict:
        return json.loads(self.payload)

    @property
    def identity(self) -> str:
        return hashlib.sha256(self.payload.encode()).hexdigest()

    def to_dict(self) -> dict:
        return self.data

    @property
    def request(self) -> Request:
        return self.cpu_plan().request

    def cpu_plan(self) -> Plan:
        data = self.data["cpu_plan"]
        data["request"] = Request(**data["request"])
        data["media"] = MediaInfo(**data["media"])
        return Plan(**data)


def load_plan(data: dict) -> PlanV2:
    version = data.get("schema_version")
    if version is None and data.get("request", {}).get("schema_version") == 1:
        # Explicit envelope migration, no DB migration and no regenerated CPU filters.
        data = {
            "schema_version": 2,
            "kind": "cpu-v1",
            "cpu_plan": data,
            "migration": {"from": 1, "filter_graph_reinterpreted": False},
        }
    if data.get("schema_version") != 2 or data.get("kind") not in ("cpu-v1", "neural-ncnn"):
        raise StudioError("Plan : schéma futur ou moteur inconnu, aucune réinterprétation.")
    try:
        plan = PlanV2(canonical(data))
        cpu = plan.cpu_plan()
        if cpu.request.schema_version != 1:
            raise StudioError("Plan CPU hérité non compatible.")
        if data["kind"] == "neural-ncnn":
            required = {"source_sha256", "engine", "model", "timing", "budgets", "policies"}
            if not required <= data.keys() or cpu.filters:
                raise StudioError("Plan neuronal incomplet ou filtre CPU d'agrandissement présent.")
        return plan
    except (TypeError, KeyError) as exc:
        raise StudioError("Plan incomplet.") from exc


def frame_table(path: Path, tools: Tools, *, max_frames: int = 10000) -> dict:
    """Read exact integer PTS and durations. Bound packets before allocating the JSON."""
    if not 1 <= max_frames <= 10000:
        raise StudioError("Budget de frames invalide.")
    data = json.loads(
        capture(
            [
                tools.ffprobe,
                "-v",
                "error",
                "-protocol_whitelist",
                "file,pipe",
                "-select_streams",
                "v:0",
                "-read_intervals",
                f"%+#{max_frames + 1}",
                "-show_frames",
                "-show_streams",
                "-show_entries",
                "frame=best_effort_timestamp,duration,pkt_duration:stream=time_base,duration_ts,nb_frames",
                "-of",
                "json",
                str(path),
            ],
            timeout=120,
        )
    )
    rows = data.get("frames", [])
    if not rows or len(rows) > max_frames:
        raise StudioError("Vidéo hors budget de frames, vide ou non décodable.")
    stream = data["streams"][0]
    time_base = stream["time_base"]
    from fractions import Fraction

    tb = Fraction(time_base)
    if tb <= 0:
        raise StudioError("Timebase invalide.")
    frames: list[dict] = []
    for index, row in enumerate(rows):
        try:
            pts = int(row["best_effort_timestamp"])
            raw_duration = row.get("duration", row.get("pkt_duration"))
            if raw_duration is not None:
                duration = int(raw_duration)
                duration_evidence = "DECODED_FRAME"
            elif index + 1 < len(rows):
                duration = int(rows[index + 1]["best_effort_timestamp"]) - pts
                duration_evidence = "NEXT_INTEGER_PTS"
            else:
                duration = int(rows[0]["best_effort_timestamp"]) + int(stream["duration_ts"]) - pts
                duration_evidence = "CONTAINER_INTEGER_DURATION_TS"
        except (KeyError, ValueError, TypeError) as exc:
            raise StudioError("PTS/durée de frame inconnus : préservation non vérifiable.") from exc
        if duration <= 0 or (frames and pts != frames[-1]["pts"] + frames[-1]["duration"]):
            raise StudioError("PTS non contigus/monotones : mode neuronal initial non qualifié.")
        frames.append(
            {
                "frame_id": index,
                "pts": pts,
                "duration": duration,
                "duration_evidence": duration_evidence,
            }
        )
    expected = stream.get("nb_frames")
    if expected not in (None, "N/A") and int(expected) != len(frames):
        raise StudioError("Nombre de frames incomplet.")
    if frames[0]["pts"] != 0:
        raise StudioError("Origine PTS non nulle : mode neuronal initial non qualifié.")
    if len({r["duration"] for r in frames}) != 1:
        raise StudioError("VFR neuronal : refus explicite avant qualification spécifique.")
    return {
        "time_base": time_base,
        "frames": frames,
        "frame_rate": str(1 / (tb * frames[0]["duration"])),
        "policy": "EXACT_CFR_PTS_NO_RESAMPLE",
    }


def compare_timing(before: dict, after: dict) -> None:
    from fractions import Fraction

    if len(before["frames"]) != len(after["frames"]):
        raise StudioError("Nombre de frames modifié.")
    a, b = Fraction(before["time_base"]), Fraction(after["time_base"])
    for source, output in zip(before["frames"], after["frames"], strict=True):
        if (
            source["pts"] * a != output["pts"] * b
            or source["duration"] * a != output["duration"] * b
        ):
            raise StudioError("Horodatage/durée de frame modifié.")
