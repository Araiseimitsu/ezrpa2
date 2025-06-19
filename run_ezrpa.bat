@echo off
REM EZRPA v2.0 - Windows起動スクリプト
REM Clean Architecture RPA Application

title EZRPA v2.0 - RPA Application

echo ==========================================================
echo EZRPA v2.0 - Clean Architecture RPA Application
echo Windows環境での自動化ソリューション
echo ==========================================================
echo.

REM 管理者権限チェック
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo 注意: 一部の機能には管理者権限が必要です。
    echo 必要に応じて管理者として実行してください。
    echo.
)

REM Windows環境チェック
if not "%OS%"=="Windows_NT" (
    echo エラー: このアプリケーションはWindows環境専用です。
    pause
    exit /b 1
)

REM Python環境チェック
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo エラー: Pythonがインストールされていません。
    echo Python 3.9以上をインストールしてください。
    echo https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Pythonバージョンチェック
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Python バージョン: %PYTHON_VERSION%

REM 仮想環境の確認
if exist "venv\Scripts\python.exe" (
    echo 仮想環境が見つかりました。
    set PYTHON_EXE=venv\Scripts\python.exe
    set PIP_EXE=venv\Scripts\pip.exe
) else (
    echo 仮想環境が見つかりません。システムPythonを使用します。
    set PYTHON_EXE=python
    set PIP_EXE=pip
)

REM 依存関係の確認とインストール
echo.
echo 依存関係を確認しています...
%PIP_EXE% list | findstr PySide6 >nul 2>&1
if %errorLevel% neq 0 (
    echo 必要な依存関係をインストールしています...
    %PIP_EXE% install -r requirements\base.txt
    if %errorLevel% neq 0 (
        echo エラー: 依存関係のインストールに失敗しました。
        pause
        exit /b 1
    )
)

REM データベースディレクトリの確認・作成
if not exist "data" mkdir data
if not exist "logs" mkdir logs
if not exist "config" mkdir config

REM アプリケーション起動
echo.
echo EZRPA v2.0 を起動しています...
echo 終了するには Ctrl+C を押すか、ウィンドウを閉じてください。
echo.

%PYTHON_EXE% main.py %*

REM 終了処理
if %errorLevel% neq 0 (
    echo.
    echo アプリケーションが異常終了しました (終了コード: %errorLevel%)
    echo ログファイルを確認してください: logs\ezrpa.log
    pause
) else (
    echo.
    echo EZRPA v2.0 が正常に終了しました。
)

exit /b %errorLevel%