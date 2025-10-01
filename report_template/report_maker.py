# main.py
import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime, date, time
import os
import time # os.path.getmtimeの代わりにpathlibで使う

# --- 設定 ---
# 1. パスAを検索するベースディレクトリ
TARGET_DIR_BASE = Path("C:/ProgramData/Canfield/Databases/HairMetrixDB") 
# 各スクリプトで利用するファイルパス
OUTPUT_JSON_FILE = Path("./combined_data.json")
OUTPUT_PDF_FILE = Path("./report_output.pdf")

# ----------------------------------------------------
# 1. パスAの取得: 最終更新が最も新しいフォルダのパスを取得
# ----------------------------------------------------
def get_latest_folder(base_dir_path: Path) -> Path:
    """
    指定されたベースディレクトリ内で、最終更新日時が最新のサブフォルダのパス (パスA) を取得します。
    """
    print(f"ステップ1: パスA (最新のフォルダ) を検索中... {base_dir_path}")
    if not base_dir_path.is_dir():
        # 実際には存在するはずですが、テスト用に警告と終了処理
        print(f"WARNING: ベースディレクトリが見つかりません: {base_dir_path}")
        # 例外を発生させ、main関数で処理
        raise FileNotFoundError(f"ベースディレクトリが見つかりません: {base_dir_path}")

    directories = [
        (d.stat().st_mtime, d) 
        for d in base_dir_path.iterdir() 
        if d.is_dir()
    ]

    if not directories:
        raise FileNotFoundError(f"ベースディレクトリ {base_dir_path} 内にフォルダが見つかりません。")

    # 最終更新日時（st_mtime）で降順ソート
    directories.sort(key=lambda x: x[0], reverse=True)
    latest_folder_a = directories[0][1]
    print(f"→ 取得されたパスA: {latest_folder_a}")
    return latest_folder_a

# ----------------------------------------------------
# 2. パスBとパスCの取得: 本日最新のフォルダとPDFパスを取得
# ----------------------------------------------------
def get_report_paths(patient_path: Path) -> tuple[Path, Path]:
    """
    パスA内で、本日最新のサブフォルダパスBと、本日日付のPDFパスCを取得します。
    """
    today = date.today()
    # 本日の00:00:00 (タイムスタンプ) を取得
    start_of_today_timestamp = datetime.combine(today, time.min).timestamp()
    today_str = today.strftime("%Y-%m-%d")
    
    # --- パスBの取得 (本日最新のサブフォルダ) ---
    data_path = None
    latest_mtime = 0.0
    
    print(f"ステップ2a: パスA内で本日({today_str})最新のフォルダ (パスB) を検索中...")
    
    for sub_dir in patient_path.iterdir():
        if sub_dir.is_dir():
            mtime = sub_dir.stat().st_mtime
            # 最終更新日時が本日以降 AND 現在の最新より新しい
            if mtime >= start_of_today_timestamp and mtime > latest_mtime:
                latest_mtime = mtime
                data_path = sub_dir
                
    if not data_path:
        raise FileNotFoundError(f"フォルダ {patient_path} 内に本日更新されたフォルダが見つかりませんでした。")
        
    print(f"→ 取得されたパスB: {data_path}")

    # --- パスCの取得 (HairReport_{YYYY-MM-DD}.pdf) ---
    pdf_filename = f"HairReport_{today_str}.pdf"
    hairreport_path = patient_path / pdf_filename # パスAの直下と仮定
    
    print(f"ステップ2b: 対象PDFパス (パスC) を決定: {hairreport_path}")
    
    return data_path, hairreport_path

# ----------------------------------------------------
# 外部コマンド実行ヘルパー関数 (変更なし)
# ----------------------------------------------------
def run_script(command_list, step_name):
    """
    外部コマンドを実行し、成功/失敗を判定するヘルパー関数
    """
    print(f"\n--- 実行: {step_name} ---")
    try:
        # check=Trueで、コマンドが非ゼロの終了コードを返した場合にCalledProcessErrorを発生させる
        result = subprocess.run(
            command_list,
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8' # 日本語の標準出力に対応
        )
        print("Success.")
        print("Stdout:\n", result.stdout.strip())
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error in {step_name}.")
        print(f"Stderr:\n", e.stderr.strip())
        return False
    except FileNotFoundError:
        print(f"Error: Command not found or script file missing for {step_name}. Is 'python'/'node' in PATH?")
        return False

# ----------------------------------------------------
# メイン実行ロジック
# ----------------------------------------------------
def main():
    # 今日検査した最新の患者のデータフォルダを取得
    try:
        patient_path = get_latest_folder(TARGET_DIR_BASE)
    except Exception as e:
        print(f"**実行失敗 (致命的なエラー)**: 最新フォルダ (パスA) の取得に失敗しました。{e}")
        sys.exit(1)
        
    # 2. 最新の検査データとレポートを取得
    try:
        data_path, hairreport_path = get_report_paths(patient_path)
    except Exception as e:
        print(f"**実行失敗 (致命的なエラー)**: 本日最新フォルダ (パスB) の取得に失敗しました。{e}")
        sys.exit(1)

    # 3. a.pyの実行
    # 引数: パスB, パスC, 出力JSONファイル
    # a.pyはJSONデータDとフォルダパスEを出力JSONに含める必要があります
    if not run_script(
        ["python", "a.py", str(data_path), str(hairreport_path), str(OUTPUT_JSON_FILE)],
        "a.pyの実行 (データDとパスEのJSON出力)"
    ):
        sys.exit(1)
    
    # フォルダパスEをJSONファイルから読み込みます
    try:
        with open(OUTPUT_JSON_FILE, 'r', encoding='utf-8') as f:
            data_d = json.load(f)
            # フォルダパスEはJSON内の 'folder_path_e' キーに格納されていると仮定
            folder_path_e_str = data_d.get("folder_path_e")
            if not folder_path_e_str:
                 raise KeyError("'folder_path_e' が JSONデータD に含まれていません。a.pyの出力を確認してください。")
            folder_path_e = Path(folder_path_e_str)
            print(f"JSONから取得されたフォルダパスE: {folder_path_e}")
            
    except Exception as e:
        print(f"**実行失敗**: a.pyの出力JSONからフォルダパスEを読み込めませんでした。{e}")
        sys.exit(1)

    # 4. render.jsの実行 (PDF作成)
    # 引数: データD (JSONファイルパス), フォルダパスE
    if not run_script(
        ["node", "render.js", str(OUTPUT_JSON_FILE), str(folder_path_e)],
        "render.jsの実行 (PDF生成)"
    ):
        sys.exit(1)

    print("\n\n✅ 全てのステップが正常に完了しました! PDFは次の場所に出力されました:", OUTPUT_PDF_FILE.resolve())

if __name__ == "__main__":
    main()