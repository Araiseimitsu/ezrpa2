"""
EZRPA v2.0 - メインエントリーポイント

Windows環境でのRPAアプリケーション起動スクリプト
"""

import sys
import os
from pathlib import Path

# Windows環境でのパス設定
if sys.platform == "win32":
    # Windows固有の設定
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = ""

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """メイン関数"""
    print("EZRPA v2.0 - クリーンアーキテクチャ版")
    print("Windows環境での実行を確認中...")
    
    if sys.platform != "win32":
        print("警告: このアプリケーションはWindows環境専用です")
        return 1
    
    print("基盤構築フェーズ - ディレクトリ構造作成完了")
    return 0

if __name__ == "__main__":
    sys.exit(main())