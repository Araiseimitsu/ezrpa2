"""
Recording Event Handler Unit Tests - 記録イベントハンドラーのテスト

記録イベントハンドラーのイベント処理とビジネスロジックをテストします。
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from src.application.handlers.recording_event_handler import RecordingEventHandler
from src.core.result import Result, Ok, Err, ErrorInfo
from src.domain.entities.recording import Recording
from tests.factories import RecordingFactory, KeyboardActionFactory


class TestRecordingEventHandler:
    """記録イベントハンドラーのテストクラス"""
    
    @pytest.fixture
    def mock_settings_repository(self):
        """モック設定リポジトリ"""
        mock_repo = AsyncMock()
        mock_repo.get_setting.return_value = Ok("default_value")
        mock_repo.save_setting.return_value = Ok(True)
        return mock_repo
    
    @pytest.fixture
    def mock_file_service(self):
        """モックファイルサービス"""
        mock_service = Mock()
        mock_service.save_backup.return_value = Ok(True)
        mock_service.cleanup_temp_files.return_value = Ok(True)
        mock_service.save_export.return_value = Ok("export_path")
        return mock_service
    
    @pytest.fixture
    def handler(self, mock_settings_repository, mock_file_service):
        """テスト対象のイベントハンドラー"""
        return RecordingEventHandler(
            settings_repository=mock_settings_repository,
            file_service=mock_file_service
        )
    
    # ========================
    # イベント登録テスト
    # ========================
    
    def test_subscribe_handler(self, handler):
        """ハンドラー登録のテスト"""
        # Arrange
        event_type = "test_event"
        test_handler = Mock()
        
        # Act
        handler.subscribe(event_type, test_handler)
        
        # Assert
        assert event_type in handler._event_listeners
        assert test_handler in handler._event_listeners[event_type]
    
    def test_subscribe_multiple_handlers(self, handler):
        """複数ハンドラー登録のテスト"""
        # Arrange
        event_type = "test_event"
        handler1 = Mock()
        handler2 = Mock()
        
        # Act
        handler.subscribe(event_type, handler1)
        handler.subscribe(event_type, handler2)
        
        # Assert
        assert len(handler._event_listeners[event_type]) == 2
        assert handler1 in handler._event_listeners[event_type]
        assert handler2 in handler._event_listeners[event_type]
    
    def test_unsubscribe_handler(self, handler):
        """ハンドラー解除のテスト"""
        # Arrange
        event_type = "test_event"
        test_handler = Mock()
        handler.subscribe(event_type, test_handler)
        
        # Act
        result = handler.unsubscribe(event_type, test_handler)
        
        # Assert
        assert result is True
        assert test_handler not in handler._event_listeners.get(event_type, [])
    
    def test_unsubscribe_nonexistent_handler(self, handler):
        """存在しないハンドラーの解除テスト"""
        # Arrange
        event_type = "test_event"
        nonexistent_handler = Mock()
        
        # Act
        result = handler.unsubscribe(event_type, nonexistent_handler)
        
        # Assert
        assert result is False
    
    # ========================
    # イベント処理テスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_handle_event_success(self, handler):
        """イベント処理成功のテスト"""
        # Arrange
        event_type = "test_event"
        event_data = {"test": "data"}
        test_handler = AsyncMock()
        test_handler.return_value = Ok(True)
        
        handler.subscribe(event_type, test_handler)
        
        # Act
        result = await handler.handle_event(event_type, event_data)
        
        # Assert
        assert result.is_success()
        test_handler.assert_called_once_with(event_data)
    
    @pytest.mark.asyncio
    async def test_handle_event_no_handlers(self, handler):
        """ハンドラーが存在しないイベントの処理テスト"""
        # Act
        result = await handler.handle_event("nonexistent_event", {})
        
        # Assert
        assert result.is_success()  # ハンドラーが無くても成功
    
    @pytest.mark.asyncio
    async def test_handle_event_handler_failure(self, handler):
        """ハンドラー処理失敗のテスト"""
        # Arrange
        event_type = "test_event"
        event_data = {"test": "data"}
        failing_handler = AsyncMock()
        failing_handler.return_value = Err(ErrorInfo("HANDLER_ERROR", "Handler failed"))
        
        handler.subscribe(event_type, failing_handler)
        
        # Act
        result = await handler.handle_event(event_type, event_data)
        
        # Assert
        assert result.is_failure()
        assert result.error.code == "HANDLER_ERROR"
    
    @pytest.mark.asyncio
    async def test_handle_event_multiple_handlers(self, handler):
        """複数ハンドラーの処理テスト"""
        # Arrange
        event_type = "test_event"
        event_data = {"test": "data"}
        handler1 = AsyncMock(return_value=Ok(True))
        handler2 = AsyncMock(return_value=Ok(True))
        
        handler.subscribe(event_type, handler1)
        handler.subscribe(event_type, handler2)
        
        # Act
        result = await handler.handle_event(event_type, event_data)
        
        # Assert
        assert result.is_success()
        handler1.assert_called_once_with(event_data)
        handler2.assert_called_once_with(event_data)
    
    # ========================
    # 記録開始イベントテスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_on_recording_started(self, handler, mock_settings_repository):
        """記録開始イベント処理のテスト"""
        # Arrange
        recording = RecordingFactory()
        event_data = {
            "recording": recording,
            "timestamp": datetime.now(timezone.utc)
        }
        
        # Act
        result = await handler._on_recording_started(event_data)
        
        # Assert
        assert result.is_success()
        # 記録開始の統計更新が呼ばれることを確認
        mock_settings_repository.save_setting.assert_called()
    
    @pytest.mark.asyncio
    async def test_on_recording_started_auto_backup_enabled(self, handler, mock_file_service):
        """自動バックアップ有効時の記録開始テスト"""
        # Arrange
        recording = RecordingFactory()
        recording.metadata.auto_save = True
        event_data = {
            "recording": recording,
            "timestamp": datetime.now(timezone.utc)
        }
        
        # Act
        result = await handler._on_recording_started(event_data)
        
        # Assert
        assert result.is_success()
        # 自動バックアップが実行されることを確認
        mock_file_service.save_backup.assert_called()
    
    # ========================
    # 記録停止イベントテスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_on_recording_stopped(self, handler, mock_settings_repository):
        """記録停止イベント処理のテスト"""
        # Arrange
        recording = RecordingFactory()
        event_data = {
            "recording": recording,
            "timestamp": datetime.now(timezone.utc),
            "reason": "user_requested"
        }
        
        # Act
        result = await handler._on_recording_stopped(event_data)
        
        # Assert
        assert result.is_success()
        # 記録停止の統計更新が呼ばれることを確認
        mock_settings_repository.save_setting.assert_called()
    
    @pytest.mark.asyncio
    async def test_on_recording_stopped_cleanup_temp_files(self, handler, mock_file_service):
        """記録停止時の一時ファイルクリーンアップテスト"""
        # Arrange
        recording = RecordingFactory()
        event_data = {
            "recording": recording,
            "timestamp": datetime.now(timezone.utc),
            "reason": "completed"
        }
        
        # Act
        result = await handler._on_recording_stopped(event_data)
        
        # Assert
        assert result.is_success()
        mock_file_service.cleanup_temp_files.assert_called()
    
    # ========================
    # 記録完了イベントテスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_on_recording_completed(self, handler, mock_file_service):
        """記録完了イベント処理のテスト"""
        # Arrange
        recording = RecordingFactory()
        event_data = {
            "recording": recording,
            "timestamp": datetime.now(timezone.utc),
            "actions_count": 10,
            "duration_seconds": 30.5
        }
        
        # Act
        result = await handler._on_recording_completed(event_data)
        
        # Assert
        assert result.is_success()
        # 完了時のエクスポート処理が呼ばれることを確認
        mock_file_service.save_export.assert_called()
    
    @pytest.mark.asyncio
    async def test_on_recording_completed_with_auto_export(self, handler, mock_file_service, mock_settings_repository):
        """自動エクスポート有効時の記録完了テスト"""
        # Arrange
        recording = RecordingFactory()
        recording.metadata.auto_export = True
        event_data = {
            "recording": recording,
            "timestamp": datetime.now(timezone.utc),
            "actions_count": 10,
            "duration_seconds": 30.5
        }
        
        # 自動エクスポート設定を有効に
        mock_settings_repository.get_setting.return_value = Ok(True)
        
        # Act
        result = await handler._on_recording_completed(event_data)
        
        # Assert
        assert result.is_success()
        mock_file_service.save_export.assert_called()
    
    # ========================
    # 記録失敗イベントテスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_on_recording_failed(self, handler, mock_settings_repository):
        """記録失敗イベント処理のテスト"""
        # Arrange
        recording = RecordingFactory()
        event_data = {
            "recording": recording,
            "timestamp": datetime.now(timezone.utc),
            "error": "Disk full",
            "error_code": "STORAGE_ERROR"
        }
        
        # Act
        result = await handler._on_recording_failed(event_data)
        
        # Assert
        assert result.is_success()
        # 失敗統計の更新が呼ばれることを確認
        mock_settings_repository.save_setting.assert_called()
    
    @pytest.mark.asyncio
    async def test_on_recording_failed_error_logging(self, handler):
        """記録失敗時のエラーログ記録テスト"""
        # Arrange
        recording = RecordingFactory()
        event_data = {
            "recording": recording,
            "timestamp": datetime.now(timezone.utc),
            "error": "Critical failure",
            "error_code": "CRITICAL_ERROR"
        }
        
        with patch('src.application.handlers.recording_event_handler.logger') as mock_logger:
            # Act
            result = await handler._on_recording_failed(event_data)
            
            # Assert
            assert result.is_success()
            mock_logger.error.assert_called()
    
    # ========================
    # アクション追加イベントテスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_on_action_added(self, handler, mock_settings_repository):
        """アクション追加イベント処理のテスト"""
        # Arrange
        recording = RecordingFactory()
        action = KeyboardActionFactory()
        event_data = {
            "recording": recording,
            "action": action,
            "timestamp": datetime.now(timezone.utc),
            "action_index": 5
        }
        
        # Act
        result = await handler._on_action_added(event_data)
        
        # Assert
        assert result.is_success()
        # アクション統計の更新が呼ばれることを確認
        mock_settings_repository.save_setting.assert_called()
    
    @pytest.mark.asyncio
    async def test_on_action_added_incremental_backup(self, handler, mock_file_service):
        """アクション追加時の増分バックアップテスト"""
        # Arrange
        recording = RecordingFactory()
        recording.metadata.incremental_backup = True
        action = KeyboardActionFactory()
        event_data = {
            "recording": recording,
            "action": action,
            "timestamp": datetime.now(timezone.utc),
            "action_index": 10  # 10件ごとにバックアップ
        }
        
        # Act
        result = await handler._on_action_added(event_data)
        
        # Assert
        assert result.is_success()
        # 増分バックアップが実行されることを確認
        if event_data["action_index"] % 10 == 0:
            mock_file_service.save_backup.assert_called()
    
    # ========================
    # 記録削除イベントテスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_on_recording_deleted(self, handler, mock_file_service):
        """記録削除イベント処理のテスト"""
        # Arrange
        recording_id = "test_recording_id"
        event_data = {
            "recording_id": recording_id,
            "timestamp": datetime.now(timezone.utc),
            "delete_files": True
        }
        
        # Act
        result = await handler._on_recording_deleted(event_data)
        
        # Assert
        assert result.is_success()
        # ファイル削除が呼ばれることを確認
        mock_file_service.cleanup_temp_files.assert_called()
    
    @pytest.mark.asyncio
    async def test_on_recording_deleted_preserve_files(self, handler, mock_file_service):
        """ファイル保持での記録削除テスト"""
        # Arrange
        recording_id = "test_recording_id"
        event_data = {
            "recording_id": recording_id,
            "timestamp": datetime.now(timezone.utc),
            "delete_files": False
        }
        
        # Act
        result = await handler._on_recording_deleted(event_data)
        
        # Assert
        assert result.is_success()
        # ファイル削除は呼ばれない
        mock_file_service.cleanup_temp_files.assert_not_called()
    
    # ========================
    # 記録更新イベントテスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_on_recording_updated(self, handler, mock_file_service):
        """記録更新イベント処理のテスト"""
        # Arrange
        recording = RecordingFactory()
        event_data = {
            "recording": recording,
            "timestamp": datetime.now(timezone.utc),
            "updated_fields": ["name", "description"],
            "previous_values": {"name": "Old Name", "description": "Old Description"}
        }
        
        # Act
        result = await handler._on_recording_updated(event_data)
        
        # Assert
        assert result.is_success()
        # 更新時のバックアップが実行されることを確認
        mock_file_service.save_backup.assert_called()
    
    # ========================
    # エラーハンドリングテスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_handle_event_exception_in_handler(self, handler):
        """ハンドラー内での例外発生テスト"""
        # Arrange
        event_type = "test_event"
        event_data = {"test": "data"}
        
        def failing_handler(data):
            raise Exception("Handler exception")
        
        handler.subscribe(event_type, failing_handler)
        
        # Act
        result = await handler.handle_event(event_type, event_data)
        
        # Assert
        assert result.is_failure()
        assert "HANDLER_EXCEPTION" in result.error.code
    
    @pytest.mark.asyncio
    async def test_handler_resilience_to_invalid_data(self, handler):
        """無効なデータに対するハンドラーの回復力テスト"""
        # Act & Assert - 空のイベントデータ
        result = await handler._on_recording_started({})
        assert result.is_failure()
        
        # Act & Assert - 必須フィールドが欠けているデータ
        result = await handler._on_recording_completed({"timestamp": datetime.now(timezone.utc)})
        assert result.is_failure()
        
        # Act & Assert - None データ
        result = await handler.handle_event("test_event", None)
        assert result.is_failure()
    
    @pytest.mark.asyncio
    async def test_handler_timeout_handling(self, handler):
        """ハンドラータイムアウト処理のテスト"""
        # Arrange
        event_type = "test_event"
        event_data = {"test": "data"}
        
        async def slow_handler(data):
            await asyncio.sleep(10)  # 長時間の処理をシミュレート
            return Ok(True)
        
        handler.subscribe(event_type, slow_handler)
        
        # Act - タイムアウト付きで実行
        with patch('asyncio.wait_for') as mock_wait_for:
            mock_wait_for.side_effect = asyncio.TimeoutError()
            
            result = await handler.handle_event(event_type, event_data)
            
            # Assert
            assert result.is_failure()
            assert "TIMEOUT" in result.error.code
    
    # ========================
    # パフォーマンステスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_handler_performance_with_many_events(self, handler):
        """大量イベント処理のパフォーマンステスト"""
        # Arrange
        event_type = "performance_test"
        fast_handler = AsyncMock(return_value=Ok(True))
        handler.subscribe(event_type, fast_handler)
        
        # Act - 100個のイベントを並行処理
        tasks = []
        for i in range(100):
            event_data = {"event_id": i}
            task = handler.handle_event(event_type, event_data)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # Assert
        assert len(results) == 100
        assert all(result.is_success() for result in results)
        assert fast_handler.call_count == 100
    
    # ========================
    # 統合テスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_end_to_end_recording_workflow(self, handler, mock_settings_repository, mock_file_service):
        """記録ワークフローのエンドツーエンドテスト"""
        # Arrange
        recording = RecordingFactory()
        
        # Act & Assert - 記録開始
        start_result = await handler.handle_event("recording_started", {
            "recording": recording,
            "timestamp": datetime.now(timezone.utc)
        })
        assert start_result.is_success()
        
        # Act & Assert - アクション追加
        action_result = await handler.handle_event("action_added", {
            "recording": recording,
            "action": KeyboardActionFactory(),
            "timestamp": datetime.now(timezone.utc),
            "action_index": 1
        })
        assert action_result.is_success()
        
        # Act & Assert - 記録停止
        stop_result = await handler.handle_event("recording_stopped", {
            "recording": recording,
            "timestamp": datetime.now(timezone.utc),
            "reason": "completed"
        })
        assert stop_result.is_success()
        
        # Act & Assert - 記録完了
        complete_result = await handler.handle_event("recording_completed", {
            "recording": recording,
            "timestamp": datetime.now(timezone.utc),
            "actions_count": 1,
            "duration_seconds": 10.0
        })
        assert complete_result.is_success()
        
        # 各段階でのサービス呼び出しを確認
        assert mock_settings_repository.save_setting.call_count >= 3
        assert mock_file_service.cleanup_temp_files.call_count >= 1
        assert mock_file_service.save_export.call_count >= 1