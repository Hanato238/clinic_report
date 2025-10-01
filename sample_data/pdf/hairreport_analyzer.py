#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified extractor for HairMetrix-like PDFs:
- Args: one PDF path
- Output: saves filtered/renamed 525x525 images and a JSON metadata file
  into temp_YYYYMMDD directory (same location as PDF).
- temp_extracted_images is automatically deleted after processing.

Requirements:
  pip install pymupdf4llm Pillow
"""

import os
import re
import sys
import json
import shutil
import pathlib
from datetime import datetime
from typing import Dict, Any
from PIL import Image

# Third-party
import pymupdf4llm  # PyMuPDF4LLM

# ---------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------
ALLOWED_SIZES = {(525, 525), (525, 526), (526, 525), (526, 526)}
RENAME_MAP = {
    "0-0": "Frontal_1_left",
    "0-1": "Frontal_2",
    "0-2": "vertex_center",
    "1-0": "occipital",
}

# ---------------------------------------------------------------------
# Image helpers
# ---------------------------------------------------------------------
def extract_all_images(pdf_path: str, output_dir: str) -> None:
    """Extract all images to output_dir using PyMuPDF4LLM."""
    pathlib.Path(output_dir).mkdir(parents=True, exist_ok=True)
    pymupdf4llm.to_markdown(
        doc=pdf_path,
        write_images=True,
        image_path=output_dir,
        image_format="png",
        dpi=300,
    )

def filter_images_by_size(source_dir: str, target_dir: str, allowed_sizes: set) -> int:
    """Copy only images whose sizes match allowed_sizes."""
    pathlib.Path(target_dir).mkdir(parents=True, exist_ok=True)
    count = 0
    for name in os.listdir(source_dir):
        if not name.lower().endswith(".png"):
            continue
        src = os.path.join(source_dir, name)
        try:
            with Image.open(src) as img:
                if img.size in allowed_sizes:
                    shutil.copy2(src, os.path.join(target_dir, name))
                    count += 1
        except Exception:
            pass
    return count

def rename_filtered_images(image_dir: str) -> int:
    """Rename images in image_dir according to RENAME_MAP patterns."""
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

# ---------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------
def convert_pdf_to_markdown_string(pdf_path: str) -> str:
    """Convert the PDF to a Markdown string."""
    return pymupdf4llm.to_markdown(doc=pdf_path)

def extract_and_format_report_data(markdown_text: str) -> Dict[str, Any]:
    """Parse the first report line and extract name, birth date, appointment date."""
    SEARCH_STRING = "HairMetrix のレポート"
    first_report_line = None
    for line in markdown_text.splitlines():
        s = line.strip()
        if s.startswith(SEARCH_STRING):
            first_report_line = s
            break
    if not first_report_line:
        return {"error": f"'{SEARCH_STRING}' で始まる行が見つかりませんでした。"}

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

# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
def main() -> int:
    if len(sys.argv) != 2:
        print("使い方: python unified_extract.py <path/to/file.pdf>")
        return 1

    pdf_path = sys.argv[1]
    if not os.path.isfile(pdf_path):
        print(f"PDFが見つかりません: {pdf_path}")
        return 1

    # PDFと同じディレクトリに temp_YYYYMMDD を作成
    pdf_dir = os.path.dirname(os.path.abspath(pdf_path))
    today = datetime.now().strftime("%Y%m%d")
    tmp_root = os.path.join(pdf_dir, f"temp_{today}")
    os.makedirs(tmp_root, exist_ok=True)

    raw_img_dir = os.path.join(tmp_root, "temp_extracted_images")
    filtered_dir = os.path.join(tmp_root, "filtered_images")
    json_dir = tmp_root

    # 1) Extract & filter/rename images
    extract_all_images(pdf_path, raw_img_dir)
    n_filtered = filter_images_by_size(raw_img_dir, filtered_dir, ALLOWED_SIZES)
    n_renamed = rename_filtered_images(filtered_dir)

    # → 処理後に raw_img_dir を削除
    shutil.rmtree(raw_img_dir, ignore_errors=True)

    # 2) Parse text -> JSON
    md_text = convert_pdf_to_markdown_string(pdf_path)
    report_data = extract_and_format_report_data(md_text)

    # 3) Save JSON
    json_path = os.path.join(json_dir, "report_metadata.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)

    # 4) Summary
    print("\n=== Extraction Summary ===")
    print(f"Temp root: {tmp_root}")
    print(f" - Filtered images: {filtered_dir}  (filtered={n_filtered}, renamed={n_renamed})")
    print(f" - JSON:            {json_path}")
    print("\nファイルは PDF と同じディレクトリ内の temp_YYYYMMDD フォルダに保存されます。")
    print("temp_extracted_images は削除済みです。")

    return 0

if __name__ == "__main__":
    sys.exit(main())
