from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
EXPERIMENT_ROOT = Path(__file__).resolve().parent
SOURCES = ("dataset/raw", "dataset/cleaned", "dataset/split")
LOCKED_FILES = (
    "ai_model/configs/eggplant_final_locked.json",
    "ai_model/experiments/eggplant_d9_refinement/R2_class_weight/best_model.keras",
)
D11_ROOT = ROOT / "ai_model/experiments/eggplant_final/d11"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot() -> dict[str, object]:
    result: dict[str, object] = {"sources": {}, "locked_files": {}, "d11_files": {}}
    for relative_root in SOURCES:
        source_root = ROOT / relative_root
        files = []
        for path in sorted(
            (item for item in source_root.rglob("*") if item.is_file()),
            key=lambda item: item.as_posix().casefold(),
        ):
            stat = path.stat()
            files.append(
                {
                    "path": path.relative_to(ROOT).as_posix(),
                    "size": stat.st_size,
                    "modified_time_ns": stat.st_mtime_ns,
                }
            )
        result["sources"][relative_root] = {
            "file_count": len(files),
            "total_bytes": sum(row["size"] for row in files),
            "files": files,
        }
    for relative_path in LOCKED_FILES:
        path = ROOT / relative_path
        result["locked_files"][relative_path] = sha256_file(path)
    for path in sorted(
        (item for item in D11_ROOT.rglob("*") if item.is_file()),
        key=lambda item: item.as_posix().casefold(),
    ):
        result["d11_files"][path.relative_to(ROOT).as_posix()] = sha256_file(path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="D12 immutable input audit")
    parser.add_argument("--write-before", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.write_before == args.verify:
        parser.error("Choose exactly one action")
    before_path = EXPERIMENT_ROOT / "immutable_state_before.json"
    current = snapshot()
    if args.write_before:
        before_path.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"source_roots": {name: value["file_count"] for name, value in current["sources"].items()}, "locked_files": current["locked_files"], "d11_file_count": len(current["d11_files"])}, indent=2))
        return 0
    before = json.loads(before_path.read_text(encoding="utf-8"))
    checks = {
        "raw_unchanged": before["sources"]["dataset/raw"] == current["sources"]["dataset/raw"],
        "cleaned_unchanged": before["sources"]["dataset/cleaned"] == current["sources"]["dataset/cleaned"],
        "split_unchanged": before["sources"]["dataset/split"] == current["sources"]["dataset/split"],
        "locked_config_and_checkpoint_unchanged": before["locked_files"] == current["locked_files"],
        "d11_results_unchanged": before["d11_files"] == current["d11_files"],
    }
    result = {"pass": all(checks.values()), "checks": checks}
    (EXPERIMENT_ROOT / "immutable_state_verification.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
