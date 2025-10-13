from __future__ import annotations
import os, json, subprocess
from typing import Optional, Sequence

class NodeRenderError(RuntimeError):
    pass

def render_pdf_with_node(
    temp_dir: str,
    render_js: str,
    *,
    out_pdf: Optional[str] = None,
    html: Optional[str] = None,
    node_bin: str = "node",
    env: Optional[dict] = None,
    check: bool = True,
) -> str:
    """
    Node.js の render.js を用いて temp_dir => PDF を生成。
    - temp_dir 内に tricho_data.json / filtered_images を前提
    - out_pdf を与えるとそのファイル名を使用（render.js の第2引数）
    - html を与えると --html フラグでテンプレートを差し替え
    戻り値: 想定される出力 PDF パス（render.js のログと一致するはず）
    """
    if not os.path.isdir(temp_dir):
        raise NodeRenderError(f"temp_dir not found: {temp_dir}")
    if not os.path.isfile(render_js):
        raise NodeRenderError(f"render_js not found: {render_js}")

    cmd: list[str] = [node_bin, render_js, temp_dir]
    if out_pdf:
        cmd.append(out_pdf)
    if html:
        cmd.extend(["--html", html])

    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if check and proc.returncode != 0:
        raise NodeRenderError(
            f"render.js failed (code {proc.returncode}).\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )

    # render.js は実際の出力パスを STDOUT に出すので、ログから拾いたければここで解析してもよい。
    # ただし out_pdf を明示していればそれを返す。指定が無ければ親ディレクトリに report-YYYYMMDD-HHMMSS.pdf の想定。
    if out_pdf:
        return out_pdf
    # 親ディレクトリ推定 + 接頭辞推定（最後の行 "✔ Done. Saved: <path>" に合わせて抽出してもよい）
    # ここでは簡潔に temp_dir の親を返す（実パスはログに出る）
    return os.path.dirname(os.path.abspath(temp_dir))
