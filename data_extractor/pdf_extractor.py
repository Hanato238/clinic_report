#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pdf_extractor.py
- Responsibility: PDF処理のみ（画像抽出→フィルタ→リネーム、テキスト→JSON）
- Temp管理は行いません（呼び出し側が out_root を渡す）

Usage:
  python pdf_extractor.py /path/to/report.pdf /path/to/out_root

Outputs (under out_root):
  - temp_extracted_images/  (raw images; 呼び出し側で削除可)
  - filtered_images/        (525x525近辺のみ)
  - report_metadata.json    (氏名/生年月日/診察日)
"""

import os
import re
import sys
import json
import shutil
import pathlib
from typing import Dict, Any
from PIL import Image
import pymupdf4llm  # pip install pymupdf4llm

ALLOWED_SIZES = {(525, 525), (525, 526), (526, 525), (526, 526)}
RENAME_MAP = {
    "0-0": "frontal_1_left",
    "0-1": "frontal_2",
    "0-2": "vertex_center",
    "1-0": "occipital",
}

def extract_all_images(pdf_path: str, output_dir: str) -> None:
    pathlib.Path(output_dir).mkdir(parents=True, exist_ok=True)
    pymupdf4llm.to_markdown(
        doc=pdf_path,
        write_images=True,
        image_path=output_dir,
        image_format="png",
        dpi=300,
    )

def filter_images_by_size(source_dir: str, target_dir: str, allowed_sizes: set) -> int:
    pathlib.Path(target_dir).mkdir(parents=True, exist_ok=True)
    count = 0
    for name in os.listdir(source_dir):
        if not name.lower().endswith(".png"):
            continue
        src = os.path.join(source_dir, name)
        try:
            from PIL import Image
            with Image.open(src) as img:
                if img.size in allowed_sizes:
                    shutil.copy2(src, os.path.join(target_dir, name))
                    count += 1
        except Exception:
            pass
    return count

def rename_filtered_images(image_dir: str) -> int:
    renamed = 0
    for filename in os.listdir(image_dir):
        if not filename.lower().endswith(".png"):
            continue
        base, ext = os.path.splitext(filename)
        for pattern, new_name in RENAME_MAP.items():
            if pattern in base:
                old_path = os.path.join(image_dir, filename)
                new_path = os.path.join(image_dir, new_name + ext)
                if os.path.exists(new_path):
                    i = 2
                    while True:
                        candidate = os.path.join(image_dir, f"{new_name}_{i}{ext}")
                        if not os.path.exists(candidate):
                            new_path = candidate
                            break
                        i += 1
                os.rename(old_path, new_path)
                renamed += 1
                break
    return renamed

def convert_pdf_to_markdown_string(pdf_path: str) -> str:
    return pymupdf4llm.to_markdown(doc=pdf_path)

def extract_and_format_report_data(markdown_text: str) -> Dict[str, Any]:
    SEARCH_STRING = "HairMetrix のレポート"
    first_report_line = None
    for line in markdown_text.splitlines():
        s = line.strip()
        if s.startswith(SEARCH_STRING):
            first_report_line = s
            break
    if not first_report_line:
        return {"error": f"'{SEARCH_STRING}' で始まる行が見つかりませんでした。"}

    import re
    pattern = re.compile(
        r"HairMetrix のレポート\s+"
        r"([\w\s]+?)"
        r"、"
        r"(\d{4}/\d{2}/\d{2})"
        r".*診察：\s*"
        r"(\d{4}/\d{2}/\d{2})"
    )
    m = pattern.search(first_report_line)
    if not m:
        return {"error": "レポート行の解析に失敗しました。", "raw": first_report_line}

    return {
        "name": m.group(1).strip(),
        "date_of_birth": m.group(2),
        "appointment_date": m.group(3),
    }

def extract_pdf_assets(pdf_path: str, out_root: str) -> dict:
    raw_img_dir = os.path.join(out_root, "temp_extracted_images")
    filtered_dir = os.path.join(out_root, "filtered_images")
    json_path = os.path.join(out_root, "report_metadata.json")

    extract_all_images(pdf_path, raw_img_dir)
    n_filtered = filter_images_by_size(raw_img_dir, filtered_dir, ALLOWED_SIZES)
    n_renamed = rename_filtered_images(filtered_dir)

    md_text = convert_pdf_to_markdown_string(pdf_path)
    report_data = extract_and_format_report_data(md_text)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)

    return {
        "raw_img_dir": raw_img_dir,
        "filtered_dir": filtered_dir,
        "json_path": json_path,
        "n_filtered": n_filtered,
        "n_renamed": n_renamed,
    }

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("使い方: python pdf_extractor.py /path/to/report.pdf /path/to/out_root")
        sys.exit(1)
    info = extract_pdf_assets(sys.argv[1], sys.argv[2])
    print(json.dumps(info, ensure_ascii=False, indent=2))
