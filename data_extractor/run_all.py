#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_all.py
- Args: 2つ
   1) tricho_0..3.json が格納されているフォルダパス
   2) PDFファイルのパス

処理内容:
  * PDFと同じディレクトリに temp_YYYYMMDD を作成
  * pdf_extractor.extract_pdf_assets() を呼ぶ
  * tricho_analyzer.run_on_dir() を呼ぶ
  * temp_extracted_images を削除
  * report_metadata.json + tricho_analysis.json を統合して final_report.json を保存
  * 元の report_metadata.json / tricho_analysis.json は削除
  * summary.json / summary.txt を保存
"""

import os
import sys
import json
import shutil
from datetime import datetime

CURDIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, CURDIR)

import pdf_extractor
import tricho_analyzer

def main() -> int:
    if len(sys.argv) != 3:
        print("使い方: python run_all.py /path/to/json_dir /path/to/report.pdf")
        return 1

    json_dir = sys.argv[1]
    pdf_path = sys.argv[2]

    if not os.path.isdir(json_dir):
        print(f"JSONフォルダが見つかりません: {json_dir}")
        return 1
    if not os.path.isfile(pdf_path):
        print(f"PDFが見つかりません: {pdf_path}")
        return 1

    pdf_dir = os.path.dirname(os.path.abspath(pdf_path))

    # temp_YYYYMMDD の作成
    today = datetime.now().strftime("%Y%m%d")
    out_root = os.path.join(pdf_dir, f"temp_{today}")
    os.makedirs(out_root, exist_ok=True)

    # 1) PDF抽出パート
    pdf_info = pdf_extractor.extract_pdf_assets(pdf_path, out_root)

    # 2) tricho解析パート
    tricho_results = tricho_analyzer.run_on_dir(json_dir)
    tricho_out_path = os.path.join(out_root, "tricho_analysis.json")
    with open(tricho_out_path, "w", encoding="utf-8") as f:
        json.dump(tricho_results, f, ensure_ascii=False, indent=2)

    # 3) raw画像ディレクトリの削除
    raw_dir = pdf_info.get("raw_img_dir")
    if raw_dir and os.path.isdir(raw_dir):
        shutil.rmtree(raw_dir, ignore_errors=True)

    # 4) report_metadata.json の読み込み
    with open(pdf_info["json_path"], "r", encoding="utf-8") as f:
        report_metadata = json.load(f)

    # 5) 統合ファイルの作成
    final_report = {
        "report_metadata": report_metadata,
        "tricho_analysis": tricho_results
    }
    final_report_path = os.path.join(out_root, "tricho_data.json")
    with open(final_report_path, "w", encoding="utf-8") as f:
        json.dump(final_report, f, ensure_ascii=False, indent=2)

    # 6) 元の中間ファイルを削除
    try:
        os.remove(pdf_info["json_path"])
    except FileNotFoundError:
        pass
    try:
        os.remove(tricho_out_path)
    except FileNotFoundError:
        pass

    # 7) サマリーの保存
    summary = {
        "temp_root": out_root,
        "filtered_images_dir": pdf_info.get("filtered_dir"),
        "final_report_json": final_report_path,
        "image_counts": {
            "filtered": pdf_info.get("n_filtered"),
            "renamed": pdf_info.get("n_renamed"),
        },
        "notes": [
            "temp_extracted_images は削除済みです。",
            "report_metadata.json と tricho_analysis.json は削除済みです。"
        ]
    }
    summary_json = os.path.join(out_root, "summary.json")
    with open(summary_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    summary_txt = os.path.join(out_root, "summary.txt")
    with open(summary_txt, "w", encoding="utf-8") as f:
        f.write("=== Run Summary ===\n")
        f.write(f"Temp root: {out_root}\n")
        f.write(f"Filtered images: {pdf_info.get('filtered_dir')}\n")
        f.write(f"Tricho data: {final_report_path}\n")
        f.write(f"Images (filtered/renamed): {pdf_info.get('n_filtered')}/{pdf_info.get('n_renamed')}\n")
        f.write("temp_extracted_images, report_metadata.json, tricho_analysis.json は削除済みです。\n")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
