"""
Keyboard Adapter Unit Tests - キーボードアダプターのテスト

Windows APIを使用したキーボード操作アダプターの機能をテストします。
"""

import pytest
import threading
import time
from unittest.mock import Mock, patch, MagicMock

from src.infrastructure.adapters.keyboard_adapter import KeyboardAdapter
from src.core.result import Result, Ok, Err, ErrorInfo
from src.domain.entities.action import KeyboardAction
from src.domain.value_objects import ActionType
from tests.factories import KeyboardActionFactory


class TestKeyboardAdapter:
    """キーボードアダプターのテストクラス"""
    
    @pytest.fixture
    def mock_windows_api_service(self):
        """モックWindows APIサービス"""
        mock_service = Mock()
        mock_service.send_key.return_value = Ok(True)
        mock_service.send_text.return_value = Ok(True)
        mock_service.get_key_state.return_value = False
        mock_service.register_hotkey.return_value = Ok("hotkey_id")
        mock_service.unregister_hotkey.return_value = Ok(True)
        return mock_service
    
    @pytest.fixture
    def adapter(self, mock_windows_api_service):
        """テスト対象のキーボードアダプター"""
        return KeyboardAdapter(windows_api_service=mock_windows_api_service)
    
    # ========================
    # 初期化・設定テスト
    # ========================
    
    def test_adapter_initialization(self, adapter):
        """アダプター初期化のテスト"""
        # Assert
        assert adapter._windows_api_service is not None
        assert adapter._lock is not None
        assert adapter._char_to_vk is not None
        assert adapter._modifier_states is not None
        assert adapter._listening is False
        assert adapter._listener_thread is None
    
    def test_char_mapping_initialization(self, adapter):
        """文字マッピング初期化のテスト"""
        # Assert - 基本的な文字マッピングが存在する
        char_mapping = adapter._char_to_vk
        
        # 英数字のマッピング確認
        assert 'a' in char_mapping or 'A' in char_mapping
        assert '1' in char_mapping
        assert ' ' in char_mapping  # スペース
        
        # 特殊キーのマッピング確認
        assert len(char_mapping) > 0
    
    def test_modifier_states_initialization(self, adapter):
        """修飾キー状態初期化のテスト"""
        # Assert
        states = adapter._modifier_states
        assert 'shift' in states
        assert 'ctrl' in states
        assert 'alt' in states
        assert 'win' in states
        
        # 初期状態は全てFalse
        assert all(not state for state in states.values())
    
    # ========================
    # キーボードアクション実行テスト
    # ========================
    
    def test_execute_text_input_success(self, adapter, mock_windows_api_service):
        """テキスト入力実行成功のテスト"""
        # Arrange
        action = KeyboardAction(
            action_id="test_action",
            action_type=ActionType.TEXT_INPUT,
            text="テスト入力",
            timestamp=time.time()
        )
        
        # Act
        result = adapter.execute_action(action)
        
        # Assert
        assert result.is_success()
        mock_windows_api_service.send_text.assert_called_once_with("テスト入力")
    
    def test_execute_key_press_success(self, adapter, mock_windows_api_service):
        """キー押下実行成功のテスト"""
        # Arrange
        action = KeyboardAction(
            action_id="test_action",
            action_type=ActionType.KEY_PRESS,
            key_code="VK_A",
            key_name="A",
            modifiers=[],
            timestamp=time.time()
        )
        
        # Act
        result = adapter.execute_action(action)
        
        # Assert
        assert result.is_success()
        mock_windows_api_service.send_key.assert_called()
    
    def test_execute_key_combination_success(self, adapter, mock_windows_api_service):
        """キー組み合わせ実行成功のテスト"""
        # Arrange
        action = KeyboardAction(
            action_id="test_action",
            action_type=ActionType.KEY_COMBINATION,
            key_code="VK_C",
            key_name="C",
            modifiers=["ctrl"],
            timestamp=time.time()
        )
        
        # Act
        result = adapter.execute_action(action)
        
        # Assert
        assert result.is_success()
        # Ctrl+C の組み合わせが送信されることを確認
        assert mock_windows_api_service.send_key.call_count >= 2  # Ctrl押下 + C押下
    
    def test_execute_japanese_text_input(self, adapter, mock_windows_api_service):
        """日本語テキスト入力のテスト"""
        # Arrange
        japanese_text = "日本語入力テスト🎌"
        action = KeyboardAction(
            action_id="test_action",
            action_type=ActionType.TEXT_INPUT,
            text=japanese_text,
            timestamp=time.time()
        )
        
        # Act
        result = adapter.execute_action(action)
        
        # Assert
        assert result.is_success()
        mock_windows_api_service.send_text.assert_called_once_with(japanese_text)
    
    def test_execute_special_keys(self, adapter, mock_windows_api_service):
        """特殊キー実行のテスト"""
        # Arrange
        special_keys = [
            ("VK_RETURN", "Enter"),
            ("VK_TAB", "Tab"),
            ("VK_ESCAPE", "Escape"),
            ("VK_SPACE", "Space")
        ]
        
        for key_code, key_name in special_keys:
            action = KeyboardAction(
                action_id=f"test_{key_name.lower()}",
                action_type=ActionType.KEY_PRESS,
                key_code=key_code,
                key_name=key_name,
                modifiers=[],
                timestamp=time.time()
            )
            
            # Act
            result = adapter.execute_action(action)
            
            # Assert
            assert result.is_success(), f"Failed for key: {key_name}"
    
    def test_execute_unsupported_action_type(self, adapter):
        """サポートされていないアクションタイプのテスト"""
        # Arrange
        action = KeyboardAction(
            action_id="test_action",
            action_type="UNSUPPORTED_TYPE",  # 無効なタイプ
            timestamp=time.time()
        )
        
        # Act
        result = adapter.execute_action(action)
        
        # Assert
        assert result.is_failure()
        assert "UNSUPPORTED_ACTION" in result.error
    
    # ========================
    # 修飾キー処理テスト
    # ========================
    
    def test_modifier_key_press_and_release(self, adapter, mock_windows_api_service):
        """修飾キーの押下・離脱処理テスト"""
        # Act - Shift キーを押下
        result = adapter.press_modifier_key("shift")
        
        # Assert
        assert result.is_success()
        assert adapter._modifier_states["shift"] is True
        mock_windows_api_service.send_key.assert_called()
        
        # Act - Shift キーを離脱
        result = adapter.release_modifier_key("shift")
        
        # Assert
        assert result.is_success()
        assert adapter._modifier_states["shift"] is False
    
    def test_multiple_modifier_keys(self, adapter, mock_windows_api_service):
        """複数修飾キーの処理テスト"""
        # Arrange
        modifiers = ["ctrl", "shift", "alt"]
        
        # Act - 複数修飾キーを押下
        for modifier in modifiers:
            result = adapter.press_modifier_key(modifier)
            assert result.is_success()
            assert adapter._modifier_states[modifier] is True
        
        # Act - 複数修飾キーを離脱
        for modifier in modifiers:
            result = adapter.release_modifier_key(modifier)
            assert result.is_success()
            assert adapter._modifier_states[modifier] is False
    
    def test_invalid_modifier_key(self, adapter):
        """無効な修飾キーのテスト"""
        # Act
        result = adapter.press_modifier_key("invalid_modifier")
        
        # Assert
        assert result.is_failure()
        assert "INVALID_MODIFIER" in result.error
    
    # ========================
    # ホットキー処理テスト
    # ========================
    
    def test_register_hotkey_success(self, adapter, mock_windows_api_service):
        """ホットキー登録成功のテスト"""
        # Arrange
        hotkey_id = "test_hotkey"
        key_combination = ["ctrl", "shift", "s"]
        callback = Mock()
        
        # Act
        result = adapter.register_hotkey(hotkey_id, key_combination, callback)
        
        # Assert
        assert result.is_success()
        assert hotkey_id in adapter._hotkey_listeners
        mock_windows_api_service.register_hotkey.assert_called_once()
    
    def test_register_duplicate_hotkey(self, adapter, mock_windows_api_service):
        """重複ホットキー登録のテスト"""
        # Arrange
        hotkey_id = "duplicate_hotkey"
        key_combination = ["ctrl", "d"]
        callback1 = Mock()
        callback2 = Mock()
        
        # Act - 最初の登録
        result1 = adapter.register_hotkey(hotkey_id, key_combination, callback1)
        assert result1.is_success()
        
        # Act - 同じIDで再登録
        result2 = adapter.register_hotkey(hotkey_id, key_combination, callback2)
        
        # Assert
        assert result2.is_failure()
        assert "HOTKEY_ALREADY_REGISTERED" in result2.error
    
    def test_unregister_hotkey_success(self, adapter, mock_windows_api_service):
        """ホットキー解除成功のテスト"""
        # Arrange
        hotkey_id = "test_hotkey"
        key_combination = ["ctrl", "u"]
        callback = Mock()
        
        adapter.register_hotkey(hotkey_id, key_combination, callback)
        
        # Act
        result = adapter.unregister_hotkey(hotkey_id)
        
        # Assert
        assert result.is_success()
        assert hotkey_id not in adapter._hotkey_listeners
        mock_windows_api_service.unregister_hotkey.assert_called()
    
    def test_unregister_nonexistent_hotkey(self, adapter):
        """存在しないホットキー解除のテスト"""
        # Act
        result = adapter.unregister_hotkey("nonexistent_hotkey")
        
        # Assert
        assert result.is_failure()
        assert "HOTKEY_NOT_FOUND" in result.error
    
    # ========================
    # ホットキーリスナーテスト
    # ========================
    
    def test_start_hotkey_listener(self, adapter):
        """ホットキーリスナー開始のテスト"""
        # Act
        result = adapter.start_hotkey_listener()
        
        # Assert
        assert result.is_success()
        assert adapter._listening is True
        assert adapter._listener_thread is not None
        assert adapter._listener_thread.is_alive()
        
        # クリーンアップ
        adapter.stop_hotkey_listener()
    
    def test_stop_hotkey_listener(self, adapter):
        """ホットキーリスナー停止のテスト"""
        # Arrange
        adapter.start_hotkey_listener()
        assert adapter._listening is True
        
        # Act
        result = adapter.stop_hotkey_listener()
        
        # Assert
        assert result.is_success()
        assert adapter._listening is False
        
        # スレッドが適切に終了するまで待機
        if adapter._listener_thread:
            adapter._listener_thread.join(timeout=1.0)
            assert not adapter._listener_thread.is_alive()
    
    def test_hotkey_callback_execution(self, adapter, mock_windows_api_service):
        """ホットキーコールバック実行のテスト"""
        # Arrange
        callback = Mock()
        hotkey_id = "test_callback"
        key_combination = ["ctrl", "t"]
        
        adapter.register_hotkey(hotkey_id, key_combination, callback)
        
        # ホットキー検出のシミュレーション
        # 実際の実装では、Windows APIからのイベントを処理
        
        # Act - ホットキーイベントのシミュレーション
        adapter._on_hotkey_pressed(hotkey_id)
        
        # Assert
        callback.assert_called_once()
    
    # ========================
    # IME・日本語入力テスト
    # ========================
    
    def test_ime_conversion_keys(self, adapter, mock_windows_api_service):
        """IME変換キーのテスト"""
        # Arrange
        ime_keys = [
            ("VK_CONVERT", "変換"),
            ("VK_NONCONVERT", "無変換"),
            ("VK_KANA", "ひらがな/カタカナ"),
            ("VK_KANJI", "漢字")
        ]
        
        for key_code, key_name in ime_keys:
            action = KeyboardAction(
                action_id=f"test_ime_{key_code}",
                action_type=ActionType.KEY_PRESS,
                key_code=key_code,
                key_name=key_name,
                modifiers=[],
                timestamp=time.time()
            )
            
            # Act
            result = adapter.execute_action(action)
            
            # Assert
            assert result.is_success(), f"Failed for IME key: {key_name}"
    
    def test_japanese_text_with_ime(self, adapter, mock_windows_api_service):
        """IME使用時の日本語テキスト入力テスト"""
        # Arrange
        japanese_phrases = [
            "こんにちは",
            "ありがとうございます",
            "お疲れ様でした",
            "よろしくお願いします"
        ]
        
        for phrase in japanese_phrases:
            action = KeyboardAction(
                action_id=f"test_japanese_{hash(phrase)}",
                action_type=ActionType.TEXT_INPUT,
                text=phrase,
                timestamp=time.time()
            )
            
            # Act
            result = adapter.execute_action(action)
            
            # Assert
            assert result.is_success(), f"Failed for Japanese phrase: {phrase}"
            mock_windows_api_service.send_text.assert_called_with(phrase)
    
    # ========================
    # エラーハンドリングテスト
    # ========================
    
    def test_windows_api_service_failure(self, adapter, mock_windows_api_service):
        """Windows APIサービス失敗時のテスト"""
        # Arrange
        mock_windows_api_service.send_key.return_value = Err("API_ERROR")
        
        action = KeyboardAction(
            action_id="test_action",
            action_type=ActionType.KEY_PRESS,
            key_code="VK_A",
            key_name="A",
            modifiers=[],
            timestamp=time.time()
        )
        
        # Act
        result = adapter.execute_action(action)
        
        # Assert
        assert result.is_failure()
        assert "API_ERROR" in result.error
    
    def test_invalid_key_code(self, adapter, mock_windows_api_service):
        """無効なキーコードのテスト"""
        # Arrange
        action = KeyboardAction(
            action_id="test_action",
            action_type=ActionType.KEY_PRESS,
            key_code="INVALID_VK_CODE",
            key_name="Invalid",
            modifiers=[],
            timestamp=time.time()
        )
        
        mock_windows_api_service.send_key.return_value = Err("INVALID_KEY_CODE")
        
        # Act
        result = adapter.execute_action(action)
        
        # Assert
        assert result.is_failure()
        assert "INVALID_KEY_CODE" in result.error
    
    def test_action_execution_exception(self, adapter, mock_windows_api_service):
        """アクション実行時の例外処理テスト"""
        # Arrange
        mock_windows_api_service.send_key.side_effect = Exception("Unexpected error")
        
        action = KeyboardAction(
            action_id="test_action",
            action_type=ActionType.KEY_PRESS,
            key_code="VK_A",
            key_name="A",
            modifiers=[],
            timestamp=time.time()
        )
        
        # Act
        result = adapter.execute_action(action)
        
        # Assert
        assert result.is_failure()
        assert "EXECUTION_ERROR" in result.error
    
    # ========================
    # スレッドセーフティテスト
    # ========================
    
    def test_concurrent_action_execution(self, adapter, mock_windows_api_service):
        """並行アクション実行のテスト"""
        import threading
        
        results = []
        errors = []
        
        def execute_action(action_id):
            try:
                action = KeyboardAction(
                    action_id=f"concurrent_action_{action_id}",
                    action_type=ActionType.KEY_PRESS,
                    key_code="VK_A",
                    key_name="A",
                    modifiers=[],
                    timestamp=time.time()
                )
                result = adapter.execute_action(action)
                if result.is_success():
                    results.append(action_id)
                else:
                    errors.append(f"Failed for {action_id}: {result.error}")
            except Exception as e:
                errors.append(f"Exception for {action_id}: {e}")
        
        # Act - 複数スレッドで並行実行
        threads = []
        for i in range(5):
            thread = threading.Thread(target=execute_action, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Assert
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 5, f"Expected 5 results, got {len(results)}"
    
    def test_concurrent_hotkey_registration(self, adapter, mock_windows_api_service):
        """並行ホットキー登録のテスト"""
        import threading
        
        successful_registrations = []
        failed_registrations = []
        
        def register_hotkey(hotkey_id):
            try:
                callback = Mock()
                key_combination = ["ctrl", str(hotkey_id)]
                result = adapter.register_hotkey(f"hotkey_{hotkey_id}", key_combination, callback)
                if result.is_success():
                    successful_registrations.append(hotkey_id)
                else:
                    failed_registrations.append(hotkey_id)
            except Exception as e:
                failed_registrations.append(f"Exception for {hotkey_id}: {e}")
        
        # Act
        threads = []
        for i in range(3):
            thread = threading.Thread(target=register_hotkey, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Assert
        assert len(successful_registrations) == 3
        assert len(failed_registrations) == 0
    
    # ========================
    # パフォーマンステスト
    # ========================
    
    def test_rapid_key_execution_performance(self, adapter, mock_windows_api_service):
        """高速キー実行パフォーマンステスト"""
        # Arrange
        actions = []
        for i in range(100):
            action = KeyboardAction(
                action_id=f"rapid_action_{i}",
                action_type=ActionType.KEY_PRESS,
                key_code="VK_A",
                key_name="A",
                modifiers=[],
                timestamp=time.time()
            )
            actions.append(action)
        
        # Act
        start_time = time.time()
        for action in actions:
            result = adapter.execute_action(action)
            assert result.is_success()
        end_time = time.time()
        
        # Assert - パフォーマンス要件: 100キーの実行が1秒以内
        assert (end_time - start_time) < 1.0
    
    # ========================
    # 統合テスト
    # ========================
    
    def test_complete_typing_workflow(self, adapter, mock_windows_api_service):
        """完全なタイピングワークフローのテスト"""
        # Arrange - 複雑なタイピングシナリオ
        workflow_actions = [
            # テキスト入力
            KeyboardAction(
                action_id="step1",
                action_type=ActionType.TEXT_INPUT,
                text="Hello, ",
                timestamp=time.time()
            ),
            # キー組み合わせ（Ctrl+A - 全選択）
            KeyboardAction(
                action_id="step2",
                action_type=ActionType.KEY_COMBINATION,
                key_code="VK_A",
                key_name="A",
                modifiers=["ctrl"],
                timestamp=time.time()
            ),
            # 日本語テキスト入力
            KeyboardAction(
                action_id="step3",
                action_type=ActionType.TEXT_INPUT,
                text="こんにちは、世界！",
                timestamp=time.time()
            ),
            # Enter キー
            KeyboardAction(
                action_id="step4",
                action_type=ActionType.KEY_PRESS,
                key_code="VK_RETURN",
                key_name="Enter",
                modifiers=[],
                timestamp=time.time()
            )
        ]
        
        # Act - ワークフロー実行
        for action in workflow_actions:
            result = adapter.execute_action(action)
            assert result.is_success(), f"Failed at action: {action.action_id}"
        
        # Assert - 全てのAPIコールが実行された
        assert mock_windows_api_service.send_text.call_count == 2  # テキスト入力2回
        assert mock_windows_api_service.send_key.call_count >= 4   # キー操作複数回