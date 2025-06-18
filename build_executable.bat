@echo off
REM EZRPA v2.0 - 実行可能ファイル作成スクリプト
REM PyInstallerを使用してWindows実行可能ファイルを作成

title EZRPA v2.0 - Build Executable

echo ==========================================================
echo EZRPA v2.0 - 実行可能ファイル作成
echo PyInstaller Build Script
echo ==========================================================
echo.

REM 仮想環境のチェック
if exist "venv\Scripts\python.exe" (
    echo 仮想環境を使用します。
    set PYTHON_EXE=venv\Scripts\python.exe
    set PIP_EXE=venv\Scripts\pip.exe
    call venv\Scripts\activate.bat
) else (
    echo システムPythonを使用します。
    set PYTHON_EXE=python
    set PIP_EXE=pip
)

REM PyInstallerのインストール確認
%PIP_EXE% show pyinstaller >nul 2>&1
if %errorLevel% neq 0 (
    echo PyInstallerをインストールしています...
    %PIP_EXE% install pyinstaller>=5.13.0
    if %errorLevel% neq 0 (
        echo エラー: PyInstallerのインストールに失敗しました。
        pause
        exit /b 1
    )
)

REM ビルドディレクトリのクリーンアップ
echo 既存のビルドファイルをクリーンアップしています...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist
if exist "*.spec" del /q *.spec

REM アイコンファイルの確認
set ICON_FILE=
if exist "assets\icons\ezrpa.ico" set ICON_FILE=--icon=assets\icons\ezrpa.ico

REM PyInstallerでビルド実行
echo.
echo 実行可能ファイルを作成しています...
echo 処理には数分かかる場合があります。

%PYTHON_EXE% -m PyInstaller ^
    --name=EZRPA ^
    --onefile ^
    --windowed ^
    %ICON_FILE% ^
    --add-data="src;src" ^
    --add-data="config;config" ^
    --add-data="assets;assets" ^
    --hidden-import=PySide6.QtCore ^
    --hidden-import=PySide6.QtWidgets ^
    --hidden-import=PySide6.QtGui ^
    --hidden-import=win32api ^
    --hidden-import=win32con ^
    --hidden-import=win32gui ^
    --hidden-import=cryptography ^
    --hidden-import=sqlalchemy ^
    --collect-submodules=PySide6 ^
    --collect-submodules=cryptography ^
    --exclude-module=tkinter ^
    --exclude-module=matplotlib ^
    --exclude-module=scipy ^
    --exclude-module=numpy ^
    --log-level=INFO ^
    main.py

if %errorLevel% neq 0 (
    echo.
    echo エラー: ビルドに失敗しました。
    echo.
    echo トラブルシューティング:
    echo 1. 依存関係が正しくインストールされているか確認
    echo 2. Python環境が正常に動作するか確認
    echo 3. ウイルス対策ソフトがビルドプロセスを阻害していないか確認
    echo.
    pause
    exit /b 1
)

REM ビルド成功の確認
if exist "dist\EZRPA.exe" (
    echo.
    echo ==========================================================
    echo ビルドが正常に完了しました！
    echo ==========================================================
    echo.
    echo 実行可能ファイル: dist\EZRPA.exe
    
    REM ファイルサイズの表示
    for %%A in (dist\EZRPA.exe) do echo ファイルサイズ: %%~zA bytes
    
    echo.
    echo 配布用ファイルの準備...
    
    REM 配布用ディレクトリの作成
    if not exist "release" mkdir release
    
    REM 実行可能ファイルをコピー
    copy "dist\EZRPA.exe" "release\"
    
    REM 設定ファイルのサンプルをコピー
    if exist "config\config.json" copy "config\config.json" "release\config_sample.json"
    
    REM READMEファイルをコピー
    if exist "README.md" copy "README.md" "release\"
    
    REM ライセンスファイルをコピー
    if exist "LICENSE" copy "LICENSE" "release\"
    
    echo.
    echo 配布用ファイルが release\ ディレクトリに準備されました。
    echo.
    echo 次の手順:
    echo 1. release\EZRPA.exe をテスト実行
    echo 2. 問題がなければ配布用パッケージの作成
    echo 3. または Windows Installer の作成
    echo.
    
    REM テスト実行の提案
    choice /C YN /M "作成された実行可能ファイルをテスト実行しますか"
    if !errorlevel! equ 1 (
        echo テスト実行中...
        start "" "dist\EZRPA.exe"
    )
    
) else (
    echo.
    echo エラー: 実行可能ファイルが作成されませんでした。
    echo ビルドログを確認してください。
    pause
    exit /b 1
)

echo.
echo ビルドプロセスが完了しました。
pause