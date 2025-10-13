from __future__ import annotations
import os, re, json, shutil, pathlib, logging
from typing import Dict, Any, Optional, Set, Tuple
from PIL import Image
import pymupdf4llm

from tricho_pipeline.core.config import ExtractorConfig

def setup_logger(out_root: str, name: str = "pdf_extractor", level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if logger.handlers:
        return logger
    pathlib.Path(out_root).mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    fh = logging.FileHandler(os.path.join(out_root, "pdf_extractor.log"), encoding="utf-8")
    fh.setLevel(level); fh.setFormatter(fmt); logger.addHandler(fh)
    ch = logging.StreamHandler(); ch.setLevel(level); ch.setFormatter(fmt); logger.addHandler(ch)
    return logger

class PdfExtractor:
    def __init__(self, config: Optional[ExtractorConfig] = None, logger: Optional[logging.Logger] = None) -> None:
        self.config = config or ExtractorConfig()
        self.logger = logger or logging.getLogger("pdf_extractor")

    def extract_pdf_assets(self, pdf_path: str, out_root: str) -> Dict[str, Any]:
        self.logger.info("=== PDF抽出処理開始 ===")
        raw_img_dir = os.path.join(out_root, "temp_extracted_images")
        filtered_dir = os.path.join(out_root, "filtered_images")
        json_path = os.path.join(out_root, "report_metadata.json")

        self._extract_all_images(pdf_path, raw_img_dir)
        n_filtered = self._filter_images_by_size(raw_img_dir, filtered_dir, self.config.allowed_sizes)
        n_renamed = self._rename_filtered_images(filtered_dir, self.config.rename_map)
        md = self._convert_pdf_to_markdown_string(pdf_path)
        report = self._extract_and_format_report_data(md)
        self._write_json(json_path, report)

        info = {
            "raw_img_dir": raw_img_dir,
            "filtered_dir": filtered_dir,
            "json_path": json_path,
            "n_filtered": n_filtered,
            "n_renamed": n_renamed,
        }
        self.logger.info("=== PDF抽出処理完了 ===")
        return info

    def _extract_all_images(self, pdf_path: str, output_dir: str) -> None:
        pathlib.Path(output_dir).mkdir(parents=True, exist_ok=True)
        pymupdf4llm.to_markdown(doc=pdf_path, write_images=True, image_path=output_dir, image_format="png", dpi=300)

    def _filter_images_by_size(self, src: str, dst: str, allowed: Set[Tuple[int,int]]) -> int:
        pathlib.Path(dst).mkdir(parents=True, exist_ok=True)
        cnt = 0
        for name in os.listdir(src):
            if not name.lower().endswith(".png"): continue
            p = os.path.join(src, name)
            try:
                with Image.open(p) as im:
                    if im.size in allowed:
                        shutil.copy2(p, os.path.join(dst, name))
                        cnt += 1
            except Exception:
                pass
        return cnt

    def _rename_filtered_images(self, image_dir: str, rename_map: Dict[str, str]) -> int:
        ren = 0
        for filename in sorted(os.listdir(image_dir)):
            if not filename.lower().endswith(".png"): continue
            base, ext = os.path.splitext(filename)
            m = re.search(r'-(\d+)-(\d+)$', base)
            if not m: continue
            key = f"{m.group(1)}-{m.group(2)}"
            new_base = rename_map.get(key)
            if not new_base: continue
            old = os.path.join(image_dir, filename)
            new = os.path.join(image_dir, new_base + ext)
            if os.path.exists(new):
                i = 2
                while os.path.exists(os.path.join(image_dir, f"{new_base}_{i}{ext}")):
                    i += 1
                new = os.path.join(image_dir, f"{new_base}_{i}{ext}")
            os.rename(old, new); ren += 1
        return ren

    def _convert_pdf_to_markdown_string(self, pdf_path: str) -> str:
        return pymupdf4llm.to_markdown(doc=pdf_path)

    def _extract_and_format_report_data(self, markdown_text: str) -> Dict[str, Any]:
        import re
        SEARCH = "HairMetrix のレポート"
        first = next((ln.strip() for ln in markdown_text.splitlines() if ln.strip().startswith(SEARCH)), None)
        if not first:
            return {"error": f"'{SEARCH}' が見つかりません"}
        pat = re.compile(r"HairMetrix のレポート\s+([\w\s]+?)、(\d{4}/\d{2}/\d{2}).*診察：\s*(\d{4}/\d{2}/\d{2})")
        m = pat.search(first)
        if not m:
            return {"error": "レポート行の解析に失敗しました。", "raw": first}
        return {"name": m.group(1).strip(), "date_of_birth": m.group(2), "appointment_date": m.group(3)}

    def _write_json(self, path: str, data: Dict[str, Any]) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
