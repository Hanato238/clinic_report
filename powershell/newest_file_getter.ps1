# ベースディレクトリ
$baseDir = "C:\ProgramData\Canfield\Databases\HairMetrixDB"

# 最新のフォルダを取得
$latestFolder = Get-ChildItem -Path $baseDir -Directory |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1 |
    ForEach-Object { $_.FullName }

# 任意の日付を指定（この日の0:00以降を対象にする）
$targetDate = Get-Date "2025-07-20" # <- (Get-Date).Date

# 最新ファイルを探す処理
$newestFile = Get-ChildItem -Path $latestFolder -File -Filter *.pdf |
    Where-Object { $_.LastWriteTime -ge $targetDate.Date } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

# 戻り値
if ($newestFile) {
    return $newestFile.FullName
} else {
    return "$($targetDate.ToShortDateString()) has no report"
}
