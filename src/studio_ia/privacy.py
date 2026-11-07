"""Allowlisted export, without paths, raw metadata, private errors or command lines."""

from pathlib import Path

from studio_ia import __version__


def public_job_report(row: dict) -> dict:
    request = row.get("request", {})
    result = row.get("result") or {}
    plan = row.get("plan") or result.get("plan") or {}
    media = plan.get("media", {})
    return {
        "schema_version": 1,
        "application_version": __version__,
        "state": row["state"],
        "source_name": Path(request.get("source", "unknown")).name,
        "output_name": Path(request.get("destination", "unknown")).name,
        "profile": request.get("profile"),
        "filters": plan.get("filters"),
        "width": plan.get("width"),
        "height": plan.get("height"),
        "duration": media.get("duration"),
        "audio_count": len(media.get("audio", [])),
        "engine_version": plan.get("engine_version"),
        "assertions": result.get("assertions"),
        "source_sha256": result.get("source_sha256"),
        "output_sha256": result.get("output_sha256"),
        "elapsed_seconds": row.get("elapsed_seconds"),
        "note": "Chemins, métadonnées libres et erreurs brutes exclus ; relire avant partage.",
    }
