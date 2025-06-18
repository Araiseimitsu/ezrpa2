"""
Playback Application Service Unit Tests - 再生アプリケーションサービスのテスト

再生アプリケーションサービスの各メソッドとビジネスロジックをテストします。
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone, timedelta
from typing import List

from src.application.services.playback_application_service import PlaybackApplicationService
from src.application.dto.playback_dto import (
    PlaybackConfigDTO,
    PlaybackDTO,
    PlaybackStatusDTO,
    PlaybackResultDTO,
    PlaybackQueueDTO,
    PlaybackQueueItemDTO,
    PlaybackValidationDTO,
    PlaybackHistoryDTO
)
from src.core.result import Result, Ok, Err, ErrorInfo
from src.domain.entities.recording import Recording
from tests.factories import RecordingFactory


class TestPlaybackApplicationService:
    """再生アプリケーションサービスのテストクラス"""
    
    @pytest.fixture
    def mock_recording_repository(self):
        """モック記録リポジトリ"""
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = Ok(RecordingFactory())
        return mock_repo
    
    @pytest.fixture
    def mock_settings_repository(self):
        """モック設定リポジトリ"""
        mock_repo = AsyncMock()
        mock_repo.get_setting.return_value = Ok("default_value")
        return mock_repo
    
    @pytest.fixture
    def mock_keyboard_adapter(self):
        """モックキーボードアダプター"""
        mock_adapter = Mock()
        mock_adapter.send_key.return_value = True
        return mock_adapter
    
    @pytest.fixture
    def mock_mouse_adapter(self):
        """モックマウスアダプター"""
        mock_adapter = Mock()
        mock_adapter.click.return_value = True
        return mock_adapter
    
    @pytest.fixture
    def playback_config(self):
        """標準的な再生設定"""
        return PlaybackConfigDTO(
            speed_multiplier=1.0,
            start_from_action=0,
            stop_on_error=True,
            repeat_count=1,
            delay_between_actions_ms=100
        )
    
    @pytest.fixture
    def service(self, mock_recording_repository, mock_settings_repository,
                mock_keyboard_adapter, mock_mouse_adapter):
        """テスト対象のアプリケーションサービス"""
        return PlaybackApplicationService(
            recording_repository=mock_recording_repository,
            settings_repository=mock_settings_repository,
            keyboard_adapter=mock_keyboard_adapter,
            mouse_adapter=mock_mouse_adapter
        )
    
    # ========================
    # start_playback テスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_start_playback_success(self, service, playback_config):
        """再生開始成功のテスト"""
        # Arrange
        recording_id = "test_recording_id"
        expected_session_id = "test_session_id"
        
        # モックの設定
        with patch.object(service._validate_recording_use_case, 'execute') as mock_validate:
            mock_validate.return_value = Ok({
                'is_playable': True,
                'warnings': [],
                'errors': [],
                'action_count': 5,
                'estimated_duration_seconds': 10.0
            })
            
            with patch.object(service._play_recording_use_case, 'execute') as mock_play:
                mock_play.return_value = Ok(expected_session_id)
                
                # Act
                result = await service.start_playback(recording_id, playback_config)
                
                # Assert
                assert result.is_success()
                assert result.value == expected_session_id
                assert expected_session_id in service._active_sessions
                mock_validate.assert_called_once_with(recording_id)
                mock_play.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_playback_validation_error(self, service):
        """再生開始時のバリデーションエラーのテスト"""
        # Arrange
        recording_id = "test_recording_id"
        invalid_config = PlaybackConfigDTO(speed_multiplier=-1.0)  # 無効な設定
        
        # Act
        result = await service.start_playback(recording_id, invalid_config)
        
        # Assert
        assert result.is_failure()
        assert "VALIDATION_ERROR" in result.error.code
    
    @pytest.mark.asyncio
    async def test_start_playback_max_concurrent_reached(self, service, playback_config):
        """同時再生数上限に達した場合のテスト"""
        # Arrange
        recording_id = "test_recording_id"
        service._max_concurrent_playbacks = 1
        
        # 既にアクティブなセッションを設定
        service._active_sessions["existing_session"] = Mock()
        
        # Act
        result = await service.start_playback(recording_id, playback_config)
        
        # Assert
        assert result.is_failure()
        assert "MAX_CONCURRENT_PLAYBACKS" in result.error.code
    
    @pytest.mark.asyncio
    async def test_start_playback_recording_not_playable(self, service, playback_config):
        """再生不可能な記録の再生開始テスト"""
        # Arrange
        recording_id = "test_recording_id"
        
        with patch.object(service._validate_recording_use_case, 'execute') as mock_validate:
            mock_validate.return_value = Ok({
                'is_playable': False,
                'warnings': [],
                'errors': ['Missing required actions'],
                'action_count': 0,
                'estimated_duration_seconds': 0.0
            })
            
            # Act
            result = await service.start_playback(recording_id, playback_config)
            
            # Assert
            assert result.is_failure()
            assert "RECORDING_NOT_PLAYABLE" in result.error.code
    
    # ========================
    # pause_playback テスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_pause_playback_success(self, service):
        """再生一時停止成功のテスト"""
        # Arrange
        session_id = "test_session_id"
        playback_dto = PlaybackDTO.create_new(
            session_id=session_id,
            recording_id="test_recording_id",
            recording_name="Test Recording",
            config=PlaybackConfigDTO()
        )
        service._active_sessions[session_id] = playback_dto
        
        with patch.object(service._pause_playback_use_case, 'execute') as mock_pause:
            mock_pause.return_value = Ok(True)
            
            # Act
            result = await service.pause_playback(session_id)
            
            # Assert
            assert result.is_success()
            assert result.value is True
            assert playback_dto.status.status == "paused"
            mock_pause.assert_called_once_with(session_id)
    
    @pytest.mark.asyncio
    async def test_pause_playback_invalid_session(self, service):
        """無効なセッションIDでの一時停止テスト"""
        # Arrange
        invalid_session_id = "invalid_session_id"
        
        # Act
        result = await service.pause_playback(invalid_session_id)
        
        # Assert
        assert result.is_failure()
        assert "INVALID_SESSION" in result.error.code
    
    # ========================
    # resume_playback テスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_resume_playback_success(self, service):
        """再生再開成功のテスト"""
        # Arrange
        session_id = "test_session_id"
        playback_dto = PlaybackDTO.create_new(
            session_id=session_id,
            recording_id="test_recording_id",
            recording_name="Test Recording",
            config=PlaybackConfigDTO()
        )
        service._active_sessions[session_id] = playback_dto
        
        with patch.object(service._resume_playback_use_case, 'execute') as mock_resume:
            mock_resume.return_value = Ok(True)
            
            # Act
            result = await service.resume_playback(session_id)
            
            # Assert
            assert result.is_success()
            assert result.value is True
            assert playback_dto.status.status == "playing"
            mock_resume.assert_called_once_with(session_id)
    
    # ========================
    # stop_playback テスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_stop_playback_success(self, service):
        """再生停止成功のテスト"""
        # Arrange
        session_id = "test_session_id"
        recording_id = "test_recording_id"
        playback_dto = PlaybackDTO.create_new(
            session_id=session_id,
            recording_id=recording_id,
            recording_name="Test Recording",
            config=PlaybackConfigDTO()
        )
        service._active_sessions[session_id] = playback_dto
        
        result_data = {
            'start_time': datetime.now(timezone.utc),
            'end_time': datetime.now(timezone.utc),
            'duration_seconds': 10.0,
            'total_actions': 5,
            'actions_executed': 5,
            'completion_rate': 1.0,
            'status': 'completed'
        }
        
        with patch.object(service._stop_playback_use_case, 'execute') as mock_stop:
            mock_stop.return_value = Ok(result_data)
            
            # Act
            result = await service.stop_playback(session_id)
            
            # Assert
            assert result.is_success()
            assert isinstance(result.value, PlaybackResultDTO)
            assert result.value.session_id == session_id
            assert result.value.recording_id == recording_id
            assert session_id not in service._active_sessions  # セッションが削除されている
            assert len(service._playback_history) == 1  # 履歴に追加されている
    
    @pytest.mark.asyncio
    async def test_stop_playback_updates_metrics(self, service):
        """再生停止時のメトリクス更新テスト"""
        # Arrange
        session_id = "test_session_id"
        playback_dto = PlaybackDTO.create_new(
            session_id=session_id,
            recording_id="test_recording_id",
            recording_name="Test Recording",
            config=PlaybackConfigDTO()
        )
        service._active_sessions[session_id] = playback_dto
        
        initial_successful = service._performance_metrics['successful_playbacks']
        
        result_data = {
            'start_time': datetime.now(timezone.utc),
            'end_time': datetime.now(timezone.utc),
            'duration_seconds': 10.0,
            'total_actions': 5,
            'actions_executed': 5,
            'completion_rate': 1.0,
            'status': 'completed'
        }
        
        with patch.object(service._stop_playback_use_case, 'execute') as mock_stop:
            mock_stop.return_value = Ok(result_data)
            
            # Act
            result = await service.stop_playback(session_id)
            
            # Assert
            assert result.is_success()
            assert service._performance_metrics['successful_playbacks'] == initial_successful + 1
    
    # ========================
    # get_playback_status テスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_get_playback_status_specific_session(self, service):
        """特定セッションのステータス取得テスト"""
        # Arrange
        session_id = "test_session_id"
        service._active_sessions[session_id] = Mock()
        
        status_info = {
            'session_id': session_id,
            'status': 'playing',
            'recording_id': 'test_recording_id',
            'recording_name': 'Test Recording',
            'current_action_index': 2,
            'total_actions': 5,
            'progress_percentage': 40.0,
            'start_time': datetime.now(timezone.utc),
            'elapsed_seconds': 5.0
        }
        
        with patch.object(service._get_playback_status_use_case, 'execute') as mock_status:
            mock_status.return_value = Ok(status_info)
            
            # Act
            result = await service.get_playback_status(session_id)
            
            # Assert
            assert result.is_success()
            assert isinstance(result.value, PlaybackStatusDTO)
            assert result.value.session_id == session_id
            assert result.value.progress_percentage == 40.0
    
    @pytest.mark.asyncio
    async def test_get_playback_status_no_active_sessions(self, service):
        """アクティブセッションが無い場合のテスト"""
        # Act
        result = await service.get_playback_status()
        
        # Assert
        assert result.is_failure()
        assert "NO_ACTIVE_SESSION" in result.error.code
    
    # ========================
    # validate_recording_for_playback テスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_validate_recording_for_playback_success(self, service):
        """記録の再生可能性検証成功のテスト"""
        # Arrange
        recording_id = "test_recording_id"
        validation_data = {
            'is_playable': True,
            'warnings': ['Minor timing issue'],
            'errors': [],
            'action_count': 10,
            'estimated_duration_seconds': 30.0
        }
        
        with patch.object(service._validate_recording_use_case, 'execute') as mock_validate:
            mock_validate.return_value = Ok(validation_data)
            
            # Act
            result = await service.validate_recording_for_playback(recording_id)
            
            # Assert
            assert result.is_success()
            assert isinstance(result.value, PlaybackValidationDTO)
            assert result.value.is_playable is True
            assert result.value.action_count == 10
            assert len(result.value.warnings) == 1
    
    # ========================
    # add_to_queue テスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_add_to_queue_success(self, service, playback_config):
        """キュー追加成功のテスト"""
        # Arrange
        recording_id = "test_recording_id"
        test_recording = RecordingFactory(recording_id=recording_id, name="Test Recording")
        service._recording_repository.get_by_id.return_value = Ok(test_recording)
        
        # Act
        result = await service.add_to_queue(recording_id, playback_config)
        
        # Assert
        assert result.is_success()
        queue_id = result.value
        assert len(service._playback_queue.queue_items) == 1
        assert service._playback_queue.queue_items[0].queue_id == queue_id
        assert service._playback_queue.total_items == 1
    
    @pytest.mark.asyncio
    async def test_add_to_queue_with_priority(self, service, playback_config):
        """優先度付きキュー追加のテスト"""
        # Arrange
        recording_id = "test_recording_id"
        test_recording = RecordingFactory(recording_id=recording_id)
        service._recording_repository.get_by_id.return_value = Ok(test_recording)
        
        # 複数のアイテムを追加（優先度の異なる）
        await service.add_to_queue(recording_id, playback_config, priority=1)
        await service.add_to_queue(recording_id, playback_config, priority=3)
        await service.add_to_queue(recording_id, playback_config, priority=2)
        
        # Act & Assert - 優先度順にソートされているか確認
        queue_items = service._playback_queue.queue_items
        priorities = [item.priority for item in queue_items]
        assert priorities == [3, 2, 1]  # 降順でソートされている
    
    # ========================
    # get_queue_status テスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_get_queue_status(self, service):
        """キュー状態取得のテスト"""
        # Act
        result = await service.get_queue_status()
        
        # Assert
        assert result.is_success()
        assert isinstance(result.value, PlaybackQueueDTO)
    
    # ========================
    # process_queue テスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_process_queue_success(self, service, playback_config):
        """キュー処理成功のテスト"""
        # Arrange
        recording_id = "test_recording_id"
        test_recording = RecordingFactory(recording_id=recording_id)
        service._recording_repository.get_by_id.return_value = Ok(test_recording)
        
        # キューにアイテムを追加
        await service.add_to_queue(recording_id, playback_config)
        
        # start_playbackをモック
        with patch.object(service, 'start_playback') as mock_start:
            mock_start.return_value = Ok("session_id_123")
            
            # Act
            result = await service.process_queue()
            
            # Assert
            assert result.is_success()
            assert len(result.value) == 1  # 1つのセッションが処理された
            assert service._playback_queue.queue_items[0].status == "running"
    
    @pytest.mark.asyncio
    async def test_process_queue_respects_concurrent_limit(self, service, playback_config):
        """キュー処理の同時実行数制限テスト"""
        # Arrange
        service._max_concurrent_playbacks = 1
        service._active_sessions["existing_session"] = Mock()  # 既に1つアクティブ
        
        recording_id = "test_recording_id"
        test_recording = RecordingFactory(recording_id=recording_id)
        service._recording_repository.get_by_id.return_value = Ok(test_recording)
        
        # キューにアイテムを追加
        await service.add_to_queue(recording_id, playbook_config)
        
        # Act
        result = await service.process_queue()
        
        # Assert
        assert result.is_success()
        assert len(result.value) == 0  # 同時実行数制限により処理されない
    
    # ========================
    # get_playback_history テスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_get_playback_history_success(self, service):
        """再生履歴取得成功のテスト"""
        # Arrange
        # 履歴データを追加
        result_dto = PlaybackResultDTO(
            session_id="session_1",
            recording_id="recording_1",
            recording_name="Test Recording",
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            duration_seconds=10.0,
            total_actions=5,
            actions_executed=5,
            actions_succeeded=5,
            actions_failed=0,
            completion_rate=1.0,
            success_rate=1.0,
            status="completed"
        )
        service._playback_history.append(result_dto)
        
        # Act
        result = await service.get_playback_history()
        
        # Assert
        assert result.is_success()
        assert isinstance(result.value, PlaybackHistoryDTO)
        assert len(result.value.results) == 1
    
    @pytest.mark.asyncio
    async def test_get_playback_history_with_filter(self, service):
        """記録IDフィルター付き履歴取得のテスト"""
        # Arrange
        # 複数の履歴を追加
        for i, recording_id in enumerate(["recording_1", "recording_2", "recording_1"]):
            result_dto = PlaybackResultDTO(
                session_id=f"session_{i}",
                recording_id=recording_id,
                recording_name=f"Test Recording {i}",
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc),
                duration_seconds=10.0,
                total_actions=5,
                actions_executed=5,
                actions_succeeded=5,
                actions_failed=0,
                completion_rate=1.0,
                success_rate=1.0,
                status="completed"
            )
            service._playback_history.append(result_dto)
        
        # Act
        result = await service.get_playbook_history(recording_id="recording_1")
        
        # Assert
        assert result.is_success()
        history_dto = result.value
        assert len(history_dto.results) == 2  # recording_1 の2件のみ
        assert all(r.recording_id == "recording_1" for r in history_dto.results)
    
    # ========================
    # パフォーマンスメトリクステスト
    # ========================
    
    def test_get_performance_metrics(self, service):
        """パフォーマンスメトリクス取得のテスト"""
        # Act
        metrics = service.get_performance_metrics()
        
        # Assert
        assert isinstance(metrics, dict)
        assert 'total_playbacks' in metrics
        assert 'successful_playbacks' in metrics
        assert 'failed_playbacks' in metrics
        assert 'average_duration' in metrics
        assert 'last_update' in metrics
    
    def test_update_performance_metrics(self, service):
        """パフォーマンスメトリクス更新のテスト"""
        # Arrange
        # 履歴データを追加
        result_dto = PlaybackResultDTO(
            session_id="session_1",
            recording_id="recording_1",
            recording_name="Test Recording",
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            duration_seconds=15.0,
            total_actions=5,
            actions_executed=5,
            actions_succeeded=5,
            actions_failed=0,
            completion_rate=1.0,
            success_rate=1.0,
            status="completed"
        )
        service._playback_history.append(result_dto)
        
        # Act
        service._update_performance_metrics()
        
        # Assert
        metrics = service._performance_metrics
        assert metrics['average_duration'] == 15.0
    
    # ========================
    # cleanup_finished_sessions テスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_cleanup_finished_sessions(self, service):
        """完了セッションクリーンアップのテスト"""
        # Arrange
        session_id = "finished_session"
        service._active_sessions[session_id] = Mock()
        
        status_dto = PlaybackStatusDTO(
            session_id=session_id,
            status="completed",
            recording_id="test_recording",
            recording_name="Test",
            current_action_index=5,
            total_actions=5,
            progress_percentage=100.0,
            start_time=datetime.now(timezone.utc),
            elapsed_seconds=10.0,
            is_finished=True
        )
        
        with patch.object(service, 'get_playback_status') as mock_status:
            mock_status.return_value = Ok(status_dto)
            
            # Act
            await service.cleanup_finished_sessions()
            
            # Assert
            assert session_id not in service._active_sessions
    
    # ========================
    # エラーハンドリングテスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_start_playback_exception_handling(self, service, playback_config):
        """再生開始時の例外処理のテスト"""
        # Arrange
        recording_id = "test_recording_id"
        
        with patch.object(service._validate_recording_use_case, 'execute') as mock_validate:
            mock_validate.side_effect = Exception("Validation failed")
            
            # Act
            result = await service.start_playback(recording_id, playback_config)
            
            # Assert
            assert result.is_failure()
            assert "START_PLAYBACK_ERROR" in result.error.code
    
    @pytest.mark.asyncio
    async def test_service_resilience_to_invalid_data(self, service):
        """無効なデータに対するサービスの回復力テスト"""
        # Act & Assert - 無効なセッションIDでの操作
        result = await service.pause_playback("invalid_session")
        assert result.is_failure()
        
        result = await service.resume_playback("invalid_session") 
        assert result.is_failure()
        
        result = await service.stop_playback("invalid_session")
        assert result.is_failure()