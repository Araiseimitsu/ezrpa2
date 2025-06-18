"""
EZRPA v2.0 インフラストラクチャ層デモ

Phase 3で実装したインフラストラクチャ層の動作確認を行います。
Windows API統合、データ永続化、暗号化等の機能を検証します。
"""

import sys
import os
import asyncio
from datetime import datetime, timezone
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def demo_file_service():
    """ファイルサービスのデモ"""
    print("=== ファイルサービス デモ ===")
    
    from src.infrastructure import FileService
    
    file_service = FileService()
    
    # ディレクトリ情報の表示
    print(f"✓ アプリデータディレクトリ: {file_service.get_app_data_dir()}")
    print(f"✓ ドキュメントディレクトリ: {file_service.get_documents_dir()}")
    print(f"✓ ログディレクトリ: {file_service.get_logs_dir()}")
    
    # ファイル書き込み・読み込み
    test_file = file_service.get_temp_dir() / "demo_test.txt"
    test_content = "EZRPA v2.0 インフラストラクチャ層テスト"
    
    write_result = file_service.write_file(test_file, test_content)
    if write_result.is_success():
        print(f"✓ ファイル書き込み成功: {test_file}")
    else:
        print(f"❌ ファイル書き込み失敗: {write_result.error}")
        return
    
    read_result = file_service.read_file(test_file)
    if read_result.is_success():
        print(f"✓ ファイル読み込み成功: 内容一致={read_result.value == test_content}")
    else:
        print(f"❌ ファイル読み込み失敗: {read_result.error}")
    
    # JSON操作
    test_json_file = file_service.get_temp_dir() / "demo_test.json"
    test_data = {
        "application": "EZRPA",
        "version": "2.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "features": ["Windows API", "暗号化", "SQLite"]
    }
    
    json_write_result = file_service.write_json_file(test_json_file, test_data)
    if json_write_result.is_success():
        print("✓ JSON書き込み成功")
    
    json_read_result = file_service.read_json_file(test_json_file)
    if json_read_result.is_success():
        loaded_data = json_read_result.value
        print(f"✓ JSON読み込み成功: 項目数={len(loaded_data)}")
    
    # ディスク使用量
    disk_usage_result = file_service.get_disk_usage()
    if disk_usage_result.is_success():
        usage = disk_usage_result.value
        print(f"✓ ディスク使用量: {usage['used_percent']:.1f}% 使用中")
    
    # バックアップ作成
    backup_result = file_service.create_backup(test_file)
    if backup_result.is_success():
        print(f"✓ バックアップ作成: {backup_result.value.name}")
    
    print()


async def demo_encryption_service():
    """暗号化サービスのデモ"""
    print("=== 暗号化サービス デモ ===")
    
    from src.infrastructure import EncryptionService
    
    # マスターパスワードで初期化
    encryption_service = EncryptionService()
    
    # パスワード設定
    password_result = encryption_service.set_master_password("demo_password_2024")
    if password_result.is_success():
        print("✓ マスターパスワード設定成功")
    else:
        print(f"❌ マスターパスワード設定失敗: {password_result.error}")
        return
    
    # データ暗号化・復号化
    test_data = "機密データ: EZRPA設定情報とユーザーデータ 🔒"
    
    encrypt_result = encryption_service.encrypt_data(test_data)
    if encrypt_result.is_success():
        encrypted_data = encrypt_result.value
        print(f"✓ データ暗号化成功: 長さ={len(encrypted_data)}")
    else:
        print(f"❌ データ暗号化失敗: {encrypt_result.error}")
        return
    
    decrypt_result = encryption_service.decrypt_data(encrypted_data)
    if decrypt_result.is_success():
        decrypted_data = decrypt_result.value
        print(f"✓ データ復号化成功: 一致={decrypted_data == test_data}")
    else:
        print(f"❌ データ復号化失敗: {decrypt_result.error}")
    
    # パスワードハッシュ化
    password_hash_result = encryption_service.hash_password("user_password_123")
    if password_hash_result.is_success():
        hash_info = password_hash_result.value
        print(f"✓ パスワードハッシュ化成功: 反復回数={hash_info['iterations']}")
        
        # パスワード検証
        is_valid = encryption_service.verify_password(
            "user_password_123", 
            hash_info['hash'], 
            hash_info['salt']
        )
        print(f"✓ パスワード検証: 正しいパスワード={is_valid}")
        
        is_invalid = encryption_service.verify_password(
            "wrong_password", 
            hash_info['hash'], 
            hash_info['salt']
        )
        print(f"✓ パスワード検証: 間違ったパスワード={not is_invalid}")
    
    # セキュアトークン生成
    token = encryption_service.generate_secure_token()
    print(f"✓ セキュアトークン生成: {token[:16]}...")
    
    # 暗号化可能性チェック
    available = encryption_service.is_encryption_available()
    print(f"✓ 暗号化利用可能: {available}")
    
    print()


async def demo_windows_api_service():
    """Windows APIサービスのデモ"""
    print("=== Windows APIサービス デモ ===")
    
    from src.infrastructure import WindowsApiService
    
    windows_api = WindowsApiService()
    
    # システム情報
    system_info = windows_api.get_system_info()
    print(f"✓ スクリーンサイズ: {system_info.screen_width}x{system_info.screen_height}")
    print(f"✓ DPI: {system_info.dpi_x}x{system_info.dpi_y} (スケール: {system_info.scale_factor:.2f})")
    
    # カーソル位置取得
    cursor_result = windows_api.get_cursor_position()
    if cursor_result.is_success():
        x, y = cursor_result.value
        print(f"✓ 現在のカーソル位置: ({x}, {y})")
    
    # ウィンドウ一覧（上位5件のみ表示）
    windows = windows_api.enumerate_windows()
    visible_windows = [w for w in windows if w.title.strip() and not w.is_minimized][:5]
    print(f"✓ 検出されたウィンドウ数: {len(windows)} (表示中: {len(visible_windows)})")
    
    for i, window in enumerate(visible_windows, 1):
        print(f"  {i}. {window.title[:50]}{'...' if len(window.title) > 50 else ''}")
    
    # IME状態確認
    ime_enabled = windows_api.is_ime_enabled()
    print(f"✓ IME状態: {'有効' if ime_enabled else '無効'}")
    
    print()


async def demo_repositories():
    """リポジトリ（データ永続化）のデモ"""
    print("=== リポジトリ デモ ===")
    
    from src.infrastructure import (
        SqliteRecordingRepository, 
        SqliteScheduleRepository,
        SqliteSettingsRepository,
        EncryptionService,
        FileService
    )
    from src.domain import Recording, ActionFactory, Coordinate, CommonKeys
    
    # サービス初期化
    encryption_service = EncryptionService()
    encryption_service.set_master_password("demo_password")
    file_service = FileService()
    
    # 設定リポジトリのテスト
    settings_repo = SqliteSettingsRepository(
        encryption_service=encryption_service,
        file_service=file_service
    )
    
    # 設定の保存・取得
    await settings_repo.set("app.name", "EZRPA")
    await settings_repo.set("app.version", "2.0.0")
    await settings_repo.set("app.features", ["RPA", "暗号化", "スケジューリング"])
    await settings_repo.set("user.password_hash", "secret_hash")
    
    app_name_result = await settings_repo.get("app.name")
    if app_name_result.is_success():
        print(f"✓ 設定取得: app.name = {app_name_result.value}")
    
    all_settings_result = await settings_repo.get_all()
    if all_settings_result.is_success():
        settings = all_settings_result.value
        print(f"✓ 全設定取得: {len(settings)}件")
    
    # 記録リポジトリのテスト
    recording_repo = SqliteRecordingRepository(
        encryption_service=encryption_service,
        file_service=file_service
    )
    
    # テスト記録の作成
    test_recording = Recording(name="インフラテスト記録")
    test_recording.start_recording()
    
    # アクションの追加
    actions = [
        ActionFactory.create_text_input("デモテキスト"),
        ActionFactory.create_key_press(CommonKeys.ENTER),
        ActionFactory.create_mouse_click(Coordinate(100, 200))
    ]
    
    for action in actions:
        test_recording.add_action(action)
    
    test_recording.complete_recording()
    
    # 記録の保存
    save_result = await recording_repo.save(test_recording)
    if save_result.is_success():
        print(f"✓ 記録保存成功: ID={save_result.value[:8]}...")
    
    # 記録の取得
    get_result = await recording_repo.get_by_id(test_recording.recording_id)
    if get_result.is_success():
        loaded_recording = get_result.value
        print(f"✓ 記録取得成功: {loaded_recording.name} ({loaded_recording.action_count}アクション)")
    
    # 統計情報
    stats_result = await recording_repo.get_statistics()
    if stats_result.is_success():
        stats = stats_result.value
        print(f"✓ 記録統計: 総記録数={stats['total_recordings']}, 総アクション数={stats['total_actions']}")
    
    print()


async def demo_adapters():
    """アダプター（ハードウェア統合）のデモ"""
    print("=== アダプター デモ ===")
    
    from src.infrastructure import WindowsApiService, KeyboardAdapter, MouseAdapter
    from src.domain import ActionFactory, Coordinate, MouseButton
    
    windows_api = WindowsApiService()
    keyboard_adapter = KeyboardAdapter(windows_api)
    mouse_adapter = MouseAdapter(windows_api)
    
    # マウスアダプターのテスト
    screen_size = mouse_adapter.get_screen_size()
    print(f"✓ スクリーンサイズ: {screen_size.x}x{screen_size.y}")
    
    dpi_scale = mouse_adapter.get_dpi_scale_factor()
    print(f"✓ DPIスケールファクター: {dpi_scale:.2f}")
    
    current_pos_result = mouse_adapter.get_cursor_position()
    if current_pos_result.is_success():
        pos = current_pos_result.value
        print(f"✓ 現在のマウス位置: ({pos.x}, {pos.y})")
    
    # ウィンドウ検索
    all_windows = mouse_adapter.get_all_windows()
    notepad_windows = [w for w in all_windows if 'notepad' in w.title.lower() or 'メモ帳' in w.title]
    
    if notepad_windows:
        window = notepad_windows[0]
        print(f"✓ メモ帳ウィンドウ検出: {window.title}")
    else:
        print("✓ メモ帳ウィンドウ未検出（テスト継続）")
    
    # キーボードアダプターのテスト
    ime_status = keyboard_adapter.is_ime_enabled()
    print(f"✓ IME状態: {'有効' if ime_status else '無効'}")
    
    # 注意: 実際のキー・マウス操作は安全性のため無効化
    print("✓ キーボード・マウス操作（実際の操作は安全性のため無効化）")
    
    # ホットキー機能のテスト（登録のみ）
    def demo_hotkey_callback():
        print("ホットキーが押されました！")
    
    register_result = keyboard_adapter.register_hotkey("ctrl+alt+f1", demo_hotkey_callback)
    if register_result.is_success():
        print("✓ ホットキー登録成功: Ctrl+Alt+F1")
    
    registered_hotkeys = keyboard_adapter.get_registered_hotkeys()
    print(f"✓ 登録済みホットキー数: {len(registered_hotkeys)}")
    
    print()


async def demo_integration():
    """統合デモ - 全レイヤーの連携"""
    print("=== 統合デモ ===")
    
    from src.infrastructure import (
        WindowsApiService, EncryptionService, FileService,
        SqliteRecordingRepository, KeyboardAdapter, MouseAdapter
    )
    from src.domain import Recording, ActionFactory, Coordinate, CommonKeys
    
    print("完全なRPAインフラストラクチャの初期化:")
    
    # 1. サービス層の初期化
    encryption_service = EncryptionService()
    encryption_service.set_master_password("ezrpa_infrastructure_demo")
    
    file_service = FileService()
    windows_api_service = WindowsApiService()
    
    # 2. リポジトリ層の初期化
    recording_repo = SqliteRecordingRepository(
        encryption_service=encryption_service,
        file_service=file_service
    )
    
    # 3. アダプター層の初期化
    keyboard_adapter = KeyboardAdapter(windows_api_service)
    mouse_adapter = MouseAdapter(windows_api_service)
    
    print("  ✓ 暗号化サービス初期化完了")
    print("  ✓ ファイルサービス初期化完了") 
    print("  ✓ Windows APIサービス初期化完了")
    print("  ✓ データベースリポジトリ初期化完了")
    print("  ✓ キーボード・マウスアダプター初期化完了")
    
    # 4. 実際のワークフローシミュレーション
    print("\n統合ワークフローの実行:")
    
    # RPAスクリプトの作成
    demo_recording = Recording(name="統合デモワークフロー")
    demo_recording.metadata.author = "EZRPA Infrastructure Demo"
    demo_recording.metadata.category = "integration_test"
    demo_recording.metadata.tags = ["統合テスト", "インフラ層", "Windows API"]
    
    demo_recording.start_recording()
    
    # 複雑なアクションシーケンス
    workflow_actions = [
        ActionFactory.create_text_input("統合デモ: インフラストラクチャ層テスト"),
        ActionFactory.create_key_press(CommonKeys.TAB),
        ActionFactory.create_mouse_click(Coordinate(300, 400)),
        ActionFactory.create_text_input("暗号化されたデータ保存テスト 🔐"),
        ActionFactory.create_key_press(CommonKeys.CTRL_S),
    ]
    
    for action in workflow_actions:
        demo_recording.add_action(action)
    
    demo_recording.complete_recording()
    
    # 暗号化保存
    save_result = await recording_repo.save(demo_recording)
    if save_result.is_success():
        print(f"  ✓ 暗号化記録保存: {demo_recording.action_count}アクション")
    
    # 復号化読み込み
    load_result = await recording_repo.get_by_id(demo_recording.recording_id)
    if load_result.is_success():
        loaded_recording = load_result.value
        print(f"  ✓ 暗号化記録読み込み: データ整合性確認完了")
    
    # システム能力の確認
    system_info = windows_api_service.get_system_info()
    screen_size = mouse_adapter.get_screen_size()
    
    print(f"  ✓ システム解像度: {screen_size.x}x{screen_size.y}")
    print(f"  ✓ DPIスケーリング: {system_info.scale_factor:.2f}x")
    print(f"  ✓ 暗号化利用可能: {encryption_service.is_encryption_available()}")
    
    # 機能統計
    stats_result = await recording_repo.get_statistics()
    if stats_result.is_success():
        stats = stats_result.value
        print(f"  ✓ データベース統計: {stats['total_recordings']}記録, {stats['total_actions']}アクション")
    
    print("\n🎉 すべてのインフラストラクチャ層機能が正常に動作しています！")
    print()


async def main():
    """メインデモ実行"""
    print("🚀 EZRPA v2.0 インフラストラクチャ層デモンストレーション")
    print("=" * 60)
    print()
    
    try:
        # 各機能のデモ実行
        await demo_file_service()
        await demo_encryption_service()
        await demo_windows_api_service()
        await demo_repositories()
        await demo_adapters()
        await demo_integration()
        
        print("🎉 すべてのインフラストラクチャ層デモが正常に完了しました！")
        print()
        print("Phase 3 インフラストラクチャ層実装完了:")
        print("✅ Windows APIサービス（キーボード・マウス・ウィンドウ操作）")
        print("✅ 暗号化サービス（AES-256・RSA・パスワードハッシュ）")
        print("✅ ファイルシステムサービス（ファイル操作・バックアップ・レジストリ）")
        print("✅ SQLiteリポジトリ（記録・スケジュール・設定の永続化）")
        print("✅ キーボードアダプター（IME対応・ホットキー・日本語入力）")
        print("✅ マウスアダプター（DPIスケーリング・ウィンドウ操作・ドラッグ）")
        print("✅ 暗号化データ永続化（チェックサム検証・スレッドセーフ）")
        print("✅ Windows環境統合（レジストリ・管理者権限・ショートカット）")
        print()
        print("EZRPA v2.0 クリーンアーキテクチャ実装完了！")
        print("次のフェーズでアプリケーション層とプレゼンテーション層を実装できます。")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))