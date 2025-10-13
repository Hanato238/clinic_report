from __future__ import annotations
import os, json, shutil
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

def ensure_dir(p: str) -> None:
    os.makedirs(p, exist_ok=True)

def make_default_out_root(pdf_path: str) -> str:
    today = datetime.now().strftime("%Y%m%d")
    base = os.path.dirname(os.path.abspath(pdf_path))
    out_root = os.path.join(base, f"temp_{today}")
    ensure_dir(out_root)
    return out_root

def write_json(path: str, data: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def read_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def try_remove(path: str) -> None:
    try:
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
        elif os.path.isfile(path):
            os.remove(path)
    except FileNotFoundError:
        pass

# === New: ① 指定パス内部で最も新しいパス（ファイル/フォルダ）を取得 ===
def newest_path_in(root: str, *, dirs_only: bool=False, files_only: bool=False) -> Optional[str]:
    """
    root 直下のエントリのうち、更新時刻(mtime)が最も新しいもののフルパスを返す。
    dirs_only=True ならディレクトリのみ、files_only=True ならファイルのみを対象。
    見つからなければ None。
    """
    if not os.path.isdir(root):
        return None
    latest = None
    latest_ts = -1.0
    with os.scandir(root) as it:
        for e in it:
            if dirs_only and not e.is_dir():   continue
            if files_only and not e.is_file(): continue
            try:
                ts = e.stat().st_mtime
                if ts > latest_ts:
                    latest_ts = ts
                    latest = e.path
            except FileNotFoundError:
                continue
    return latest

# === New: ② 指定パス内で「最も新しいパス」と「その配下で最も新しいPDF」を取得 ===
def newest_path_and_pdf(root: str) -> Tuple[Optional[str], Optional[str]]:
    """
    root 直下で最も新しいエントリ(newest)を取得。
    newest がディレクトリなら、その配下(非再帰)で最も新しい PDF を探す。
    newest がファイルなら、拡張子が .pdf の場合のみ pdf とみなす。
    いずれも見つからなければ None を返す。
    """
    newest = newest_path_in(root)
    if newest is None:
        return None, None

    pdf_path = None
    if os.path.isdir(newest):
        # そのディレクトリ直下で一番新しい PDF を探す
        latest_pdf = None
        latest_ts = -1.0
        with os.scandir(newest) as it:
            for e in it:
                if e.is_file() and e.name.lower().endswith(".pdf"):
                    try:
                        ts = e.stat().st_mtime
                        if ts > latest_ts:
                            latest_ts = ts
                            latest_pdf = e.path
                    except FileNotFoundError:
                        continue
        pdf_path = latest_pdf
    else:
        # newest がファイルなら PDF かどうか
        if newest.lower().endswith(".pdf"):
            pdf_path = newest

    return newest, pdf_path
