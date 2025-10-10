@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem =========================
rem 設定（必要に応じて編集）
rem =========================
rem 引数:
rem   %1 : 検索対象のベースディレクトリ（省略時はこのbatのあるフォルダ）
rem   %2 : get_newest_folder.ps1 のパス（省略時は同フォルダ）
rem   %3 : run_all.py のパス（省略時は同フォルダ）
rem   %4 : render.js のパス（省略時は同フォルダ）

set "SCRIPT_DIR=%~dp0"
set "BASE_DIR=%~1"
if "%BASE_DIR%"=="" set "BASE_DIR=%SCRIPT_DIR%"

set "PS1_PATH=%~2"
if "%PS1_PATH%"=="" set "PS1_PATH=%SCRIPT_DIR%get_newest_folder.ps1"

set "PY_PATH=%~3"
if "%PY_PATH%"=="" set "PY_PATH=%SCRIPT_DIR%run_all.py"

set "JS_PATH=%~4"
if "%JS_PATH%"=="" set "JS_PATH=%SCRIPT_DIR%render.js"

rem ログ設定（任意）
for /f "tokens=1-3 delims=/- " %%a in ("%date%") do set "TODAY=%%a-%%b-%%c"
for /f "tokens=1-2 delims=:." %%a in ("%time%") do set "NOW=%%a-%%b"
set "LOG_DIR=%SCRIPT_DIR%logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1
set "LOG_FILE=%LOG_DIR%\run_%TODAY%_%NOW%.log"

echo [START] %date% %time%  >> "%LOG_FILE%"
echo BASE_DIR=%BASE_DIR%     >> "%LOG_FILE%"
echo PS1_PATH=%PS1_PATH%     >> "%LOG_FILE%"
echo PY_PATH=%PY_PATH%       >> "%LOG_FILE%"
echo JS_PATH=%JS_PATH%       >> "%LOG_FILE%"

rem =========================
rem 依存コマンド確認
rem =========================
where powershell >nul 2>&1 || (echo [ERROR] powershell が見つかりません & goto :die)
where python     >nul 2>&1 || (echo [ERROR] python が見つかりません & goto :die)
where node       >nul 2>&1 || (echo [ERROR] node が見つかりません   & goto :die)

if not exist "%PS1_PATH%" (echo [ERROR] PS1がありません: "%PS1_PATH%" & goto :die)
if not exist "%PY_PATH%"  (echo [ERROR] Pythonがありません: "%PY_PATH%" & goto :die)
if not exist "%JS_PATH%"  (echo [ERROR] NodeJSがありません: "%JS_PATH%" & goto :die)

rem =========================
rem ① PowerShell: 最新フォルダAとPDF B の取得
rem   ※ get_newest_folder.ps1 は次の2行を標準出力に返す想定
rem      FOLDER_A=...
rem      FILE_B=...
rem =========================
echo [STEP1] PowerShell 実行中...  >> "%LOG_FILE%"
set "FOLDER_A="
set "FILE_B="

for /f "usebackq tokens=1,* delims==" %%K in (`
  powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1_PATH%" -BaseDir "%BASE_DIR%"
`) do (
  if /I "%%~K"=="FOLDER_A" set "FOLDER_A=%%~L"
  if /I "%%~K"=="FILE_B"   set "FILE_B=%%~L"
)

if not defined FOLDER_A (echo [ERROR] FOLDER_A が取得できませんでした & goto :die)
if not defined FILE_B   (echo [WARN ] FILE_B が取得できませんでした（既存PDFが無い想定かも）)

echo FOLDER_A=%FOLDER_A% >> "%LOG_FILE%"
echo FILE_B  =%FILE_B%   >> "%LOG_FILE%"

rem =========================
rem ② Python: temp データ作成（json/txt/log 等）
rem   ・stdout の最後の行を TEMP_DIR に採用
rem   ・"TEMP_DIR=..." と出す場合にも対応
rem =========================
echo [STEP2] Python 実行中...      >> "%LOG_FILE%"
set "TEMP_DIR="
set "LASTLINE="

for /f "usebackq delims=" %%I in (`
  python "%PY_PATH%" "%FOLDER_A%" "%FILE_B%"
`) do (
  set "LASTLINE=%%~I"
  for /f "tokens=1,* delims==" %%X in ("%%~I") do (
    if /I "%%~X"=="TEMP_DIR" set "TEMP_DIR=%%~Y"
  )
)

if not defined TEMP_DIR set "TEMP_DIR=%LASTLINE%"
if defined TEMP_DIR set "TEMP_DIR=%TEMP_DIR:"=%"

if not defined TEMP_DIR (echo [ERROR] TEMP_DIR が取得できませんでした & goto :die)
if not exist "%TEMP_DIR%" (echo [ERROR] TEMP_DIR が存在しません: "%TEMP_DIR%" & goto :die)

echo TEMP_DIR=%TEMP_DIR% >> "%LOG_FILE%"

rem =========================
rem ③ Node.js: render.js で PDF 出力
rem   ・temp データのパスを引数で渡す
rem   ・stdout の最後の行を PDF_OUT として拾う（任意）
rem =========================
echo [STEP3] Node 実行中...        >> "%LOG_FILE%"
set "PDF_OUT="
for /f "usebackq delims=" %%I in (`
  node "%JS_PATH%" "%TEMP_DIR%"
`) do set "PDF_OUT=%%~I"

if defined PDF_OUT echo PDF_OUT=%PDF_OUT% >> "%LOG_FILE%"
echo [DONE ] すべて完了しました。         >> "%LOG_FILE%"

echo.
echo ===== 実行結果 =====
echo FOLDER_A: %FOLDER_A%
echo FILE_B  : %FILE_B%
echo TEMP_DIR: %TEMP_DIR%
if defined PDF_OUT echo PDF_OUT : %PDF_OUT%
echo ログ: "%LOG_FILE%"
echo =====================
echo.

endlocal
exit /b 0

:die
echo 失敗しました。ログを確認してください: "%LOG_FILE%"
endlocal
exit /b 1
