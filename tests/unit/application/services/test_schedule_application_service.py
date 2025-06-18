"""
Schedule Application Service Unit Tests - スケジュールアプリケーションサービスのテスト

スケジュールアプリケーションサービスの各メソッドとビジネスロジックをテストします。
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone, timedelta
from typing import List

from src.application.services.schedule_application_service import ScheduleApplicationService
from src.application.dto.schedule_dto import (
    CreateScheduleDTO,
    UpdateScheduleDTO,
    ScheduleDTO,
    ScheduleListDTO,
    ScheduleStatsDTO,
    ExecutionResultDTO,
    ScheduleExecutionHistoryDTO
)
from src.core.result import Result, Ok, Err, ErrorInfo
from src.domain.entities.schedule import Schedule
from src.domain.value_objects import ScheduleStatus, TriggerType
from tests.factories import (
    ScheduleFactory,
    CreateScheduleDTOFactory,
    UpdateScheduleDTOFactory,
    RecordingFactory
)


class TestScheduleApplicationService:
    """スケジュールアプリケーションサービスのテストクラス"""
    
    @pytest.fixture
    def mock_schedule_repository(self):
        """モックスケジュールリポジトリ"""
        mock_repo = AsyncMock()
        mock_repo.save.return_value = Ok("schedule_id")
        mock_repo.get_by_id.return_value = Ok(ScheduleFactory())
        mock_repo.get_all.return_value = Ok([])
        mock_repo.delete.return_value = Ok(True)
        return mock_repo
    
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
    def mock_playback_service(self):
        """モック再生サービス"""
        mock_service = AsyncMock()
        mock_service.start_playback.return_value = Ok("playback_session_id")
        mock_service.stop_playback.return_value = Ok(Mock())
        mock_service.get_playback_status.return_value = Ok(Mock(is_finished=True, status="completed"))
        return mock_service
    
    @pytest.fixture
    def service(self, mock_schedule_repository, mock_recording_repository,
                mock_settings_repository, mock_playback_service):
        """テスト対象のアプリケーションサービス"""
        return ScheduleApplicationService(
            schedule_repository=mock_schedule_repository,
            recording_repository=mock_recording_repository,
            settings_repository=mock_settings_repository,
            playback_service=mock_playback_service
        )
    
    # ========================
    # create_schedule テスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_create_schedule_success(self, service):
        """スケジュール作成成功のテスト"""
        # Arrange
        create_dto = CreateScheduleDTOFactory()
        expected_id = "test_schedule_id"
        
        with patch.object(service._create_schedule_use_case, 'execute') as mock_execute:
            mock_execute.return_value = Ok(expected_id)
            
            # Act
            result = await service.create_schedule(create_dto)
            
            # Assert
            assert result.is_success()
            assert result.value == expected_id
            mock_execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_schedule_with_activation(self, service):
        """アクティブ化付きスケジュール作成のテスト"""
        # Arrange
        create_dto = CreateScheduleDTOFactory(is_active=True)
        expected_id = "test_schedule_id"
        
        with patch.object(service._create_schedule_use_case, 'execute') as mock_create:
            mock_create.return_value = Ok(expected_id)
            
            with patch.object(service._activate_schedule_use_case, 'execute') as mock_activate:
                mock_activate.return_value = Ok(ScheduleFactory())
                
                # Act
                result = await service.create_schedule(create_dto)
                
                # Assert
                assert result.is_success()
                mock_activate.assert_called_once_with(expected_id)
    
    @pytest.mark.asyncio
    async def test_create_schedule_validation_error(self, service):
        """スケジュール作成時のバリデーションエラーのテスト"""
        # Arrange
        invalid_dto = CreateScheduleDTOFactory(name="")  # 無効な名前
        
        # Act
        result = await service.create_schedule(invalid_dto)
        
        # Assert
        assert result.is_failure()
        assert "VALIDATION_ERROR" in result.error.code
    
    @pytest.mark.asyncio
    async def test_create_schedule_use_case_failure(self, service):
        """スケジュール作成時のユースケース失敗のテスト"""
        # Arrange
        create_dto = CreateScheduleDTOFactory()
        
        with patch.object(service._create_schedule_use_case, 'execute') as mock_execute:
            mock_execute.return_value = Err(ErrorInfo("CREATE_ERROR", "Failed to create"))
            
            # Act
            result = await service.create_schedule(create_dto)
            
            # Assert
            assert result.is_failure()
            assert result.error.code == "CREATE_ERROR"
    
    # ========================
    # update_schedule テスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_update_schedule_success(self, service):
        """スケジュール更新成功のテスト"""
        # Arrange
        schedule_id = "test_schedule_id"
        update_dto = UpdateScheduleDTOFactory(name="Updated Schedule")
        updated_schedule = ScheduleFactory(schedule_id=schedule_id)
        
        with patch.object(service._update_schedule_use_case, 'execute') as mock_update:
            mock_update.return_value = Ok(updated_schedule)
            
            # Act
            result = await service.update_schedule(schedule_id, update_dto)
            
            # Assert
            assert result.is_success()
            assert isinstance(result.value, ScheduleDTO)
            mock_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_schedule_with_activation_change(self, service):
        """アクティブ状態変更付き更新のテスト"""
        # Arrange
        schedule_id = "test_schedule_id"
        update_dto = UpdateScheduleDTOFactory(is_active=True)
        updated_schedule = ScheduleFactory(schedule_id=schedule_id)
        
        with patch.object(service._update_schedule_use_case, 'execute') as mock_update:
            mock_update.return_value = Ok(updated_schedule)
            
            with patch.object(service._activate_schedule_use_case, 'execute') as mock_activate:
                mock_activate.return_value = Ok(updated_schedule)
                
                with patch.object(service._get_schedule_use_case, 'execute') as mock_get:
                    mock_get.return_value = Ok(updated_schedule)
                    
                    # Act
                    result = await service.update_schedule(schedule_id, update_dto)
                    
                    # Assert
                    assert result.is_success()
                    mock_activate.assert_called_once_with(schedule_id)
    
    @pytest.mark.asyncio
    async def test_update_schedule_validation_error(self, service):
        """スケジュール更新時のバリデーションエラーのテスト"""
        # Arrange
        schedule_id = "test_schedule_id"
        invalid_dto = UpdateScheduleDTOFactory(name="")  # 無効な名前
        
        # Act
        result = await service.update_schedule(schedule_id, invalid_dto)
        
        # Assert
        assert result.is_failure()
        assert "VALIDATION_ERROR" in result.error.code
    
    # ========================
    # delete_schedule テスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_delete_schedule_success(self, service):
        """スケジュール削除成功のテスト"""
        # Arrange
        schedule_id = "test_schedule_id"
        
        with patch.object(service._delete_schedule_use_case, 'execute') as mock_delete:
            mock_delete.return_value = Ok(True)
            
            # Act
            result = await service.delete_schedule(schedule_id)
            
            # Assert
            assert result.is_success()
            assert result.value is True
            mock_delete.assert_called_once_with(schedule_id, False)
    
    @pytest.mark.asyncio
    async def test_delete_schedule_with_force(self, service):
        """強制削除のテスト"""
        # Arrange
        schedule_id = "test_schedule_id"
        
        with patch.object(service._delete_schedule_use_case, 'execute') as mock_delete:
            mock_delete.return_value = Ok(True)
            
            # Act
            result = await service.delete_schedule(schedule_id, force=True)
            
            # Assert
            assert result.is_success()
            mock_delete.assert_called_once_with(schedule_id, True)
    
    @pytest.mark.asyncio
    async def test_delete_schedule_with_active_execution(self, service, mock_playback_service):
        """実行中のスケジュール削除のテスト"""
        # Arrange
        schedule_id = "test_schedule_id"
        service._active_executions[schedule_id] = {
            'execution_id': 'exec_123',
            'session_id': 'session_123'
        }
        
        with patch.object(service._delete_schedule_use_case, 'execute') as mock_delete:
            mock_delete.return_value = Ok(True)
            
            # Act
            result = await service.delete_schedule(schedule_id)
            
            # Assert
            assert result.is_success()
            assert schedule_id not in service._active_executions
            mock_playback_service.stop_playback.assert_called_once_with('session_123')
    
    # ========================
    # get_schedule テスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_get_schedule_success(self, service):
        """スケジュール取得成功のテスト"""
        # Arrange
        schedule_id = "test_schedule_id"
        test_schedule = ScheduleFactory(schedule_id=schedule_id)
        
        with patch.object(service._get_schedule_use_case, 'execute') as mock_get:
            mock_get.return_value = Ok(test_schedule)
            
            # Act
            result = await service.get_schedule(schedule_id)
            
            # Assert
            assert result.is_success()
            assert isinstance(result.value, ScheduleDTO)
            assert result.value.schedule_id == schedule_id
    
    @pytest.mark.asyncio
    async def test_get_schedule_not_found(self, service):
        """存在しないスケジュール取得のテスト"""
        # Arrange
        schedule_id = "nonexistent_id"
        
        with patch.object(service._get_schedule_use_case, 'execute') as mock_get:
            mock_get.return_value = Err(ErrorInfo("NOT_FOUND", "Schedule not found"))
            
            # Act
            result = await service.get_schedule(schedule_id)
            
            # Assert
            assert result.is_failure()
            assert result.error.code == "NOT_FOUND"
    
    # ========================
    # get_all_schedules テスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_get_all_schedules_success(self, service):
        """全スケジュール取得成功のテスト"""
        # Arrange
        test_schedules = [
            ScheduleFactory(status=ScheduleStatus.ACTIVE),
            ScheduleFactory(status=ScheduleStatus.INACTIVE),
            ScheduleFactory(status=ScheduleStatus.RUNNING)
        ]
        
        with patch.object(service._get_all_schedules_use_case, 'execute') as mock_get:
            mock_get.return_value = Ok(test_schedules)
            
            # Act
            result = await service.get_all_schedules()
            
            # Assert
            assert result.is_success()
            list_dto = result.value
            assert isinstance(list_dto, ScheduleListDTO)
            assert list_dto.total_count == 3
            assert list_dto.active_count == 1
            assert list_dto.inactive_count == 1
            assert list_dto.running_count == 1
    
    @pytest.mark.asyncio
    async def test_get_all_schedules_active_only(self, service):
        """アクティブなスケジュールのみ取得のテスト"""
        # Arrange
        active_schedules = [ScheduleFactory(status=ScheduleStatus.ACTIVE)]
        
        with patch.object(service._get_all_schedules_use_case, 'execute') as mock_get:
            mock_get.return_value = Ok(active_schedules)
            
            # Act
            result = await service.get_all_schedules(active_only=True)
            
            # Assert
            assert result.is_success()
            list_dto = result.value
            assert list_dto.filters["active_only"] is True
            mock_get.assert_called_once_with(True)
    
    @pytest.mark.asyncio
    async def test_get_all_schedules_pagination(self, service):
        """ページング処理のテスト"""
        # Arrange
        test_schedules = [ScheduleFactory() for _ in range(15)]
        
        with patch.object(service._get_all_schedules_use_case, 'execute') as mock_get:
            mock_get.return_value = Ok(test_schedules)
            
            # Act
            result = await service.get_all_schedules(page=2, page_size=10)
            
            # Assert
            assert result.is_success()
            list_dto = result.value
            assert list_dto.total_count == 15
            assert len(list_dto.schedules) == 5  # 2ページ目の残り5件
            assert list_dto.has_next is False
            assert list_dto.has_previous is True
    
    # ========================
    # activate/deactivate_schedule テスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_activate_schedule_success(self, service):
        """スケジュールアクティブ化成功のテスト"""
        # Arrange
        schedule_id = "test_schedule_id"
        activated_schedule = ScheduleFactory(schedule_id=schedule_id, status=ScheduleStatus.ACTIVE)
        
        with patch.object(service._activate_schedule_use_case, 'execute') as mock_activate:
            mock_activate.return_value = Ok(activated_schedule)
            
            # Act
            result = await service.activate_schedule(schedule_id)
            
            # Assert
            assert result.is_success()
            assert isinstance(result.value, ScheduleDTO)
            mock_activate.assert_called_once_with(schedule_id)
    
    @pytest.mark.asyncio
    async def test_deactivate_schedule_success(self, service):
        """スケジュール非アクティブ化成功のテスト"""
        # Arrange
        schedule_id = "test_schedule_id"
        deactivated_schedule = ScheduleFactory(schedule_id=schedule_id, status=ScheduleStatus.INACTIVE)
        
        with patch.object(service._deactivate_schedule_use_case, 'execute') as mock_deactivate:
            mock_deactivate.return_value = Ok(deactivated_schedule)
            
            # Act
            result = await service.deactivate_schedule(schedule_id)
            
            # Assert
            assert result.is_success()
            assert isinstance(result.value, ScheduleDTO)
            mock_deactivate.assert_called_once_with(schedule_id)
    
    # ========================
    # get_execution_history テスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_get_execution_history_success(self, service):
        """実行履歴取得成功のテスト"""
        # Arrange
        schedule_id = "test_schedule_id"
        history_data = [
            {
                'execution_id': 'exec_1',
                'recording_id': 'rec_1',
                'started_at': datetime.now(timezone.utc),
                'completed_at': datetime.now(timezone.utc),
                'status': 'completed',
                'success': True,
                'duration_seconds': 10.0
            },
            {
                'execution_id': 'exec_2',
                'recording_id': 'rec_1',
                'started_at': datetime.now(timezone.utc),
                'completed_at': None,
                'status': 'failed',
                'success': False,
                'error_message': 'Test error',
                'duration_seconds': 5.0
            }
        ]
        
        with patch.object(service._get_execution_history_use_case, 'execute') as mock_history:
            mock_history.return_value = Ok(history_data)
            
            with patch.object(service._get_next_execution_time_use_case, 'execute') as mock_next:
                next_time = datetime.now(timezone.utc) + timedelta(hours=1)
                mock_next.return_value = Ok(next_time)
                
                # Act
                result = await service.get_execution_history(schedule_id)
                
                # Assert
                assert result.is_success()
                history_dto = result.value
                assert isinstance(history_dto, ScheduleExecutionHistoryDTO)
                assert history_dto.schedule_id == schedule_id
                assert history_dto.total_executions == 2
                assert history_dto.successful_executions == 1
                assert history_dto.failed_executions == 1
                assert history_dto.next_execution == next_time
    
    # ========================
    # スケジューラーテスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_start_scheduler_success(self, service):
        """スケジューラー開始成功のテスト"""
        # Act
        result = await service.start_scheduler()
        
        # Assert
        assert result.is_success()
        assert service._scheduler_running is True
        assert service._scheduler_task is not None
        
        # クリーンアップ
        await service.stop_scheduler()
    
    @pytest.mark.asyncio
    async def test_start_scheduler_already_running(self, service):
        """既に実行中のスケジューラー開始のテスト"""
        # Arrange
        service._scheduler_running = True
        
        # Act
        result = await service.start_scheduler()
        
        # Assert
        assert result.is_success()  # 既に実行中でも成功を返す
    
    @pytest.mark.asyncio
    async def test_stop_scheduler_success(self, service):
        """スケジューラー停止成功のテスト"""
        # Arrange
        await service.start_scheduler()
        
        # Act
        result = await service.stop_scheduler()
        
        # Assert
        assert result.is_success()
        assert service._scheduler_running is False
        assert service._scheduler_task is None
    
    @pytest.mark.asyncio
    async def test_stop_scheduler_not_running(self, service):
        """停止済みスケジューラーの停止のテスト"""
        # Act
        result = await service.stop_scheduler()
        
        # Assert
        assert result.is_success()  # 既に停止済みでも成功を返す
    
    # ========================
    # スケジュール実行テスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_should_execute_schedule(self, service):
        """スケジュール実行判定のテスト"""
        # Arrange
        now = datetime.now(timezone.utc)
        
        # アクティブで実行時刻が来ているスケジュール
        active_schedule = ScheduleFactory(status=ScheduleStatus.ACTIVE)
        active_schedule.get_next_execution_time = Mock(return_value=now - timedelta(minutes=1))
        
        # 非アクティブなスケジュール
        inactive_schedule = ScheduleFactory(status=ScheduleStatus.INACTIVE)
        
        # 実行時刻が来ていないスケジュール
        future_schedule = ScheduleFactory(status=ScheduleStatus.ACTIVE)
        future_schedule.get_next_execution_time = Mock(return_value=now + timedelta(hours=1))
        
        # Act & Assert
        assert await service._should_execute_schedule(active_schedule) is True
        assert await service._should_execute_schedule(inactive_schedule) is False
        assert await service._should_execute_schedule(future_schedule) is False
    
    @pytest.mark.asyncio
    async def test_execute_schedule_success(self, service, mock_playback_service):
        """スケジュール実行成功のテスト"""
        # Arrange
        test_schedule = ScheduleFactory()
        test_schedule.recording_id = "test_recording_id"
        
        # Act
        await service._execute_schedule(test_schedule)
        
        # Assert
        assert test_schedule.schedule_id in service._active_executions
        mock_playback_service.start_playback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_schedule_concurrent_limit(self, service):
        """スケジュール実行の同時実行数制限テスト"""
        # Arrange
        service._max_concurrent_executions = 1
        service._active_executions["existing_execution"] = Mock()
        
        test_schedule = ScheduleFactory()
        
        # Act
        await service._execute_schedule(test_schedule)
        
        # Assert - 同時実行数制限により実行されない
        assert test_schedule.schedule_id not in service._active_executions
    
    @pytest.mark.asyncio
    async def test_monitor_active_executions(self, service, mock_playback_service):
        """アクティブ実行監視のテスト"""
        # Arrange
        schedule_id = "test_schedule_id"
        session_id = "test_session_id"
        execution_info = {
            'execution_id': 'exec_123',
            'schedule_id': schedule_id,
            'session_id': session_id,
            'started_at': datetime.now(timezone.utc)
        }
        service._active_executions[schedule_id] = execution_info
        
        # 完了したステータスを返すように設定
        completed_status = Mock()
        completed_status.is_finished = True
        completed_status.status = "completed"
        mock_playback_service.get_playback_status.return_value = Ok(completed_status)
        
        # Act
        await service._monitor_active_executions()
        
        # Assert
        assert schedule_id not in service._active_executions  # 完了したので削除される
        assert service._stats['total_executions'] == 1
        assert service._stats['successful_executions'] == 1
    
    # ========================
    # get_statistics テスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_get_statistics_success(self, service):
        """統計情報取得成功のテスト"""
        # Arrange
        test_schedules = [
            ScheduleFactory(status=ScheduleStatus.ACTIVE),
            ScheduleFactory(status=ScheduleStatus.INACTIVE),
            ScheduleFactory(status=ScheduleStatus.RUNNING)
        ]
        
        with patch.object(service._get_all_schedules_use_case, 'execute') as mock_get:
            mock_get.return_value = Ok(test_schedules)
            
            # Act
            result = await service.get_statistics()
            
            # Assert
            assert result.is_success()
            stats_dto = result.value
            assert isinstance(stats_dto, ScheduleStatsDTO)
            assert stats_dto.total_schedules == 3
            assert stats_dto.active_schedules == 1
            assert stats_dto.inactive_schedules == 1
            assert stats_dto.running_schedules == 1
    
    # ========================
    # スケジューラー状態テスト
    # ========================
    
    def test_is_scheduler_running(self, service):
        """スケジューラー実行状態確認のテスト"""
        # 初期状態
        assert service.is_scheduler_running() is False
        
        # 実行中に設定
        service._scheduler_running = True
        assert service.is_scheduler_running() is True
        
        # 停止状態に設定
        service._scheduler_running = False
        assert service.is_scheduler_running() is False
    
    # ========================
    # エラーハンドリングテスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_create_schedule_exception_handling(self, service):
        """スケジュール作成時の例外処理のテスト"""
        # Arrange
        create_dto = CreateScheduleDTOFactory()
        
        with patch.object(service._create_schedule_use_case, 'execute') as mock_execute:
            mock_execute.side_effect = Exception("Unexpected error")
            
            # Act
            result = await service.create_schedule(create_dto)
            
            # Assert
            assert result.is_failure()
            assert "CREATE_SCHEDULE_ERROR" in result.error.code
    
    @pytest.mark.asyncio
    async def test_scheduler_loop_error_resilience(self, service):
        """スケジューラーループのエラー回復力テスト"""
        # Arrange
        with patch.object(service._get_all_schedules_use_case, 'execute') as mock_get:
            mock_get.side_effect = Exception("Database error")
            
            # スケジューラーを短時間実行
            await service.start_scheduler()
            
            # 少し待機してからエラーが発生するか確認
            await asyncio.sleep(0.1)
            
            # スケジューラーは実行中のまま（エラーで停止しない）
            assert service._scheduler_running is True
            
            # クリーンアップ
            await service.stop_scheduler()
    
    @pytest.mark.asyncio
    async def test_service_robustness_with_invalid_data(self, service):
        """無効なデータに対するサービスの堅牢性テスト"""
        # Act & Assert - None IDでの操作
        result = await service.get_schedule(None)
        assert result.is_failure()
        
        result = await service.delete_schedule(None)
        assert result.is_failure()
        
        # None DTOでの操作
        with pytest.raises((AttributeError, TypeError)):
            await service.create_schedule(None)
        
        with pytest.raises((AttributeError, TypeError)):
            await service.update_schedule("test_id", None)