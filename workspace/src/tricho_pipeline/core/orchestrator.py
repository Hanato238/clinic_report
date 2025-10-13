from __future__ import annotations
import os, json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from tricho_pipeline.core.config import PipelineConfig
from tricho_pipeline.core.io_utils import (
    make_default_out_root, ensure_dir, write_json, try_remove, read_json
)
from tricho_pipeline.extraction.pdf_extractor import PdfExtractor, setup_logger
from tricho_pipeline.analysis.tricho_analyzer import run_on_dir as tricho_run_on_dir
from tricho_pipeline.core.node_render import render_pdf_with_node

@dataclass
class OrchestratorSummary:
    temp_root: str
    filtered_images_dir: str | None
    final_report_json: str
    image_counts: Dict[str, int]
    notes: List[str]

class Orchestrator:
    def __init__(self, config: PipelineConfig | None = None) -> None:
        self.config = config or PipelineConfig()

    def run(self, json_dir: str, pdf_path: str, out_root: str | None = None) -> OrchestratorSummary:
        out_root = out_root or self.config.out_root or make_default_out_root(pdf_path)
        ensure_dir(out_root)
        logger = setup_logger(out_root)
        extractor = PdfExtractor(logger=logger)
        pdf_info = extractor.extract_pdf_assets(pdf_path, out_root)

        tricho_results = tricho_run_on_dir(json_dir)
        tricho_out_path = os.path.join(out_root, "tricho_analysis.json")
        write_json(tricho_out_path, tricho_results)

        if self.config.remove_raw_images:
            raw_dir = pdf_info.get("raw_img_dir")
            if raw_dir:
                try_remove(raw_dir)

        report_metadata = read_json(pdf_info["json_path"])

        final_report = { "report_metadata": report_metadata, "tricho_analysis": tricho_results }
        final_report_path = os.path.join(out_root, "tricho_data.json")
        write_json(final_report_path, final_report)

        try_remove(pdf_info["json_path"])
        try_remove(tricho_out_path)

        summary_json = os.path.join(out_root, "summary.json")
        summary_txt  = os.path.join(out_root, "summary.txt")
        summary = OrchestratorSummary(
            temp_root=out_root,
            filtered_images_dir=pdf_info.get("filtered_dir"),
            final_report_json=final_report_path,
            image_counts={"filtered": pdf_info.get("n_filtered", 0), "renamed": pdf_info.get("n_renamed", 0)},
            notes=[
                "temp_extracted_images は削除済みです。" if self.config.remove_raw_images else "temp_extracted_images は残しています。",
                "report_metadata.json と tricho_analysis.json は削除済みです。"
            ]
        )
        write_json(summary_json, {
            "temp_root": summary.temp_root,
            "filtered_images_dir": summary.filtered_images_dir,
            "final_report_json": summary.final_report_json,
            "image_counts": summary.image_counts,
            "notes": summary.notes
        })
        with open(summary_txt, "w", encoding="utf-8") as f:
            f.write("=== Run Summary ===\n")
            f.write(f"Temp root: {summary.temp_root}\n")
            f.write(f"Filtered images: {summary.filtered_images_dir}\n")
            f.write(f"Tricho data: {summary.final_report_json}\n")
            f.write(f"Images (filtered/renamed): {summary.image_counts['filtered']}/{summary.image_counts['renamed']}\n")
            f.write("temp_extracted_images, report_metadata.json, tricho_analysis.json は削除済みです。\n")

        return summary

    # === New: ③ run の後で Node.js による PDF レンダリングまで実施するユーティリティ ===
    def run_and_render(
        self,
        json_dir: str,
        pdf_path: str,
        out_root: str | None = None,
        *,
        render_js: str,
        out_pdf: Optional[str] = None,
        html: Optional[str] = None,
        node_bin: str = "node",
    ) -> tuple[OrchestratorSummary, str]:
        """
        1) run() で temp を作る
        2) Node の render.js を使って PDF を生成
        戻り値: (summary, out_pdf_path)
        """
        summary = self.run(json_dir, pdf_path, out_root)
        out_pdf_path = render_pdf_with_node(
            temp_dir=summary.temp_root,
            render_js=render_js,
            out_pdf=out_pdf,
            html=html,
            node_bin=node_bin,
        )
        return summary, out_pdf_path
