from __future__ import annotations
import argparse, json, sys
from tricho_pipeline.core.config import PipelineConfig
from tricho_pipeline.core.orchestrator import Orchestrator
from tricho_pipeline.core.io_utils import newest_path_in, newest_path_and_pdf

def _cmd_newest(args) -> int:
    p = newest_path_in(args.path, dirs_only=args.dirs_only, files_only=args.files_only)
    print(p or "")
    return 0

def _cmd_newest_with_pdf(args) -> int:
    newest, pdfp = newest_path_and_pdf(args.path)
    print(json.dumps({"newest": newest, "pdf": pdfp}, ensure_ascii=False, indent=2))
    return 0

def _cmd_run(args) -> int:
    cfg = PipelineConfig(out_root=args.out_root, remove_raw_images=not args.keep_raw)
    orch = Orchestrator(cfg)
    summary = orch.run(args.json_dir, args.pdf_path, args.out_root)
    print(json.dumps({
        "temp_root": summary.temp_root,
        "filtered_images_dir": summary.filtered_images_dir,
        "final_report_json": summary.final_report_json,
        "image_counts": summary.image_counts,
        "notes": summary.notes
    }, ensure_ascii=False, indent=2))
    return 0

def _cmd_run_render(args) -> int:
    cfg = PipelineConfig(out_root=args.out_root, remove_raw_images=not args.keep_raw)
    orch = Orchestrator(cfg)
    summary, out_pdf = orch.run_and_render(
        args.json_dir, args.pdf_path, args.out_root,
        render_js=args.render_js, out_pdf=args.out_pdf, html=args.html, node_bin=args.node_bin
    )
    print(json.dumps({
        "temp_root": summary.temp_root,
        "pdf_out": out_pdf,
        "filtered_images_dir": summary.filtered_images_dir,
        "final_report_json": summary.final_report_json,
        "image_counts": summary.image_counts,
        "notes": summary.notes
    }, ensure_ascii=False, indent=2))
    return 0

def main() -> int:
    p = argparse.ArgumentParser(prog="tricho-pipeline", description="Tricho pipeline utilities")
    sub = p.add_subparsers(dest="cmd", required=True)

    # newest
    sp = sub.add_parser("newest", help="Show newest entry under a directory")
    sp.add_argument("path")
    g = sp.add_mutually_exclusive_group()
    g.add_argument("--dirs-only", action="store_true")
    g.add_argument("--files-only", action="store_true")
    sp.set_defaults(func=_cmd_newest)

    # newest-with-pdf
    sp = sub.add_parser("newest-with-pdf", help="Show newest entry and newest PDF under it")
    sp.add_argument("path")
    sp.set_defaults(func=_cmd_newest_with_pdf)

    # run
    sp = sub.add_parser("run", help="Run extraction+analysis pipeline")
    sp.add_argument("json_dir")
    sp.add_argument("pdf_path")
    sp.add_argument("--out-root")
    sp.add_argument("--keep-raw", action="store_true")
    sp.set_defaults(func=_cmd_run)

    # run-render
    sp = sub.add_parser("run-render", help="Run pipeline then render PDF via Node.js")
    sp.add_argument("json_dir")
    sp.add_argument("pdf_path")
    sp.add_argument("--out-root")
    sp.add_argument("--keep-raw", action="store_true")
    sp.add_argument("--render-js", required=True, help="Path to Node render.js")
    sp.add_argument("--out-pdf", help="Output PDF name (optional)")
    sp.add_argument("--html", help="Override report.html path (optional)")
    sp.add_argument("--node-bin", default="node", help='Node binary (default: "node")')
    sp.set_defaults(func=_cmd_run_render)

    args = p.parse_args()
    return args.func(args)

if __name__ == "__main__":
    sys.exit(main())
