"""Fail when application version metadata drifts between deliverables."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:[-+][0-9A-Za-z.-]+)?$")


def read_json(relative_path: str) -> dict:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def main() -> int:
    canonical = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if not SEMVER.fullmatch(canonical):
        print(f"VERSION is not valid semantic versioning: {canonical!r}", file=sys.stderr)
        return 1

    versions = {
        "frontend/package.json": read_json("frontend/package.json")["version"],
        "frontend/package-lock.json": read_json("frontend/package-lock.json")["version"],
        "mobile/package.json": read_json("mobile/package.json")["version"],
        "mobile/package-lock.json": read_json("mobile/package-lock.json")["version"],
        "mobile/app.json": read_json("mobile/app.json")["expo"]["version"],
        "desktop/package.json": read_json("desktop/package.json")["version"],
        "desktop/package-lock.json": read_json("desktop/package-lock.json")["version"],
    }
    mismatches = {path: value for path, value in versions.items() if value != canonical}
    if mismatches:
        print(f"Expected every deliverable to use version {canonical}:", file=sys.stderr)
        for path, value in mismatches.items():
            print(f"- {path}: {value}", file=sys.stderr)
        return 1

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if f"## [{canonical}]" not in changelog:
        print(f"CHANGELOG.md has no section for version {canonical}", file=sys.stderr)
        return 1

    print(f"Release metadata is consistent at version {canonical}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
