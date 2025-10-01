import pymupdf4llm
import sys
import os
import re
import json
from typing import Dict, Any

# ------------------------------------------------------------------------------
# 抽出・解析関数
# ------------------------------------------------------------------------------

def convert_pdf_to_markdown_string(pdf_path: str) -> str:
    """PDFをMarkdown文字列として抽出し、返す関数。"""
    if not os.path.exists(pdf_path):
        print(f"❌ エラー: ファイルが見つかりません: {pdf_path}")
        return ""
    try:
        # PyMuPDF4LLMでPDFをMarkdownに変換
        md_text = pymupdf4llm.to_markdown(doc=pdf_path)
        return md_text
    except Exception as e:
        print(f"変換エラーが発生しました: {e}")
        return ""

def extract_and_format_report_data(markdown_text: str) -> Dict[str, Any]:
    """
    Markdownテキストから最初のレポート行を抽出し、名前、生年月日、診察日を解析して
    JSON形式で出力するための辞書を返します。
    """
    SEARCH_STRING = "HairMetrix のレポート"
    
    # Markdown文字列を行ごとに分割
    lines = markdown_text.splitlines()
    
    # 最初の該当行を見つける
    first_report_line = None
    for line in lines:
        stripped_line = line.strip()
        if stripped_line.startswith(SEARCH_STRING):
            first_report_line = stripped_line
            break

    if not first_report_line:
        print(f"❌ '{SEARCH_STRING}' で始まる行が見つかりませんでした。")
        return {"error": f"'{SEARCH_STRING}' で始まる行が見つかりませんでした。"}

    # 実際には名前と生年月日の区切りが「、」であることを利用し、パターンを具体的にします
    pattern = re.compile(
        r"HairMetrix のレポート\s+"  # 固定の開始文字列
        r"([\w\s]+?)"                # グループ1: 名前 (次の「、」まで)
        r"、"                       # 名前と生年月日の区切り
        r"(\d{4}/\d{2}/\d{2})"       # グループ2: 生年月日 (YYYY/MM/DD)
        r".*診察：\s*"               # 「• 診察：」およびその前後の任意の文字
        r"(\d{4}/\d{2}/\d{2})"       # グループ3: 診察日 (YYYY/MM/DD)
    )

    match = pattern.search(first_report_line)

    if match:
        name = match.group(1).strip()
        dob = match.group(2)
        appointment_date = match.group(3)
        
        # 抽出結果を辞書として返す
        return {
            "name": name,
            "date_of_birth": dob,
            "appointment_date": appointment_date
        }
    else:
        print("❌ パターンに一致するデータ (名前、生年月日、診察日) を抽出できませんでした。")
        print(f"解析対象の行: {first_report_line}")
        return {"error": "レポート行の解析に失敗しました。"}

# ------------------------------------------------------------------------------
# メイン処理
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("💡 使用方法: python your_script_name.py <PDFファイルのパス>")
        sys.exit(1)
    
    pdf_file_path = sys.argv[1]
    
    # 1. PDFからMarkdown文字列を取得
    print(f"📄 PDFファイル '{pdf_file_path}' からMarkdownを抽出中...")
    markdown_content = convert_pdf_to_markdown_string(pdf_file_path)

    if markdown_content:
        # 2. 最初のレポート行を解析し、データを抽出
        report_data = extract_and_format_report_data(markdown_content)
        
        # 3. 結果をJSON形式で出力
        print("\n" + "=" * 40)
        print("✅ 抽出データ (JSON形式):")
        print("=" * 40)
        
        # JSONを整形して出力
        json_output = json.dumps(report_data, indent=4, ensure_ascii=False)
        print(json_output)