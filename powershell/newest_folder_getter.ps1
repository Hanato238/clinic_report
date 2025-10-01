# 対象ディレクトリを指定
$dir = "C:\ProgramData\Canfield\Databases\HairMetrixDB"

    
$latestFolder = Get-ChildItem -Path $dir -Directory |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1 |
    ForEach-Object { $_.FullName }

$latestFolder