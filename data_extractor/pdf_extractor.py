#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pdf_extractor.py (OOP + Logging)
- Responsibility: PDF処理のみ（画像抽出→フィルタ→リネーム、テキスト→JSON）
- Temp管理は行いません（呼び出し側が out_root を渡す）

Usage:
  python pdf_extractor.py /path/to/report.pdf /path/to/out_root

Outputs (under out_root):
  - temp_extracted_images/  (raw images; 呼び出し側で削除可)
  - filtered_images/        (525x525近辺のみ)
  - report_metadata.json    (氏名/生年月日/診察日)
  - pdf_extractor.log       (実行ログ)
"""

from __future__ import annotations

import os
import re
import sys
import json
import shutil
import pathlib
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Set, Tuple

from PIL import Image
import pymupdf4llm  # pip install pymupdf4llm


# =========================
# 設定データ
# =========================
DEFAULT_ALLOWED_SIZES: Set[Tuple[int, int]] = {
    (525, 525), (525, 526), (526, 525), (526, 526)
}
DEFAULT_RENAME_MAP: Dict[str, str] = {
    "0-0": "frontal_1_left",
    "0-1": "mid",
    "0-2": "vertex_center",
    "1-0": "occipital",
}


@dataclass(frozen=True)
class ExtractorConfig:
    allowed_sizes: Set[Tuple[int, int]] = field(default_factory=lambda: set(DEFAULT_ALLOWED_SIZES))
    rename_map: Dict[str, str] = field(default_factory=lambda: dict(DEFAULT_RENAME_MAP))


# =========================
# ロガー構築
# =========================
def _setup_logger(out_root: str, name: str = "pdf_extractor", level: int = logging.INFO) -> logging.Logger:
    """out_root 配下にファイルログを作り、同時にコンソールにも出す"""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 二重追加防止
    if logger.handlers:
        return logger

    # out_root を作成（念のため）
    pathlib.Path(out_root).mkdir(parents=True, exist_ok=True)

    # フォーマット
    fmt = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")

    # ファイルハンドラ
    fh = logging.FileHandler(os.path.join(out_root, "pdf_extractor.log"), encoding="utf-8")
    fh.setLevel(level)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # コンソール（stderr）
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    return logger


# =========================
# 本体クラス
# =========================
class PdfExtractor:
    def __init__(self, config: Optional[ExtractorConfig] = None, logger: Optional[logging.Logger] = None) -> None:
        self.config = config or ExtractorConfig()
        self.logger = logger or logging.getLogger("pdf_extractor")

    # --- 公開API ---
    def extract_pdf_assets(self, pdf_path: str, out_root: str) -> Dict[str, Any]:
        """
        画像抽出→フィルタ→リネーム、テキスト抽出→report_metadata.json 作成までを実行。
        戻り値のキーは従来互換:
            raw_img_dir, filtered_dir, json_path, n_filtered, n_renamed
        """
        self.logger.info("=== PDF抽出処理開始 ===")
        self.logger.info("PDF: %s", pdf_path)
        self.logger.info("出力ルート: %s", out_root)

        raw_img_dir = os.path.join(out_root, "temp_extracted_images")
        filtered_dir = os.path.join(out_root, "filtered_images")
        json_path = os.path.join(out_root, "report_metadata.json")

        # 1) 画像抽出
        self._extract_all_images(pdf_path, raw_img_dir)

        # 2) 画像フィルタ
        n_filtered = self._filter_images_by_size(raw_img_dir, filtered_dir, self.config.allowed_sizes)

        # 3) リネーム
        n_renamed = self._rename_filtered_images(filtered_dir, self.config.rename_map)

        # 4) テキスト→JSON
        md_text = self._convert_pdf_to_markdown_string(pdf_path)
        report_data = self._extract_and_format_report_data(md_text)
        self._write_json(json_path, report_data)

        info = {
            "raw_img_dir": raw_img_dir,
            "filtered_dir": filtered_dir,
            "json_path": json_path,
            "n_filtered": n_filtered,
            "n_renamed": n_renamed,
        }
        self.logger.info("処理結果: %s", json.dumps(info, ensure_ascii=False))
        self.logger.info("=== PDF抽出処理完了 ===")
        return info

    # --- 内部処理 ---
    def _extract_all_images(self, pdf_path: str, output_dir: str) -> None:
        pathlib.Path(output_dir).mkdir(parents=True, exist_ok=True)
        self.logger.info("画像抽出: %s -> %s", pdf_path, output_dir)
        try:
            pymupdf4llm.to_markdown(
                doc=pdf_path,
                write_images=True,
                image_path=output_dir,
                image_format="png",
                dpi=300,
            )
            self.logger.info("画像抽出完了")
        except Exception as e:
            self.logger.exception("画像抽出に失敗しました: %s", e)
            raise

    def _filter_images_by_size(self, source_dir: str, target_dir: str, allowed_sizes: Set[Tuple[int, int]]) -> int:
        pathlib.Path(target_dir).mkdir(parents=True, exist_ok=True)
        count = 0
        self.logger.info("画像フィルタ: %s -> %s (許可サイズ: %s)", source_dir, target_dir, sorted(list(allowed_sizes)))
        for name in os.listdir(source_dir):
            if not name.lower().endswith(".png"):
                continue
            src = os.path.join(source_dir, name)
            try:
                with Image.open(src) as img:
                    if img.size in allowed_sizes:
                        shutil.copy2(src, os.path.join(target_dir, name))
                        count += 1
                        self.logger.debug("保持: %s (%sx%s)", name, img.size[0], img.size[1])
                    else:
                        self.logger.debug("除外: %s (%sx%s)", name, img.size[0], img.size[1])
            except Exception as e:
                self.logger.warning("画像読み込み失敗のため除外: %s  (%s)", src, e)
        self.logger.info("フィルタ結果: %d 枚", count)
        return count

    # 置き換え版: 末尾 -i-j のみをキーにして厳密マッピング
    def _rename_filtered_images(self, image_dir: str, rename_map: Dict[str, str]) -> int:
        """
        image_dir 内の PNG について、ファイル名（拡張子除く）末尾が `-i-j` に一致するものだけを
        RENAME_MAP（例: {"0-0": "frontal_1_left", ...}）でリネームする。
        既存ファイル名との重複は _2, _3 ... を自動付番して回避。
        """
        self.logger.info("画像リネーム(末尾 -i-j のみマッチ): %s", image_dir)
        renamed = 0
        # 予測可能性のためソート
        for filename in sorted(os.listdir(image_dir)):
            if not filename.lower().endswith(".png"):
                continue
            base, ext = os.path.splitext(filename)

            # 末尾に「-i-j」がある場合だけ拾う（例: ...pdf-0-1）
            m = re.search(r'-(\d+)-(\d+)$', base)
            if not m:
                self.logger.debug("スキップ(末尾に -i-j が無い): %s", filename)
                continue

            key = f"{m.group(1)}-{m.group(2)}"  # 例: "0-1"
            new_base = rename_map.get(key)
            if not new_base:
                self.logger.debug("スキップ(未定義キー %s): %s", key, filename)
                continue

            old_path = os.path.join(image_dir, filename)
            new_path = os.path.join(image_dir, new_base + ext)

            # 既に存在する場合は _2, _3 ... と連番付与
            if os.path.exists(new_path):
                i = 2
                while True:
                    candidate = os.path.join(image_dir, f"{new_base}_{i}{ext}")
                    if not os.path.exists(candidate):
                        new_path = candidate
                        break
                    i += 1

            os.rename(old_path, new_path)
            self.logger.info("  %s -> %s  (key=%s)", filename, os.path.basename(new_path), key)
            renamed += 1

        self.logger.info("リネーム完了: %d 件", renamed)
        return renamed

    def _convert_pdf_to_markdown_string(self, pdf_path: str) -> str:
        self.logger.info("PDF→Markdown 変換開始")
        try:
            md = pymupdf4llm.to_markdown(doc=pdf_path)
            self.logger.info("PDF→Markdown 完了（%d 文字）", len(md))
            return md
        except Exception as e:
            self.logger.exception("PDF→Markdown 変換に失敗しました: %s", e)
            raise

    def _extract_and_format_report_data(self, markdown_text: str) -> Dict[str, Any]:
        self.logger.info("レポートデータ抽出開始")
        SEARCH_STRING = "HairMetrix のレポート"
        first_report_line = None
        for line in markdown_text.splitlines():
            s = line.strip()
            if s.startswith(SEARCH_STRING):
                first_report_line = s
                break
        if not first_report_line:
            self.logger.warning("'%s' で始まる行が見つかりません。", SEARCH_STRING)
            return {"error": f"'{SEARCH_STRING}' で始まる行が見つかりませんでした。"}

        pattern = re.compile(
            r"HairMetrix のレポート\s+"
            r"([\w\s]+?)"            # 氏名（適宜調整）
            r"、"
            r"(\d{4}/\d{2}/\d{2})"   # 生年月日
            r".*診察：\s*"
            r"(\d{4}/\d{2}/\d{2})"   # 診察日
        )
        m = pattern.search(first_report_line)
        if not m:
            self.logger.warning("レポート行の解析に失敗: %s", first_report_line)
            return {"error": "レポート行の解析に失敗しました。", "raw": first_report_line}

        result = {
            "name": m.group(1).strip(),
            "date_of_birth": m.group(2),
            "appointment_date": m.group(3),
        }
        self.logger.info("レポート抽出結果: %s", json.dumps(result, ensure_ascii=False))
        return result

    def _write_json(self, path: str, data: Dict[str, Any]) -> None:
        self.logger.info("JSON書き出し: %s", path)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.exception("JSON書き出しに失敗: %s", e)
            raise


# =========================
# 互換API（既存呼び出し側を壊さない）
# =========================
def extract_pdf_assets(pdf_path: str, out_root: str) -> dict:
    """
    既存の関数シグネチャを維持。
    内部で PdfExtractor + ロガー(file+console) を構築して実行。
    """
    logger = _setup_logger(out_root)
    extractor = PdfExtractor(logger=logger)
    return extractor.extract_pdf_assets(pdf_path, out_root)


# =========================
# CLI
# =========================
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("使い方: python pdf_extractor.py /path/to/report.pdf /path/to/out_root")
        sys.exit(1)
    pdf_path = sys.argv[1]
    out_root = sys.argv[2]

    # out_rootにログを残す
    logger = _setup_logger(out_root)
    try:
        info = PdfExtractor(logger=logger).extract_pdf_assets(pdf_path, out_root)
        print(json.dumps(info, ensure_ascii=False, indent=2))
    except Exception as e:
        logger.exception("致命的エラー: %s", e)
        print(json.dumps({"error": str(e)}, ensure_ascii=False, indent=2))
        sys.exit(1)
