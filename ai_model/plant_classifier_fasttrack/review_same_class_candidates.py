from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import cv2
import imagehash
import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity

from phyto_fasttrack.core import sha256_file, write_json
from phyto_fasttrack.exploratory import load_pool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Measure same-class pHash candidates without changing the pHash guard."
    )
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()


def _foreground_crop(rgb: np.ndarray) -> tuple[np.ndarray, float]:
    height, width = rgb.shape[:2]
    border = np.concatenate((rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]), axis=0)
    border_colour = np.median(border.astype(np.float32), axis=0)
    distance = np.linalg.norm(rgb.astype(np.float32) - border_colour, axis=2)
    mask = (distance >= 28).astype(np.uint8)
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    points = cv2.findNonZero(mask)
    coverage = float(mask.mean())
    if points is None or coverage < 0.02 or coverage > 0.85:
        return rgb, coverage
    x, y, crop_width, crop_height = cv2.boundingRect(points)
    pad_x = max(2, round(crop_width * 0.05))
    pad_y = max(2, round(crop_height * 0.05))
    x0, y0 = max(0, x - pad_x), max(0, y - pad_y)
    x1, y1 = min(width, x + crop_width + pad_x), min(height, y + crop_height + pad_y)
    return rgb[y0:y1, x0:x1], coverage


def _read_rgb(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        return np.asarray(image.convert("RGB"))


def _distance(left: imagehash.ImageHash, right: imagehash.ImageHash) -> int:
    return int(left - right)


def _metrics(left_path: Path, right_path: Path) -> dict[str, float | int]:
    left_rgb = _read_rgb(left_path)
    right_rgb = _read_rgb(right_path)
    left_crop, left_coverage = _foreground_crop(left_rgb)
    right_crop, right_coverage = _foreground_crop(right_rgb)
    size = (160, 160)
    left_scaled = cv2.resize(left_crop, size, interpolation=cv2.INTER_AREA)
    right_scaled = cv2.resize(right_crop, size, interpolation=cv2.INTER_AREA)
    left_gray = cv2.cvtColor(left_scaled, cv2.COLOR_RGB2GRAY)
    right_gray = cv2.cvtColor(right_scaled, cv2.COLOR_RGB2GRAY)
    ssim = float(structural_similarity(left_gray, right_gray, data_range=255))
    mae = float(np.mean(np.abs(left_scaled.astype(np.float32) - right_scaled.astype(np.float32))) / 255.0)
    left_pil = Image.fromarray(left_crop)
    right_pil = Image.fromarray(right_crop)
    return {
        "foreground_ssim": ssim,
        "foreground_mae": mae,
        "foreground_dhash_distance": _distance(imagehash.dhash(left_pil), imagehash.dhash(right_pil)),
        "foreground_whash_distance": _distance(imagehash.whash(left_pil), imagehash.whash(right_pil)),
        "left_foreground_coverage": left_coverage,
        "right_foreground_coverage": right_coverage,
        "left_width": int(left_rgb.shape[1]),
        "left_height": int(left_rgb.shape[0]),
        "right_width": int(right_rgb.shape[1]),
        "right_height": int(right_rgb.shape[0]),
    }


def main() -> int:
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    output_dir = args.output_dir
    if output_dir.exists():
        raise SystemExit(f"Refusing to overwrite output directory: {output_dir}")
    output_dir.mkdir(parents=True)
    rows, pool_audit = load_pool(config)
    distance_limit = int(config["split"]["near_duplicate_phash_distance"])
    values = np.asarray([int(row.phash, 16) for row in rows], dtype=np.uint64)
    candidates: list[dict[str, object]] = []
    for index in range(len(rows) - 1):
        xor = np.bitwise_xor(values[index + 1 :], values[index])
        distances = (
            np.bitwise_count(xor)
            if hasattr(np, "bitwise_count")
            else np.unpackbits(xor.view(np.uint8).reshape(-1, 8), axis=1).sum(axis=1)
        )
        for offset in np.nonzero(distances <= distance_limit)[0]:
            other = index + 1 + int(offset)
            left, right = rows[index], rows[other]
            if left.plant != right.plant or left.semantic_group == right.semantic_group or left.sha256 == right.sha256:
                continue
            evidence = _metrics(left.path, right.path)
            candidates.append(
                {
                    "pair_id": f"same-class-{len(candidates) + 1:04d}",
                    "plant": left.plant,
                    "left_path": str(left.path),
                    "right_path": str(right.path),
                    "left_group": left.semantic_group,
                    "right_group": right.semantic_group,
                    "left_source": left.source,
                    "right_source": right.source,
                    "phash_distance": int(distances[int(offset)]),
                    **evidence,
                }
            )
    decisions: list[dict[str, object]] = []
    for candidate in candidates:
        visibly_distinct = (
            float(candidate["foreground_ssim"]) <= 0.92
            and float(candidate["foreground_mae"]) >= 0.02
            and (
                int(candidate["foreground_dhash_distance"]) >= 6
                or int(candidate["foreground_whash_distance"]) >= 6
            )
        )
        decision = "false_phash_collision" if visibly_distinct else "uncertain"
        rationale = (
            "Different trusted semantic groups and foreground comparison exceeds the locked "
            "visual-difference rule; pHash similarity alone is a collision."
            if visibly_distinct
            else "Supplementary image evidence is not strong enough for automatic clearance; exclude both groups from debug validation."
        )
        decisions.append(
            {
                **candidate,
                "decision": decision,
                "rationale": rationale,
                "manual_label_approval_claimed": False,
            }
        )
    csv_path = output_dir / "same_class_phash_candidate_metrics.csv"
    fields = list(candidates[0]) if candidates else ["pair_id"]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(candidates)
    adjudication_path = output_dir / "same_class_phash_adjudication.json"
    adjudication = {
        "schema_version": 1,
        "purpose": "same_class_phash_leakage_adjudication_for_exploratory_split_only",
        "source_metrics_csv": str(csv_path),
        "source_metrics_csv_sha256": sha256_file(csv_path),
        "phash_distance_limit": distance_limit,
        "phash_threshold_changed": False,
        "policy": {
            "false_phash_collision": "different semantic groups AND foreground_ssim <= 0.92 AND foreground_mae >= 0.02 AND (foreground_dhash_distance >= 6 OR foreground_whash_distance >= 6)",
            "uncertain": "all remaining pHash-only pairs; both semantic components are excluded from internal debug validation",
            "confirmed_duplicates": "exact SHA or trusted same semantic group only; handled before this manifest",
            "label_issues": "not inferred by this automated same-class comparison",
        },
        "decision_counts": {
            "false_phash_collision": sum(row["decision"] == "false_phash_collision" for row in decisions),
            "uncertain": sum(row["decision"] == "uncertain" for row in decisions),
            "true_duplicate": 0,
            "label_issue": 0,
        },
        "pairs": decisions,
    }
    write_json(adjudication_path, adjudication)
    summary = {
        "schema_version": 1,
        "purpose": "same_class_phash_candidate_measurement_only",
        "decision_status": "adjudicated_with_strict_visual_difference_rule",
        "phash_distance_limit": distance_limit,
        "phash_threshold_changed": False,
        "candidate_count": len(candidates),
        "candidate_counts_by_class": {
            plant: sum(row["plant"] == plant for row in candidates) for plant in config["classes"]
        },
        "pool_audit": pool_audit,
        "metrics_csv": str(csv_path),
        "metrics_csv_sha256": sha256_file(csv_path),
        "adjudication_json": str(adjudication_path),
        "adjudication_json_sha256": sha256_file(adjudication_path),
        "decision_counts": adjudication["decision_counts"],
    }
    write_json(output_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
