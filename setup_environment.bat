@echo off
REM EZRPA v2.0 - 環境セットアップスクリプト
REM 開発環境およびデプロイ環境の構築

title EZRPA v2.0 - Environment Setup

echo ==========================================================
echo EZRPA v2.0 - 環境セットアップ
echo Clean Architecture RPA Application
echo ==========================================================
echo.

REM 管理者権限チェック
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo 警告: 管理者権限で実行することを推奨します。
    echo 一部の設定が正常に実行されない可能性があります。
    echo.
    pause
)

REM Windows環境チェック
if not "%OS%"=="Windows_NT" (
    echo エラー: このスクリプトはWindows環境専用です。
    pause
    exit /b 1
)

REM Python環境チェック
echo Step 1: Python環境の確認
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo エラー: Pythonがインストールされていません。
    echo 以下のURLからPython 3.9以上をダウンロードしてインストールしてください:
    echo https://www.python.org/downloads/
    echo.
    echo インストール時の注意:
    echo - "Add Python to PATH" をチェックしてください
    echo - "Install for all users" を選択することを推奨します
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Python %PYTHON_VERSION% が見つかりました。

REM Pythonバージョンチェック（3.9以上）
python -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>&1
if %errorLevel% neq 0 (
    echo エラー: Python 3.9以上が必要です。現在のバージョン: %PYTHON_VERSION%
    echo 新しいバージョンをインストールしてください。
    pause
    exit /b 1
)

echo ✓ Python環境OK
echo.

REM 仮想環境の作成
echo Step 2: 仮想環境のセットアップ
if exist "venv" (
    echo 既存の仮想環境が見つかりました。
    choice /C YN /M "既存の仮想環境を再構築しますか"
    if !errorlevel! equ 1 (
        echo 既存の仮想環境を削除しています...
        rmdir /s /q venv
    ) else (
        echo 既存の仮想環境を使用します。
        goto :skip_venv_creation
    )
)

echo 仮想環境を作成しています...
python -m venv venv
if %errorLevel% neq 0 (
    echo エラー: 仮想環境の作成に失敗しました。
    pause
    exit /b 1
)

:skip_venv_creation
echo ✓ 仮想環境の準備完了
echo.

REM 仮想環境のアクティベート
echo Step 3: 仮想環境のアクティベート
call venv\Scripts\activate.bat
if %errorLevel% neq 0 (
    echo エラー: 仮想環境のアクティベートに失敗しました。
    pause
    exit /b 1
)

echo ✓ 仮想環境がアクティベートされました
echo.

REM pipのアップグレード
echo Step 4: pipのアップグレード
python -m pip install --upgrade pip
if %errorLevel% neq 0 (
    echo 警告: pipのアップグレードに失敗しました。続行します...
)

echo ✓ pipアップグレード完了
echo.

REM 基本依存関係のインストール
echo Step 5: 基本依存関係のインストール
if exist "requirements\base.txt" (
    pip install -r requirements\base.txt
    if %errorLevel% neq 0 (
        echo エラー: 基本依存関係のインストールに失敗しました。
        pause
        exit /b 1
    )
) else (
    echo 警告: requirements\base.txt が見つかりません。
    echo 手動で依存関係をインストールしてください。
)

echo ✓ 基本依存関係インストール完了
echo.

REM 開発依存関係のインストール（オプション）
echo Step 6: 開発依存関係のインストール（オプション）
choice /C YN /M "開発・テスト用の依存関係もインストールしますか"
if !errorlevel! equ 1 (
    if exist "requirements\development.txt" (
        pip install -r requirements\development.txt
        echo ✓ 開発依存関係インストール完了
    )
    if exist "requirements\test.txt" (
        pip install -r requirements\test.txt
        echo ✓ テスト依存関係インストール完了
    )
) else (
    echo 開発依存関係のインストールをスキップしました。
)

echo.

REM ディレクトリ構造の作成
echo Step 7: ディレクトリ構造の作成
if not exist "data" mkdir data
if not exist "logs" mkdir logs
if not exist "config" mkdir config
if not exist "recordings" mkdir recordings
if not exist "backups" mkdir backups

echo ✓ ディレクトリ構造作成完了
echo.

REM 設定ファイルの初期化
echo Step 8: 設定ファイルの初期化
python -c "
import json
from pathlib import Path

config_dir = Path('config')
config_file = config_dir / 'config.json'

if not config_file.exists():
    default_config = {
        'app': {
            'name': 'EZRPA',
            'version': '2.0.0',
            'debug': False,
            'language': 'ja'
        },
        'ui': {
            'theme': 'light',
            'window_width': 1200,
            'window_height': 800,
            'remember_position': True
        },
        'recording': {
            'auto_save': True,
            'capture_screenshots': True,
            'max_history': 100
        },
        'security': {
            'encrypt_recordings': True,
            'session_timeout': 3600
        },
        'logging': {
            'level': 'INFO',
            'file_rotation': True,
            'max_file_size': '10MB',
            'backup_count': 5
        }
    }
    
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(default_config, f, indent=2, ensure_ascii=False)
    
    print('デフォルト設定ファイルを作成しました。')
else:
    print('設定ファイルは既に存在します。')
"

echo ✓ 設定ファイル初期化完了
echo.

REM システムの確認テスト
echo Step 9: システム確認テスト
echo システムの動作確認を実行しています...
python -c "
import sys
print(f'Python バージョン: {sys.version}')

try:
    import PySide6
    print(f'✓ PySide6: {PySide6.__version__}')
except ImportError:
    print('✗ PySide6がインストールされていません')

try:
    import cryptography
    print(f'✓ cryptography: {cryptography.__version__}')
except ImportError:
    print('✗ cryptographyがインストールされていません')

try:
    import win32api
    print('✓ pywin32がインストールされています')
except ImportError:
    print('✗ pywin32がインストールされていません')

print('システム確認完了')
"

echo.
echo ==========================================================
echo セットアップが完了しました！
echo ==========================================================
echo.
echo 次の手順:
echo 1. run_ezrpa.bat でアプリケーションを起動
echo 2. または 'python main.py' で直接起動
echo.
echo トラブルシューティング:
echo - ログファイル: logs\ezrpa.log
echo - 設定ファイル: config\config.json
echo - 依存関係の確認: pip list
echo.
echo 開発者向け:
echo - テスト実行: pytest
echo - コード品質チェック: ruff check src/
echo - 型チェック: mypy src/
echo.

pause