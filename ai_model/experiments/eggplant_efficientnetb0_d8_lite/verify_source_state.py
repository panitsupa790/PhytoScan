from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
EXPERIMENT_ROOT = Path(__file__).resolve().parent
SOURCES = ("dataset/raw", "dataset/cleaned", "dataset/split")


def snapshot() -> dict[str, object]:
    result: dict[str, object] = {}
    for relative_root in SOURCES:
        source_root = ROOT / relative_root
        files = []
        for path in sorted((item for item in source_root.rglob("*") if item.is_file()), key=lambda item: item.as_posix().casefold()):
            stat = path.stat()
            files.append({"path": path.relative_to(ROOT).as_posix(), "size": stat.st_size, "modified_time_ns": stat.st_mtime_ns})
        result[relative_root] = {"file_count": len(files), "total_bytes": sum(row["size"] for row in files), "files": files}
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Metadata-only immutable source audit for D8 Lite")
    parser.add_argument("--write-before", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.write_before == args.verify:
        parser.error("Choose exactly one action")
    before_path = EXPERIMENT_ROOT / "source_state_before.json"
    current = snapshot()
    if args.write_before:
        before_path.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({name: {"file_count": value["file_count"], "total_bytes": value["total_bytes"]} for name, value in current.items()}, indent=2))
        return 0
    before = json.loads(before_path.read_text(encoding="utf-8"))
    unchanged = {name: before[name] == current[name] for name in SOURCES}
    report = {"method": "path, size, and modified-time metadata; test image bytes were not opened", "unchanged": unchanged, "pass": all(unchanged.values())}
    (EXPERIMENT_ROOT / "source_state_verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
