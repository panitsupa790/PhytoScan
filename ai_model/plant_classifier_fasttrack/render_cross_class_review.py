from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


def render_page(output: Path, pairs: list[dict], page: int) -> None:
    cell_width, image_height, label_height = 310, 230, 76
    pair_height = image_height + label_height
    canvas = Image.new("RGB", (cell_width * 2, 40 + pair_height * len(pairs)), "white")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    draw.text((10, 12), f"Cross-class pHash review page {page} (visual adjudication required)", fill="black", font=font)
    for row, pair in enumerate(pairs):
        top = 40 + row * pair_height
        for column, side in enumerate(("left", "right")):
            path = Path(pair[side])
            left = column * cell_width
            try:
                with Image.open(path) as image:
                    image = ImageOps.exif_transpose(image).convert("RGB")
                    fitted = ImageOps.contain(image, (cell_width - 12, image_height - 12), Image.Resampling.LANCZOS)
                    canvas.paste(fitted, (left + (cell_width - fitted.width) // 2, top + (image_height - fitted.height) // 2))
            except Exception:
                draw.rectangle((left, top, left + cell_width - 1, top + image_height - 1), fill="#dddddd")
            label = (
                f"{pair['pair_id']} | {pair[f'{side}_plant']} | d={pair['distance']}\n"
                f"{path.name[:46]}\n"
                f"{str(path.parent)[-46:]}"
            )
            draw.multiline_text((left + 4, top + image_height + 3), label, fill="black", font=font, spacing=2)
            draw.rectangle((left, top, left + cell_width - 1, top + pair_height - 1), outline="#777777")
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, quality=92)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit = json.loads(args.audit.read_text(encoding="utf-8"))
    examples = audit["cross_class_near_duplicate_examples"]
    rows = []
    for index, item in enumerate(examples, start=1):
        rows.append(
            {
                "pair_id": f"cross-class-{index:03d}",
                **item,
                "review_status": "pending",
                "same_or_near_duplicate": "",
                "label_issue": "",
                "safe_to_keep_both_in_same_component": "",
                "review_notes": "",
            }
        )
    manifest = args.output / "cross_class_near_duplicate_review.csv"
    args.output.mkdir(parents=True, exist_ok=True)
    with manifest.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    page_size = 5
    for start in range(0, len(rows), page_size):
        page = start // page_size + 1
        render_page(args.output / f"cross_class_review_{page:02d}.jpg", rows[start : start + page_size], page)
    print(f"WROTE {len(rows)} pairs to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
