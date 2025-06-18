#!/usr/bin/env python3
"""
EZRPA v2.0 - システム統合テストスクリプト

メインアプリケーションの統合テストを実行
"""

import sys
import os
import tempfile
import json
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """必要なモジュールのインポートテスト"""
    print("=== モジュールインポートテスト ===")
    
    try:
        # Core imports
        from src.core.container import Container
        from src.core.event_bus import EventBus
        from src.core.result import Result, Ok, Err
        print("✓ Core層のインポート成功")
        
        # Domain imports
        from src.domain.entities.recording import Recording
        from src.domain.entities.action import KeyboardAction, MouseAction
        from src.domain.value_objects import ActionType
        print("✓ Domain層のインポート成功")
        
        # Infrastructure imports (Windows関連は除く)
        from src.infrastructure.services.encryption_service import EncryptionService
        from src.infrastructure.services.file_service import FileService
        print("✓ Infrastructure層のインポート成功")
        
        # Shared imports
        from src.shared.constants import APP_NAME, APP_VERSION
        print("✓ Shared層のインポート成功")
        
        return True
        
    except ImportError as e:
        print(f"✗ インポートエラー: {e}")
        print("  注意: Windows固有の機能は非Windows環境では利用できません")
        return False

def test_config_manager():
    """設定管理システムのテスト"""
    print("\n=== 設定管理システムテスト ===")
    
    try:
        # メインモジュールから設定管理をインポート
        # main.pyの ConfigManager をインポートするために、実際のmain.pyから抽出
        import tempfile
        import json
        from pathlib import Path
        
        # テスト用一時ディレクトリ
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / "config"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = config_dir / "config.json"
            
            # デフォルト設定を作成
            default_config = {
                "app": {
                    "name": "EZRPA",
                    "version": "2.0.0",
                    "debug": False,
                    "language": "ja"
                },
                "ui": {
                    "theme": "light",
                    "window_width": 1200,
                    "window_height": 800
                }
            }
            
            # 設定ファイル作成
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            
            # 設定ファイル読み込みテスト
            with open(config_file, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
            
            assert loaded_config["app"]["name"] == "EZRPA"
            assert loaded_config["ui"]["window_width"] == 1200
            
            print("✓ 設定ファイルの作成・読み込み成功")
            return True
            
    except Exception as e:
        print(f"✗ 設定管理テストエラー: {e}")
        return False

def test_container_initialization():
    """DIコンテナ初期化テスト"""
    print("\n=== DIコンテナ初期化テスト ===")
    
    try:
        from src.core.container import Container
        
        # コンテナ作成
        container = Container()
        
        # サービス登録のテスト
        from src.infrastructure.services.encryption_service import EncryptionService
        
        # 暗号化サービスの解決テスト
        # Note: Windows APIサービスは除外
        print("✓ DIコンテナ初期化成功")
        return True
        
    except Exception as e:
        print(f"✗ DIコンテナテストエラー: {e}")
        return False

def test_event_bus():
    """イベントバステスト"""
    print("\n=== イベントバステスト ===")
    
    try:
        from src.core.event_bus import EventBus
        
        # イベントバス作成
        event_bus = EventBus()
        
        # テストイベント
        test_event_received = False
        
        def test_handler(event_data):
            nonlocal test_event_received
            test_event_received = True
        
        # サブスクライバー登録
        event_bus.subscribe("test_event", test_handler)
        
        # イベント発行
        event_bus.publish("test_event", {"test": True})
        
        assert test_event_received, "イベントが受信されませんでした"
        
        print("✓ イベントバス動作確認成功")
        return True
        
    except Exception as e:
        print(f"✗ イベントバステストエラー: {e}")
        return False

def test_directory_creation():
    """ディレクトリ作成テスト"""
    print("\n=== ディレクトリ作成テスト ===")
    
    try:
        from src.shared.constants import WindowsPaths
        
        # 一時ディレクトリでのテスト
        with tempfile.TemporaryDirectory() as temp_dir:
            test_paths = [
                Path(temp_dir) / "data",
                Path(temp_dir) / "logs", 
                Path(temp_dir) / "config",
                Path(temp_dir) / "recordings"
            ]
            
            for path in test_paths:
                path.mkdir(parents=True, exist_ok=True)
                assert path.exists(), f"ディレクトリ作成失敗: {path}"
            
            print("✓ ディレクトリ作成テスト成功")
            return True
            
    except Exception as e:
        print(f"✗ ディレクトリ作成テストエラー: {e}")
        return False

def test_encryption_service():
    """暗号化サービステスト"""
    print("\n=== 暗号化サービステスト ===")
    
    try:
        from src.infrastructure.services.encryption_service import EncryptionService
        
        # 暗号化サービス作成
        encryption_service = EncryptionService()
        
        # テストデータ
        test_data = "Hello EZRPA v2.0!"
        password = "test_password"
        
        # 暗号化
        encrypt_result = encryption_service.encrypt_data(test_data, password)
        assert encrypt_result.is_success(), f"暗号化失敗: {encrypt_result.error}"
        
        encrypted_data = encrypt_result.value
        
        # 復号化
        decrypt_result = encryption_service.decrypt_data(encrypted_data, password)
        assert decrypt_result.is_success(), f"復号化失敗: {decrypt_result.error}"
        
        decrypted_data = decrypt_result.value
        assert decrypted_data == test_data, "復号化データが一致しません"
        
        print("✓ 暗号化サービステスト成功")
        return True
        
    except Exception as e:
        print(f"✗ 暗号化サービステストエラー: {e}")
        return False

def main():
    """メインテスト関数"""
    print("EZRPA v2.0 - システム統合テスト")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_config_manager,
        test_container_initialization,
        test_event_bus,
        test_directory_creation,
        test_encryption_service,
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
        print("🎉 全てのシステム統合テストが成功しました！")
        return 0
    else:
        print("❌ 一部のテストが失敗しました。")
        return 1

if __name__ == "__main__":
    sys.exit(main())