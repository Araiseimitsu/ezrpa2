#!/usr/bin/env python3
"""
EZRPA v2.0 - クイックテストスクリプト

Windows環境での基本動作確認テスト
"""

import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_basic_imports():
    """基本的なインポートテスト"""
    print("=== 基本インポートテスト ===")
    
    try:
        # Core imports
        from src.core.result import Ok, Err, BoolResult
        print("✓ Result型のインポート成功")
        
        from src.core.container import Container
        print("✓ DIコンテナのインポート成功")
        
        from src.core.event_bus import EventBus
        print("✓ EventBusのインポート成功")
        
        # Shared imports
        from src.shared.constants import APP_NAME, APP_VERSION
        print(f"✓ 定数のインポート成功: {APP_NAME} v{APP_VERSION}")
        
        return True
        
    except ImportError as e:
        print(f"✗ インポートエラー: {e}")
        return False
    except Exception as e:
        print(f"✗ その他のエラー: {e}")
        return False

def test_result_type():
    """Result型の動作テスト"""
    print("\n=== Result型動作テスト ===")
    
    try:
        from src.core.result import Ok, Err, BoolResult
        
        # 成功ケース
        success_result = Ok(True)
        assert success_result.is_success()
        assert not success_result.is_failure()
        assert success_result.unwrap() == True
        print("✓ 成功結果の動作確認完了")
        
        # 失敗ケース
        failure_result = Err("テストエラー")
        assert not failure_result.is_success()
        assert failure_result.is_failure()
        assert failure_result.unwrap_or(False) == False
        print("✓ 失敗結果の動作確認完了")
        
        return True
        
    except Exception as e:
        print(f"✗ Result型テストエラー: {e}")
        return False

def test_config_system():
    """設定システムの基本テスト"""
    print("\n=== 設定システムテスト ===")
    
    try:
        import tempfile
        import json
        from pathlib import Path
        
        # テスト用一時ディレクトリ
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / "config"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = config_dir / "config.json"
            
            # 設定ファイル作成テスト
            test_config = {
                "app": {"name": "EZRPA", "version": "2.0.0"},
                "ui": {"theme": "light"}
            }
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(test_config, f, indent=2, ensure_ascii=False)
            
            # 設定ファイル読み込みテスト
            with open(config_file, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
            
            assert loaded_config["app"]["name"] == "EZRPA"
            print("✓ 設定ファイルの作成・読み込み確認完了")
            
        return True
        
    except Exception as e:
        print(f"✗ 設定システムテストエラー: {e}")
        return False

def test_windows_environment():
    """Windows環境チェック"""
    print("\n=== Windows環境確認 ===")
    
    try:
        import platform
        print(f"OS: {platform.system()}")
        print(f"バージョン: {platform.version()}")
        print(f"アーキテクチャ: {platform.architecture()}")
        
        if platform.system() == "Windows":
            print("✓ Windows環境での実行を確認")
            return True
        else:
            print("⚠ 非Windows環境です（開発・テスト用）")
            return True
            
    except Exception as e:
        print(f"✗ 環境確認エラー: {e}")
        return False

def main():
    """メインテスト関数"""
    print("EZRPA v2.0 - クイック動作確認テスト")
    print("=" * 50)
    
    tests = [
        test_basic_imports,
        test_result_type,
        test_config_system,
        test_windows_environment,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ テスト実行エラー: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"テスト結果: {passed} 成功, {failed} 失敗")
    
    if failed == 0:
        print("🎉 基本動作確認テストが成功しました！")
        print("\n次のステップ:")
        print("1. Windows環境で main.py を実行")
        print("2. setup_environment.bat でフル環境セットアップ")
        print("3. build_executable.bat で実行可能ファイル作成")
        return 0
    else:
        print("❌ 一部のテストが失敗しました。")
        return 1

if __name__ == "__main__":
    sys.exit(main())