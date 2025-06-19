"""
Recording Application Service Unit Tests - 記録アプリケーションサービスのテスト

記録アプリケーションサービスの各メソッドとビジネスロジックをテストします。
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone, timedelta
from typing import List

from src.application.services.recording_application_service import RecordingApplicationService
from src.application.dto.recording_dto import (
    CreateRecordingDTO, 
    UpdateRecordingDTO, 
    RecordingDTO,
    RecordingSearchDTO
)
from src.core.result import Result, Ok, Err, ErrorInfo
from src.domain.entities.recording import Recording
from src.domain.entities.action import KeyboardAction
from src.domain.value_objects import RecordingStatus
from tests.factories import (
    RecordingFactory,
    CreateRecordingDTOFactory,
    UpdateRecordingDTOFactory,
    KeyboardActionFactory
)


class TestRecordingApplicationService:
    """記録アプリケーションサービスのテストクラス"""
    
    @pytest.fixture
    def mock_recording_repository(self):
        """モック記録リポジトリ"""
        mock_repo = AsyncMock()
        mock_repo.save.return_value = Ok("test_id")
        mock_repo.get_by_id.return_value = Ok(RecordingFactory())
        mock_repo.get_all.return_value = Ok([])
        mock_repo.delete.return_value = Ok(True)
        mock_repo.search.return_value = Ok([])
        mock_repo.get_statistics.return_value = Ok({
            'total_recordings': 10,
            'active_recordings': 5,
            'completed_recordings': 3,
            'failed_recordings': 2
        })
        return mock_repo
    
    @pytest.fixture
    def mock_settings_repository(self):
        """モック設定リポジトリ"""
        mock_repo = AsyncMock()
        mock_repo.get_setting.return_value = Ok("default_value")
        return mock_repo
    
    @pytest.fixture
    def mock_encryption_service(self):
        """モック暗号化サービス"""
        mock_service = Mock()
        mock_service.encrypt.return_value = b"encrypted_data"
        mock_service.decrypt.return_value = b"decrypted_data"
        return mock_service
    
    @pytest.fixture
    def mock_file_service(self):
        """モックファイルサービス"""
        mock_service = Mock()
        mock_service.save_file.return_value = Ok(True)
        mock_service.load_file.return_value = Ok("file_content")
        return mock_service
    
    @pytest.fixture
    def service(self, mock_recording_repository, mock_settings_repository, 
                mock_encryption_service, mock_file_service):
        """テスト対象のアプリケーションサービス"""
        return RecordingApplicationService(
            recording_repository=mock_recording_repository,
            settings_repository=mock_settings_repository,
            encryption_service=mock_encryption_service,
            file_service=mock_file_service
        )
    
    # ========================
    # create_recording テスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_create_recording_success(self, service, mock_recording_repository):
        """記録作成成功のテスト"""
        # Arrange
        create_dto = CreateRecordingDTOFactory()
        expected_id = "test_recording_id"
        
        # StartRecordingUseCaseのモック設定
        with patch.object(service._start_recording_use_case, 'execute') as mock_execute:
            mock_execute.return_value = Ok(expected_id)
            
            # GetRecordingUseCaseのモック設定
            test_recording = RecordingFactory(recording_id=expected_id)
            with patch.object(service._get_recording_use_case, 'execute') as mock_get:
                mock_get.return_value = Ok(test_recording)
                
                # Act
                result = await service.create_recording(create_dto)
                
                # Assert
                assert result.is_success()
                assert result.value == expected_id
                mock_execute.assert_called_once_with(
                    name=create_dto.name,
                    description=create_dto.description
                )
                mock_recording_repository.save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_recording_validation_error(self, service):
        """記録作成時のバリデーションエラーのテスト"""
        # Arrange
        invalid_dto = CreateRecordingDTOFactory(name="")  # 無効な名前
        
        # Act
        result = await service.create_recording(invalid_dto)
        
        # Assert
        assert result.is_failure()
        assert "VALIDATION_ERROR" in result.error.code
    
    @pytest.mark.asyncio
    async def test_create_recording_use_case_failure(self, service):
        """記録作成時のユースケース失敗のテスト"""
        # Arrange
        create_dto = CreateRecordingDTOFactory()
        
        with patch.object(service._start_recording_use_case, 'execute') as mock_execute:
            mock_execute.return_value = Err(ErrorInfo("USE_CASE_ERROR", "Failed to start recording"))
            
            # Act
            result = await service.create_recording(create_dto)
            
            # Assert
            assert result.is_failure()
            assert result.error.code == "USE_CASE_ERROR"
    
    # ========================
    # start_recording テスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_start_recording_success(self, service, mock_recording_repository):
        """記録開始成功のテスト"""
        # Arrange
        recording_id = "test_recording_id"
        test_recording = RecordingFactory(
            recording_id=recording_id,
            status=RecordingStatus.STOPPED
        )
        
        with patch.object(service._get_recording_use_case, 'execute') as mock_get:
            mock_get.return_value = Ok(test_recording)
            
            # Act
            result = await service.start_recording(recording_id)
            
            # Assert
            assert result.is_success()
            assert result.value is True
            mock_recording_repository.save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_recording_already_recording(self, service):
        """既に記録中の記録の開始テスト"""
        # Arrange
        recording_id = "test_recording_id"
        test_recording = RecordingFactory(
            recording_id=recording_id,
            status=RecordingStatus.RECORDING
        )
        
        with patch.object(service._get_recording_use_case, 'execute') as mock_get:
            mock_get.return_value = Ok(test_recording)
            
            # Act
            result = await service.start_recording(recording_id)
            
            # Assert
            assert result.is_failure()
            assert "RECORDING_ALREADY_STARTED" in result.error.code
    
    # ========================
    # stop_recording テスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_stop_recording_success(self, service):
        """記録停止成功のテスト"""
        # Arrange
        recording_id = "test_recording_id"
        test_recording = RecordingFactory(recording_id=recording_id)
        
        with patch.object(service._stop_recording_use_case, 'execute') as mock_execute:
            mock_execute.return_value = Ok(test_recording)
            
            # Act
            result = await service.stop_recording(recording_id)
            
            # Assert
            assert result.is_success()
            assert isinstance(result.value, RecordingDTO)
            assert result.value.recording_id == recording_id
    
    @pytest.mark.asyncio
    async def test_stop_recording_failure(self, service):
        """記録停止失敗のテスト"""
        # Arrange
        recording_id = "test_recording_id"
        
        with patch.object(service._stop_recording_use_case, 'execute') as mock_execute:
            mock_execute.return_value = Err(ErrorInfo("STOP_ERROR", "Failed to stop"))
            
            # Act
            result = await service.stop_recording(recording_id)
            
            # Assert
            assert result.is_failure()
            assert result.error.code == "STOP_ERROR"
    
    # ========================
    # add_action テスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_add_action_success(self, service):
        """アクション追加成功のテスト"""
        # Arrange
        recording_id = "test_recording_id"
        action = KeyboardActionFactory()
        
        with patch.object(service._add_action_use_case, 'execute') as mock_execute:
            mock_execute.return_value = Ok(True)
            
            # Act
            result = await service.add_action(recording_id, action)
            
            # Assert
            assert result.is_success()
            assert result.value is True
            mock_execute.assert_called_once_with(recording_id, action)
    
    @pytest.mark.asyncio
    async def test_add_action_failure(self, service):
        """アクション追加失敗のテスト"""
        # Arrange
        recording_id = "test_recording_id"
        action = KeyboardActionFactory()
        
        with patch.object(service._add_action_use_case, 'execute') as mock_execute:
            mock_execute.return_value = Err(ErrorInfo("ADD_ACTION_ERROR", "Failed to add action"))
            
            # Act
            result = await service.add_action(recording_id, action)
            
            # Assert
            assert result.is_failure()
            assert result.error.code == "ADD_ACTION_ERROR"
    
    # ========================
    # get_recording テスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_get_recording_success(self, service):
        """記録取得成功のテスト"""
        # Arrange
        recording_id = "test_recording_id"
        test_recording = RecordingFactory(recording_id=recording_id)
        
        with patch.object(service._get_recording_use_case, 'execute') as mock_execute:
            mock_execute.return_value = Ok(test_recording)
            
            # Act
            result = await service.get_recording(recording_id)
            
            # Assert
            assert result.is_success()
            assert isinstance(result.value, RecordingDTO)
            assert result.value.recording_id == recording_id
    
    @pytest.mark.asyncio
    async def test_get_recording_with_cache(self, service):
        """キャッシュされた記録取得のテスト"""
        # Arrange
        recording_id = "test_recording_id"
        cached_dto = RecordingDTO(
            recording_id=recording_id,
            name="Cached Recording",
            description="Test",
            category="test",
            tags=[],
            status="STOPPED",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            action_count=0,
            estimated_duration_ms=0
        )
        
        # キャッシュに保存
        cache_key = f"recording_{recording_id}_True"
        service._save_to_cache(cache_key, cached_dto)
        
        with patch.object(service._get_recording_use_case, 'execute') as mock_execute:
            # Act
            result = await service.get_recording(recording_id)
            
            # Assert
            assert result.is_success()
            assert result.value.name == "Cached Recording"
            mock_execute.assert_not_called()  # キャッシュから取得されるため呼ばれない
    
    @pytest.mark.asyncio
    async def test_get_recording_not_found(self, service):
        """記録が見つからない場合のテスト"""
        # Arrange
        recording_id = "nonexistent_id"
        
        with patch.object(service._get_recording_use_case, 'execute') as mock_execute:
            mock_execute.return_value = Err(ErrorInfo("NOT_FOUND", "Recording not found"))
            
            # Act
            result = await service.get_recording(recording_id)
            
            # Assert
            assert result.is_failure()
            assert result.error.code == "NOT_FOUND"
    
    # ========================
    # get_all_recordings テスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_get_all_recordings_success(self, service):
        """全記録取得成功のテスト"""
        # Arrange
        test_recordings = [RecordingFactory() for _ in range(3)]
        
        with patch.object(service._get_all_recordings_use_case, 'execute') as mock_execute:
            mock_execute.return_value = Ok(test_recordings)
            
            # Act
            result = await service.get_all_recordings(page=1, page_size=10)
            
            # Assert
            assert result.is_success()
            list_dto = result.value
            assert list_dto.total_count == 3
            assert len(list_dto.recordings) == 3
            assert list_dto.page == 1
            assert list_dto.page_size == 10
    
    @pytest.mark.asyncio
    async def test_get_all_recordings_with_status_filter(self, service):
        """ステータスフィルター付き全記録取得のテスト"""
        # Arrange
        test_recordings = [RecordingFactory(status=RecordingStatus.COMPLETED)]
        
        with patch.object(service._get_recordings_by_status_use_case, 'execute') as mock_execute:
            mock_execute.return_value = Ok(test_recordings)
            
            # Act
            result = await service.get_all_recordings(
                status_filter=RecordingStatus.COMPLETED
            )
            
            # Assert
            assert result.is_success()
            list_dto = result.value
            assert list_dto.filters["status"] == RecordingStatus.COMPLETED.value
            mock_execute.assert_called_once_with(RecordingStatus.COMPLETED)
    
    @pytest.mark.asyncio
    async def test_get_all_recordings_pagination(self, service):
        """ページング処理のテスト"""
        # Arrange
        test_recordings = [RecordingFactory() for _ in range(25)]  # 25件のテストデータ
        
        with patch.object(service._get_all_recordings_use_case, 'execute') as mock_execute:
            mock_execute.return_value = Ok(test_recordings)
            
            # Act - 2ページ目、10件ずつ
            result = await service.get_all_recordings(page=2, page_size=10)
            
            # Assert
            assert result.is_success()
            list_dto = result.value
            assert list_dto.total_count == 25
            assert len(list_dto.recordings) == 10  # 2ページ目の10件
            assert list_dto.page == 2
            assert list_dto.has_next is True
            assert list_dto.has_previous is True
    
    # ========================
    # search_recordings テスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_search_recordings_success(self, service):
        """記録検索成功のテスト"""
        # Arrange
        search_dto = RecordingSearchDTO(
            query="test query",
            page=1,
            page_size=10,
            filters={},
            sort_by="created_at",
            sort_order="desc"
        )
        test_recordings = [RecordingFactory() for _ in range(2)]
        
        with patch.object(service._search_recordings_use_case, 'execute') as mock_execute:
            mock_execute.return_value = Ok(test_recordings)
            
            # Act
            result = await service.search_recordings(search_dto)
            
            # Assert
            assert result.is_success()
            list_dto = result.value
            assert len(list_dto.recordings) == 2
            assert list_dto.sort_by == "created_at"
            assert list_dto.sort_order == "desc"
    
    @pytest.mark.asyncio
    async def test_search_recordings_validation_error(self, service):
        """検索時のバリデーションエラーのテスト"""
        # Arrange
        invalid_search_dto = RecordingSearchDTO(
            query="",  # 無効なクエリ
            page=1,
            page_size=10,
            filters={},
            sort_by="created_at",
            sort_order="desc"
        )
        
        # Act
        result = await service.search_recordings(invalid_search_dto)
        
        # Assert
        assert result.is_failure()
        assert "VALIDATION_ERROR" in result.error.code
    
    # ========================
    # update_recording テスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_update_recording_success(self, service, mock_recording_repository):
        """記録更新成功のテスト"""
        # Arrange
        recording_id = "test_recording_id"
        update_dto = UpdateRecordingDTOFactory(name="Updated Name")
        test_recording = RecordingFactory(recording_id=recording_id)
        
        with patch.object(service._get_recording_use_case, 'execute') as mock_get:
            mock_get.return_value = Ok(test_recording)
            
            # Act
            result = await service.update_recording(recording_id, update_dto)
            
            # Assert
            assert result.is_success()
            assert isinstance(result.value, RecordingDTO)
            assert test_recording.name == update_dto.name
            mock_recording_repository.save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_recording_not_found(self, service):
        """存在しない記録の更新テスト"""
        # Arrange
        recording_id = "nonexistent_id"
        update_dto = UpdateRecordingDTOFactory()
        
        with patch.object(service._get_recording_use_case, 'execute') as mock_get:
            mock_get.return_value = Err(ErrorInfo("NOT_FOUND", "Recording not found"))
            
            # Act
            result = await service.update_recording(recording_id, update_dto)
            
            # Assert
            assert result.is_failure()
            assert result.error.code == "NOT_FOUND"
    
    # ========================
    # delete_recording テスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_delete_recording_success(self, service):
        """記録削除成功のテスト"""
        # Arrange
        recording_id = "test_recording_id"
        
        with patch.object(service._delete_recording_use_case, 'execute') as mock_execute:
            mock_execute.return_value = Ok(True)
            
            # Act
            result = await service.delete_recording(recording_id)
            
            # Assert
            assert result.is_success()
            assert result.value is True
            mock_execute.assert_called_once_with(recording_id)
    
    @pytest.mark.asyncio
    async def test_delete_recording_failure(self, service):
        """記録削除失敗のテスト"""
        # Arrange
        recording_id = "test_recording_id"
        
        with patch.object(service._delete_recording_use_case, 'execute') as mock_execute:
            mock_execute.return_value = Err(ErrorInfo("DELETE_ERROR", "Failed to delete"))
            
            # Act
            result = await service.delete_recording(recording_id)
            
            # Assert
            assert result.is_failure()
            assert result.error.code == "DELETE_ERROR"
    
    # ========================
    # get_statistics テスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_get_statistics_success(self, service, mock_recording_repository):
        """統計情報取得成功のテスト"""
        # Arrange
        mock_stats = {
            'total_recordings': 10,
            'active_recordings': 5,
            'completed_recordings': 3,
            'failed_recordings': 2
        }
        mock_recording_repository.get_statistics.return_value = Ok(mock_stats)
        
        # Act
        result = await service.get_statistics()
        
        # Assert
        assert result.is_success()
        stats_dto = result.value
        assert hasattr(stats_dto, 'total_recordings')
    
    @pytest.mark.asyncio
    async def test_get_statistics_with_cache(self, service, mock_recording_repository):
        """キャッシュされた統計情報取得のテスト"""
        # Arrange
        from src.application.dto.recording_dto import RecordingStatsDTO
        cached_stats = RecordingStatsDTO(
            total_recordings=10,
            active_recordings=5,
            completed_recordings=3,
            failed_recordings=2,
            average_duration_seconds=120.0,
            total_actions=100
        )
        
        # キャッシュに保存
        service._save_to_cache("recording_stats", cached_stats)
        
        # Act
        result = await service.get_statistics()
        
        # Assert
        assert result.is_success()
        assert result.value.total_recordings == 10
        mock_recording_repository.get_statistics.assert_not_called()
    
    # ========================
    # キャッシュ管理テスト
    # ========================
    
    def test_cache_operations(self, service):
        """キャッシュ操作のテスト"""
        # Arrange
        test_data = {"test": "data"}
        cache_key = "test_key"
        
        # Act & Assert - 保存と取得
        service._save_to_cache(cache_key, test_data)
        cached_data = service._get_from_cache(cache_key)
        assert cached_data == test_data
        
        # Act & Assert - キャッシュクリア
        service._clear_cache()
        cleared_data = service._get_from_cache(cache_key)
        assert cleared_data is None
    
    def test_cache_expiration(self, service):
        """キャッシュ有効期限のテスト"""
        # Arrange
        test_data = {"test": "data"}
        cache_key = "test_key"
        
        # キャッシュタイムアウトを短く設定
        service._cache_timeout = 0.1  # 0.1秒
        
        # Act
        service._save_to_cache(cache_key, test_data)
        
        # 少し待機
        import time
        time.sleep(0.2)
        
        # Assert - 期限切れで取得できない
        cached_data = service._get_from_cache(cache_key)
        assert cached_data is None
    
    def test_clear_cache_for_recording(self, service):
        """特定記録のキャッシュクリアのテスト"""
        # Arrange
        recording_id = "test_recording_id"
        service._save_to_cache(f"recording_{recording_id}_True", {"data": "1"})
        service._save_to_cache(f"recording_{recording_id}_False", {"data": "2"})
        service._save_to_cache("other_key", {"data": "3"})
        
        # Act
        service._clear_cache_for_recording(recording_id)
        
        # Assert
        assert service._get_from_cache(f"recording_{recording_id}_True") is None
        assert service._get_from_cache(f"recording_{recording_id}_False") is None
        assert service._get_from_cache("other_key") is not None
    
    # ========================
    # エラーハンドリングテスト
    # ========================
    
    @pytest.mark.asyncio
    async def test_create_recording_exception_handling(self, service):
        """記録作成時の例外処理のテスト"""
        # Arrange
        create_dto = CreateRecordingDTOFactory()
        
        with patch.object(service._start_recording_use_case, 'execute') as mock_execute:
            mock_execute.side_effect = Exception("Unexpected error")
            
            # Act
            result = await service.create_recording(create_dto)
            
            # Assert
            assert result.is_failure()
            assert "CREATE_RECORDING_ERROR" in result.error.code
            assert "Unexpected error" in result.error.message
    
    @pytest.mark.asyncio
    async def test_service_robustness_with_none_values(self, service):
        """None値に対するサービスの堅牢性テスト"""
        # Act & Assert - None IDでの取得
        result = await service.get_recording(None)
        assert result.is_failure()
        
        # Act & Assert - None DTOでの作成
        with pytest.raises((AttributeError, TypeError)):
            await service.create_recording(None)