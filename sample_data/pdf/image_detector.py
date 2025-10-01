import pymupdf4llm
import pathlib
import sys
import os
import shutil
from PIL import Image
from typing import List

# ------------------------------------------------------------------------------
# 定数定義
# ------------------------------------------------------------------------------

# 抽出されたすべての画像を一時的に保存するディレクトリ
TEMP_IMAGE_DIR = "temp_extracted_images"
# フィルタリングされた画像を保存する最終的なディレクトリ
FILTERED_IMAGE_DIR = "filtered_images"

# リネームパターンマップ: (ファイル名に含まれるパターン: 新しいファイル名)
# PyMuPDF4LLMが出力するファイル名 (例: image_p0_b0_0-0.png) の中の数字部分を基にリネームします。
RENAME_MAP = {
    "0-0": "Frontal_1_left",
    "0-1": "Frontal_2",
    "0-2": "vertex_center",
    "1-0": "occipital",
}

# ------------------------------------------------------------------------------
# 1. 画像抽出関数 (PyMuPDF4LLMを使用)
# ------------------------------------------------------------------------------

def extract_all_images(pdf_path: str, output_dir: str = TEMP_IMAGE_DIR) -> None:
    """
    PyMuPDF4LLMを使用してPDFからすべての画像を抽出し、指定されたディレクトリに保存します。
    """
    pathlib.Path(output_dir).mkdir(exist_ok=True)
    
    print(f"📄 PDFファイル '{pdf_path}' からすべての画像を '{output_dir}' に抽出中...")
    
    pymupdf4llm.to_markdown(
        doc=pdf_path,
        write_images=True,
        image_path=output_dir,
        image_format="png",
        dpi=300
    )
    print(f"✅ 画像抽出完了: 画像は一時的に '{output_dir}' に保存されました。")

# ------------------------------------------------------------------------------
# 2. 画像フィルタリング関数 (Pillowを使用)
# ------------------------------------------------------------------------------

def filter_images_by_size(
    source_dir: str = TEMP_IMAGE_DIR, 
    target_dir: str = FILTERED_IMAGE_DIR, 
    allowed_sizes: List[tuple] = [(525, 525), (525, 526), (526, 525), (526, 526)]
) -> None:
    """
    指定されたディレクトリ内の画像を読み込み、特定のサイズに一致するものだけを
    別のターゲットディレクトリにコピーします。
    """
    pathlib.Path(target_dir).mkdir(exist_ok=True)
    
    print(f"\n🔍 '{source_dir}' 内の画像をサイズ {allowed_sizes} でフィルタリング中...")

    filtered_count = 0
    
    for filename in os.listdir(source_dir):
        if filename.lower().endswith(('.png')):
            source_path = os.path.join(source_dir, filename)
            
            try:
                with Image.open(source_path) as img:
                    width, height = img.size
                    
                    if (width, height) in allowed_sizes:
                        target_path = os.path.join(target_dir, filename)
                        shutil.copy2(source_path, target_path)
                        # print(f"  抽出: {filename} ({width}x{height})")
                        filtered_count += 1
                    
            except IOError:
                pass # ファイルを開けなかった場合はスキップ

    print(f"✅ フィルタリング完了: {filtered_count} 個の画像が '{target_dir}' にコピーされました。")

# ------------------------------------------------------------------------------
# 3. 画像リネーム関数 (osモジュールを使用)
# ------------------------------------------------------------------------------

def rename_filtered_images(image_dir: str = FILTERED_IMAGE_DIR) -> None:
    """
    特定のパターンに一致する画像ファイル名 (PNG) を、指定された名前にリネームします。
    """
    print(f"\n🏷️ '{image_dir}' 内の画像をリネーム中...")
    renamed_count = 0
    
    for filename in os.listdir(image_dir):
        # ファイルが.pngであることを確認
        if filename.lower().endswith('.png'):
            base_name = os.path.splitext(filename)[0]
            extension = os.path.splitext(filename)[1]
            
            # リネームパターンをチェック
            for pattern, new_name in RENAME_MAP.items():
                # ファイル名にパターンが含まれているかチェック (例: '...0-0'がbase_nameに含まれるか)
                if pattern in base_name:
                    old_path = os.path.join(image_dir, filename)
                    # 新しいファイル名を作成: {新しい名前}.png
                    new_filename = new_name + extension
                    new_path = os.path.join(image_dir, new_filename)
                    
                    try:
                        # リネームを実行
                        os.rename(old_path, new_path)
                        print(f"  ✅ リネーム: {filename} -> {new_filename}")
                        renamed_count += 1
                        break # 一致したら次のファイルへ
                    except OSError as e:
                        print(f"  ❌ エラー: {filename} のリネームに失敗しました: {e}")
                        
    print("-" * 30)
    print(f"✅ リネーム完了: {renamed_count} 個のファイルがリネームされました。")

# ------------------------------------------------------------------------------
# メイン処理
# ------------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("💡 使用方法: python your_script_name.py <PDFファイルのパス>")
        sys.exit(1)
    
    pdf_file_path = sys.argv[1]
    
    try:
        # 1. 画像をすべて一時フォルダに抽出
        extract_all_images(pdf_file_path, TEMP_IMAGE_DIR)
        
        # 2. 一時フォルダから特定のサイズに一致するものをフィルタリング
        target_sizes = [(525, 525), (525, 526), (526, 525), (526, 526)]
        filter_images_by_size(TEMP_IMAGE_DIR, FILTERED_IMAGE_DIR, target_sizes)

        # 3. フィルタリングされた画像をリネーム
        rename_filtered_images(FILTERED_IMAGE_DIR)

    except Exception as e:
        print(f"致命的なエラーが発生しました: {e}")

    finally:
        # 4. クリーンアップ：一時フォルダとその中身を削除
        if os.path.exists(TEMP_IMAGE_DIR):
            shutil.rmtree(TEMP_IMAGE_DIR)
            print(f"\n🗑️ 一時フォルダ '{TEMP_IMAGE_DIR}' を削除しました。")


if __name__ == "__main__":
    main()