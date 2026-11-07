import json

from studio_ia.privacy import public_job_report


def test_shareable_report_excludes_private_metadata_and_paths():
    row = {
        "state": "FAILED",
        "error": "/private/alice/password-in-metadata",
        "request": {"source": "/private/alice/source.mp4", "destination": "/private/alice/out.mp4"},
        "plan": {
            "media": {"raw": {"title": "private secret"}, "path": "/private/alice/source.mp4"}
        },
    }
    report = public_job_report(row)
    encoded = json.dumps(report)
    assert "/private" not in encoded and "alice" not in encoded and "secret" not in encoded
    assert report["source_name"] == "source.mp4" and report["state"] == "FAILED"
